# -*- coding: utf-8 -*-
"""
多因子模型工具类
功能：因子计算、打分、选股、回测
"""

import datetime
import pandas as pd
import numpy as np
from logs.logger import LogManager
from src.utils.mysql_tool import MySQLUtil
from src.utils.baosock_tool import BaostockFetcher


class MultiFactorAnalyzer:
    """多因子分析器"""
    
    def __init__(self):
        self.mysql_manager = MySQLUtil()
        self.mysql_manager.connect()
        self.logger = LogManager.get_logger("multi_factor")
        self.now_date = datetime.datetime.now().strftime('%Y-%m-%d')
        
        # 因子权重配置（可根据市场状态动态调整）
        self.factor_weights = {
            'value': 0.25,        # 价值因子
            'quality': 0.25,      # 质量因子
            'growth': 0.20,       # 成长因子
            'momentum': 0.15,     # 动量因子
            'capital': 0.10,      # 资金流向因子
            'expectation': 0.05   # 分析师预期因子
        }
    
    # =====================================================
    # 因子计算模块
    # =====================================================
    
    def calculate_pe_percentile(self, stock_code=None, lookback_years=3):
        """
        计算 PE 历史分位数
        :param stock_code: 股票代码（None 表示全部）
        :param lookback_years: 回看年数
        :return: DataFrame with pe_percentile
        """
        where_clause = "WHERE 1=1"
        params = []
        if stock_code:
            where_clause += " AND stock_code = %s"
            params.append(stock_code)
        
        sql = f"""
        SELECT 
            stock_code, 
            stock_date, 
            rolling_p,
            PERCENT_RANK() OVER (
                PARTITION BY stock_code 
                ORDER BY rolling_p
                ROWS BETWEEN {lookback_years * 365} PRECEDING AND CURRENT ROW
            ) as pe_percentile
        FROM stock.stock_history_date_price
        {where_clause}
          AND rolling_p > 0
          AND stock_date <= %s
        ORDER BY stock_code, stock_date
        """
        params.append(self.now_date)
        
        result = self.mysql_manager.query_all(sql, params)
        if not result:
            return pd.DataFrame()
        
        df = pd.DataFrame(result)
        df['pe_percentile'] = df['pe_percentile'] * 100  # 转换为百分比
        return df
    
    def calculate_pb_percentile(self, stock_code=None, lookback_years=3):
        """计算 PB 历史分位数"""
        where_clause = "WHERE 1=1"
        params = []
        if stock_code:
            where_clause += " AND stock_code = %s"
            params.append(stock_code)
        
        sql = f"""
        SELECT 
            stock_code, 
            stock_date, 
            pb_ratio,
            PERCENT_RANK() OVER (
                PARTITION BY stock_code 
                ORDER BY pb_ratio
                ROWS BETWEEN {lookback_years * 365} PRECEDING AND CURRENT ROW
            ) as pb_percentile
        FROM stock.stock_history_date_price
        {where_clause}
          AND pb_ratio > 0
          AND stock_date <= %s
        ORDER BY stock_code, stock_date
        """
        params.append(self.now_date)
        
        result = self.mysql_manager.query_all(sql, params)
        if not result:
            return pd.DataFrame()
        
        df = pd.DataFrame(result)
        df['pb_percentile'] = df['pb_percentile'] * 100
        return df
    
    def calculate_momentum(self, window=60, exclude_recent=5):
        """
        计算动量因子（60 日动量，剔除近 5 日）
        :param window: 动量窗口
        :param exclude_recent: 剔除最近 N 天
        """
        sql = f"""
        SELECT 
            a.stock_code,
            a.stock_date,
            (a.close_price - b.close_price) / b.close_price * 100 as momentum_{window}d
        FROM stock.stock_history_date_price a
        JOIN stock.stock_history_date_price b 
          ON a.stock_code = b.stock_code 
          AND DATEDIFF(a.stock_date, b.stock_date) = {window + exclude_recent}
        WHERE a.stock_date = %s
        """
        result = self.mysql_manager.query_all(sql, (self.now_date,))
        if not result:
            return pd.DataFrame()
        return pd.DataFrame(result)
    
    def calculate_reversal(self, window=5):
        """
        计算反转因子（短期反转，负向因子）
        :param window: 反转窗口
        """
        sql = f"""
        SELECT 
            stock_code,
            stock_date,
            (close_price - LAG(close_price, {window}) OVER (
                PARTITION BY stock_code ORDER BY stock_date
            )) / LAG(close_price, {window}) OVER (
                PARTITION BY stock_code ORDER BY stock_date
            ) * 100 as reversal_{window}d
        FROM stock.stock_history_date_price
        WHERE stock_date = %s
        """
        result = self.mysql_manager.query_all(sql, (self.now_date,))
        if not result:
            return pd.DataFrame()
        return pd.DataFrame(result)
    
    def calculate_growth_factors(self):
        """计算成长因子（营收增速、净利润增速）"""
        sql = """
        SELECT 
            a.stock_code,
            a.publish_date,
            (a.mb_revenue - b.mb_revenue) / NULLIF(b.mb_revenue, 0) * 100 as revenue_growth_yoy,
            (a.net_profit - b.net_profit) / NULLIF(b.net_profit, 0) * 100 as profit_growth_yoy,
            (a.roe_avg - b.roe_avg) as roe_improvement
        FROM stock.stock_profit_data a
        LEFT JOIN stock.stock_profit_data b 
          ON a.stock_code = b.stock_code 
          AND a.season = b.season 
          AND YEAR(a.publish_date) = YEAR(b.publish_date) + 1
        WHERE a.publish_date <= %s
        ORDER BY a.stock_code, a.publish_date DESC
        """
        result = self.mysql_manager.query_all(sql, (self.now_date,))
        if not result:
            return pd.DataFrame()
        return pd.DataFrame(result)
    
    def calculate_quality_factors(self):
        """计算质量因子（ROE、毛利率、净利率）"""
        sql = """
        SELECT 
            stock_code,
            publish_date,
            roe_avg,
            gp_margin,
            np_margin,
            eps_ttm
        FROM stock.stock_profit_data
        WHERE publish_date <= %s
        ORDER BY stock_code, publish_date DESC
        """
        result = self.mysql_manager.query_all(sql, (self.now_date,))
        if not result:
            return pd.DataFrame()
        
        df = pd.DataFrame(result)
        # 取最新数据
        df = df.groupby('stock_code').first().reset_index()
        return df
    
    # =====================================================
    # 因子标准化与打分
    # =====================================================
    
    def normalize_factor(self, df, factor_col, ascending=True):
        """
        因子标准化（0-100 分）
        :param df: DataFrame
        :param factor_col: 因子列名
        :param ascending: True=越小越好（如 PE），False=越大越好（如 ROE）
        :return: 标准化后的分数
        """
        if factor_col not in df.columns:
            return None
        
        # 去极值（3 倍标准差）
        mean = df[factor_col].mean()
        std = df[factor_col].std()
        df[factor_col] = df[factor_col].clip(mean - 3*std, mean + 3*std)
        
        # Min-Max 标准化到 0-100
        min_val = df[factor_col].min()
        max_val = df[factor_col].max()
        
        if max_val == min_val:
            df[f'{factor_col}_score'] = 50.0
        else:
            if ascending:
                df[f'{factor_col}_score'] = 100 * (max_val - df[factor_col]) / (max_val - min_val)
            else:
                df[f'{factor_col}_score'] = 100 * (df[factor_col] - min_val) / (max_val - min_val)
        
        return df
    
    def calculate_value_score(self, df):
        """计算价值因子得分（PE 分位数 + PB 分位数）"""
        if df.empty:
            return df
        
        df = self.normalize_factor(df, 'pe_percentile', ascending=True)
        df = self.normalize_factor(df, 'pb_percentile', ascending=True)
        
        # 价值得分 = PE 分数 * 0.6 + PB 分数 * 0.4
        if 'pe_percentile_score' in df.columns and 'pb_percentile_score' in df.columns:
            df['value_score'] = df['pe_percentile_score'] * 0.6 + df['pb_percentile_score'] * 0.4
        else:
            df['value_score'] = 50.0
        
        return df
    
    def calculate_quality_score(self, df):
        """计算质量因子得分（ROE + 毛利率）"""
        if df.empty:
            return df
        
        df = self.normalize_factor(df, 'roe_avg', ascending=False)
        df = self.normalize_factor(df, 'gp_margin', ascending=False)
        
        if 'roe_avg_score' in df.columns and 'gp_margin_score' in df.columns:
            df['quality_score'] = df['roe_avg_score'] * 0.6 + df['gp_margin_score'] * 0.4
        else:
            df['quality_score'] = 50.0
        
        return df
    
    def calculate_growth_score(self, df):
        """计算成长因子得分（营收增速 + 净利润增速）"""
        if df.empty:
            return df
        
        df = self.normalize_factor(df, 'revenue_growth_yoy', ascending=False)
        df = self.normalize_factor(df, 'profit_growth_yoy', ascending=False)
        
        if 'revenue_growth_yoy_score' in df.columns and 'profit_growth_yoy_score' in df.columns:
            df['growth_score'] = df['revenue_growth_yoy_score'] * 0.5 + df['profit_growth_yoy_score'] * 0.5
        else:
            df['growth_score'] = 50.0
        
        return df
    
    def calculate_momentum_score(self, df):
        """计算动量因子得分（60 日动量 - 5 日反转）"""
        if df.empty:
            return df
        
        df = self.normalize_factor(df, f'momentum_60d', ascending=False)
        df = self.normalize_factor(df, f'reversal_5d', ascending=True)  # 反转是负向因子
        
        if f'momentum_60d_score' in df.columns:
            df['momentum_score'] = df[f'momentum_60d_score'] * 0.7
            if f'reversal_5d_score' in df.columns:
                df['momentum_score'] += df[f'reversal_5d_score'] * 0.3
        else:
            df['momentum_score'] = 50.0
        
        return df
    
    # =====================================================
    # 综合打分与选股
    # =====================================================
    
    def calculate_total_score(self, df):
        """计算综合得分"""
        if df.empty:
            return df
        
        df['total_score'] = (
            df.get('value_score', 50) * self.factor_weights['value'] +
            df.get('quality_score', 50) * self.factor_weights['quality'] +
            df.get('growth_score', 50) * self.factor_weights['growth'] +
            df.get('momentum_score', 50) * self.factor_weights['momentum'] +
            df.get('capital_score', 50) * self.factor_weights['capital'] +
            df.get('expectation_score', 50) * self.factor_weights['expectation']
        )
        
        # 计算排名
        df['total_rank'] = df['total_score'].rank(ascending=False, method='min').astype(int)
        
        return df
    
    def run_factor_analysis(self, save_to_db=True):
        """
        运行完整的多因子分析流程
        :param save_to_db: 是否保存到数据库
        :return: 打分结果 DataFrame
        """
        self.logger.info("开始多因子分析...")
        
        # 1. 获取基础数据
        self.logger.info("计算估值分位数...")
        pe_df = self.calculate_pe_percentile()
        pb_df = self.calculate_pb_percentile()
        
        self.logger.info("计算动量因子...")
        momentum_df = self.calculate_momentum()
        reversal_df = self.calculate_reversal()
        
        self.logger.info("计算成长因子...")
        growth_df = self.calculate_growth_factors()
        
        self.logger.info("计算质量因子...")
        quality_df = self.calculate_quality_factors()
        
        # 2. 合并数据
        self.logger.info("合并因子数据...")
        df = pe_df[['stock_code', 'stock_date', 'pe_percentile']].copy()
        
        if not pb_df.empty:
            df = df.merge(pb_df[['stock_code', 'pb_percentile']], on=['stock_code', 'stock_date'], how='left')
        if not momentum_df.empty:
            df = df.merge(momentum_df, on=['stock_code', 'stock_date'], how='left')
        if not reversal_df.empty:
            df = df.merge(reversal_df, on=['stock_code', 'stock_date'], how='left')
        if not growth_df.empty:
            df = df.merge(growth_df[['stock_code', 'revenue_growth_yoy', 'profit_growth_yoy', 'roe_improvement']], 
                         on='stock_code', how='left')
        if not quality_df.empty:
            df = df.merge(quality_df[['stock_code', 'roe_avg', 'gp_margin', 'np_margin', 'eps_ttm']], 
                         on='stock_code', how='left')
        
        # 3. 计算各因子得分
        self.logger.info("计算因子得分...")
        df = self.calculate_value_score(df)
        df = self.calculate_quality_score(df)
        df = self.calculate_growth_score(df)
        df = self.calculate_momentum_score(df)
        
        # 4. 计算综合得分
        df = self.calculate_total_score(df)
        
        # 5. 保存到数据库
        if save_to_db and not df.empty:
            self.logger.info("保存打分结果到数据库...")
            self._save_factor_score(df)
        
        self.logger.info(f"多因子分析完成，共处理 {len(df)} 只股票")
        return df
    
    def _save_factor_score(self, df):
        """保存因子打分结果到数据库"""
        # 准备入库数据
        insert_df = df[[
            'stock_code', 'stock_date',
            'value_score', 'pe_percentile', 'pb_percentile',
            'quality_score', 'roe_avg', 'gp_margin',
            'growth_score', 'revenue_growth_yoy', 'profit_growth_yoy',
            'momentum_score', 'momentum_60d', 'reversal_5d',
            'total_score', 'total_rank'
        ]].copy()
        
        # 填充空值
        insert_df = insert_df.fillna(0)
        
        # 批量插入
        self.mysql_manager.batch_insert_or_update(
            table_name='stock_factor_score',
            df=insert_df,
            unique_keys=['stock_code', 'stock_date']
        )
    
    # =====================================================
    # 选股策略
    # =====================================================
    
    def select_stocks(self, top_n=50, min_score=70, exclude_st=True):
        """
        选股策略
        :param top_n: 选前 N 只
        :param min_score: 最低分数要求
        :param exclude_st: 排除 ST
        :return: 选股结果 DataFrame
        """
        sql = """
        SELECT 
            f.stock_code,
            b.stock_name,
            f.stock_date,
            f.total_score,
            f.total_rank,
            f.industry_rank,
            i.industry,
            h.close_price,
            h.rolling_p as pe_ttm,
            h.pb_ratio,
            p.roe_avg,
            p.eps_ttm
        FROM stock.stock_factor_score f
        JOIN stock.stock_basic b ON f.stock_code = b.stock_code
        LEFT JOIN stock.stock_industry i ON f.stock_code = i.stock_code
        LEFT JOIN stock.stock_history_date_price h ON f.stock_code = h.stock_code AND f.stock_date = h.stock_date
        LEFT JOIN stock.stock_profit_data p ON f.stock_code = p.stock_code
        WHERE f.stock_date = (SELECT MAX(stock_date) FROM stock.stock_factor_score)
          AND b.stock_status = 1
        """
        
        if exclude_st:
            sql += " AND h.if_st = 0"
        
        sql += f" AND f.total_score >= {min_score}"
        sql += f" ORDER BY f.total_score DESC LIMIT {top_n}"
        
        result = self.mysql_manager.query_all(sql)
        if not result:
            return pd.DataFrame()
        
        df = pd.DataFrame(result)
        
        # 计算建议仓位（按得分加权）
        df['weight'] = df['total_score'] / df['total_score'].sum() * 100
        
        # 计算止损止盈
        df['stop_loss'] = df['close_price'] * 0.92  # -8% 止损
        df['stop_profit'] = df['close_price'] * 1.15  # +15% 止盈
        
        return df
    
    def save_selection_result(self, df, strategy_name='multi_factor_v1'):
        """保存选股结果到数据库"""
        if df.empty:
            return
        
        insert_df = df.copy()
        insert_df['strategy_name'] = strategy_name
        insert_df['select_date'] = insert_df['stock_date']
        insert_df['hold_period'] = 5
        insert_df['status'] = 'pending'
        
        # 选择需要的列
        cols = [
            'strategy_name', 'select_date', 'stock_code', 'stock_name',
            'total_score', 'total_rank', 'industry', 'close_price',
            'weight', 'hold_period', 'stop_loss', 'stop_profit', 'status'
        ]
        
        self.mysql_manager.batch_insert_or_update(
            table_name='stock_selection_result',
            df=insert_df[cols],
            unique_keys=['strategy_name', 'select_date', 'stock_code']
        )
        
        self.logger.info(f"保存选股结果：{len(df)} 只股票")
    
    def close(self):
        """关闭连接"""
        self.mysql_manager.close()


# =====================================================
# 测试入口
# =====================================================
if __name__ == '__main__':
    analyzer = MultiFactorAnalyzer()
    
    # 运行因子分析
    df = analyzer.run_factor_analysis(save_to_db=True)
    print(f"\n因子分析完成，共 {len(df)} 只股票")
    print(df[['stock_code', 'total_score', 'total_rank', 'value_score', 'quality_score']].head(10))
    
    # 选股
    print("\n=== 选股结果 ===")
    selected = analyzer.select_stocks(top_n=20, min_score=60)
    if not selected.empty:
        print(selected[['stock_code', 'stock_name', 'total_score', 'close_price', 'weight']].to_string())
        analyzer.save_selection_result(selected)
    
    analyzer.close()

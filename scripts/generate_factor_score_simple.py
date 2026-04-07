#!/usr/bin/env python3
"""
简化版因子打分生成脚本
- 只计算最新一天的因子值（高效）
- 基于现有数据：日线行情 + 财务数据 + 技术指标
- 输出到 stock_factor_score 表

执行方式：
    python3 scripts/generate_factor_score_simple.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import datetime
import pandas as pd
import numpy as np
from logs.logger import LogManager
from src.utils.mysql_tool import MySQLUtil


class SimpleFactorGenerator:
    """简化版因子生成器"""
    
    def __init__(self):
        self.mysql = MySQLUtil()
        self.mysql.connect()
        self.logger = LogManager.get_logger("factor_generator")
        
        # 因子权重
        self.weights = {
            'value': 0.30,      # 价值因子
            'quality': 0.25,    # 质量因子  
            'momentum': 0.20,   # 动量因子
            'volatility': 0.15, # 波动因子
            'volume': 0.10      # 成交量因子
        }
    
    def get_latest_trading_date(self):
        """获取最新交易日期"""
        sql = """
        SELECT MAX(stock_date) as latest_date 
        FROM stock_history_date_price 
        WHERE tradestatus = 1
        """
        result = self.mysql.query_one(sql)
        return result['latest_date'] if result else None
    
    def fetch_latest_price_data(self, date):
        """获取最新日线数据"""
        sql = """
        SELECT 
            stock_code,
            stock_date,
            close_price,
            pre_close,
            high_price,
            low_price,
            trading_volume,
            trading_amount,
            turn as turnover_rate,
            rolling_p as pe_ttm,
            pb_ratio,
            if_st
        FROM stock_history_date_price
        WHERE stock_date = %s
          AND tradestatus = 1
          AND rolling_p > 0
          AND pb_ratio > 0
        """
        result = self.mysql.query_all(sql, (date,))
        return pd.DataFrame(result) if result else pd.DataFrame()
    
    def fetch_history_for_momentum(self, date, days_back=60):
        """获取历史数据计算动量"""
        sql = """
        SELECT 
            stock_code,
            stock_date,
            close_price
        FROM stock_history_date_price
        WHERE stock_date BETWEEN DATE_SUB(%s, INTERVAL %s DAY) AND %s
          AND tradestatus = 1
        ORDER BY stock_code, stock_date
        """
        result = self.mysql.query_all(sql, (date, days_back + 5, date))
        return pd.DataFrame(result) if result else pd.DataFrame()
    
    def fetch_technical_indicators(self, date):
        """获取技术指标数据"""
        sql = """
        SELECT 
            m.stock_code,
            m.ma5,
            m.ma10,
            m.ma20,
            m.ma60,
            r.rsi_6,
            r.rsi_12,
            r.rsi_24,
            a.atr_14
        FROM date_stock_moving_average_table m
        LEFT JOIN stock_date_rsi r ON m.stock_code = r.stock_code AND m.stock_date = r.stock_date
        LEFT JOIN stock_date_atr a ON m.stock_code = a.stock_code AND m.stock_date = a.stock_date
        WHERE m.stock_date = %s
        """
        result = self.mysql.query_all(sql, (date,))
        return pd.DataFrame(result) if result else pd.DataFrame()
    
    def fetch_financial_data(self):
        """获取最新财务数据"""
        sql = """
        SELECT 
            stock_code,
            publish_date,
            roe_avg,
            roe_diluted,
            gp_margin as gross_margin,
            np_margin as net_margin,
            eps_ttm,
            mb_revenue,
            net_profit
        FROM stock_profit_data
        WHERE (stock_code, publish_date) IN (
            SELECT stock_code, MAX(publish_date) 
            FROM stock_profit_data 
            GROUP BY stock_code
        )
        """
        result = self.mysql.query_all(sql)
        return pd.DataFrame(result) if result else pd.DataFrame()
    
    def calculate_factors(self, latest_date):
        """计算全部因子"""
        self.logger.info(f"开始计算因子，日期: {latest_date}")
        
        # 1. 获取最新价格数据
        self.logger.info("获取最新价格数据...")
        price_df = self.fetch_latest_price_data(latest_date)
        if price_df.empty:
            self.logger.error("无价格数据")
            return pd.DataFrame()
        self.logger.info(f"价格数据: {len(price_df)} 只股票")
        
        # 2. 获取历史数据计算动量
        self.logger.info("获取历史数据计算动量...")
        hist_df = self.fetch_history_for_momentum(latest_date, 60)
        
        # 3. 计算动量因子
        momentum_factors = self._calculate_momentum(hist_df, latest_date)
        
        # 4. 获取技术指标
        self.logger.info("获取技术指标...")
        tech_df = self.fetch_technical_indicators(latest_date)
        
        # 5. 获取财务数据
        self.logger.info("获取财务数据...")
        fin_df = self.fetch_financial_data()
        
        # 6. 合并所有数据
        self.logger.info("合并数据...")
        df = price_df.copy()
        
        if not momentum_factors.empty:
            df = df.merge(momentum_factors, on='stock_code', how='left')
        
        if not tech_df.empty:
            df = df.merge(tech_df, on='stock_code', how='left')
        
        if not fin_df.empty:
            df = df.merge(fin_df, on='stock_code', how='left')
        
        # 7. 计算各因子得分
        self.logger.info("计算因子得分...")
        df = self._calculate_value_score(df)
        df = self._calculate_quality_score(df)
        df = self._calculate_momentum_score(df)
        df = self._calculate_volatility_score(df)
        df = self._calculate_volume_score(df)
        
        # 8. 计算综合得分
        df = self._calculate_total_score(df)
        
        self.logger.info(f"因子计算完成，共 {len(df)} 只股票")
        return df
    
    def _calculate_momentum(self, hist_df, latest_date):
        """计算动量因子"""
        if hist_df.empty:
            return pd.DataFrame()
        
        result = []
        for stock_code in hist_df['stock_code'].unique():
            stock_data = hist_df[hist_df['stock_code'] == stock_code].sort_values('stock_date')
            
            if len(stock_data) < 20:
                continue
            
            close = stock_data['close_price'].values
            latest_close = close[-1]
            
            # 20日动量
            if len(close) >= 20:
                momentum_20d = (latest_close - close[-20]) / close[-20] * 100
            else:
                momentum_20d = 0
            
            # 60日动量
            if len(close) >= 60:
                momentum_60d = (latest_close - close[-60]) / close[-60] * 100
            else:
                momentum_60d = 0
            
            # 5日反转（负向因子）
            if len(close) >= 5:
                reversal_5d = (latest_close - close[-5]) / close[-5] * 100
            else:
                reversal_5d = 0
            
            result.append({
                'stock_code': stock_code,
                'momentum_20d': momentum_20d,
                'momentum_60d': momentum_60d,
                'reversal_5d': reversal_5d
            })
        
        return pd.DataFrame(result)
    
    def _normalize_score(self, series, ascending=True):
        """标准化到 0-100 分"""
        # 去极值（3倍标准差）
        mean = series.mean()
        std = series.std()
        series = series.clip(mean - 3*std, mean + 3*std)
        
        # Min-Max 标准化
        min_val = series.min()
        max_val = series.max()
        
        if max_val == min_val:
            return pd.Series([50.0] * len(series))
        
        if ascending:
            return 100 * (max_val - series) / (max_val - min_val)
        else:
            return 100 * (series - min_val) / (max_val - min_val)
    
    def _calculate_value_score(self, df):
        """计算价值因子得分（PE + PB）"""
        # PE 越小越好
        if 'pe_ttm' in df.columns:
            df['pe_score'] = self._normalize_score(df['pe_ttm'], ascending=True)
        else:
            df['pe_score'] = 50.0
        
        # PB 越小越好
        if 'pb_ratio' in df.columns:
            df['pb_score'] = self._normalize_score(df['pb_ratio'], ascending=True)
        else:
            df['pb_score'] = 50.0
        
        # 价值得分 = PE得分 * 0.6 + PB得分 * 0.4
        df['value_score'] = df['pe_score'] * 0.6 + df['pb_score'] * 0.4
        
        return df
    
    def _calculate_quality_score(self, df):
        """计算质量因子得分（ROE + 毛利率）"""
        # ROE 越大越好
        if 'roe_avg' in df.columns:
            df['roe_score'] = self._normalize_score(df['roe_avg'].fillna(0), ascending=False)
        else:
            df['roe_score'] = 50.0
        
        # 毛利率越大越好
        if 'gross_margin' in df.columns:
            df['margin_score'] = self._normalize_score(df['gross_margin'].fillna(0), ascending=False)
        else:
            df['margin_score'] = 50.0
        
        # 质量得分 = ROE得分 * 0.6 + 毛利率得分 * 0.4
        df['quality_score'] = df['roe_score'] * 0.6 + df['margin_score'] * 0.4
        
        return df
    
    def _calculate_momentum_score(self, df):
        """计算动量因子得分"""
        # 60日动量越大越好
        if 'momentum_60d' in df.columns:
            df['momentum_60d_score'] = self._normalize_score(df['momentum_60d'].fillna(0), ascending=False)
        else:
            df['momentum_60d_score'] = 50.0
        
        # 5日反转越小越好（负向因子）
        if 'reversal_5d' in df.columns:
            df['reversal_5d_score'] = self._normalize_score(df['reversal_5d'].fillna(0), ascending=True)
        else:
            df['reversal_5d_score'] = 50.0
        
        # 动量得分 = 60日动量 * 0.7 + 5日反转 * 0.3
        df['momentum_score'] = df['momentum_60d_score'] * 0.7 + df['reversal_5d_score'] * 0.3
        
        return df
    
    def _calculate_volatility_score(self, df):
        """计算波动因子得分（ATR + RSI）"""
        # ATR 越小越好（低波动）
        if 'atr_14' in df.columns:
            df['atr_score'] = self._normalize_score(df['atr_14'].fillna(0), ascending=True)
        else:
            df['atr_score'] = 50.0
        
        # RSI_6 偏离50越小越好（不极端）
        if 'rsi_6' in df.columns:
            rsi_deviation = abs(df['rsi_6'].fillna(50) - 50)
            df['rsi_score'] = self._normalize_score(rsi_deviation, ascending=True)
        else:
            df['rsi_score'] = 50.0
        
        # 波动得分 = ATR得分 * 0.6 + RSI得分 * 0.4
        df['volatility_score'] = df['atr_score'] * 0.6 + df['rsi_score'] * 0.4
        
        return df
    
    def _calculate_volume_score(self, df):
        """计算成交量因子得分（换手率）"""
        # 换手率适中最好（5-10%）
        if 'turnover_rate' in df.columns:
            turnover = df['turnover_rate'].fillna(0)
            # 换手率在 5-10% 区间得分最高
            volume_score = 100 - abs(turnover - 7.5) * 5  # 7.5% 是理想值
            volume_score = volume_score.clip(0, 100)
            df['volume_score'] = volume_score
        else:
            df['volume_score'] = 50.0
        
        return df
    
    def _calculate_total_score(self, df):
        """计算综合得分"""
        df['total_score'] = (
            df['value_score'] * self.weights['value'] +
            df['quality_score'] * self.weights['quality'] +
            df['momentum_score'] * self.weights['momentum'] +
            df['volatility_score'] * self.weights['volatility'] +
            df['volume_score'] * self.weights['volume']
        )
        
        # 排名
        df['total_rank'] = df['total_score'].rank(ascending=False, method='min').astype(int)
        
        return df
    
    def save_to_db(self, df):
        """保存因子打分到数据库"""
        if df.empty:
            self.logger.warning("无数据可保存")
            return
        
        self.logger.info("保存因子打分到数据库...")
        
        # 准备插入数据
        insert_df = df[['stock_code', 'stock_date', 
                        'pe_ttm', 'pb_ratio', 'pe_score', 'pb_score', 'value_score',
                        'roe_avg', 'gross_margin', 'roe_score', 'margin_score', 'quality_score',
                        'momentum_20d', 'momentum_60d', 'reversal_5d', 
                        'momentum_60d_score', 'reversal_5d_score', 'momentum_score',
                        'atr_14', 'rsi_6', 'atr_score', 'rsi_score', 'volatility_score',
                        'turnover_rate', 'volume_score',
                        'total_score', 'total_rank']].copy()
        
        # 填充空值
        insert_df = insert_df.fillna(0)
        
        # 添加权重字段
        insert_df['value_weight'] = self.weights['value']
        insert_df['quality_weight'] = self.weights['quality']
        insert_df['momentum_weight'] = self.weights['momentum']
        insert_df['volatility_weight'] = self.weights['volatility']
        insert_df['volume_weight'] = self.weights['volume']
        
        # 批量插入
        self.mysql.batch_insert_or_update(
            table_name='stock_factor_score',
            df=insert_df,
            unique_keys=['stock_code', 'stock_date']
        )
        
        self.logger.info(f"保存完成：{len(df)} 条记录")
    
    def run(self):
        """执行完整流程"""
        try:
            # 获取最新交易日
            latest_date = self.get_latest_trading_date()
            if not latest_date:
                self.logger.error("无法获取最新交易日")
                return
            
            self.logger.info(f"最新交易日: {latest_date}")
            
            # 计算因子
            df = self.calculate_factors(latest_date)
            
            if df.empty:
                self.logger.error("因子计算失败")
                return
            
            # 保存到数据库
            self.save_to_db(df)
            
            # 输出前20只高分股票
            print("\n=== 多因子选股结果（Top 20）===")
            top20 = df.nlargest(20, 'total_score')
            display_cols = ['stock_code', 'total_score', 'total_rank', 
                           'value_score', 'quality_score', 'momentum_score',
                           'pe_ttm', 'pb_ratio', 'roe_avg', 'close_price']
            print(top20[display_cols].to_string(index=False))
            
            return df
            
        finally:
            self.mysql.close()


if __name__ == '__main__':
    generator = SimpleFactorGenerator()
    generator.run()
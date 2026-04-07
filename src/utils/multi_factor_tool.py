# -*- coding: utf-8 -*-
"""
多因子模型工具类 v2
功能：因子计算、打分、选股
优化：分批处理、内存优化、增量计算
"""

import datetime
import pandas as pd
import numpy as np
import random
import time
from logs.logger import LogManager
from src.utils.mysql_tool import MySQLUtil
from decimal import Decimal


class MultiFactorAnalyzer:
    """多因子分析器（分批处理版）"""

    # 默认配置
    DEFAULT_BATCH_SIZE = 100  # 每批处理股票数量
    DEFAULT_LOOKBACK_DAYS = 252 * 3  # 回看天数（3年）

    def __init__(self, batch_size=None):
        self.mysql_manager = MySQLUtil()
        self.mysql_manager.connect()
        self.logger = LogManager.get_logger("multi_factor")
        self.now_date = datetime.datetime.now().strftime('%Y-%m-%d')
        self.batch_size = batch_size or self.DEFAULT_BATCH_SIZE

        # 因子权重配置
        self.factor_weights = {
            'value': 0.25,        # 价值因子
            'quality': 0.25,      # 质量因子
            'growth': 0.20,       # 成长因子
            'momentum': 0.15,     # 动量因子
            'capital': 0.10,      # 资金流向因子
            'expectation': 0.05   # 分析师预期因子
        }

    # =====================================================
    # 股票列表获取
    # =====================================================

    def get_stock_list(self, exclude_st=True, min_days=60):
        """
        获取股票列表
        :param exclude_st: 排除ST
        :param min_days: 最小上市天数
        :return: 股票代码列表
        """
        sql = """
        SELECT DISTINCT stock_code
        FROM stock_history_date_price
        WHERE stock_date >= %s
          AND tradestatus = 1
        """
        params = [self.now_date]

        if exclude_st:
            sql += " AND if_st = 0"

        sql += " GROUP BY stock_code HAVING COUNT(*) >= %s"
        params.append(min_days)

        # 排除科创板和创业板（可选）
        # sql += " AND LEFT(stock_code, 2) NOT IN ('68', '30')"

        result = self.mysql_manager.query_all(sql, params)
        if not result:
            return []

        return [r['stock_code'] for r in result]

    # =====================================================
    # 分批因子计算
    # =====================================================

    def calculate_value_factors_batch(self, stock_codes, target_date=None):
        """
        分批计算价值因子（PE/PB分位数）
        使用Python计算分位数，避免SQL窗口函数性能问题
        """
        target_date = target_date or self.now_date
        lookback_days = self.DEFAULT_LOOKBACK_DAYS

        all_results = []
        total = len(stock_codes)

        for i in range(0, total, self.batch_size):
            batch = stock_codes[i:i + self.batch_size]
            self.logger.info(f"价值因子计算进度: {i+1}-{min(i+self.batch_size, total)}/{total}")

            # 批量获取历史数据
            placeholders = ','.join(['%s'] * len(batch))
            sql = f"""
            SELECT stock_code, stock_date, rolling_p, pb_ratio
            FROM stock_history_date_price
            WHERE stock_code IN ({placeholders})
              AND stock_date <= %s
              AND stock_date >= DATE_SUB(%s, INTERVAL %s DAY)
              AND tradestatus = 1
            ORDER BY stock_code, stock_date
            """
            params = tuple(batch) + (target_date, target_date, lookback_days)

            result = self.mysql_manager.query_all(sql, params)
            if not result:
                continue

            df = pd.DataFrame(result)

            # 转换Decimal
            for col in ['rolling_p', 'pb_ratio']:
                if col in df.columns:
                    df[col] = df[col].apply(lambda x: float(x) if isinstance(x, Decimal) else x)

            # 按股票分组计算分位数
            for stock_code in batch:
                stock_df = df[df['stock_code'] == stock_code].copy()
                if len(stock_df) < 30:  # 数据太少跳过
                    continue

                # 取最新一天
                latest = stock_df.iloc[-1]

                # 计算PE分位数
                pe_values = stock_df['rolling_p'].dropna()
                pe_values = pe_values[pe_values > 0]
                if len(pe_values) > 0 and pd.notna(latest['rolling_p']) and latest['rolling_p'] > 0:
                    pe_percentile = (pe_values < latest['rolling_p']).mean() * 100
                else:
                    pe_percentile = None

                # 计算PB分位数
                pb_values = stock_df['pb_ratio'].dropna()
                pb_values = pb_values[pb_values > 0]
                if len(pb_values) > 0 and pd.notna(latest['pb_ratio']) and latest['pb_ratio'] > 0:
                    pb_percentile = (pb_values < latest['pb_ratio']).mean() * 100
                else:
                    pb_percentile = None

                all_results.append({
                    'stock_code': stock_code,
                    'stock_date': latest['stock_date'],
                    'pe_percentile': pe_percentile,
                    'pb_percentile': pb_percentile,
                    'pe_ttm': float(latest['rolling_p']) if pd.notna(latest['rolling_p']) else None,
                    'pb': float(latest['pb_ratio']) if pd.notna(latest['pb_ratio']) else None
                })

            # 批次间休息
            time.sleep(random.uniform(0.3, 0.5))

        return pd.DataFrame(all_results)

    def calculate_momentum_factors_batch(self, stock_codes, target_date=None):
        """
        分批计算动量因子
        """
        target_date = target_date or self.now_date

        all_results = []
        total = len(stock_codes)

        for i in range(0, total, self.batch_size):
            batch = stock_codes[i:i + self.batch_size]
            self.logger.info(f"动量因子计算进度: {i+1}-{min(i+self.batch_size, total)}/{total}")

            placeholders = ','.join(['%s'] * len(batch))
            sql = f"""
            SELECT stock_code, stock_date, close_price, ups_and_downs
            FROM stock_history_date_price
            WHERE stock_code IN ({placeholders})
              AND stock_date <= %s
              AND stock_date >= DATE_SUB(%s, INTERVAL 80 DAY)
              AND tradestatus = 1
            ORDER BY stock_code, stock_date
            """
            params = tuple(batch) + (target_date, target_date)

            result = self.mysql_manager.query_all(sql, params)
            if not result:
                continue

            df = pd.DataFrame(result)

            # 转换
            for col in ['close_price', 'ups_and_downs']:
                if col in df.columns:
                    df[col] = df[col].apply(lambda x: float(x) if isinstance(x, Decimal) else x)

            # 按股票计算
            for stock_code in batch:
                stock_df = df[df['stock_code'] == stock_code].copy()
                if len(stock_df) < 65:
                    continue

                stock_df = stock_df.sort_values('stock_date').reset_index(drop=True)
                latest = stock_df.iloc[-1]

                # 60日动量（剔除近5日）
                if len(stock_df) >= 65:
                    close_65d_ago = stock_df.iloc[-65]['close_price']
                    close_5d_ago = stock_df.iloc[-5]['close_price']
                    momentum_60d = (close_5d_ago - close_65d_ago) / close_65d_ago * 100
                else:
                    momentum_60d = None

                # 5日反转
                if len(stock_df) >= 5:
                    close_5d_ago = stock_df.iloc[-5]['close_price']
                    reversal_5d = (latest['close_price'] - close_5d_ago) / close_5d_ago * 100
                else:
                    reversal_5d = None

                all_results.append({
                    'stock_code': stock_code,
                    'stock_date': latest['stock_date'],
                    'momentum_60d': momentum_60d,
                    'reversal_5d': reversal_5d,
                    'close_price': float(latest['close_price'])
                })

            time.sleep(random.uniform(0.3, 0.5))

        return pd.DataFrame(all_results)

    def calculate_quality_factors_batch(self, stock_codes):
        """
        分批计算质量因子（财务数据）
        """
        all_results = []
        total = len(stock_codes)

        for i in range(0, total, self.batch_size):
            batch = stock_codes[i:i + self.batch_size]
            self.logger.info(f"质量因子计算进度: {i+1}-{min(i+self.batch_size, total)}/{total}")

            placeholders = ','.join(['%s'] * len(batch))
            sql = f"""
            SELECT stock_code, roe_avg, gp_margin, np_margin, eps_ttm
            FROM stock_profit_data
            WHERE stock_code IN ({placeholders})
            ORDER BY stock_code, publish_date DESC
            """
            params = tuple(batch)

            result = self.mysql_manager.query_all(sql, params)
            if not result:
                continue

            df = pd.DataFrame(result)

            # 转换
            for col in ['roe_avg', 'gp_margin', 'np_margin', 'eps_ttm']:
                if col in df.columns:
                    df[col] = df[col].apply(lambda x: float(x) if isinstance(x, Decimal) else x)

            # 取每只股票最新一条
            df = df.drop_duplicates(subset=['stock_code'], keep='first')

            all_results.append(df)
            time.sleep(random.uniform(0.2, 0.3))

        if all_results:
            return pd.concat(all_results, ignore_index=True)
        return pd.DataFrame()

    def calculate_growth_factors_batch(self, stock_codes):
        """
        分批计算成长因子（同比增速）
        """
        all_results = []
        total = len(stock_codes)

        for i in range(0, total, self.batch_size):
            batch = stock_codes[i:i + self.batch_size]
            self.logger.info(f"成长因子计算进度: {i+1}-{min(i+self.batch_size, total)}/{total}")

            placeholders = ','.join(['%s'] * len(batch))
            sql = f"""
            SELECT
                a.stock_code,
                (a.mb_revenue - b.mb_revenue) / NULLIF(b.mb_revenue, 0) * 100 as revenue_growth_yoy,
                (a.net_profit - b.net_profit) / NULLIF(b.net_profit, 0) * 100 as profit_growth_yoy
            FROM stock_profit_data a
            LEFT JOIN stock_profit_data b
              ON a.stock_code = b.stock_code
              AND a.season = b.season
              AND YEAR(a.publish_date) = YEAR(b.publish_date) + 1
            WHERE a.stock_code IN ({placeholders})
            ORDER BY a.stock_code, a.publish_date DESC
            """
            params = tuple(batch)

            result = self.mysql_manager.query_all(sql, params)
            if not result:
                continue

            df = pd.DataFrame(result)

            for col in ['revenue_growth_yoy', 'profit_growth_yoy']:
                if col in df.columns:
                    df[col] = df[col].apply(lambda x: float(x) if isinstance(x, Decimal) else x)

            df = df.drop_duplicates(subset=['stock_code'], keep='first')
            all_results.append(df)
            time.sleep(random.uniform(0.2, 0.3))

        if all_results:
            return pd.concat(all_results, ignore_index=True)
        return pd.DataFrame()

    def calculate_capital_factors_batch(self, stock_codes, target_date=None):
        """
        分批计算资金流向因子
        """
        target_date = target_date or self.now_date

        all_results = []
        total = len(stock_codes)

        for i in range(0, total, self.batch_size):
            batch = stock_codes[i:i + self.batch_size]
            self.logger.info(f"资金流向因子计算进度: {i+1}-{min(i+self.batch_size, total)}/{total}")

            placeholders = ','.join(['%s'] * len(batch))
            sql = f"""
            SELECT stock_code, stock_date,
                   main_net_in, main_net_in_rate,
                   super_net_in, big_net_in
            FROM stock_capital_flow
            WHERE stock_code IN ({placeholders})
              AND stock_date <= %s
            ORDER BY stock_code, stock_date DESC
            """
            params = tuple(batch) + (target_date,)

            result = self.mysql_manager.query_all(sql, params)
            if not result:
                continue

            df = pd.DataFrame(result)

            for col in ['main_net_in', 'main_net_in_rate', 'super_net_in', 'big_net_in']:
                if col in df.columns:
                    df[col] = df[col].apply(lambda x: float(x) if isinstance(x, Decimal) else x)

            # 取每只股票最新一条
            df = df.drop_duplicates(subset=['stock_code'], keep='first')

            all_results.append(df)
            time.sleep(random.uniform(0.2, 0.3))

        if all_results:
            return pd.concat(all_results, ignore_index=True)
        return pd.DataFrame()

    def calculate_expectation_factors_batch(self, stock_codes):
        """
        分批计算分析师预期因子
        """
        all_results = []
        total = len(stock_codes)

        for i in range(0, total, self.batch_size):
            batch = stock_codes[i:i + self.batch_size]
            self.logger.info(f"分析师预期因子计算进度: {i+1}-{min(i+self.batch_size, total)}/{total}")

            placeholders = ','.join(['%s'] * len(batch))
            sql = f"""
            SELECT stock_code, rating_score, rating_type, target_price
            FROM stock_analyst_expectation
            WHERE stock_code IN ({placeholders})
            ORDER BY stock_code, publish_date DESC
            """
            params = tuple(batch)

            result = self.mysql_manager.query_all(sql, params)
            if not result:
                continue

            df = pd.DataFrame(result)

            for col in ['rating_score', 'target_price']:
                if col in df.columns:
                    df[col] = df[col].apply(lambda x: float(x) if isinstance(x, Decimal) else x)

            df = df.drop_duplicates(subset=['stock_code'], keep='first')
            all_results.append(df)
            time.sleep(random.uniform(0.2, 0.3))

        if all_results:
            return pd.concat(all_results, ignore_index=True)
        return pd.DataFrame()

    # =====================================================
    # 因子标准化
    # =====================================================

    def normalize_factor(self, df, factor_col, ascending=True):
        """
        因子标准化（0-100分）
        :param ascending: True=越小越好（如PE），False=越大越好（如ROE）
        """
        if factor_col not in df.columns:
            return df

        # 去极值（3倍标准差）
        valid = df[factor_col].dropna()
        if len(valid) < 10:
            df[f'{factor_col}_score'] = 50.0
            return df

        mean = valid.mean()
        std = valid.std()
        lower = mean - 3 * std
        upper = mean + 3 * std

        df[factor_col] = df[factor_col].clip(lower, upper)

        # Min-Max标准化
        min_val = df[factor_col].min()
        max_val = df[factor_col].max()

        if max_val == min_val or pd.isna(min_val) or pd.isna(max_val):
            df[f'{factor_col}_score'] = 50.0
        else:
            if ascending:
                df[f'{factor_col}_score'] = 100 * (max_val - df[factor_col]) / (max_val - min_val)
            else:
                df[f'{factor_col}_score'] = 100 * (df[factor_col] - min_val) / (max_val - min_val)

        # 空值填充中位数
        df[f'{factor_col}_score'] = df[f'{factor_col}_score'].fillna(50.0)

        return df

    def calculate_all_scores(self, df):
        """计算所有因子得分"""
        if df.empty:
            return df

        # 价值得分
        df = self.normalize_factor(df, 'pe_percentile', ascending=True)
        df = self.normalize_factor(df, 'pb_percentile', ascending=True)
        if 'pe_percentile_score' in df.columns and 'pb_percentile_score' in df.columns:
            df['value_score'] = df['pe_percentile_score'] * 0.6 + df['pb_percentile_score'] * 0.4
        else:
            df['value_score'] = 50.0

        # 质量得分
        df = self.normalize_factor(df, 'roe_avg', ascending=False)
        df = self.normalize_factor(df, 'gp_margin', ascending=False)
        if 'roe_avg_score' in df.columns and 'gp_margin_score' in df.columns:
            df['quality_score'] = df['roe_avg_score'] * 0.6 + df['gp_margin_score'] * 0.4
        else:
            df['quality_score'] = 50.0

        # 成长得分
        df = self.normalize_factor(df, 'revenue_growth_yoy', ascending=False)
        df = self.normalize_factor(df, 'profit_growth_yoy', ascending=False)
        if 'revenue_growth_yoy_score' in df.columns and 'profit_growth_yoy_score' in df.columns:
            df['growth_score'] = df['revenue_growth_yoy_score'] * 0.5 + df['profit_growth_yoy_score'] * 0.5
        else:
            df['growth_score'] = 50.0

        # 动量得分
        df = self.normalize_factor(df, 'momentum_60d', ascending=False)
        df = self.normalize_factor(df, 'reversal_5d', ascending=True)
        if 'momentum_60d_score' in df.columns:
            df['momentum_score'] = df['momentum_60d_score'] * 0.7
            if 'reversal_5d_score' in df.columns:
                df['momentum_score'] = df['momentum_score'] + df['reversal_5d_score'] * 0.3
        else:
            df['momentum_score'] = 50.0

        # 资金流向得分
        df = self.normalize_factor(df, 'main_net_in_rate', ascending=False)
        if 'main_net_in_rate_score' in df.columns:
            df['capital_score'] = df['main_net_in_rate_score']
        else:
            df['capital_score'] = 50.0

        # 分析师预期得分
        df = self.normalize_factor(df, 'rating_score', ascending=False)
        if 'rating_score_score' in df.columns:
            df['expectation_score'] = df['rating_score_score']
        else:
            df['expectation_score'] = 50.0

        # 综合得分
        df['total_score'] = (
            df['value_score'].fillna(50) * self.factor_weights['value'] +
            df['quality_score'].fillna(50) * self.factor_weights['quality'] +
            df['growth_score'].fillna(50) * self.factor_weights['growth'] +
            df['momentum_score'].fillna(50) * self.factor_weights['momentum'] +
            df['capital_score'].fillna(50) * self.factor_weights['capital'] +
            df['expectation_score'].fillna(50) * self.factor_weights['expectation']
        )

        # 排名
        df['total_rank'] = df['total_score'].rank(ascending=False, method='min').astype(int)

        return df

    # =====================================================
    # 主流程
    # =====================================================

    def run_factor_analysis(self, stock_codes=None, save_to_db=True, target_date=None):
        """
        运行完整的多因子分析（分批处理）
        :param stock_codes: 股票列表（None则自动获取）
        :param save_to_db: 是否保存到数据库
        :param target_date: 目标日期
        :return: 打分结果DataFrame
        """
        target_date = target_date or self.now_date
        self.logger.info(f"=== 开始多因子分析 {target_date} ===")

        # 1. 获取股票列表
        if stock_codes is None:
            self.logger.info("获取股票列表...")
            stock_codes = self.get_stock_list()
            self.logger.info(f"共 {len(stock_codes)} 只股票")

        if not stock_codes:
            self.logger.error("股票列表为空")
            return pd.DataFrame()

        # 2. 分批计算各因子
        self.logger.info("\n[1/6] 计算价值因子...")
        value_df = self.calculate_value_factors_batch(stock_codes, target_date)

        self.logger.info("\n[2/6] 计算动量因子...")
        momentum_df = self.calculate_momentum_factors_batch(stock_codes, target_date)

        self.logger.info("\n[3/6] 计算质量因子...")
        quality_df = self.calculate_quality_factors_batch(stock_codes)

        self.logger.info("\n[4/6] 计算成长因子...")
        growth_df = self.calculate_growth_factors_batch(stock_codes)

        self.logger.info("\n[5/6] 计算资金流向因子...")
        capital_df = self.calculate_capital_factors_batch(stock_codes, target_date)

        self.logger.info("\n[6/6] 计算分析师预期因子...")
        expectation_df = self.calculate_expectation_factors_batch(stock_codes)

        # 3. 合并数据
        self.logger.info("\n合并因子数据...")
        df = value_df.copy()

        if not momentum_df.empty:
            df = df.merge(momentum_df[['stock_code', 'momentum_60d', 'reversal_5d', 'close_price']],
                          on='stock_code', how='left')
        if not quality_df.empty:
            df = df.merge(quality_df, on='stock_code', how='left')
        if not growth_df.empty:
            df = df.merge(growth_df, on='stock_code', how='left')
        if not capital_df.empty:
            df = df.merge(capital_df, on='stock_code', how='left')
        if not expectation_df.empty:
            df = df.merge(expectation_df, on='stock_code', how='left')

        # 4. 计算得分
        self.logger.info("计算因子得分...")
        df = self.calculate_all_scores(df)

        # 5. 保存到数据库
        if save_to_db and not df.empty:
            self.logger.info("保存打分结果...")
            self._save_factor_score(df, target_date)

        self.logger.info(f"\n=== 多因子分析完成，共 {len(df)} 只股票 ===")
        return df

    def _save_factor_score(self, df, target_date):
        """保存因子打分结果（列名映射到数据库表）"""
        # 选择需要保存的列，并重命名为数据库表对应的列名
        save_cols = {
            'stock_code': 'stock_code',
            'stock_date': 'stock_date',
            'value_score': 'value_score',
            'pe_percentile': 'pe_percentile',
            'pb_percentile': 'pb_percentile',
            'quality_score': 'quality_score',
            'roe_avg': 'roe_score',  # 映射
            'gp_margin': 'margin_score',  # 映射
            'growth_score': 'growth_score',
            'revenue_growth_yoy': 'revenue_growth',  # 映射
            'profit_growth_yoy': 'profit_growth',  # 映射
            'momentum_score': 'momentum_score',
            'momentum_60d': 'momentum_60d',
            'reversal_5d': 'reversal_5d',
            'capital_score': 'capital_score',
            'main_net_in_rate': 'main_net_ratio',  # 映射
            'expectation_score': 'expectation_score',
            'rating_score': 'rating_score',
            'total_score': 'total_score',
            'total_rank': 'total_rank'
        }

        # 只选择存在的列
        available_cols = [col for col in save_cols.keys() if col in df.columns]
        insert_df = df[available_cols].copy()

        # 重命名列
        insert_df = insert_df.rename(columns={k: v for k, v in save_cols.items() if k in available_cols})

        insert_df = insert_df.fillna(0)
        insert_df['stock_date'] = target_date

        self.mysql_manager.batch_insert_or_update(
            table_name='stock_factor_score',
            df=insert_df,
            unique_keys=['stock_code', 'stock_date']
        )

    def select_stocks(self, top_n=50, min_score=60, target_date=None):
        """
        选股策略
        """
        target_date = target_date or self.now_date

        sql = """
        SELECT
            f.stock_code,
            b.stock_name,
            f.stock_date,
            f.total_score,
            f.total_rank,
            f.value_score,
            f.quality_score,
            f.growth_score,
            f.momentum_score,
            f.capital_score,
            h.close_price,
            f.pe_percentile,
            f.pb_percentile
        FROM stock_factor_score f
        JOIN stock_basic b ON f.stock_code = b.stock_code
        LEFT JOIN stock_history_date_price h
          ON f.stock_code = h.stock_code AND f.stock_date = h.stock_date
        WHERE f.stock_date = %s
          AND f.total_score >= %s
          AND b.stock_status = 1
        ORDER BY f.total_score DESC
        LIMIT %s
        """

        result = self.mysql_manager.query_all(sql, (target_date, min_score, top_n))
        if not result:
            return pd.DataFrame()

        df = pd.DataFrame(result)

        # 计算建议仓位
        df['weight'] = df['total_score'] / df['total_score'].sum() * 100

        # 止损止盈
        df['stop_loss'] = df['close_price'] * 0.92
        df['stop_profit'] = df['close_price'] * 1.15

        return df

    def close(self):
        """关闭连接"""
        self.mysql_manager.close()


# =====================================================
# 测试入口
# =====================================================
if __name__ == '__main__':
    analyzer = MultiFactorAnalyzer(batch_size=100)

    try:
        # 运行因子分析
        df = analyzer.run_factor_analysis(save_to_db=True)
        print(f"\n因子分析完成，共 {len(df)} 只股票")

        if not df.empty:
            print("\n=== TOP 10 股票 ===")
            top10 = df.nsmallest(10, 'total_rank')[['stock_code', 'total_score', 'total_rank',
                                                      'value_score', 'quality_score', 'growth_score']]
            print(top10.to_string())

            # 选股
            print("\n=== 选股结果 ===")
            selected = analyzer.select_stocks(top_n=20, min_score=60)
            if not selected.empty:
                print(selected[['stock_code', 'stock_name', 'total_score', 'close_price', 'weight']].to_string())
    finally:
        analyzer.close()
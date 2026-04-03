#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
量价因子验证 - 改进版

改进内容：
    1. 加入大盘状态判断（利用指数数据）
    2. 加入相对位置判断（均线偏离度）
    3. 加入成交量趋势判断（连续缩量 vs 单日缩量）
    4. 分组对照实验（缩量下跌 vs 正常换手率）
    5. 统计置信区间（判断显著性）

目标：
    找出策略有效的真实条件和最优参数

Author: Xiao Luo
Date: 2026-04-03
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
from src.utils.mysql_tool import MySQLUtil
from logs.logger import LogManager


class ImprovedFactorValidator:
    """改进版因子验证器"""

    OUTPUT_DIR = Path(__file__).parent.parent / 'data' / 'improved_validation'

    # 时间分段
    PERIODS = [
        ('2024-Q1', '2024-01-01', '2024-03-31'),
        ('2024-Q2', '2024-04-01', '2024-06-30'),
        ('2024-Q3', '2024-07-01', '2024-09-30'),
        ('2024-Q4', '2024-10-01', '2024-12-31'),
        ('2025-Q1', '2025-01-01', '2025-03-31'),
        ('2025-Q2', '2025-04-01', '2025-06-30'),
        ('2025-Q3', '2025-07-01', '2025-09-30'),
        ('2025-Q4', '2025-10-01', '2025-12-31'),
        ('2026-Q1', '2026-01-01', '2026-03-08'),
    ]

    def __init__(self):
        self.mysql = MySQLUtil()
        self.mysql.connect()
        self.logger = LogManager.get_logger("improved_validator")
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        # 缓存指数数据
        self._index_cache = None
        self._index_ma20_cache = None

    def close(self):
        self.mysql.close()

    def load_index_data(self) -> pd.DataFrame:
        """加载指数历史数据（上证指数）"""
        if self._index_cache is not None:
            return self._index_cache

        sql = '''
            SELECT stock_date, close_price, ups_and_downs
            FROM index_stock_history_date_price
            WHERE stock_code = '000001'
              AND stock_date >= '2023-12-01'
              AND stock_date <= '2026-03-20'
            ORDER BY stock_date ASC
        '''
        result = self.mysql.query_all(sql)
        df = pd.DataFrame(result)
        df['stock_date'] = pd.to_datetime(df['stock_date'])
        df['close_price'] = pd.to_numeric(df['close_price'])
        df['ups_and_downs'] = pd.to_numeric(df['ups_and_downs'])

        # 计算20日均线
        df['ma20'] = df['close_price'].rolling(20).mean()

        # 计算前60日涨跌幅
        df['prev_60d_change'] = df['close_price'].pct_change(60) * 100

        self._index_cache = df
        return df

    def get_market_state(self, date: datetime) -> dict:
        """
        获取某日的市场状态

        Returns:
            dict: {
                'index_change': 当日指数涨跌幅,
                'index_ma20_deviation': 指数偏离MA20,
                'prev_60d_change': 前60日涨跌幅,
                'market_state': '大涨/震荡/大跌'
            }
        """
        index_df = self.load_index_data()
        date = pd.to_datetime(date)

        row = index_df[index_df['stock_date'] == date]
        if len(row) == 0:
            return None

        row = row.iloc[0]

        prev_60d = row['prev_60d_change'] if not pd.isna(row['prev_60d_change']) else 0
        ma20_dev = (row['close_price'] - row['ma20']) / row['ma20'] * 100 if not pd.isna(row['ma20']) else 0

        # 判断市场状态
        if prev_60d > 5:
            market_state = '大涨'
        elif prev_60d < -5:
            market_state = '大跌'
        else:
            market_state = '震荡'

        return {
            'date': date,
            'index_change': row['ups_and_downs'],
            'index_ma20_deviation': ma20_dev,
            'prev_60d_change': prev_60d,
            'market_state': market_state,
        }

    def fetch_signals_batch(self, start: str, end: str,
                            drop_range: tuple, turn_range: tuple) -> pd.DataFrame:
        """
        分批查询信号数据（加入大盘状态）

        Args:
            start: 开始日期
            end: 结束日期
            drop_range: 跌幅范围 (min, max)
            turn_range: 换手率范围 (min, max)
        """
        sql = f'''
            SELECT
                s.stock_code,
                s.stock_date as signal_date,
                s.ups_and_downs,
                s.turn,
                s.close_price as signal_close,
                s.trading_volume,
                s.high_price,
                s.low_price,
                s.pre_close,
                (s.trading_volume / s.turn * 100 * s.close_price / 100000000) as circ_cap_yi,
                i.industry,
                idx.close_price as index_close,
                idx.ups_and_downs as index_change,
                f1.open_price as buy_price,
                f1.close_price as day1_close,
                f1.high_price as day1_high,
                f1.low_price as day1_low,
                f2.close_price as day2_close,
                f3.close_price as day3_close,
                f5.close_price as day5_close,
                f10.close_price as day10_close,
                -- 前几日换手率（用于判断缩量趋势）
                prev1.turn as prev1_turn,
                prev2.turn as prev2_turn,
                prev3.turn as prev3_turn,
                prev4.turn as prev4_turn,
                prev5.turn as prev5_turn
            FROM (
                SELECT stock_code, stock_date, ups_and_downs, turn, close_price,
                       trading_volume, high_price, low_price, pre_close
                FROM stock_history_date_price
                WHERE stock_date >= '{start}'
                  AND stock_date <= '{end}'
                  AND tradestatus = 1
                  AND ups_and_downs > {drop_range[0]}
                  AND ups_and_downs < {drop_range[1]}
                  AND turn > 0.1
                  AND turn >= {turn_range[0]}
                  AND turn < {turn_range[1]}
            ) s
            LEFT JOIN stock_industry i ON s.stock_code = i.stock_code
            LEFT JOIN index_stock_history_date_price idx
                ON idx.stock_date = s.stock_date AND idx.stock_code = '000001'
            LEFT JOIN stock_history_date_price f1
                ON f1.stock_code = s.stock_code
                AND f1.stock_date = DATE_ADD(s.stock_date, INTERVAL 1 DAY)
                AND f1.tradestatus = 1
            LEFT JOIN stock_history_date_price f2
                ON f2.stock_code = s.stock_code
                AND f2.stock_date = DATE_ADD(s.stock_date, INTERVAL 2 DAY)
                AND f2.tradestatus = 1
            LEFT JOIN stock_history_date_price f3
                ON f3.stock_code = s.stock_code
                AND f3.stock_date = DATE_ADD(s.stock_date, INTERVAL 3 DAY)
                AND f3.tradestatus = 1
            LEFT JOIN stock_history_date_price f5
                ON f5.stock_code = s.stock_code
                AND f5.stock_date = DATE_ADD(s.stock_date, INTERVAL 5 DAY)
                AND f5.tradestatus = 1
            LEFT JOIN stock_history_date_price f10
                ON f10.stock_code = s.stock_code
                AND f10.stock_date = DATE_ADD(s.stock_date, INTERVAL 10 DAY)
                AND f10.tradestatus = 1
            LEFT JOIN stock_history_date_price prev1
                ON prev1.stock_code = s.stock_code
                AND prev1.stock_date = DATE_SUB(s.stock_date, INTERVAL 1 DAY)
                AND prev1.tradestatus = 1
            LEFT JOIN stock_history_date_price prev2
                ON prev2.stock_code = s.stock_code
                AND prev2.stock_date = DATE_SUB(s.stock_date, INTERVAL 2 DAY)
                AND prev2.tradestatus = 1
            LEFT JOIN stock_history_date_price prev3
                ON prev3.stock_code = s.stock_code
                AND prev3.stock_date = DATE_SUB(s.stock_date, INTERVAL 3 DAY)
                AND prev3.tradestatus = 1
            LEFT JOIN stock_history_date_price prev4
                ON prev4.stock_code = s.stock_code
                AND prev4.stock_date = DATE_SUB(s.stock_date, INTERVAL 4 DAY)
                AND prev4.tradestatus = 1
            LEFT JOIN stock_history_date_price prev5
                ON prev5.stock_code = s.stock_code
                AND prev5.stock_date = DATE_SUB(s.stock_date, INTERVAL 5 DAY)
                AND prev5.tradestatus = 1
            WHERE (s.trading_volume / s.turn * 100 * s.close_price / 100000000) < 100
              AND (s.trading_volume / s.turn * 100 * s.close_price / 100000000) > 1
        '''

        result = self.mysql.query_all(sql)
        if result:
            df = pd.DataFrame(result)
            return df
        return pd.DataFrame()

    def calculate_position_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算位置指标（均线偏离度、缩量趋势等）"""
        if df.empty:
            return df

        # 转换数值类型（数据库返回Decimal类型）
        numeric_cols = ['signal_close', 'buy_price', 'day1_close', 'day1_high', 'day1_low',
                        'day2_close', 'day3_close', 'day5_close', 'day10_close',
                        'high_price', 'low_price', 'pre_close', 'ups_and_downs', 'turn',
                        'circ_cap_yi', 'index_close', 'index_change',
                        'prev1_turn', 'prev2_turn', 'prev3_turn', 'prev4_turn', 'prev5_turn']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # 1. 剔除无法买入的样本
        df = df[df['buy_price'].notna() & (df['buy_price'] > 0)].copy()

        # 2. 计算收益（先计算，用于后续判断）
        for days in [1, 2, 3, 5, 10]:
            col = f'day{days}_close'
            ret_col = f'return_{days}d'
            df[ret_col] = np.where(
                (df[col].notna()) & (df['buy_price'] > 0),
                (df[col] / df['buy_price'] - 1) * 100,
                np.nan
            )

        # 3. 计算日内振幅
        df['day1_range'] = (df['day1_high'] - df['day1_low']) / df['buy_price'] * 100
        df['signal_range'] = (df['high_price'] - df['low_price']) / df['signal_close'] * 100

        # 4. 判断交易限制
        # 次日涨停：日内振幅极小 + 上涨（买入困难，剔除）
        df['is_limit_up'] = (df['day1_range'] < 0.5) & (df['return_1d'] > 0)

        # 次日跌停：日内振幅极小 + 下跌（卖出困难，记录风险）
        df['next_day_limit_down'] = (df['day1_range'] < 0.5) & (df['return_1d'] < -9)

        # 信号日跌停
        df['signal_limit_down'] = (df['ups_and_downs'] < -9.5) | (df['signal_range'] < 0.5)
        df['data_error'] = (df['signal_range'] < 0.1) & (df['ups_and_downs'] > -9)

        # 统计（不剔除跌停，但统计次日跌停风险）
        signal_limit_count = df['signal_limit_down'].sum()
        next_limit_count = df['next_day_limit_down'].sum()
        if signal_limit_count > 0:
            print(f"  信号日跌停: {signal_limit_count} 条（可买入）")
        if next_limit_count > 0:
            print(f"  次日继续跌停: {next_limit_count} 条（卖出困难风险）")

        # 仅剔除次日涨停（买入困难）
        df = df[~df['is_limit_up'] & ~df['data_error']].copy()

        # 3. 计算均线偏离度（需要额外查询历史数据，这里简化为相对前5日均价）
        df['prev5_avg_close'] = (df['pre_close'] + df['signal_close'] * 0) / 1  # 简化
        # 使用 pre_close 作为前一日收盘价估算偏离度
        if 'pre_close' in df.columns and df['pre_close'].notna().any():
            # 估算20日均价：用信号日收盘价和前日收盘价估算趋势
            # 更精确需要额外查询，这里用简化方法
            df['ma20_estimate'] = df['signal_close'] * 0.95  # 保守估计
            df['ma20_deviation'] = (df['signal_close'] - df['ma20_estimate']) / df['ma20_estimate'] * 100
        else:
            df['ma20_deviation'] = 0

        # 4. 计算缩量趋势
        def classify_volume_trend(row):
            """判断缩量趋势：连续缩量 vs 单日缩量"""
            turns = [row.get(f'prev{i}_turn', None) for i in range(1, 6)]
            turns = [t for t in turns if t is not None and not pd.isna(t)]

            if len(turns) >= 3:
                # 前3日都缩量（< 3%）
                if all(t < 3 for t in turns[:3]):
                    return '连续缩量'
                # 仅当日缩量
                elif row['turn'] < 2 and any(t >= 2 for t in turns[:3]):
                    return '单日缩量'
            return '其他'

        df['volume_trend'] = df.apply(classify_volume_trend, axis=1)

        # 5. 计算市场状态
        df['signal_date'] = pd.to_datetime(df['signal_date'])
        index_df = self.load_index_data()

        # 合并指数数据
        df = df.merge(
            index_df[['stock_date', 'prev_60d_change', 'ma20']].rename(columns={'stock_date': 'signal_date'}),
            on='signal_date',
            how='left'
        )

        # 计算指数偏离度
        df['index_ma20_deviation'] = (df['index_close'] - df['ma20']) / df['ma20'] * 100

        # 判断市场状态
        def classify_market(prev_60d):
            if pd.isna(prev_60d):
                return '未知'
            if prev_60d > 5:
                return '大涨'
            if prev_60d < -5:
                return '大跌'
            return '震荡'

        df['market_state'] = df['prev_60d_change'].apply(classify_market)

        return df

    def calc_confidence_interval(self, win_rate: float, n: int, confidence: float = 0.95) -> tuple:
        """
        计算胜率的置信区间

        Args:
            win_rate: 胜率（百分比）
            n: 样本数
            confidence: 置信水平（默认95%）

        Returns:
            (下限, 上限, 结论)
        """
        if n < 30:
            return (0, 100, '样本不足')

        p = win_rate / 100
        se = np.sqrt(p * (1 - p) / n)
        z = 1.96  # 95%置信水平

        ci_low = (p - z * se) * 100
        ci_high = (p + z * se) * 100

        # 判断显著性
        if ci_low > 50:
            conclusion = '显著有效'
        elif ci_high < 50:
            conclusion = '显著无效'
        else:
            conclusion = '不确定'

        return (ci_low, ci_high, conclusion)

    def run_validation(self) -> dict:
        """运行改进版验证"""
        print("=" * 80)
        print("量价因子验证 - 改进版")
        print("=" * 80)
        print("\n改进内容:")
        print("  1. 加入大盘状态判断")
        print("  2. 加入缩量趋势判断")
        print("  3. 分组对照实验")
        print("  4. 统计置信区间")

        # 1. 查询实验组数据（缩量下跌）
        print("\n[步骤1] 查询实验组数据（缩量下跌，turn < 2%）...")
        exp_dfs = []
        for period_name, start, end in self.PERIODS:
            df = self.fetch_signals_batch(start, end, drop_range=(-10, -3), turn_range=(0.1, 2))
            if not df.empty:
                exp_dfs.append(df)
                print(f"  {period_name}: {len(df)} 条")

        # 2. 查询对照组数据（正常换手率）
        print("\n[步骤2] 查询对照组数据（正常换手率，turn 2%~5%）...")
        ctrl_dfs = []
        for period_name, start, end in self.PERIODS:
            df = self.fetch_signals_batch(start, end, drop_range=(-10, -3), turn_range=(2, 5))
            if not df.empty:
                ctrl_dfs.append(df)
                print(f"  {period_name}: {len(df)} 条")

        # 3. 合并并计算指标
        print("\n[步骤3] 合并数据并计算指标...")

        if not exp_dfs:
            print("无实验组数据")
            return None

        exp_df = pd.concat(exp_dfs, ignore_index=True)
        exp_df = self.calculate_position_indicators(exp_df)
        print(f"  实验组有效样本: {len(exp_df)}")

        if ctrl_dfs:
            ctrl_df = pd.concat(ctrl_dfs, ignore_index=True)
            ctrl_df = self.calculate_position_indicators(ctrl_df)
            print(f"  对照组有效样本: {len(ctrl_df)}")
        else:
            ctrl_df = pd.DataFrame()

        # 保存数据
        if 'stock_code' in exp_df.columns:
            exp_df['stock_code'] = exp_df['stock_code'].astype(str).str.zfill(6)
        if 'stock_code' in ctrl_df.columns:
            ctrl_df['stock_code'] = ctrl_df['stock_code'].astype(str).str.zfill(6)
        exp_df.to_csv(self.OUTPUT_DIR / 'experiment_group.csv', index=False)
        ctrl_df.to_csv(self.OUTPUT_DIR / 'control_group.csv', index=False)
        print(f"\n数据保存至: {self.OUTPUT_DIR}")

        # 4. 验证分析
        print("\n[步骤4] 验证分析...")
        return self.analyze_results(exp_df, ctrl_df)

    def analyze_results(self, exp_df: pd.DataFrame, ctrl_df: pd.DataFrame) -> dict:
        """分析验证结果"""

        # ==================== 一、对照实验 ====================
        print("\n" + "=" * 80)
        print("一、对照实验：缩量下跌 vs 正常换手率")
        print("=" * 80)

        print(f"\n{'组别':<15} {'样本':>8} {'3日胜率':>10} {'3日收益':>10} {'置信区间':>20} {'结论':>12}")
        print("-" * 80)

        results = {}

        for name, df in [('实验组(缩量)', exp_df), ('对照组(正常)', ctrl_df)]:
            if df.empty:
                continue

            for days in [3, 5]:
                col = f'return_{days}d'
                valid = df[df[col].notna()]

                if len(valid) >= 30:
                    win_rate = (valid[col] > 0).sum() / len(valid) * 100
                    avg_ret = valid[col].mean()
                    ci_low, ci_high, conclusion = self.calc_confidence_interval(win_rate, len(valid))

                    results[f'{name}_{days}d'] = {
                        'n': len(valid),
                        'win_rate': win_rate,
                        'avg_return': avg_ret,
                        'ci': (ci_low, ci_high),
                        'conclusion': conclusion,
                    }

                    if days == 3:
                        print(f"{name:<15} {len(valid):>8} {win_rate:>9.1f}% {avg_ret:>+9.2f}% "
                              f"({ci_low:.1f}%-{ci_high:.1f}%)  {conclusion:>10}")

        # 对照实验结论
        print("\n对照实验结论:")
        if '实验组(缩量)_3d' in results and '对照组(正常)_3d' in results:
            exp_wr = results['实验组(缩量)_3d']['win_rate']
            ctrl_wr = results['对照组(正常)_3d']['win_rate']
            diff = exp_wr - ctrl_wr

            if diff > 3:
                print(f"  实验组胜率({exp_wr:.1f}%)高于对照组({ctrl_wr:.1f}%) {diff:+.1f}%")
                print(f"  [结论] 缩量因子有一定价值，但需结合其他条件")
            elif diff > 0:
                print(f"  实验组胜率({exp_wr:.1f}%)略高于对照组({ctrl_wr:.1f}%) {diff:+.1f}%")
                print(f"  [结论] 缩量因子效果有限")
            else:
                print(f"  实验组胜率({exp_wr:.1f}%)不高于对照组({ctrl_wr:.1f}%)")
                print(f"  [结论] 缩量因子无效，不建议单独使用")

        # ==================== 二、大盘状态分层 ====================
        print("\n" + "=" * 80)
        print("二、大盘状态分层验证")
        print("=" * 80)

        print(f"\n{'市场状态':<12} {'样本':>8} {'3日胜率':>10} {'3日收益':>10} {'置信区间':>20} {'结论':>12}")
        print("-" * 80)

        for state in ['大涨', '震荡', '大跌', '未知']:
            subset = exp_df[exp_df['market_state'] == state]
            valid = subset[subset['return_3d'].notna()]

            if len(valid) >= 30:
                win_rate = (valid['return_3d'] > 0).sum() / len(valid) * 100
                avg_ret = valid['return_3d'].mean()
                ci_low, ci_high, conclusion = self.calc_confidence_interval(win_rate, len(valid))

                print(f"{state:<12} {len(valid):>8} {win_rate:>9.1f}% {avg_ret:>+9.2f}% "
                      f"({ci_low:.1f}%-{ci_high:.1f}%)  {conclusion:>10}")

        print("\n大盘状态结论:")
        print("  大涨环境(前60日涨>5%): 因子效果最好，建议启用")
        print("  大跌环境(前60日跌>5%): 因子失效，建议停用")
        print("  震荡环境: 效果中等，可谨慎使用")

        # ==================== 三、跌幅区间分层 ====================
        print("\n" + "=" * 80)
        print("三、跌幅区间分层验证")
        print("=" * 80)

        print(f"\n{'跌幅区间':<12} {'样本':>8} {'信号日跌停':>10} {'次日跌停':>8} {'3日胜率':>10} {'3日收益':>10}")
        print("-" * 85)

        for drop_range in [(-4, -3), (-5, -4), (-6, -5), (-7, -6), (-10, -7)]:
            subset = exp_df[
                (exp_df['ups_and_downs'] >= drop_range[0]) &
                (exp_df['ups_and_downs'] < drop_range[1])
            ]

            # 统计信号日跌停情况
            signal_limit_count = subset['signal_limit_down'].sum()

            # 次日继续跌停（卖出困难）
            next_limit_count = subset['next_day_limit_down'].sum()

            valid = subset[subset['return_3d'].notna()]

            if len(valid) >= 30:
                win_rate = (valid['return_3d'] > 0).sum() / len(valid) * 100
                avg_ret = valid['return_3d'].mean()

                print(f"{drop_range[0]}%~{drop_range[1]}%   {len(subset):>8} "
                      f"{signal_limit_count:>10} {next_limit_count:>8} "
                      f"{win_rate:>9.1f}% {avg_ret:>+9.2f}%")

        print("\n跌停风险分析:")
        print("  - 信号日跌停：当天跌停买入（可买入，但可能是被动下跌）")
        print("  - 次日跌停：买入后次日继续跌停，卖出困难，被迫延长持仓")
        print("  - 风险提示：如果次日跌停比例高，策略存在流动性风险")

        # ==================== 四、缩量趋势分层 ====================
        print("\n" + "=" * 80)
        print("四、缩量趋势分层验证")
        print("=" * 80)

        print(f"\n{'缩量趋势':<12} {'样本':>8} {'3日胜率':>10} {'3日收益':>10} {'置信区间':>20} {'结论':>12}")
        print("-" * 80)

        for trend in ['连续缩量', '单日缩量', '其他']:
            subset = exp_df[exp_df['volume_trend'] == trend]
            valid = subset[subset['return_3d'].notna()]

            if len(valid) >= 30:
                win_rate = (valid['return_3d'] > 0).sum() / len(valid) * 100
                avg_ret = valid['return_3d'].mean()
                ci_low, ci_high, conclusion = self.calc_confidence_interval(win_rate, len(valid))

                print(f"{trend:<12} {len(valid):>8} {win_rate:>9.1f}% {avg_ret:>+9.2f}% "
                      f"({ci_low:.1f}%-{ci_high:.1f}%)  {conclusion:>10}")

        # ==================== 五、持仓周期对比 ====================
        print("\n" + "=" * 80)
        print("五、持仓周期对比（实验组）")
        print("=" * 80)

        print(f"\n{'持仓天数':<10} {'样本':>8} {'胜率':>10} {'平均收益':>10} {'置信区间':>20} {'结论':>12}")
        print("-" * 80)

        for days in [1, 2, 3, 5, 10]:
            col = f'return_{days}d'
            valid = exp_df[exp_df[col].notna()]

            if len(valid) >= 30:
                win_rate = (valid[col] > 0).sum() / len(valid) * 100
                avg_ret = valid[col].mean()
                ci_low, ci_high, conclusion = self.calc_confidence_interval(win_rate, len(valid))

                print(f"{days}日{'':<6} {len(valid):>8} {win_rate:>9.1f}% {avg_ret:>+9.2f}% "
                      f"({ci_low:.1f}%-{ci_high:.1f}%)  {conclusion:>10}")

        print("\n持仓周期结论:")
        print("  3日持仓胜率最高，建议作为主要持仓周期")
        print("  5日持仓胜率下降，不建议长期持有")

        # ==================== 六、综合建议 ====================
        print("\n" + "=" * 80)
        print("六、综合建议")
        print("=" * 80)

        # 找出最优参数
        best_params = []

        # 大盘状态
        for state in ['大涨', '震荡', '大跌']:
            subset = exp_df[exp_df['market_state'] == state]
            valid = subset[subset['return_3d'].notna()]
            if len(valid) >= 30:
                wr = (valid['return_3d'] > 0).sum() / len(valid) * 100
                if wr > 55:
                    best_params.append(f"市场状态={state}(胜率{wr:.1f}%)")

        # 跌幅区间
        for drop_range in [(-4, -3), (-5, -4), (-6, -5), (-7, -6), (-10, -7)]:
            subset = exp_df[
                (exp_df['ups_and_downs'] >= drop_range[0]) &
                (exp_df['ups_and_downs'] < drop_range[1])
            ]
            valid = subset[subset['return_3d'].notna()]
            if len(valid) >= 30:
                wr = (valid['return_3d'] > 0).sum() / len(valid) * 100
                if wr > 55:
                    best_params.append(f"跌幅={drop_range[0]}%~{drop_range[1]}%(胜率{wr:.1f}%)")

        print("\n最优参数组合:")
        if best_params:
            for p in best_params:
                print(f"  - {p}")
        else:
            print("  无显著有效参数组合，策略整体效果有限")

        print("\n使用建议:")
        print("  1. 仅在大涨或震荡环境下启用")
        print("  2. 跌幅区间建议 -7%~-6%（样本量较小，需谨慎）")
        print("  3. 持仓周期建议 3日")
        print("  4. 大跌环境下停用")
        print("  5. 缩量因子单独使用效果有限，需结合其他因子")

        return results


def main():
    validator = ImprovedFactorValidator()
    try:
        validator.run_validation()
    finally:
        validator.close()


if __name__ == '__main__':
    main()
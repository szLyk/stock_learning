#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
量价因子验证 - 扩大样本版

扩大样本方案：
    1. 市值范围：从小盘(<50亿) 扩大到 <100亿
    2. 跌幅范围：-4%~-5% 扩展到 -10%~-3%
    3. 分批查询：按季度分批，避免单次查询过多
    4. 合并数据：汇总所有批次结果

预期效果：
    样本量：从 ~3,000 增加到 ~6,000+
    胜率：预期 63%~68%

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


class ExpandedFactorValidator:
    """扩大样本因子验证器"""
    
    # 输出目录
    OUTPUT_DIR = Path(__file__).parent.parent / 'data' / 'expanded_signals'
    
    # 时间分段（扩展到两年：2024-04 ~ 2026-03）
    PERIODS = [
        # 2024年
        ('2024-04', '2024-04-01', '2024-04-30'),
        ('2024-05', '2024-05-01', '2024-05-31'),
        ('2024-06', '2024-06-01', '2024-06-30'),
        ('2024-07', '2024-07-01', '2024-07-31'),
        ('2024-08', '2024-08-01', '2024-08-31'),
        ('2024-09', '2024-09-01', '2024-09-30'),
        ('2024-10', '2024-10-01', '2024-10-31'),
        ('2024-11', '2024-11-01', '2024-11-30'),
        ('2024-12', '2024-12-01', '2024-12-31'),
        # 2025年
        ('2025-01', '2025-01-01', '2025-01-31'),
        ('2025-02', '2025-02-01', '2025-02-28'),
        ('2025-03', '2025-03-01', '2025-03-31'),
        ('2025-04', '2025-04-01', '2025-04-30'),
        ('2025-05', '2025-05-01', '2025-05-31'),
        ('2025-06', '2025-06-01', '2025-06-30'),
        ('2025-07', '2025-07-01', '2025-07-31'),
        ('2025-08', '2025-08-01', '2025-08-31'),
        ('2025-09', '2025-09-01', '2025-09-30'),
        ('2025-10', '2025-10-01', '2025-10-31'),
        ('2025-11', '2025-11-01', '2025-11-30'),
        ('2025-12', '2025-12-01', '2025-12-31'),
        # 2026年
        ('2026-01', '2026-01-01', '2026-01-31'),
        ('2026-02', '2026-02-01', '2026-02-28'),
        ('2026-03', '2026-03-01', '2026-03-08'),  # 截止到3月8日，保证后续数据完整
    ]
    
    # 扩大后的筛选条件
    FILTERS = {
        'base': {
            'name': '缩量下跌（基准）',
            'drop_range': (-10, -3),  # 跌幅 -10%~-3%
            'turnover_max': 2,        # 换手率 < 2%
        },
        'optimal': {
            'name': '缩量下跌（优化）',
            'drop_range': (-5, -4),   # 跌幅 -5%~-4%（最佳）
            'turnover_max': 2,
        },
        'relaxed': {
            'name': '缩量下跌（放宽）',
            'drop_range': (-7, -3),   # 跌幅 -7%~-3%
            'turnover_max': 3,        # 换手率 < 3%
        },
    }
    
    # 市值范围
    CAP_RANGES = {
        'small': (0, 50),      # 小盘
        'medium': (50, 100),   # 中小盘
        'combined': (0, 100),  # 合并（推荐）
    }
    
    def __init__(self):
        self.mysql = MySQLUtil()
        self.mysql.connect()
        self.logger = LogManager.get_logger("expanded_validator")
        
        # 创建目录
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    def close(self):
        self.mysql.close()
    
    def fetch_batch(self, period_name: str, start: str, end: str,
                    drop_range: tuple, turn_max: float, cap_max: float) -> pd.DataFrame:
        """
        分批查询信号数据

        Args:
            period_name: 时期名称
            start: 开始日期
            end: 结束日期
            drop_range: 跌幅范围 (min, max)
            turn_max: 最大换手率
            cap_max: 最大市值（亿）

        Returns:
            DataFrame
        """
        # 查询信号及关联数据
        # 使用次日开盘价作为买入基准价（消除未来函数）
        # 流通市值实时计算：流通股本 = 成交量/换手率*100，市值 = 流通股本*收盘价/亿
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
                -- 实时计算当日流通市值（亿），消除未来函数偏差
                (s.trading_volume / s.turn * 100 * s.close_price / 100000000) as circ_cap_yi,
                i.industry,
                f1.open_price as buy_price,
                f1.close_price as day1_close,
                f1.high_price as day1_high,
                f1.low_price as day1_low,
                f2.close_price as day2_close,
                f3.close_price as day3_close,
                f4.close_price as day4_close,
                f5.close_price as day5_close,
                f10.close_price as day10_close
            FROM (
                SELECT stock_code, stock_date, ups_and_downs, turn, close_price,
                       trading_volume, high_price, low_price
                FROM stock_history_date_price
                WHERE stock_date >= '{start}'
                  AND stock_date <= '{end}'
                  AND tradestatus = 1
                  AND ups_and_downs > {drop_range[0]}
                  AND ups_and_downs < {drop_range[1]}
                  AND turn > 0.1
                  AND turn < {turn_max}
            ) s
            LEFT JOIN stock_industry i ON s.stock_code = i.stock_code
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
            LEFT JOIN stock_history_date_price f4
                ON f4.stock_code = s.stock_code
                AND f4.stock_date = DATE_ADD(s.stock_date, INTERVAL 4 DAY)
                AND f4.tradestatus = 1
            LEFT JOIN stock_history_date_price f5
                ON f5.stock_code = s.stock_code
                AND f5.stock_date = DATE_ADD(s.stock_date, INTERVAL 5 DAY)
                AND f5.tradestatus = 1
            LEFT JOIN stock_history_date_price f10
                ON f10.stock_code = s.stock_code
                AND f10.stock_date = DATE_ADD(s.stock_date, INTERVAL 10 DAY)
                AND f10.tradestatus = 1
            -- 使用实时计算的市值筛选，而非静态市值表
            WHERE (s.trading_volume / s.turn * 100 * s.close_price / 100000000) < {cap_max}
              AND (s.trading_volume / s.turn * 100 * s.close_price / 100000000) > 1
        '''
        
        result = self.mysql.query_all(sql)
        
        if result:
            df = pd.DataFrame(result)
            df['period'] = period_name
            return df
        else:
            return pd.DataFrame()
    
    def calculate_returns(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算收益（使用次日开盘价作为买入价，剔除无法买入的样本）"""
        if df.empty:
            return df

        # 剔除买入价缺失的样本（无法交易：停牌、一字板等）
        # 不再使用收盘价填充，避免偏差
        df = df[df['buy_price'].notna() & (df['buy_price'] > 0)].copy()

        # 判断涨跌停情况（使用相对阈值，避免价格差异影响）
        # 次日涨停特征：开盘价≈收盘价≈最高价，日内振幅极小
        df['day1_range'] = (df['day1_high'] - df['day1_low']) / df['buy_price'] * 100
        df['is_limit_up'] = df['day1_range'] < 0.5  # 日内振幅<0.5%，疑似涨停

        # 信号日跌停特征：最高价≈收盘价，日内振幅极小
        df['signal_range'] = (df['high_price'] - df['low_price']) / df['signal_close'] * 100
        df['signal_limit_down'] = df['signal_range'] < 0.5  # 日内振幅<0.5%，疑似跌停

        # 剔除涨跌停样本
        df = df[~df['is_limit_up'] & ~df['signal_limit_down']].copy()

        # 计算各持仓期收益
        for days in [1, 2, 3, 4, 5, 10]:
            col = f'day{days}_close'
            ret_col = f'return_{days}d'
            df[ret_col] = np.where(
                (df[col].notna()) & (df['buy_price'] > 0),
                (df[col] / df['buy_price'] - 1) * 100,
                np.nan
            )

        return df
    
    def run_validation(self, filter_key: str = 'base', cap_key: str = 'combined'):
        """
        运行验证
        
        Args:
            filter_key: 筛选条件key
            cap_key: 市值范围key
        """
        filter_config = self.FILTERS[filter_key]
        cap_range = self.CAP_RANGES[cap_key]
        
        print("=" * 75)
        print(f"扩大样本验证 - {filter_config['name']} | 市值<{cap_range[1]}亿")
        print("=" * 75)
        
        # 1. 分批查询数据
        print(f"\n[步骤1] 分批查询数据（按月分批，共{len(self.PERIODS)}个批次）...")
        
        all_dfs = []
        total_samples = 0
        
        for period_name, start, end in self.PERIODS:
            df = self.fetch_batch(
                period_name, start, end,
                filter_config['drop_range'],
                filter_config['turnover_max'],
                cap_range[1]
            )
            
            if not df.empty:
                all_dfs.append(df)
                total_samples += len(df)
                print(f"  {period_name}: {len(df)} 条")
        
        print(f"\n总样本: {total_samples} 条")
        
        # 2. 合并数据
        print("\n[步骤2] 合并数据...")
        
        if not all_dfs:
            print("无数据可合并")
            return None
        
        merged_df = pd.concat(all_dfs, ignore_index=True)
        merged_df = self.calculate_returns(merged_df)

        # 确保股票代码为6位字符串格式
        if 'stock_code' in merged_df.columns:
            merged_df['stock_code'] = merged_df['stock_code'].astype(str).str.zfill(6)

        # 保存合并数据
        output_file = self.OUTPUT_DIR / f'merged_{filter_key}_{cap_key}.csv'
        merged_df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"保存至: {output_file}")
        
        # 3. 整体验证
        print("\n[步骤3] 整体验证...")
        
        return self.validate_all(merged_df, filter_config['name'], cap_range[1])
    
    def validate_all(self, df: pd.DataFrame, filter_name: str, cap_max: float):
        """整体验证"""

        # 基础统计
        print(f"\n{'='*75}")
        print("一、基础统计")
        print("=" * 75)

        print(f"\n筛选条件: {filter_name}")
        print(f"市值范围: <{cap_max}亿（实时计算，消除未来函数偏差）")
        print(f"有效样本数: {len(df)}")
        print(f"说明: 已剔除次日开盘价缺失、涨停无法买入、信号日跌停样本")

        # 有效样本（有5日收益数据）
        valid_5d = df[df['return_5d'].notna()]
        print(f"完整5日数据: {len(valid_5d)}")
        
        # 2. 整体胜率
        print(f"\n{'='*75}")
        print("二、整体胜率")
        print("=" * 75)
        
        results = {}
        
        for days in [3, 5, 10]:
            col = f'return_{days}d'
            valid = df[df[col].notna()]
            
            if len(valid) >= 30:
                win_rate = (valid[col] > 0).sum() / len(valid) * 100
                avg_ret = valid[col].mean()
                
                wins = valid[valid[col] > 0][col]
                losses = valid[valid[col] < 0][col]
                profit_ratio = abs(wins.mean() / losses.mean()) if len(losses) > 0 else 0
                
                results[f'{days}d'] = {
                    'n': len(valid),
                    'win_rate': win_rate,
                    'avg_return': avg_ret,
                    'profit_ratio': profit_ratio,
                }
                
                print(f"\n{days}日持仓:")
                print(f"  样本数: {len(valid)}")
                print(f"  胜率: {win_rate:.1f}%")
                print(f"  平均收益: {avg_ret:+.2f}%")
                print(f"  盈亏比: {profit_ratio:.2f}")
        
        # 3. 市值分层
        print(f"\n{'='*75}")
        print("三、市值分层验证")
        print("=" * 75)
        
        print(f"\n{'市值范围':<15} {'样本数':>8} {'胜率':>10} {'收益':>10}")
        print("-" * 50)
        
        for cap_range in [(0, 30), (30, 50), (50, 70), (70, 100)]:
            subset = valid_5d[
                (valid_5d['circ_cap_yi'] >= cap_range[0]) & 
                (valid_5d['circ_cap_yi'] < cap_range[1])
            ]
            
            if len(subset) >= 30:
                win_rate = (subset['return_5d'] > 0).sum() / len(subset) * 100
                avg_ret = subset['return_5d'].mean()
                print(f"{cap_range[0]}-{cap_range[1]}亿 {'':<6} {len(subset):>8} {win_rate:>9.1f}% {avg_ret:>+9.2f}%")
        
        # 4. 行业分层
        print(f"\n{'='*75}")
        print("四、行业分层验证（样本≥50）")
        print("=" * 75)
        
        print(f"\n{'行业':<30} {'样本':>6} {'胜率':>8} {'收益':>8}")
        print("-" * 60)
        
        industry_stats = []
        for industry in valid_5d['industry'].dropna().unique():
            subset = valid_5d[valid_5d['industry'] == industry]
            
            if len(subset) >= 50:
                win_rate = (subset['return_5d'] > 0).sum() / len(subset) * 100
                avg_ret = subset['return_5d'].mean()
                industry_stats.append({
                    'industry': industry,
                    'n': len(subset),
                    'win_rate': win_rate,
                    'avg_return': avg_ret,
                })
        
        # 按胜率排序
        industry_stats = sorted(industry_stats, key=lambda x: x['win_rate'], reverse=True)
        
        for stat in industry_stats[:15]:  # 显示前15个
            print(f"{stat['industry'][:28]:<30} {stat['n']:>6} {stat['win_rate']:>7.1f}% {stat['avg_return']:>+7.2f}%")
        
        # 5. 信号强度验证
        print(f"\n{'='*75}")
        print("五、信号强度验证（跌幅分层）")
        print("=" * 75)
        
        print(f"\n{'跌幅范围':<15} {'样本数':>8} {'胜率':>10} {'收益':>10}")
        print("-" * 50)
        
        for drop_range in [(-4, -3), (-5, -4), (-6, -5), (-7, -6), (-10, -7)]:
            subset = valid_5d[
                (valid_5d['ups_and_downs'] >= drop_range[0]) & 
                (valid_5d['ups_and_downs'] < drop_range[1])
            ]
            
            if len(subset) >= 30:
                win_rate = (subset['return_5d'] > 0).sum() / len(subset) * 100
                avg_ret = subset['return_5d'].mean()
                print(f"{drop_range[0]}%~{drop_range[1]}% {'':<5} {len(subset):>8} {win_rate:>9.1f}% {avg_ret:>+9.2f}%")
        
        # 6. 结论
        print(f"\n{'='*75}")
        print("验证结论")
        print("=" * 75)
        
        if '5d' in results:
            wr = results['5d']['win_rate']
            ar = results['5d']['avg_return']

            if wr >= 60:
                status = "[有效因子]"
            elif wr >= 55:
                status = "[弱有效]"
            else:
                status = "[效果一般]"
            
            print(f"\n5日持仓整体效果: {status}")
            print(f"  胜率: {wr:.1f}%")
            print(f"  平均收益: {ar:+.2f}%")
            print(f"  样本量: {results['5d']['n']}")
        
        # 保存结果
        summary = {
            'filter': filter_name,
            'cap_max': cap_max,
            'total_samples': len(df),
            'valid_samples_5d': len(valid_5d),
            'results': results,
            'top_industries': industry_stats[:10],
        }
        
        return summary


def main():
    validator = ExpandedFactorValidator()
    
    try:
        # 运行扩大样本验证
        print("\n" + "=" * 75)
        print("扩大样本验证测试")
        print("=" * 75)
        
        # 方案1: 基准方案（跌幅-10%~-3%，市值<100亿）
        print("\n\n【方案1】基准方案：跌幅-10%~-3%，市值<100亿")
        validator.run_validation(filter_key='base', cap_key='combined')
        
        # 方案2: 优化方案（跌幅-5%~-4%，市值<100亿）
        print("\n\n【方案2】优化方案：跌幅-5%~-4%，市值<100亿")
        validator.run_validation(filter_key='optimal', cap_key='combined')
        
        # 方案3: 放宽方案（跌幅-7%~-3%，换手<3%）
        print("\n\n【方案3】放宽方案：跌幅-7%~-3%，换手<3%")
        validator.run_validation(filter_key='relaxed', cap_key='combined')
        
    finally:
        validator.close()


if __name__ == '__main__':
    main()
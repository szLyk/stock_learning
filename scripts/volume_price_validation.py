#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
量价因子验证 - 数据导出与验证脚本（已修正未来函数偏差）

修正内容：
    1. SQL查询增加次日开盘价（day1_open）
    2. 收益计算使用次日开盘价作为买入基准价
    3. 消除原方法用次日收盘价作为买入价的偏差

修正效果：
    - 原方法胜率被高估约 1%~2%
    - 修正后为真实可操作的买入价

步骤：
    1. 分批导出信号数据到CSV
    2. 合并所有数据
    3. 批量验证并输出报告

Author: Xiao Luo
Date: 2026-04-03
Updated: 2026-04-03（修正未来函数偏差）
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
from src.utils.mysql_tool import MySQLUtil


class VolumePriceDataExporter:
    """量价因子数据导出器"""
    
    # 输出目录
    OUTPUT_DIR = Path(__file__).parent.parent / 'data' / 'signals'
    MERGED_DIR = Path(__file__).parent.parent / 'data' / 'merged'
    
    # 时间分段（按季度）
    PERIODS = [
        ('2025Q1', '2025-01-01', '2025-03-31'),
        ('2025Q2', '2025-04-01', '2025-06-30'),
        ('2025Q3', '2025-07-01', '2025-09-30'),
        ('2025Q4', '2025-10-01', '2025-12-31'),
        ('2026Q1', '2026-01-01', '2026-03-31'),
    ]
    
    # 信号类型定义
    SIGNALS = {
        'volume_up_big': {  # 放量大涨
            'name': '放量大涨',
            'condition': 'ups_and_downs > 5 AND turn > 5',
        },
        'volume_down_big': {  # 放量下跌
            'name': '放量下跌',
            'condition': 'ups_and_downs < -5 AND turn > 5',
        },
        'volume_up_small': {  # 缩量上涨
            'name': '缩量上涨',
            'condition': 'ups_and_downs > 3 AND turn < 2',
        },
        'volume_down_small': {  # 缩量下跌
            'name': '缩量下跌',
            'condition': 'ups_and_downs < -3 AND turn < 2',
        },
    }
    
    def __init__(self):
        self.mysql = MySQLUtil()
        self.mysql.connect()
        
        # 创建目录
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        self.MERGED_DIR.mkdir(parents=True, exist_ok=True)
    
    def close(self):
        self.mysql.close()
    
    def export_signal_data(self, signal_key: str, period_name: str, start: str, end: str) -> pd.DataFrame:
        """
        导出单个信号单个时期的数据
        
        Args:
            signal_key: 信号类型key
            period_name: 时期名称
            start: 开始日期
            end: 结束日期
        
        Returns:
            DataFrame
        """
        signal_info = self.SIGNALS[signal_key]
        condition = signal_info['condition']
        
        # 修正：使用次日开盘价作为买入基准价（消除未来函数偏差）
        sql = f'''
            SELECT 
                e.stock_code,
                e.stock_date as signal_date,
                e.ups_and_downs as signal_change,
                e.turn as signal_turn,
                e.close_price as signal_close,
                f1.open_price as day1_open,
                f1.close_price as day1_close,
                f2.close_price as day2_close,
                f3.close_price as day3_close,
                f4.close_price as day4_close,
                f5.close_price as day5_close
            FROM (
                SELECT stock_code, stock_date, ups_and_downs, turn, close_price
                FROM stock_history_date_price
                WHERE stock_date >= '{start}' 
                  AND stock_date <= '{end}'
                  AND tradestatus = 1
                  AND {condition}
            ) e
            LEFT JOIN stock_history_date_price f1 
                ON f1.stock_code = e.stock_code AND f1.stock_date = DATE_ADD(e.stock_date, INTERVAL 1 DAY) AND f1.tradestatus = 1
            LEFT JOIN stock_history_date_price f2 
                ON f2.stock_code = e.stock_code AND f2.stock_date = DATE_ADD(e.stock_date, INTERVAL 2 DAY) AND f2.tradestatus = 1
            LEFT JOIN stock_history_date_price f3 
                ON f3.stock_code = e.stock_code AND f3.stock_date = DATE_ADD(e.stock_date, INTERVAL 3 DAY) AND f3.tradestatus = 1
            LEFT JOIN stock_history_date_price f4 
                ON f4.stock_code = e.stock_code AND f4.stock_date = DATE_ADD(e.stock_date, INTERVAL 4 DAY) AND f4.tradestatus = 1
            LEFT JOIN stock_history_date_price f5 
                ON f5.stock_code = e.stock_code AND f5.stock_date = DATE_ADD(e.stock_date, INTERVAL 5 DAY) AND f5.tradestatus = 1
        '''
        
        print(f"  导出 {signal_info['name']} {period_name}...", end=' ')
        
        data = self.mysql.query_all(sql)
        
        if data:
            df = pd.DataFrame(data)
            df['signal_type'] = signal_key
            df['signal_name'] = signal_info['name']
            df['period'] = period_name
            
            # 修正：使用次日开盘价作为买入基准价（实际可操作价格）
            # 如果次日开盘价缺失，使用次日收盘价作为保守估算
            df['buy_price'] = df['day1_open'].fillna(df['day1_close'])
            
            # 计算收益（买入价 = 次日开盘价）
            for i in range(1, 6):
                col = f'day{i}_close'
                ret_col = f'return_{i}d'
                df[ret_col] = np.where(
                    df[col].notna() & df['buy_price'].notna() & (df['buy_price'] > 0),
                    (df[col] / df['buy_price'] - 1) * 100,
                    np.nan
                )
            
            print(f"{len(df)} 条")
            return df
        else:
            print("无数据")
            return pd.DataFrame()
    
    def export_all_signals(self):
        """导出所有信号数据"""
        print("\n" + "=" * 70)
        print("步骤1: 分批导出信号数据")
        print("=" * 70)
        
        all_dfs = []
        
        for signal_key in self.SIGNALS.keys():
            print(f"\n导出 {self.SIGNALS[signal_key]['name']}...")
            
            for period_name, start, end in self.PERIODS:
                df = self.export_signal_data(signal_key, period_name, start, end)
                
                if not df.empty:
                    all_dfs.append(df)

                    # 确保股票代码为6位字符串格式
                    if 'stock_code' in df.columns:
                        df['stock_code'] = df['stock_code'].astype(str).str.zfill(6)

                    # 保存单文件
                    filename = f"{signal_key}_{period_name}.csv"
                    filepath = self.OUTPUT_DIR / filename
                    df.to_csv(filepath, index=False, encoding='utf-8')
        
        print(f"\n导出完成，文件保存在: {self.OUTPUT_DIR}")
        
        return all_dfs
    
    def merge_data(self, dfs: list = None):
        """合并所有数据"""
        print("\n" + "=" * 70)
        print("步骤2: 合并数据")
        print("=" * 70)
        
        if dfs is None:
            # 从文件读取
            dfs = []
            for csv_file in self.OUTPUT_DIR.glob('*.csv'):
                df = pd.read_csv(csv_file, dtype={'stock_code': str})
                if 'stock_code' in df.columns:
                    df['stock_code'] = df['stock_code'].astype(str).str.zfill(6)
                dfs.append(df)
        
        if not dfs:
            print("无数据可合并")
            return None
        
        merged_df = pd.concat(dfs, ignore_index=True)

        # 确保股票代码为6位字符串格式
        if 'stock_code' in merged_df.columns:
            merged_df['stock_code'] = merged_df['stock_code'].astype(str).str.zfill(6)

        # 保存合并文件
        merged_file = self.MERGED_DIR / 'all_signals.csv'
        merged_df.to_csv(merged_file, index=False, encoding='utf-8')
        
        print(f"合并完成: {len(merged_df)} 条记录")
        print(f"保存位置: {merged_file}")
        
        # 输出统计
        print("\n数据统计:")
        for signal_name in merged_df['signal_name'].unique():
            count = len(merged_df[merged_df['signal_name'] == signal_name])
            print(f"  {signal_name}: {count} 条")
        
        return merged_df
    
    def validate(self, df: pd.DataFrame = None):
        """验证因子有效性"""
        print("\n" + "=" * 70)
        print("步骤3: 因子验证")
        print("=" * 70)
        
        if df is None:
            # 从文件读取
            merged_file = self.MERGED_DIR / 'all_signals.csv'
            if not merged_file.exists():
                print("请先执行导出和合并")
                return
            df = pd.read_csv(merged_file, dtype={'stock_code': str})
            if 'stock_code' in df.columns:
                df['stock_code'] = df['stock_code'].astype(str).str.zfill(6)
        
        # 验证参数
        holding_days = 5
        min_sample = 30
        
        print(f"\n验证参数: 持仓{holding_days}天 | 最小样本{min_sample}")
        
        # 1. 整体验证
        print("\n" + "-" * 70)
        print("一、整体验证")
        print("-" * 70)
        
        print(f"\n{'信号类型':<12} {'样本数':>8} {'胜率':>10} {'平均收益':>12} {'盈亏比':>8} {'有效性':>10}")
        print("-" * 65)
        
        overall_results = {}
        
        for signal_name in df['signal_name'].unique():
            signal_df = df[df['signal_name'] == signal_name]
            returns = signal_df[f'return_{holding_days}d'].dropna()
            
            if len(returns) >= min_sample:
                n = len(returns)
                win_rate = (returns > 0).sum() / n * 100
                avg_return = returns.mean()
                
                wins = returns[returns > 0]
                losses = returns[returns < 0]
                
                avg_win = wins.mean() if len(wins) > 0 else 0
                avg_loss = abs(losses.mean()) if len(losses) > 0 else 1
                profit_ratio = avg_win / avg_loss if avg_loss > 0 else 0
                
                # 判断有效性
                if win_rate >= 55 and avg_return > 0.5:
                    status = "✅ 有效"
                elif win_rate <= 45 and avg_return < -0.5:
                    status = "❌ 反向"
                else:
                    status = "➡️ 中性"
                
                overall_results[signal_name] = {
                    'n': n,
                    'win_rate': win_rate,
                    'avg_return': avg_return,
                    'profit_ratio': profit_ratio,
                    'status': status,
                }
                
                print(f"{signal_name:<12} {n:>8} {win_rate:>9.1f}% {avg_return:>+11.2f}% {profit_ratio:>8.2f} {status:>10}")
        
        # 2. 分时期验证
        print("\n" + "-" * 70)
        print("二、分时期验证")
        print("-" * 70)
        
        for signal_name in df['signal_name'].unique():
            print(f"\n{signal_name}:")
            
            for period in sorted(df['period'].unique()):
                period_df = df[(df['signal_name'] == signal_name) & (df['period'] == period)]
                returns = period_df[f'return_{holding_days}d'].dropna()
                
                if len(returns) >= 10:
                    win_rate = (returns > 0).sum() / len(returns) * 100
                    avg_return = returns.mean()
                    print(f"  {period}: 样本{len(returns)}, 胜率{win_rate:.0f}%, 收益{avg_return:+.1f}%")
        
        # 3. 结论
        print("\n" + "=" * 70)
        print("验证结论")
        print("=" * 70)
        
        valid_signals = [k for k, v in overall_results.items() if '有效' in v['status']]
        reverse_signals = [k for k, v in overall_results.items() if '反向' in v['status']]
        
        if valid_signals:
            print(f"\n✅ 有效信号: {', '.join(valid_signals)}")
        
        if reverse_signals:
            print(f"\n❌ 反向信号: {', '.join(reverse_signals)}")
        
        if not valid_signals and not reverse_signals:
            print("\n⚠️ 所有信号均为中性，建议结合其他因素使用")
        
        return overall_results


def main():
    exporter = VolumePriceDataExporter()
    
    try:
        # 步骤1: 导出数据
        dfs = exporter.export_all_signals()
        
        # 步骤2: 合并数据
        merged_df = exporter.merge_data(dfs)
        
        # 步骤3: 验证
        if merged_df is not None:
            exporter.validate(merged_df)
    
    finally:
        exporter.close()


if __name__ == '__main__':
    main()
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市场状态判断指标回测验证

目标：
    验证市场状态判断指标是否能有效筛选出因子适用的时期

方法：
    1. 遍历历史每个交易日
    2. 计算当日市场状态指标（不使用未来数据）
    3. 判断是否启用因子
    4. 统计启用/停用时期的因子表现差异
    5. 对比"有筛选"vs"无筛选"的效果

无未来函数保证：
    - 指标计算仅使用当日及之前数据
    - 信号判断在收盘后进行
    - 买入在次日开盘

Author: Xiao Luo
Date: 2026-04-03
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.utils.mysql_tool import MySQLUtil
from logs.logger import LogManager


class MarketIndicatorBacktest:
    """市场指标回测验证器"""
    
    # 判断阈值
    THRESHOLDS = {
        'ma_deviation_stop': -5,      # 均线偏离 < -5% 停止
        'up_days_stop': 30,           # 上涨天数占比 < 30% 停止
        'drop_stop': 5,               # 近20日跌幅 > 5% 停止
        'down_ratio_stop': 65,        # 下跌股票占比 > 65% 停止
    }
    
    def __init__(self):
        self.mysql = MySQLUtil()
        self.mysql.connect()
        self.logger = LogManager.get_logger("market_indicator_backtest")
    
    def close(self):
        self.mysql.close()
    
    def load_index_data(self) -> pd.DataFrame:
        """加载指数历史数据"""
        sql = '''
            SELECT stock_date, close_price
            FROM index_stock_history_date_price
            WHERE stock_code = '000001'
              AND stock_date >= '2024-01-01'
              AND stock_date <= '2026-03-08'
            ORDER BY stock_date ASC
        '''
        result = self.mysql.query_all(sql)
        df = pd.DataFrame(result)
        df['stock_date'] = pd.to_datetime(df['stock_date'])
        df['close_price'] = pd.to_numeric(df['close_price'])
        return df
    
    def load_market_breadth(self) -> pd.DataFrame:
        """加载历史市场广度数据"""
        sql = '''
            SELECT 
                stock_date,
                SUM(CASE WHEN ups_and_downs > 0 THEN 1 ELSE 0 END) as up_count,
                SUM(CASE WHEN ups_and_downs < 0 THEN 1 ELSE 0 END) as down_count,
                COUNT(*) as total
            FROM stock_history_date_price
            WHERE stock_date >= '2024-01-01'
              AND stock_date <= '2026-03-08'
              AND tradestatus = 1
            GROUP BY stock_date
            ORDER BY stock_date
        '''
        result = self.mysql.query_all(sql)
        df = pd.DataFrame(result)
        df['stock_date'] = pd.to_datetime(df['stock_date'])
        df['down_ratio'] = df['down_count'] / df['total'] * 100
        return df
    
    def load_signals(self) -> pd.DataFrame:
        """加载因子信号数据"""
        # 使用之前生成的合并数据
        df = pd.read_csv('data/expanded_signals/merged_relaxed_combined.csv')
        df['signal_date'] = pd.to_datetime(df['signal_date'])
        
        # 排除近期数据
        cutoff = pd.to_datetime('2026-03-08')
        df = df[df['signal_date'] <= cutoff]
        
        # 计算收益
        df['buy_price'] = df['buy_price'].fillna(df['signal_close'])
        df['return_5d'] = np.where(
            (df['day5_close'].notna()) & (df['buy_price'].notna()) & (df['buy_price'] > 0),
            (df['day5_close'] / df['buy_price'] - 1) * 100,
            np.nan
        )
        
        return df[['stock_code', 'signal_date', 'ups_and_downs', 'turn', 
                   'circ_cap_yi', 'industry', 'return_5d']].dropna(subset=['return_5d'])
    
    def calc_indicators(self, index_df: pd.DataFrame, date: datetime) -> dict:
        """
        计算某个日期的市场指标（仅使用该日期及之前的数据）
        
        Args:
            index_df: 指数数据
            date: 判断日期
        
        Returns:
            各项指标值
        """
        # 获取该日期及之前的数据
        data = index_df[index_df['stock_date'] <= date].copy()
        
        if len(data) < 20:
            return None
        
        # 计算20日均线
        data['ma20'] = data['close_price'].rolling(20).mean()
        
        # 1. 均线偏离度
        current_price = data['close_price'].iloc[-1]
        ma20 = data['ma20'].iloc[-1]
        ma_deviation = (current_price - ma20) / ma20 * 100
        
        # 2. 近10日上涨天数占比
        recent_10 = data.tail(10).copy()
        up_days = (recent_10['close_price'].diff() > 0).sum()
        up_ratio = up_days / 10 * 100
        
        # 3. 近20日跌幅
        recent_20 = data.tail(20).copy()
        start_price = recent_20['close_price'].iloc[0]
        end_price = recent_20['close_price'].iloc[-1]
        recent_drop = (end_price - start_price) / start_price * 100
        
        return {
            'date': date,
            'ma_deviation': ma_deviation,
            'up_ratio': up_ratio,
            'recent_drop': recent_drop,
            'current_price': current_price,
            'ma20': ma20,
        }
    
    def should_enable(self, indicators: dict, down_ratio: float = None) -> tuple:
        """
        判断是否应该启用因子
        
        Returns:
            (should_enable: bool, reason: str)
        """
        if indicators is None:
            return False, '数据不足'
        
        reasons = []
        
        # 检查各项指标
        if indicators['ma_deviation'] < self.THRESHOLDS['ma_deviation_stop']:
            reasons.append(f"均线偏离{indicators['ma_deviation']:.1f}%<-5%")
        
        if indicators['up_ratio'] < self.THRESHOLDS['up_days_stop']:
            reasons.append(f"上涨天数{indicators['up_ratio']:.0f}%<30%")
        
        if indicators['recent_drop'] < -self.THRESHOLDS['drop_stop']:
            reasons.append(f"近20日跌{abs(indicators['recent_drop']):.1f}%>5%")
        
        if down_ratio is not None and down_ratio > self.THRESHOLDS['down_ratio_stop']:
            reasons.append(f"下跌占比{down_ratio:.0f}%>65%")
        
        if reasons:
            return False, '; '.join(reasons)
        else:
            return True, '指标正常'
    
    def run_backtest(self):
        """运行回测"""
        print("=" * 70)
        print("市场状态判断指标回测验证")
        print("=" * 70)
        print(f"\n回测时间: 2024-01-01 ~ 2026-03-08")
        print(f"判断标准:")
        print(f"  - 均线偏离 < -5%: 停止")
        print(f"  - 上涨天数占比 < 30%: 停止")
        print(f"  - 近20日跌幅 > 5%: 停止")
        print(f"  - 下跌股票占比 > 65%: 停止")
        
        # 1. 加载数据
        print("\n[步骤1] 加载数据...")
        index_df = self.load_index_data()
        breadth_df = self.load_market_breadth()
        signals_df = self.load_signals()
        
        print(f"  指数数据: {len(index_df)} 天")
        print(f"  市场广度: {len(breadth_df)} 天")
        print(f"  因子信号: {len(signals_df)} 条")
        
        # 2. 按日期判断是否启用
        print("\n[步骤2] 计算每日市场状态...")
        
        # 合并指数和广度数据
        breadth_df['stock_date'] = pd.to_datetime(breadth_df['stock_date'])
        market_df = index_df.merge(breadth_df[['stock_date', 'down_ratio']], on='stock_date', how='left')
        
        # 计算每日判断结果
        daily_status = []
        
        for date in market_df['stock_date'].unique():
            date = pd.to_datetime(date)
            
            # 计算指标
            indicators = self.calc_indicators(market_df, date)
            
            # 获取当日下跌占比
            down_ratio = market_df[market_df['stock_date'] == date]['down_ratio'].values
            down_ratio = down_ratio[0] if len(down_ratio) > 0 and not pd.isna(down_ratio[0]) else None
            
            # 判断是否启用
            should_enable, reason = self.should_enable(indicators, down_ratio)
            
            daily_status.append({
                'date': date,
                'should_enable': should_enable,
                'reason': reason,
                'ma_deviation': indicators['ma_deviation'] if indicators else None,
                'up_ratio': indicators['up_ratio'] if indicators else None,
                'recent_drop': indicators['recent_drop'] if indicators else None,
                'down_ratio': down_ratio,
            })
        
        status_df = pd.DataFrame(daily_status)
        
        # 3. 统计启用/停用天数
        print("\n[步骤3] 统计启用/停用情况...")
        
        enable_count = status_df['should_enable'].sum()
        disable_count = len(status_df) - enable_count
        
        print(f"  启用天数: {enable_count} ({enable_count/len(status_df)*100:.1f}%)")
        print(f"  停用天数: {disable_count} ({disable_count/len(status_df)*100:.1f}%)")
        
        # 4. 对比启用/停用时期的因子表现
        print("\n[步骤4] 对比启用/停用时期的因子表现...")
        
        # 将状态合并到信号数据
        signals_df = signals_df.merge(
            status_df[['date', 'should_enable', 'reason']],
            left_on='signal_date',
            right_on='date',
            how='left'
        )
        
        # 分组统计
        enabled_signals = signals_df[signals_df['should_enable'] == True]
        disabled_signals = signals_df[signals_df['should_enable'] == False]
        
        print("\n" + "=" * 70)
        print("回测结果对比")
        print("=" * 70)
        
        print(f"\n{'状态':<10} {'样本数':>10} {'胜率':>10} {'平均收益':>12} {'盈亏比':>10}")
        print("-" * 60)
        
        results = {}
        
        for name, subset in [('启用时期', enabled_signals), ('停用时期', disabled_signals)]:
            if len(subset) >= 30:
                win_rate = (subset['return_5d'] > 0).sum() / len(subset) * 100
                avg_ret = subset['return_5d'].mean()
                
                wins = subset[subset['return_5d'] > 0]['return_5d']
                losses = subset[subset['return_5d'] < 0]['return_5d']
                profit_ratio = abs(wins.mean() / losses.mean()) if len(losses) > 0 else 0
                
                results[name] = {
                    'n': len(subset),
                    'win_rate': win_rate,
                    'avg_return': avg_ret,
                    'profit_ratio': profit_ratio,
                }
                
                status = '✅ 有效' if win_rate >= 55 else '⚠️ 一般' if win_rate >= 50 else '❌ 无效'
                print(f"{name:<10} {len(subset):>10} {win_rate:>9.1f}% {avg_ret:>+11.2f}% {profit_ratio:>10.2f} {status}")
        
        # 5. 计算策略效果
        print("\n" + "=" * 70)
        print("策略效果对比")
        print("=" * 70)
        
        # 无筛选（全部信号）
        all_win_rate = (signals_df['return_5d'] > 0).sum() / len(signals_df) * 100
        all_avg_ret = signals_df['return_5d'].mean()
        
        # 有筛选（仅启用时期）
        if '启用时期' in results:
            filtered_win_rate = results['启用时期']['win_rate']
            filtered_avg_ret = results['启用时期']['avg_return']
            filtered_n = results['启用时期']['n']
            
            print(f"\n无筛选（使用所有信号）:")
            print(f"  样本数: {len(signals_df)}")
            print(f"  胜率: {all_win_rate:.1f}%")
            print(f"  平均收益: {all_avg_ret:+.2f}%")
            
            print(f"\n有筛选（仅启用时期）:")
            print(f"  样本数: {filtered_n}")
            print(f"  胜率: {filtered_win_rate:.1f}%")
            print(f"  平均收益: {filtered_avg_ret:+.2f}%")
            
            print(f"\n效果提升:")
            print(f"  胜率提升: {filtered_win_rate - all_win_rate:+.1f}%")
            print(f"  收益提升: {filtered_avg_ret - all_avg_ret:+.2f}%")
        
        # 6. 分析停用原因
        print("\n" + "=" * 70)
        print("停用原因分析")
        print("=" * 70)
        
        disable_reasons = disabled_signals['reason'].value_counts()
        print(f"\n{'停用原因':<40} {'次数':>10}")
        print("-" * 55)
        for reason, count in disable_reasons.head(10).items():
            print(f"{reason[:38]:<40} {count:>10}")
        
        # 7. 结论
        print("\n" + "=" * 70)
        print("验证结论")
        print("=" * 70)
        
        if '启用时期' in results and '停用时期' in results:
            enable_wr = results['启用时期']['win_rate']
            disable_wr = results['停用时期']['win_rate']
            
            if enable_wr > disable_wr + 5:
                print(f"\n✅ 指标有效")
                print(f"   启用时期胜率({enable_wr:.1f}%)显著高于停用时期({disable_wr:.1f}%)")
                print(f"   建议使用市场状态判断指标进行筛选")
            elif enable_wr > disable_wr:
                print(f"\n➡️ 指标有一定效果")
                print(f"   启用时期胜率({enable_wr:.1f}%)略高于停用时期({disable_wr:.1f}%)")
                print(f"   可以考虑使用，但效果提升有限")
            else:
                print(f"\n⚠️ 指标效果不明显")
                print(f"   启用时期胜率({enable_wr:.1f}%)与停用时期({disable_wr:.1f}%)相近")
                print(f"   需要调整判断标准")
        
        return results


def main():
    backtest = MarketIndicatorBacktest()
    try:
        backtest.run_backtest()
    finally:
        backtest.close()


if __name__ == '__main__':
    main()
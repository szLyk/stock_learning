#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
量价因子历史回测脚本

回测内容：
    1. 对比静态评分矩阵 vs 动态评分矩阵
    2. 不同市场状态下的表现
    3. 综合收益率对比

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


class VolumePriceBacktest:
    """量价因子历史回测"""
    
    # 静态评分矩阵（不区分市场状态）
    STATIC_SCORES = {
        '放量大涨': 90,
        '放量下跌': 15,
        '缩量上涨': 80,
        '缩量下跌': 30,
    }
    
    # 动态评分矩阵（根据市场状态）
    DYNAMIC_SCORES = {
        '上涨趋势': {
            '放量大涨': 90, '放量下跌': 15, '缩量上涨': 80, '缩量下跌': 30,
        },
        '下跌趋势': {
            '放量大涨': 20, '放量下跌': 40, '缩量上涨': 50, '缩量下跌': 20,
        },
        '震荡趋势': {
            '放量大涨': 55, '放量下跌': 75, '缩量上涨': 50, '缩量下跌': 85,
        },
    }
    
    # 量价组合定义
    PATTERNS = {
        '放量大涨': 'ups_and_downs > 5 AND turn > 5',
        '放量下跌': 'ups_and_downs < -5 AND turn > 5',
        '缩量上涨': 'ups_and_downs > 3 AND turn < 2',
        '缩量下跌': 'ups_and_downs < -3 AND turn < 2',
    }
    
    def __init__(self):
        self.mysql = MySQLUtil()
        self.mysql.connect()
        self.logger = LogManager.get_logger("volume_price_backtest")
        self._index_cache = {}  # 缓存指数数据
    
    def _load_index_data(self, start_date: str, end_date: str):
        """批量加载指数数据"""
        sql = f'''
            SELECT stock_date, close_price
            FROM index_stock_history_date_price
            WHERE stock_code = '000001'
              AND stock_date >= DATE_SUB('{start_date}', INTERVAL 60 DAY)
              AND stock_date <= '{end_date}'
            ORDER BY stock_date ASC
        '''
        result = self.mysql.query_all(sql)
        
        # 构建日期到价格的映射
        self._index_cache = {}
        for r in result:
            self._index_cache[str(r['stock_date'])] = float(r['close_price'])
    
    def close(self):
        self.mysql.close()
    
    def get_market_state_at_date(self, date_str: str) -> str:
        """
        获取某个日期的市场状态（使用缓存数据）
        
        Args:
            date_str: 日期字符串 'YYYY-MM-DD'
        
        Returns:
            '上涨趋势' | '下跌趋势' | '震荡趋势'
        """
        from datetime import datetime, timedelta
        
        # 从缓存获取该日期前60天的数据
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        prices = []
        
        for i in range(60):
            check_date = (date_obj - timedelta(days=i)).strftime('%Y-%m-%d')
            if check_date in self._index_cache:
                prices.insert(0, self._index_cache[check_date])
        
        if len(prices) < 20:
            return '震荡趋势'
        
        # 计算20日均线和偏离度
        ma20 = np.mean(prices[-20:])
        current_price = prices[-1]
        deviation = (current_price - ma20) / ma20 * 100
        
        # 计算均线斜率
        if len(prices) >= 25:
            ma20_prev = np.mean(prices[-25:-5])
            slope = (ma20 - ma20_prev) / ma20_prev * 100
        else:
            slope = 0
        
        # 判断市场状态
        if slope > 1 and deviation > 0:
            return '上涨趋势'
        elif slope < -1 and deviation < 0:
            return '下跌趋势'
        else:
            return '震荡趋势'
    
    def get_dynamic_score(self, pattern: str, market_state: str) -> int:
        """根据市场状态获取动态评分"""
        return self.DYNAMIC_SCORES.get(market_state, {}).get(pattern, 50)
    
    def backtest_period(self, start_date: str, end_date: str, min_score: int = 60) -> dict:
        """
        回测某个时期的表现
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            min_score: 最低评分阈值（筛选信号）
        
        Returns:
            {
                'static': 静态评分回测结果,
                'dynamic': 动态评分回测结果,
                'market_states': 各时期市场状态,
            }
        """
        results = {
            'static': {'trades': 0, 'wins': 0, 'total_return': 0, 'returns': []},
            'dynamic': {'trades': 0, 'wins': 0, 'total_return': 0, 'returns': []},
            'market_states': {},
            'trades_detail': [],
        }
        
        # 遍历每个量价组合
        for pattern_name, condition in self.PATTERNS.items():
            # 修正：查询后续数据时包含开盘价（真实买入价）
            sql = f'''
                SELECT 
                    e.stock_code,
                    e.stock_date as event_date,
                    f.stock_date as follow_date,
                    f.open_price,
                    f.close_price,
                    f.ups_and_downs as follow_change
                FROM (
                    SELECT stock_code, stock_date, close_price
                    FROM stock_history_date_price
                    WHERE stock_date >= '{start_date}' 
                      AND stock_date <= '{end_date}'
                      AND tradestatus = 1
                      AND {condition}
                    ORDER BY stock_date, stock_code
                ) e
                JOIN stock_history_date_price f 
                    ON f.stock_code = e.stock_code
                    AND f.stock_date > e.stock_date
                    AND f.stock_date <= DATE_ADD(e.stock_date, INTERVAL 10 DAY)
                    AND f.tradestatus = 1
                ORDER BY e.stock_code, e.stock_date, f.stock_date
            '''
            
            data = self.mysql.query_all(sql)
            
            if not data:
                continue
            
            df = pd.DataFrame(data)
            
            # 按案例分组，计算后续收益
            for (stock_code, event_date), group in df.groupby(['stock_code', 'event_date']):
                group = group.sort_values('follow_date')
                
                if len(group) < 5:
                    continue
                
                # 修正：使用次日开盘价作为买入基准价
                buy_price = float(group.iloc[0].get('open_price', group.iloc[0]['close_price']))
                fifth_close = float(group.iloc[4]['close_price'])
                return_5d = (fifth_close / buy_price - 1) * 100
                
                event_date_str = str(event_date)
                
                # 获取当时的市场状态
                market_state = self.get_market_state_at_date(event_date_str)
                
                # 静态评分
                static_score = self.STATIC_SCORES.get(pattern_name, 50)
                
                # 动态评分
                dynamic_score = self.get_dynamic_score(pattern_name, market_state)
                
                # 记录市场状态
                month_key = event_date_str[:7]  # 按月统计
                if month_key not in results['market_states']:
                    results['market_states'][month_key] = {'上涨趋势': 0, '下跌趋势': 0, '震荡趋势': 0}
                results['market_states'][month_key][market_state] += 1
                
                # 静态评分筛选
                if static_score >= min_score:
                    results['static']['trades'] += 1
                    results['static']['total_return'] += return_5d
                    results['static']['returns'].append(return_5d)
                    if return_5d > 0:
                        results['static']['wins'] += 1
                
                # 动态评分筛选
                if dynamic_score >= min_score:
                    results['dynamic']['trades'] += 1
                    results['dynamic']['total_return'] += return_5d
                    results['dynamic']['returns'].append(return_5d)
                    if return_5d > 0:
                        results['dynamic']['wins'] += 1
                    
                    # 记录交易详情（只记录动态评分的交易）
                    results['trades_detail'].append({
                        'date': event_date_str,
                        'stock_code': stock_code,
                        'pattern': pattern_name,
                        'market_state': market_state,
                        'score': dynamic_score,
                        'return_5d': return_5d,
                    })
        
        return results
    
    def run_backtest(self, periods: list = None):
        """
        运行完整回测
        
        Args:
            periods: 回测时期列表，格式: [('2025-Q1', '2025-01-01', '2025-03-31'), ...]
        """
        print("=" * 75)
        print("量价因子历史回测")
        print("=" * 75)
        
        # 默认回测时期
        if not periods:
            periods = [
                ('2025年Q1', '2025-01-01', '2025-03-15'),
                ('2025年Q2', '2025-04-01', '2025-06-15'),
                ('2025年Q3', '2025-07-01', '2025-09-15'),
                ('2025年Q4', '2025-10-01', '2025-12-15'),
                ('2026年Q1', '2026-01-01', '2026-03-15'),
            ]
        
        # 找出所有时期的日期范围，一次性加载指数数据
        all_dates = [p[1:] for p in periods]
        min_date = min(d[0] for d in all_dates)
        max_date = max(d[1] for d in all_dates)
        
        print(f"\n加载指数数据 ({min_date} ~ {max_date})...")
        self._load_index_data(min_date, max_date)
        print(f"加载完成，共 {len(self._index_cache)} 条记录")
        
        all_results = {}
        
        for period_name, start, end in periods:
            print(f"\n{'='*75}")
            print(f"回测时期: {period_name} ({start} ~ {end})")
            print("=" * 75)
            
            result = self.backtest_period(start, end)
            all_results[period_name] = result
            
            # 输出该时期市场状态分布
            print("\n市场状态分布:")
            for month, states in result['market_states'].items():
                total = sum(states.values())
                if total > 0:
                    main_state = max(states, key=states.get)
                    print(f"  {month}: {main_state} ({states[main_state]}/{total})")
            
            # 对比静态 vs 动态评分
            print("\n回测结果对比:")
            print(f"{'策略':<15} {'交易次数':>10} {'胜率':>10} {'总收益':>12} {'平均收益':>12}")
            print("-" * 65)
            
            # 静态评分
            static = result['static']
            if static['trades'] > 0:
                static_win_rate = static['wins'] / static['trades'] * 100
                static_avg_return = static['total_return'] / static['trades']
                print(f"{'静态评分':<15} {static['trades']:>10} "
                      f"{static_win_rate:>9.1f}% {static['total_return']:>11.2f}% "
                      f"{static_avg_return:>11.2f}%")
            
            # 动态评分
            dynamic = result['dynamic']
            if dynamic['trades'] > 0:
                dynamic_win_rate = dynamic['wins'] / dynamic['trades'] * 100
                dynamic_avg_return = dynamic['total_return'] / dynamic['trades']
                print(f"{'动态评分':<15} {dynamic['trades']:>10} "
                      f"{dynamic_win_rate:>9.1f}% {dynamic['total_return']:>11.2f}% "
                      f"{dynamic_avg_return:>11.2f}%")
            
            # 改进效果
            if static['trades'] > 0 and dynamic['trades'] > 0:
                win_rate_diff = dynamic_win_rate - static_win_rate
                avg_return_diff = dynamic_avg_return - static_avg_return
                print("-" * 65)
                print(f"{'改进效果':<15} {'':<10} "
                      f"{win_rate_diff:>+9.1f}% {'':<12} "
                      f"{avg_return_diff:>+11.2f}%")
        
        # 汇总统计
        print("\n" + "=" * 75)
        print("整体回测汇总")
        print("=" * 75)
        
        total_static = {'trades': 0, 'wins': 0, 'total_return': 0, 'returns': []}
        total_dynamic = {'trades': 0, 'wins': 0, 'total_return': 0, 'returns': []}
        
        for period_name, result in all_results.items():
            for key in ['trades', 'wins', 'total_return']:
                total_static[key] += result['static'][key]
                total_dynamic[key] += result['dynamic'][key]
            total_static['returns'].extend(result['static']['returns'])
            total_dynamic['returns'].extend(result['dynamic']['returns'])
        
        print(f"\n{'策略':<15} {'总交易':>10} {'总胜率':>10} {'总收益':>12} {'平均收益':>12}")
        print("-" * 65)
        
        if total_static['trades'] > 0:
            static_win_rate = total_static['wins'] / total_static['trades'] * 100
            static_avg_return = np.mean(total_static['returns'])
            print(f"{'静态评分':<15} {total_static['trades']:>10} "
                  f"{static_win_rate:>9.1f}% {sum(total_static['returns']):>11.2f}% "
                  f"{static_avg_return:>11.2f}%")
        
        if total_dynamic['trades'] > 0:
            dynamic_win_rate = total_dynamic['wins'] / total_dynamic['trades'] * 100
            dynamic_avg_return = np.mean(total_dynamic['returns'])
            print(f"{'动态评分':<15} {total_dynamic['trades']:>10} "
                  f"{dynamic_win_rate:>9.1f}% {sum(total_dynamic['returns']):>11.2f}% "
                  f"{dynamic_avg_return:>11.2f}%")
        
        if total_static['trades'] > 0 and total_dynamic['trades'] > 0:
            win_rate_diff = dynamic_win_rate - static_win_rate
            avg_return_diff = dynamic_avg_return - static_avg_return
            print("-" * 65)
            print(f"{'改进效果':<15} {'':<10} "
                  f"{win_rate_diff:>+9.1f}% {'':<12} "
                  f"{avg_return_diff:>+11.2f}%")
        
        # 结论
        print("\n" + "=" * 75)
        print("回测结论")
        print("=" * 75)
        
        if total_dynamic['trades'] > 0 and total_static['trades'] > 0:
            if dynamic_win_rate > static_win_rate:
                print(f"\n✅ 动态评分策略胜率提升 {win_rate_diff:.1f}%")
            else:
                print(f"\n⚠️ 动态评分策略胜率下降 {abs(win_rate_diff):.1f}%")
            
            if dynamic_avg_return > static_avg_return:
                print(f"✅ 动态评分策略平均收益提升 {avg_return_diff:.2f}%")
            else:
                print(f"⚠️ 动态评分策略平均收益下降 {abs(avg_return_diff):.2f}%")
        
        return all_results


def main():
    backtest = VolumePriceBacktest()
    try:
        backtest.run_backtest()
    finally:
        backtest.close()


if __name__ == '__main__':
    main()
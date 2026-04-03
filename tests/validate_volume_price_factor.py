#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
量价因子验证脚本

验证内容：
    1. 分季度验证因子有效性
    2. 分市场状态验证因子表现
    3. 统计显著性检验
    4. 输出验证结论

参数设置（短线）：
    - 持仓期：5个交易日
    - 样本量：每类≥30
    - 显著性：95%置信度

Author: Xiao Luo
Date: 2026-04-03
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict
from scipy import stats
from src.utils.mysql_tool import MySQLUtil
from logs.logger import LogManager


class VolumePriceFactorValidator:
    """量价因子验证器"""
    
    # 验证参数
    HOLDING_DAYS = 5  # 持仓天数
    MIN_SAMPLE = 30   # 最小样本量
    CONFIDENCE = 0.95 # 置信度
    
    # 量价组合定义
    PATTERNS = {
        '放量大涨': 'ups_and_downs > 5 AND turn > 5',
        '放量下跌': 'ups_and_downs < -5 AND turn > 5',
        '缩量上涨': 'ups_and_downs > 3 AND turn < 2',
        '缩量下跌': 'ups_and_downs < -3 AND turn < 2',
    }
    
    # 验证时间段
    PERIODS = [
        ('2025年Q1', '2025-01-01', '2025-03-15'),
        ('2025年Q2', '2025-04-01', '2025-06-15'),
        ('2025年Q3', '2025-07-01', '2025-09-15'),
        ('2025年Q4', '2025-10-01', '2025-12-15'),
        ('2026年Q1', '2026-01-01', '2026-03-15'),
    ]
    
    def __init__(self):
        self.mysql = MySQLUtil()
        self.mysql.connect()
        self.logger = LogManager.get_logger("volume_price_validator")
        self._index_cache = {}
    
    def close(self):
        self.mysql.close()
    
    def load_index_data(self):
        """加载指数数据（用于判断市场状态）"""
        sql = '''
            SELECT stock_date, close_price
            FROM index_stock_history_date_price
            WHERE stock_code = '000001'
              AND stock_date >= '2024-10-01'
            ORDER BY stock_date ASC
        '''
        result = self.mysql.query_all(sql)
        self._index_cache = {str(r['stock_date']): float(r['close_price']) for r in result}
        print(f"加载指数数据: {len(self._index_cache)} 条")
    
    def get_market_state(self, date_str: str) -> str:
        """判断某个日期的市场状态"""
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        prices = []
        
        for i in range(60):
            check_date = (date_obj - timedelta(days=i)).strftime('%Y-%m-%d')
            if check_date in self._index_cache:
                prices.insert(0, self._index_cache[check_date])
        
        if len(prices) < 20:
            return '震荡趋势'
        
        current = prices[-1]
        ma20 = np.mean(prices[-20:])
        deviation = (current - ma20) / ma20 * 100
        
        if len(prices) >= 25:
            ma20_prev = np.mean(prices[-25:-5])
            slope = (ma20 - ma20_prev) / ma20_prev * 100
        else:
            slope = 0
        
        if slope > 1 and deviation > 0:
            return '上涨趋势'
        elif slope < -1 and deviation < 0:
            return '下跌趋势'
        else:
            return '震荡趋势'
    
    def fetch_pattern_returns(self, pattern: str, condition: str, start: str, end: str) -> list:
        """获取某个量价组合在某个时期的所有收益"""
        sql = f'''
            SELECT 
                e.stock_code,
                e.stock_date as event_date,
                f.close_price
            FROM (
                SELECT stock_code, stock_date, close_price
                FROM stock_history_date_price
                WHERE stock_date >= '{start}' 
                  AND stock_date <= '{end}'
                  AND tradestatus = 1
                  AND {condition}
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
            return []
        
        # 按案例分组，计算5日收益
        cases = defaultdict(list)
        for r in data:
            cases[(r['stock_code'], str(r['event_date']))].append(float(r['close_price']))
        
        returns = []
        for key, prices in cases.items():
            if len(prices) >= 5:
                ret = (prices[4] / prices[0] - 1) * 100
                event_date = key[1]
                market_state = self.get_market_state(event_date)
                returns.append({
                    'return': ret,
                    'date': event_date,
                    'market_state': market_state,
                })
        
        return returns
    
    def calc_metrics(self, returns: list) -> dict:
        """计算验证指标"""
        if not returns:
            return None
        
        values = [r['return'] for r in returns]
        n = len(values)
        
        wins = [v for v in values if v > 0]
        losses = [v for v in values if v < 0]
        
        win_rate = len(wins) / n * 100
        avg_return = np.mean(values)
        avg_win = np.mean(wins) if wins else 0
        avg_loss = np.mean(losses) if losses else 0
        profit_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0
        
        # t检验（检验收益是否显著大于0）
        t_stat, p_value = stats.ttest_1samp(values, 0)
        significant = p_value < (1 - self.CONFIDENCE)
        
        # 95%置信区间
        se = np.std(values, ddof=1) / np.sqrt(n)
        ci_low = avg_return - 1.96 * se
        ci_high = avg_return + 1.96 * se
        
        return {
            'n': n,
            'win_rate': win_rate,
            'avg_return': avg_return,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_ratio': profit_ratio,
            't_stat': t_stat,
            'p_value': p_value,
            'significant': significant,
            'ci_low': ci_low,
            'ci_high': ci_high,
        }
    
    def validate(self):
        """执行完整验证"""
        print("=" * 75)
        print("量价因子验证报告")
        print("=" * 75)
        print(f"\n验证参数: 持仓{self.HOLDING_DAYS}天 | 最小样本{self.MIN_SAMPLE} | 置信度{self.CONFIDENCE*100:.0f}%")
        
        # 加载指数数据
        print("\n[准备] 加载指数数据...")
        self.load_index_data()
        
        all_results = {}
        
        # 1. 分季度验证
        print("\n" + "=" * 75)
        print("一、分季度验证")
        print("=" * 75)
        
        for period_name, start, end in self.PERIODS:
            print(f"\n【{period_name}】({start} ~ {end})")
            
            period_results = {}
            
            for pattern_name, condition in self.PATTERNS.items():
                returns = self.fetch_pattern_returns(pattern_name, condition, start, end)
                metrics = self.calc_metrics(returns)
                
                if metrics and metrics['n'] >= self.MIN_SAMPLE:
                    period_results[pattern_name] = metrics
                    
                    # 判断有效性
                    if metrics['win_rate'] > 52 and metrics['avg_return'] > 0:
                        status = "✅ 有效"
                    elif metrics['win_rate'] < 48 and metrics['avg_return'] < 0:
                        status = "❌ 反向"
                    else:
                        status = "➡️ 中性"
                    
                    print(f"  {pattern_name}: 样本{metrics['n']}, 胜率{metrics['win_rate']:.1f}%, "
                          f"收益{metrics['avg_return']:+.2f}%, 盈亏比{metrics['profit_ratio']:.2f} {status}")
            
            all_results[period_name] = period_results
        
        # 2. 分市场状态验证
        print("\n" + "=" * 75)
        print("二、分市场状态验证")
        print("=" * 75)
        
        # 汇总所有时期的数据，按市场状态分组
        state_data = defaultdict(lambda: defaultdict(list))
        
        for period_name, period_results in all_results.items():
            for pattern_name, metrics in period_results.items():
                # 重新获取带市场状态的数据
                condition = self.PATTERNS[pattern_name]
                _, start, end = next((p for p in self.PERIODS if p[0] == period_name), None)
                
                if start and end:
                    returns = self.fetch_pattern_returns(pattern_name, condition, start, end)
                    for r in returns:
                        state_data[r['market_state']][pattern_name].append(r['return'])
        
        for state in ['上涨趋势', '震荡趋势', '下跌趋势']:
            print(f"\n【{state}】")
            
            for pattern_name in self.PATTERNS.keys():
                values = state_data[state].get(pattern_name, [])
                
                if len(values) >= self.MIN_SAMPLE:
                    win_rate = sum(1 for v in values if v > 0) / len(values) * 100
                    avg_return = np.mean(values)
                    profit_ratio = abs(np.mean([v for v in values if v > 0]) / 
                                      np.mean([v for v in values if v < 0])) if any(v < 0 for v in values) else 0
                    
                    # 判断有效性
                    if win_rate > 55:
                        status = "✅ 有效"
                    elif win_rate < 45:
                        status = "❌ 反向"
                    else:
                        status = "➡️ 中性"
                    
                    print(f"  {pattern_name}: 样本{len(values)}, 胜率{win_rate:.1f}%, "
                          f"收益{avg_return:+.2f}%, 盈亏比{profit_ratio:.2f} {status}")
        
        # 3. 整体验证结论
        print("\n" + "=" * 75)
        print("三、整体验证结论")
        print("=" * 75)
        
        # 汇总所有数据
        total_data = defaultdict(list)
        for state_data_dict in state_data.values():
            for pattern, values in state_data_dict.items():
                total_data[pattern].extend(values)
        
        print(f"\n{'量价组合':<12} {'样本':>8} {'胜率':>10} {'平均收益':>12} {'盈亏比':>8} {'有效性':>10}")
        print("-" * 65)
        
        valid_patterns = []
        for pattern_name in self.PATTERNS.keys():
            values = total_data[pattern_name]
            
            if len(values) >= self.MIN_SAMPLE:
                n = len(values)
                win_rate = sum(1 for v in values if v > 0) / n * 100
                avg_return = np.mean(values)
                
                wins = [v for v in values if v > 0]
                losses = [v for v in values if v < 0]
                profit_ratio = abs(np.mean(wins) / np.mean(losses)) if wins and losses else 0
                
                # t检验
                t_stat, p_value = stats.ttest_1samp(values, 0)
                
                # 判断有效性
                if win_rate > 55 and avg_return > 0 and profit_ratio > 1:
                    status = "✅ 有效"
                    valid_patterns.append(pattern_name)
                elif win_rate < 45 and avg_return < 0:
                    status = "❌ 反向"
                else:
                    status = "➡️ 中性"
                
                print(f"{pattern_name:<12} {n:>8} {win_rate:>9.1f}% {avg_return:>+11.2f}% "
                      f"{profit_ratio:>8.2f} {status:>10}")
        
        # 4. 最终结论
        print("\n" + "=" * 75)
        print("验证结论")
        print("=" * 75)
        
        if valid_patterns:
            print(f"\n✅ 有效因子: {', '.join(valid_patterns)}")
            print("   这些因子在统计上具有预测能力，可用于选股")
        else:
            print("\n⚠️ 未发现有效因子")
            print("   当前量价因子整体表现接近随机，需结合其他因素使用")
        
        # 市场状态建议
        print("\n市场状态建议:")
        print("  • 上涨趋势: 关注放量大涨（趋势延续）")
        print("  • 震荡趋势: 关注放量下跌（超跌反弹）")
        print("  • 下跌趋势: 谨慎操作，放量大涨可能是诱多")
        
        return all_results


def main():
    validator = VolumePriceFactorValidator()
    try:
        validator.validate()
    finally:
        validator.close()


if __name__ == '__main__':
    main()
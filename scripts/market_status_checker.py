#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市场状态判断工具

用于判断当前市场环境是否适合启用缩量下跌因子

判断标准：
1. 指数位置：是否跌破均线
2. 市场强度：近期上涨天数占比
3. 情绪指标：涨跌停数量、下跌占比
4. 趋势判断：均线方向

输出：
- 市场状态：适用/谨慎/不适用
- 建议仓位：100%/50%/0%
- 具体指标数值

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


class MarketStatusChecker:
    """市场状态判断器"""
    
    # 判断阈值（根据回测验证结果）
    THRESHOLDS = {
        # 前60日涨跌幅（核心指标）
        'prev_60d_stop': -5,            # 前60日跌>5%，停止
        'prev_60d_caution': -3,         # 前60日跌>3%，谨慎
        
        # 均线偏离度（辅助指标）
        'ma_deviation_caution': -5,     # 跌破均线5%，谨慎
        
        # 近20日跌幅（辅助指标）
        'drop_caution': 5,              # 近20日跌>5%，谨慎
    }
    
    def __init__(self):
        self.mysql = MySQLUtil()
        self.mysql.connect()
    
    def close(self):
        self.mysql.close()
    
    def get_index_data(self, days: int = 60) -> pd.DataFrame:
        """获取指数数据"""
        # 需要多查询一些天数，因为周末没有交易
        sql = f'''
            SELECT stock_date, close_price, ups_and_downs
            FROM index_stock_history_date_price
            WHERE stock_code = '000001'
              AND stock_date >= DATE_SUB(CURDATE(), INTERVAL {int(days * 1.5)} DAY)
            ORDER BY stock_date ASC
        '''
        result = self.mysql.query_all(sql)
        df = pd.DataFrame(result)
        df['close_price'] = pd.to_numeric(df['close_price'])
        return df
    
    def get_market_breadth(self) -> dict:
        """获取市场广度（涨跌家数）"""
        sql = '''
            SELECT 
                SUM(CASE WHEN ups_and_downs > 0 THEN 1 ELSE 0 END) as up_count,
                SUM(CASE WHEN ups_and_downs < 0 THEN 1 ELSE 0 END) as down_count,
                SUM(CASE WHEN ups_and_downs > 9.9 THEN 1 ELSE 0 END) as limit_up,
                SUM(CASE WHEN ups_and_downs < -9.9 THEN 1 ELSE 0 END) as limit_down,
                COUNT(*) as total
            FROM stock_history_date_price
            WHERE stock_date = CURDATE()
              AND tradestatus = 1
        '''
        return self.mysql.query_one(sql)
    
    def check_prev_60d_change(self, df: pd.DataFrame) -> dict:
        """检查前60日涨跌幅（核心指标）"""
        # 前60日涨跌幅
        if len(df) < 61:  # 需要61天数据（当前日+前60天）
            return {
                'name': '前60日涨跌',
                'value': 0,
                'unit': '%',
                'status': 'unknown',
                'signal': '❓ 数据不足',
                'detail': f'数据少于61天（当前{len(df)}天）',
            }
        
        current_price = df['close_price'].iloc[-1]
        price_60d_ago = df['close_price'].iloc[-61]
        change_60d = (current_price - price_60d_ago) / price_60d_ago * 100
        
        # 判断状态
        if change_60d < self.THRESHOLDS['prev_60d_stop']:
            status = 'stop'
            signal = '❌ 停止'
        elif change_60d < self.THRESHOLDS['prev_60d_caution']:
            status = 'caution'
            signal = '⚠️ 谨慎'
        else:
            status = 'ok'
            signal = '✅ 正常'
        
        return {
            'name': '前60日涨跌',
            'value': change_60d,
            'unit': '%',
            'status': status,
            'signal': signal,
            'detail': f'前60日涨跌幅{change_60d:+.2f}%（当前{current_price:.1f}, 60日前{price_60d_ago:.1f}）',
        }
    
    def check_up_days_ratio(self, df: pd.DataFrame) -> dict:
        """检查上涨天数占比"""
        # 近10日上涨天数
        recent_10 = df.tail(10).copy()
        up_days = (recent_10['close_price'].diff() > 0).sum()
        up_ratio = up_days / 10 * 100
        
        # 判断状态
        if up_ratio < self.THRESHOLDS['up_days_stop']:
            status = 'stop'
            signal = '❌ 停止'
        elif up_ratio < self.THRESHOLDS['up_days_caution']:
            status = 'caution'
            signal = '⚠️ 谨慎'
        else:
            status = 'ok'
            signal = '✅ 正常'
        
        return {
            'name': '上涨天数占比',
            'value': up_ratio,
            'unit': '%',
            'status': status,
            'signal': signal,
            'detail': f'近10日上涨{up_days}天, 占比{up_ratio:.0f}%',
        }
    
    def check_recent_drop(self, df: pd.DataFrame) -> dict:
        """检查近期跌幅"""
        # 近20日跌幅
        recent_20 = df.tail(20).copy()
        start_price = recent_20['close_price'].iloc[0]
        end_price = recent_20['close_price'].iloc[-1]
        drop = (end_price - start_price) / start_price * 100
        
        # 判断状态（辅助指标，仅作参考）
        if drop < -self.THRESHOLDS['drop_caution']:
            status = 'caution'
            signal = '⚠️ 谨慎'
        else:
            status = 'ok'
            signal = '✅ 正常'
        
        return {
            'name': '近20日跌幅',
            'value': drop,
            'unit': '%',
            'status': status,
            'signal': signal,
            'detail': f'近20日涨跌幅{drop:+.2f}%',
        }
    
    def check_market_breadth(self) -> dict:
        """检查市场广度（辅助指标）"""
        breadth = self.get_market_breadth()
        
        if not breadth or breadth['total'] == 0:
            return {
                'name': '市场广度',
                'value': 0,
                'unit': '%',
                'status': 'unknown',
                'signal': '❓ 数据缺失',
                'detail': '无法获取今日市场数据',
            }
        
        down_ratio = breadth['down_count'] / breadth['total'] * 100
        
        # 仅作参考，不作为核心判断
        status = 'ok'
        signal = '✅ 正常'
        
        return {
            'name': '下跌股票占比',
            'value': down_ratio,
            'unit': '%',
            'status': status,
            'signal': signal,
            'detail': f"上涨{breadth['up_count']}只, 下跌{breadth['down_count']}只, 跌幅占比{down_ratio:.0f}%",
        }
    
    def check_trend(self, df: pd.DataFrame) -> dict:
        """检查趋势方向"""
        df['ma20'] = df['close_price'].rolling(20).mean()
        
        # 计算均线斜率（近5日均线变化）
        ma20_current = df['ma20'].iloc[-1]
        ma20_5d_ago = df['ma20'].iloc[-6]
        slope = (ma20_current - ma20_5d_ago) / ma20_5d_ago * 100
        
        # 判断趋势
        if slope > 1:
            trend = '上涨'
            status = 'ok'
        elif slope < -1:
            trend = '下跌'
            status = 'caution'
        else:
            trend = '震荡'
            status = 'ok'
        
        return {
            'name': '趋势方向',
            'value': slope,
            'unit': '%',
            'status': status,
            'signal': '✅' if status == 'ok' else '⚠️',
            'detail': f'趋势: {trend}, 均线斜率{slope:+.2f}%',
        }
    
    def run_check(self) -> dict:
        """运行完整检查"""
        print("=" * 60)
        print("市场状态检查（基于回测验证）")
        print("=" * 60)
        print(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        
        # 获取数据
        df = self.get_index_data(days=90)  # 需要90天数据计算60日前价格
        
        # 执行各项检查
        checks = {
            'prev_60d_change': self.check_prev_60d_change(df),
            'recent_drop': self.check_recent_drop(df),
            'market_breadth': self.check_market_breadth(),
            'trend': self.check_trend(df),
        }
        
        # 输出结果
        print("【各项指标】\n")
        print(f"{'指标':<15} {'数值':>10} {'状态':>10} {'说明'}")
        print("-" * 60)
        
        stop_count = 0
        caution_count = 0
        
        for key, check in checks.items():
            print(f"{check['name']:<15} {check['value']:>+8.2f}{check['unit']} {check['signal']:>10} {check['detail']}")
            
            if check['status'] == 'stop':
                stop_count += 1
            elif check['status'] == 'caution':
                caution_count += 1
        
        # 综合判断
        print("\n" + "=" * 60)
        print("【综合判断】")
        print("=" * 60)
        
        # 核心判断：前60日涨跌幅
        prev_60d = checks['prev_60d_change']['value']
        
        if prev_60d < self.THRESHOLDS['prev_60d_stop']:
            final_status = 'stop'
            recommendation = '❌ 不建议启用'
            position = '0%'
            reason = f'前60日大跌{abs(prev_60d):.1f}%，因子历史胜率仅43.8%'
        elif prev_60d < self.THRESHOLDS['prev_60d_caution']:
            final_status = 'caution'
            recommendation = '⚠️ 谨慎启用'
            position = '30%~50%'
            reason = f'前60日下跌{abs(prev_60d):.1f}%，建议减仓'
        elif stop_count >= 2:
            final_status = 'caution'
            recommendation = '⚠️ 谨慎启用'
            position = '50%~80%'
            reason = f'有{stop_count}项指标异常'
        else:
            final_status = 'ok'
            recommendation = '✅ 建议启用'
            position = '80%~100%'
            reason = '前60日涨跌正常，市场环境适合'
        
        print(f"\n状态: {recommendation}")
        print(f"建议仓位: {position}")
        print(f"判断依据: {reason}")
        
        # 输出回测验证结论
        print("\n" + "=" * 60)
        print("【回测验证结论】")
        print("=" * 60)
        print("""
基于历史数据验证:
  - 前60日大涨(>+5%): 胜率59.4%, 收益+1.12% ✅ 有效
  - 前60日震荡: 胜率53%~56%, 收益+0.0%~+0.87% ➡️ 一般
  - 前60日大跌(<-5%): 胜率43.8%, 收益+0.05% ❌ 失效

核心判断标准: 前60日涨跌幅
  - 前60日跌 > 5%: 停止使用
  - 前60日跌 > 3%: 谨慎使用
  - 其他情况: 正常使用
""")
        
        return {
            'status': final_status,
            'recommendation': recommendation,
            'position': position,
            'checks': checks,
        }


def main():
    checker = MarketStatusChecker()
    try:
        result = checker.run_check()
    finally:
        checker.close()


if __name__ == '__main__':
    main()
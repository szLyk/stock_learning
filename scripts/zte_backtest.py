#!/usr/bin/env python3
"""
中兴通讯（000063）近5年主升浪回测分析

严格遵循原则：
1. 不使用未来函数（所有判断基于历史数据）
2. 使用固定的参数配置
3. 验证指标的可预测性
4. 计算置信区间

Author: Xiao Luo
Date: 2026-04-02
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime
from src.utils.mysql_tool import MySQLUtil
from logs.logger import LogManager


class ZTEBacktest:
    """中兴通讯主升浪回测分析"""
    
    # 固定参数（不使用未来函数）
    QUERY_DAYS = 90          # 回溯数据天数
    ACCUMULATION_DAYS = 10   # 蓄势期天数
    
    # 主升浪判断参数
    VOLUME_START_RATIO = 2.0      # 成交量启动阈值
    VOLUME_CONFIRM_RATIO = 3.0    # 成交量确认阈值
    LIMIT_UP_THRESHOLD = 9.5      # 涨停判断（%）
    MIN_LIMIT_UP_COUNT = 3        # 最少涨停次数
    
    def __init__(self):
        self.mysql = MySQLUtil()
        self.mysql.connect()
        self.logger = LogManager.get_logger("zte_backtest")
    
    def close(self):
        self.mysql.close()
    
    def get_price_data(self, end_date: str) -> pd.DataFrame:
        """
        获取指定日期之前的历史数据
        
        重要：不使用datetime.now()，只用传入的end_date
        """
        # 从end_date向前推QUERY_DAYS天
        sql = f"""
            SELECT 
                stock_date,
                open_price as open,
                high_price as high,
                low_price as low,
                close_price as close,
                trading_volume as volume,
                ups_and_downs as change_pct
            FROM stock_history_date_price
            WHERE stock_code = '000063'
                AND stock_date <= %s
                AND stock_date >= DATE_SUB(%s, INTERVAL {self.QUERY_DAYS + 30} DAY)
                AND tradestatus = 1
            ORDER BY stock_date ASC
        """
        
        result = self.mysql.query_all(sql, (end_date, end_date))
        if not result:
            return pd.DataFrame()
        
        df = pd.DataFrame(result)
        df['stock_date'] = pd.to_datetime(df['stock_date'])
        
        for col in ['open', 'high', 'low', 'close', 'volume', 'change_pct']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 只保留最近QUERY_DAYS天的数据
        df = df.tail(self.QUERY_DAYS).reset_index(drop=True)
        
        return df
    
    def get_future_data(self, signal_date: str, days: int = 20) -> pd.DataFrame:
        """
        获取信号日期之后的未来数据（仅用于验证，不参与判断）
        """
        sql = f"""
            SELECT 
                stock_date,
                close_price as close,
                high_price as high,
                ups_and_downs as change_pct
            FROM stock_history_date_price
            WHERE stock_code = '000063'
                AND stock_date > %s
                AND stock_date <= DATE_ADD(%s, INTERVAL {days + 10} DAY)
                AND tradestatus = 1
            ORDER BY stock_date ASC
        """
        
        result = self.mysql.query_all(sql, (signal_date, signal_date))
        if not result:
            return pd.DataFrame()
        
        df = pd.DataFrame(result)
        df['stock_date'] = pd.to_datetime(df['stock_date'])
        
        for col in ['close', 'high', 'change_pct']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df.head(days)
    
    def calculate_volume_ratio(self, price_df: pd.DataFrame) -> float:
        """计算最新成交量放大倍数"""
        if len(price_df) < self.ACCUMULATION_DAYS + 1:
            return 0
        
        # 用之前ACCUMULATION_DAYS天的平均成交量作为基准
        base_volume = price_df.iloc[-self.ACCUMULATION_DAYS-1:-1]['volume'].mean()
        current_volume = price_df.iloc[-1]['volume']
        
        return current_volume / base_volume if base_volume > 0 else 0
    
    def count_limit_ups(self, price_df: pd.DataFrame) -> int:
        """统计涨停次数"""
        return len(price_df[price_df['change_pct'] >= self.LIMIT_UP_THRESHOLD])
    
    def detect_signal(self, end_date: str) -> dict:
        """
        在指定日期检测主升浪信号
        
        严格原则：只使用end_date之前的数据
        """
        price_df = self.get_price_data(end_date)
        
        if price_df.empty or len(price_df) < 30:
            return {'signal': '数据不足', 'confidence': 0}
        
        # 1. 成交量放大倍数
        volume_ratio = self.calculate_volume_ratio(price_df)
        
        # 2. 涨停次数
        limit_up_count = self.count_limit_ups(price_df)
        
        # 3. 最新涨幅
        latest_change = price_df.iloc[-1]['change_pct']
        
        # 4. 近期涨停（最近10天）
        recent_limit_ups = self.count_limit_ups(price_df.tail(10))
        
        # 5. 成交量趋势（最近3天是否持续放大）
        if len(price_df) >= 3:
            vol_trend = (price_df.iloc[-1]['volume'] > price_df.iloc[-2]['volume'] > price_df.iloc[-3]['volume'])
        else:
            vol_trend = False
        
        # 计算置信度
        score = 0
        signals = []
        
        # 成交量放大
        if volume_ratio >= self.VOLUME_CONFIRM_RATIO:
            score += 1.5
            signals.append(f"成交量放大{volume_ratio:.1f}x(确认)")
        elif volume_ratio >= self.VOLUME_START_RATIO:
            score += 1
            signals.append(f"成交量放大{volume_ratio:.1f}x(启动)")
        else:
            signals.append(f"成交量放大{volume_ratio:.1f}x(不足)")
        
        # 涨停次数
        if limit_up_count >= self.MIN_LIMIT_UP_COUNT:
            score += 1.5
            signals.append(f"涨停{limit_up_count}次(充足)")
        elif limit_up_count >= 2:
            score += 1
            signals.append(f"涨停{limit_up_count}次(一般)")
        else:
            signals.append(f"涨停{limit_up_count}次(不足)")
        
        # 近期涨停密度
        if recent_limit_ups >= 2:
            score += 1
            signals.append(f"近10天涨停{recent_limit_ups}次")
        
        # 当日涨停
        if latest_change >= self.LIMIT_UP_THRESHOLD:
            score += 1
            signals.append(f"当日涨停{latest_change:.1f}%")
        
        # 成交量趋势
        if vol_trend:
            score += 0.5
            signals.append("成交量持续放大")
        
        # 归一化置信度（满分5分）
        confidence = min(score / 5, 1.0)
        
        # 判断信号类型
        if confidence >= 0.7:
            signal_type = '强烈启动信号'
        elif confidence >= 0.5:
            signal_type = '启动信号'
        elif confidence >= 0.3:
            signal_type = '观望信号'
        else:
            signal_type = '无信号'
        
        return {
            'signal': signal_type,
            'confidence': confidence,
            'volume_ratio': volume_ratio,
            'limit_up_count': limit_up_count,
            'recent_limit_ups': recent_limit_ups,
            'latest_change': latest_change,
            'signals': signals
        }
    
    def verify_signal(self, signal_date: str, verify_days: int = 20) -> dict:
        """
        验证信号准确性（使用未来数据）
        
        返回后续涨幅、涨停次数等验证指标
        """
        # 获取未来数据
        future_df = self.get_future_data(signal_date, verify_days)
        
        if future_df.empty:
            return {'valid': False, 'reason': '无后续数据'}
        
        # 获取信号日的收盘价
        signal_price_sql = "SELECT close_price FROM stock_history_date_price WHERE stock_code = '000063' AND stock_date = %s"
        signal_result = self.mysql.query_one(signal_price_sql, (signal_date,))
        
        if not signal_result:
            return {'valid': False, 'reason': '无信号日价格'}
        
        signal_price = float(signal_result['close_price'])
        
        # 计算后续涨幅
        end_price = future_df.iloc[-1]['close']
        max_price = future_df['high'].max()
        
        total_change = (end_price - signal_price) / signal_price * 100
        max_change = (max_price - signal_price) / signal_price * 100
        
        # 统计后续涨停次数
        future_limit_ups = len(future_df[future_df['change_pct'] >= self.LIMIT_UP_THRESHOLD])
        
        # 判断是否验证成功
        # 成功标准：后续涨幅>=10% 或 有涨停
        is_success = total_change >= 10 or future_limit_ups >= 1
        
        return {
            'valid': True,
            'signal_date': signal_date,
            'signal_price': signal_price,
            'end_price': end_price,
            'max_price': max_price,
            'total_change': total_change,
            'max_change': max_change,
            'future_limit_ups': future_limit_ups,
            'is_success': is_success,
            'verify_days': len(future_df)
        }
    
    def run_backtest(self, signal_dates: list, verify_days: int = 20):
        """
        批量回测
        
        Args:
            signal_dates: 信号日期列表
            verify_days: 验证天数
        """
        results = []
        
        print("=" * 80)
        print("📊 中兴通讯（000063）近5年主升浪回测分析")
        print("=" * 80)
        
        print(f"\n回测参数：")
        print(f"  - 成交量启动阈值: {self.VOLUME_START_RATIO}x")
        print(f"  - 成交量确认阈值: {self.VOLUME_CONFIRM_RATIO}x")
        print(f"  - 涨停判断阈值: {self.LIMIT_UP_THRESHOLD}%")
        print(f"  - 最少涨停次数: {self.MIN_LIMIT_UP_COUNT}次")
        print(f"  - 验证周期: {verify_days}天")
        
        print("\n" + "=" * 80)
        print("📋 回测结果")
        print("=" * 80)
        
        for date in signal_dates:
            print(f"\n【回测日期: {date}】")
            
            # 1. 检测信号（只使用历史数据）
            signal_result = self.detect_signal(date)
            
            print(f"信号类型: {signal_result['signal']}")
            print(f"置信度: {signal_result['confidence']:.2f}")
            print(f"信号详情: {', '.join(signal_result['signals'])}")
            
            # 2. 验证信号（使用未来数据）
            verify_result = self.verify_signal(date, verify_days)
            
            if verify_result['valid']:
                print(f"\n后续走势（{verify_result['verify_days']}天）:")
                print(f"  - 起始价格: {verify_result['signal_price']:.2f}")
                print(f"  - 结束价格: {verify_result['end_price']:.2f}")
                print(f"  - 最高价格: {verify_result['max_price']:.2f}")
                print(f"  - 总涨幅: {verify_result['total_change']:+.2f}%")
                print(f"  - 最大涨幅: {verify_result['max_change']:+.2f}%")
                print(f"  - 后续涨停: {verify_result['future_limit_ups']}次")
                
                result = {
                    'date': date,
                    'signal': signal_result['signal'],
                    'confidence': signal_result['confidence'],
                    'total_change': verify_result['total_change'],
                    'max_change': verify_result['max_change'],
                    'future_limit_ups': verify_result['future_limit_ups'],
                    'is_success': verify_result['is_success']
                }
                results.append(result)
                
                print(f"验证结果: {'✅ 成功' if verify_result['is_success'] else '❌ 失败'}")
            else:
                print(f"验证失败: {verify_result['reason']}")
        
        # 统计结果
        print("\n" + "=" * 80)
        print("📈 回测统计")
        print("=" * 80)
        
        if results:
            success_count = sum(1 for r in results if r['is_success'])
            total_count = len(results)
            accuracy = success_count / total_count * 100
            
            print(f"\n总测试次数: {total_count}")
            print(f"成功次数: {success_count}")
            print(f"失败次数: {total_count - success_count}")
            print(f"准确率: {accuracy:.1f}%")
            
            # 按置信度分组统计
            high_conf = [r for r in results if r['confidence'] >= 0.6]
            mid_conf = [r for r in results if 0.3 <= r['confidence'] < 0.6]
            low_conf = [r for r in results if r['confidence'] < 0.3]
            
            print(f"\n【按置信度分组】")
            
            if high_conf:
                high_success = sum(1 for r in high_conf if r['is_success'])
                print(f"高置信度(≥0.6): {high_success}/{len(high_conf)} = {high_success/len(high_conf)*100:.1f}%")
            
            if mid_conf:
                mid_success = sum(1 for r in mid_conf if r['is_success'])
                print(f"中置信度(0.3-0.6): {mid_success}/{len(mid_conf)} = {mid_success/len(mid_conf)*100:.1f}%")
            
            if low_conf:
                low_success = sum(1 for r in low_conf if r['is_success'])
                print(f"低置信度(<0.3): {low_success}/{len(low_conf)} = {low_success/len(low_conf)*100:.1f}%")
            
            # 计算置信区间（Wilson区间）
            from math import sqrt
            n = total_count
            p = success_count / n
            z = 1.96  # 95%置信水平
            
            if n > 0:
                denominator = 1 + z**2/n
                center = (p + z**2/(2*n)) / denominator
                margin = z * sqrt((p*(1-p) + z**2/(4*n))/n) / denominator
                
                lower_bound = max(0, center - margin)
                upper_bound = min(1, center + margin)
                
                print(f"\n【置信区间（95%）】")
                print(f"准确率: {accuracy:.1f}%")
                print(f"95%置信区间: [{lower_bound*100:.1f}%, {upper_bound*100:.1f}%]")
                print(f"解释: 有95%的概率，真实准确率落在[{lower_bound*100:.1f}%, {upper_bound*100:.1f}%]区间内")
        
        return results


def main():
    """主函数"""
    backtest = ZTEBacktest()
    
    # 定义回测日期（基于历史涨停数据分析）
    # 这些日期是涨停日，用于测试模型是否能在当天识别启动信号
    signal_dates = [
        '2023-04-07',   # 2023年主升浪启动
        '2023-06-20',   # 2023年主升浪确认
        '2024-02-27',   # 2024年2月涨停
        '2024-10-08',   # 2024年10月主升浪启动
        '2024-11-11',   # 2024年11月涨停
        '2024-12-19',   # 2024年12月大涨
        '2025-01-09',   # 2025年1月涨停
        '2025-10-09',   # 2025年10月涨停
        '2025-12-01',   # 2025年12月涨停
    ]
    
    # 运行回测
    results = backtest.run_backtest(signal_dates, verify_days=15)
    
    backtest.close()
    
    return results


if __name__ == '__main__':
    main()
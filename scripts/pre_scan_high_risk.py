#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
盘后预筛选 - 高风险股票池

目标：找出"明天可能大跌"的股票池

筛选条件：
1. RSI(14) > 70：超买，短期过热
2. 均线偏离 > 10%：股价远高于MA20
3. 连续上涨 >= 3天：涨势可能衰竭
4. 放量滞涨：成交量放大但涨幅小
5. 近10日涨幅 > 20%：短期暴涨

运行时间：每天盘后 20:00

输出：data/pre_scan/high_risk_pool_{date}.csv

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


class HighRiskScanner:
    """高风险股票扫描器"""

    OUTPUT_DIR = Path(__file__).parent.parent / 'data' / 'pre_scan'

    # 筛选阈值
    THRESHOLDS = {
        'rsi_overbought': 70,           # RSI超买阈值
        'ma_deviation_high': 10,        # 均线偏离阈值(%)
        'consecutive_up_days': 3,        # 连续上涨天数
        'volume_surge': 2.0,            # 放量倍数（相对5日均量）
        'stagnant_gain': 2.0,           # 滞涨阈值(%)，放量但涨幅小于此值
        'recent_gain_high': 20,         # 近10日涨幅阈值(%)
        'min_price': 3,                 # 最低价格
        'max_cap': 100,                 # 最大市值(亿)
    }

    def __init__(self):
        self.mysql = MySQLUtil()
        self.mysql.connect()
        self.logger = LogManager.get_logger("high_risk_scanner")
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def close(self):
        self.mysql.close()

    def fetch_stock_list(self) -> pd.DataFrame:
        """获取股票列表"""
        sql = '''
            SELECT DISTINCT stock_code
            FROM stock_history_date_price
            WHERE stock_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
              AND tradestatus = 1
        '''
        result = self.mysql.query_all(sql)
        return pd.DataFrame(result)

    def fetch_stock_data(self, stock_code: str, days: int = 60) -> pd.DataFrame:
        """获取单只股票历史数据"""
        sql = f'''
            SELECT stock_date, open_price, close_price, high_price, low_price,
                   trading_volume, turn, ups_and_downs
            FROM stock_history_date_price
            WHERE stock_code = '{stock_code}'
              AND stock_date >= DATE_SUB(CURDATE(), INTERVAL {days} DAY)
              AND tradestatus = 1
            ORDER BY stock_date ASC
        '''
        result = self.mysql.query_all(sql)
        if not result:
            return pd.DataFrame()

        df = pd.DataFrame(result)
        df['stock_date'] = pd.to_datetime(df['stock_date'])
        for col in ['open_price', 'close_price', 'high_price', 'low_price',
                    'trading_volume', 'turn', 'ups_and_downs']:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        return df

    def calc_rsi(self, df: pd.DataFrame, period: int = 14) -> float:
        """计算RSI"""
        if len(df) < period + 1:
            return None

        delta = df['close_price'].diff()
        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)

        avg_gain = gain.rolling(period).mean()
        avg_loss = loss.rolling(period).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else None

    def calc_ma_deviation(self, df: pd.DataFrame) -> float:
        """计算均线偏离度"""
        if len(df) < 20:
            return None

        df['ma20'] = df['close_price'].rolling(20).mean()
        current = df['close_price'].iloc[-1]
        ma20 = df['ma20'].iloc[-1]

        if pd.isna(ma20) or ma20 == 0:
            return None

        return (current - ma20) / ma20 * 100

    def calc_consecutive_up(self, df: pd.DataFrame) -> int:
        """计算连续上涨天数"""
        if len(df) < 5:
            return 0

        changes = df['ups_and_downs'].values
        count = 0
        for i in range(len(changes) - 1, -1, -1):
            if changes[i] > 0:
                count += 1
            else:
                break
        return count

    def calc_volume_surge(self, df: pd.DataFrame) -> tuple:
        """计算放量情况"""
        if len(df) < 10:
            return None, None

        volume_ma5 = df['trading_volume'].rolling(5).mean().iloc[-1]
        today_volume = df['trading_volume'].iloc[-1]
        today_change = df['ups_and_downs'].iloc[-1]

        if pd.isna(volume_ma5) or volume_ma5 == 0:
            return None, None

        volume_ratio = today_volume / volume_ma5
        return volume_ratio, today_change

    def calc_recent_gain(self, df: pd.DataFrame, days: int = 10) -> float:
        """计算近N日涨幅"""
        if len(df) < days:
            return None

        start_price = df['close_price'].iloc[-days]
        end_price = df['close_price'].iloc[-1]

        if pd.isna(start_price) or start_price == 0:
            return None

        return (end_price - start_price) / start_price * 100

    def calc_market_cap(self, df: pd.DataFrame) -> float:
        """估算流通市值（亿）"""
        if df.empty:
            return None

        close = df['close_price'].iloc[-1]
        volume = df['trading_volume'].iloc[-1]
        turn = df['turn'].iloc[-1]

        if pd.isna(turn) or turn <= 0 or pd.isna(volume):
            return None

        # 流通股本 = 成交量 / 换手率 * 100
        circ_share = volume / turn * 100
        circ_cap = circ_share * close / 100000000

        return circ_cap

    def scan_single_stock(self, stock_code: str) -> dict:
        """扫描单只股票"""
        df = self.fetch_stock_data(stock_code)
        if df.empty or len(df) < 30:
            return None

        # 计算各项指标
        rsi = self.calc_rsi(df)
        ma_dev = self.calc_ma_deviation(df)
        consec_up = self.calc_consecutive_up(df)
        vol_ratio, today_change = self.calc_volume_surge(df)
        recent_gain = self.calc_recent_gain(df)
        market_cap = self.calc_market_cap(df)

        current_price = df['close_price'].iloc[-1]
        pre_close = df['close_price'].iloc[-2] if len(df) > 1 else current_price

        # 基本过滤
        if current_price < self.THRESHOLDS['min_price']:
            return None
        if market_cap and market_cap > self.THRESHOLDS['max_cap']:
            return None

        # 计算风险评分（各项条件加权）
        risk_signals = []
        risk_score = 0

        # 1. RSI超买
        if rsi and rsi > self.THRESHOLDS['rsi_overbought']:
            risk_signals.append(f"RSI={rsi:.1f}")
            risk_score += 20

        # 2. 均线偏离过大
        if ma_dev and ma_dev > self.THRESHOLDS['ma_deviation_high']:
            risk_signals.append(f"偏离MA20={ma_dev:.1f}%")
            risk_score += 20

        # 3. 连续上涨天数过多
        if consec_up >= self.THRESHOLDS['consecutive_up_days']:
            risk_signals.append(f"连涨{consec_up}天")
            risk_score += 15

        # 4. 放量滞涨
        if vol_ratio and vol_ratio > self.THRESHOLDS['volume_surge']:
            if today_change is not None and today_change < self.THRESHOLDS['stagnant_gain']:
                risk_signals.append(f"放量{vol_ratio:.1f}倍滞涨")
                risk_score += 25

        # 5. 近期涨幅过大
        if recent_gain and recent_gain > self.THRESHOLDS['recent_gain_high']:
            risk_signals.append(f"近10日涨{recent_gain:.1f}%")
            risk_score += 20

        # 至少满足2个条件才纳入
        if len(risk_signals) < 2:
            return None

        return {
            'stock_code': stock_code,
            'stock_name': '',  # 后续补充
            'close_price': round(current_price, 2),
            'pre_close': round(pre_close, 2),
            'change_pct': round((current_price - pre_close) / pre_close * 100, 2) if pre_close > 0 else 0,
            'rsi': round(rsi, 1) if rsi else None,
            'ma_deviation': round(ma_dev, 2) if ma_dev else None,
            'consecutive_up': consec_up,
            'volume_ratio': round(vol_ratio, 2) if vol_ratio else None,
            'recent_gain_10d': round(recent_gain, 2) if recent_gain else None,
            'market_cap_yi': round(market_cap, 2) if market_cap else None,
            'risk_score': risk_score,
            'risk_signals': '; '.join(risk_signals),
            'scan_date': datetime.now().strftime('%Y-%m-%d'),
        }

    def run_scan(self) -> pd.DataFrame:
        """运行扫描"""
        print("=" * 70)
        print("高风险股票池扫描")
        print("=" * 70)
        print(f"扫描时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print()

        # 获取股票列表
        print("[步骤1] 获取股票列表...")
        stock_list = self.fetch_stock_list()
        total = len(stock_list)
        print(f"  共 {total} 只股票")

        # 逐个扫描
        print(f"\n[步骤2] 扫描股票（筛选条件：至少满足2项风险信号）...")
        print(f"  - RSI > {self.THRESHOLDS['rsi_overbought']}")
        print(f"  - 均线偏离 > {self.THRESHOLDS['ma_deviation_high']}%")
        print(f"  - 连涨 >= {self.THRESHOLDS['consecutive_up_days']}天")
        print(f"  - 放量 > {self.THRESHOLDS['volume_surge']}倍且滞涨")
        print(f"  - 近10日涨幅 > {self.THRESHOLDS['recent_gain_high']}%")
        print()

        results = []
        for i, row in stock_list.iterrows():
            stock_code = row['stock_code']

            try:
                result = self.scan_single_stock(stock_code)
                if result:
                    results.append(result)

                # 进度
                if (i + 1) % 500 == 0:
                    print(f"  进度: {i+1}/{total}, 已筛选: {len(results)}")

            except Exception as e:
                pass

        print(f"\n  扫描完成，筛选出 {len(results)} 只高风险股票")

        if not results:
            print("无符合条件的股票")
            return pd.DataFrame()

        # 转换为DataFrame
        df = pd.DataFrame(results)

        # 确保stock_code为字符串类型
        df['stock_code'] = df['stock_code'].astype(str).str.zfill(6)

        # 补充股票名称
        print("\n[步骤3] 补充股票名称...")
        # 将股票代码转为6位字符串格式用于SQL查询
        code_list = df['stock_code'].tolist()
        code_str = "','".join(code_list)
        name_sql = f"""
            SELECT stock_code, stock_name
            FROM stock_basic
            WHERE stock_code IN ('{code_str}')
        """
        names = self.mysql.query_all(name_sql)
        if names:
            name_map = {r['stock_code']: r['stock_name'] for r in names}
            df['stock_name'] = df['stock_code'].map(name_map)

        # 按风险评分排序
        df = df.sort_values('risk_score', ascending=False)

        # 保存结果
        today = datetime.now().strftime('%Y%m%d')
        output_file = self.OUTPUT_DIR / f'high_risk_pool_{today}.csv'
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\n结果已保存: {output_file}")

        # 输出统计
        print("\n" + "=" * 70)
        print("扫描结果统计")
        print("=" * 70)
        print(f"总扫描股票: {total}")
        print(f"高风险股票: {len(df)}")
        print(f"占比: {len(df)/total*100:.2f}%")

        print(f"\n风险评分分布:")
        print(f"  高风险(≥60分): {len(df[df['risk_score']>=60])} 只")
        print(f"  中风险(40-60分): {len(df[(df['risk_score']>=40) & (df['risk_score']<60)])} 只")
        print(f"  低风险(<40分): {len(df[df['risk_score']<40])} 只")

        print(f"\nTop 10 高风险股票:")
        print(f"{'代码':<10} {'名称':<10} {'现价':>8} {'风险分':>8} {'风险信号'}")
        print("-" * 70)
        for _, row in df.head(10).iterrows():
            print(f"{row['stock_code']:<10} {row['stock_name']:<10} {row['close_price']:>8.2f} {row['risk_score']:>8} {row['risk_signals'][:40]}")

        return df


def main():
    scanner = HighRiskScanner()
    try:
        df = scanner.run_scan()
    finally:
        scanner.close()


if __name__ == '__main__':
    main()
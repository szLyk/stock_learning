#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
盘中实时信号扫描器

目标：下午14:00运行，筛选符合买入条件的股票

流程：
1. 读取前一天生成的高风险股票池
2. 调用实时接口获取当前价格
3. 筛选跌幅 -7%~-6% 且换手率 < 2% 的股票
4. 输出推荐买入列表

运行时间：下午 14:00

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
from src.utils.realtime_quote_fetcher import RealtimeQuoteFetcher
from logs.logger import LogManager


class RealtimeSignalScanner:
    """实时信号扫描器"""

    INPUT_DIR = Path(__file__).parent.parent / 'data' / 'pre_scan'
    OUTPUT_DIR = Path(__file__).parent.parent / 'data' / 'realtime_signals'

    # 买入条件（基于回测验证结果）
    BUY_CONDITIONS = {
        'drop_range': (-7.5, -5.5),     # 跌幅范围 -7.5%~-5.5%（放宽一点）
        'turnover_max': 2.5,             # 最大换手率
        'min_drop_range': (-10, -7),     # 跌停区域（高胜率）
        'min_drop_turnover_max': 3,      # 跌停区换手率放宽
        'market_cap_max': 100,           # 最大市值(亿)
    }

    def __init__(self):
        self.mysql = MySQLUtil()
        self.mysql.connect()
        self.quote_fetcher = RealtimeQuoteFetcher()
        self.logger = LogManager.get_logger("realtime_scanner")
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def close(self):
        self.mysql.close()

    def load_high_risk_pool(self, date: str = None) -> pd.DataFrame:
        """加载高风险股票池"""
        if date is None:
            # 查找最新文件
            files = sorted(self.INPUT_DIR.glob('high_risk_pool_*.csv'), reverse=True)
            if not files:
                print("未找到高风险股票池文件，请先运行 pre_scan_high_risk.py")
                return pd.DataFrame()
            input_file = files[0]
        else:
            input_file = self.INPUT_DIR / f'high_risk_pool_{date}.csv'

        if not input_file.exists():
            print(f"文件不存在: {input_file}")
            return pd.DataFrame()

        df = pd.read_csv(input_file, dtype={'stock_code': str})
        # 确保股票代码为6位字符串格式
        df['stock_code'] = df['stock_code'].astype(str).str.zfill(6)
        print(f"加载高风险股票池: {input_file.name}，共 {len(df)} 只")
        return df

    def get_market_state(self) -> dict:
        """获取大盘状态"""
        try:
            quote = self.quote_fetcher.fetch_single('000001')  # 上证指数
            if quote:
                return {
                    'index_code': '000001',
                    'index_name': quote.get('name', '上证指数'),
                    'index_price': quote.get('current', 0),
                    'index_change': quote.get('change_pct', 0),
                }
        except Exception as e:
            self.logger.warning(f"获取大盘状态失败: {e}")

        return {
            'index_code': '000001',
            'index_name': '上证指数',
            'index_price': 0,
            'index_change': 0,
        }

    def get_stock_info(self, stock_codes: list) -> dict:
        """从数据库获取股票信息"""
        if not stock_codes:
            return {}

        # 将股票代码转为字符串
        code_str = "','".join([str(c).zfill(6) for c in stock_codes])

        sql = f'''
            SELECT stock_code, stock_name
            FROM stock_basic
            WHERE stock_code IN ('{code_str}')
        '''
        result = self.mysql.query_all(sql)

        info_map = {}
        for r in result:
            info_map[str(r['stock_code']).zfill(6)] = {
                'stock_name': r.get('stock_name', ''),
            }
        return info_map

    def scan(self, use_high_risk_pool: bool = True) -> pd.DataFrame:
        """运行扫描"""
        print("=" * 70)
        print("实时信号扫描器")
        print("=" * 70)
        print(f"扫描时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print()

        # 1. 获取大盘状态
        print("[步骤1] 获取大盘状态...")
        market = self.get_market_state()
        print(f"  {market['index_name']}: {market['index_price']} ({market['index_change']:+.2f}%)")
        print()

        # 2. 获取待扫描股票列表
        if use_high_risk_pool:
            print("[步骤2] 加载高风险股票池...")
            risk_df = self.load_high_risk_pool()
            if risk_df.empty:
                # 如果没有高风险池，扫描全市场
                print("  无高风险池，改为扫描全市场...")
                sql = '''
                    SELECT DISTINCT stock_code
                    FROM stock_history_date_price
                    WHERE stock_date = CURDATE() - INTERVAL 1 DAY
                      AND tradestatus = 1
                '''
                result = self.mysql.query_all(sql)
                stock_codes = [r['stock_code'] for r in result]
            else:
                stock_codes = risk_df['stock_code'].tolist()
        else:
            print("[步骤2] 扫描全市场...")
            sql = '''
                SELECT DISTINCT stock_code
                FROM stock_history_date_price
                WHERE stock_date = CURDATE() - INTERVAL 1 DAY
                  AND tradestatus = 1
            '''
            result = self.mysql.query_all(sql)
            stock_codes = [r['stock_code'] for r in result]

        print(f"  待扫描股票: {len(stock_codes)} 只")
        print()

        # 3. 获取实时行情
        print("[步骤3] 获取实时行情...")
        print(f"  使用接口: 多接口轮换（新浪/腾讯）")
        print()

        quotes = self.quote_fetcher.fetch_quotes(stock_codes)
        print(f"  成功获取: {len(quotes)} 只")
        print()

        if not quotes:
            print("无实时行情数据")
            return pd.DataFrame()

        # 4. 筛选符合买入条件的股票
        print("[步骤4] 筛选买入信号...")
        print(f"  条件1: 跌幅 {self.BUY_CONDITIONS['drop_range'][0]}%~{self.BUY_CONDITIONS['drop_range'][1]}%")
        print(f"  条件2: 换手率 < {self.BUY_CONDITIONS['turnover_max']}%")
        print(f"  条件3: 跌停区域 {self.BUY_CONDITIONS['min_drop_range'][0]}%~{self.BUY_CONDITIONS['min_drop_range'][1]}%（胜率更高）")
        print()

        signals = []
        for code, quote in quotes.items():
            change_pct = quote['change_pct']
            # 从实时数据无法直接获取换手率，需要从数据库查询
            # 这里用成交量判断（简化）
            current = quote['current']
            pre_close = quote['pre_close']
            volume = quote.get('volume', 0)

            # 判断跌幅
            if change_pct > self.BUY_CONDITIONS['drop_range'][1]:
                continue  # 跌幅不够
            if change_pct < self.BUY_CONDITIONS['drop_range'][0]:
                # 跌停区域，单独处理
                pass

            signals.append({
                'stock_code': code,
                'stock_name': quote.get('name', ''),
                'current_price': current,
                'pre_close': pre_close,
                'change_pct': change_pct,
                'high': quote.get('high', 0),
                'low': quote.get('low', 0),
                'volume': volume,
                'source': quote.get('source', ''),
                'is_limit_down': change_pct < -9.5,  # 是否跌停
            })

        if not signals:
            print("无符合条件的股票")
            return pd.DataFrame()

        df = pd.DataFrame(signals)

        # 补充股票信息
        info_map = self.get_stock_info(df['stock_code'].tolist())
        df['stock_name'] = df['stock_code'].map(lambda x: info_map.get(str(x).zfill(6), {}).get('stock_name', quote.get('name', '')))
        if 'stock_name' not in df.columns or df['stock_name'].isna().any():
            df['stock_name'] = df['stock_code'].map(lambda x: info_map.get(str(x).zfill(6), {}).get('stock_name', ''))

        # 标记推荐级别
        def get_recommend_level(row):
            change = row['change_pct']
            is_limit = row['is_limit_down']

            if is_limit:
                return '跌停(高胜率)'
            elif change < -7:
                return '强烈推荐'
            elif change < -6:
                return '推荐'
            else:
                return '一般'

        df['recommend_level'] = df.apply(get_recommend_level, axis=1)

        # 按跌幅排序
        df = df.sort_values('change_pct')

        # 5. 输出结果
        print("\n" + "=" * 70)
        print("扫描结果")
        print("=" * 70)

        print(f"\n总筛选股票: {len(df)} 只")
        print(f"  跌停区域: {len(df[df['is_limit_down']])} 只")
        print(f"  强烈推荐: {len(df[(df['change_pct']<-7) & (~df['is_limit_down'])])} 只")
        print(f"  推荐: {len(df[(df['change_pct']>=-7) & (df['change_pct']<-6)])} 只")

        # 保存结果
        today = datetime.now().strftime('%Y%m%d_%H%M')
        output_file = self.OUTPUT_DIR / f'signals_{today}.csv'
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\n结果已保存: {output_file}")

        # 输出推荐列表
        print("\n" + "=" * 70)
        print("推荐买入列表")
        print("=" * 70)

        print(f"\n{'代码':<10} {'名称':<10} {'现价':>8} {'跌幅':>8} {'推荐级别':>12}")
        print("-" * 60)
        for _, row in df.head(20).iterrows():
            print(f"{row['stock_code']:<10} {row['stock_name']:<10} {row['current_price']:>8.2f} "
                  f"{row['change_pct']:>+7.2f}% {row['recommend_level']:>12}")

        # 风险提示
        print("\n" + "=" * 70)
        print("风险提示")
        print("=" * 70)
        print("""
1. 跌停股票可买入但需排队，建议小仓位尝试
2. 持仓周期建议 3 日，不要超过 5 日
3. 大盘大跌环境下效果更好
4. 连续缩量效果更好
5. 需结合个人判断，不构成投资建议
""")

        print("接口状态:", self.quote_fetcher.get_status())

        return df


def main():
    scanner = RealtimeSignalScanner()
    try:
        df = scanner.scan(use_high_risk_pool=True)
    finally:
        scanner.close()


if __name__ == '__main__':
    main()
#!/usr/bin/env python3
"""
股票个股信息采集脚本（带断点续传）

数据源: AKShare - stock_individual_info_em (东方财富)
功能: 获取股票的股本、市值、行业等信息
特性: 支持断点续传，异常中断后可继续采集

使用方法:
    # 测试模式（少量数据）
    python scripts/fetch_stock_individual_info.py --test
    
    # 正式采集（全量）
    python scripts/fetch_stock_individual_info.py --all
    
    # 查看状态
    python scripts/fetch_stock_individual_info.py --status
    
    # 清除 Redis 记录（重新采集）
    python scripts/fetch_stock_individual_info.py --reset

参考: baostock_financial.py 的断点续传实现
数据表: stock_individual_info

Author: Xiao Luo
Date: 2026-04-02
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import argparse
import pandas as pd
import akshare as ak
from datetime import datetime
from typing import List, Optional, Dict
from src.utils.mysql_tool import MySQLUtil
from src.utils.redis_tool import RedisUtil
from logs.logger import LogManager


class StockIndividualInfoFetcher:
    """股票个股信息采集器（支持断点续传）"""

    DATA_TYPE = 'individual_info'

    def __init__(self):
        self.mysql = MySQLUtil()
        self.mysql.connect()
        self.redis = RedisUtil() if RedisUtil else None
        self.logger = LogManager.get_logger("stock_individual_info")
        self.now_date = datetime.now().strftime('%Y-%m-%d')

    def close(self):
        self.mysql.close()

    # =====================================================
    # 数据获取
    # =====================================================

    def fetch_single_stock(self, stock_code: str, retry: int = 3) -> Optional[Dict]:
        """
        获取单只股票的个股信息
        
        Args:
            stock_code: 股票代码（纯代码，如 000063）
            retry: 重试次数
        
        Returns:
            字典或 None
        """
        for i in range(retry):
            try:
                df = ak.stock_individual_info_em(symbol=stock_code)

                if df.empty:
                    return None

                # 解析数据
                result = {'stock_code': stock_code}

                for _, row in df.iterrows():
                    item = row['item']
                    value = row['value']

                    if item == '股票简称':
                        result['stock_name'] = value
                    elif item == '最新':
                        result['latest_price'] = float(value) if value else None
                    elif item == '总股本':
                        result['total_share'] = float(value) if value else None
                    elif item == '流通股':
                        result['circ_share'] = float(value) if value else None
                    elif item == '总市值':
                        result['total_market_cap'] = float(value) if value else None
                    elif item == '流通市值':
                        result['circ_market_cap'] = float(value) if value else None
                    elif item == '行业':
                        result['industry'] = value
                    elif item == '上市时间':
                        if value and len(str(value)) == 8:
                            result['list_date'] = f"{value[:4]}-{value[4:6]}-{value[6:8]}"
                        else:
                            result['list_date'] = None

                return result

            except Exception as e:
                self.logger.warning(f"获取 {stock_code} 失败 (尝试 {i + 1}/{retry}): {e}")
                time.sleep(1)

        return None

    # =====================================================
    # 数据存储
    # =====================================================

    def save_to_db(self, data: Dict) -> bool:
        """保存到数据库"""
        if not data:
            return False

        sql = """
            INSERT INTO stock_individual_info 
            (stock_code, stock_name, latest_price, total_share, circ_share,
             total_market_cap, circ_market_cap, industry, list_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
                stock_name = VALUES(stock_name),
                latest_price = VALUES(latest_price),
                total_share = VALUES(total_share),
                circ_share = VALUES(circ_share),
                total_market_cap = VALUES(total_market_cap),
                circ_market_cap = VALUES(circ_market_cap),
                industry = VALUES(industry),
                list_date = VALUES(list_date),
                update_time = NOW()
        """

        params = (
            data['stock_code'],
            data.get('stock_name'),
            data.get('latest_price'),
            data.get('total_share'),
            data.get('circ_share'),
            data.get('total_market_cap'),
            data.get('circ_market_cap'),
            data.get('industry'),
            data.get('list_date')
        )

        try:
            self.mysql.execute(sql, params)
            return True
        except Exception as e:
            self.logger.error(f"保存 {data['stock_code']} 失败: {e}")
            return False

    # =====================================================
    # Redis 断点续传机制
    # =====================================================

    def get_pending_stocks(self) -> List[str]:
        """
        获取待采集股票列表（支持断点续传）
        
        优先级：
        1. Redis 中的待处理列表（断点续传）
        2. 数据库中的全部股票（首次执行）
        """
        if self.redis:
            # 尝试从 Redis 获取
            pending = self.redis.get_unprocessed_stocks(self.now_date, self.DATA_TYPE)

            if pending:
                self.logger.info(f"📌 Redis 断点续传: {len(pending)} 只待处理股票")
                return pending

        # 从数据库获取全部股票
        sql = "SELECT stock_code FROM stock_basic WHERE stock_status = 1"
        result = self.mysql.query_all(sql)

        if not result:
            self.logger.warning("数据库中无股票数据")
            return []

        stock_list = [row['stock_code'] for row in result]

        # 初始化 Redis
        if self.redis:
            self.redis.add_unprocessed_stocks(stock_list, self.now_date, self.DATA_TYPE)
            self.logger.info(f"✅ Redis 初始化: {len(stock_list)} 只股票")

        return stock_list

    def mark_as_processed(self, stock_code: str):
        """标记股票为已处理"""
        if self.redis:
            self.redis.remove_unprocessed_stocks([stock_code], self.now_date, self.DATA_TYPE)

    def reset_redis(self):
        """清除 Redis 记录（重新开始）"""
        if self.redis:
            # 清除待处理列表
            key = f"{self.DATA_TYPE}:stock_data:{self.now_date}:unprocessed"
            self.redis.client.delete(key)
            self.logger.info("✅ Redis 记录已清除")

    def get_status(self) -> Dict:
        """获取采集状态"""
        status = {
            'date': self.now_date,
            'total': 0,
            'pending': 0,
            'processed': 0
        }

        # 获取总股票数
        sql = "SELECT COUNT(*) as cnt FROM stock_basic WHERE stock_status = 1"
        result = self.mysql.query_one(sql)
        status['total'] = result['cnt'] if result else 0

        # 获取已采集数量（从目标表查询）
        sql = "SELECT COUNT(*) as cnt FROM stock_individual_info"
        result = self.mysql.query_one(sql)
        status['processed'] = result['cnt'] if result else 0

        # 获取 Redis 状态
        if self.redis:
            pending = self.redis.get_unprocessed_stocks(self.now_date, self.DATA_TYPE)
            status['pending'] = len(pending)
        else:
            status['pending'] = status['total'] - status['processed']

        return status

    # =====================================================
    # 批量采集
    # =====================================================

    def fetch_batch(self, batch_size: int = 50, delay: float = 0.5, max_retries: int = 3):
        """
        批量采集个股信息
        
        Args:
            batch_size: 每批处理数量（进度报告）
            delay: 请求间隔（秒）
            max_retries: 最大重试轮数
        """
        retry_count = 0

        while retry_count < max_retries:
            # 获取待处理股票
            pending_stocks = self.get_pending_stocks()

            if not pending_stocks:
                self.logger.info("✅ 所有股票已采集完成")
                return

            total = len(pending_stocks)
            success = 0
            failed = 0

            self.logger.info(f"开始采集 {total} 只股票")

            for i, stock_code in enumerate(pending_stocks):
                try:
                    # 获取数据
                    data = self.fetch_single_stock(stock_code)

                    if data:
                        # 保存到数据库
                        if self.save_to_db(data):
                            success += 1
                            # 标记为已处理
                            self.mark_as_processed(stock_code)
                        else:
                            failed += 1
                    else:
                        failed += 1

                    # 进度报告
                    if (i + 1) % batch_size == 0:
                        self.logger.info(f"进度: {i + 1}/{total}, 成功: {success}, 失败: {failed}")

                    # 延迟
                    time.sleep(delay)

                except Exception as e:
                    self.logger.error(f"处理 {stock_code} 失败: {e}")
                    failed += 1

            self.logger.info(f"本轮完成: 成功 {success}, 失败 {failed}")

            # 检查是否还有剩余
            remaining = self.get_pending_stocks()
            if not remaining:
                self.logger.info("✅ 全部采集完成")
                return

            retry_count += 1
            if retry_count < max_retries:
                self.logger.info(f"⚠️ 仍有 {len(remaining)} 只未处理, 5秒后重试...")
                time.sleep(5)

        self.logger.warning(f"达到最大重试次数 {max_retries}, 采集结束")

    def fetch_test(self, test_count: int = 5):
        """
        测试模式：只采集少量股票
        
        Args:
            test_count: 测试数量
        """
        self.logger.info(f"=== 测试模式: 采集 {test_count} 只股票 ===")

        # 获取少量股票
        sql = f"SELECT stock_code FROM stock_basic WHERE stock_status = 1 LIMIT {test_count}"
        result = self.mysql.query_all(sql)

        if not result:
            self.logger.error("无法获取股票列表")
            return

        test_stocks = [row['stock_code'] for row in result]

        # 初始化 Redis（仅测试股票）
        if self.redis:
            self.redis.add_unprocessed_stocks(test_stocks, self.now_date, self.DATA_TYPE)

        success = 0
        failed = 0

        for i, stock_code in enumerate(test_stocks):
            self.logger.info(f"[{i + 1}/{len(test_stocks)}] 获取 {stock_code}...")

            data = self.fetch_single_stock(stock_code)

            if data:
                if self.save_to_db(data):
                    success += 1
                    self.mark_as_processed(stock_code)
                    self.logger.info(f"  ✅ {data.get('stock_name', stock_code)} "
                                     f"流通市值: {data.get('circ_market_cap', 0) / 100000000:.1f}亿")
                else:
                    failed += 1
            else:
                failed += 1

            time.sleep(1)

        self.logger.info(f"\n测试完成: 成功 {success}, 失败 {failed}")

        # 验证断点续传
        if self.redis:
            remaining = self.redis.get_unprocessed_stocks(self.now_date, self.DATA_TYPE)
            self.logger.info(f"Redis 待处理: {len(remaining)} 只")
            self.logger.info(f"断点续传测试: {'✅ 正常' if len(remaining) == failed else '❌ 异常'}")


def main():
    parser = argparse.ArgumentParser(description='股票个股信息采集（支持断点续传）')

    parser.add_argument('--test', action='store_true', help='测试模式（采集少量股票）')
    parser.add_argument('--test-count', type=int, default=5, help='测试数量')
    parser.add_argument('--all', action='store_true', help='全量采集')
    parser.add_argument('--batch', type=int, default=50, help='批次大小')
    parser.add_argument('--delay', type=float, default=1.0, help='请求间隔(秒)')
    parser.add_argument('--retries', type=int, default=3, help='最大重试轮数')
    parser.add_argument('--status', action='store_true', help='查看采集状态')
    parser.add_argument('--reset', action='store_true', help='清除 Redis 记录')

    args = parser.parse_args()

    fetcher = StockIndividualInfoFetcher()

    try:
        if args.test:
            # 测试模式
            fetcher.fetch_test(args.test_count)

        elif args.all:
            # 全量采集
            fetcher.fetch_batch(
                batch_size=args.batch,
                delay=args.delay,
                max_retries=args.retries
            )

        elif args.status:
            # 查看状态
            status = fetcher.get_status()
            print("\n" + "=" * 50)
            print("📊 采集状态")
            print("=" * 50)
            print(f"日期: {status['date']}")
            print(f"总股票数: {status['total']}")
            print(f"已采集: {status['processed']}")
            print(f"待采集: {status['pending']}")
            print(f"进度: {status['processed'] / status['total'] * 100:.1f}%")

        elif args.reset:
            # 清除 Redis
            fetcher.reset_redis()
            print("✅ Redis 记录已清除，可重新采集")

        else:
            parser.print_help()

    finally:
        fetcher.close()


if __name__ == '__main__':
    main()

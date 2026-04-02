#!/usr/bin/env python3
"""
股本数据更新脚本

数据源：AkShare stock_individual_info_em
存储：stock_profit_data 表（更新 total_share, liqa_share）

Author: Xiao Luo
Date: 2026-04-02
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import pandas as pd
import akshare as ak
from datetime import datetime
from src.utils.mysql_tool import MySQLUtil
from logs.logger import LogManager


class MarketCapUpdater:
    """股本数据更新器"""
    
    def __init__(self):
        self.mysql = MySQLUtil()
        self.mysql.connect()
        self.logger = LogManager.get_logger("market_cap_updater")
    
    def close(self):
        self.mysql.close()
    
    def fetch_stock_capital(self, stock_code: str, retry: int = 3) -> dict:
        """
        从 AkShare 获取股本数据
        
        Returns:
            {
                'total_share': float,  # 总股本
                'liqa_share': float,   # 流通股本
                'total_mv': float,     # 总市值
                'circ_mv': float       # 流通市值
            }
        """
        for i in range(retry):
            try:
                df = ak.stock_individual_info_em(symbol=stock_code)
                
                result = {}
                for _, row in df.iterrows():
                    item = row['item']
                    value = row['value']
                    
                    if item == '总股本':
                        result['total_share'] = float(value)
                    elif item == '流通股':
                        result['liqa_share'] = float(value)
                    elif item == '总市值':
                        result['total_mv'] = float(value) / 100000000  # 转为亿
                    elif item == '流通市值':
                        result['circ_mv'] = float(value) / 100000000  # 转为亿
                
                return result
                
            except Exception as e:
                self.logger.warning(f"获取 {stock_code} 股本失败 (尝试 {i+1}/{retry}): {e}")
                time.sleep(1)
        
        return None
    
    def update_single_stock(self, stock_code: str) -> bool:
        """更新单只股票的股本数据"""
        
        # 获取股本数据
        capital_data = self.fetch_stock_capital(stock_code)
        
        if not capital_data:
            self.logger.error(f"无法获取 {stock_code} 的股本数据")
            return False
        
        # 检查是否已有记录
        check_sql = """
            SELECT id FROM stock_profit_data 
            WHERE stock_code = %s 
            ORDER BY statistic_date DESC 
            LIMIT 1
        """
        existing = self.mysql.query_one(check_sql, (stock_code,))
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        if existing:
            # 更新现有记录
            update_sql = """
                UPDATE stock_profit_data 
                SET total_share = %s, liqa_share = %s, update_time = NOW()
                WHERE id = %s
            """
            self.mysql.execute(update_sql, (
                capital_data['total_share'],
                capital_data['liqa_share'],
                existing['id']
            ))
            self.logger.info(f"更新 {stock_code} 股本数据")
        else:
            # 插入新记录
            insert_sql = """
                INSERT INTO stock_profit_data 
                (stock_code, statistic_date, total_share, liqa_share, create_time, update_time)
                VALUES (%s, %s, %s, %s, NOW(), NOW())
            """
            self.mysql.execute(insert_sql, (
                stock_code,
                today,
                capital_data['total_share'],
                capital_data['liqa_share']
            ))
            self.logger.info(f"新增 {stock_code} 股本数据")
        
        return True
    
    def update_all_stocks(self, batch_size: int = 50, delay: float = 0.5):
        """
        批量更新所有股票的股本数据
        
        Args:
            batch_size: 每批处理数量
            delay: 请求间隔（秒）
        """
        # 获取所有股票代码
        sql = "SELECT stock_code, stock_name FROM stock_basic WHERE stock_status = 1"
        stocks = self.mysql.query_all(sql)
        
        if not stocks:
            self.logger.error("无法获取股票列表")
            return
        
        total = len(stocks)
        success = 0
        failed = 0
        
        self.logger.info(f"开始更新 {total} 只股票的股本数据")
        
        for i, stock in enumerate(stocks):
            stock_code = stock['stock_code']
            stock_name = stock['stock_name']
            
            try:
                result = self.update_single_stock(stock_code)
                if result:
                    success += 1
                else:
                    failed += 1
                
                # 进度报告
                if (i + 1) % batch_size == 0:
                    self.logger.info(f"进度: {i+1}/{total}, 成功: {success}, 失败: {failed}")
                
                # 延迟避免请求过快
                time.sleep(delay)
                
            except Exception as e:
                self.logger.error(f"更新 {stock_code} {stock_name} 失败: {e}")
                failed += 1
        
        self.logger.info(f"更新完成: 总计 {total}, 成功 {success}, 失败 {failed}")


def main():
    """主函数"""
    updater = MarketCapUpdater()
    
    # 测试单只股票
    print("测试获取中兴通讯股本数据...")
    data = updater.fetch_stock_capital('000063')
    if data:
        print(f"总股本: {data['total_share']/100000000:.2f}亿股")
        print(f"流通股本: {data['liqa_share']/100000000:.2f}亿股")
        print(f"总市值: {data['total_mv']:.2f}亿")
        print(f"流通市值: {data['circ_mv']:.2f}亿")
    
    updater.close()


if __name__ == '__main__':
    main()
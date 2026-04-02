#!/usr/bin/env python3
"""
股票财务数据采集脚本（带断点续传）

数据源: AkShare - stock_financial_abstract
功能: 获取财务摘要数据（80个指标）
特性: 支持断点续传，异常中断后可继续采集

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
from src.utils.redis_tool import RedisUtil
from logs.logger import LogManager


class FinancialDataFetcher:
    """财务数据采集器"""
    
    DATA_TYPE = 'financial_summary'
    
    def __init__(self):
        self.mysql = MySQLUtil()
        self.mysql.connect()
        self.redis = RedisUtil() if RedisUtil else None
        self.logger = LogManager.get_logger("financial_fetcher")
        self.now_date = datetime.now().strftime('%Y-%m-%d')
    
    def close(self):
        self.mysql.close()
    
    def fetch_single_stock(self, stock_code: str) -> dict:
        """获取单只股票的财务数据"""
        try:
            df = ak.stock_financial_abstract(symbol=stock_code)
            
            if df.empty:
                return None
            
            # 解析数据：每行是一个指标，列是不同报告期
            results = []
            cols = df.columns.tolist()
            date_cols = [c for c in cols if c not in ['选项', '指标']]
            
            for date_col in date_cols:
                # 提取该报告期的所有指标
                row_data = {'report_date': date_col, 'stock_code': stock_code}
                
                for _, row in df.iterrows():
                    indicator = row['指标']
                    value = row[date_col]
                    
                    # 映射指标名到字段名（只使用实际存在的指标）
                    field_map = {
                        '归母净利润': 'parent_net_profit',
                        '净利润': 'net_profit',
                        '扣非净利润': 'deduct_net_profit',
                        '营业总收入': 'operating_income',
                        '营业成本': 'operating_cost',
                        '股东权益合计(净资产)': 'net_assets',
                        '经营现金流量净额': 'operating_cash_flow',
                        '基本每股收益': 'eps_basic',
                        '每股净资产': 'bvps',
                        '每股现金流': 'cfps',
                        '净资产收益率(ROE)': 'roe',
                        '总资产报酬率(ROA)': 'roa',
                        '毛利率': 'gross_margin',
                        '销售净利率': 'net_margin',
                        '资产负债率': 'debt_ratio',
                    }
                    
                    if indicator in field_map:
                        field_name = field_map[indicator]
                        try:
                            row_data[field_name] = float(value) if value else None
                        except:
                            row_data[field_name] = None
                
                results.append(row_data)
            
            return results
            
        except Exception as e:
            self.logger.error(f"获取 {stock_code} 财务数据失败: {e}")
            return None
    
    def save_to_db(self, data_list: list) -> int:
        """保存到数据库"""
        if not data_list:
            return 0
        
        sql = """
            INSERT INTO stock_financial_summary 
            (stock_code, report_date, net_profit, parent_net_profit, deduct_net_profit,
             operating_income, roe, roa, gross_margin, net_margin,
             debt_ratio, eps_basic, bvps, cfps, net_assets, operating_cash_flow)
            VALUES (%(stock_code)s, %(report_date)s, %(net_profit)s, %(parent_net_profit)s,
                    %(deduct_net_profit)s, %(operating_income)s,
                    %(roe)s, %(roa)s, %(gross_margin)s, %(net_margin)s, %(debt_ratio)s,
                    %(eps_basic)s, %(bvps)s, %(cfps)s, %(net_assets)s, %(operating_cash_flow)s)
            ON DUPLICATE KEY UPDATE
                net_profit = VALUES(net_profit),
                parent_net_profit = VALUES(parent_net_profit),
                operating_income = VALUES(operating_income),
                roe = VALUES(roe),
                gross_margin = VALUES(gross_margin),
                update_time = NOW()
        """
        
        import numpy as np
        
        count = 0
        for data in data_list:
            try:
                # 将NaN转换为None
                clean_data = {}
                for key, value in data.items():
                    if isinstance(value, float) and (np.isnan(value) or value is None):
                        clean_data[key] = None
                    else:
                        clean_data[key] = value
                
                self.mysql.execute(sql, clean_data)
                count += 1
            except Exception as e:
                self.logger.error(f"保存数据失败: {e}")
        
        return count
    
    def get_pending_stocks(self) -> list:
        """获取待采集股票列表（支持断点续传）"""
        if self.redis:
            pending = self.redis.get_unprocessed_stocks(self.now_date, self.DATA_TYPE)
            if pending:
                self.logger.info(f"📌 Redis断点续传: {len(pending)}只待处理")
                return pending
        
        # 从数据库获取全部股票
        sql = "SELECT stock_code FROM stock_basic WHERE stock_status = 1"
        result = self.mysql.query_all(sql)
        
        if not result:
            return []
        
        stock_list = [row['stock_code'] for row in result]
        
        # 初始化Redis
        if self.redis:
            self.redis.add_unprocessed_stocks(stock_list, self.now_date, self.DATA_TYPE)
            self.logger.info(f"✅ Redis初始化: {len(stock_list)}只股票")
        
        return stock_list
    
    def mark_as_processed(self, stock_code: str):
        """标记为已处理"""
        if self.redis:
            self.redis.remove_unprocessed_stocks([stock_code], self.now_date, self.DATA_TYPE)
    
    def test_fetch(self, test_count: int = 5):
        """测试模式：采集少量股票"""
        self.logger.info(f"=== 测试模式: 采集{test_count}只股票 ===")
        
        # 获取测试股票
        sql = f"SELECT stock_code FROM stock_basic WHERE stock_status = 1 LIMIT {test_count}"
        result = self.mysql.query_all(sql)
        
        if not result:
            self.logger.error("无法获取股票列表")
            return
        
        test_stocks = [row['stock_code'] for row in result]
        
        success = 0
        failed = 0
        
        for i, stock_code in enumerate(test_stocks):
            self.logger.info(f"[{i+1}/{len(test_stocks)}] 获取 {stock_code}...")
            
            data_list = self.fetch_single_stock(stock_code)
            
            if data_list:
                count = self.save_to_db(data_list)
                if count > 0:
                    success += 1
                    self.logger.info(f"  ✅ 保存{count}期数据")
                else:
                    failed += 1
            else:
                failed += 1
            
            time.sleep(1)
        
        self.logger.info(f"\n测试完成: 成功{success}, 失败{failed}")
    
    def fetch_all(self, batch_size: int = 50, delay: float = 0.5):
        """全量采集"""
        self.logger.info("=== 开始全量采集财务数据 ===")
        
        pending = self.get_pending_stocks()
        
        if not pending:
            self.logger.info("✅ 所有股票已采集完成")
            return
        
        total = len(pending)
        success = 0
        failed = 0
        
        for i, stock_code in enumerate(pending):
            try:
                data_list = self.fetch_single_stock(stock_code)
                
                if data_list:
                    count = self.save_to_db(data_list)
                    if count > 0:
                        success += 1
                        self.mark_as_processed(stock_code)
                else:
                    failed += 1
                
                if (i + 1) % batch_size == 0:
                    self.logger.info(f"进度: {i+1}/{total}, 成功{success}, 失败{failed}")
                
                time.sleep(delay)
                
            except Exception as e:
                self.logger.error(f"处理 {stock_code} 失败: {e}")
                failed += 1
        
        self.logger.info(f"采集完成: 总计{total}, 成功{success}, 失败{failed}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='财务数据采集')
    parser.add_argument('--test', action='store_true', help='测试模式')
    parser.add_argument('--test-count', type=int, default=5, help='测试数量')
    parser.add_argument('--all', action='store_true', help='全量采集')
    parser.add_argument('--batch', type=int, default=50, help='批次大小')
    
    args = parser.parse_args()
    
    fetcher = FinancialDataFetcher()
    
    try:
        if args.test:
            fetcher.test_fetch(args.test_count)
        elif args.all:
            fetcher.fetch_all(batch_size=args.batch)
        else:
            fetcher.test_fetch(5)
    finally:
        fetcher.close()


if __name__ == '__main__':
    main()
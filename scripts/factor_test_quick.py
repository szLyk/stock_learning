#!/usr/bin/env python3
"""
因子生成测试版 - 只处理100只股票验证逻辑
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from logs.logger import LogManager
from src.utils.mysql_tool import MySQLUtil


class FactorGeneratorTest:
    """测试版因子生成器"""
    
    def __init__(self):
        self.mysql = MySQLUtil()
        self.mysql.connect()
        self.logger = LogManager.get_logger("factor_test")
    
    def run_test(self, limit=100):
        """测试运行，只处理 limit 只股票"""
        
        self.logger.info(f"测试运行，处理 {limit} 只股票")
        
        # 1. 获取最新交易日
        sql = "SELECT MAX(stock_date) as d FROM stock_history_date_price WHERE tradestatus = 1"
        result = self.mysql.query_one(sql)
        latest_date = result['d']
        self.logger.info(f"最新交易日: {latest_date}")
        
        # 2. 获取最新价格数据（只取100只）
        sql = f"""
        SELECT 
            stock_code,
            close_price,
            rolling_p as pe_ttm,
            pb_ratio,
            turn as turnover_rate
        FROM stock_history_date_price
        WHERE stock_date = '{latest_date}'
          AND tradestatus = 1
          AND rolling_p > 0
          AND pb_ratio > 0
        LIMIT {limit}
        """
        price_df = pd.DataFrame(self.mysql.query_all(sql))
        self.logger.info(f"获取 {len(price_df)} 只股票价格数据")
        
        if price_df.empty:
            self.logger.error("无数据")
            return
        
        # 3. 计算因子得分
        # PE得分（越小越好）
        pe_mean = price_df['pe_ttm'].mean()
        pe_std = price_df['pe_ttm'].std()
        price_df['pe_score'] = 100 * (price_df['pe_ttm'].max() - price_df['pe_ttm']) / \
                               (price_df['pe_ttm'].max() - price_df['pe_ttm'].min())
        
        # PB得分（越小越好）
        price_df['pb_score'] = 100 * (price_df['pb_ratio'].max() - price_df['pb_ratio']) / \
                               (price_df['pb_ratio'].max() - price_df['pb_ratio'].min())
        
        # 价值得分
        price_df['value_score'] = price_df['pe_score'] * 0.6 + price_df['pb_score'] * 0.4
        
        # 换手率得分（适中最好）
        price_df['volume_score'] = 100 - abs(price_df['turnover_rate'] - 7.5) * 5
        price_df['volume_score'] = price_df['volume_score'].clip(0, 100)
        
        # 综合得分（简化版：价值70% + 成交量30%）
        price_df['total_score'] = price_df['value_score'] * 0.7 + price_df['volume_score'] * 0.3
        price_df['total_rank'] = price_df['total_score'].rank(ascending=False, method='min').astype(int)
        
        # 4. 输出结果
        print("\n=== 因子打分测试结果 ===")
        print(price_df[['stock_code', 'pe_ttm', 'pb_ratio', 'pe_score', 'pb_score', 
                       'value_score', 'volume_score', 'total_score', 'total_rank']]
              .sort_values('total_rank')
              .to_string(index=False))
        
        self.mysql.close()
        return price_df


if __name__ == '__main__':
    test = FactorGeneratorTest()
    test.run_test(limit=100)
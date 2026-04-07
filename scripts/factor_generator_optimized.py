#!/usr/bin/env python3
"""
优化版因子生成脚本 - 修正查询性能问题
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from logs.logger import LogManager
from src.utils.mysql_tool import MySQLUtil


class OptimizedFactorGenerator:
    """优化版因子生成器"""
    
    def __init__(self):
        self.mysql = MySQLUtil()
        self.mysql.connect()
        self.logger = LogManager.get_logger("factor_opt")
    
    def run(self, limit=500):
        """
        执行因子计算
        :param limit: 处理股票数量（测试时可限制，生产环境去掉）
        """
        
        self.logger.info(f"开始因子计算，处理 {limit} 只股票")
        
        # 1. 获取最新交易日（不用 WHERE 条件）
        sql = "SELECT MAX(stock_date) as d FROM stock_history_date_price"
        result = self.mysql.query_one(sql)
        latest_date = result['d']
        self.logger.info(f"最新交易日: {latest_date}")
        
        # 2. 获取最新价格数据
        # 优化：先获取股票代码，再批量获取数据
        sql = f"""
        SELECT 
            stock_code,
            close_price,
            rolling_p as pe_ttm,
            pb_ratio,
            turn as turnover_rate,
            trading_volume,
            high_price,
            low_price
        FROM stock_history_date_price
        WHERE stock_date = '{latest_date}'
          AND rolling_p > 0
          AND rolling_p < 200
          AND pb_ratio > 0
          AND pb_ratio < 20
          AND close_price > 1
        LIMIT {limit}
        """
        self.logger.info("获取价格数据...")
        price_df = pd.DataFrame(self.mysql.query_all(sql))
        self.logger.info(f"获取 {len(price_df)} 只股票")
        
        # 转换数值类型（Decimal -> float）
        numeric_cols = ['close_price', 'pe_ttm', 'pb_ratio', 'turnover_rate', 
                        'trading_volume', 'high_price', 'low_price']
        for col in numeric_cols:
            if col in price_df.columns:
                price_df[col] = price_df[col].astype(float)
        
        if price_df.empty:
            self.logger.error("无有效数据")
            self.mysql.close()
            return
        
        # 3. 计算因子得分
        self.logger.info("计算因子得分...")
        
        # PE得分（越小越好，但限制范围）
        pe_max = price_df['pe_ttm'].quantile(0.95)  # 用分位数避免极端值
        pe_min = price_df['pe_ttm'].quantile(0.05)
        price_df['pe_score'] = 100 * (pe_max - price_df['pe_ttm']) / (pe_max - pe_min + 0.01)
        price_df['pe_score'] = price_df['pe_score'].clip(0, 100)
        
        # PB得分（越小越好）
        pb_max = price_df['pb_ratio'].quantile(0.95)
        pb_min = price_df['pb_ratio'].quantile(0.05)
        price_df['pb_score'] = 100 * (pb_max - price_df['pb_ratio']) / (pb_max - pb_min + 0.01)
        price_df['pb_score'] = price_df['pb_score'].clip(0, 100)
        
        # 价值得分
        price_df['value_score'] = price_df['pe_score'] * 0.6 + price_df['pb_score'] * 0.4
        
        # 换手率得分（5-10% 最佳）
        price_df['volume_score'] = 100 - abs(price_df['turnover_rate'].fillna(5) - 7.5) * 10
        price_df['volume_score'] = price_df['volume_score'].clip(0, 100)
        
        # 波动得分（日内振幅越小越好）
        price_df['daily_range'] = (price_df['high_price'] - price_df['low_price']) / price_df['close_price'] * 100
        range_max = price_df['daily_range'].quantile(0.95)
        range_min = price_df['daily_range'].quantile(0.05)
        price_df['volatility_score'] = 100 * (range_max - price_df['daily_range']) / (range_max - range_min + 0.01)
        price_df['volatility_score'] = price_df['volatility_score'].clip(0, 100)
        
        # 综合得分
        price_df['total_score'] = (
            price_df['value_score'] * 0.35 +
            price_df['volume_score'] * 0.25 +
            price_df['volatility_score'] * 0.20 +
            50 * 0.20  # 其他因子暂时用基准值
        )
        price_df['total_rank'] = price_df['total_score'].rank(ascending=False, method='min').astype(int)
        
        # 4. 输出结果
        print("\n" + "="*60)
        print(f"因子打分结果（最新日期：{latest_date}）")
        print("="*60)
        
        top20 = price_df.nlargest(20, 'total_score')
        print(top20[['stock_code', 'pe_ttm', 'pb_ratio', 'turnover_rate', 
                    'pe_score', 'pb_score', 'value_score', 'volume_score',
                    'total_score', 'total_rank']].to_string(index=False))
        
        # 5. 保存到数据库
        self.logger.info("保存到数据库...")
        
        # 添加日期列
        price_df['stock_date'] = latest_date
        
        # 选择保存的列
        save_cols = ['stock_code', 'stock_date', 
                     'pe_ttm', 'pb_ratio', 'pe_score', 'pb_score', 'value_score',
                     'turnover_rate', 'volume_score',
                     'daily_range', 'volatility_score',
                     'total_score', 'total_rank']
        
        save_df = price_df[save_cols].copy()
        save_df = save_df.fillna(0)
        
        # 添加权重列
        save_df['value_weight'] = 0.35
        save_df['volume_weight'] = 0.25
        save_df['volatility_weight'] = 0.20
        
        try:
            self.mysql.batch_insert_or_update(
                table_name='stock_factor_score',
                df=save_df,
                unique_keys=['stock_code', 'stock_date']
            )
            self.logger.info(f"保存成功：{len(save_df)} 条记录")
        except Exception as e:
            self.logger.error(f"保存失败：{e}")
        
        self.mysql.close()
        return price_df


if __name__ == '__main__':
    gen = OptimizedFactorGenerator()
    gen.run(limit=500)  # 测试时处理500只，生产环境去掉 LIMIT
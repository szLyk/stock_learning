#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票流通市值估算脚本（批量优化版）

优化策略：
    1. SQL层面聚合计算，避免逐条查询
    2. 批量插入，减少数据库交互
    3. 分批处理，避免内存溢出

Author: Xiao Luo
Date: 2026-04-03
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.utils.mysql_tool import MySQLUtil
from logs.logger import LogManager


class MarketCapEstimatorOptimized:
    """流通市值估算器（批量优化版）"""
    
    def __init__(self, batch_size: int = 500):
        self.mysql = MySQLUtil()
        self.mysql.connect()
        self.logger = LogManager.get_logger("market_cap_estimator")
        self.batch_size = batch_size
    
    def close(self):
        self.mysql.close()
    
    def estimate_all_batch(self):
        """批量估算所有股票（SQL层面聚合）"""
        self.logger.info("=" * 60)
        self.logger.info("开始批量估算流通市值")
        self.logger.info("=" * 60)
        
        # 步骤1: 在SQL层面完成聚合计算
        self.logger.info("\n[步骤1] SQL聚合计算...")
        
        sql = '''
            SELECT 
                stock_code,
                AVG(trading_volume) as avg_volume,
                AVG(turn) as avg_turn,
                AVG(close_price) as avg_price,
                COUNT(*) as sample_days,
                STDDEV(turn) as turn_std
            FROM stock_history_date_price
            WHERE stock_date >= DATE_SUB(CURDATE(), INTERVAL 90 DAY)
              AND stock_date <= CURDATE()
              AND tradestatus = 1
              AND turn > 0.1
              AND turn < 50
              AND trading_volume > 0
              AND close_price > 0
            GROUP BY stock_code
            HAVING COUNT(*) >= 10
        '''
        
        data = self.mysql.query_all(sql)
        
        if not data:
            self.logger.error("无法获取数据")
            return
        
        self.logger.info(f"获取到 {len(data)} 只股票的聚合数据")
        
        # 步骤2: 转为DataFrame计算
        self.logger.info("\n[步骤2] 计算流通市值...")
        
        df = pd.DataFrame(data)
        
        df['avg_volume'] = pd.to_numeric(df['avg_volume'], errors='coerce')
        df['avg_turn'] = pd.to_numeric(df['avg_turn'], errors='coerce')
        df['avg_price'] = pd.to_numeric(df['avg_price'], errors='coerce')
        df['turn_std'] = pd.to_numeric(df['turn_std'], errors='coerce')
        
        # 计算流通市值
        # 流通股本 = 成交量(股) / 换手率(%) × 100
        # 流通市值 = 流通股本 × 价格
        df['circ_share_est'] = df['avg_volume'] / df['avg_turn'] * 100
        df['circ_cap_est'] = df['circ_share_est'] * df['avg_price']
        df['circ_cap_yi'] = df['circ_cap_est'] / 100000000
        
        # 市值分组
        def classify_cap(cap):
            if pd.isna(cap): return '未知'
            elif cap < 50: return '小盘'
            elif cap < 200: return '中盘'
            else: return '大盘'
        
        df['cap_group'] = df['circ_cap_yi'].apply(classify_cap)
        
        # 数据质量判断
        def quality(row):
            if row['sample_days'] < 20:
                return 2
            elif row['turn_std'] and row['turn_std'] > row['avg_turn'] * 0.5:
                return 2
            elif row['avg_turn'] < 0.5 or row['avg_turn'] > 20:
                return 2
            else:
                return 1
        
        df['data_quality'] = df.apply(quality, axis=1)
        
        # 过滤异常值
        df = df[(df['circ_cap_yi'] > 5) & (df['circ_cap_yi'] < 50000)]
        
        self.logger.info(f"有效估算: {len(df)} 只")
        
        # 步骤3: 批量插入数据库
        self.logger.info("\n[步骤3] 批量保存到数据库...")
        
        calc_date = datetime.now().strftime('%Y-%m-%d')
        success = 0
        failed = 0
        
        total = len(df)
        
        for i in range(0, total, self.batch_size):
            batch = df.iloc[i:i+self.batch_size]
            
            # 构建批量插入SQL
            values = []
            for _, row in batch.iterrows():
                val = f"('{row['stock_code']}', '{calc_date}', " \
                      f"{row['avg_volume']:.2f}, {row['avg_turn']:.4f}, " \
                      f"{row['avg_price']:.4f}, {row['circ_share_est']:.2f}, " \
                      f"{row['circ_cap_est']:.2f}, {row['circ_cap_yi']:.2f}, " \
                      f"'{row['cap_group']}', {int(row['sample_days'])}, " \
                      f"{int(row['data_quality'])})"
                values.append(val)
            
            sql = f'''
                INSERT INTO stock_market_cap_estimated 
                (stock_code, calc_date, avg_volume, avg_turn, avg_price,
                 circ_share_est, circ_cap_est, circ_cap_yi, cap_group, 
                 sample_days, data_quality)
                VALUES {','.join(values)}
                ON DUPLICATE KEY UPDATE 
                    avg_volume = VALUES(avg_volume),
                    avg_turn = VALUES(avg_turn),
                    avg_price = VALUES(avg_price),
                    circ_share_est = VALUES(circ_share_est),
                    circ_cap_est = VALUES(circ_cap_est),
                    circ_cap_yi = VALUES(circ_cap_yi),
                    cap_group = VALUES(cap_group),
                    sample_days = VALUES(sample_days),
                    data_quality = VALUES(data_quality),
                    update_time = NOW()
            '''
            
            try:
                self.mysql.execute(sql)
                success += len(batch)
            except Exception as e:
                self.logger.error(f"批次 {i//self.batch_size + 1} 失败: {e}")
                failed += len(batch)
            
            # 进度报告
            if (i + self.batch_size) % 2000 == 0 or i + self.batch_size >= total:
                self.logger.info(f"进度: {min(i+self.batch_size, total)}/{total}")
        
        # 步骤4: 统计结果
        self.logger.info("\n[步骤4] 统计结果...")
        
        summary = df.groupby('cap_group').agg({
            'stock_code': 'count',
            'circ_cap_yi': 'mean'
        }).reset_index()
        
        self.logger.info("\n" + "=" * 60)
        self.logger.info("市值分布统计")
        self.logger.info("=" * 60)
        
        for _, row in summary.iterrows():
            self.logger.info(f"{row['cap_group']}: {row['stock_code']}只, 平均{row['circ_cap_yi']:.0f}亿")
        
        self.logger.info("\n" + "-" * 60)
        self.logger.info(f"总计: 成功 {success}, 失败 {failed}")
        self.logger.info("=" * 60)
        
        return {
            'total': total,
            'success': success,
            'failed': failed,
            'summary': summary.to_dict('records')
        }
    
    def get_status(self) -> dict:
        """获取状态"""
        # 总股票数
        sql1 = '''
            SELECT COUNT(DISTINCT stock_code) as cnt 
            FROM stock_history_date_price 
            WHERE stock_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
        '''
        total = self.mysql.query_one(sql1)
        
        # 已估算数
        sql2 = '''
            SELECT COUNT(*) as cnt 
            FROM stock_market_cap_estimated 
            WHERE calc_date = CURDATE()
        '''
        estimated = self.mysql.query_one(sql2)
        
        # 分组统计
        sql3 = '''
            SELECT cap_group, COUNT(*) as cnt, AVG(circ_cap_yi) as avg_cap
            FROM stock_market_cap_estimated
            WHERE calc_date = CURDATE()
            GROUP BY cap_group
            ORDER BY 
                CASE cap_group 
                    WHEN '小盘' THEN 1 
                    WHEN '中盘' THEN 2 
                    WHEN '大盘' THEN 3 
                    ELSE 4 
                END
        '''
        groups = self.mysql.query_all(sql3)
        
        return {
            'total_stocks': total['cnt'] if total else 0,
            'estimated': estimated['cnt'] if estimated else 0,
            'groups': groups,
        }


def main():
    parser = argparse.ArgumentParser(description='股票流通市值估算（批量优化版）')
    parser.add_argument('--all', action='store_true', help='估算全部股票')
    parser.add_argument('--batch', type=int, default=500, help='批次大小')
    parser.add_argument('--status', action='store_true', help='查看状态')
    
    args = parser.parse_args()
    
    estimator = MarketCapEstimatorOptimized(batch_size=args.batch)
    
    try:
        if args.all:
            estimator.estimate_all_batch()
            
        elif args.status:
            status = estimator.get_status()
            print("\n" + "=" * 50)
            print("📊 市值估算状态")
            print("=" * 50)
            print(f"日期: {datetime.now().strftime('%Y-%m-%d')}")
            print(f"总股票数: {status['total_stocks']}")
            print(f"已估算: {status['estimated']}")
            
            if status['total_stocks'] > 0:
                pct = status['estimated'] / status['total_stocks'] * 100
                print(f"进度: {pct:.1f}%")
            
            if status['groups']:
                print("\n市值分布:")
                for g in status['groups']:
                    print(f"  {g['cap_group']}: {g['cnt']}只, 平均{g['avg_cap']:.0f}亿")
            
        else:
            parser.print_help()
            
    finally:
        estimator.close()


if __name__ == '__main__':
    main()
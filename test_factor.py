# -*- coding: utf-8 -*-
"""
多因子模型快速测试脚本
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pymysql
import pandas as pd
from datetime import datetime

# 数据库连接
conn = pymysql.connect(
    host='192.168.1.109',
    port=3306,
    user='root',
    password='123456',
    database='stock',
    charset='utf8mb4'
)

print("=" * 60)
print("多因子模型数据测试")
print("=" * 60)

# 1. 测试 PE/PB 数据
print("\n[1/5] 检查 PE/PB 数据...")
sql = """
SELECT stock_code, stock_date, rolling_p as pe_ttm, pb_ratio 
FROM stock_history_date_price 
WHERE stock_date = '2026-03-13' AND rolling_p > 0 
LIMIT 5
"""
df = pd.read_sql(sql, conn)
print(df.to_string())

# 2. 测试财务数据
print("\n[2/5] 检查财务数据 (ROE, 毛利率)...")
sql = """
SELECT stock_code, publish_date, roe_avg, gp_margin, np_margin, eps_ttm 
FROM stock_profit_data 
ORDER BY publish_date DESC 
LIMIT 5
"""
df = pd.read_sql(sql, conn)
print(df.to_string())

# 3. 测试技术指标 (MACD)
print("\n[3/5] 检查 MACD 指标...")
sql = """
SELECT stock_code, stock_date, diff, dea, macd 
FROM date_stock_macd 
WHERE stock_date = '2026-03-13' 
LIMIT 5
"""
df = pd.read_sql(sql, conn)
print(df.to_string())

# 4. 测试 RSI 指标
print("\n[4/5] 检查 RSI 指标...")
sql = """
SELECT stock_code, stock_date, rsi_6, rsi_12, rsi_24 
FROM stock_date_rsi 
WHERE stock_date = '2026-03-13' 
LIMIT 5
"""
df = pd.read_sql(sql, conn)
print(df.to_string())

# 5. 统计各表数据量
print("\n[5/5] 各表数据量统计...")
tables = [
    'stock_history_date_price',
    'stock_profit_data',
    'date_stock_macd',
    'stock_date_rsi',
    'date_stock_moving_average_table',
    'stock_factor_score',
    'stock_capital_flow',
    'stock_analyst_expectation'
]

for table in tables:
    try:
        sql = f"SELECT COUNT(*) as cnt FROM {table}"
        df = pd.read_sql(sql, conn)
        cnt = df['cnt'].iloc[0]
        print(f"  {table}: {cnt:,} 条")
    except Exception as e:
        print(f"  {table}: 表不存在或查询失败")

print("\n" + "=" * 60)
print("测试完成！")
print("=" * 60)

conn.close()

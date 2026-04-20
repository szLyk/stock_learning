#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证申万行业数据准确性
"""

import pymysql
from pymysql.cursors import DictCursor

DB_CONFIG = {
    'host': '192.168.1.128',
    'port': 3306,
    'user': 'root',
    'password': '123456',
    'database': 'stock',
    'charset': 'utf8mb4',
    'cursorclass': DictCursor
}

conn = pymysql.connect(**DB_CONFIG)
cursor = conn.cursor()

print('=== 申万行业数据验证 ===\n')

# 1. 查询总数
cursor.execute('SELECT COUNT(*) as cnt FROM stock_industry_sw')
total = cursor.fetchone()
print(f'总记录数: {total["cnt"]}')

# 2. 查询未知行业
cursor.execute("SELECT COUNT(*) as cnt FROM stock_industry_sw WHERE industry_name LIKE '%未知%'")
unknown = cursor.fetchone()
print(f'未知行业数: {unknown["cnt"]}')

# 3. 查询部分示例数据
cursor.execute('SELECT * FROM stock_industry_sw ORDER BY stock_code LIMIT 10')
samples = cursor.fetchall()
print('\n前10条示例:')
for row in samples:
    print(f'{row["stock_code"]}: {row["industry_name"]} (代码: {row["industry_code"]})')

# 4. 查询行业分布
cursor.execute('SELECT industry_name, COUNT(*) as cnt FROM stock_industry_sw GROUP BY industry_name ORDER BY cnt DESC')
dist = cursor.fetchall()
print(f'\n行业分布（共{len(dist)}个行业）:')
for row in dist:
    print(f'  {row["industry_name"]}: {row["cnt"]}只')

# 5. 验证具体股票（抽样）
cursor.execute("SELECT stock_code, industry_name FROM stock_industry_sw WHERE stock_code IN ('000001', '600519', '000002', '600036')")
samples2 = cursor.fetchall()
print('\n知名股票行业:')
for row in samples2:
    print(f'{row["stock_code"]}: {row["industry_name"]}')

cursor.close()
conn.close()
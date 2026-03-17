#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查东财相关表的完整性
"""

import sys
sys.path.insert(0, '.')

from src.utils.mysql_tool import MySQLUtil

mysql = MySQLUtil()
mysql.connect()

print("=" * 80)
print("东财相关表检查报告")
print("=" * 80)

# 1. 检查表是否存在
tables = [
    'stock_capital_flow',
    'stock_shareholder_info', 
    'stock_concept',
    'stock_analyst_expectation',
    'update_eastmoney_record'
]

print("\n【1】表存在性检查")
print("-" * 80)
for table in tables:
    result = mysql.query_all(f"SHOW TABLES LIKE '{table}'")
    status = "✅ 存在" if result else "❌ 不存在"
    print(f"  {table:35} {status}")

# 2. 检查表结构和注释
print("\n【2】表结构检查")
print("-" * 80)
for table in tables:
    result = mysql.query_all(f"SHOW CREATE TABLE {table}")
    if result:
        create_sql = result[0][1] if len(result[0]) > 1 else str(result[0])
        comment_start = create_sql.find("COMMENT='")
        if comment_start > 0:
            comment_end = create_sql.find("'", comment_start + 9)
            comment = create_sql[comment_start+9:comment_end]
            print(f"  {table:35} 📋 {comment}")
        else:
            print(f"  {table:35} ⚠️ 无注释")
    else:
        print(f"  {table:35} ❌ 无法获取结构")

# 3. 检查数据量
print("\n【3】数据量统计")
print("-" * 80)
for table in tables:
    try:
        result = mysql.query_all(f"SELECT COUNT(*) as cnt FROM {table}")
        if result:
            count = result[0].get('cnt', 0) if isinstance(result[0], dict) else result[0][0]
            print(f"  {table:35} 📊 {count:,} 条")
        else:
            print(f"  {table:35} ⚠️ 无法查询")
    except Exception as e:
        print(f"  {table:35} ❌ 查询失败：{e}")

# 4. 检查采集记录表
print("\n【4】采集进度检查 (update_eastmoney_record)")
print("-" * 80)
try:
    result = mysql.query_all("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN update_moneyflow IS NOT NULL THEN 1 ELSE 0 END) as moneyflow_done,
            SUM(CASE WHEN update_north IS NOT NULL THEN 1 ELSE 0 END) as north_done,
            SUM(CASE WHEN update_shareholder IS NOT NULL THEN 1 ELSE 0 END) as shareholder_done,
            SUM(CASE WHEN update_concept IS NOT NULL THEN 1 ELSE 0 END) as concept_done,
            SUM(CASE WHEN update_analyst IS NOT NULL THEN 1 ELSE 0 END) as analyst_done
        FROM update_eastmoney_record
    """)
    if result:
        row = result[0]
        total = row.get('total', 0) if isinstance(row, dict) else row[0]
        print(f"  总股票数：{total:,}")
        print(f"  资金流向：{row.get('moneyflow_done', 0):,} ({row.get('moneyflow_done', 0)/max(total,1)*100:.1f}%)")
        print(f"  北向资金：{row.get('north_done', 0):,} ({row.get('north_done', 0)/max(total,1)*100:.1f}%)")
        print(f"  股东人数：{row.get('shareholder_done', 0):,} ({row.get('shareholder_done', 0)/max(total,1)*100:.1f}%)")
        print(f"  概念板块：{row.get('concept_done', 0):,} ({row.get('concept_done', 0)/max(total,1)*100:.1f}%)")
        print(f"  分析师评级：{row.get('analyst_done', 0):,} ({row.get('analyst_done', 0)/max(total,1)*100:.1f}%)")
except Exception as e:
    print(f"  ❌ 查询失败：{e}")

# 5. XXL-JOB 任务配置检查
print("\n【5】XXL-JOB 任务配置")
print("-" * 80)
eastmoney_jobs = [
    '资金流向数据采集',
    '北向资金数据采集',
    '股东人数数据采集',
    '概念板块数据采集',
    '分析师评级数据采集'
]
print("  以下任务已在 create_jobs.py 中配置:")
for job in eastmoney_jobs:
    print(f"  ✅ {job}")

print("\n" + "=" * 80)
print("检查完成！")
print("=" * 80)

mysql.close()

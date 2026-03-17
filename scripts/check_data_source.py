#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查数据源替换情况
"""

import os
import re

workspace = '/home/fan/.openclaw/workspace/stock_learning'

print("=" * 80)
print("数据源替换检查报告")
print("=" * 80)

# 1. 检查 XXL-JOB 任务配置
print("\n【1】XXL-JOB 任务配置")
print("-" * 80)

with open(f'{workspace}/xxljob/create_jobs.py', 'r', encoding='utf-8') as f:
    content = f.read()
    
# 检查任务 handler
if 'run_eastmoney_collection' in content:
    print("  ❌ 仍在使用：run_eastmoney_collection")
else:
    print("  ✅ 已移除：run_eastmoney_collection")

if 'run_akshare_collection' in content:
    print("  ✅ 已添加：run_akshare_collection")
else:
    print("  ❌ 未添加：run_akshare_collection")

# 2. 检查执行器
print("\n【2】XXL-JOB 执行器")
print("-" * 80)

executor_files = [
    'xxljob/executor_server_simple.py',
    'xxljob/executor_server.py',
    'xxljob/executor.py'
]

for ef in executor_files:
    path = f'{workspace}/{ef}'
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            ec = f.read()
        has_eastmoney = 'eastmoney' in ec.lower()
        has_akshare = 'akshare' in ec.lower()
        print(f"  {ef}:")
        print(f"    东财引用：{'❌ 有' if has_eastmoney else '✅ 无'}")
        print(f"    AKShare 引用：{'✅ 有' if has_akshare else '❌ 无'}")

# 3. 检查采集脚本
print("\n【3】数据采集脚本")
print("-" * 80)

utils_files = [
    'src/utils/eastmoney_tool.py',
    'src/utils/akshare_fetcher.py'
]

for uf in utils_files:
    path = f'{workspace}/{uf}'
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        print(f"  {uf}: {len(lines)} 行")

# 4. 检查表结构
print("\n【4】数据库表")
print("-" * 80)
print("  以下表需要保留（数据来源已切换为 AKShare）：")
print("    - stock_capital_flow（资金流向）")
print("    - stock_shareholder_info（股东人数）")
print("    - stock_concept（概念板块）")
print("    - stock_analyst_expectation（分析师评级）")

print("\n" + "=" * 80)
print("替换建议：")
print("  1. 修改 xxljob/create_jobs.py - 任务 handler 改为 run_akshare_collection")
print("  2. 修改 xxljob/executor_server_*.py - 执行逻辑调用 AkShareFetcher")
print("  3. 删除或归档 src/utils/eastmoney_tool.py")
print("=" * 80)

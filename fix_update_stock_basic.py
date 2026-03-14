#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复 update_stock_basic 方法
- 添加对新记录表的支持
- 移除 stock_name 为空的记录
"""
import sys
sys.path.insert(0, '/home/fan/.openclaw/workspace/stock_learning')

from src.utils.mysql_tool import MySQLUtil

mysql = MySQLUtil()
mysql.connect()

print('=== 检查 stock_name 为空的记录 ===\n')

# 检查 stock_basic 表
result = mysql.query_all("SELECT COUNT(*) as cnt FROM stock_basic WHERE stock_name IS NULL OR stock_name = ''")
print(f"stock_basic 表中 stock_name 为空的记录：{result[0]['cnt']}")

# 检查 update_stock_record 表
result = mysql.query_all("SELECT COUNT(*) as cnt FROM update_stock_record WHERE stock_name IS NULL OR stock_name = ''")
print(f"update_stock_record 表中 stock_name 为空的记录：{result[0]['cnt']}")

# 检查 stock_performance_update_record 表
result = mysql.query_all("SELECT COUNT(*) as cnt FROM stock_performance_update_record WHERE stock_name IS NULL OR stock_name = ''")
print(f"stock_performance_update_record 表中 stock_name 为空的记录：{result[0]['cnt']}")

# 检查 update_eastmoney_record 表
result = mysql.query_all("SELECT COUNT(*) as cnt FROM update_eastmoney_record WHERE stock_name IS NULL OR stock_name = ''")
print(f"update_eastmoney_record 表中 stock_name 为空的记录：{result[0]['cnt']}")

print('\n=== 清理 stock_name 为空的记录 ===\n')

# 清理 stock_performance_update_record
mysql.execute("DELETE FROM stock_performance_update_record WHERE stock_name IS NULL OR stock_name = ''")
print('✅ 清理 stock_performance_update_record 表中 stock_name 为空的记录')

# 清理 update_eastmoney_record
mysql.execute("DELETE FROM update_eastmoney_record WHERE stock_name IS NULL OR stock_name = ''")
print('✅ 清理 update_eastmoney_record 表中 stock_name 为空的记录')

print('\n=== 从 stock_basic 同步数据到新记录表 ===\n')

# 从 stock_basic 同步到 stock_performance_update_record
mysql.execute("""
INSERT INTO stock_performance_update_record (stock_code, stock_name, market_type)
SELECT stock_code, stock_name, market_type 
FROM stock_basic 
WHERE stock_status = 1 
  AND stock_name IS NOT NULL 
  AND stock_name != ''
ON DUPLICATE KEY UPDATE 
  stock_name = VALUES(stock_name),
  market_type = VALUES(market_type)
""")
print('✅ 同步 stock_basic → stock_performance_update_record')

# 从 stock_basic 同步到 update_eastmoney_record
mysql.execute("""
INSERT INTO update_eastmoney_record (stock_code, stock_name, market_type)
SELECT stock_code, stock_name, market_type 
FROM stock_basic 
WHERE stock_status = 1 
  AND stock_name IS NOT NULL 
  AND stock_name != ''
ON DUPLICATE KEY UPDATE 
  stock_name = VALUES(stock_name),
  market_type = VALUES(market_type)
""")
print('✅ 同步 stock_basic → update_eastmoney_record')

# 验证
print('\n=== 验证结果 ===\n')
result = mysql.query_all("SELECT COUNT(*) as cnt FROM stock_performance_update_record WHERE stock_name IS NOT NULL AND stock_name != ''")
print(f"stock_performance_update_record 表有效记录：{result[0]['cnt']}")

result = mysql.query_all("SELECT COUNT(*) as cnt FROM update_eastmoney_record WHERE stock_name IS NOT NULL AND stock_name != ''")
print(f"update_eastmoney_record 表有效记录：{result[0]['cnt']}")

mysql.close()
print('\n✅ 修复完成！')

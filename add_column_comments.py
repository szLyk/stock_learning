#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
添加字段注释
"""
import sys
sys.path.insert(0, '/home/fan/.openclaw/workspace/stock_learning')

from src.utils.mysql_tool import MySQLUtil

mysql = MySQLUtil()
mysql.connect()

print('=== 添加字段注释 ===\n')

# 字段注释定义
columns = [
    ('id', 'INT AUTO_INCREMENT', '自增主键'),
    ('stock_code', 'VARCHAR(10) NOT NULL', '股票代码'),
    ('stock_name', 'VARCHAR(50) DEFAULT NULL', '股票名称'),
    ('market_type', 'VARCHAR(10) DEFAULT NULL', '市场类型'),
    ('update_moneyflow', 'DATE DEFAULT NULL', '资金流向最后更新日期'),
    ('update_north', 'DATE DEFAULT NULL', '北向资金最后更新日期'),
    ('update_shareholder', 'DATE DEFAULT NULL', '股东人数最后更新日期'),
    ('update_concept', 'DATE DEFAULT NULL', '概念板块最后更新日期'),
    ('update_analyst', 'DATE DEFAULT NULL', '分析师评级最后更新日期'),
    ('create_time', 'DATETIME DEFAULT CURRENT_TIMESTAMP', '创建时间'),
    ('update_time', 'DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP', '更新时间'),
]

for col_name, col_type, comment in columns:
    sql = f"ALTER TABLE update_eastmoney_record MODIFY COLUMN `{col_name}` {col_type} COMMENT '{comment}'"
    try:
        mysql.execute(sql)
        print(f'✅ {col_name}: {comment}')
    except Exception as e:
        print(f'⚠️ {col_name}: {str(e)[:50]}')

# 验证
print('\n=== 验证 ===\n')
result = mysql.query_all('DESC update_eastmoney_record')
has_chinese_count = 0
for row in result:
    field = row['Field']
    comment = row.get('Comment', 'N/A') if isinstance(row, dict) else row[7] if len(row) > 7 else 'N/A'
    has_chinese = any('\u4e00' <= c <= '\u9fff' for c in str(comment))
    if has_chinese:
        has_chinese_count += 1
    status = '✅' if has_chinese else '⚠️'
    print(f'{status} {field}: {comment}')

print(f'\n中文字段注释：{has_chinese_count}/{len(columns)}')

mysql.close()

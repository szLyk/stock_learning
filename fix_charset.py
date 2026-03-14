#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复表中文注释乱码
"""
import sys
sys.path.insert(0, '/home/fan/.openclaw/workspace/stock_learning')

from src.utils.mysql_tool import MySQLUtil

mysql = MySQLUtil()
mysql.connect()

print('=== 执行 SQL 修复脚本 ===\n')

# 读取 SQL 文件
with open('sql/fix_all_tables_charset.sql', 'r', encoding='utf-8') as f:
    sql_content = f.read()

# 分割执行（按 CREATE TABLE 分割）
import re
create_statements = re.findall(r'(DROP TABLE.*?COMMENT=\'[^\']*\');', sql_content, re.DOTALL)

print(f'找到 {len(create_statements)} 个建表语句\n')

for stmt in create_statements:
    try:
        # 提取表名
        match = re.search(r'CREATE TABLE (\w+)', stmt)
        if match:
            table_name = match.group(1)
            mysql.execute(stmt)
            print(f'✅ {table_name}')
    except Exception as e:
        print(f'⚠️  {str(e)[:60]}')

print('\n=== 验证表注释 ===\n')

# 验证
tables_to_check = [
    'update_eastmoney_record',
    'stock_performance_update_record', 
    'stock_capital_flow',
    'stock_analyst_expectation',
    'stock_concept'
]

all_ok = True
for table in tables_to_check:
    result = mysql.query_all(f'SHOW CREATE TABLE {table}')
    if result:
        create_stmt = result[0][1] if isinstance(result[0], tuple) else list(result[0].values())[1]
        # 检查 COMMENT
        import re
        comments = re.findall(r"COMMENT='([^']*)'", create_stmt)
        has_chinese = any('\u4e00' <= c <= '\u9fff' for c in ' '.join(comments))
        status = '✅' if has_chinese else '⚠️'
        print(f'{status} {table}: {len(comments)} 个注释')
        if not has_chinese:
            all_ok = False

mysql.close()

if all_ok:
    print('\n✅ 所有表注释正常！修复完成！')
else:
    print('\n⚠️ 请检查')

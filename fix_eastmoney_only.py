#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单独修复 update_eastmoney_record 表
"""
import sys
sys.path.insert(0, '/home/fan/.openclaw/workspace/stock_learning')

from src.utils.mysql_tool import MySQLUtil

mysql = MySQLUtil()
mysql.connect()

print('=== 修复 update_eastmoney_record ===\n')

# 删除旧表
mysql.execute('DROP TABLE IF EXISTS update_eastmoney_record')
print('✅ 删除旧表')

# 创建新表（分句执行避免语法错误）
mysql.execute("""
CREATE TABLE update_eastmoney_record (
    id INT AUTO_INCREMENT PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    stock_name VARCHAR(50) DEFAULT NULL,
    market_type VARCHAR(10) DEFAULT NULL,
    update_moneyflow DATE DEFAULT NULL,
    update_north DATE DEFAULT NULL,
    update_shareholder DATE DEFAULT NULL,
    update_concept DATE DEFAULT NULL,
    update_analyst DATE DEFAULT NULL,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_stock (stock_code),
    KEY idx_update_moneyflow (update_moneyflow),
    KEY idx_update_north (update_north)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
""")
print('✅ 创建表')

# 添加注释
mysql.execute("ALTER TABLE update_eastmoney_record MODIFY COLUMN id INT COMMENT '自增主键'")
mysql.execute("ALTER TABLE update_eastmoney_record MODIFY COLUMN stock_code VARCHAR(10) COMMENT '股票代码'")
mysql.execute("ALTER TABLE update_eastmoney_record MODIFY COLUMN stock_name VARCHAR(50) COMMENT '股票名称'")
mysql.execute("ALTER TABLE update_eastmoney_record MODIFY COLUMN market_type VARCHAR(10) COMMENT '市场类型'")
mysql.execute("ALTER TABLE update_eastmoney_record MODIFY COLUMN update_moneyflow DATE COMMENT '资金流向最后更新日期'")
mysql.execute("ALTER TABLE update_eastmoney_record MODIFY COLUMN update_north DATE COMMENT '北向资金最后更新日期'")
mysql.execute("ALTER TABLE update_eastmoney_record MODIFY COLUMN update_shareholder DATE COMMENT '股东人数最后更新日期'")
mysql.execute("ALTER TABLE update_eastmoney_record MODIFY COLUMN update_concept DATE COMMENT '概念板块最后更新日期'")
mysql.execute("ALTER TABLE update_eastmoney_record MODIFY COLUMN update_analyst DATE COMMENT '分析师评级最后更新日期'")
mysql.execute("ALTER TABLE update_eastmoney_record COMMENT '东方财富数据采集记录表'")
print('✅ 添加注释')

# 验证
print('\n=== 验证 ===\n')
result = mysql.query_all("SHOW CREATE TABLE update_eastmoney_record")
if result:
    stmt = result[0][1] if isinstance(result[0], tuple) else list(result[0].values())[1]
    import re
    comments = re.findall(r"COMMENT='([^']*)'", stmt)
    print(f'表注释：{comments[-1]}')
    print(f'字段注释数：{len(comments)-1}')
    
    # 检查是否有中文
    has_chinese = any('\u4e00' <= c <= '\u9fff' for c in comments[-1])
    if has_chinese:
        print('\n✅ 中文注释正常！')
    else:
        print('\n⚠️ 可能仍有问题')

mysql.close()

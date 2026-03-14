#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复表中文注释乱码 - 简化版
"""
import sys
sys.path.insert(0, '/home/fan/.openclaw/workspace/stock_learning')

from src.utils.mysql_tool import MySQLUtil

mysql = MySQLUtil()
mysql.connect()

print('=== 修复表注释 ===\n')

# 手动执行每个表的修复
tables_sql = [
    # update_eastmoney_record
    """
    DROP TABLE IF EXISTS update_eastmoney_record;
    CREATE TABLE update_eastmoney_record (
        id INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
        stock_code VARCHAR(10) NOT NULL COMMENT '股票代码',
        stock_name VARCHAR(50) DEFAULT NULL COMMENT '股票名称',
        market_type VARCHAR(10) DEFAULT NULL COMMENT '市场类型',
        update_moneyflow DATE DEFAULT NULL COMMENT '资金流向最后更新日期',
        update_north DATE DEFAULT NULL COMMENT '北向资金最后更新日期',
        update_shareholder DATE DEFAULT NULL COMMENT '股东人数最后更新日期',
        update_concept DATE DEFAULT NULL COMMENT '概念板块最后更新日期',
        update_analyst DATE DEFAULT NULL COMMENT '分析师评级最后更新日期',
        create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
        update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uk_stock (stock_code),
        KEY idx_update_moneyflow (update_moneyflow),
        KEY idx_update_north (update_north)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='东方财富数据采集记录表'
    """,
    
    # stock_performance_update_record  
    """
    DROP TABLE IF EXISTS stock_performance_update_record;
    CREATE TABLE stock_performance_update_record (
        id INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
        stock_code VARCHAR(10) NOT NULL COMMENT '股票代码',
        stock_name VARCHAR(50) DEFAULT NULL COMMENT '股票名称',
        market_type VARCHAR(10) DEFAULT NULL COMMENT '市场类型',
        update_profit_date DATE DEFAULT NULL COMMENT '利润表最后更新日期',
        update_balance_date DATE DEFAULT NULL COMMENT '资产负债表最后更新日期',
        update_cashflow_date DATE DEFAULT NULL COMMENT '现金流量表最后更新日期',
        update_growth_date DATE DEFAULT NULL COMMENT '成长能力最后更新日期',
        update_operation_date DATE DEFAULT NULL COMMENT '运营能力最后更新日期',
        update_dupont_date DATE DEFAULT NULL COMMENT '杜邦分析最后更新日期',
        update_forecast_date DATE DEFAULT NULL COMMENT '业绩预告最后更新日期',
        update_express_date DATE DEFAULT NULL COMMENT '业绩快报最后更新日期',
        update_dividend_date DATE DEFAULT NULL COMMENT '分红送配最后更新日期',
        create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
        update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uk_stock (stock_code),
        KEY idx_update_profit (update_profit_date),
        KEY idx_update_forecast (update_forecast_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='财务数据采集记录表'
    """
]

for i, sql in enumerate(tables_sql):
    try:
        mysql.execute(sql)
        print(f'✅ 表 {i+1} 修复成功')
    except Exception as e:
        print(f'⚠️ 表 {i+1} 失败：{str(e)[:60]}')

print('\n=== 验证 ===\n')

# 验证
result = mysql.query_all("SHOW CREATE TABLE update_eastmoney_record")
if result:
    stmt = result[0][1] if isinstance(result[0], tuple) else list(result[0].values())[1]
    print('update_eastmoney_record:')
    # 提取 COMMENT
    import re
    comments = re.findall(r"COMMENT='([^']*)'", stmt)
    for c in comments[:5]:  # 显示前 5 个
        print(f'  {c}')

result = mysql.query_all("SHOW CREATE TABLE stock_performance_update_record")
if result:
    stmt = result[0][1] if isinstance(result[0], tuple) else list(result[0].values())[1]
    print('\nstock_performance_update_record:')
    comments = re.findall(r"COMMENT='([^']*)'", stmt)
    for c in comments[:5]:
        print(f'  {c}')

mysql.close()
print('\n完成')

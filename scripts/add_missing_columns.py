#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接添加缺失的数据库字段
"""

import mysql.connector

# 数据库配置
config = {
    'host': '192.168.1.109',
    'port': 3306,
    'user': 'root',
    'password': '123456',
    'database': 'stock'
}

# 需要添加的字段
columns_to_add = {
    'stock_balance_data': [
        ('total_assets', 'DECIMAL(20,4) DEFAULT NULL', '总资产'),
        ('total_liabilities', 'DECIMAL(20,4) DEFAULT NULL', '总负债'),
        ('total_equity', 'DECIMAL(20,4) DEFAULT NULL', '股东权益合计'),
        ('capital_reserve', 'DECIMAL(20,4) DEFAULT NULL', '资本公积金'),
        ('surplus_reserve', 'DECIMAL(20,4) DEFAULT NULL', '盈余公积金'),
        ('undistributed_profit', 'DECIMAL(20,4) DEFAULT NULL', '未分配利润'),
        ('current_ratio', 'DECIMAL(10,4) DEFAULT NULL', '流动比率'),
        ('quick_ratio', 'DECIMAL(10,4) DEFAULT NULL', '速动比率'),
        ('cash_ratio', 'DECIMAL(10,4) DEFAULT NULL', '现金比率'),
        ('yoy_liability', 'DECIMAL(10,4) DEFAULT NULL', '负债同比增长率 (%)'),
        ('liability_to_asset', 'DECIMAL(10,4) DEFAULT NULL', '资产负债率 (%)'),
        ('asset_to_equity', 'DECIMAL(10,4) DEFAULT NULL', '资产/权益'),
    ],
    'stock_growth_data': [
        ('revenue_yoy', 'DECIMAL(10,4) DEFAULT NULL', '营业收入同比增长率 (%)'),
        ('operating_profit_yoy', 'DECIMAL(10,4) DEFAULT NULL', '营业利润同比增长率 (%)'),
        ('net_profit_yoy', 'DECIMAL(10,4) DEFAULT NULL', '净利润同比增长率 (%)'),
        ('total_assets_yoy', 'DECIMAL(10,4) DEFAULT NULL', '总资产同比增长率 (%)'),
        ('total_equity_yoy', 'DECIMAL(10,4) DEFAULT NULL', '股东权益同比增长率 (%)'),
        ('yoy_equity', 'DECIMAL(10,4) DEFAULT NULL', '净资产同比增长率 (%)'),
        ('yoy_asset', 'DECIMAL(10,4) DEFAULT NULL', '总资产同比增长率 (%)'),
        ('yoy_ni', 'DECIMAL(10,4) DEFAULT NULL', '净利润同比增长率 (%)'),
        ('yoy_eps_basic', 'DECIMAL(10,4) DEFAULT NULL', '基本 EPS 同比增长率 (%)'),
        ('yoy_pni', 'DECIMAL(10,4) DEFAULT NULL', '归属母公司净利润同比增长率 (%)'),
    ],
    'stock_operation_data': [
        ('inventory_turnover', 'DECIMAL(10,4) DEFAULT NULL', '存货周转率'),
        ('receivables_turnover', 'DECIMAL(10,4) DEFAULT NULL', '应收账款周转率'),
        ('current_assets_turnover', 'DECIMAL(10,4) DEFAULT NULL', '流动资产周转率'),
        ('total_assets_turnover', 'DECIMAL(10,4) DEFAULT NULL', '总资产周转率'),
        ('nr_turn_ratio', 'DECIMAL(10,4) DEFAULT NULL', '营业收入周转率'),
        ('nr_turn_days', 'DECIMAL(10,4) DEFAULT NULL', '营业收入周转天数'),
        ('inv_turn_ratio', 'DECIMAL(10,4) DEFAULT NULL', '存货周转率'),
        ('inv_turn_days', 'DECIMAL(10,4) DEFAULT NULL', '存货周转天数'),
        ('ca_turn_ratio', 'DECIMAL(10,4) DEFAULT NULL', '流动资产周转率'),
        ('asset_turn_ratio', 'DECIMAL(10,4) DEFAULT NULL', '总资产周转率'),
    ],
    'stock_dupont_data': [
        ('roe', 'DECIMAL(10,4) DEFAULT NULL', '净资产收益率 (%)'),
        ('net_profit_margin', 'DECIMAL(10,4) DEFAULT NULL', '销售净利率 (%)'),
        ('asset_turnover', 'DECIMAL(10,4) DEFAULT NULL', '总资产周转率'),
        ('equity_multiplier', 'DECIMAL(10,4) DEFAULT NULL', '权益乘数'),
        ('dupont_roe', 'DECIMAL(10,4) DEFAULT NULL', 'ROE(杜邦分析)'),
        ('dupont_asset_sto_equity', 'DECIMAL(10,4) DEFAULT NULL', '资产/权益'),
        ('dupont_asset_turn', 'DECIMAL(10,4) DEFAULT NULL', '资产周转率'),
        ('dupont_pnitoni', 'DECIMAL(10,4) DEFAULT NULL', '净利润/总收入'),
        ('dupont_nitogr', 'DECIMAL(10,4) DEFAULT NULL', '净利润/营业收入'),
        ('dupont_tax_burden', 'DECIMAL(10,4) DEFAULT NULL', '税负比率'),
        ('dupont_int_burden', 'DECIMAL(10,4) DEFAULT NULL', '利息负担比率'),
        ('dupont_ebit_to_gr', 'DECIMAL(10,4) DEFAULT NULL', 'EBIT/营业收入'),
    ],
    'stock_profit_data': [
        ('roe_avg', 'DECIMAL(10,4) DEFAULT NULL', '平均 ROE'),
        ('np_margin', 'DECIMAL(10,4) DEFAULT NULL', '净利率'),
        ('gp_margin', 'DECIMAL(10,4) DEFAULT NULL', '毛利率'),
        ('net_profit', 'DECIMAL(20,4) DEFAULT NULL', '净利润'),
        ('eps_ttm', 'DECIMAL(10,4) DEFAULT NULL', 'EPS(TTM)'),
        ('mb_revenue', 'DECIMAL(20,4) DEFAULT NULL', '营业收入'),
    ],
}

def column_exists(cursor, table_name, column_name):
    """检查列是否存在"""
    cursor.execute("""
        SELECT COUNT(*) 
        FROM information_schema.columns 
        WHERE table_schema = DATABASE() 
          AND table_name = %s 
          AND column_name = %s
    """, (table_name, column_name))
    result = cursor.fetchone()
    return result[0] > 0

def add_column(cursor, table_name, column_name, column_def, comment):
    """添加列"""
    sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def} COMMENT '{comment}'"
    try:
        cursor.execute(sql)
        print(f"✅ {table_name}.{column_name} 添加成功")
        return True
    except Exception as e:
        print(f"❌ {table_name}.{column_name} 添加失败：{e}")
        return False

def main():
    conn = mysql.connector.connect(**config)
    cursor = conn.cursor()
    
    print("=" * 80)
    print("开始添加缺失的字段")
    print("=" * 80)
    
    for table_name, columns in columns_to_add.items():
        print(f"\n处理表：{table_name}")
        print("-" * 80)
        
        for column_name, column_def, comment in columns:
            if column_exists(cursor, table_name, column_name):
                print(f"⚠️  {table_name}.{column_name} 已存在，跳过")
            else:
                add_column(cursor, table_name, column_name, column_def, comment)
        
        conn.commit()
    
    print("\n" + "=" * 80)
    print("验证结果")
    print("=" * 80)
    
    # 验证关键字段
    key_columns = [
        ('stock_balance_data', 'current_ratio'),
        ('stock_growth_data', 'yoy_equity'),
        ('stock_operation_data', 'nr_turn_ratio'),
        ('stock_dupont_data', 'dupont_roe'),
    ]
    
    for table_name, column_name in key_columns:
        exists = column_exists(cursor, table_name, column_name)
        status = "✅" if exists else "❌"
        print(f"{status} {table_name}.{column_name}: {'存在' if exists else '不存在'}")
    
    cursor.close()
    conn.close()
    
    print("\n完成！")

if __name__ == '__main__':
    main()

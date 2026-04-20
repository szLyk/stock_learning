#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
申万行业分类采集 - 使用申万指数建立正确映射
核心逻辑：申万指数代码后3位的前2位 = 行业分类代码前2位
"""

import akshare as ak
import pandas as pd
import pymysql
from pymysql.cursors import DictCursor

# 数据库配置
DB_CONFIG = {
    "host": "192.168.1.128",
    "port": 3306,
    "user": "root",
    "password": "123456",
    "database": "stock",
    "charset": "utf8mb4",
    "cursorclass": DictCursor
}

def build_correct_industry_map():
    """建立正确的申万行业代码映射"""
    # 获取申万一级行业指数
    df1 = ak.sw_index_first_info()
    
    # 正确映射：指数代码后3位的前2位 = 分类代码前2位
    industry_map = {}
    for _, row in df1.iterrows():
        code = row['行业代码']  # 如 801780.SI
        name = row['行业名称']
        
        # 801780.SI -> 780 -> 78
        suffix = code.replace('.SI', '')[-3:]  # 取后3位
        prefix = suffix[:2]  # 取前2位
        
        industry_map[prefix] = name
    
    print(f'建立 {len(industry_map)} 个行业映射')
    
    # 显示映射
    print('\n行业映射表:')
    for prefix, name in sorted(industry_map.items()):
        print(f'  {prefix} -> {name}')
    
    return industry_map


def collect_sw_industry():
    """采集申万行业分类"""
    print("=" * 60)
    print("申万行业分类采集（正确映射）")
    print("=" * 60)
    
    # 1. 建立正确的行业映射
    print("\n1. 建立行业代码映射...")
    industry_map = build_correct_industry_map()
    
    # 2. 获取申万历史分类数据
    print("\n2. 获取申万历史分类数据...")
    df = ak.stock_industry_clf_hist_sw()
    print(f"   获取到 {len(df)} 条历史记录")
    
    # 3. 取每只股票最新分类
    print("\n3. 提取每只股票最新分类...")
    df['update_time'] = pd.to_datetime(df['update_time'])
    df_latest = df.sort_values('update_time').groupby('symbol').last().reset_index()
    print(f"   最新分类: {len(df_latest)} 只股票")
    
    # 4. 解析行业名称
    print("\n4. 解析行业名称...")
    def get_industry_name(code):
        if not code or len(code) < 2:
            return None
        prefix = code[:2]
        return industry_map.get(prefix, f'未知({prefix})')
    
    df_latest['industry_name'] = df_latest['industry_code'].apply(get_industry_name)
    
    # 统计未知行业
    unknown = df_latest[df_latest['industry_name'].str.contains('未知', na=False)]
    if len(unknown) > 0:
        print(f"\n⚠️ 发现 {len(unknown)} 只股票行业未识别")
        print("未识别的行业代码前缀:")
        for prefix in unknown['industry_code'].str[:2].unique():
            count = len(unknown[unknown['industry_code'].str[:2] == prefix])
            print(f"  {prefix}: {count}只")
    
    # 5. 存入数据库
    print("\n5. 存入数据库...")
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # 清空旧数据
    cursor.execute("TRUNCATE TABLE stock_industry_sw")
    conn.commit()
    print("   清空旧数据")
    
    insert_count = 0
    for _, row in df_latest.iterrows():
        stock_code = row['symbol']
        industry_code = row['industry_code']
        industry_name = row['industry_name']
        
        if not industry_name or '未知' in industry_name:
            continue
        
        sql = """
        INSERT INTO stock_industry_sw 
        (stock_code, industry_code, industry_name, industry_level, data_source)
        VALUES (%s, %s, %s, 1, 'sw_index')
        """
        cursor.execute(sql, (stock_code, industry_code, industry_name))
        insert_count += 1
        
        # 更新进度表
        sql_update = """
        UPDATE update_sw_industry_record 
        SET update_sw_industry = CURDATE(),
            update_status = 'success'
        WHERE stock_code = %s
        """
        cursor.execute(sql_update, (stock_code,))
    
    conn.commit()
    print(f"   存储 {insert_count} 条记录")
    
    # 6. 验证知名股票
    print("\n6. 验证知名股票...")
    test_stocks = [
        ('000001', '平安银行', '银行'),
        ('000002', '万科A', '房地产'),
        ('600519', '贵州茅台', '食品饮料'),
        ('600036', '招商银行', '银行'),
        ('000333', '美的集团', '家用电器'),
        ('000651', '格力电器', '家用电器'),
        ('002415', '海康威视', '电子'),
        ('300750', '宁德时代', '电力设备'),
    ]
    
    print("\n知名股票行业验证:")
    all_correct = True
    for code, name, expected in test_stocks:
        row = df_latest[df_latest['symbol'] == code]
        if not row.empty:
            actual = row['industry_name'].values[0]
            status = '✅' if actual == expected else '❌'
            if actual != expected:
                all_correct = False
            print(f"  {code} {name}: {actual} (期望: {expected}) {status}")
        else:
            print(f"  {code} {name}: 未找到")
    
    # 行业分布
    print("\n行业分布:")
    cursor.execute("""
        SELECT industry_name, COUNT(*) as cnt 
        FROM stock_industry_sw 
        GROUP BY industry_name 
        ORDER BY cnt DESC
    """)
    for row in cursor.fetchall():
        print(f"  {row['industry_name']}: {row['cnt']}只")
    
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 60)
    if all_correct:
        print("✅ 采集完成！数据验证全部正确")
    else:
        print("⚠️ 采集完成，但部分数据需要修正")
    print("=" * 60)


if __name__ == '__main__':
    collect_sw_industry()
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 EastMoneyFetcher 数据入库
验证 API 返回的字段能否正常写入 MySQL
"""

import sys
import os
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.mysql_tool import MySQLUtil


def test_insert():
    """测试数据入库"""
    
    print("=" * 80)
    print("测试 EastMoney 数据入库")
    print("=" * 80)
    
    mysql = MySQLUtil()
    mysql.connect()
    
    test_results = {}
    
    # 1. 测试 stock_capital_flow
    print("\n[1/4] 测试 stock_capital_flow...")
    try:
        test_df = pd.DataFrame([{
            'stock_code': '000001',
            'stock_date': '2026-03-16',
            'main_net_in': 1000.50,
            'sm_net_in': 200.30,
            'mm_net_in': 300.20,
            'bm_net_in': 500.00,
            'main_net_in_rate': 2.5,
            'close_price': 15.80,
            'change_rate': 1.25,
            'turnover_rate': 3.50,
            'north_hold': 5000.00,
            'north_net_in': 100.50
        }])
        
        rows = mysql.batch_insert_or_update('stock_capital_flow', test_df, ['stock_code', 'stock_date'])
        print(f"  ✅ 入库成功：{rows} 条")
        test_results['capital_flow'] = True
    except Exception as e:
        print(f"  ❌ 入库失败：{e}")
        test_results['capital_flow'] = False
    
    # 2. 测试 stock_shareholder_info
    print("\n[2/4] 测试 stock_shareholder_info...")
    try:
        test_df = pd.DataFrame([{
            'stock_code': '000001',
            'stock_name': '平安银行',
            'report_date': '2026-03-31',
            'shareholder_count': 150000,
            'shareholder_change': -2.5,
            'avg_hold_per_household': 10000,
            'avg_hold_change': 3.2,
            'freehold_shares': 1500000000,
            'freehold_ratio': 85.5
        }])
        
        rows = mysql.batch_insert_or_update('stock_shareholder_info', test_df, ['stock_code', 'report_date'])
        print(f"  ✅ 入库成功：{rows} 条")
        test_results['shareholder'] = True
    except Exception as e:
        print(f"  ❌ 入库失败：{e}")
        test_results['shareholder'] = False
    
    # 3. 测试 stock_concept
    print("\n[3/4] 测试 stock_concept...")
    try:
        test_df = pd.DataFrame([{
            'stock_code': '000001',
            'stock_name': '平安银行',
            'concept_name': '银行',
            'concept_type': '行业',
            'is_hot': 0
        }, {
            'stock_code': '000001',
            'stock_name': '平安银行',
            'concept_name': '金融科技',
            'concept_type': '主题',
            'is_hot': 1
        }])
        
        rows = mysql.batch_insert_or_update('stock_concept', test_df, ['stock_code', 'concept_name'])
        print(f"  ✅ 入库成功：{rows} 条")
        test_results['concept'] = True
    except Exception as e:
        print(f"  ❌ 入库失败：{e}")
        test_results['concept'] = False
    
    # 4. 测试 stock_analyst_expectation
    print("\n[4/4] 测试 stock_analyst_expectation...")
    try:
        test_df = pd.DataFrame([{
            'stock_code': '000001',
            'stock_name': '平安银行',
            'publish_date': '2026-03-16',
            'institution_name': '中信证券',
            'analyst_name': '张三',
            'rating_type': '买入',
            'rating_score': 5.0,
            'target_price': 18.50
        }])
        
        rows = mysql.batch_insert_or_update('stock_analyst_expectation', test_df, ['stock_code', 'publish_date'])
        print(f"  ✅ 入库成功：{rows} 条")
        test_results['analyst'] = True
    except Exception as e:
        print(f"  ❌ 入库失败：{e}")
        test_results['analyst'] = False
    
    # 输出总结
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)
    
    all_passed = all(test_results.values())
    
    for test_name, passed in test_results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    if all_passed:
        print("\n🎉 所有测试通过！表结构已修复，可以正常入库！")
    else:
        print("\n⚠️  部分测试失败，需要检查表结构")
    
    mysql.close()
    
    return all_passed


if __name__ == '__main__':
    success = test_insert()
    sys.exit(0 if success else 1)

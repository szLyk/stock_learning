#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AKShare 数据采集 - 手动执行脚本
支持断点续传，可随时中断后继续执行
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.akshare_fetcher import AkShareFetcher
from datetime import datetime

def main():
    if len(sys.argv) < 2:
        print("=" * 80)
        print("AKShare 数据采集 - 手动执行")
        print("=" * 80)
        print("\n用法：python3 scripts/run_akshare.py [数据类型]")
        print("\n数据类型:")
        print("  moneyflow   - 资金流向")
        print("  shareholder - 股东人数")
        print("  concept     - 概念板块")
        print("  analyst     - 分析师评级")
        print("\n示例:")
        print("  python3 scripts/run_akshare.py analyst")
        print("  python3 scripts/run_akshare.py moneyflow")
        print("=" * 80)
        return
    
    data_type = sys.argv[1]
    
    valid_types = ['moneyflow', 'shareholder', 'concept', 'analyst']
    if data_type not in valid_types:
        print(f"❌ 无效的数据类型：{data_type}")
        print(f"有效类型：{', '.join(valid_types)}")
        return
    
    print("=" * 80)
    print(f"AKShare 数据采集：{data_type}")
    print(f"开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    fetcher = AkShareFetcher()
    
    try:
        if data_type == 'moneyflow':
            fetcher.fetch_moneyflow_batch(max_retries=3)
        elif data_type == 'shareholder':
            fetcher.fetch_shareholder_batch(max_retries=3)
        elif data_type == 'concept':
            fetcher.fetch_concept_batch(max_retries=3)
        elif data_type == 'analyst':
            fetcher.fetch_analyst_batch(max_retries=3)
        
        print("\n" + "=" * 80)
        print("✅ 采集完成！")
        print(f"结束时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
    except KeyboardInterrupt:
        print("\n⚠️  用户中断（可随时重新运行继续采集）")
    except Exception as e:
        print(f"\n❌ 采集异常：{e}")
    finally:
        fetcher.mysql_manager.close()

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
东财数据初始化采集脚本
一次性采集所有类型的东财数据（带断点续传）
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.eastmoney_tool import EastMoneyFetcher
from datetime import datetime

def main():
    print("=" * 80)
    print("东方财富数据初始化采集")
    print(f"开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    fetcher = EastMoneyFetcher()
    
    try:
        # 1. 资金流向
        print("\n" + "=" * 80)
        print("【1/5】资金流向数据采集")
        print("=" * 80)
        fetcher.fetch_moneyflow_batch(max_retries=3)
        
        # 2. 北向资金
        print("\n" + "=" * 80)
        print("【2/5】北向资金数据采集")
        print("=" * 80)
        fetcher.fetch_north_batch(max_retries=3)
        
        # 3. 股东人数
        print("\n" + "=" * 80)
        print("【3/5】股东人数数据采集")
        print("=" * 80)
        fetcher.fetch_shareholder_batch(max_retries=3)
        
        # 4. 概念板块
        print("\n" + "=" * 80)
        print("【4/5】概念板块数据采集")
        print("=" * 80)
        fetcher.fetch_concept_batch(max_retries=3)
        
        # 5. 分析师评级
        print("\n" + "=" * 80)
        print("【5/5】分析师评级数据采集")
        print("=" * 80)
        fetcher.fetch_analyst_batch(max_retries=3)
        
        print("\n" + "=" * 80)
        print("✅ 所有数据采集完成！")
        print(f"结束时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
    except KeyboardInterrupt:
        print("\n⚠️  用户中断，采集结束")
    except Exception as e:
        print(f"\n❌ 采集异常：{e}")
        import traceback
        traceback.print_exc()
    finally:
        fetcher.mysql_manager.close()

if __name__ == '__main__':
    main()

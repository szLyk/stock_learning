#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AKShare 数据初始化采集脚本（带 Redis 断点续传）
采集：资金流向、股东人数、概念板块、分析师评级

特性：
- 自动从数据库获取待采集股票
- Redis 记录采集进度，支持中断后继续
- 自动重试失败的任务
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.akshare_fetcher import AkShareFetcher
from datetime import datetime

def main():
    print("=" * 80)
    print("AKShare 数据初始化采集（带断点续传）")
    print(f"开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    fetcher = AkShareFetcher()
    
    try:
        # 1. 资金流向
        print("\n" + "=" * 80)
        print("【1/4】资金流向数据采集")
        print("=" * 80)
        fetcher.fetch_moneyflow_batch(max_retries=3)
        
        # 2. 股东人数
        print("\n" + "=" * 80)
        print("【2/4】股东人数数据采集")
        print("=" * 80)
        fetcher.fetch_shareholder_batch(max_retries=3)
        
        # 3. 概念板块
        print("\n" + "=" * 80)
        print("【3/4】概念板块数据采集")
        print("=" * 80)
        fetcher.fetch_concept_batch(max_retries=3)
        
        # 4. 分析师评级
        print("\n" + "=" * 80)
        print("【4/4】分析师评级数据采集")
        print("=" * 80)
        fetcher.fetch_analyst_batch(max_retries=3)
        
        print("\n" + "=" * 80)
        print("✅ 所有数据采集完成！")
        print(f"结束时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
    except KeyboardInterrupt:
        print("\n⚠️  用户中断，采集结束（下次运行会自动续传）")
    except Exception as e:
        print(f"\n❌ 采集异常：{e}")
        import traceback
        traceback.print_exc()
    finally:
        fetcher.mysql_manager.close()

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tushare 资金流向数据初始化采集脚本
支持断点续传，可随时中断后继续执行

使用前请确认：
1. 已在 Tushare 官网完善个人信息（获取 120 积分）
2. Token 已配置（见 TOOLS.md）
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.tushare_moneyflow import TushareMoneyflowFetcher
from datetime import datetime

# Token 配置
TUSHARE_TOKEN = 'db6f63e5ad93cc28f9150c3b7338a6bffe8034db743095ebb3f847ae'

def main():
    print("=" * 80)
    print("Tushare 资金流向数据初始化采集")
    print(f"开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # 创建采集器
    fetcher = TushareMoneyflowFetcher(token=TUSHARE_TOKEN)
    
    try:
        # 批量采集（默认最近 30 天）
        fetcher.fetch_moneyflow_batch(max_retries=3)
        
        print("\n" + "=" * 80)
        print("✅ 采集完成！")
        print(f"结束时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
    except KeyboardInterrupt:
        print("\n⚠️  用户中断（可随时重新运行继续采集）")
    except Exception as e:
        print(f"\n❌ 采集异常：{e}")
        import traceback
        traceback.print_exc()
    finally:
        fetcher.close()

if __name__ == '__main__':
    main()

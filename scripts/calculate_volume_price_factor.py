#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
量价因子计算脚本
基于 Baostock 数据计算量价因子，替代资金流向因子

使用方法：
  python3 scripts/calculate_volume_price_factor.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.volume_price_factor import VolumePriceFactor
from datetime import datetime

def main():
    print("=" * 80)
    print("量价因子计算")
    print(f"开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    analyzer = VolumePriceFactor()
    
    try:
        # 批量计算
        results = analyzer.calculate_batch()
        
        # 保存到数据库
        if results:
            analyzer.save_to_db(results)
        
        print("\n" + "=" * 80)
        print("✅ 量价因子计算完成！")
        print(f"结束时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
    except KeyboardInterrupt:
        print("\n⚠️  用户中断")
    except Exception as e:
        print(f"\n❌ 计算失败：{e}")
        import traceback
        traceback.print_exc()
    finally:
        analyzer.close()

if __name__ == '__main__':
    main()

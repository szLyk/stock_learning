#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
利润表数据采集测试工具
独立运行，不依赖 XXL-JOB
"""

import sys
import os
import argparse
import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.baostock_financial import BaostockFinancialFetcher


def test_single_stock(stock_code, years=None):
    """
    测试单只股票利润表数据采集
    
    Args:
        stock_code: 股票代码，如 'sh.603083'
        years: 年份列表，None 表示当前年和上一年
    """
    print("=" * 70)
    print("利润表数据采集测试 - 单只股票")
    print("=" * 70)
    
    if not years:
        current_year = datetime.datetime.now().year
        years = [current_year, current_year - 1]
    
    fetcher = BaostockFinancialFetcher()
    
    try:
        print(f"\n测试股票：{stock_code}")
        print(f"采集年份：{years}")
        
        total_rows = 0
        
        for year in years:
            print(f"\n[{year}] 采集利润表数据...")
            df = fetcher.fetch_profit_data(stock_code, year)
            
            if not df.empty:
                print(f"✅ 成功获取 {len(df)} 条数据")
                total_rows += len(df)
                
                # 显示数据预览
                print(f"\n数据预览（{year}年）：")
                cols = ['stock_code', 'publish_date', 'statistic_date', 'roe_avg', 'net_profit', 'mb_revenue']
                available_cols = [c for c in cols if c in df.columns]
                print(df[available_cols].to_string())
            else:
                print(f"⚠️ {year}年无数据")
        
        print("\n" + "=" * 70)
        print(f"测试完成！共获取 {total_rows} 条数据")
        print("=" * 70)
        
        return total_rows > 0
        
    except Exception as e:
        print(f"\n❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        fetcher.logout()
        fetcher.mysql_manager.close()


def test_batch_collection(limit=10):
    """
    批量采集利润表数据
    
    Args:
        limit: 采集股票数量限制
    """
    print("=" * 70)
    print("利润表数据采集测试 - 批量采集")
    print("=" * 70)
    
    fetcher = BaostockFinancialFetcher()
    
    try:
        # 获取股票列表
        print("\n[1/3] 获取股票列表...")
        stocks_df = fetcher.get_pending_stocks('profit')
        
        if stocks_df.empty:
            print("❌ 未找到股票列表")
            return False
        
        # 限制数量
        stocks_df = stocks_df.head(limit)
        total = len(stocks_df)
        print(f"✅ 找到 {total} 只股票")
        
        # 批量采集
        print("\n[2/3] 开始批量采集...")
        success_count = 0
        fail_count = 0
        total_rows = 0
        
        for i, row in stocks_df.iterrows():
            stock_code = row['stock_code']
            last_update = row.get('last_update_date', '1990-01-01')
            
            try:
                # 计算需要采集的年份
                years_to_fetch = fetcher._get_years_to_fetch(last_update)
                
                if not years_to_fetch:
                    success_count += 1
                    continue
                
                rows_inserted = 0
                for year in years_to_fetch:
                    df = fetcher.fetch_profit_data(stock_code, year)
                    if not df.empty:
                        rows_inserted += len(df)
                        # 入库
                        fetcher.mysql_manager.batch_insert_or_update(
                            'stock_profit_data', df, ['stock_code', 'statistic_date']
                        )
                
                if rows_inserted > 0:
                    success_count += 1
                    total_rows += rows_inserted
                    print(f"  [{i+1}/{total}] {stock_code}: {rows_inserted}条")
                else:
                    success_count += 1
                    
            except Exception as e:
                fail_count += 1
                print(f"  [{i+1}/{total}] {stock_code}: ❌ {e}")
        
        # 输出结果
        print("\n[3/3] 采集结果统计：")
        print(f"  总计：{total} 只")
        print(f"  成功：{success_count} 只")
        print(f"  失败：{fail_count} 只")
        print(f"  总数据：{total_rows} 条")
        if total > 0:
            print(f"  成功率：{success_count/total*100:.1f}%")
        
        print("\n" + "=" * 70)
        print("批量采集测试完成！")
        print("=" * 70)
        
        return success_count > 0
        
    except Exception as e:
        print(f"\n❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        fetcher.logout()
        fetcher.mysql_manager.close()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='利润表数据采集测试工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 单只股票测试（默认 603083）
  python3 baostock_test_two.py single
  
  # 指定股票测试
  python3 baostock_test_two.py single --stock sh.603083
  
  # 批量采集测试（默认 10 只）
  python3 baostock_test_two.py batch
  
  # 批量采集 50 只
  python3 baostock_test_two.py batch --limit 50
        """
    )
    
    parser.add_argument(
        'mode',
        choices=['single', 'batch'],
        help='测试模式：single=单只股票，batch=批量采集'
    )
    
    parser.add_argument(
        '--stock',
        type=str,
        default='sh.603083',
        help='股票代码（single 模式），默认：sh.603083'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        default=10,
        help='采集股票数量（batch 模式），默认：10'
    )
    
    args = parser.parse_args()
    
    if args.mode == 'single':
        success = test_single_stock(args.stock)
    elif args.mode == 'batch':
        success = test_batch_collection(args.limit)
    else:
        parser.print_help()
        success = False
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

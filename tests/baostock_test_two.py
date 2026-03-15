import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.baostock_financial import BaostockFinancialFetcher
import datetime

def test_fetch_profit_data():
    """
    测试任务：拉取股票利润表数据
    测试 XXL-JOB 财务数据采集功能
    """
    print("=" * 70)
    print("测试任务：拉取利润表数据")
    print("=" * 70)
    
    fetcher = BaostockFinancialFetcher()
    
    try:
        # 测试股票：603083（航天发展）
        test_stock = 'sh.603083'
        current_year = datetime.datetime.now().year
        
        print(f"\n测试股票：{test_stock}")
        print(f"采集年份：{current_year}, {current_year - 1}")
        
        # 获取利润表数据
        print("\n[1/2] 采集利润表数据...")
        profit_df = fetcher.fetch_profit_data(test_stock, year=current_year)
        
        if not profit_df.empty:
            print(f"✅ 成功获取 {len(profit_df)} 条利润表数据")
            print("\n数据预览：")
            print(profit_df[['stock_code', 'publish_date', 'statistic_date', 'roe_avg', 'net_profit']].head())
        else:
            print("⚠️ 未获取到利润表数据")
        
        # 测试上一年数据
        print(f"\n[2/2] 采集{current_year - 1}年利润表数据...")
        profit_df_last = fetcher.fetch_profit_data(test_stock, year=current_year - 1)
        
        if not profit_df_last.empty:
            print(f"✅ 成功获取 {len(profit_df_last)} 条利润表数据")
            print("\n数据预览：")
            print(profit_df_last[['stock_code', 'publish_date', 'statistic_date', 'roe_avg', 'net_profit']].head())
        else:
            print("⚠️ 未获取到利润表数据")
        
        print("\n" + "=" * 70)
        print("测试完成！")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()
    finally:
        fetcher.logout()
        fetcher.mysql_manager.close()


def test_profit_batch_collection():
    """
    测试批量采集利润表数据（模拟 XXL-JOB 任务）
    """
    print("=" * 70)
    print("测试任务：批量采集利润表数据（XXL-JOB 模拟）")
    print("=" * 70)
    
    fetcher = BaostockFinancialFetcher()
    
    try:
        # 从数据库获取待采集股票
        print("\n[1/3] 获取待采集股票列表...")
        stocks_df = fetcher.get_pending_stocks('profit')
        
        if stocks_df.empty:
            print("❌ 未找到待采集股票")
            return
        
        total = len(stocks_df)
        print(f"✅ 找到 {total} 只待采集股票")
        
        # 批量采集
        print("\n[2/3] 开始批量采集...")
        success_count = 0
        fail_count = 0
        
        for i, row in stocks_df.iterrows():
            stock_code = row['stock_code']
            last_update_date = row.get('last_update_date', '1990-01-01')
            
            try:
                # 计算需要采集的年份
                years_to_fetch = fetcher._get_years_to_fetch(last_update_date)
                
                if not years_to_fetch:
                    continue
                
                rows_inserted = 0
                for year in years_to_fetch:
                    df = fetcher.fetch_profit_data(stock_code, year)
                    if not df.empty:
                        rows_inserted += len(df)
                
                if rows_inserted > 0:
                    success_count += 1
                
                if (i + 1) % 10 == 0:
                    print(f"已处理 {i+1}/{total}，成功 {success_count}")
                    
            except Exception as e:
                fail_count += 1
                print(f"❌ {stock_code} 失败：{e}")
        
        # 输出结果
        print("\n[3/3] 采集结果统计：")
        print(f"  总计：{total} 只")
        print(f"  成功：{success_count} 只")
        print(f"  失败：{fail_count} 只")
        print(f"  成功率：{success_count/total*100:.1f}%")
        
        print("\n" + "=" * 70)
        print("批量采集测试完成！")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()
    finally:
        fetcher.logout()
        fetcher.mysql_manager.close()


if __name__ == '__main__':
    import sys
    
    print("\n请选择测试模式：")
    print("1. 单只股票利润表测试")
    print("2. 批量利润表采集测试（XXL-JOB 模拟）")
    print()
    
    if len(sys.argv) > 1:
        choice = sys.argv[1]
    else:
        choice = input("输入选项 (1/2): ").strip()
    
    if choice == '1':
        test_fetch_profit_data()
    elif choice == '2':
        test_profit_batch_collection()
    else:
        # 默认运行单只股票测试
        test_fetch_profit_data()

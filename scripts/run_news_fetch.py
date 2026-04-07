# -*- coding: utf-8 -*-
"""
股票新闻批量采集脚本

使用方法：
1. 采集所有RSS源：python run_news_fetch.py
2. 采集特定股票：python run_news_fetch.py --stocks 000001,600519
3. 仅分析未处理新闻：python run_news_fetch.py --analyze-only
"""

import argparse
import sys
import time
from datetime import datetime

from src.utils.news_fetcher import NewsFetcher, fetch_news_batch
from logs.logger import LogManager


def main():
    parser = argparse.ArgumentParser(description='股票新闻采集')
    parser.add_argument('--stocks', type=str, help='股票代码列表（逗号分隔）')
    parser.add_argument('--analyze-only', action='store_true', help='仅分析未处理新闻')
    parser.add_argument('--stats', type=str, help='查看特定股票情绪统计')
    parser.add_argument('--days', type=int, default=7, help='统计天数')

    args = parser.parse_args()

    logger = LogManager.get_logger('run_news_fetch')

    print("=" * 60)
    print(f"股票新闻采集脚本 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    fetcher = NewsFetcher()
    total_count = 0

    try:
        if args.analyze_only:
            # 仅分析未处理新闻
            print("\n[模式] 仅分析未处理新闻")
            count = fetcher.analyze_unprocessed()
            total_count = count

        elif args.stats:
            # 查看情绪统计
            print(f"\n[模式] 查看 {args.stats} 情绪统计（最近 {args.days} 天）")
            stats = fetcher.get_stock_sentiment_stats(args.stats, days=args.days)
            print(f"\n统计结果:")
            print(f"  新闻数量: {stats.get('count', 0)}")
            print(f"  平均情绪分数: {stats.get('mean', 0):.4f}")
            print(f"  正面新闻: {stats.get('positive_count', 0)}")
            print(f"  负面新闻: {stats.get('negative_count', 0)}")
            print(f"  中性新闻: {stats.get('neutral_count', 0)}")
            print(f"  正面比例: {stats.get('positive_ratio', 0):.2%}")

        else:
            # 采集新闻
            print("\n[模式] 采集新闻")

            # 1. 采集所有RSS源
            print("\n[1] 采集RSS源...")
            count = fetcher.fetch_all()
            total_count += count
            print(f"✅ RSS采集 {count} 条")

            # 2. 采集特定股票新闻
            if args.stocks:
                stock_codes = args.stocks.split(',')
                print(f"\n[2] 采集特定股票新闻: {stock_codes}")

                for i, code in enumerate(stock_codes):
                    count = fetcher.fetch_for_stock(code)
                    total_count += count
                    print(f"  {code}: {count} 条")

                    # 控制频率
                    if i % 5 == 0:
                        time.sleep(2)

            # 3. 分析未处理新闻
            print("\n[3] 分析未处理新闻...")
            count = fetcher.analyze_unprocessed()
            total_count += count
            print(f"✅ 分析 {count} 条")

        print("\n" + "=" * 60)
        print(f"✅ 完成！总计处理 {total_count} 条新闻")
        print("=" * 60)

    except Exception as e:
        logger.error(f"采集失败: {e}")
        print(f"\n❌ 错误: {e}")
        sys.exit(1)

    finally:
        fetcher.close()


if __name__ == '__main__':
    main()
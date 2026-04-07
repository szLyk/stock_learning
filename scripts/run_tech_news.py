# -*- coding: utf-8 -*-
"""
科技新闻批量采集脚本

使用方法：
1. 采集全部（国内+国外）：python run_tech_news.py
2. 仅采集国内：python run_tech_news.py --cn-only
3. 仅采集国外：python run_tech_news.py --global-only
4. 采集特定A股：python run_tech_news.py --stocks 000001,600519

注意：
- 国外RSS源需要VPN
- 建议先测试网络连通性：python run_tech_news.py --test
"""

import argparse
import sys
import time
from datetime import datetime

from src.utils.tech_news_fetcher import TechNewsFetcher
from src.utils.mysql_tool import MySQLUtil
from logs.logger import LogManager


def test_network():
    """测试网络连通性"""
    import urllib.request

    print("测试国外RSS源连通性...")
    test_urls = [
        ('BBC Tech', 'https://feeds.bbci.co.uk/news/technology/rss.xml'),
        ('CNBC', 'https://www.cnbc.com/id/10000664/device/rss/rss.html'),
        ('Google News', 'https://news.google.com/rss/search?q=NVIDIA&hl=en-US'),
    ]

    for name, url in test_urls:
        try:
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0')
            with urllib.request.urlopen(req, timeout=10) as resp:
                status = resp.status
                print(f"  ✅ {name}: HTTP {status}")
        except Exception as e:
            print(f"  ❌ {name}: {str(e)[:50]}")

    print("\n如果全部失败，请检查VPN连接")


def main():
    parser = argparse.ArgumentParser(description='科技新闻采集')
    parser.add_argument('--cn-only', action='store_true', help='仅采集国内A股新闻')
    parser.add_argument('--global-only', action='store_true', help='仅采集国外科技新闻')
    parser.add_argument('--stocks', type=str, help='指定A股代码（逗号分隔）')
    parser.add_argument('--test', action='store_true', help='测试网络连通性')

    args = parser.parse_args()

    print("=" * 60)
    print(f"科技新闻采集 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    if args.test:
        test_network()
        return

    fetcher = TechNewsFetcher()
    total = 0

    try:
        if args.global_only:
            # 仅国外
            print("\n[模式] 仅采集国外科技新闻（需要VPN）")
            total = fetcher.fetch_global_news()

        elif args.cn_only:
            # 仅国内
            print("\n[模式] 仅采集国内A股新闻")
            codes = args.stocks.split(',') if args.stocks else None
            total = fetcher.fetch_cn_news(codes)

        else:
            # 全部采集
            print("\n[模式] 采集全部（国内+国外）")

            # 1. 国内
            codes = args.stocks.split(',') if args.stocks else None
            cn_count = fetcher.fetch_cn_news(codes)
            total += cn_count
            print(f"  国内: {cn_count} 条")

            # 2. 国外
            print("\n请确保VPN已开启...")
            time.sleep(2)
            gl_count = fetcher.fetch_global_news()
            total += gl_count
            print(f"  国外: {gl_count} 条")

        # 统计
        print("\n" + "=" * 60)
        print("采集结果统计")
        print("=" * 60)

        mysql = MySQLUtil()
        mysql.connect()

        cn = mysql.query_one('SELECT COUNT(*) as cnt FROM stock_news_cn')
        gl = mysql.query_one('SELECT COUNT(*) as cnt FROM stock_news_global')
        imp = mysql.query_one('SELECT COUNT(*) as cnt FROM stock_news_impact')

        print(f"国内新闻: {cn['cnt']} 条")
        print(f"国外新闻: {gl['cnt']} 条")
        print(f"影响关联: {imp['cnt']} 条")

        # 显示最新国外新闻
        if gl['cnt'] > 0:
            print("\n最新国外科技新闻:")
            news = mysql.query_all('''
                SELECT title, source, related_company, sentiment_score, sentiment_type
                FROM stock_news_global
                ORDER BY id DESC LIMIT 5
            ''')
            for n in news:
                company = n['related_company'] or '-'
                sentiment = f"{n['sentiment_score']:.2f}" if n['sentiment_score'] else '0.00'
                print(f"  [{n['source']}] {n['title'][:40]}...")
                print(f"    公司: {company}, 情绪: {sentiment} ({n['sentiment_type']})")

        mysql.close()

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        sys.exit(1)

    finally:
        fetcher.close()

    print(f"\n✅ 完成！本次采集 {total} 条")


if __name__ == '__main__':
    main()
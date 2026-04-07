# -*- coding: utf-8 -*-
"""
股票科技新闻采集器（国内+国外）

数据源：
1. 国内A股新闻：AkShare（东方财富个股新闻）
2. 国外科技新闻：RSS（Reuters/BBC/CNBC/MarketWatch）
   - NVIDIA/Micron/AMD/Intel/Tesla等美股科技新闻
   - 自动关联A股产业链影响

表结构：
- stock_news_cn: 国内A股新闻
- stock_news_global: 国外科技新闻
- stock_news_impact: 新闻影响关联（美股→A股）
- tech_company_mapping: 科技公司映射表
"""

import hashlib
import json
import re
import time
import random
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Dict, Optional

import akshare as ak
import numpy as np

from logs.logger import LogManager
from src.utils.mysql_tool import MySQLUtil


class TechNewsFetcher:
    """科技新闻统一采集器"""

    # 科技公司关键词（用于识别新闻相关公司）
    US_TECH_KEYWORDS = {
        'NVIDIA': ['nvidia', 'nvda', 'gpu', 'ai chip', 'artificial intelligence'],
        'Micron': ['micron', 'mu', 'memory', 'dram', 'nand', 'storage'],
        'AMD': ['amd', 'advanced micro', 'ryzen', 'epyc'],
        'Intel': ['intel', 'intc', 'cpu', 'x86'],
        'Tesla': ['tesla', 'tsla', 'ev', 'electric vehicle', 'battery'],
        'Apple': ['apple', 'aapl', 'iphone', 'mac'],
        'Qualcomm': ['qualcomm', 'qcom', 'snapdragon', 'mobile chip'],
        'Microsoft': ['microsoft', 'msft', 'azure', 'openai'],
        'Google': ['google', 'googl', 'alphabet', 'deepmind'],
    }

    # 中文情绪词典
    CN_POSITIVE = {
        '上涨': 1.0, '涨停': 1.5, '大涨': 1.5, '飙升': 1.5, '突破': 1.0,
        '新高': 1.5, '利好': 1.0, '业绩大增': 1.5, '盈利': 1.0, '增长': 1.0,
        '增持': 1.0, '买入': 1.0, '反弹': 0.8, '企稳': 0.5, '超预期': 1.0,
    }

    CN_NEGATIVE = {
        '下跌': 1.0, '跌停': 1.5, '暴跌': 1.5, '大跌': 1.5, '跌破': 1.0,
        '新低': 1.5, '利空': 1.0, '业绩下滑': 1.5, '亏损': 1.0, '减持': 1.0,
        '卖出': 1.0, '清仓': 1.5, '调查': 0.8, '处罚': 1.0, '爆雷': 1.5,
    }

    # 英文情绪词典
    EN_POSITIVE = {
        'surge': 1.5, 'boom': 1.5, 'record': 1.5, 'rally': 1.5, 'high': 1.0,
        'rise': 1.0, 'gain': 1.0, 'profit': 1.0, 'growth': 1.0, 'beat': 1.0,
        'upgrade': 1.0, 'bullish': 1.0, 'strong': 1.0, 'outperform': 1.0,
    }

    EN_NEGATIVE = {
        'crash': 1.5, 'plunge': 1.5, 'crisis': 1.5, 'collapse': 1.5, 'low': 1.0,
        'fall': 1.0, 'drop': 1.0, 'decline': 1.0, 'loss': 1.0, 'miss': 1.0,
        'downgrade': 1.0, 'bearish': 1.0, 'weak': 1.0, 'concern': 1.0,
    }

    def __init__(self):
        self.logger = LogManager.get_logger('tech_news_fetcher')
        self.mysql = MySQLUtil()
        self.mysql.connect()
        self._load_mappings()

    def _load_mappings(self):
        """加载科技公司映射"""
        try:
            result = self.mysql.query_all(
                "SELECT us_company, us_ticker, sector, cn_related_stocks, impact_logic FROM tech_company_mapping WHERE is_active=1"
            )
            self.company_mapping = {}
            for row in result:
                company = row['us_company']
                self.company_mapping[company.lower()] = {
                    'ticker': row['us_ticker'],
                    'sector': row['sector'],
                    'cn_stocks': json.loads(row['cn_related_stocks']) if row['cn_related_stocks'] else [],
                    'impact_logic': row['impact_logic'],
                }
            self.logger.info(f"加载 {len(self.company_mapping)} 家科技公司映射")
        except Exception as e:
            self.logger.error(f"加载映射失败: {e}")
            self.company_mapping = {}

    def _hash_content(self, title: str) -> str:
        """内容哈希"""
        return hashlib.md5(title.encode('utf-8')).hexdigest()

    def _is_duplicate_cn(self, hash: str) -> bool:
        """国内新闻去重"""
        r = self.mysql.query_one("SELECT COUNT(*) as cnt FROM stock_news_cn WHERE content_hash=%s", (hash,))
        return r['cnt'] > 0 if r else False

    def _is_duplicate_global(self, hash: str) -> bool:
        """国外新闻去重"""
        r = self.mysql.query_one("SELECT COUNT(*) as cnt FROM stock_news_global WHERE content_hash=%s", (hash,))
        return r['cnt'] > 0 if r else False

    def _analyze_sentiment_cn(self, text: str) -> Dict:
        """中文情绪分析"""
        pos_words = []
        neg_words = []
        pos_score = 0
        neg_score = 0

        for word, weight in self.CN_POSITIVE.items():
            if word in text:
                pos_words.append(word)
                pos_score += weight

        for word, weight in self.CN_NEGATIVE.items():
            if word in text:
                neg_words.append(word)
                neg_score += weight

        total = len(pos_words) + len(neg_words)
        if total == 0:
            return {'score': 0, 'type': 'neutral', 'pos_words': [], 'neg_words': []}

        score = (pos_score - neg_score) / (pos_score + neg_score + 1)
        type = 'positive' if score > 0.15 else ('negative' if score < -0.15 else 'neutral')

        return {'score': round(score, 4), 'type': type, 'pos_words': pos_words, 'neg_words': neg_words}

    def _analyze_sentiment_en(self, text: str) -> Dict:
        """英文情绪分析"""
        text_lower = text.lower()
        pos_words = []
        neg_words = []
        pos_score = 0
        neg_score = 0

        for word, weight in self.EN_POSITIVE.items():
            if word in text_lower:
                pos_words.append(word)
                pos_score += weight

        for word, weight in self.EN_NEGATIVE.items():
            if word in text_lower:
                neg_words.append(word)
                neg_score += weight

        total = len(pos_words) + len(neg_words)
        if total == 0:
            return {'score': 0, 'type': 'neutral', 'pos_words': [], 'neg_words': []}

        score = (pos_score - neg_score) / (pos_score + neg_score + 1)
        type = 'positive' if score > 0.15 else ('negative' if score < -0.15 else 'neutral')

        return {'score': round(score, 4), 'type': type, 'pos_words': pos_words, 'neg_words': neg_words}

    def _detect_related_company(self, title: str, desc: str) -> List[str]:
        """检测新闻相关的美股公司"""
        text = f"{title} {desc}".lower()
        related = []

        for company, keywords in self.US_TECH_KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    related.append(company)
                    break

        return related

    # =====================================================
    # 国内A股新闻采集
    # =====================================================

    def fetch_cn_news(self, stock_codes: List[str] = None) -> int:
        """采集国内A股新闻"""
        codes = stock_codes or ['000001', '600519', '300750', '688981']  # 默认几个重要股票
        total = 0

        for code in codes:
            try:
                self.logger.info(f"[CN] 采集 {code} 新闻...")
                df = ak.stock_news_em(symbol=code)

                if df is None or df.empty:
                    continue

                for _, row in df.iterrows():
                    title = row.get('新闻标题', '')
                    content = row.get('新闻内容', '')
                    pub_time = row.get('发布时间', '')

                    if not title:
                        continue

                    hash = self._hash_content(title)
                    if self._is_duplicate_cn(hash):
                        continue

                    # 解析时间
                    try:
                        published = datetime.strptime(pub_time, '%Y-%m-%d %H:%M:%S')
                    except:
                        published = datetime.now()

                    # 保存新闻
                    self.mysql.execute("""
                        INSERT INTO stock_news_cn (title, content, source, stock_code, published_at, content_hash)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (title, content[:1000], '东方财富', code, published, hash))

                    result = self.mysql.query_one("SELECT LAST_INSERT_ID() as id")
                    news_id = result['id']

                    # 情绪分析
                    sentiment = self._analyze_sentiment_cn(f"{title} {content}")
                    self.mysql.execute("""
                        INSERT INTO stock_news_sentiment_cn (news_id, stock_code, sentiment_score, sentiment_type, positive_words, negative_words)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (news_id, code, sentiment['score'], sentiment['type'],
                          json.dumps(sentiment['pos_words']), json.dumps(sentiment['neg_words'])))

                    self.mysql.execute("UPDATE stock_news_cn SET is_processed=1 WHERE id=%s", (news_id,))
                    total += 1

                time.sleep(random.uniform(1, 2))

            except Exception as e:
                self.logger.error(f"采集 {code} 失败: {e}")

        self.logger.info(f"[CN] 完成，采集 {total} 条")
        return total

    # =====================================================
    # 国外科技新闻采集（RSS）
    # =====================================================

    def fetch_global_news(self) -> int:
        """采集国外科技新闻"""
        total = 0

        # 获取RSS源
        sources = self.mysql.query_all(
            "SELECT source_name, source_url, category FROM rss_source_config WHERE is_active=1 ORDER BY priority"
        )

        for source in sources:
            name = source['source_name']
            url = source['source_url']
            category = source['category']

            self.logger.info(f"[Global] 采集 {name}...")

            try:
                articles = self._fetch_rss(url, name)
                self.logger.info(f"  获取 {len(articles)} 条")

                for article in articles:
                    title = article['title']
                    desc = article['description']

                    hash = self._hash_content(title)
                    if self._is_duplicate_global(hash):
                        continue

                    # 检测相关公司
                    related_companies = self._detect_related_company(title, desc)
                    related_str = ','.join(related_companies) if related_companies else None

                    # 情绪分析
                    sentiment = self._analyze_sentiment_en(f"{title} {desc}")

                    # 保存
                    self.mysql.execute("""
                        INSERT INTO stock_news_global (title, description, source, source_url, published_at,
                                                       category, related_company, content_hash, sentiment_score, sentiment_type)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (title, desc[:500], name, article['url'], article['published_at'],
                          category, related_str, hash, sentiment['score'], sentiment['type']))

                    result = self.mysql.query_one("SELECT LAST_INSERT_ID() as id")
                    news_id = result['id']

                    # 创建影响关联
                    for company in related_companies:
                        mapping = self.company_mapping.get(company.lower())
                        if mapping and mapping['cn_stocks']:
                            for cn_stock in mapping['cn_stocks'][:3]:  # 最多3个
                                self.mysql.execute("""
                                    INSERT INTO stock_news_impact (global_news_id, cn_stock_code, cn_stock_name, impact_type, impact_reason)
                                    VALUES (%s, %s, %s, %s, %s)
                                    ON DUPLICATE KEY UPDATE impact_reason = VALUES(impact_reason)
                                """, (news_id, cn_stock, cn_stock, 'sector', mapping['impact_logic']))

                    self.mysql.execute("UPDATE stock_news_global SET is_processed=1 WHERE id=%s", (news_id,))
                    total += 1

                # 更新源状态
                self.mysql.execute("""
                    UPDATE rss_source_config SET last_fetch_time=NOW(), fetch_count=fetch_count+%s WHERE source_name=%s
                """, (len(articles), name))

                time.sleep(random.uniform(2, 4))

            except Exception as e:
                self.logger.error(f"采集 {name} 失败: {e}")
                self.mysql.execute("UPDATE rss_source_config SET error_count=error_count+1 WHERE source_name=%s", (name,))

        self.logger.info(f"[Global] 完成，采集 {total} 条")
        return total

    def _fetch_rss(self, url: str, source_name: str) -> List[Dict]:
        """获取RSS"""
        articles = []

        try:
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0 (compatible; TechNewsBot/1.0)')

            with urllib.request.urlopen(req, timeout=20) as response:
                xml_content = response.read().decode('utf-8')
                root = ET.fromstring(xml_content)

                # RSS 2.0
                channel = root.find('channel')
                if channel:
                    items = channel.findall('item')
                    for item in items[:20]:  # 限制20条
                        title = item.find('title')
                        desc = item.find('description')
                        link = item.find('link')
                        pubdate = item.find('pubDate')

                        if title and title.text:
                            # 清理HTML
                            desc_text = re.sub(r'<[^>]+>', '', desc.text if desc and desc.text else '')
                            try:
                                pub = datetime.strptime(pubdate.text.strip() if pubdate else '',
                                                       '%a, %d %b %Y %H:%M:%S %Z')
                            except:
                                pub = datetime.now()

                            articles.append({
                                'title': title.text.strip(),
                                'description': desc_text[:500],
                                'url': link.text if link and link.text else '',
                                'published_at': pub,
                            })

        except Exception as e:
            self.logger.error(f"RSS获取失败: {e}")

        return articles

    # =====================================================
    # 查询功能
    # =====================================================

    def get_impact_summary(self, cn_stock: str, days: int = 7) -> Dict:
        """获取A股受国外新闻影响的统计"""
        from datetime import timedelta
        start = datetime.now() - timedelta(days=days)

        impacts = self.mysql.query_all("""
            SELECT gi.global_news_id, gn.title, gn.source, gn.related_company, gn.sentiment_score, gn.published_at
            FROM stock_news_impact gi
            JOIN stock_news_global gn ON gi.global_news_id = gn.id
            WHERE gi.cn_stock_code = %s AND gn.published_at >= %s
            ORDER BY gn.published_at DESC
        """, (cn_stock, start))

        if not impacts:
            return {'count': 0, 'avg_sentiment': 0}

        scores = [float(i['sentiment_score']) for i in impacts if i['sentiment_score']]

        return {
            'count': len(impacts),
            'avg_sentiment': np.mean(scores) if scores else 0,
            'sources': [i['source'] for i in impacts[:5]],
            'companies': [i['related_company'] for i in impacts if i['related_company']],
        }

    def close(self):
        self.mysql.close()


# =====================================================
# 测试
# =====================================================

if __name__ == '__main__':
    print("=" * 60)
    print("科技新闻采集器测试（国内+国外）")
    print("=" * 60)

    fetcher = TechNewsFetcher()

    # 1. 国内A股新闻
    print("\n[1] 国内A股新闻...")
    count = fetcher.fetch_cn_news(['000001'])
    print(f"  采集 {count} 条")

    # 2. 国外科技新闻
    print("\n[2] 国外科技新闻...")
    count = fetcher.fetch_global_news()
    print(f"  采集 {count} 条")

    # 3. 查看影响关联
    print("\n[3] 查看新闻影响关联...")
    impacts = fetcher.mysql.query_all("SELECT * FROM stock_news_impact LIMIT 5")
    for i in impacts:
        print(f"  news_id={i['global_news_id']}, A股={i['cn_stock_name']}, 原因={i['impact_reason'][:30]}")

    fetcher.close()
    print("\n完成!")
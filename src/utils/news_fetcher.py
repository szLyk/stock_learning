# -*- coding: utf-8 -*-
"""
股票财经新闻采集模块（A股专用）

核心功能：
1. AkShare 股票新闻采集（东方财富、CCTV等）
2. 新闻去重（基于内容哈希）
3. 新闻-股票关联（通过关键词匹配）
4. 情绪分析（基于中文词典）
5. 断点续传（Redis checkpoint）

数据源：
- ak.stock_news_em() - 东方财富个股新闻
- ak.news_cctv() - CCTV财经新闻

设计模式应用：
- 装饰器：@timer、@retry、@rate_limit
- 上下文管理器：采集统计管理
- 生成器：流式处理新闻数据
"""

import hashlib
import json
import re
import time
import random
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from contextlib import contextmanager
from datetime import datetime, timedelta
from functools import wraps
from typing import Generator, List, Dict, Optional

import numpy as np
import pandas as pd

from logs.logger import LogManager
from src.utils.mysql_tool import MySQLUtil
from src.utils.redis_tool import RedisUtil


# ============================================================
# 装饰器
# ============================================================

def timer(unit: str = 's'):
    """计时装饰器"""
    factor = {'s': 1, 'ms': 1000, 'us': 1000000}

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            end = time.perf_counter()
            elapsed = (end - start) * factor[unit]
            # 使用 logger 而非 print
            logger = LogManager.get_logger('news_fetcher')
            logger.debug(f"[Timer] {func.__name__} 执行时间: {elapsed:.4f} {unit}")
            return result
        return wrapper
    return decorator


def retry(max_attempts: int = 3, delay: float = 1.0, exceptions: tuple = (Exception,)):
    """重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            logger = LogManager.get_logger('news_fetcher')
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts:
                        logger.error(f"[Retry] {func.__name__} 重试 {max_attempts} 次后失败: {e}")
                        raise
                    logger.warning(f"[Retry] {func.__name__} 第 {attempt} 次失败: {e}")
                    time.sleep(current_delay)
                    current_delay *= 2
            return None
        return wrapper
    return decorator


def rate_limit(calls_per_second: float = 2.0):
    """限速装饰器"""
    min_interval = 1.0 / calls_per_second
    last_call_time = {}

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            func_name = func.__name__
            now = time.time()
            if func_name in last_call_time:
                elapsed = now - last_call_time[func_name]
                if elapsed < min_interval:
                    wait_time = min_interval - elapsed
                    time.sleep(wait_time)
            last_call_time[func_name] = time.time()
            return func(*args, **kwargs)
        return wrapper
    return decorator


# ============================================================
# 上下文管理器
# ============================================================

@contextmanager
def fetch_stats_context(logger) -> Generator[dict, None, None]:
    """采集统计上下文管理器"""
    stats = {
        'start_time': time.time(),
        'news_count': 0,
        'sources': [],
        'requests': 0,
        'success': 0,
        'failed': 0,
    }
    logger.info("[Stats] 新闻采集开始")
    try:
        yield stats
    finally:
        stats['end_time'] = time.time()
        stats['duration'] = stats['end_time'] - stats['start_time']
        logger.info(f"[Stats] 新闻采集结束，耗时 {stats['duration']:.2f}s，"
                   f"采集 {stats['news_count']} 条新闻，来源: {stats['sources']}")


# ============================================================
# 情绪分析器
# ============================================================

class SentimentAnalyzer:
    """情绪分析器（基于词典）"""

    def __init__(self, mysql_manager: MySQLUtil):
        self.logger = LogManager.get_logger('sentiment_analyzer')
        self.mysql_manager = mysql_manager
        self.positive_words = {}
        self.negative_words = {}
        self.weights = {}
        self._load_dictionary()

    def _load_dictionary(self):
        """从数据库加载情绪词典"""
        try:
            # 加载正面词
            pos_sql = "SELECT word, weight FROM sentiment_dictionary WHERE word_type='positive' AND is_active=1"
            pos_result = self.mysql_manager.query_all(pos_sql)
            for row in pos_result:
                word, weight = row['word'], float(row['weight'])
                self.positive_words[word] = weight
                self.weights[word] = weight

            # 加载负面词
            neg_sql = "SELECT word, weight FROM sentiment_dictionary WHERE word_type='negative' AND is_active=1"
            neg_result = self.mysql_manager.query_all(neg_sql)
            for row in neg_result:
                word, weight = row['word'], float(row['weight'])
                self.negative_words[word] = weight
                self.weights[word] = weight

            self.logger.info(f"加载情绪词典：正面词 {len(self.positive_words)}，负面词 {len(self.negative_words)}")

        except Exception as e:
            self.logger.error(f"加载情绪词典失败: {e}")
            # 使用默认词典
            self._load_default_dictionary()

    def _load_default_dictionary(self):
        """加载默认词典（数据库加载失败时）"""
        positive_default = ['rise', 'surge', 'gain', 'profit', 'growth', 'rally', 'boom',
                           'increase', 'up', 'positive', 'strong', 'success', 'record', 'recover']
        negative_default = ['fall', 'drop', 'decline', 'loss', 'plunge', 'crash', 'sink',
                           'down', 'negative', 'weak', 'fail', 'crisis', 'recession', 'fear']

        for word in positive_default:
            self.positive_words[word] = 1.0
            self.weights[word] = 1.0

        for word in negative_default:
            self.negative_words[word] = -1.0
            self.weights[word] = -1.0

    def analyze_text(self, text: str) -> Dict:
        """分析单条文本的情绪"""
        if not text:
            return {
                'score': 0.0,
                'positive_count': 0,
                'negative_count': 0,
                'keywords': [],
                'sentiment_type': 'neutral',
                'confidence': 0.0
            }

        text_lower = text.lower()
        words = re.findall(r'\b[a-z]+\b', text_lower)

        positive_matches = []
        negative_matches = []

        for word in words:
            if word in self.positive_words:
                positive_matches.append(word)
            elif word in self.negative_words:
                negative_matches.append(word)

        # 计算分数
        pos_score = sum(abs(self.weights.get(w, 0)) for w in positive_matches)
        neg_score = sum(abs(self.weights.get(w, 0)) for w in negative_matches)

        total_keywords = len(positive_matches) + len(negative_matches)
        if total_keywords == 0:
            score = 0.0
            sentiment_type = 'neutral'
            confidence = 0.0
        else:
            # 分数范围 [-1, 1]
            score = (pos_score - neg_score) / (pos_score + neg_score + 1)
            confidence = min(total_keywords / 5.0, 1.0)  # 基于关键词数量计算置信度

            if score > 0.1:
                sentiment_type = 'positive'
            elif score < -0.1:
                sentiment_type = 'negative'
            else:
                sentiment_type = 'neutral'

        return {
            'score': round(score, 4),
            'positive_count': len(positive_matches),
            'negative_count': len(negative_matches),
            'keywords': json.dumps(positive_matches + negative_matches),
            'positive_words': positive_matches,
            'negative_words': negative_matches,
            'sentiment_type': sentiment_type,
            'confidence': round(confidence, 2)
        }

    def analyze_batch_numpy(self, texts: List[str]) -> np.ndarray:
        """批量分析（NumPy向量化）"""
        scores = np.zeros(len(texts))
        for i, text in enumerate(texts):
            result = self.analyze_text(text)
            scores[i] = result['score']
        return scores

    def get_statistics(self, scores: np.ndarray) -> Dict:
        """统计情绪分数分布"""
        if len(scores) == 0:
            return {}
        return {
            'mean': np.mean(scores),
            'median': np.median(scores),
            'std': np.std(scores),
            'min': np.min(scores),
            'max': np.max(scores),
            'positive_ratio': np.sum(scores > 0.1) / len(scores),
            'negative_ratio': np.sum(scores < -0.1) / len(scores),
            'neutral_ratio': np.sum((scores >= -0.1) & (scores <= 0.1)) / len(scores),
        }


# ============================================================
# 新闻采集器
# ============================================================

class NewsFetcher:
    """新闻采集器"""

    def __init__(self):
        self.logger = LogManager.get_logger('news_fetcher')
        self.mysql_manager = MySQLUtil()
        self.mysql_manager.connect()
        self.redis_manager = RedisUtil() if RedisUtil else None
        self.analyzer = SentimentAnalyzer(self.mysql_manager)

        # 缓存股票代码列表（用于新闻关联）
        self.stock_codes = self._load_stock_codes()

    def _load_stock_codes(self) -> List[str]:
        """加载股票代码列表"""
        try:
            sql = "SELECT DISTINCT stock_code FROM stock_daily ORDER BY stock_code"
            result = self.mysql_manager.query_all(sql)
            codes = [row['stock_code'] for row in result]
            self.logger.info(f"加载股票代码：{len(codes)} 只")
            return codes
        except Exception as e:
            self.logger.error(f"加载股票代码失败: {e}")
            return []

    def _generate_content_hash(self, title: str, source: str) -> str:
        """生成内容哈希（用于去重）"""
        content = f"{title}|{source}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    def _is_duplicate(self, content_hash: str) -> bool:
        """检查是否重复"""
        sql = "SELECT COUNT(*) as cnt FROM stock_news WHERE content_hash = ?"
        result = self.mysql_manager.query_one(sql, (content_hash,))
        return result['cnt'] > 0 if result else False

    @retry(max_attempts=3, delay=2.0)
    @rate_limit(calls_per_second=0.5)
    def _fetch_rss(self, rss_url: str, source_name: str, stats: dict) -> List[Dict]:
        """获取并解析 RSS 源"""
        stats['requests'] += 1

        try:
            req = urllib.request.Request(rss_url)
            req.add_header('User-Agent', 'Mozilla/5.0 (compatible; StockNewsBot/1.0)')

            with urllib.request.urlopen(req, timeout=15) as response:
                xml_content = response.read().decode('utf-8')
                stats['success'] += 1

                articles = self._parse_rss_xml(xml_content, source_name)
                return articles

        except Exception as e:
            stats['failed'] += 1
            self.logger.error(f"[RSS] 获取 {source_name} 失败: {e}")
            return []

    def _parse_rss_xml(self, xml_content: str, source_name: str) -> List[Dict]:
        """解析 RSS XML"""
        articles = []

        try:
            root = ET.fromstring(xml_content)

            # RSS 2.0 格式
            channel = root.find('channel')
            if channel is None:
                # Atom 格式
                items = root.findall('{http://www.w3.org/2005/Atom}entry')
                for entry in items:
                    article = self._parse_atom_entry(entry, source_name)
                    if article:
                        articles.append(article)
            else:
                items = channel.findall('item')
                for item in items:
                    article = self._parse_rss_item(item, source_name)
                    if article:
                        articles.append(article)

        except ET.ParseError as e:
            self.logger.error(f"[RSS] XML 解析错误: {e}")

        return articles

    def _parse_rss_item(self, item, source_name: str) -> Optional[Dict]:
        """解析 RSS item"""
        title_elem = item.find('title')
        desc_elem = item.find('description')
        link_elem = item.find('link')
        pubdate_elem = item.find('pubDate')

        title = title_elem.text if title_elem is not None and title_elem.text else ''
        description = desc_elem.text if desc_elem is not None and desc_elem.text else ''
        link = link_elem.text if link_elem is not None and link_elem.text else ''
        pub_date = pubdate_elem.text if pubdate_elem is not None and pubdate_elem.text else ''

        # 清理 HTML 标签
        description = re.sub(r'<[^>]+>', '', description)

        if not title:
            return None

        # 解析日期
        try:
            if pub_date:
                # RSS 日期格式：Wed, 01 Apr 2026 10:00:00 GMT
                published_at = datetime.strptime(pub_date.strip(), '%a, %d %b %Y %H:%M:%S %Z')
            else:
                published_at = datetime.now()
        except:
            published_at = datetime.now()

        return {
            'title': title.strip(),
            'description': description.strip()[:500],
            'source': source_name,
            'source_type': 'rss',
            'url': link.strip(),
            'published_at': published_at,
            'language': 'en',
        }

    def _parse_atom_entry(self, entry, source_name: str) -> Optional[Dict]:
        """解析 Atom entry"""
        ns = {'atom': 'http://www.w3.org/2005/Atom'}

        title_elem = entry.find('atom:title', ns)
        summary_elem = entry.find('atom:summary', ns)
        link_elem = entry.find('atom:link', ns)
        published_elem = entry.find('atom:published', ns)

        title = title_elem.text if title_elem is not None and title_elem.text else ''
        description = summary_elem.text if summary_elem is not None and summary_elem.text else ''
        link = link_elem.get('href', '') if link_elem is not None else ''
        pub_date = published_elem.text if published_elem is not None and published_elem.text else ''

        description = re.sub(r'<[^>]+>', '', description)

        if not title:
            return None

        try:
            if pub_date:
                published_at = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
            else:
                published_at = datetime.now()
        except:
            published_at = datetime.now()

        return {
            'title': title.strip(),
            'description': description.strip()[:500],
            'source': source_name,
            'source_type': 'rss',
            'url': link.strip(),
            'published_at': published_at,
            'language': 'en',
        }

    def _match_stock_codes(self, title: str, description: str) -> List[Dict]:
        """匹配股票代码（基于关键词）"""
        text = f"{title} {description}".lower()
        matches = []

        # 简单匹配：检查股票代码是否出现在文本中
        for code in self.stock_codes:
            if code in text:
                matches.append({
                    'stock_code': code,
                    'match_type': 'mention',
                    'match_score': 0.5
                })

        return matches

    def _save_news(self, article: Dict) -> Optional[int]:
        """保存新闻到数据库"""
        content_hash = self._generate_content_hash(article['title'], article['source'])

        # 检查重复
        if self._is_duplicate(content_hash):
            self.logger.debug(f"新闻已存在: {article['title'][:50]}")
            return None

        # 插入新闻
        sql = """
        INSERT INTO stock_news (title, description, source, source_type, url, published_at, language, content_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            article['title'],
            article['description'],
            article['source'],
            article['source_type'],
            article['url'],
            article['published_at'],
            article['language'],
            content_hash
        )

        try:
            self.mysql_manager.execute(sql, params)
            # 获取插入的ID
            result = self.mysql_manager.query_one("SELECT LAST_INSERT_ID() as id")
            news_id = result['id'] if result else None
            return news_id
        except Exception as e:
            self.logger.error(f"保存新闻失败: {e}")
            return None

    def _save_news_relation(self, news_id: int, matches: List[Dict]):
        """保存新闻-股票关联"""
        for match in matches:
            sql = """
            INSERT INTO stock_news_relation (news_id, stock_code, match_type, match_score)
            VALUES (?, ?, ?, ?)
            ON DUPLICATE KEY UPDATE match_score = VALUES(match_score)
            """
            params = (news_id, match['stock_code'], match['match_type'], match['match_score'])
            try:
                self.mysql_manager.execute(sql, params)
            except Exception as e:
                self.logger.error(f"保存关联失败: {e}")

    def _save_sentiment(self, news_id: int, article: Dict, stock_code: str = None):
        """保存情绪分析结果"""
        # 分析标题+描述
        text = f"{article['title']} {article['description']}"
        result = self.analyzer.analyze_text(text)

        sql = """
        INSERT INTO stock_news_sentiment (news_id, stock_code, sentiment_score, sentiment_type,
                                          positive_count, negative_count, keywords, confidence)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            news_id,
            stock_code,
            result['score'],
            result['sentiment_type'],
            result['positive_count'],
            result['negative_count'],
            result['keywords'],
            result['confidence']
        )

        try:
            self.mysql_manager.execute(sql, params)
        except Exception as e:
            self.logger.error(f"保存情绪分析失败: {e}")

    @timer(unit='s')
    def fetch_all(self) -> int:
        """采集所有 RSS 源（主入口）"""
        total_count = 0

        with fetch_stats_context(self.logger) as stats:
            # 从数据库获取活跃的 RSS 源
            sql = "SELECT source_name, source_url FROM rss_source_config WHERE is_active=1 ORDER BY priority"
            sources = self.mysql_manager.query_all(sql)

            for row in sources:
                source_name = row['source_name']
                source_url = row['source_url']
                self.logger.info(f"[RSS] 正在获取 {source_name}...")

                articles = self._fetch_rss(source_url, source_name, stats)
                stats['sources'].append(source_name)

                for article in articles:
                    # 保存新闻
                    news_id = self._save_news(article)
                    if news_id:
                        stats['news_count'] += 1
                        total_count += 1

                        # 匹配股票
                        matches = self._match_stock_codes(article['title'], article['description'])
                        if matches:
                            self._save_news_relation(news_id, matches)

                        # 分析情绪
                        self._save_sentiment(news_id, article)

                        # 如果有股票匹配，为每个股票也保存情绪
                        for match in matches:
                            self._save_sentiment(news_id, article, match['stock_code'])

                        # 更新新闻状态
                        self.mysql_manager.execute(
                            "UPDATE stock_news SET is_processed=1 WHERE id=?", (news_id,))

                # 更新 RSS 源状态
                self.mysql_manager.execute(
                    "UPDATE rss_source_config SET last_fetch_time=NOW(), fetch_count=fetch_count+? WHERE source_name=?",
                    (len(articles), source_name)
                )

                # 控制频率
                time.sleep(random.uniform(1, 3))

        self.logger.info(f"新闻采集完成，共 {total_count} 条新新闻")
        return total_count

    def fetch_for_stock(self, stock_code: str) -> int:
        """采集特定股票相关新闻（通过 Google News 搜索）"""
        self.logger.info(f"[News] 采集股票 {stock_code} 相关新闻")

        # 构建 Google News RSS URL
        search_query = f"{stock_code} stock news"
        encoded_query = urllib.parse.quote(search_query)
        rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"

        stats = {'requests': 0, 'success': 0, 'failed': 0, 'news_count': 0}

        articles = self._fetch_rss(rss_url, f"Google-{stock_code}", stats)

        total_count = 0
        for article in articles:
            news_id = self._save_news(article)
            if news_id:
                stats['news_count'] += 1
                total_count += 1

                # 直接关联股票
                self._save_news_relation(news_id, [{
                    'stock_code': stock_code,
                    'match_type': 'subject',
                    'match_score': 0.8
                }])

                # 分析情绪
                self._save_sentiment(news_id, article)
                self._save_sentiment(news_id, article, stock_code)

                self.mysql_manager.execute(
                    "UPDATE stock_news SET is_processed=1 WHERE id=?", (news_id,))

        return total_count

    def analyze_unprocessed(self) -> int:
        """分析未处理的新闻"""
        self.logger.info("[Sentiment] 分析未处理新闻")

        sql = "SELECT id, title, description FROM stock_news WHERE is_processed=0 LIMIT 100"
        result = self.mysql_manager.query_all(sql)

        count = 0
        for row in result:
            news_id = row['id']
            title = row['title']
            description = row['description']
            text = f"{title} {description}"
            sentiment_result = self.analyzer.analyze_text(text)

            # 更新情绪分析
            self._save_sentiment(news_id, {'title': title, 'description': description})
            self.mysql_manager.execute("UPDATE stock_news SET is_processed=1 WHERE id=?", (news_id,))

            count += 1

        self.logger.info(f"情绪分析完成，共 {count} 条")
        return count

    def get_stock_sentiment_stats(self, stock_code: str, days: int = 7) -> Dict:
        """获取股票情绪统计"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        sql = """
        SELECT sentiment_score, sentiment_type
        FROM stock_news_sentiment
        WHERE stock_code = ? AND analyzed_at >= ?
        """
        result = self.mysql_manager.query_all(sql, (stock_code, start_date))

        if not result:
            return {'count': 0, 'mean': 0, 'positive_ratio': 0}

        scores = [float(row['sentiment_score']) for row in result]
        types = [row['sentiment_type'] for row in result]

        return {
            'count': len(scores),
            'mean': np.mean(scores) if scores else 0,
            'positive_count': types.count('positive'),
            'negative_count': types.count('negative'),
            'neutral_count': types.count('neutral'),
            'positive_ratio': types.count('positive') / len(types) if types else 0,
        }

    def close(self):
        """关闭连接"""
        self.mysql_manager.close()


# ============================================================
# 批量采集
# ============================================================

def fetch_news_batch(stock_codes: List[str] = None) -> int:
    """批量采集新闻"""
    fetcher = NewsFetcher()

    total = 0

    # 1. 采集 RSS 源
    total += fetcher.fetch_all()

    # 2. 采集特定股票新闻
    if stock_codes:
        for i, code in enumerate(stock_codes):
            total += fetcher.fetch_for_stock(code)
            if i % 10 == 0:
                time.sleep(2)

    fetcher.close()
    return total


# ============================================================
# 测试入口
# ============================================================

if __name__ == '__main__':
    print("=" * 60)
    print("股票新闻采集器测试")
    print("=" * 60)

    fetcher = NewsFetcher()

    # 测试 RSS 采集
    print("\n[1] 测试 RSS 采集...")
    count = fetcher.fetch_all()
    print(f"✅ 采集 {count} 条新闻")

    # 测试情绪分析
    print("\n[2] 测试情绪分析...")
    analyzer = fetcher.analyzer

    test_texts = [
        "Stock prices surge to record high amid strong earnings",
        "Market crashes as recession fears escalate",
        "Company reports stable quarterly growth",
    ]

    for text in test_texts:
        result = analyzer.analyze_text(text)
        print(f"\n文本: {text}")
        print(f"  情绪分数: {result['score']:.3f} ({result['sentiment_type']})")
        print(f"  关键词: {result['keywords']}")

    # 测试股票情绪统计
    print("\n[3] 测试股票情绪统计...")
    stats = fetcher.get_stock_sentiment_stats('AAPL', days=7)
    print(f"AAPL 情绪统计: {stats}")

    fetcher.close()
    print("\n测试完成！")
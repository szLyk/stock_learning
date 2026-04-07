# -*- coding: utf-8 -*-
"""
股票财经新闻采集模块（A股专用）

核心功能：
1. AkShare 股票新闻采集（东方财富个股新闻）
2. CCTV财经新闻采集
3. 新闻去重（基于内容哈希）
4. 新闻-股票关联
5. 情绪分析（中文关键词）

数据源：
- ak.stock_news_em() - 东方财富个股新闻（按股票代码）
- ak.news_cctv() - CCTV财经新闻
"""

import hashlib
import json
import re
import time
import random
from contextlib import contextmanager
from datetime import datetime, timedelta
from functools import wraps
from typing import Generator, List, Dict, Optional

import numpy as np
import pandas as pd
import akshare as ak

from logs.logger import LogManager
from src.utils.mysql_tool import MySQLUtil


# ============================================================
# 装饰器
# ============================================================

def timer(unit: str = 's'):
    """计时装饰器"""
    factor = {'s': 1, 'ms': 1000}

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            elapsed = (time.perf_counter() - start) * factor[unit]
            logger = LogManager.get_logger('news_fetcher')
            logger.debug(f"[Timer] {func.__name__} 耗时: {elapsed:.2f}{unit}")
            return result
        return wrapper
    return decorator


def retry(max_attempts: int = 3, delay: float = 2.0):
    """重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = LogManager.get_logger('news_fetcher')
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts:
                        logger.error(f"[Retry] {func.__name__} 失败: {e}")
                        raise
                    logger.warning(f"[Retry] {func.__name__} 第{attempt}次失败，重试...")
                    time.sleep(delay * attempt)
            return None
        return wrapper
    return decorator


@contextmanager
def fetch_stats_context(logger) -> Generator[dict, None, None]:
    """采集统计上下文管理器"""
    stats = {
        'start_time': time.time(),
        'news_count': 0,
        'sources': [],
        'success': 0,
        'failed': 0,
    }
    logger.info("[Stats] 开始采集财经新闻...")
    try:
        yield stats
    finally:
        duration = time.time() - stats['start_time']
        logger.info(f"[Stats] 完成，耗时{duration:.1f}s，采集{stats['news_count']}条")


# ============================================================
# 中文情绪分析器
# ============================================================

class ChineseSentimentAnalyzer:
    """中文情绪分析器（基于关键词）"""

    # 中文情绪词典
    POSITIVE_WORDS = {
        '上涨': 1.0, '涨': 1.0, '涨停': 1.5, '大涨': 1.5, '飙升': 1.5,
        '突破': 1.0, '新高': 1.5, '创新高': 1.5, '走强': 1.0,
        '利好': 1.0, '利好消息': 1.0, '业绩大增': 1.5, '盈利': 1.0,
        '净利润增长': 1.0, '营收增长': 1.0, '超预期': 1.0,
        '增持': 1.0, '买入': 1.0, '推荐': 1.0, '看好': 1.0,
        '反弹': 0.8, '回暖': 0.8, '企稳': 0.5, '触底反弹': 1.0,
        '并购': 0.8, '重组': 0.8, '收购': 0.5, '合作': 0.5,
        '分红': 0.8, '派息': 0.8, '高送转': 1.0,
        '龙头': 0.5, '领跑': 0.5, '市场份额提升': 1.0,
    }

    NEGATIVE_WORDS = {
        '下跌': 1.0, '跌': 1.0, '跌停': 1.5, '大跌': 1.5, '暴跌': 1.5, '闪崩': 1.5,
        '跌破': 1.0, '新低': 1.5, '创新低': 1.5, '走弱': 1.0,
        '利空': 1.0, '利空消息': 1.0, '业绩下滑': 1.5, '亏损': 1.0,
        '净利润下降': 1.0, '营收下降': 1.0, '不及预期': 1.0,
        '减持': 1.0, '卖出': 1.0, '抛售': 1.0, '清仓': 1.5,
        '套牢': 1.0, '被套': 1.0, '止损': 0.8,
        '调查': 0.8, '处罚': 1.0, '违规': 1.0, '立案': 1.5,
        '退市': 1.5, 'ST': 1.0, '*ST': 1.5, '风险警示': 1.0,
        '债务危机': 1.5, '资金链断裂': 1.5, '破产': 2.0,
        '爆雷': 1.5, '财务造假': 2.0, '欺诈': 2.0,
        '诉讼': 0.8, '索赔': 0.8, '纠纷': 0.5,
        '召回': 0.8, '质量问题': 1.0,
    }

    def analyze_text(self, text: str) -> Dict:
        """分析中文文本情绪"""
        if not text:
            return {'score': 0.0, 'type': 'neutral', 'keywords': [], 'confidence': 0.0}

        positive_matches = []
        negative_matches = []
        pos_score = 0.0
        neg_score = 0.0

        for word, weight in self.POSITIVE_WORDS.items():
            if word in text:
                positive_matches.append(word)
                pos_score += weight

        for word, weight in self.NEGATIVE_WORDS.items():
            if word in text:
                negative_matches.append(word)
                neg_score += abs(weight)

        total_keywords = len(positive_matches) + len(negative_matches)

        if total_keywords == 0:
            score = 0.0
            sentiment_type = 'neutral'
            confidence = 0.0
        else:
            score = (pos_score - neg_score) / (pos_score + neg_score + 1)
            confidence = min(total_keywords / 5.0, 1.0)

            if score > 0.15:
                sentiment_type = 'positive'
            elif score < -0.15:
                sentiment_type = 'negative'
            else:
                sentiment_type = 'neutral'

        return {
            'score': round(score, 4),
            'type': sentiment_type,
            'positive_words': positive_matches,
            'negative_words': negative_matches,
            'keywords': positive_matches + negative_matches,
            'confidence': round(confidence, 2),
        }


# ============================================================
# AkShare 新闻采集器
# ============================================================

class StockNewsFetcher:
    """A股财经新闻采集器"""

    def __init__(self):
        self.logger = LogManager.get_logger('stock_news_fetcher')
        self.mysql = MySQLUtil()
        self.mysql.connect()
        self.analyzer = ChineseSentimentAnalyzer()
        self._load_stock_codes()

    def _load_stock_codes(self):
        """加载股票代码列表"""
        try:
            result = self.mysql.query_all(
                "SELECT DISTINCT stock_code FROM stock_basic_info ORDER BY stock_code"
            )
            self.stock_codes = [row['stock_code'] for row in result] if result else []
            self.logger.info(f"加载 {len(self.stock_codes)} 只股票代码")
        except:
            # 如果表不存在，使用默认列表
            self.stock_codes = ['000001', '000002', '600519', '600036']
            self.logger.warning("股票代码表不存在，使用默认列表")

    def _hash_content(self, title: str) -> str:
        """生成内容哈希"""
        return hashlib.md5(title.encode('utf-8')).hexdigest()

    def _is_duplicate(self, content_hash: str) -> bool:
        """检查是否重复"""
        result = self.mysql.query_one(
            "SELECT COUNT(*) as cnt FROM stock_news WHERE content_hash = %s",
            (content_hash,)
        )
        return result['cnt'] > 0 if result else False

    @retry(max_attempts=3, delay=2.0)
    def _fetch_stock_news_akshare(self, stock_code: str) -> List[Dict]:
        """使用 AkShare 获取个股新闻"""
        self.logger.info(f"[AkShare] 获取 {stock_code} 新闻...")

        try:
            df = ak.stock_news_em(symbol=stock_code)

            if df is None or df.empty:
                self.logger.warning(f"{stock_code} 无新闻数据")
                return []

            news_list = []
            for _, row in df.iterrows():
                title = row.get('新闻标题', '')
                content = row.get('新闻内容', '')
                pub_time = row.get('发布时间', '')

                if not title:
                    continue

                # 解析时间
                try:
                    if isinstance(pub_time, str):
                        published_at = datetime.strptime(pub_time, '%Y-%m-%d %H:%M:%S')
                    else:
                        published_at = datetime.now()
                except:
                    published_at = datetime.now()

                news_list.append({
                    'title': title.strip(),
                    'description': content[:500] if content else '',
                    'source': '东方财富',
                    'source_type': 'akshare',
                    'published_at': published_at,
                    'language': 'zh',
                    'stock_code': stock_code,
                })

            return news_list

        except Exception as e:
            self.logger.error(f"AkShare获取{stock_code}失败: {e}")
            return []

    @retry(max_attempts=2, delay=1.0)
    def _fetch_cctv_news(self) -> List[Dict]:
        """获取CCTV财经新闻"""
        self.logger.info("[AkShare] 获取CCTV新闻...")

        try:
            df = ak.news_cctv()

            if df is None or df.empty:
                return []

            news_list = []
            for _, row in df.iterrows():
                title = row.get('title', '')
                content = row.get('content', '')
                date_str = row.get('date', '')

                if not title:
                    continue

                try:
                    published_at = datetime.strptime(str(date_str), '%Y%m%d')
                except:
                    published_at = datetime.now()

                news_list.append({
                    'title': title.strip(),
                    'description': content[:500] if content else '',
                    'source': 'CCTV',
                    'source_type': 'akshare',
                    'published_at': published_at,
                    'language': 'zh',
                })

            return news_list

        except Exception as e:
            self.logger.error(f"CCTV获取失败: {e}")
            return []

    def _save_news(self, news: Dict) -> Optional[int]:
        """保存新闻"""
        content_hash = self._hash_content(news['title'])

        if self._is_duplicate(content_hash):
            return None

        sql = """
        INSERT INTO stock_news (title, description, source, source_type, published_at, language, content_hash)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            news['title'],
            news['description'],
            news['source'],
            news['source_type'],
            news['published_at'],
            news['language'],
            content_hash
        )

        try:
            self.mysql.execute(sql, params)
            result = self.mysql.query_one("SELECT LAST_INSERT_ID() as id")
            return result['id'] if result else None
        except Exception as e:
            self.logger.error(f"保存新闻失败: {e}")
            return None

    def _save_relation(self, news_id: int, stock_code: str, match_type: str = 'subject'):
        """保存新闻-股票关联"""
        sql = """
        INSERT INTO stock_news_relation (news_id, stock_code, match_type, match_score)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE match_type = VALUES(match_type)
        """
        params = (news_id, stock_code, match_type, 0.8)
        try:
            self.mysql.execute(sql, params)
        except Exception as e:
            self.logger.error(f"保存关联失败: {e}")

    def _save_sentiment(self, news_id: int, news: Dict, stock_code: str = None):
        """保存情绪分析"""
        text = f"{news['title']} {news['description']}"
        result = self.analyzer.analyze_text(text)

        sql = """
        INSERT INTO stock_news_sentiment (news_id, stock_code, sentiment_score, sentiment_type,
                                          positive_count, negative_count, keywords, confidence)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            news_id,
            stock_code,
            result['score'],
            result['type'],
            len(result['positive_words']),
            len(result['negative_words']),
            json.dumps(result['keywords']),
            result['confidence']
        )

        try:
            self.mysql.execute(sql, params)
        except Exception as e:
            self.logger.error(f"保存情绪失败: {e}")

    @timer(unit='s')
    def fetch_batch(self, stock_codes: List[str] = None, limit: int = 50) -> int:
        """批量采集股票新闻"""
        codes = stock_codes or self.stock_codes[:limit]

        with fetch_stats_context(self.logger) as stats:
            for i, code in enumerate(codes):
                try:
                    news_list = self._fetch_stock_news_akshare(code)

                    for news in news_list:
                        news_id = self._save_news(news)
                        if news_id:
                            stats['news_count'] += 1
                            self._save_relation(news_id, code, 'subject')
                            self._save_sentiment(news_id, news, code)

                            # 标记已处理
                            self.mysql.execute(
                                "UPDATE stock_news SET is_processed=1 WHERE id=%s", (news_id,)
                            )

                    stats['sources'].append(code)

                    # 控制频率
                    if i % 5 == 0:
                        time.sleep(random.uniform(1, 2))

                except Exception as e:
                    stats['failed'] += 1
                    self.logger.error(f"处理{code}失败: {e}")

        return stats['news_count']

    @timer(unit='s')
    def fetch_market_news(self) -> int:
        """采集市场整体新闻（CCTV）"""
        with fetch_stats_context(self.logger) as stats:
            news_list = self._fetch_cctv_news()

            for news in news_list:
                news_id = self._save_news(news)
                if news_id:
                    stats['news_count'] += 1
                    self._save_sentiment(news_id, news)
                    self.mysql.execute("UPDATE stock_news SET is_processed=1 WHERE id=%s", (news_id,))

            stats['sources'].append('CCTV')

        return stats['news_count']

    def get_sentiment_summary(self, stock_code: str, days: int = 7) -> Dict:
        """获取股票情绪汇总"""
        start_date = datetime.now() - timedelta(days=days)

        result = self.mysql.query_all(
            """
            SELECT sentiment_score, sentiment_type
            FROM stock_news_sentiment
            WHERE stock_code = %s AND analyzed_at >= %s
            """,
            (stock_code, start_date)
        )

        if not result:
            return {'count': 0, 'avg_score': 0}

        scores = [float(r['sentiment_score']) for r in result]
        types = [r['sentiment_type'] for r in result]

        return {
            'count': len(scores),
            'avg_score': np.mean(scores),
            'positive': types.count('positive'),
            'negative': types.count('negative'),
            'neutral': types.count('neutral'),
        }

    def close(self):
        self.mysql.close()


# ============================================================
# 测试
# ============================================================

if __name__ == '__main__':
    print("=" * 60)
    print("A股财经新闻采集器测试")
    print("=" * 60)

    fetcher = StockNewsFetcher()

    # 1. 测试情绪分析
    print("\n[1] 测试中文情绪分析...")
    test_texts = [
        "平安银行一季度业绩大涨，净利润同比增长40%",
        "某股票因财务造假被立案调查，面临退市风险",
        "公司发布年度报告，营收稳定增长",
    ]

    for text in test_texts:
        result = fetcher.analyzer.analyze_text(text)
        print(f"\n文本: {text}")
        print(f"  情绪: {result['type']} (分数={result['score']:.3f})")
        print(f"  正面词: {result['positive_words']}")
        print(f"  负面词: {result['negative_words']}")

    # 2. 测试新闻采集
    print("\n[2] 测试单只股票新闻采集...")
    count = fetcher.fetch_batch(['000001'], limit=1)
    print(f"  采集 {count} 条新闻")

    # 3. 测试CCTV新闻
    print("\n[3] 测试CCTV新闻...")
    count = fetcher.fetch_market_news()
    print(f"  采集 {count} 条CCTV新闻")

    fetcher.close()
    print("\n测试完成!")
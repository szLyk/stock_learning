-- =====================================================
-- 股票新闻采集表结构设计
-- 设计理念：
-- 1. 新闻主表存储新闻元信息
-- 2. 新闻关联表关联股票代码（一条新闻可能涉及多只股票）
-- 3. 情绪分析表存储情绪计算结果
-- =====================================================

USE stock;

-- =====================================================
-- 1. 新闻主表
-- =====================================================
DROP TABLE IF EXISTS stock_news;
CREATE TABLE stock_news (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(500) NOT NULL COMMENT '新闻标题',
    description TEXT COMMENT '新闻摘要/描述',
    source VARCHAR(100) DEFAULT NULL COMMENT '新闻来源（Reuters/BBC/CNBC等）',
    source_type VARCHAR(20) DEFAULT 'rss' COMMENT '来源类型：rss/api/manual',
    url VARCHAR(500) DEFAULT NULL COMMENT '新闻链接',
    published_at DATETIME DEFAULT NULL COMMENT '发布时间',
    fetched_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '采集时间',
    language VARCHAR(10) DEFAULT 'en' COMMENT '语言：en/zh',
    news_type VARCHAR(20) DEFAULT 'market' COMMENT '新闻类型：market/company/industry/macro',
    content_hash VARCHAR(64) DEFAULT NULL COMMENT '内容哈希（用于去重）',
    is_processed TINYINT DEFAULT 0 COMMENT '是否已处理情绪分析：0/1',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_content_hash (content_hash),
    KEY idx_published_at (published_at),
    KEY idx_source (source),
    KEY idx_is_processed (is_processed)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='股票新闻主表';

-- =====================================================
-- 2. 新闻-股票关联表（一条新闻可能涉及多只股票）
-- =====================================================
DROP TABLE IF EXISTS stock_news_relation;
CREATE TABLE stock_news_relation (
    id INT AUTO_INCREMENT PRIMARY KEY,
    news_id INT NOT NULL COMMENT '新闻ID',
    stock_code VARCHAR(10) NOT NULL COMMENT '股票代码',
    match_type VARCHAR(20) DEFAULT 'mention' COMMENT '匹配类型：mention/subject/related',
    match_score DECIMAL(5,2) DEFAULT 0.50 COMMENT '匹配置信度（0-1）',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_news_stock (news_id, stock_code),
    KEY idx_news_id (news_id),
    KEY idx_stock_code (stock_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='新闻-股票关联表';

-- =====================================================
-- 3. 情绪分析结果表
-- =====================================================
DROP TABLE IF EXISTS stock_news_sentiment;
CREATE TABLE stock_news_sentiment (
    id INT AUTO_INCREMENT PRIMARY KEY,
    news_id INT NOT NULL COMMENT '新闻ID',
    stock_code VARCHAR(10) DEFAULT NULL COMMENT '股票代码（可为空，表示市场整体情绪）',
    sentiment_score DECIMAL(5,4) DEFAULT 0 COMMENT '情绪分数（-1到1，正数正面，负数负面）',
    sentiment_type VARCHAR(10) DEFAULT 'neutral' COMMENT '情绪类型：positive/negative/neutral',
    positive_count INT DEFAULT 0 COMMENT '正面关键词数量',
    negative_count INT DEFAULT 0 COMMENT '负面关键词数量',
    keywords TEXT COMMENT '匹配到的关键词（JSON格式）',
    confidence DECIMAL(5,2) DEFAULT 0 COMMENT '置信度（基于关键词数量）',
    analyzed_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '分析时间',
    analyzer_version VARCHAR(20) DEFAULT 'v1.0' COMMENT '分析器版本',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_news_stock (news_id, stock_code),
    KEY idx_news_id (news_id),
    KEY idx_stock_code (stock_code),
    KEY idx_sentiment_type (sentiment_type),
    KEY idx_sentiment_score (sentiment_score)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='新闻情绪分析结果表';

-- =====================================================
-- 4. RSS源配置表（支持动态管理RSS源）
-- =====================================================
DROP TABLE IF EXISTS rss_source_config;
CREATE TABLE rss_source_config (
    id INT AUTO_INCREMENT PRIMARY KEY,
    source_name VARCHAR(50) NOT NULL COMMENT '源名称',
    source_url VARCHAR(500) NOT NULL COMMENT 'RSS URL',
    source_type VARCHAR(10) DEFAULT 'rss' COMMENT '源类型：rss/atom',
    priority INT DEFAULT 1 COMMENT '优先级（1最高）',
    is_active TINYINT DEFAULT 1 COMMENT '是否启用：0/1',
    language VARCHAR(10) DEFAULT 'en' COMMENT '语言',
    category VARCHAR(20) DEFAULT 'market' COMMENT '分类：market/company/industry',
    last_fetch_time DATETIME DEFAULT NULL COMMENT '最后采集时间',
    fetch_count INT DEFAULT 0 COMMENT '累计采集数量',
    error_count INT DEFAULT 0 COMMENT '错误次数',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_source_name (source_name),
    KEY idx_is_active (is_active),
    KEY idx_priority (priority)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='RSS源配置表';

-- =====================================================
-- 5. 情绪词典表（支持动态扩展关键词）
-- =====================================================
DROP TABLE IF EXISTS sentiment_dictionary;
CREATE TABLE sentiment_dictionary (
    id INT AUTO_INCREMENT PRIMARY KEY,
    word VARCHAR(50) NOT NULL COMMENT '关键词',
    word_type VARCHAR(10) NOT NULL COMMENT '词类型：positive/negative',
    weight DECIMAL(5,2) DEFAULT 1.0 COMMENT '权重（正数正面，负数负面）',
    intensity VARCHAR(10) DEFAULT 'normal' COMMENT '强度：strong/normal',
    language VARCHAR(10) DEFAULT 'en' COMMENT '语言',
    category VARCHAR(20) DEFAULT 'general' COMMENT '分类',
    is_active TINYINT DEFAULT 1 COMMENT '是否启用',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_word_lang (word, language),
    KEY idx_word_type (word_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='情绪词典表';

-- =====================================================
-- 6. 初始化RSS源数据（聚焦A股财经新闻）
-- =====================================================
-- 说明：英文源保留但优先级降低，中文源优先级提高
INSERT INTO rss_source_config (source_name, source_url, source_type, priority, is_active, language, category) VALUES
-- === 中文财经新闻源（优先）===
('eastmoney_news', 'https://news.10jqka.com.cn/news_list.shtml', 'web', 1, 0, 'zh', 'market'),
('sina_finance', 'https://finance.sina.com.cn/stock/', 'web', 1, 0, 'zh', 'market'),
('cls_cn', 'https://www.cls.cn/telegraph', 'web', 1, 0, 'zh', 'realtime'),
('yicai', 'https://www.yicai.com/news/', 'web', 2, 0, 'zh', 'market'),
('caixin', 'https://www.caixin.com/', 'web', 2, 0, 'zh', 'macro'),
-- === API 接口（AkShare数据源）===
('akshare_news', '', 'api', 1, 1, 'zh', 'market'),
-- === 英文财经新闻源（备用）===
('reuters_google', 'https://news.google.com/rss/search?q=reuters+business&hl=en-US&gl=US&ceid=US:en', 'rss', 3, 0, 'en', 'market'),
('google_business', 'https://news.google.com/rss/search?q=stock+market+finance&hl=en-US&gl=US&ceid=US:en', 'rss', 3, 0, 'en', 'market'),
('bbc_business', 'https://feeds.bbci.co.uk/news/business/rss.xml', 'rss', 4, 0, 'en', 'market'),
('cnbc_markets', 'https://www.cnbc.com/id/10000664/device/rss/rss.html', 'rss', 4, 0, 'en', 'market'),
('marketwatch', 'https://www.marketwatch.com/rss/topstories', 'rss', 4, 0, 'en', 'market')
ON DUPLICATE KEY UPDATE source_url = VALUES(source_url), priority = VALUES(priority), is_active = VALUES(is_active);

-- =====================================================
-- 7. 初始化情绪词典数据
-- =====================================================
-- 正面词汇
INSERT INTO sentiment_dictionary (word, word_type, weight, intensity, language) VALUES
-- 强正面词
('surge', 'positive', 1.5, 'strong', 'en'),
('boom', 'positive', 1.5, 'strong', 'en'),
('record', 'positive', 1.5, 'strong', 'en'),
('rally', 'positive', 1.5, 'strong', 'en'),
('unprecedented', 'positive', 1.5, 'strong', 'en'),
('all-time', 'positive', 1.5, 'strong', 'en'),
-- 一般正面词
('rise', 'positive', 1.0, 'normal', 'en'),
('rising', 'positive', 1.0, 'normal', 'en'),
('gain', 'positive', 1.0, 'normal', 'en'),
('gaining', 'positive', 1.0, 'normal', 'en'),
('profit', 'positive', 1.0, 'normal', 'en'),
('profits', 'positive', 1.0, 'normal', 'en'),
('growth', 'positive', 1.0, 'normal', 'en'),
('growing', 'positive', 1.0, 'normal', 'en'),
('increase', 'positive', 1.0, 'normal', 'en'),
('increasing', 'positive', 1.0, 'normal', 'en'),
('up', 'positive', 1.0, 'normal', 'en'),
('higher', 'positive', 1.0, 'normal', 'en'),
('positive', 'positive', 1.0, 'normal', 'en'),
('strong', 'positive', 1.0, 'normal', 'en'),
('success', 'positive', 1.0, 'normal', 'en'),
('successful', 'positive', 1.0, 'normal', 'en'),
('recover', 'positive', 1.0, 'normal', 'en'),
('recovery', 'positive', 1.0, 'normal', 'en'),
('beat', 'positive', 1.0, 'normal', 'en'),
('beating', 'positive', 1.0, 'normal', 'en'),
('exceed', 'positive', 1.0, 'normal', 'en'),
('exceeding', 'positive', 1.0, 'normal', 'en'),
('outperform', 'positive', 1.0, 'normal', 'en'),
('bullish', 'positive', 1.0, 'normal', 'en'),
('buy', 'positive', 1.0, 'normal', 'en'),
('upgrade', 'positive', 1.0, 'normal', 'en'),
('optimistic', 'positive', 1.0, 'normal', 'en'),
('hope', 'positive', 1.0, 'normal', 'en'),
('hopeful', 'positive', 1.0, 'normal', 'en'),
('peak', 'positive', 1.0, 'normal', 'en'),
('high', 'positive', 1.0, 'normal', 'en')
ON DUPLICATE KEY UPDATE weight = VALUES(weight);

-- 负面词汇
INSERT INTO sentiment_dictionary (word, word_type, weight, intensity, language) VALUES
-- 强负面词
('crash', 'negative', -1.5, 'strong', 'en'),
('plunge', 'negative', -1.5, 'strong', 'en'),
('crisis', 'negative', -1.5, 'strong', 'en'),
('recession', 'negative', -1.5, 'strong', 'en'),
('sell-off', 'negative', -1.5, 'strong', 'en'),
('collapse', 'negative', -1.5, 'strong', 'en'),
-- 一般负面词
('fall', 'negative', -1.0, 'normal', 'en'),
('falling', 'negative', -1.0, 'normal', 'en'),
('drop', 'negative', -1.0, 'normal', 'en'),
('dropping', 'negative', -1.0, 'normal', 'en'),
('decline', 'negative', -1.0, 'normal', 'en'),
('declining', 'negative', -1.0, 'normal', 'en'),
('loss', 'negative', -1.0, 'normal', 'en'),
('losses', 'negative', -1.0, 'normal', 'en'),
('sink', 'negative', -1.0, 'normal', 'en'),
('sinking', 'negative', -1.0, 'normal', 'en'),
('down', 'negative', -1.0, 'normal', 'en'),
('lower', 'negative', -1.0, 'normal', 'en'),
('decrease', 'negative', -1.0, 'normal', 'en'),
('decreasing', 'negative', -1.0, 'normal', 'en'),
('negative', 'negative', -1.0, 'normal', 'en'),
('weak', 'negative', -1.0, 'normal', 'en'),
('weakness', 'negative', -1.0, 'normal', 'en'),
('fail', 'negative', -1.0, 'normal', 'en'),
('failure', 'negative', -1.0, 'normal', 'en'),
('failed', 'negative', -1.0, 'normal', 'en'),
('concern', 'negative', -1.0, 'normal', 'en'),
('concerns', 'negative', -1.0, 'normal', 'en'),
('worried', 'negative', -1.0, 'normal', 'en'),
('fear', 'negative', -1.0, 'normal', 'en'),
('fears', 'negative', -1.0, 'normal', 'en'),
('sell', 'negative', -1.0, 'normal', 'en'),
('selling', 'negative', -1.0, 'normal', 'en'),
('bearish', 'negative', -1.0, 'normal', 'en'),
('downgrade', 'negative', -1.0, 'normal', 'en'),
('pessimistic', 'negative', -1.0, 'normal', 'en'),
('risk', 'negative', -1.0, 'normal', 'en'),
('risky', 'negative', -1.0, 'normal', 'en'),
('miss', 'negative', -1.0, 'normal', 'en'),
('missing', 'negative', -1.0, 'normal', 'en'),
('underperform', 'negative', -1.0, 'normal', 'en'),
('worse', 'negative', -1.0, 'normal', 'en'),
('worst', 'negative', -1.0, 'normal', 'en')
ON DUPLICATE KEY UPDATE weight = VALUES(weight);

-- =====================================================
-- 8. 验证表创建
-- =====================================================
SELECT 'stock_news' as table_name, COUNT(*) as cnt FROM stock_news
UNION ALL
SELECT 'stock_news_relation', COUNT(*) FROM stock_news_relation
UNION ALL
SELECT 'stock_news_sentiment', COUNT(*) FROM stock_news_sentiment
UNION ALL
SELECT 'rss_source_config', COUNT(*) FROM rss_source_config
UNION ALL
SELECT 'sentiment_dictionary', COUNT(*) FROM sentiment_dictionary;
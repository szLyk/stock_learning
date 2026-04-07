-- =====================================================
-- 股票新闻采集表结构（国内外分开）
-- 设计理念：
-- 1. 国内A股新闻表 - 来自AkShare（东方财富个股新闻）
-- 2. 国外科技新闻表 - 来自RSS（Reuters/BBC/CNBC/MarketWatch）
-- 3. 新闻影响关联表 - 国外新闻对A股的影响映射
-- =====================================================

USE stock;

-- =====================================================
-- 1. 国内A股新闻表
-- =====================================================
DROP TABLE IF EXISTS stock_news_cn;
CREATE TABLE stock_news_cn (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(500) NOT NULL COMMENT '新闻标题',
    content TEXT COMMENT '新闻内容',
    source VARCHAR(100) DEFAULT NULL COMMENT '新闻来源（东方财富/CCTV/新浪财经）',
    source_type VARCHAR(20) DEFAULT 'akshare' COMMENT '来源类型',
    stock_code VARCHAR(10) DEFAULT NULL COMMENT '关联股票代码',
    stock_name VARCHAR(50) DEFAULT NULL COMMENT '股票简称',
    published_at DATETIME DEFAULT NULL COMMENT '发布时间',
    fetched_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '采集时间',
    content_hash VARCHAR(64) DEFAULT NULL COMMENT '内容哈希（去重）',
    is_processed TINYINT DEFAULT 0 COMMENT '是否已分析',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_hash (content_hash),
    KEY idx_stock_code (stock_code),
    KEY idx_published_at (published_at),
    KEY idx_source (source)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='国内A股新闻表';

-- =====================================================
-- 2. 国外科技新闻表
-- =====================================================
DROP TABLE IF EXISTS stock_news_global;
CREATE TABLE stock_news_global (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(500) NOT NULL COMMENT '新闻标题',
    description TEXT COMMENT '新闻摘要',
    source VARCHAR(100) DEFAULT NULL COMMENT '新闻来源（Reuters/BBC/CNBC/MarketWatch）',
    source_url VARCHAR(500) DEFAULT NULL COMMENT '原文链接',
    published_at DATETIME DEFAULT NULL COMMENT '发布时间',
    fetched_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '采集时间',
    language VARCHAR(10) DEFAULT 'en' COMMENT '语言',
    category VARCHAR(50) DEFAULT 'tech' COMMENT '分类（tech/semiconductor/AI/chip）',
    related_company VARCHAR(100) DEFAULT NULL COMMENT '相关公司（NVIDIA/Micron/AMD/Tesla）',
    content_hash VARCHAR(64) DEFAULT NULL COMMENT '内容哈希（去重）',
    sentiment_score DECIMAL(5,4) DEFAULT 0 COMMENT '情绪分数（英文分析）',
    sentiment_type VARCHAR(10) DEFAULT 'neutral' COMMENT '情绪类型',
    is_processed TINYINT DEFAULT 0 COMMENT '是否已分析',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_hash (content_hash),
    KEY idx_published_at (published_at),
    KEY idx_source (source),
    KEY idx_category (category),
    KEY idx_related_company (related_company)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='国外科技新闻表';

-- =====================================================
-- 3. 新闻影响关联表（国外新闻对A股的影响）
-- =====================================================
DROP TABLE IF EXISTS stock_news_impact;
CREATE TABLE stock_news_impact (
    id INT AUTO_INCREMENT PRIMARY KEY,
    global_news_id INT NOT NULL COMMENT '国外新闻ID',
    cn_stock_code VARCHAR(10) NOT NULL COMMENT 'A股股票代码',
    cn_stock_name VARCHAR(50) DEFAULT NULL COMMENT 'A股股票简称',
    impact_type VARCHAR(20) DEFAULT 'related' COMMENT '影响类型：direct/indirect/sector',
    impact_reason VARCHAR(200) DEFAULT NULL COMMENT '影响原因（产业链/竞争关系/供需）',
    impact_score DECIMAL(5,2) DEFAULT 0.50 COMMENT '影响强度（0-1）',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_news_stock (global_news_id, cn_stock_code),
    KEY idx_global_news (global_news_id),
    KEY idx_cn_stock (cn_stock_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='新闻影响关联表';

-- =====================================================
-- 4. 国内新闻情绪分析表
-- =====================================================
DROP TABLE IF EXISTS stock_news_sentiment_cn;
CREATE TABLE stock_news_sentiment_cn (
    id INT AUTO_INCREMENT PRIMARY KEY,
    news_id INT NOT NULL COMMENT '新闻ID',
    stock_code VARCHAR(10) DEFAULT NULL COMMENT '股票代码',
    sentiment_score DECIMAL(5,4) DEFAULT 0 COMMENT '情绪分数',
    sentiment_type VARCHAR(10) DEFAULT 'neutral' COMMENT '情绪类型',
    positive_words TEXT COMMENT '正面关键词JSON',
    negative_words TEXT COMMENT '负面关键词JSON',
    confidence DECIMAL(5,2) DEFAULT 0 COMMENT '置信度',
    analyzed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_news_stock (news_id, stock_code),
    KEY idx_news_id (news_id),
    KEY idx_sentiment_type (sentiment_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='国内新闻情绪分析表';

-- =====================================================
-- 5. 科技公司映射表（美股→A股产业链映射）
-- =====================================================
DROP TABLE IF EXISTS tech_company_mapping;
CREATE TABLE tech_company_mapping (
    id INT AUTO_INCREMENT PRIMARY KEY,
    us_company VARCHAR(100) NOT NULL COMMENT '美股公司（NVIDIA/Micron/AMD/Intel/Tesla）',
    us_ticker VARCHAR(20) DEFAULT NULL COMMENT '美股代码（NVDA/MU/AMD/INTC/TSLA）',
    sector VARCHAR(50) DEFAULT NULL COMMENT '行业（半导体/AI芯片/新能源）',
    cn_related_stocks TEXT COMMENT '相关A股（JSON格式：产业链上下游）',
    impact_logic VARCHAR(200) DEFAULT NULL COMMENT '影响逻辑说明',
    priority INT DEFAULT 1 COMMENT '优先级',
    is_active TINYINT DEFAULT 1 COMMENT '是否关注',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_us_company (us_company),
    KEY idx_sector (sector)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='科技公司映射表';

-- =====================================================
-- 6. RSS源配置表（保留国外源）
-- =====================================================
DROP TABLE IF EXISTS rss_source_config;
CREATE TABLE rss_source_config (
    id INT AUTO_INCREMENT PRIMARY KEY,
    source_name VARCHAR(50) NOT NULL COMMENT '源名称',
    source_url VARCHAR(500) NOT NULL COMMENT 'RSS URL',
    source_type VARCHAR(10) DEFAULT 'rss' COMMENT '源类型：rss/api',
    priority INT DEFAULT 1 COMMENT '优先级',
    is_active TINYINT DEFAULT 1 COMMENT '是否启用',
    language VARCHAR(10) DEFAULT 'en' COMMENT '语言：en/zh',
    category VARCHAR(50) DEFAULT 'tech' COMMENT '分类：tech/market/semiconductor',
    keywords VARCHAR(200) DEFAULT NULL COMMENT '搜索关键词',
    last_fetch_time DATETIME DEFAULT NULL COMMENT '最后采集时间',
    fetch_count INT DEFAULT 0 COMMENT '累计采集数',
    error_count INT DEFAULT 0 COMMENT '错误次数',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_source_name (source_name),
    KEY idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='RSS源配置表';

-- =====================================================
-- 7. 初始化RSS源（国外科技新闻源）
-- =====================================================
INSERT INTO rss_source_config (source_name, source_url, source_type, priority, is_active, language, category, keywords) VALUES
-- === 科技/半导体新闻（优先）===
('reuters_tech', 'https://news.google.com/rss/search?q=NVIDIA+OR+Micron+OR+AMD+OR+semiconductor+when:24h&hl=en-US&gl=US&ceid=US:en', 'rss', 1, 1, 'en', 'semiconductor', 'NVIDIA,Micron,AMD,Intel'),
('cnbc_tech', 'https://www.cnbc.com/id/10000664/device/rss/rss.html', 'rss', 1, 1, 'en', 'tech', 'chip,AI,semiconductor'),
('marketwatch_tech', 'https://www.marketwatch.com/rss/topstories', 'rss', 2, 1, 'en', 'tech', 'NVDA,MU,TSLA'),
('bbc_tech', 'https://feeds.bbci.co.uk/news/technology/rss.xml', 'rss', 2, 1, 'en', 'tech', 'chip,AI'),
-- === 财经市场新闻（备用）===
('google_finance', 'https://news.google.com/rss/search?q=stock+market+finance+when:24h&hl=en-US&gl=US&ceid=US:en', 'rss', 3, 1, 'en', 'market', 'market,stock'),
('reuters_business', 'https://news.google.com/rss/search?q=reuters+business+finance&hl=en-US&gl=US&ceid=US:en', 'rss', 3, 1, 'en', 'market', 'business')
ON DUPLICATE KEY UPDATE source_url = VALUES(source_url);

-- =====================================================
-- 8. 初始化科技公司映射
-- =====================================================
INSERT INTO tech_company_mapping (us_company, us_ticker, sector, cn_related_stocks, impact_logic, priority) VALUES
-- === 半导体芯片 ===
('NVIDIA', 'NVDA', 'AI芯片/GPU',
 '["寒武纪", "海光信息", "龙芯中科", "景嘉微", "中科曙光"]',
 '国产GPU替代，AI算力需求带动产业链', 1),

('Micron', 'MU', '存储芯片',
 '["长江存储", "兆易创新", "北京君正", "澜起科技", "佰维存储"]',
 '存储价格上涨，国产替代机遇', 1),

('AMD', 'AMD', 'CPU/GPU',
 '["海光信息", "龙芯中科", "中国长城", "中科曙光"]',
 '国产CPU替代，服务器市场', 1),

('Intel', 'INTC', 'CPU',
 '["龙芯中科", "海光信息", "中国长城"]',
 '国产CPU替代机遇', 2),

('Qualcomm', 'QCOM', '通信芯片',
 '["紫光展锐", "翱捷科技", "乐鑫信息"]',
 '手机芯片国产替代', 2),

('Texas Instruments', 'TXN', '模拟芯片',
 '["圣邦股份", "思瑞浦", "纳芯微", "帝奥微"]',
 '模拟芯片国产替代', 2),

-- === 新能源汽车 ===
('Tesla', 'TSLA', '新能源汽车',
 '["比亚迪", "宁德时代", "蔚来", "小鹏", "理想", "亿纬锂能"]',
 '电动车技术路线，电池需求', 1),

('Tesla Energy', 'TSLA', '储能',
 '["宁德时代", "比亚迪", "亿纬锂能", "国轩高科"]',
 '储能电池需求', 2),

-- === AI人工智能 ===
('Microsoft', 'MSFT', 'AI软件',
 '["科大讯飞", "拓尔思", "云从科技", "海康威视"]',
 'AI应用落地，大模型竞争', 2),

('Google', 'GOOGL', 'AI/云计算',
 '["百度", "阿里巴巴", "腾讯", "金山云"]',
 'AI大模型竞争', 2),

('Apple', 'AAPL', '消费电子',
 '["立讯精密", "歌尔股份", "蓝思科技", "鹏鼎控股"]',
 '供应链订单，消费电子需求', 1),

('Amazon', 'AMZN', '云计算/AI',
 '["阿里巴巴", "腾讯", "光环新网", "数据港"]',
 '云计算需求', 2)

ON DUPLICATE KEY UPDATE cn_related_stocks = VALUES(cn_related_stocks);

-- =====================================================
-- 9. 初始化情绪词典（英文+中文）
-- =====================================================
DROP TABLE IF EXISTS sentiment_dictionary;
CREATE TABLE sentiment_dictionary (
    id INT AUTO_INCREMENT PRIMARY KEY,
    word VARCHAR(50) NOT NULL COMMENT '关键词',
    weight DECIMAL(5,2) NOT NULL COMMENT '权重（正=正面，负=负面）',
    language VARCHAR(10) DEFAULT 'en' COMMENT '语言',
    category VARCHAR(20) DEFAULT 'general' COMMENT '分类',
    is_active TINYINT DEFAULT 1,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_word_lang (word, language)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='情绪词典表';

-- 英文正面词
INSERT INTO sentiment_dictionary (word, weight, language) VALUES
('surge', 1.5, 'en'), ('boom', 1.5, 'en'), ('record', 1.5, 'en'), ('rally', 1.5, 'en'),
('rise', 1.0, 'en'), ('gain', 1.0, 'en'), ('profit', 1.0, 'en'), ('growth', 1.0, 'en'),
('increase', 1.0, 'en'), ('beat', 1.0, 'en'), ('upgrade', 1.0, 'en'), ('bullish', 1.0, 'en'),
('strong', 1.0, 'en'), ('positive', 1.0, 'en'), ('outperform', 1.0, 'en'), ('high', 1.0, 'en')
ON DUPLICATE KEY UPDATE weight = VALUES(weight);

-- 英文负面词
INSERT INTO sentiment_dictionary (word, weight, language) VALUES
('crash', -1.5, 'en'), ('plunge', -1.5, 'en'), ('crisis', -1.5, 'en'), ('collapse', -1.5, 'en'),
('fall', -1.0, 'en'), ('drop', -1.0, 'en'), ('decline', -1.0, 'en'), ('loss', -1.0, 'en'),
('down', -1.0, 'en'), ('weak', -1.0, 'en'), ('miss', -1.0, 'en'), ('downgrade', -1.0, 'en'),
('bearish', -1.0, 'en'), ('negative', -1.0, 'en'), ('fear', -1.0, 'en'), ('concern', -1.0, 'en')
ON DUPLICATE KEY UPDATE weight = VALUES(weight);

-- 中文正面词
INSERT INTO sentiment_dictionary (word, weight, language) VALUES
('上涨', 1.0, 'zh'), ('涨停', 1.5, 'zh'), ('大涨', 1.5, 'zh'), ('飙升', 1.5, 'zh'),
('利好', 1.0, 'zh'), ('业绩大增', 1.5, 'zh'), ('盈利', 1.0, 'zh'), ('增长', 1.0, 'zh'),
('突破', 1.0, 'zh'), ('新高', 1.5, 'zh'), ('增持', 1.0, 'zh'), ('买入', 1.0, 'zh'),
('反弹', 0.8, 'zh'), ('企稳', 0.5, 'zh'), ('超预期', 1.0, 'zh'), ('分红', 0.8, 'zh')
ON DUPLICATE KEY UPDATE weight = VALUES(weight);

-- 中文负面词
INSERT INTO sentiment_dictionary (word, weight, language) VALUES
('下跌', -1.0, 'zh'), ('跌停', -1.5, 'zh'), ('暴跌', -1.5, 'zh'), ('大跌', -1.5, 'zh'),
('利空', -1.0, 'zh'), ('业绩下滑', -1.5, 'zh'), ('亏损', -1.0, 'zh'), ('减持', -1.0, 'zh'),
('跌破', -1.0, 'zh'), ('新低', -1.5, 'zh'), ('卖出', -1.0, 'zh'), ('清仓', -1.5, 'zh'),
('调查', -0.8, 'zh'), ('处罚', -1.0, 'zh'), ('爆雷', -1.5, 'zh'), ('退市', -2.0, 'zh')
ON DUPLICATE KEY UPDATE weight = VALUES(weight);

-- =====================================================
-- 10. 验证
-- =====================================================
SELECT 'stock_news_cn' as tbl, COUNT(*) as cnt FROM stock_news_cn
UNION ALL SELECT 'stock_news_global', COUNT(*) FROM stock_news_global
UNION ALL SELECT 'stock_news_impact', COUNT(*) FROM stock_news_impact
UNION ALL SELECT 'tech_company_mapping', COUNT(*) FROM tech_company_mapping
UNION ALL SELECT 'rss_source_config', COUNT(*) FROM rss_source_config
UNION ALL SELECT 'sentiment_dictionary', COUNT(*) FROM sentiment_dictionary;
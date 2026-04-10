-- 指数分钟线数据表
-- 创建日期：2026-04-10
-- 用途：存储从东方财富爬取的指数分钟线历史数据

-- =====================================================
-- 表：index_stock_history_min_price
-- 说明：指数分钟线数据表，支持多种频率（5/15/30/60分钟）
-- =====================================================

CREATE TABLE IF NOT EXISTS `index_stock_history_min_price` (
  `id` int NOT NULL AUTO_INCREMENT,
  `stock_code` varchar(20) NOT NULL COMMENT '指数代码（如000001）',
  `stock_date` date NOT NULL COMMENT '交易日期',
  `stock_time` varchar(20) NOT NULL COMMENT '时间点（如09:30、10:00）',
  `min_type` int NOT NULL COMMENT '分钟线类型：5=5分钟,15=15分钟,30=30分钟,60=60分钟',
  `open_price` decimal(10,4) DEFAULT NULL COMMENT '开盘价',
  `high_price` decimal(10,4) DEFAULT NULL COMMENT '最高价',
  `low_price` decimal(10,4) DEFAULT NULL COMMENT '最低价',
  `close_price` decimal(10,4) DEFAULT NULL COMMENT '收盘价',
  `trading_volume` decimal(20,4) DEFAULT NULL COMMENT '成交量',
  `trading_amount` decimal(20,4) DEFAULT NULL COMMENT '成交额',
  `amplitude` decimal(10,4) DEFAULT NULL COMMENT '振幅（%）',
  `change_pct` decimal(10,4) DEFAULT NULL COMMENT '涨跌幅（%）',
  `change_amt` decimal(10,4) DEFAULT NULL COMMENT '涨跌额',
  `market_type` varchar(5) NOT NULL COMMENT '市场类型：sh|sz',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_index_min_price` (`stock_code`, `market_type`, `stock_date`, `stock_time`, `min_type`) USING BTREE,
  KEY `idx_stock_date` (`stock_date`) USING BTREE,
  KEY `idx_stock_code_date` (`stock_code`, `stock_date`) USING BTREE,
  KEY `idx_min_type` (`min_type`) USING BTREE,
  KEY `idx_stock_min_type` (`stock_code`, `min_type`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='指数分钟线数据表';

-- =====================================================
-- 表：index_minute_progress（进度记录表）
-- 说明：记录爬取进度，支持断点续传
-- =====================================================

CREATE TABLE IF NOT EXISTS `index_minute_progress` (
  `id` int NOT NULL AUTO_INCREMENT,
  `stock_code` varchar(20) NOT NULL COMMENT '指数代码',
  `market_type` varchar(5) NOT NULL COMMENT '市场类型：sh|sz',
  `min_type` int NOT NULL COMMENT '分钟线类型：5=5分钟,15=15分钟,30=30分钟,60=60分钟',
  `last_fetch_date` date DEFAULT NULL COMMENT '最后爬取日期',
  `last_fetch_time` varchar(20) DEFAULT NULL COMMENT '最后爬取时间点',
  `total_records` int DEFAULT 0 COMMENT '已爬取总条数',
  `status` varchar(20) DEFAULT 'pending' COMMENT '状态：pending/running/completed/failed',
  `error_msg` text DEFAULT NULL COMMENT '错误信息',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_progress` (`stock_code`, `market_type`, `min_type`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='指数分钟线爬取进度表';
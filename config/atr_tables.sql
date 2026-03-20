-- ATR 指标表结构（日/周/月三周期）
-- 创建时间：2026-03-20
-- 说明：使用 TA-Lib 计算 ATR 指标

USE `stock`;

-- --------------------------------------------------------
-- Table structure for table `stock_date_atr` (日线 ATR)
-- --------------------------------------------------------
DROP TABLE IF EXISTS `stock_date_atr`;
CREATE TABLE `stock_date_atr` (
  `stock_code` varchar(20) NOT NULL COMMENT '证券代码',
  `stock_date` date NOT NULL COMMENT '交易所行情日期',
  `tr` decimal(10,4) DEFAULT NULL COMMENT '真实波动幅度 (TR)',
  `atr` decimal(10,4) DEFAULT NULL COMMENT '平均真实波动幅度 (ATR)',
  `natr` decimal(10,4) DEFAULT NULL COMMENT '归一化 ATR (%)',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`stock_code`,`stock_date`) USING BTREE,
  KEY `index_stock_date` (`stock_date`) USING BTREE,
  KEY `index_stock_date_price` (`stock_code`,`stock_date`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='股票日线 ATR 指标表';

-- --------------------------------------------------------
-- Table structure for table `stock_week_atr` (周线 ATR)
-- --------------------------------------------------------
DROP TABLE IF EXISTS `stock_week_atr`;
CREATE TABLE `stock_week_atr` (
  `stock_code` varchar(20) NOT NULL COMMENT '证券代码',
  `stock_date` date NOT NULL COMMENT '周线截止日期',
  `tr` decimal(10,4) DEFAULT NULL COMMENT '真实波动幅度 (TR)',
  `atr` decimal(10,4) DEFAULT NULL COMMENT '平均真实波动幅度 (ATR)',
  `natr` decimal(10,4) DEFAULT NULL COMMENT '归一化 ATR (%)',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`stock_code`,`stock_date`) USING BTREE,
  KEY `index_stock_date` (`stock_date`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='股票周线 ATR 指标表';

-- --------------------------------------------------------
-- Table structure for table `stock_month_atr` (月线 ATR)
-- --------------------------------------------------------
DROP TABLE IF EXISTS `stock_month_atr`;
CREATE TABLE `stock_month_atr` (
  `stock_code` varchar(20) NOT NULL COMMENT '证券代码',
  `stock_date` date NOT NULL COMMENT '月线截止日期',
  `tr` decimal(10,4) DEFAULT NULL COMMENT '真实波动幅度 (TR)',
  `atr` decimal(10,4) DEFAULT NULL COMMENT '平均真实波动幅度 (ATR)',
  `natr` decimal(10,4) DEFAULT NULL COMMENT '归一化 ATR (%)',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`stock_code`,`stock_date`) USING BTREE,
  KEY `index_stock_date` (`stock_date`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='股票月线 ATR 指标表';

-- --------------------------------------------------------
-- 更新记录表字段（在 update_stock_record 表中添加 ATR 更新记录）
-- --------------------------------------------------------
ALTER TABLE `update_stock_record` 
ADD COLUMN `update_stock_date_atr` date DEFAULT '1990-01-01' COMMENT 'ATR 值日线更新记录' AFTER `update_stock_month_adx`,
ADD COLUMN `update_stock_week_atr` date DEFAULT '1990-01-01' COMMENT 'ATR 值周线更新记录' AFTER `update_stock_date_atr`,
ADD COLUMN `update_stock_month_atr` date DEFAULT '1990-01-01' COMMENT 'ATR 值月线更新记录' AFTER `update_stock_week_atr`;

-- --------------------------------------------------------
-- 示例查询
-- --------------------------------------------------------

-- 查询单只股票的日线 ATR
SELECT 
    a.stock_code,
    a.stock_date,
    a.tr,
    a.atr,
    a.natr,
    p.close_price
FROM stock_date_atr a
JOIN stock_history_date_price p ON a.stock_code = p.stock_code AND a.stock_date = p.stock_date
WHERE a.stock_code = '000001'
ORDER BY a.stock_date DESC
LIMIT 30;

-- 查询 ATR 最高的股票（波动最大）
SELECT 
    s.stock_code,
    s.stock_name,
    a.atr,
    a.natr,
    p.close_price
FROM stock_date_atr a
JOIN stock_basic s ON a.stock_code = s.stock_code
JOIN stock_history_date_price p ON a.stock_code = p.stock_code AND a.stock_date = p.stock_date
WHERE a.stock_date = CURDATE()
ORDER BY a.natr DESC
LIMIT 20;

-- 查询 ATR 突破的股票（波动率放大）
SELECT 
    a.stock_code,
    a.stock_date,
    a.atr,
    a.natr,
    (a.atr / LAG(a.atr, 5) OVER (PARTITION BY a.stock_code ORDER BY a.stock_date)) as atr_ratio
FROM stock_date_atr a
WHERE a.stock_date >= DATE_SUB(CURDATE(), INTERVAL 10 DAY)
HAVING atr_ratio > 1.5
ORDER BY atr_ratio DESC
LIMIT 20;

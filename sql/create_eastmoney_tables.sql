-- =====================================================
-- 东方财富数据采集 - 必需的数据表
-- 执行前请确保：SET NAMES utf8mb4;
-- =====================================================

SET NAMES utf8mb4;
USE stock;

-- =====================================================
-- 1. 资金流向表（包含北向资金）
-- =====================================================
DROP TABLE IF EXISTS `stock_capital_flow`;

CREATE TABLE `stock_capital_flow` (
  `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
  `stock_code` VARCHAR(10) NOT NULL COMMENT '股票代码',
  `stock_date` DATE NOT NULL COMMENT '交易日期',
  `main_net_in` DECIMAL(15,2) DEFAULT 0 COMMENT '主力净流入 (万元)',
  `sm_net_in` DECIMAL(15,2) DEFAULT 0 COMMENT '小单净流入 (万元)',
  `mm_net_in` DECIMAL(15,2) DEFAULT 0 COMMENT '中单净流入 (万元)',
  `bm_net_in` DECIMAL(15,2) DEFAULT 0 COMMENT '大单净流入 (万元)',
  `north_hold` DECIMAL(15,2) DEFAULT NULL COMMENT '北向资金持仓 (万股)',
  `north_net_in` DECIMAL(15,2) DEFAULT 0 COMMENT '北向资金净流入 (万股)',
  `margin_balance` DECIMAL(15,2) DEFAULT NULL COMMENT '融资余额 (万元)',
  `market_type` VARCHAR(10) COMMENT '市场类型',
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY `uk_code_date` (`stock_code`, `stock_date`),
  KEY `idx_stock_date` (`stock_code`, `stock_date`),
  KEY `idx_main_net` (`main_net_in`),
  KEY `idx_north_net` (`north_net_in`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='股票资金流向表';

-- =====================================================
-- 2. 股东筹码信息表
-- =====================================================
DROP TABLE IF EXISTS `stock_shareholder_info`;

CREATE TABLE `stock_shareholder_info` (
  `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
  `stock_code` VARCHAR(10) NOT NULL COMMENT '股票代码',
  `report_date` DATE NOT NULL COMMENT '报告日期',
  `shareholder_count` INT DEFAULT NULL COMMENT '股东总人数',
  `shareholder_change` DECIMAL(10,2) DEFAULT NULL COMMENT '股东人数变化率',
  `avg_hold_per_household` DECIMAL(15,2) DEFAULT NULL COMMENT '户均持股数',
  `institution_hold_ratio` DECIMAL(10,2) DEFAULT NULL COMMENT '机构持仓比例',
  `fund_hold_ratio` DECIMAL(10,2) DEFAULT NULL COMMENT '基金持仓比例',
  `executive_hold` DECIMAL(15,2) DEFAULT NULL COMMENT '高管持股数',
  `executive_hold_ratio` DECIMAL(10,2) DEFAULT NULL COMMENT '高管持股比例',
  `top10_hold_ratio` DECIMAL(10,2) DEFAULT NULL COMMENT '前 10 大股东持股比例',
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY `uk_code_date` (`stock_code`, `report_date`),
  KEY `idx_stock_date` (`stock_code`, `report_date`),
  KEY `idx_shareholder_change` (`shareholder_change`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='股东筹码信息表';

-- =====================================================
-- 3. 股票概念板块表
-- =====================================================
DROP TABLE IF EXISTS `stock_concept`;

CREATE TABLE `stock_concept` (
  `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
  `stock_code` VARCHAR(10) NOT NULL COMMENT '股票代码',
  `concept_name` VARCHAR(50) NOT NULL COMMENT '概念名称',
  `concept_type` VARCHAR(20) DEFAULT NULL COMMENT '概念类型',
  `is_hot` TINYINT DEFAULT 0 COMMENT '是否热点概念',
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY `uk_code_concept` (`stock_code`, `concept_name`),
  KEY `idx_stock` (`stock_code`),
  KEY `idx_concept` (`concept_name`),
  KEY `idx_hot` (`is_hot`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='股票概念板块表';

-- =====================================================
-- 4. 分析师预期与评级表
-- =====================================================
DROP TABLE IF EXISTS `stock_analyst_expectation`;

CREATE TABLE `stock_analyst_expectation` (
  `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
  `stock_code` VARCHAR(10) NOT NULL COMMENT '股票代码',
  `publish_date` DATE NOT NULL COMMENT '发布日期',
  `forecast_type` VARCHAR(20) DEFAULT NULL COMMENT '业绩预告类型',
  `forecast_content` TEXT COMMENT '业绩预告内容',
  `analyst_rating` VARCHAR(10) DEFAULT NULL COMMENT '分析师评级',
  `analyst_count` INT DEFAULT 0 COMMENT '分析师人数',
  `target_price` DECIMAL(10,2) DEFAULT NULL COMMENT '目标价',
  `consensus_eps` DECIMAL(10,4) DEFAULT NULL COMMENT '一致预期 EPS',
  `consensus_pe` DECIMAL(10,2) DEFAULT NULL COMMENT '一致预期 PE',
  `rating_score` DECIMAL(5,2) DEFAULT NULL COMMENT '评级打分',
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY `uk_code_date` (`stock_code`, `publish_date`),
  KEY `idx_stock_date` (`stock_code`, `publish_date`),
  KEY `idx_rating` (`analyst_rating`),
  KEY `idx_rating_score` (`rating_score`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='分析师预期与评级表';

-- =====================================================
-- 5. 东方财富数据采集记录表
-- =====================================================
DROP TABLE IF EXISTS `update_eastmoney_record`;

CREATE TABLE `update_eastmoney_record` (
  `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
  `stock_code` VARCHAR(10) NOT NULL COMMENT '股票代码',
  `stock_name` VARCHAR(50) DEFAULT NULL COMMENT '股票名称',
  `market_type` VARCHAR(10) DEFAULT NULL COMMENT '市场类型',
  `update_moneyflow` DATE DEFAULT NULL COMMENT '资金流向最后更新日期',
  `update_north` DATE DEFAULT NULL COMMENT '北向资金最后更新日期',
  `update_shareholder` DATE DEFAULT NULL COMMENT '股东人数最后更新日期',
  `update_concept` DATE DEFAULT NULL COMMENT '概念板块最后更新日期',
  `update_analyst` DATE DEFAULT NULL COMMENT '分析师评级最后更新日期',
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY `uk_stock` (`stock_code`),
  KEY `idx_update_moneyflow` (`update_moneyflow`),
  KEY `idx_update_north` (`update_north`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='东方财富数据采集记录表';

-- =====================================================
-- 验证表创建
-- =====================================================
SELECT '=== 表创建完成 ===' AS status;

SELECT table_name, table_comment 
FROM information_schema.tables 
WHERE table_schema = 'stock' 
  AND table_name IN (
    'stock_capital_flow',
    'stock_shareholder_info',
    'stock_concept',
    'stock_analyst_expectation',
    'update_eastmoney_record'
  )
ORDER BY table_name;

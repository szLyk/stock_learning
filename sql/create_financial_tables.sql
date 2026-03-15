-- =====================================================
-- 财务数据表结构（缺失的表）
-- 执行前请确保：USE stock;
-- =====================================================

USE stock;

-- =====================================================
-- 1. 资产负债表
-- =====================================================
DROP TABLE IF EXISTS `stock_balance_data`;

CREATE TABLE `stock_balance_data` (
  `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
  `stock_code` VARCHAR(10) NOT NULL COMMENT '证券代码',
  `publish_date` DATE DEFAULT NULL COMMENT '公司发布财报的日期',
  `statistic_date` DATE DEFAULT NULL COMMENT '财报统计的季度的最后一天',
  `total_assets` DECIMAL(20,4) DEFAULT NULL COMMENT '总资产',
  `total_liabilities` DECIMAL(20,4) DEFAULT NULL COMMENT '总负债',
  `total_equity` DECIMAL(20,4) DEFAULT NULL COMMENT '股东权益合计',
  `total_share` DECIMAL(20,4) DEFAULT NULL COMMENT '总股本',
  `liqa_share` DECIMAL(20,4) DEFAULT NULL COMMENT '流通股本',
  `capital_reserve` DECIMAL(20,4) DEFAULT NULL COMMENT '资本公积金',
  `surplus_reserve` DECIMAL(20,4) DEFAULT NULL COMMENT '盈余公积金',
  `undistributed_profit` DECIMAL(20,4) DEFAULT NULL COMMENT '未分配利润',
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY `uk_stock_date` (`stock_code`, `statistic_date`),
  KEY `idx_publish_date` (`publish_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='证券季频资产负债表';

-- =====================================================
-- 2. 成长能力数据
-- =====================================================
DROP TABLE IF EXISTS `stock_growth_data`;

CREATE TABLE `stock_growth_data` (
  `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
  `stock_code` VARCHAR(10) NOT NULL COMMENT '证券代码',
  `publish_date` DATE DEFAULT NULL COMMENT '公司发布财报的日期',
  `statistic_date` DATE DEFAULT NULL COMMENT '财报统计的季度的最后一天',
  `revenue_yoy` DECIMAL(10,4) DEFAULT NULL COMMENT '营业收入同比增长率 (%)',
  `operating_profit_yoy` DECIMAL(10,4) DEFAULT NULL COMMENT '营业利润同比增长率 (%)',
  `net_profit_yoy` DECIMAL(10,4) DEFAULT NULL COMMENT '净利润同比增长率 (%)',
  `total_assets_yoy` DECIMAL(10,4) DEFAULT NULL COMMENT '总资产同比增长率 (%)',
  `total_equity_yoy` DECIMAL(10,4) DEFAULT NULL COMMENT '股东权益同比增长率 (%)',
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY `uk_stock_date` (`stock_code`, `statistic_date`),
  KEY `idx_publish_date` (`publish_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='证券季频成长能力表';

-- =====================================================
-- 3. 运营能力数据
-- =====================================================
DROP TABLE IF EXISTS `stock_operation_data`;

CREATE TABLE `stock_operation_data` (
  `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
  `stock_code` VARCHAR(10) NOT NULL COMMENT '证券代码',
  `publish_date` DATE DEFAULT NULL COMMENT '公司发布财报的日期',
  `statistic_date` DATE DEFAULT NULL COMMENT '财报统计的季度的最后一天',
  `inventory_turnover` DECIMAL(10,4) DEFAULT NULL COMMENT '存货周转率',
  `receivables_turnover` DECIMAL(10,4) DEFAULT NULL COMMENT '应收账款周转率',
  `current_assets_turnover` DECIMAL(10,4) DEFAULT NULL COMMENT '流动资产周转率',
  `total_assets_turnover` DECIMAL(10,4) DEFAULT NULL COMMENT '总资产周转率',
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY `uk_stock_date` (`stock_code`, `statistic_date`),
  KEY `idx_publish_date` (`publish_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='证券季频运营能力表';

-- =====================================================
-- 4. 杜邦分析数据
-- =====================================================
DROP TABLE IF EXISTS `stock_dupont_data`;

CREATE TABLE `stock_dupont_data` (
  `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
  `stock_code` VARCHAR(10) NOT NULL COMMENT '证券代码',
  `publish_date` DATE DEFAULT NULL COMMENT '公司发布财报的日期',
  `statistic_date` DATE DEFAULT NULL COMMENT '财报统计的季度的最后一天',
  `roe` DECIMAL(10,4) DEFAULT NULL COMMENT '净资产收益率 (%)',
  `net_profit_margin` DECIMAL(10,4) DEFAULT NULL COMMENT '销售净利率 (%)',
  `asset_turnover` DECIMAL(10,4) DEFAULT NULL COMMENT '总资产周转率',
  `equity_multiplier` DECIMAL(10,4) DEFAULT NULL COMMENT '权益乘数',
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY `uk_stock_date` (`stock_code`, `statistic_date`),
  KEY `idx_publish_date` (`publish_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='证券季频杜邦分析表';

-- =====================================================
-- 验证表创建
-- =====================================================
SELECT '=== 财务数据表创建完成 ===' AS status;

SELECT table_name, table_comment 
FROM information_schema.tables 
WHERE table_schema = 'stock' 
  AND table_name IN (
    'stock_balance_data',
    'stock_growth_data',
    'stock_operation_data',
    'stock_dupont_data'
  )
ORDER BY table_name;

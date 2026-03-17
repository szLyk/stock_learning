-- =====================================================
-- Tushare 资金流向数据表
-- 执行前请确保：SET NAMES utf8mb4;
-- =====================================================

SET NAMES utf8mb4;
USE stock;

-- =====================================================
-- 1. 个股资金流向表
-- =====================================================
DROP TABLE IF EXISTS `stock_moneyflow`;

CREATE TABLE `stock_moneyflow` (
  `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
  `ts_code` VARCHAR(20) NOT NULL COMMENT 'TS 代码',
  `trade_date` DATE NOT NULL COMMENT '交易日期',
  `buy_sm_amount` DECIMAL(15,2) DEFAULT 0 COMMENT '小单买入金额 (万元)',
  `sell_sm_amount` DECIMAL(15,2) DEFAULT 0 COMMENT '小单卖出金额 (万元)',
  `buy_md_amount` DECIMAL(15,2) DEFAULT 0 COMMENT '中单买入金额 (万元)',
  `sell_md_amount` DECIMAL(15,2) DEFAULT 0 COMMENT '中单卖出金额 (万元)',
  `buy_lg_amount` DECIMAL(15,2) DEFAULT 0 COMMENT '大单买入金额 (万元)',
  `sell_lg_amount` DECIMAL(15,2) DEFAULT 0 COMMENT '大单卖出金额 (万元)',
  `buy_elg_amount` DECIMAL(15,2) DEFAULT 0 COMMENT '特大单买入金额 (万元)',
  `sell_elg_amount` DECIMAL(15,2) DEFAULT 0 COMMENT '特大单卖出金额 (万元)',
  `net_mf_amount` DECIMAL(15,2) DEFAULT 0 COMMENT '净流入金额 (万元)',
  `net_mf_rate` DECIMAL(10,4) DEFAULT 0 COMMENT '净流入率 (%)',
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY `uk_code_date` (`ts_code`, `trade_date`),
  KEY `idx_trade_date` (`trade_date`),
  KEY `idx_net_mf` (`net_mf_amount`),
  KEY `idx_net_mf_rate` (`net_mf_rate`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='个股资金流向表 (Tushare)';

-- =====================================================
-- 2. Tushare 数据采集记录表
-- =====================================================
DROP TABLE IF EXISTS `update_tushare_record`;

CREATE TABLE `update_tushare_record` (
  `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
  `ts_code` VARCHAR(20) NOT NULL COMMENT 'TS 代码',
  `stock_name` VARCHAR(100) DEFAULT NULL COMMENT '股票名称',
  `update_moneyflow` DATE DEFAULT NULL COMMENT '资金流向最后更新日期',
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY `uk_ts_code` (`ts_code`),
  KEY `idx_update_moneyflow` (`update_moneyflow`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='Tushare 数据采集记录表';

-- =====================================================
-- 3. 初始化记录表（从 stock_basic 同步）
-- =====================================================
INSERT INTO update_tushare_record (ts_code, stock_name)
SELECT ts_code, name 
FROM stock_basic 
WHERE list_status = 'L'
ON DUPLICATE KEY UPDATE stock_name = VALUES(stock_name);

-- =====================================================
-- 验证表创建
-- =====================================================
SELECT '=== 表创建完成 ===' AS status;

SELECT table_name, table_comment 
FROM information_schema.tables 
WHERE table_schema = 'stock' 
  AND table_name IN ('stock_moneyflow', 'update_tushare_record')
ORDER BY table_name;

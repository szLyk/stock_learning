-- =====================================================
-- 量价因子数据表
-- 执行前请确保：SET NAMES utf8mb4;
-- =====================================================

SET NAMES utf8mb4;
USE stock;

-- =====================================================
-- 1. 量价因子表
-- =====================================================
DROP TABLE IF EXISTS `stock_factor_volume_price`;

CREATE TABLE `stock_factor_volume_price` (
  `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
  `stock_code` VARCHAR(10) NOT NULL COMMENT '股票代码',
  `calc_date` DATE NOT NULL COMMENT '计算日期',
  `volume_price_score` DECIMAL(10,4) DEFAULT 50.0 COMMENT '量价因子得分 (0-100)',
  `volume_ratio` DECIMAL(10,4) DEFAULT 1.0 COMMENT '成交量比率',
  `price_change` DECIMAL(10,4) DEFAULT 0.0 COMMENT '价格变化率 (%)',
  `turnover_rate` DECIMAL(10,4) DEFAULT 0.0 COMMENT '换手率 (%)',
  `obv_change` DECIMAL(10,4) DEFAULT 0.0 COMMENT 'OBV 变化率 (%)',
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY `uk_code_date` (`stock_code`, `calc_date`),
  KEY `idx_calc_date` (`calc_date`),
  KEY `idx_vp_score` (`volume_price_score`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='量价因子表';

-- =====================================================
-- 2. 量价因子采集记录表
-- =====================================================
DROP TABLE IF EXISTS `update_volume_price_record`;

CREATE TABLE `update_volume_price_record` (
  `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
  `stock_code` VARCHAR(10) NOT NULL COMMENT '股票代码',
  `last_calc_date` DATE DEFAULT NULL COMMENT '最后计算日期',
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY `uk_stock_code` (`stock_code`),
  KEY `idx_last_calc_date` (`last_calc_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='量价因子采集记录表';

-- =====================================================
-- 3. 初始化记录表
-- =====================================================
INSERT INTO update_volume_price_record (stock_code)
SELECT stock_code 
FROM stock_basic 
WHERE stock_status = 1
ON DUPLICATE KEY UPDATE stock_code = VALUES(stock_code);

-- =====================================================
-- 验证表创建
-- =====================================================
SELECT '=== 表创建完成 ===' AS status;

SELECT table_name, table_comment 
FROM information_schema.tables 
WHERE table_schema = 'stock' 
  AND table_name IN ('stock_factor_volume_price', 'update_volume_price_record')
ORDER BY table_name;

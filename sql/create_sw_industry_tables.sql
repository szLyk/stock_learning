-- =====================================================
-- 申万一级行业分类表
-- 创建时间: 2026-04-20
-- 数据源: AkShare (stock_industry_category_sw)
-- =====================================================

SET NAMES utf8mb4;
USE stock;

-- =====================================================
-- 1. 申万行业分类主表
-- =====================================================
CREATE TABLE IF NOT EXISTS `stock_industry_sw` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `stock_code` VARCHAR(10) NOT NULL COMMENT '股票代码',
    `stock_name` VARCHAR(50) DEFAULT NULL COMMENT '股票简称',
    `industry_code` VARCHAR(10) DEFAULT NULL COMMENT '申万行业代码',
    `industry_name` VARCHAR(50) DEFAULT NULL COMMENT '申万行业名称',
    `industry_level` INT DEFAULT 1 COMMENT '行业层级（1=一级行业, 2=二级行业, 3=三级行业）',
    `market_type` VARCHAR(5) DEFAULT NULL COMMENT '市场类型',
    `data_source` VARCHAR(20) DEFAULT 'akshare' COMMENT '数据来源',
    `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_stock_level` (`stock_code`, `industry_level`),
    KEY `idx_stock_code` (`stock_code`),
    KEY `idx_industry_name` (`industry_name`),
    KEY `idx_level` (`industry_level`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='申万行业分类表';

-- =====================================================
-- 2. 行业分类更新进度表
-- =====================================================
CREATE TABLE IF NOT EXISTS `update_sw_industry_record` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `stock_code` VARCHAR(10) NOT NULL COMMENT '股票代码',
    `stock_name` VARCHAR(50) DEFAULT NULL COMMENT '股票简称',
    `market_type` VARCHAR(5) DEFAULT NULL COMMENT '市场类型',
    `update_sw_industry` DATE DEFAULT NULL COMMENT '申万行业数据最后更新日期',
    `update_status` VARCHAR(20) DEFAULT 'pending' COMMENT '更新状态',
    `error_msg` VARCHAR(500) DEFAULT NULL COMMENT '错误信息',
    `retry_count` INT DEFAULT 0 COMMENT '重试次数',
    `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_stock_code` (`stock_code`),
    KEY `idx_update_status` (`update_status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='申万行业分类更新进度表';

-- =====================================================
-- 3. 初始化进度表（从stock_basic同步）
-- =====================================================
INSERT INTO update_sw_industry_record (stock_code, stock_name, market_type, update_status)
SELECT stock_code, stock_name, market_type, 'pending'
FROM stock_basic
WHERE stock_status = 1
ON DUPLICATE KEY UPDATE
    stock_name = VALUES(stock_name),
    market_type = VALUES(market_type);

-- =====================================================
-- 完成提示
-- =====================================================
SELECT '申万行业分类表创建完成！' AS message;
SELECT COUNT(*) AS '待更新股票数' FROM update_sw_industry_record WHERE update_status = 'pending';
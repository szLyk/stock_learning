-- =====================================================
-- 波动率因子数据表
-- 包含：历史波动率、Parkinson波动率、GARCH预测波动率
-- 创建时间: 2026-04-02
-- =====================================================

SET NAMES utf8mb4;
USE stock;

-- =====================================================
-- 1. 日线波动率因子表
-- =====================================================
DROP TABLE IF EXISTS `stock_date_volatility`;

CREATE TABLE `stock_date_volatility` (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    `stock_code` VARCHAR(10) NOT NULL COMMENT '股票代码',
    `stock_date` DATE NOT NULL COMMENT '交易日期',
    
    -- 历史波动率（基于收盘价）
    `hist_vol_20` DECIMAL(10, 6) DEFAULT NULL COMMENT '20日历史波动率(年化)',
    `hist_vol_60` DECIMAL(10, 6) DEFAULT NULL COMMENT '60日历史波动率(年化)',
    
    -- Parkinson 波动率（基于日内高低价）
    `parkinson_vol_20` DECIMAL(10, 6) DEFAULT NULL COMMENT '20日Parkinson波动率(年化)',
    `parkinson_vol_60` DECIMAL(10, 6) DEFAULT NULL COMMENT '60日Parkinson波动率(年化)',
    
    -- Garman-Klass 波动率（更精确的估计量）
    `gk_vol_20` DECIMAL(10, 6) DEFAULT NULL COMMENT '20日Garman-Klass波动率(年化)',
    
    -- GARCH 预测
    `garch_vol` DECIMAL(10, 6) DEFAULT NULL COMMENT 'GARCH(1,1)当前条件波动率(年化)',
    `garch_forecast_5d` DECIMAL(10, 6) DEFAULT NULL COMMENT 'GARCH预测5日后波动率(年化)',
    `garch_persistence` DECIMAL(10, 6) DEFAULT NULL COMMENT 'GARCH持续性参数(α+β)',
    
    -- ATR 相关
    `atr_14` DECIMAL(10, 4) DEFAULT NULL COMMENT '14日ATR',
    `natr_14` DECIMAL(10, 6) DEFAULT NULL COMMENT '14日归一化ATR(%)',
    
    -- 波动率变化
    `vol_change_5d` DECIMAL(10, 6) DEFAULT NULL COMMENT '5日波动率变化(%)',
    `vol_change_20d` DECIMAL(10, 6) DEFAULT NULL COMMENT '20日波动率变化(%)',
    
    -- 元数据
    `data_source` VARCHAR(20) DEFAULT 'calculated' COMMENT '数据来源',
    `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY `uk_stock_date` (`stock_code`, `stock_date`),
    KEY `idx_stock_code` (`stock_code`),
    KEY `idx_stock_date` (`stock_date`),
    KEY `idx_parkinson_vol` (`parkinson_vol_20`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='日线波动率因子表';

-- =====================================================
-- 2. 波动率计算记录表
-- =====================================================
DROP TABLE IF EXISTS `stock_volatility_record`;

CREATE TABLE `stock_volatility_record` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `stock_code` VARCHAR(10) NOT NULL COMMENT '股票代码',
    `update_date_vol` DATE DEFAULT NULL COMMENT '波动率最后更新日期',
    `garch_fitted` TINYINT DEFAULT 0 COMMENT 'GARCH是否拟合成功',
    `garch_error` VARCHAR(500) DEFAULT NULL COMMENT 'GARCH拟合错误信息',
    `data_days` INT DEFAULT NULL COMMENT '数据天数',
    `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY `uk_stock` (`stock_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='波动率计算记录表';

-- =====================================================
-- 完成提示
-- =====================================================
SELECT '波动率因子表创建完成！' AS message;
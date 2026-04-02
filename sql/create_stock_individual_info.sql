-- =====================================================
-- 股票个股信息表（来自 AKShare stock_individual_info_em 接口）
-- 创建时间: 2026-04-02
-- 数据源: 东方财富
-- 接口: ak.stock_individual_info_em(symbol='股票代码')
-- =====================================================

CREATE TABLE IF NOT EXISTS `stock_individual_info` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `stock_code` VARCHAR(10) NOT NULL COMMENT '股票代码',
    `stock_name` VARCHAR(50) DEFAULT NULL COMMENT '股票简称',
    `latest_price` DECIMAL(10, 2) DEFAULT NULL COMMENT '最新价格',
    `total_share` DECIMAL(20, 2) DEFAULT NULL COMMENT '总股本(股)',
    `circ_share` DECIMAL(20, 2) DEFAULT NULL COMMENT '流通股(股)',
    `total_market_cap` DECIMAL(20, 2) DEFAULT NULL COMMENT '总市值(元)',
    `circ_market_cap` DECIMAL(20, 2) DEFAULT NULL COMMENT '流通市值(元)',
    `industry` VARCHAR(50) DEFAULT NULL COMMENT '所属行业',
    `list_date` DATE DEFAULT NULL COMMENT '上市日期',
    `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_stock_code` (`stock_code`),
    KEY `idx_industry` (`industry`),
    KEY `idx_total_market_cap` (`total_market_cap`),
    KEY `idx_circ_market_cap` (`circ_market_cap`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='股票个股信息表(东方财富)';

-- =====================================================
-- 说明：
-- 1. total_share: 总股本，单位为股
-- 2. circ_share: 流通股本，单位为股  
-- 3. total_market_cap: 总市值，单位为元
-- 4. circ_market_cap: 流通市值，单位为元
-- 5. 数据更新频率：建议每日或每周更新
-- =====================================================

-- 示例数据
-- INSERT INTO stock_individual_info 
-- (stock_code, stock_name, latest_price, total_share, circ_share, total_market_cap, circ_market_cap, industry, list_date)
-- VALUES 
-- ('000063', '中兴通讯', 32.16, 4783534887.0, 4027621232.0, 153838481965.92, 129528298821.12, '通信设备', '1997-11-18');
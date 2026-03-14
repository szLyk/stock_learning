-- =====================================================
-- 财务数据采集表结构
-- 创建时间：2026-03-14
-- =====================================================

-- 设置字符集，避免中文乱码
SET NAMES utf8mb4;

USE stock;

-- =====================================================
-- 1. 财务数据采集记录表
-- =====================================================
DROP TABLE IF EXISTS stock_performance_update_record;

CREATE TABLE stock_performance_update_record (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    stock_code VARCHAR(10) NOT NULL COMMENT '股票代码',
    stock_name VARCHAR(50) DEFAULT NULL COMMENT '股票名称',
    market_type VARCHAR(10) DEFAULT NULL COMMENT '市场类型',
    
    -- 财务数据更新时间
    update_profit_date DATE DEFAULT NULL COMMENT '利润表最后更新日期',
    update_balance_date DATE DEFAULT NULL COMMENT '资产负债表最后更新日期',
    update_cashflow_date DATE DEFAULT NULL COMMENT '现金流量表最后更新日期',
    update_growth_date DATE DEFAULT NULL COMMENT '成长能力最后更新日期',
    update_operation_date DATE DEFAULT NULL COMMENT '运营能力最后更新日期',
    update_dupont_date DATE DEFAULT NULL COMMENT '杜邦分析最后更新日期',
    
    -- 业绩预告和分红
    update_forecast_date DATE DEFAULT NULL COMMENT '业绩预告最后更新日期',
    update_express_date DATE DEFAULT NULL COMMENT '业绩快报最后更新日期',
    update_dividend_date DATE DEFAULT NULL COMMENT '分红送配最后更新日期',
    
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_stock (stock_code),
    KEY idx_update_profit (update_profit_date),
    KEY idx_update_forecast (update_forecast_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='财务数据采集记录表';

-- =====================================================
-- 2. 利润表
-- =====================================================
DROP TABLE IF EXISTS stock_profit_data;

CREATE TABLE stock_profit_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL COMMENT '股票代码',
    publish_date DATE DEFAULT NULL COMMENT '发布日期',
    statistic_date DATE DEFAULT NULL COMMENT '统计日期',
    roe_avg DECIMAL(10,4) DEFAULT NULL COMMENT '加权 ROE(%)',
    np_margin DECIMAL(10,4) DEFAULT NULL COMMENT '净利率 (%)',
    gp_margin DECIMAL(10,4) DEFAULT NULL COMMENT '毛利率 (%)',
    net_profit DECIMAL(15,2) DEFAULT NULL COMMENT '净利润 (元)',
    eps_ttm DECIMAL(10,4) DEFAULT NULL COMMENT '每股收益 (元)',
    mb_revenue DECIMAL(15,2) DEFAULT NULL COMMENT '营业总收入 (元)',
    total_share DECIMAL(15,2) DEFAULT NULL COMMENT '总股本 (万股)',
    liqa_share DECIMAL(15,2) DEFAULT NULL COMMENT '流通股本 (万股)',
    season INT DEFAULT NULL COMMENT '季度 (1-4)',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_code_date (stock_code, statistic_date),
    KEY idx_stock (stock_code),
    KEY idx_publish (publish_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='利润表数据';

-- =====================================================
-- 3. 资产负债表
-- =====================================================
DROP TABLE IF EXISTS stock_balance_data;

CREATE TABLE stock_balance_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL COMMENT '股票代码',
    publish_date DATE DEFAULT NULL COMMENT '发布日期',
    statistic_date DATE DEFAULT NULL COMMENT '统计日期',
    season INT DEFAULT NULL COMMENT '季度 (1-4)',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_code_date (stock_code, statistic_date),
    KEY idx_stock (stock_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='资产负债表数据';

-- =====================================================
-- 4. 现金流量表
-- =====================================================
DROP TABLE IF EXISTS stock_cash_flow_data;

CREATE TABLE stock_cash_flow_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL COMMENT '股票代码',
    publish_date DATE DEFAULT NULL COMMENT '发布日期',
    statistic_date DATE DEFAULT NULL COMMENT '统计日期',
    season INT DEFAULT NULL COMMENT '季度 (1-4)',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_code_date (stock_code, statistic_date),
    KEY idx_stock (stock_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='现金流量表数据';

-- =====================================================
-- 5. 成长能力
-- =====================================================
DROP TABLE IF EXISTS stock_growth_data;

CREATE TABLE stock_growth_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL COMMENT '股票代码',
    publish_date DATE DEFAULT NULL COMMENT '发布日期',
    statistic_date DATE DEFAULT NULL COMMENT '统计日期',
    season INT DEFAULT NULL COMMENT '季度 (1-4)',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_code_date (stock_code, statistic_date),
    KEY idx_stock (stock_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='成长能力数据';

-- =====================================================
-- 6. 运营能力
-- =====================================================
DROP TABLE IF EXISTS stock_operation_data;

CREATE TABLE stock_operation_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL COMMENT '股票代码',
    publish_date DATE DEFAULT NULL COMMENT '发布日期',
    statistic_date DATE DEFAULT NULL COMMENT '统计日期',
    season INT DEFAULT NULL COMMENT '季度 (1-4)',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_code_date (stock_code, statistic_date),
    KEY idx_stock (stock_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='运营能力数据';

-- =====================================================
-- 7. 杜邦分析
-- =====================================================
DROP TABLE IF EXISTS stock_dupont_data;

CREATE TABLE stock_dupont_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL COMMENT '股票代码',
    publish_date DATE DEFAULT NULL COMMENT '发布日期',
    statistic_date DATE DEFAULT NULL COMMENT '统计日期',
    season INT DEFAULT NULL COMMENT '季度 (1-4)',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_code_date (stock_code, statistic_date),
    KEY idx_stock (stock_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='杜邦分析数据';

-- =====================================================
-- 8. 业绩预告
-- =====================================================
DROP TABLE IF EXISTS stock_forecast_report;

CREATE TABLE stock_forecast_report (
    id INT AUTO_INCREMENT PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL COMMENT '股票代码',
    publish_date DATE DEFAULT NULL COMMENT '发布日期',
    statistic_date DATE DEFAULT NULL COMMENT '统计日期',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_code_date (stock_code, publish_date),
    KEY idx_stock (stock_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='业绩预告数据';

-- =====================================================
-- 9. 分红送配
-- =====================================================
DROP TABLE IF EXISTS stock_dividend_data;

CREATE TABLE stock_dividend_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL COMMENT '股票代码',
    dividend_year INT DEFAULT NULL COMMENT '分红年度',
    announce_date DATE DEFAULT NULL COMMENT '公告日期',
    ex_dividend_date DATE DEFAULT NULL COMMENT '除权除息日',
    cash_dividend DECIMAL(10,4) DEFAULT NULL COMMENT '现金分红 (元/10 股)',
    bonus_shares DECIMAL(10,4) DEFAULT NULL COMMENT '送股 (股/10 股)',
    reserved_per_share DECIMAL(10,4) DEFAULT NULL COMMENT '转增 (股/10 股)',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_code_date (stock_code, announce_date),
    KEY idx_stock (stock_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='分红送配数据';

-- =====================================================
-- 完成提示
-- =====================================================
SELECT '财务数据表结构创建完成！' AS message;

-- =====================================================
-- 股票财务数据表
-- 数据源: AkShare - stock_financial_abstract
-- 创建时间: 2026-04-02
-- =====================================================

-- 1. 财务摘要表（核心表，包含80个指标）
CREATE TABLE IF NOT EXISTS `stock_financial_summary` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `stock_code` VARCHAR(10) NOT NULL COMMENT '股票代码',
    `report_date` VARCHAR(10) NOT NULL COMMENT '报告期（如20251231）',
    
    -- 利润指标
    `net_profit` DECIMAL(20, 2) DEFAULT NULL COMMENT '净利润',
    `parent_net_profit` DECIMAL(20, 2) DEFAULT NULL COMMENT '归母净利润',
    `deduct_net_profit` DECIMAL(20, 2) DEFAULT NULL COMMENT '扣非净利润',
    `operating_income` DECIMAL(20, 2) DEFAULT NULL COMMENT '营业收入',
    `operating_profit` DECIMAL(20, 2) DEFAULT NULL COMMENT '营业利润',
    
    -- 资产指标
    `total_assets` DECIMAL(20, 2) DEFAULT NULL COMMENT '总资产',
    `net_assets` DECIMAL(20, 2) DEFAULT NULL COMMENT '净资产',
    `total_liability` DECIMAL(20, 2) DEFAULT NULL COMMENT '总负债',
    
    -- 现金流指标
    `operating_cash_flow` DECIMAL(20, 2) DEFAULT NULL COMMENT '经营现金流净额',
    
    -- 每股指标
    `eps_basic` DECIMAL(10, 4) DEFAULT NULL COMMENT '基本每股收益',
    `eps_diluted` DECIMAL(10, 4) DEFAULT NULL COMMENT '稀释每股收益',
    `bvps` DECIMAL(10, 4) DEFAULT NULL COMMENT '每股净资产',
    `cfps` DECIMAL(10, 4) DEFAULT NULL COMMENT '每股现金流',
    
    -- 盈利能力指标
    `roe` DECIMAL(10, 4) DEFAULT NULL COMMENT '净资产收益率ROE(%)',
    `roa` DECIMAL(10, 4) DEFAULT NULL COMMENT '总资产报酬率ROA(%)',
    `gross_margin` DECIMAL(10, 4) DEFAULT NULL COMMENT '毛利率(%)',
    `net_margin` DECIMAL(10, 4) DEFAULT NULL COMMENT '净利率(%)',
    
    -- 偿债能力指标
    `debt_ratio` DECIMAL(10, 4) DEFAULT NULL COMMENT '资产负债率(%)',
    `current_ratio` DECIMAL(10, 4) DEFAULT NULL COMMENT '流动比率',
    `quick_ratio` DECIMAL(10, 4) DEFAULT NULL COMMENT '速动比率',
    
    -- 成长能力指标
    `revenue_yoy` DECIMAL(10, 4) DEFAULT NULL COMMENT '营收同比增长(%)',
    `profit_yoy` DECIMAL(10, 4) DEFAULT NULL COMMENT '净利润同比增长(%)',
    
    -- 元数据
    `data_source` VARCHAR(20) DEFAULT 'akshare' COMMENT '数据来源',
    `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_stock_report` (`stock_code`, `report_date`),
    KEY `idx_stock_code` (`stock_code`),
    KEY `idx_report_date` (`report_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='股票财务摘要表';

-- 2. 财务数据更新记录表（用于断点续传）
CREATE TABLE IF NOT EXISTS `stock_financial_update_log` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `stock_code` VARCHAR(10) NOT NULL COMMENT '股票代码',
    `report_date` VARCHAR(10) NOT NULL COMMENT '报告期',
    `update_status` TINYINT DEFAULT 0 COMMENT '更新状态：0-待处理，1-成功，2-失败',
    `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '更新时间',
    `error_msg` VARCHAR(500) DEFAULT NULL COMMENT '错误信息',
    
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_stock_report` (`stock_code`, `report_date`),
    KEY `idx_status` (`update_status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='财务数据更新日志';

-- 3. 创建视图：最新财务数据
CREATE OR REPLACE VIEW `v_stock_financial_latest` AS
SELECT 
    s.stock_code,
    b.stock_name,
    s.report_date,
    s.net_profit,
    s.parent_net_profit,
    s.operating_income,
    s.roe,
    s.gross_margin,
    s.net_margin,
    s.debt_ratio,
    s.eps_basic,
    s.bvps,
    s.revenue_yoy,
    s.profit_yoy
FROM stock_financial_summary s
JOIN stock_basic b ON s.stock_code = b.stock_code
WHERE (s.stock_code, s.report_date) IN (
    SELECT stock_code, MAX(report_date) 
    FROM stock_financial_summary 
    GROUP BY stock_code
);

-- =====================================================
-- 说明：
-- 1. stock_financial_summary：存储财务摘要数据
-- 2. stock_financial_update_log：记录更新状态，支持断点续传
-- 3. v_stock_financial_latest：视图，查询每只股票的最新财务数据
-- =====================================================
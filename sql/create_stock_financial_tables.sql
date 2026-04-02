-- =====================================================
-- 股票财务摘要表（完整版，包含80个指标）
-- 数据源: AkShare - stock_financial_abstract
-- 创建时间: 2026-04-02
-- =====================================================

DROP TABLE IF EXISTS `stock_financial_summary`;

CREATE TABLE `stock_financial_summary` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `stock_code` VARCHAR(10) NOT NULL COMMENT '股票代码',
    `report_date` VARCHAR(10) NOT NULL COMMENT '报告期',
    
    -- 利润指标
    `parent_net_profit` DECIMAL(20, 2) DEFAULT NULL COMMENT '归母净利润',
    `total_revenue` DECIMAL(20, 2) DEFAULT NULL COMMENT '营业总收入',
    `operating_cost` DECIMAL(20, 2) DEFAULT NULL COMMENT '营业成本',
    `net_profit` DECIMAL(20, 2) DEFAULT NULL COMMENT '净利润',
    `deduct_net_profit` DECIMAL(20, 2) DEFAULT NULL COMMENT '扣非净利润',
    
    -- 资产指标
    `net_assets` DECIMAL(20, 2) DEFAULT NULL COMMENT '股东权益合计(净资产)',
    `goodwill` DECIMAL(20, 2) DEFAULT NULL COMMENT '商誉',
    
    -- 现金流指标
    `operating_cash_flow` DECIMAL(20, 2) DEFAULT NULL COMMENT '经营现金流量净额',
    
    -- 每股指标
    `eps_basic` DECIMAL(10, 4) DEFAULT NULL COMMENT '基本每股收益',
    `eps_diluted` DECIMAL(10, 4) DEFAULT NULL COMMENT '稀释每股收益',
    `eps_diluted_latest` DECIMAL(10, 4) DEFAULT NULL COMMENT '摊薄每股收益_最新股数',
    `bvps_diluted` DECIMAL(10, 4) DEFAULT NULL COMMENT '摊薄每股净资产_期末股数',
    `bvps_adjusted` DECIMAL(10, 4) DEFAULT NULL COMMENT '调整每股净资产_期末股数',
    `bvps_latest` DECIMAL(10, 4) DEFAULT NULL COMMENT '每股净资产_最新股数',
    `cfps` DECIMAL(10, 4) DEFAULT NULL COMMENT '每股经营现金流',
    `cash_flow_per_share` DECIMAL(10, 4) DEFAULT NULL COMMENT '每股现金流量净额',
    `fcff_per_share` DECIMAL(10, 4) DEFAULT NULL COMMENT '每股企业自由现金流量',
    `fcfe_per_share` DECIMAL(10, 4) DEFAULT NULL COMMENT '每股股东自由现金流量',
    `retained_earnings_per_share` DECIMAL(10, 4) DEFAULT NULL COMMENT '每股未分配利润',
    `capital_reserve_per_share` DECIMAL(10, 4) DEFAULT NULL COMMENT '每股资本公积金',
    `surplus_reserve_per_share` DECIMAL(10, 4) DEFAULT NULL COMMENT '每股盈余公积金',
    `retained_per_share` DECIMAL(10, 4) DEFAULT NULL COMMENT '每股留存收益',
    `revenue_per_share` DECIMAL(10, 4) DEFAULT NULL COMMENT '每股营业收入',
    `total_revenue_per_share` DECIMAL(10, 4) DEFAULT NULL COMMENT '每股营业总收入',
    `ebit_per_share` DECIMAL(10, 4) DEFAULT NULL COMMENT '每股息税前利润',
    
    -- 盈利能力指标
    `roe` DECIMAL(10, 4) DEFAULT NULL COMMENT '净资产收益率ROE(%)',
    `roe_diluted` DECIMAL(10, 4) DEFAULT NULL COMMENT '摊薄净资产收益率(%)',
    `roe_avg` DECIMAL(10, 4) DEFAULT NULL COMMENT '净资产收益率_平均(%)',
    `roe_avg_deduct` DECIMAL(10, 4) DEFAULT NULL COMMENT '净资产收益率_平均_扣非(%)',
    `roe_diluted_deduct` DECIMAL(10, 4) DEFAULT NULL COMMENT '摊薄净资产收益率_扣非(%)',
    `ebit_margin` DECIMAL(10, 4) DEFAULT NULL COMMENT '息税前利润率(%)',
    `roa` DECIMAL(10, 4) DEFAULT NULL COMMENT '总资产报酬率ROA(%)',
    `roic` DECIMAL(10, 4) DEFAULT NULL COMMENT '投入资本回报率(%)',
    `rota` DECIMAL(10, 4) DEFAULT NULL COMMENT '总资本回报率(%)',
    `roa_avg_after_tax` DECIMAL(10, 4) DEFAULT NULL COMMENT '息前税后总资产报酬率_平均(%)',
    `gross_margin` DECIMAL(10, 4) DEFAULT NULL COMMENT '毛利率(%)',
    `net_margin` DECIMAL(10, 4) DEFAULT NULL COMMENT '销售净利率(%)',
    `cost_profit_ratio` DECIMAL(10, 4) DEFAULT NULL COMMENT '成本费用利润率(%)',
    `operating_margin` DECIMAL(10, 4) DEFAULT NULL COMMENT '营业利润率(%)',
    `roa_avg` DECIMAL(10, 4) DEFAULT NULL COMMENT '总资产净利率_平均(%)',
    `roa_avg_minority` DECIMAL(10, 4) DEFAULT NULL COMMENT '总资产净利率_平均_含少数股东(%)',
    
    -- 成长能力指标
    `revenue_growth` DECIMAL(10, 4) DEFAULT NULL COMMENT '营业总收入增长率(%)',
    `profit_growth` DECIMAL(10, 4) DEFAULT NULL COMMENT '归母净利润增长率(%)',
    
    -- 运营能力指标
    `cash_to_revenue` DECIMAL(10, 4) DEFAULT NULL COMMENT '经营活动净现金/销售收入',
    `cash_to_total_revenue` DECIMAL(10, 4) DEFAULT NULL COMMENT '经营性现金净流量/营业总收入',
    `cost_ratio` DECIMAL(10, 4) DEFAULT NULL COMMENT '成本费用率(%)',
    `expense_ratio` DECIMAL(10, 4) DEFAULT NULL COMMENT '期间费用率(%)',
    `cost_of_sales_ratio` DECIMAL(10, 4) DEFAULT NULL COMMENT '销售成本率(%)',
    `cash_to_profit` DECIMAL(10, 4) DEFAULT NULL COMMENT '经营活动净现金/归母净利润',
    `tax_to_profit` DECIMAL(10, 4) DEFAULT NULL COMMENT '所得税/利润总额',
    
    -- 偿债能力指标
    `current_ratio` DECIMAL(10, 4) DEFAULT NULL COMMENT '流动比率',
    `quick_ratio` DECIMAL(10, 4) DEFAULT NULL COMMENT '速动比率',
    `conservative_quick_ratio` DECIMAL(10, 4) DEFAULT NULL COMMENT '保守速动比率',
    `debt_ratio` DECIMAL(10, 4) DEFAULT NULL COMMENT '资产负债率(%)',
    `equity_multiplier` DECIMAL(10, 4) DEFAULT NULL COMMENT '权益乘数',
    `equity_multiplier_minority` DECIMAL(10, 4) DEFAULT NULL COMMENT '权益乘数_含少数股权',
    `debt_equity_ratio` DECIMAL(10, 4) DEFAULT NULL COMMENT '产权比率',
    `cash_ratio` DECIMAL(10, 4) DEFAULT NULL COMMENT '现金比率',
    
    -- 周转能力指标
    `ar_turnover` DECIMAL(10, 4) DEFAULT NULL COMMENT '应收账款周转率',
    `ar_turnover_days` DECIMAL(10, 4) DEFAULT NULL COMMENT '应收账款周转天数',
    `inventory_turnover` DECIMAL(10, 4) DEFAULT NULL COMMENT '存货周转率',
    `inventory_turnover_days` DECIMAL(10, 4) DEFAULT NULL COMMENT '存货周转天数',
    `asset_turnover` DECIMAL(10, 4) DEFAULT NULL COMMENT '总资产周转率',
    `asset_turnover_days` DECIMAL(10, 4) DEFAULT NULL COMMENT '总资产周转天数',
    `current_asset_turnover` DECIMAL(10, 4) DEFAULT NULL COMMENT '流动资产周转率',
    `current_asset_turnover_days` DECIMAL(10, 4) DEFAULT NULL COMMENT '流动资产周转天数',
    `ap_turnover` DECIMAL(10, 4) DEFAULT NULL COMMENT '应付账款周转率',
    
    -- 元数据
    `data_source` VARCHAR(20) DEFAULT 'akshare' COMMENT '数据来源',
    `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_stock_report` (`stock_code`, `report_date`),
    KEY `idx_stock_code` (`stock_code`),
    KEY `idx_report_date` (`report_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='股票财务摘要表(80个指标)';
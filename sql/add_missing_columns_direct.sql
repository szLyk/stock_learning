-- =====================================================
-- 直接添加缺失字段（不使用存储过程）
-- 执行方式：mysql -h 192.168.1.109 -P 3306 -u root -p123456 stock < sql/add_missing_columns_direct.sql
-- =====================================================

USE stock;

-- =====================================================
-- 1. stock_balance_data
-- =====================================================
SELECT '=== Adding columns to stock_balance_data ===' AS status;

ALTER TABLE stock_balance_data ADD COLUMN total_assets DECIMAL(20,4) DEFAULT NULL COMMENT '总资产' AFTER statistic_date;
ALTER TABLE stock_balance_data ADD COLUMN total_liabilities DECIMAL(20,4) DEFAULT NULL COMMENT '总负债' AFTER total_assets;
ALTER TABLE stock_balance_data ADD COLUMN total_equity DECIMAL(20,4) DEFAULT NULL COMMENT '股东权益合计' AFTER total_liabilities;
ALTER TABLE stock_balance_data ADD COLUMN capital_reserve DECIMAL(20,4) DEFAULT NULL COMMENT '资本公积金' AFTER total_equity;
ALTER TABLE stock_balance_data ADD COLUMN surplus_reserve DECIMAL(20,4) DEFAULT NULL COMMENT '盈余公积金' AFTER capital_reserve;
ALTER TABLE stock_balance_data ADD COLUMN undistributed_profit DECIMAL(20,4) DEFAULT NULL COMMENT '未分配利润' AFTER surplus_reserve;
ALTER TABLE stock_balance_data ADD COLUMN current_ratio DECIMAL(10,4) DEFAULT NULL COMMENT '流动比率' AFTER undistributed_profit;
ALTER TABLE stock_balance_data ADD COLUMN quick_ratio DECIMAL(10,4) DEFAULT NULL COMMENT '速动比率' AFTER current_ratio;
ALTER TABLE stock_balance_data ADD COLUMN cash_ratio DECIMAL(10,4) DEFAULT NULL COMMENT '现金比率' AFTER quick_ratio;
ALTER TABLE stock_balance_data ADD COLUMN yoy_liability DECIMAL(10,4) DEFAULT NULL COMMENT '负债同比增长率 (%)' AFTER cash_ratio;
ALTER TABLE stock_balance_data ADD COLUMN liability_to_asset DECIMAL(10,4) DEFAULT NULL COMMENT '资产负债率 (%)' AFTER yoy_liability;
ALTER TABLE stock_balance_data ADD COLUMN asset_to_equity DECIMAL(10,4) DEFAULT NULL COMMENT '资产/权益' AFTER liability_to_asset;

-- =====================================================
-- 2. stock_cash_flow_data (创建表)
-- =====================================================
SELECT '=== Creating stock_cash_flow_data table ===' AS status;

DROP TABLE IF EXISTS stock_cash_flow_data;

CREATE TABLE stock_cash_flow_data (
  id INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
  stock_code VARCHAR(10) NOT NULL COMMENT '证券代码',
  publish_date DATE DEFAULT NULL COMMENT '发布日期',
  statistic_date DATE DEFAULT NULL COMMENT '统计日期',
  season INT DEFAULT NULL COMMENT '季度 (1-4)',
  cfo_to_or DECIMAL(10,4) DEFAULT NULL COMMENT '经营活动产生的现金流量净额/营业收入',
  cfo_to_np DECIMAL(10,4) DEFAULT NULL COMMENT '经营活动产生的现金流量净额/净利润',
  cfo_to_gr DECIMAL(10,4) DEFAULT NULL COMMENT '经营活动产生的现金流量净额/营业总收入',
  ca_to_asset DECIMAL(10,4) DEFAULT NULL COMMENT '流动资产/总资产',
  nca_to_asset DECIMAL(10,4) DEFAULT NULL COMMENT '非流动资产/总资产',
  tangible_asset_to_asset DECIMAL(10,4) DEFAULT NULL COMMENT '有形资产/总资产',
  ebit_to_interest DECIMAL(10,4) DEFAULT NULL COMMENT '息税前利润/利息支出',
  create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
  update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY `uk_stock_date` (`stock_code`, `statistic_date`),
  KEY `idx_publish_date` (`publish_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='证券季频现金流量表';

-- =====================================================
-- 3. stock_growth_data
-- =====================================================
SELECT '=== Adding columns to stock_growth_data ===' AS status;

ALTER TABLE stock_growth_data ADD COLUMN revenue_yoy DECIMAL(10,4) DEFAULT NULL COMMENT '营业收入同比增长率 (%)' AFTER statistic_date;
ALTER TABLE stock_growth_data ADD COLUMN operating_profit_yoy DECIMAL(10,4) DEFAULT NULL COMMENT '营业利润同比增长率 (%)' AFTER revenue_yoy;
ALTER TABLE stock_growth_data ADD COLUMN net_profit_yoy DECIMAL(10,4) DEFAULT NULL COMMENT '净利润同比增长率 (%)' AFTER operating_profit_yoy;
ALTER TABLE stock_growth_data ADD COLUMN total_assets_yoy DECIMAL(10,4) DEFAULT NULL COMMENT '总资产同比增长率 (%)' AFTER net_profit_yoy;
ALTER TABLE stock_growth_data ADD COLUMN total_equity_yoy DECIMAL(10,4) DEFAULT NULL COMMENT '股东权益同比增长率 (%)' AFTER total_assets_yoy;
ALTER TABLE stock_growth_data ADD COLUMN yoy_equity DECIMAL(10,4) DEFAULT NULL COMMENT '净资产同比增长率 (%)' AFTER total_equity_yoy;
ALTER TABLE stock_growth_data ADD COLUMN yoy_asset DECIMAL(10,4) DEFAULT NULL COMMENT '总资产同比增长率 (%)' AFTER yoy_equity;
ALTER TABLE stock_growth_data ADD COLUMN yoy_ni DECIMAL(10,4) DEFAULT NULL COMMENT '净利润同比增长率 (%)' AFTER yoy_asset;
ALTER TABLE stock_growth_data ADD COLUMN yoy_eps_basic DECIMAL(10,4) DEFAULT NULL COMMENT '基本 EPS 同比增长率 (%)' AFTER yoy_ni;
ALTER TABLE stock_growth_data ADD COLUMN yoy_pni DECIMAL(10,4) DEFAULT NULL COMMENT '归属母公司净利润同比增长率 (%)' AFTER yoy_eps_basic;

-- =====================================================
-- 4. stock_operation_data
-- =====================================================
SELECT '=== Adding columns to stock_operation_data ===' AS status;

ALTER TABLE stock_operation_data ADD COLUMN inventory_turnover DECIMAL(10,4) DEFAULT NULL COMMENT '存货周转率' AFTER statistic_date;
ALTER TABLE stock_operation_data ADD COLUMN receivables_turnover DECIMAL(10,4) DEFAULT NULL COMMENT '应收账款周转率' AFTER inventory_turnover;
ALTER TABLE stock_operation_data ADD COLUMN current_assets_turnover DECIMAL(10,4) DEFAULT NULL COMMENT '流动资产周转率' AFTER receivables_turnover;
ALTER TABLE stock_operation_data ADD COLUMN total_assets_turnover DECIMAL(10,4) DEFAULT NULL COMMENT '总资产周转率' AFTER current_assets_turnover;
ALTER TABLE stock_operation_data ADD COLUMN nr_turn_ratio DECIMAL(10,4) DEFAULT NULL COMMENT '营业收入周转率' AFTER total_assets_turnover;
ALTER TABLE stock_operation_data ADD COLUMN nr_turn_days DECIMAL(10,4) DEFAULT NULL COMMENT '营业收入周转天数' AFTER nr_turn_ratio;
ALTER TABLE stock_operation_data ADD COLUMN inv_turn_ratio DECIMAL(10,4) DEFAULT NULL COMMENT '存货周转率' AFTER nr_turn_days;
ALTER TABLE stock_operation_data ADD COLUMN inv_turn_days DECIMAL(10,4) DEFAULT NULL COMMENT '存货周转天数' AFTER inv_turn_ratio;
ALTER TABLE stock_operation_data ADD COLUMN ca_turn_ratio DECIMAL(10,4) DEFAULT NULL COMMENT '流动资产周转率' AFTER inv_turn_days;
ALTER TABLE stock_operation_data ADD COLUMN asset_turn_ratio DECIMAL(10,4) DEFAULT NULL COMMENT '总资产周转率' AFTER ca_turn_ratio;

-- =====================================================
-- 5. stock_dupont_data
-- =====================================================
SELECT '=== Adding columns to stock_dupont_data ===' AS status;

ALTER TABLE stock_dupont_data ADD COLUMN roe DECIMAL(10,4) DEFAULT NULL COMMENT '净资产收益率 (%)' AFTER statistic_date;
ALTER TABLE stock_dupont_data ADD COLUMN net_profit_margin DECIMAL(10,4) DEFAULT NULL COMMENT '销售净利率 (%)' AFTER roe;
ALTER TABLE stock_dupont_data ADD COLUMN asset_turnover DECIMAL(10,4) DEFAULT NULL COMMENT '总资产周转率' AFTER net_profit_margin;
ALTER TABLE stock_dupont_data ADD COLUMN equity_multiplier DECIMAL(10,4) DEFAULT NULL COMMENT '权益乘数' AFTER asset_turnover;
ALTER TABLE stock_dupont_data ADD COLUMN dupont_roe DECIMAL(10,4) DEFAULT NULL COMMENT 'ROE(杜邦分析)' AFTER equity_multiplier;
ALTER TABLE stock_dupont_data ADD COLUMN dupont_asset_sto_equity DECIMAL(10,4) DEFAULT NULL COMMENT '资产/权益' AFTER dupont_roe;
ALTER TABLE stock_dupont_data ADD COLUMN dupont_asset_turn DECIMAL(10,4) DEFAULT NULL COMMENT '资产周转率' AFTER dupont_asset_sto_equity;
ALTER TABLE stock_dupont_data ADD COLUMN dupont_pnitoni DECIMAL(10,4) DEFAULT NULL COMMENT '净利润/总收入' AFTER dupont_asset_turn;
ALTER TABLE stock_dupont_data ADD COLUMN dupont_nitogr DECIMAL(10,4) DEFAULT NULL COMMENT '净利润/营业收入' AFTER dupont_pnitoni;
ALTER TABLE stock_dupont_data ADD COLUMN dupont_tax_burden DECIMAL(10,4) DEFAULT NULL COMMENT '税负比率' AFTER dupont_nitogr;
ALTER TABLE stock_dupont_data ADD COLUMN dupont_int_burden DECIMAL(10,4) DEFAULT NULL COMMENT '利息负担比率' AFTER dupont_tax_burden;
ALTER TABLE stock_dupont_data ADD COLUMN dupont_ebit_to_gr DECIMAL(10,4) DEFAULT NULL COMMENT 'EBIT/营业收入' AFTER dupont_int_burden;

-- =====================================================
-- 6. stock_profit_data
-- =====================================================
SELECT '=== Adding columns to stock_profit_data ===' AS status;

ALTER TABLE stock_profit_data ADD COLUMN roe_avg DECIMAL(10,4) DEFAULT NULL COMMENT '平均 ROE' AFTER statistic_date;
ALTER TABLE stock_profit_data ADD COLUMN np_margin DECIMAL(10,4) DEFAULT NULL COMMENT '净利率' AFTER roe_avg;
ALTER TABLE stock_profit_data ADD COLUMN gp_margin DECIMAL(10,4) DEFAULT NULL COMMENT '毛利率' AFTER np_margin;
ALTER TABLE stock_profit_data ADD COLUMN net_profit DECIMAL(20,4) DEFAULT NULL COMMENT '净利润' AFTER gp_margin;
ALTER TABLE stock_profit_data ADD COLUMN eps_ttm DECIMAL(10,4) DEFAULT NULL COMMENT 'EPS(TTM)' AFTER net_profit;
ALTER TABLE stock_profit_data ADD COLUMN mb_revenue DECIMAL(20,4) DEFAULT NULL COMMENT '营业收入' AFTER eps_ttm;

-- =====================================================
-- 验证
-- =====================================================
SELECT '=== Verification ===' AS status;

SELECT table_name, column_name, data_type 
FROM information_schema.columns 
WHERE table_schema = 'stock' 
  AND table_name IN ('stock_balance_data', 'stock_growth_data', 'stock_operation_data', 'stock_dupont_data', 'stock_cash_flow_data')
  AND column_name IN ('current_ratio', 'yoy_equity', 'nr_turn_ratio', 'dupont_roe', 'cfo_to_or')
ORDER BY table_name, ordinal_position;

SELECT '=== Done ===' AS status;

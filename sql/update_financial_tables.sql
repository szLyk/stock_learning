-- =====================================================
-- 财务数据表结构更新（添加缺失的字段）
-- 执行前请确保：USE stock;
-- 注意：需要使用 root 用户或有 ALTER 权限的用户执行
-- =====================================================

USE stock;

-- =====================================================
-- 1. 资产负债表添加字段
-- =====================================================
ALTER TABLE stock_balance_data 
ADD COLUMN IF NOT EXISTS current_ratio DECIMAL(10,4) DEFAULT NULL COMMENT '流动比率' AFTER update_time,
ADD COLUMN IF NOT EXISTS quick_ratio DECIMAL(10,4) DEFAULT NULL COMMENT '速动比率' AFTER current_ratio,
ADD COLUMN IF NOT EXISTS cash_ratio DECIMAL(10,4) DEFAULT NULL COMMENT '现金比率' AFTER quick_ratio,
ADD COLUMN IF NOT EXISTS yoy_liability DECIMAL(10,4) DEFAULT NULL COMMENT '负债同比增长率 (%)' AFTER cash_ratio,
ADD COLUMN IF NOT EXISTS liability_to_asset DECIMAL(10,4) DEFAULT NULL COMMENT '资产负债率 (%)' AFTER yoy_liability,
ADD COLUMN IF NOT EXISTS asset_to_equity DECIMAL(10,4) DEFAULT NULL COMMENT '资产/权益' AFTER liability_to_asset;

-- =====================================================
-- 2. 成长能力表添加字段
-- =====================================================
ALTER TABLE stock_growth_data 
ADD COLUMN IF NOT EXISTS yoy_equity DECIMAL(10,4) DEFAULT NULL COMMENT '净资产同比增长率 (%)' AFTER update_time,
ADD COLUMN IF NOT EXISTS yoy_asset DECIMAL(10,4) DEFAULT NULL COMMENT '总资产同比增长率 (%)' AFTER yoy_equity,
ADD COLUMN IF NOT EXISTS yoy_ni DECIMAL(10,4) DEFAULT NULL COMMENT '净利润同比增长率 (%)' AFTER yoy_asset,
ADD COLUMN IF NOT EXISTS yoy_eps_basic DECIMAL(10,4) DEFAULT NULL COMMENT '基本 EPS 同比增长率 (%)' AFTER yoy_ni,
ADD COLUMN IF NOT EXISTS yoy_pni DECIMAL(10,4) DEFAULT NULL COMMENT '归属母公司净利润同比增长率 (%)' AFTER yoy_eps_basic;

-- =====================================================
-- 3. 运营能力表添加字段
-- =====================================================
ALTER TABLE stock_operation_data 
ADD COLUMN IF NOT EXISTS nr_turn_ratio DECIMAL(10,4) DEFAULT NULL COMMENT '营业收入周转率' AFTER update_time,
ADD COLUMN IF NOT EXISTS nr_turn_days DECIMAL(10,4) DEFAULT NULL COMMENT '营业收入周转天数' AFTER nr_turn_ratio,
ADD COLUMN IF NOT EXISTS inv_turn_ratio DECIMAL(10,4) DEFAULT NULL COMMENT '存货周转率' AFTER nr_turn_days,
ADD COLUMN IF NOT EXISTS inv_turn_days DECIMAL(10,4) DEFAULT NULL COMMENT '存货周转天数' AFTER inv_turn_ratio,
ADD COLUMN IF NOT EXISTS ca_turn_ratio DECIMAL(10,4) DEFAULT NULL COMMENT '流动资产周转率' AFTER inv_turn_days,
ADD COLUMN IF NOT EXISTS asset_turn_ratio DECIMAL(10,4) DEFAULT NULL COMMENT '总资产周转率' AFTER ca_turn_ratio;

-- =====================================================
-- 4. 杜邦分析表添加字段
-- =====================================================
ALTER TABLE stock_dupont_data 
ADD COLUMN IF NOT EXISTS dupont_roe DECIMAL(10,4) DEFAULT NULL COMMENT 'ROE(杜邦分析)' AFTER update_time,
ADD COLUMN IF NOT EXISTS dupont_asset_sto_equity DECIMAL(10,4) DEFAULT NULL COMMENT '资产/权益' AFTER dupont_roe,
ADD COLUMN IF NOT EXISTS dupont_asset_turn DECIMAL(10,4) DEFAULT NULL COMMENT '资产周转率' AFTER dupont_asset_sto_equity,
ADD COLUMN IF NOT EXISTS dupont_pnitoni DECIMAL(10,4) DEFAULT NULL COMMENT '净利润/总收入' AFTER dupont_asset_turn,
ADD COLUMN IF NOT EXISTS dupont_nitogr DECIMAL(10,4) DEFAULT NULL COMMENT '净利润/营业收入' AFTER dupont_pnitoni,
ADD COLUMN IF NOT EXISTS dupont_tax_burden DECIMAL(10,4) DEFAULT NULL COMMENT '税负比率' AFTER dupont_nitogr,
ADD COLUMN IF NOT EXISTS dupont_int_burden DECIMAL(10,4) DEFAULT NULL COMMENT '利息负担比率' AFTER dupont_tax_burden,
ADD COLUMN IF NOT EXISTS dupont_ebit_to_gr DECIMAL(10,4) DEFAULT NULL COMMENT 'EBIT/营业收入' AFTER dupont_int_burden;

-- =====================================================
-- 5. 现金流量表添加字段
-- =====================================================
ALTER TABLE stock_cash_flow_data 
ADD COLUMN IF NOT EXISTS ca_to_asset DECIMAL(10,4) DEFAULT NULL COMMENT '流动资产/总资产' AFTER update_time,
ADD COLUMN IF NOT EXISTS nca_to_asset DECIMAL(10,4) DEFAULT NULL COMMENT '非流动资产/总资产' AFTER ca_to_asset,
ADD COLUMN IF NOT EXISTS tangible_asset_to_asset DECIMAL(10,4) DEFAULT NULL COMMENT '有形资产/总资产' AFTER nca_to_asset,
ADD COLUMN IF NOT EXISTS ebit_to_interest DECIMAL(10,4) DEFAULT NULL COMMENT '息税前利润/利息支出' AFTER tangible_asset_to_asset,
ADD COLUMN IF NOT EXISTS cfo_to_or DECIMAL(10,4) DEFAULT NULL COMMENT '经营活动现金流量净额/营业收入' AFTER ebit_to_interest,
ADD COLUMN IF NOT EXISTS cfo_to_np DECIMAL(10,4) DEFAULT NULL COMMENT '经营活动现金流量净额/净利润' AFTER cfo_to_or,
ADD COLUMN IF NOT EXISTS cfo_to_gr DECIMAL(10,4) DEFAULT NULL COMMENT '经营活动现金流量净额/营业总收入' AFTER cfo_to_np;

-- =====================================================
-- 验证表结构
-- =====================================================
SELECT '=== 表结构更新完成 ===' AS status;

SELECT table_name, column_name, data_type, column_comment
FROM information_schema.columns
WHERE table_schema = 'stock' 
  AND table_name IN ('stock_balance_data', 'stock_growth_data', 'stock_operation_data', 'stock_dupont_data', 'stock_cash_flow_data')
ORDER BY table_name, ordinal_position;

-- =====================================================
-- 同步 Baostock 财务数据表结构（2026-03-16）
-- 根据 Baostock 实际返回的字段更新数据库表结构
-- 执行方式：mysql -h 192.168.1.109 -P 3306 -u root -p stock < sql/sync_baostock_tables.sql
-- =====================================================

USE stock;

-- =====================================================
-- 存储过程：安全添加列
-- =====================================================
DROP PROCEDURE IF EXISTS AddColumnIfNotExists;

DELIMITER $$

CREATE PROCEDURE AddColumnIfNotExists(
    IN table_name VARCHAR(64),
    IN column_name VARCHAR(64),
    IN column_definition TEXT,
    IN column_comment VARCHAR(255)
)
BEGIN
    DECLARE column_exists INT DEFAULT 0;
    
    SELECT COUNT(*) INTO column_exists
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = table_name
      AND column_name = column_name;
    
    IF column_exists = 0 THEN
        SET @sql = CONCAT('ALTER TABLE ', table_name, ' ADD COLUMN ', column_name, ' ', column_definition, ' COMMENT \'', column_comment, '\'');
        PREPARE stmt FROM @sql;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
        SELECT CONCAT('添加列 ', table_name, '.', column_name, ' 成功') AS result;
    ELSE
        SELECT CONCAT('列 ', table_name, '.', column_name, ' 已存在，跳过') AS result;
    END IF;
END$$

DELIMITER ;

-- =====================================================
-- 1. 资产负债表 (query_balance_data)
-- Baostock 返回字段：code, pubDate, statDate, totalAssets, totalLiability, totalEquity, 
-- totalShare, liqaShare, capitalReserve, surplusReserve, undistributedProfit, 
-- currentRatio, quickRatio, cashRatio, YOYLiability, liabilityToAsset, assetToEquity
-- =====================================================
SELECT '=== 更新 stock_balance_data ===' AS status;

CALL AddColumnIfNotExists('stock_balance_data', 'total_assets', 'DECIMAL(20,4) DEFAULT NULL', '总资产');
CALL AddColumnIfNotExists('stock_balance_data', 'total_liabilities', 'DECIMAL(20,4) DEFAULT NULL', '总负债');
CALL AddColumnIfNotExists('stock_balance_data', 'total_equity', 'DECIMAL(20,4) DEFAULT NULL', '股东权益合计');
CALL AddColumnIfNotExists('stock_balance_data', 'total_share', 'DECIMAL(20,4) DEFAULT NULL', '总股本');
CALL AddColumnIfNotExists('stock_balance_data', 'liqa_share', 'DECIMAL(20,4) DEFAULT NULL', '流通股本');
CALL AddColumnIfNotExists('stock_balance_data', 'capital_reserve', 'DECIMAL(20,4) DEFAULT NULL', '资本公积金');
CALL AddColumnIfNotExists('stock_balance_data', 'surplus_reserve', 'DECIMAL(20,4) DEFAULT NULL', '盈余公积金');
CALL AddColumnIfNotExists('stock_balance_data', 'undistributed_profit', 'DECIMAL(20,4) DEFAULT NULL', '未分配利润');
CALL AddColumnIfNotExists('stock_balance_data', 'current_ratio', 'DECIMAL(10,4) DEFAULT NULL', '流动比率');
CALL AddColumnIfNotExists('stock_balance_data', 'quick_ratio', 'DECIMAL(10,4) DEFAULT NULL', '速动比率');
CALL AddColumnIfNotExists('stock_balance_data', 'cash_ratio', 'DECIMAL(10,4) DEFAULT NULL', '现金比率');
CALL AddColumnIfNotExists('stock_balance_data', 'yoy_liability', 'DECIMAL(10,4) DEFAULT NULL', '负债同比增长率 (%)');
CALL AddColumnIfNotExists('stock_balance_data', 'liability_to_asset', 'DECIMAL(10,4) DEFAULT NULL', '资产负债率 (%)');
CALL AddColumnIfNotExists('stock_balance_data', 'asset_to_equity', 'DECIMAL(10,4) DEFAULT NULL', '资产/权益');
CALL AddColumnIfNotExists('stock_balance_data', 'season', 'INT DEFAULT NULL', '季度 (1-4)');

-- =====================================================
-- 2. 现金流量表 (query_cash_flow_data)
-- Baostock 返回字段：code, pubDate, statDate, cfoToOR, cfoToNP, cfoToGR, 
-- caToAsset, ncaToAsset, tangibleAssetToAsset, ebitToInterest
-- =====================================================
SELECT '=== 更新 stock_cash_flow_data ===' AS status;

CALL AddColumnIfNotExists('stock_cash_flow_data', 'cfo_to_or', 'DECIMAL(10,4) DEFAULT NULL', '经营活动产生的现金流量净额/营业收入');
CALL AddColumnIfNotExists('stock_cash_flow_data', 'cfo_to_np', 'DECIMAL(10,4) DEFAULT NULL', '经营活动产生的现金流量净额/净利润');
CALL AddColumnIfNotExists('stock_cash_flow_data', 'cfo_to_gr', 'DECIMAL(10,4) DEFAULT NULL', '经营活动产生的现金流量净额/营业总收入');
CALL AddColumnIfNotExists('stock_cash_flow_data', 'ca_to_asset', 'DECIMAL(10,4) DEFAULT NULL', '流动资产/总资产');
CALL AddColumnIfNotExists('stock_cash_flow_data', 'nca_to_asset', 'DECIMAL(10,4) DEFAULT NULL', '非流动资产/总资产');
CALL AddColumnIfNotExists('stock_cash_flow_data', 'tangible_asset_to_asset', 'DECIMAL(10,4) DEFAULT NULL', '有形资产/总资产');
CALL AddColumnIfNotExists('stock_cash_flow_data', 'ebit_to_interest', 'DECIMAL(10,4) DEFAULT NULL', '息税前利润/利息支出');
CALL AddColumnIfNotExists('stock_cash_flow_data', 'season', 'INT DEFAULT NULL', '季度 (1-4)');

-- =====================================================
-- 3. 成长能力表 (query_growth_data)
-- Baostock 返回字段：code, pubDate, statDate, revenueYOY, operatingProfitYOY, 
-- netProfitYOY, totalAssetsYOY, totalEquityYOY, YOYEquity, YOYAsset, YOYNI, 
-- YOYEPSBasic, YOYPNI
-- =====================================================
SELECT '=== 更新 stock_growth_data ===' AS status;

CALL AddColumnIfNotExists('stock_growth_data', 'revenue_yoy', 'DECIMAL(10,4) DEFAULT NULL', '营业收入同比增长率 (%)');
CALL AddColumnIfNotExists('stock_growth_data', 'operating_profit_yoy', 'DECIMAL(10,4) DEFAULT NULL', '营业利润同比增长率 (%)');
CALL AddColumnIfNotExists('stock_growth_data', 'net_profit_yoy', 'DECIMAL(10,4) DEFAULT NULL', '净利润同比增长率 (%)');
CALL AddColumnIfNotExists('stock_growth_data', 'total_assets_yoy', 'DECIMAL(10,4) DEFAULT NULL', '总资产同比增长率 (%)');
CALL AddColumnIfNotExists('stock_growth_data', 'total_equity_yoy', 'DECIMAL(10,4) DEFAULT NULL', '股东权益同比增长率 (%)');
CALL AddColumnIfNotExists('stock_growth_data', 'yoy_equity', 'DECIMAL(10,4) DEFAULT NULL', '净资产同比增长率 (%)');
CALL AddColumnIfNotExists('stock_growth_data', 'yoy_asset', 'DECIMAL(10,4) DEFAULT NULL', '总资产同比增长率 (%)');
CALL AddColumnIfNotExists('stock_growth_data', 'yoy_ni', 'DECIMAL(10,4) DEFAULT NULL', '净利润同比增长率 (%)');
CALL AddColumnIfNotExists('stock_growth_data', 'yoy_eps_basic', 'DECIMAL(10,4) DEFAULT NULL', '基本 EPS 同比增长率 (%)');
CALL AddColumnIfNotExists('stock_growth_data', 'yoy_pni', 'DECIMAL(10,4) DEFAULT NULL', '归属母公司净利润同比增长率 (%)');
CALL AddColumnIfNotExists('stock_growth_data', 'season', 'INT DEFAULT NULL', '季度 (1-4)');

-- =====================================================
-- 4. 运营能力表 (query_operation_data)
-- Baostock 返回字段：code, pubDate, statDate, inventoryTurnover, receivablesTurnover, 
-- currentAssetsTurnover, totalAssetsTurnover, NRTurnRatio, NRTurnDays, INVTurnRatio, 
-- INVTurnDays, CATurnRatio, AssetTurnRatio
-- =====================================================
SELECT '=== 更新 stock_operation_data ===' AS status;

CALL AddColumnIfNotExists('stock_operation_data', 'inventory_turnover', 'DECIMAL(10,4) DEFAULT NULL', '存货周转率');
CALL AddColumnIfNotExists('stock_operation_data', 'receivables_turnover', 'DECIMAL(10,4) DEFAULT NULL', '应收账款周转率');
CALL AddColumnIfNotExists('stock_operation_data', 'current_assets_turnover', 'DECIMAL(10,4) DEFAULT NULL', '流动资产周转率');
CALL AddColumnIfNotExists('stock_operation_data', 'total_assets_turnover', 'DECIMAL(10,4) DEFAULT NULL', '总资产周转率');
CALL AddColumnIfNotExists('stock_operation_data', 'nr_turn_ratio', 'DECIMAL(10,4) DEFAULT NULL', '营业收入周转率');
CALL AddColumnIfNotExists('stock_operation_data', 'nr_turn_days', 'DECIMAL(10,4) DEFAULT NULL', '营业收入周转天数');
CALL AddColumnIfNotExists('stock_operation_data', 'inv_turn_ratio', 'DECIMAL(10,4) DEFAULT NULL', '存货周转率');
CALL AddColumnIfNotExists('stock_operation_data', 'inv_turn_days', 'DECIMAL(10,4) DEFAULT NULL', '存货周转天数');
CALL AddColumnIfNotExists('stock_operation_data', 'ca_turn_ratio', 'DECIMAL(10,4) DEFAULT NULL', '流动资产周转率');
CALL AddColumnIfNotExists('stock_operation_data', 'asset_turn_ratio', 'DECIMAL(10,4) DEFAULT NULL', '总资产周转率');
CALL AddColumnIfNotExists('stock_operation_data', 'season', 'INT DEFAULT NULL', '季度 (1-4)');

-- =====================================================
-- 5. 杜邦分析表 (query_dupont_data)
-- Baostock 返回字段：code, pubDate, statDate, ROE, netProfitMargin, assetTurnover, 
-- equityMultiplier, dupontROE, dupontAssetStoEquity, dupontAssetTurn, 
-- dupontPnitoni, dupontNitogr, dupontTaxBurden, dupontIntburden, dupontEbittogr
-- =====================================================
SELECT '=== 更新 stock_dupont_data ===' AS status;

CALL AddColumnIfNotExists('stock_dupont_data', 'roe', 'DECIMAL(10,4) DEFAULT NULL', '净资产收益率 (%)');
CALL AddColumnIfNotExists('stock_dupont_data', 'net_profit_margin', 'DECIMAL(10,4) DEFAULT NULL', '销售净利率 (%)');
CALL AddColumnIfNotExists('stock_dupont_data', 'asset_turnover', 'DECIMAL(10,4) DEFAULT NULL', '总资产周转率');
CALL AddColumnIfNotExists('stock_dupont_data', 'equity_multiplier', 'DECIMAL(10,4) DEFAULT NULL', '权益乘数');
CALL AddColumnIfNotExists('stock_dupont_data', 'dupont_roe', 'DECIMAL(10,4) DEFAULT NULL', 'ROE(杜邦分析)');
CALL AddColumnIfNotExists('stock_dupont_data', 'dupont_asset_sto_equity', 'DECIMAL(10,4) DEFAULT NULL', '资产/权益');
CALL AddColumnIfNotExists('stock_dupont_data', 'dupont_asset_turn', 'DECIMAL(10,4) DEFAULT NULL', '资产周转率');
CALL AddColumnIfNotExists('stock_dupont_data', 'dupont_pnitoni', 'DECIMAL(10,4) DEFAULT NULL', '净利润/总收入');
CALL AddColumnIfNotExists('stock_dupont_data', 'dupont_nitogr', 'DECIMAL(10,4) DEFAULT NULL', '净利润/营业收入');
CALL AddColumnIfNotExists('stock_dupont_data', 'dupont_tax_burden', 'DECIMAL(10,4) DEFAULT NULL', '税负比率');
CALL AddColumnIfNotExists('stock_dupont_data', 'dupont_int_burden', 'DECIMAL(10,4) DEFAULT NULL', '利息负担比率');
CALL AddColumnIfNotExists('stock_dupont_data', 'dupont_ebit_to_gr', 'DECIMAL(10,4) DEFAULT NULL', 'EBIT/营业收入');
CALL AddColumnIfNotExists('stock_dupont_data', 'season', 'INT DEFAULT NULL', '季度 (1-4)');

-- =====================================================
-- 6. 利润表 (query_profit_data)
-- 确保所有字段都存在
-- =====================================================
SELECT '=== 更新 stock_profit_data ===' AS status;

CALL AddColumnIfNotExists('stock_profit_data', 'roe_avg', 'DECIMAL(10,4) DEFAULT NULL', '平均 ROE');
CALL AddColumnIfNotExists('stock_profit_data', 'np_margin', 'DECIMAL(10,4) DEFAULT NULL', '净利率');
CALL AddColumnIfNotExists('stock_profit_data', 'gp_margin', 'DECIMAL(10,4) DEFAULT NULL', '毛利率');
CALL AddColumnIfNotExists('stock_profit_data', 'net_profit', 'DECIMAL(20,4) DEFAULT NULL', '净利润');
CALL AddColumnIfNotExists('stock_profit_data', 'eps_ttm', 'DECIMAL(10,4) DEFAULT NULL', 'EPS(TTM)');
CALL AddColumnIfNotExists('stock_profit_data', 'mb_revenue', 'DECIMAL(20,4) DEFAULT NULL', '营业收入');
CALL AddColumnIfNotExists('stock_profit_data', 'total_share', 'DECIMAL(20,4) DEFAULT NULL', '总股本');
CALL AddColumnIfNotExists('stock_profit_data', 'liqa_share', 'DECIMAL(20,4) DEFAULT NULL', '流通股本');
CALL AddColumnIfNotExists('stock_profit_data', 'season', 'INT DEFAULT NULL', '季度 (1-4)');

-- =====================================================
-- 清理存储过程
-- =====================================================
DROP PROCEDURE IF EXISTS AddColumnIfNotExists;

-- =====================================================
-- 验证表结构
-- =====================================================
SELECT '=== 表结构更新完成，验证结果 ===' AS status;

SELECT 
    table_name,
    COUNT(*) as column_count
FROM information_schema.columns
WHERE table_schema = 'stock' 
  AND table_name IN (
    'stock_profit_data',
    'stock_balance_data',
    'stock_cash_flow_data',
    'stock_growth_data',
    'stock_operation_data',
    'stock_dupont_data'
  )
GROUP BY table_name
ORDER BY table_name;

-- 显示关键缺失字段是否已添加
SELECT '=== 检查关键字段 ===' AS status;

SELECT 
    table_name,
    column_name,
    data_type,
    column_type
FROM information_schema.columns
WHERE table_schema = 'stock' 
  AND table_name IN (
    'stock_balance_data',
    'stock_growth_data',
    'stock_operation_data',
    'stock_dupont_data'
  )
  AND column_name IN (
    'current_ratio', 'quick_ratio', 'cash_ratio',
    'yoy_equity', 'yoy_asset', 'yoy_ni',
    'nr_turn_ratio', 'nr_turn_days', 'inv_turn_ratio',
    'dupont_roe', 'dupont_asset_sto_equity', 'dupont_asset_turn'
  )
ORDER BY table_name, column_name;

SELECT '=== 同步完成 ===' AS status;

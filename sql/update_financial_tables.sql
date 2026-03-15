-- =====================================================
-- 财务数据表结构更新（添加缺失的字段）
-- 执行前请确保：USE stock;
-- 注意：需要使用 root 用户或有 ALTER 权限的用户执行
-- 执行方式：mysql -h 192.168.1.109 -P 3306 -u root -p stock < sql/update_financial_tables.sql
-- =====================================================

USE stock;

-- =====================================================
-- 存储过程：安全添加列（如果列不存在）
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
    END IF;
END$$

DELIMITER ;

-- =====================================================
-- 1. 资产负债表添加字段
-- =====================================================
CALL AddColumnIfNotExists('stock_balance_data', 'current_ratio', 'DECIMAL(10,4) DEFAULT NULL', '流动比率');
CALL AddColumnIfNotExists('stock_balance_data', 'quick_ratio', 'DECIMAL(10,4) DEFAULT NULL', '速动比率');
CALL AddColumnIfNotExists('stock_balance_data', 'cash_ratio', 'DECIMAL(10,4) DEFAULT NULL', '现金比率');
CALL AddColumnIfNotExists('stock_balance_data', 'yoy_liability', 'DECIMAL(10,4) DEFAULT NULL', '负债同比增长率 (%)');
CALL AddColumnIfNotExists('stock_balance_data', 'liability_to_asset', 'DECIMAL(10,4) DEFAULT NULL', '资产负债率 (%)');
CALL AddColumnIfNotExists('stock_balance_data', 'asset_to_equity', 'DECIMAL(10,4) DEFAULT NULL', '资产/权益');

-- =====================================================
-- 2. 成长能力表添加字段
-- =====================================================
CALL AddColumnIfNotExists('stock_growth_data', 'yoy_equity', 'DECIMAL(10,4) DEFAULT NULL', '净资产同比增长率 (%)');
CALL AddColumnIfNotExists('stock_growth_data', 'yoy_asset', 'DECIMAL(10,4) DEFAULT NULL', '总资产同比增长率 (%)');
CALL AddColumnIfNotExists('stock_growth_data', 'yoy_ni', 'DECIMAL(10,4) DEFAULT NULL', '净利润同比增长率 (%)');
CALL AddColumnIfNotExists('stock_growth_data', 'yoy_eps_basic', 'DECIMAL(10,4) DEFAULT NULL', '基本 EPS 同比增长率 (%)');
CALL AddColumnIfNotExists('stock_growth_data', 'yoy_pni', 'DECIMAL(10,4) DEFAULT NULL', '归属母公司净利润同比增长率 (%)');

-- =====================================================
-- 3. 运营能力表添加字段
-- =====================================================
CALL AddColumnIfNotExists('stock_operation_data', 'nr_turn_ratio', 'DECIMAL(10,4) DEFAULT NULL', '营业收入周转率');
CALL AddColumnIfNotExists('stock_operation_data', 'nr_turn_days', 'DECIMAL(10,4) DEFAULT NULL', '营业收入周转天数');
CALL AddColumnIfNotExists('stock_operation_data', 'inv_turn_ratio', 'DECIMAL(10,4) DEFAULT NULL', '存货周转率');
CALL AddColumnIfNotExists('stock_operation_data', 'inv_turn_days', 'DECIMAL(10,4) DEFAULT NULL', '存货周转天数');
CALL AddColumnIfNotExists('stock_operation_data', 'ca_turn_ratio', 'DECIMAL(10,4) DEFAULT NULL', '流动资产周转率');
CALL AddColumnIfNotExists('stock_operation_data', 'asset_turn_ratio', 'DECIMAL(10,4) DEFAULT NULL', '总资产周转率');

-- =====================================================
-- 4. 杜邦分析表添加字段
-- =====================================================
CALL AddColumnIfNotExists('stock_dupont_data', 'dupont_roe', 'DECIMAL(10,4) DEFAULT NULL', 'ROE(杜邦分析)');
CALL AddColumnIfNotExists('stock_dupont_data', 'dupont_asset_sto_equity', 'DECIMAL(10,4) DEFAULT NULL', '资产/权益');
CALL AddColumnIfNotExists('stock_dupont_data', 'dupont_asset_turn', 'DECIMAL(10,4) DEFAULT NULL', '资产周转率');
CALL AddColumnIfNotExists('stock_dupont_data', 'dupont_pnitoni', 'DECIMAL(10,4) DEFAULT NULL', '净利润/总收入');
CALL AddColumnIfNotExists('stock_dupont_data', 'dupont_nitogr', 'DECIMAL(10,4) DEFAULT NULL', '净利润/营业收入');
CALL AddColumnIfNotExists('stock_dupont_data', 'dupont_tax_burden', 'DECIMAL(10,4) DEFAULT NULL', '税负比率');
CALL AddColumnIfNotExists('stock_dupont_data', 'dupont_int_burden', 'DECIMAL(10,4) DEFAULT NULL', '利息负担比率');
CALL AddColumnIfNotExists('stock_dupont_data', 'dupont_ebit_to_gr', 'DECIMAL(10,4) DEFAULT NULL', 'EBIT/营业收入');

-- =====================================================
-- 5. 现金流量表添加字段
-- =====================================================
CALL AddColumnIfNotExists('stock_cash_flow_data', 'ca_to_asset', 'DECIMAL(10,4) DEFAULT NULL', '流动资产/总资产');
CALL AddColumnIfNotExists('stock_cash_flow_data', 'nca_to_asset', 'DECIMAL(10,4) DEFAULT NULL', '非流动资产/总资产');
CALL AddColumnIfNotExists('stock_cash_flow_data', 'tangible_asset_to_asset', 'DECIMAL(10,4) DEFAULT NULL', '有形资产/总资产');
CALL AddColumnIfNotExists('stock_cash_flow_data', 'ebit_to_interest', 'DECIMAL(10,4) DEFAULT NULL', '息税前利润/利息支出');
CALL AddColumnIfNotExists('stock_cash_flow_data', 'cfo_to_or', 'DECIMAL(10,4) DEFAULT NULL', '经营活动现金流量净额/营业收入');
CALL AddColumnIfNotExists('stock_cash_flow_data', 'cfo_to_np', 'DECIMAL(10,4) DEFAULT NULL', '经营活动现金流量净额/净利润');
CALL AddColumnIfNotExists('stock_cash_flow_data', 'cfo_to_gr', 'DECIMAL(10,4) DEFAULT NULL', '经营活动现金流量净额/营业总收入');

-- =====================================================
-- 清理存储过程
-- =====================================================
DROP PROCEDURE IF EXISTS AddColumnIfNotExists;

-- =====================================================
-- 验证表结构
-- =====================================================
SELECT '=== 表结构更新完成 ===' AS status;

SELECT table_name, COUNT(*) as column_count
FROM information_schema.columns
WHERE table_schema = 'stock' 
  AND table_name IN ('stock_balance_data', 'stock_growth_data', 'stock_operation_data', 'stock_dupont_data', 'stock_cash_flow_data')
GROUP BY table_name;

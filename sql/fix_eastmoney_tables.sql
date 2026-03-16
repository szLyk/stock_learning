-- =====================================================
-- EastMoney 表结构修复（同步 API 返回字段）
-- 执行方式：mysql -h 192.168.1.109 -P 3306 -u root -p123456 stock < sql/fix_eastmoney_tables.sql
-- =====================================================

SET NAMES utf8mb4;
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
        SELECT CONCAT('✅ 添加列 ', table_name, '.', column_name, ' 成功') AS result;
    ELSE
        SELECT CONCAT('⚠️  列 ', table_name, '.', column_name, ' 已存在，跳过') AS result;
    END IF;
END$$

DELIMITER ;

-- =====================================================
-- 1. stock_capital_flow (资金流向表)
-- =====================================================
-- API 返回字段：stock_code, stock_date, main_net_in, sm_net_in, mm_net_in, bm_net_in,
--              main_net_in_rate, close_price, change_rate, turnover_rate, north_hold, north_net_in

SELECT '=== 修复 stock_capital_flow ===' AS status;

CALL AddColumnIfNotExists('stock_capital_flow', 'main_net_in_rate', 'DECIMAL(10,4) DEFAULT NULL', '主力净流入率 (%)');
CALL AddColumnIfNotExists('stock_capital_flow', 'close_price', 'DECIMAL(10,2) DEFAULT NULL', '收盘价');
CALL AddColumnIfNotExists('stock_capital_flow', 'change_rate', 'DECIMAL(10,4) DEFAULT NULL', '涨跌幅 (%)');
CALL AddColumnIfNotExists('stock_capital_flow', 'turnover_rate', 'DECIMAL(10,4) DEFAULT NULL', '换手率 (%)');

-- =====================================================
-- 2. stock_shareholder_info (股东筹码信息表)
-- =====================================================
-- API 返回字段：stock_code, stock_name, report_date, shareholder_count, shareholder_change,
--              avg_hold_per_household, avg_hold_change, freehold_shares, freehold_ratio

SELECT '=== 修复 stock_shareholder_info ===' AS status;

CALL AddColumnIfNotExists('stock_shareholder_info', 'stock_name', 'VARCHAR(50) DEFAULT NULL', '股票名称' AFTER stock_code);
CALL AddColumnIfNotExists('stock_shareholder_info', 'avg_hold_change', 'DECIMAL(10,2) DEFAULT NULL', '户均持股变化率' AFTER avg_hold_per_household);
CALL AddColumnIfNotExists('stock_shareholder_info', 'freehold_shares', 'DECIMAL(15,2) DEFAULT NULL', '流通股份' AFTER avg_hold_change);
CALL AddColumnIfNotExists('stock_shareholder_info', 'freehold_ratio', 'DECIMAL(10,2) DEFAULT NULL', '流通比例 (%)' AFTER freehold_shares);

-- =====================================================
-- 3. stock_concept (概念板块表)
-- =====================================================
-- API 返回字段：stock_code, stock_name, concept_name, concept_type, is_hot
-- 当前表结构已匹配，添加 stock_name 字段

SELECT '=== 修复 stock_concept ===' AS status;

CALL AddColumnIfNotExists('stock_concept', 'stock_name', 'VARCHAR(50) DEFAULT NULL', '股票名称' AFTER stock_code);

-- =====================================================
-- 4. stock_analyst_expectation (分析师预期与评级表)
-- =====================================================
-- API 返回字段：stock_code, stock_name, publish_date, institution_name, analyst_name,
--              rating_type, rating_score, target_price

SELECT '=== 修复 stock_analyst_expectation ===' AS status;

CALL AddColumnIfNotExists('stock_analyst_expectation', 'stock_name', 'VARCHAR(50) DEFAULT NULL', '股票名称' AFTER stock_code);
CALL AddColumnIfNotExists('stock_analyst_expectation', 'institution_name', 'VARCHAR(100) DEFAULT NULL', '机构名称' AFTER publish_date);
CALL AddColumnIfNotExists('stock_analyst_expectation', 'analyst_name', 'VARCHAR(50) DEFAULT NULL', '分析师姓名' AFTER institution_name);
CALL AddColumnIfNotExists('stock_analyst_expectation', 'rating_type', 'VARCHAR(10) DEFAULT NULL', '评级类型' AFTER analyst_name);

-- =====================================================
-- 清理存储过程
-- =====================================================
DROP PROCEDURE IF EXISTS AddColumnIfNotExists;

-- =====================================================
-- 验证修复结果
-- =====================================================
SELECT '=== 验证修复结果 ===' AS status;

SELECT 
    table_name,
    GROUP_CONCAT(column_name ORDER BY ordinal_position SEPARATOR ', ') AS columns
FROM information_schema.columns
WHERE table_schema = 'stock' 
  AND table_name IN (
    'stock_capital_flow',
    'stock_shareholder_info',
    'stock_concept',
    'stock_analyst_expectation'
  )
GROUP BY table_name
ORDER BY table_name;

SELECT '=== 修复完成 ===' AS status;

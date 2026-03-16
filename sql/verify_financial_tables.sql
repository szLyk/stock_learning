-- =====================================================
-- 验证财务数据表结构
-- 执行方式：mysql -h 192.168.1.109 -P 3306 -u root -p stock < sql/verify_financial_tables.sql
-- =====================================================

USE stock;

SELECT '=== 验证财务数据表结构 ===' AS status;

-- 1. 检查资产负债表字段
SELECT '--- stock_balance_data ---' AS table_name;
SELECT column_name, data_type, column_comment 
FROM information_schema.columns 
WHERE table_schema = 'stock' AND table_name = 'stock_balance_data'
ORDER BY ordinal_position;

-- 2. 检查成长能力表字段
SELECT '--- stock_growth_data ---' AS table_name;
SELECT column_name, data_type, column_comment 
FROM information_schema.columns 
WHERE table_schema = 'stock' AND table_name = 'stock_growth_data'
ORDER BY ordinal_position;

-- 3. 检查运营能力表字段
SELECT '--- stock_operation_data ---' AS table_name;
SELECT column_name, data_type, column_comment 
FROM information_schema.columns 
WHERE table_schema = 'stock' AND table_name = 'stock_operation_data'
ORDER BY ordinal_position;

-- 4. 检查杜邦分析表字段
SELECT '--- stock_dupont_data ---' AS table_name;
SELECT column_name, data_type, column_comment 
FROM information_schema.columns 
WHERE table_schema = 'stock' AND table_name = 'stock_dupont_data'
ORDER BY ordinal_position;

-- 5. 检查关键缺失字段
SELECT '=== 检查关键字段是否存在 ===' AS status;

SELECT 
    'stock_balance_data.current_ratio' AS field,
    COUNT(*) AS exists_flag
FROM information_schema.columns 
WHERE table_schema = 'stock' AND table_name = 'stock_balance_data' AND column_name = 'current_ratio'
UNION ALL
SELECT 
    'stock_growth_data.yoy_equity' AS field,
    COUNT(*) AS exists_flag
FROM information_schema.columns 
WHERE table_schema = 'stock' AND table_name = 'stock_growth_data' AND column_name = 'yoy_equity'
UNION ALL
SELECT 
    'stock_operation_data.nr_turn_ratio' AS field,
    COUNT(*) AS exists_flag
FROM information_schema.columns 
WHERE table_schema = 'stock' AND table_name = 'stock_operation_data' AND column_name = 'nr_turn_ratio'
UNION ALL
SELECT 
    'stock_dupont_data.dupont_roe' AS field,
    COUNT(*) AS exists_flag
FROM information_schema.columns 
WHERE table_schema = 'stock' AND table_name = 'stock_dupont_data' AND column_name = 'dupont_roe';

SELECT '=== 验证完成 ===' AS status;

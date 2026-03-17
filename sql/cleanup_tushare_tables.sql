-- =====================================================
-- 清理 Tushare 相关表结构
-- 执行前请确认：已备份重要数据
-- =====================================================

USE stock;

-- =====================================================
-- 删除 Tushare 资金流向表
-- =====================================================
DROP TABLE IF EXISTS `stock_moneyflow`;
DROP TABLE IF EXISTS `update_tushare_record`;

-- =====================================================
-- 验证删除
-- =====================================================
SELECT '=== Tushare 表已删除 ===' AS status;

SELECT table_name, table_comment 
FROM information_schema.tables 
WHERE table_schema = 'stock' 
  AND (table_name LIKE '%moneyflow%' OR table_name LIKE '%tushare%')
ORDER BY table_name;

-- 如果返回空结果，说明删除成功

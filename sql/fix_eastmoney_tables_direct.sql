-- =====================================================
-- EastMoney 表结构修复（直接执行 ALTER TABLE）
-- 执行方式：mysql -h 192.168.1.109 -P 3306 -u root -p123456 stock < sql/fix_eastmoney_tables_direct.sql
-- =====================================================

SET NAMES utf8mb4;
USE stock;

-- =====================================================
-- 1. stock_capital_flow (资金流向表)
-- =====================================================
SELECT '=== 修复 stock_capital_flow ===' AS status;

ALTER TABLE stock_capital_flow ADD COLUMN IF NOT EXISTS main_net_in_rate DECIMAL(10,4) DEFAULT NULL COMMENT '主力净流入率 (%)' AFTER bm_net_in;
ALTER TABLE stock_capital_flow ADD COLUMN IF NOT EXISTS close_price DECIMAL(10,2) DEFAULT NULL COMMENT '收盘价' AFTER main_net_in_rate;
ALTER TABLE stock_capital_flow ADD COLUMN IF NOT EXISTS change_rate DECIMAL(10,4) DEFAULT NULL COMMENT '涨跌幅 (%)' AFTER close_price;
ALTER TABLE stock_capital_flow ADD COLUMN IF NOT EXISTS turnover_rate DECIMAL(10,4) DEFAULT NULL COMMENT '换手率 (%)' AFTER change_rate;

-- =====================================================
-- 2. stock_shareholder_info (股东筹码信息表)
-- =====================================================
SELECT '=== 修复 stock_shareholder_info ===' AS status;

ALTER TABLE stock_shareholder_info ADD COLUMN IF NOT EXISTS stock_name VARCHAR(50) DEFAULT NULL COMMENT '股票名称' AFTER stock_code;
ALTER TABLE stock_shareholder_info ADD COLUMN IF NOT EXISTS avg_hold_change DECIMAL(10,2) DEFAULT NULL COMMENT '户均持股变化率' AFTER avg_hold_per_household;
ALTER TABLE stock_shareholder_info ADD COLUMN IF NOT EXISTS freehold_shares DECIMAL(15,2) DEFAULT NULL COMMENT '流通股份' AFTER avg_hold_change;
ALTER TABLE stock_shareholder_info ADD COLUMN IF NOT EXISTS freehold_ratio DECIMAL(10,2) DEFAULT NULL COMMENT '流通比例 (%)' AFTER freehold_shares;

-- =====================================================
-- 3. stock_concept (概念板块表)
-- =====================================================
SELECT '=== 修复 stock_concept ===' AS status;

ALTER TABLE stock_concept ADD COLUMN IF NOT EXISTS stock_name VARCHAR(50) DEFAULT NULL COMMENT '股票名称' AFTER stock_code;

-- =====================================================
-- 4. stock_analyst_expectation (分析师预期与评级表)
-- =====================================================
SELECT '=== 修复 stock_analyst_expectation ===' AS status;

ALTER TABLE stock_analyst_expectation ADD COLUMN IF NOT EXISTS stock_name VARCHAR(50) DEFAULT NULL COMMENT '股票名称' AFTER stock_code;
ALTER TABLE stock_analyst_expectation ADD COLUMN IF NOT EXISTS institution_name VARCHAR(100) DEFAULT NULL COMMENT '机构名称' AFTER publish_date;
ALTER TABLE stock_analyst_expectation ADD COLUMN IF NOT EXISTS analyst_name VARCHAR(50) DEFAULT NULL COMMENT '分析师姓名' AFTER institution_name;
ALTER TABLE stock_analyst_expectation ADD COLUMN IF NOT EXISTS rating_type VARCHAR(10) DEFAULT NULL COMMENT '评级类型' AFTER analyst_name;

-- =====================================================
-- 验证修复结果
-- =====================================================
SELECT '=== 验证修复结果 ===' AS status;

SELECT 
    table_name,
    COUNT(*) as column_count
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

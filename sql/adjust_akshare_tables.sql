-- =====================================================
-- AkShare 数据表结构调整
-- 执行方式：mysql -h 192.168.1.109 -P 3306 -u root -p123456 stock < sql/adjust_akshare_tables.sql
-- =====================================================

SET NAMES utf8mb4;
USE stock;

-- =====================================================
-- 1. stock_capital_flow (资金流向表)
-- AkShare 返回字段：
-- 日期，主力净流入-净额，小单净流入 - 净额，中单净流入 - 净额，大单净流入 - 净额，
-- 主力净流入 - 净占比，收盘价，涨跌幅，换手率
-- =====================================================
SELECT '=== 调整 stock_capital_flow ===' AS status;

-- 检查并添加缺失字段
ALTER TABLE stock_capital_flow ADD COLUMN IF NOT EXISTS sm_net_in_rate DECIMAL(10,4) DEFAULT NULL COMMENT '小单净流入率 (%)' AFTER main_net_in_rate;
ALTER TABLE stock_capital_flow ADD COLUMN IF NOT EXISTS mm_net_in_rate DECIMAL(10,4) DEFAULT NULL COMMENT '中单净流入率 (%)' AFTER sm_net_in_rate;
ALTER TABLE stock_capital_flow ADD COLUMN IF NOT EXISTS bm_net_in_rate DECIMAL(10,4) DEFAULT NULL COMMENT '大单净流入率 (%)' AFTER mm_net_in_rate;

-- =====================================================
-- 2. stock_shareholder_info (股东人数表)
-- AkShare 返回字段：
-- 股东名称，持股数量，持股比例，股本性质，截至日期，公告日期，
-- 股东说明，股东总数，平均持股数
-- =====================================================
SELECT '=== 调整 stock_shareholder_info ===' AS status;

-- 添加 AkShare 特有字段
ALTER TABLE stock_shareholder_info ADD COLUMN IF NOT EXISTS shareholder_name VARCHAR(100) DEFAULT NULL COMMENT '股东名称' AFTER stock_name;
ALTER TABLE stock_shareholder_info ADD COLUMN IF NOT EXISTS hold_shares DECIMAL(15,2) DEFAULT NULL COMMENT '持股数量' AFTER shareholder_name;
ALTER TABLE stock_shareholder_info ADD COLUMN IF NOT EXISTS hold_ratio DECIMAL(10,4) DEFAULT NULL COMMENT '持股比例 (%)' AFTER hold_shares;
ALTER TABLE stock_shareholder_info ADD COLUMN IF NOT EXISTS share_type VARCHAR(20) DEFAULT NULL COMMENT '股本性质' AFTER hold_ratio;
ALTER TABLE stock_shareholder_info ADD COLUMN IF NOT EXISTS announce_date DATE DEFAULT NULL COMMENT '公告日期' AFTER report_date;
ALTER TABLE stock_shareholder_info ADD COLUMN IF NOT EXISTS shareholder_desc TEXT DEFAULT NULL COMMENT '股东说明' AFTER announce_date;
ALTER TABLE stock_shareholder_info ADD COLUMN IF NOT EXISTS total_shareholders INT DEFAULT NULL COMMENT '股东总数' AFTER shareholder_desc;

-- =====================================================
-- 3. stock_analyst_expectation (分析师评级表)
-- AkShare 返回字段：
-- 股票代码，股票简称，报告名称，东财评级，机构，近一月个股研报数，
-- 2025-盈利预测 - 收益，2025-盈利预测 - 市盈率，2026-盈利预测 - 收益，
-- 2026-盈利预测 - 市盈率，2027-盈利预测 - 收益，2027-盈利预测 - 市盈率，
-- 行业，日期，报告 PDF 链接
-- =====================================================
SELECT '=== 调整 stock_analyst_expectation ===' AS status;

-- 添加 AkShare 特有字段
ALTER TABLE stock_analyst_expectation ADD COLUMN IF NOT EXISTS report_name VARCHAR(200) DEFAULT NULL COMMENT '报告名称' AFTER stock_name;
ALTER TABLE stock_shareholder_info ADD COLUMN IF NOT EXISTS df_rating VARCHAR(20) DEFAULT NULL COMMENT '东财评级' AFTER analyst_rating;
ALTER TABLE stock_analyst_expectation ADD COLUMN IF NOT EXISTS research_count INT DEFAULT 0 COMMENT '近一月研报数' AFTER analyst_name;
ALTER TABLE stock_analyst_expectation ADD COLUMN IF NOT EXISTS forecast_eps_2025 DECIMAL(10,4) DEFAULT NULL COMMENT '2025 年 EPS 预测' AFTER research_count;
ALTER TABLE stock_analyst_expectation ADD COLUMN IF NOT EXISTS forecast_pe_2025 DECIMAL(10,2) DEFAULT NULL COMMENT '2025 年 PE 预测' AFTER forecast_eps_2025;
ALTER TABLE stock_analyst_expectation ADD COLUMN IF NOT EXISTS forecast_eps_2026 DECIMAL(10,4) DEFAULT NULL COMMENT '2026 年 EPS 预测' AFTER forecast_pe_2025;
ALTER TABLE stock_analyst_expectation ADD COLUMN IF NOT EXISTS forecast_pe_2026 DECIMAL(10,2) DEFAULT NULL COMMENT '2026 年 PE 预测' AFTER forecast_eps_2026;
ALTER TABLE stock_analyst_expectation ADD COLUMN IF NOT EXISTS forecast_eps_2027 DECIMAL(10,4) DEFAULT NULL COMMENT '2027 年 EPS 预测' AFTER forecast_pe_2026;
ALTER TABLE stock_analyst_expectation ADD COLUMN IF NOT EXISTS forecast_pe_2027 DECIMAL(10,2) DEFAULT NULL COMMENT '2027 年 PE 预测' AFTER forecast_eps_2027;
ALTER TABLE stock_analyst_expectation ADD COLUMN IF NOT EXISTS industry VARCHAR(50) DEFAULT NULL COMMENT '行业' AFTER forecast_pe_2027;
ALTER TABLE stock_analyst_expectation ADD COLUMN IF NOT EXISTS report_link VARCHAR(500) DEFAULT NULL COMMENT '报告 PDF 链接' AFTER industry;

-- =====================================================
-- 4. stock_concept (概念板块表)
-- 需要创建新表或调整
-- =====================================================
SELECT '=== 检查 stock_concept ===' AS status;

-- stock_concept 表结构基本匹配，无需调整

-- =====================================================
-- 验证调整结果
-- =====================================================
SELECT '=== 验证调整结果 ===' AS status;

SELECT 
    table_name,
    COUNT(*) as column_count
FROM information_schema.columns
WHERE table_schema = 'stock' 
  AND table_name IN (
    'stock_capital_flow',
    'stock_shareholder_info',
    'stock_analyst_expectation',
    'stock_concept'
  )
GROUP BY table_name
ORDER BY table_name;

SELECT '=== 调整完成 ===' AS status;

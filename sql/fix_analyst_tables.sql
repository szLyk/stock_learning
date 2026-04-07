-- =====================================================
-- 分析师预期表结构优化
-- 问题：原来用年份做列名（forecast_eps_2025等），每年需要加列
-- 解决：拆分为两个表，盈利预测数据单独存储
-- =====================================================

USE stock;

-- 1. 分析师评级主表（保留原有字段，去掉年份列）
DROP TABLE IF EXISTS stock_analyst_expectation_new;
CREATE TABLE stock_analyst_expectation_new (
    id INT AUTO_INCREMENT PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL COMMENT '股票代码',
    stock_name VARCHAR(50) DEFAULT NULL COMMENT '股票简称',
    publish_date DATE NOT NULL COMMENT '发布日期',
    institution_name VARCHAR(100) NOT NULL COMMENT '机构名称',
    rating_type VARCHAR(10) DEFAULT NULL COMMENT '评级类型：买入/增持/中性/减持/卖出',
    rating_score DECIMAL(5,2) DEFAULT NULL COMMENT '评级打分',
    research_count INT DEFAULT 0 COMMENT '近一月研报数',
    industry VARCHAR(50) DEFAULT NULL COMMENT '行业',
    report_name VARCHAR(500) DEFAULT NULL COMMENT '报告名称',
    report_link VARCHAR(500) DEFAULT NULL COMMENT '报告链接',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_code_date_inst (stock_code, publish_date, institution_name),
    KEY idx_stock_code (stock_code),
    KEY idx_publish_date (publish_date),
    KEY idx_rating (rating_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='分析师评级表';

-- 2. 盈利预测表（年份作为行的值）
DROP TABLE IF EXISTS stock_earnings_forecast;
CREATE TABLE stock_earnings_forecast (
    id INT AUTO_INCREMENT PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL COMMENT '股票代码',
    institution_name VARCHAR(100) NOT NULL COMMENT '机构名称',
    publish_date DATE NOT NULL COMMENT '发布日期',
    forecast_year INT NOT NULL COMMENT '预测年份',
    forecast_eps DECIMAL(10,4) DEFAULT NULL COMMENT '预测EPS',
    forecast_pe DECIMAL(10,2) DEFAULT NULL COMMENT '预测PE',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_code_inst_year (stock_code, institution_name, publish_date, forecast_year),
    KEY idx_stock_code (stock_code),
    KEY idx_forecast_year (forecast_year)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='盈利预测表';

-- 3. 迁移旧数据到新表
INSERT INTO stock_analyst_expectation_new
    (stock_code, stock_name, publish_date, institution_name, rating_type, rating_score,
     research_count, industry, report_name, report_link, create_time, update_time)
SELECT
    stock_code, stock_name, publish_date, institution_name, rating_type, rating_score,
    research_count, industry, report_name, report_link, create_time, update_time
FROM stock_analyst_expectation
ON DUPLICATE KEY UPDATE
    rating_type = VALUES(rating_type),
    rating_score = VALUES(rating_score),
    research_count = VALUES(research_count),
    industry = VALUES(industry),
    report_name = VALUES(report_name),
    report_link = VALUES(report_link);

-- 4. 迁移盈利预测数据（从旧表的年份列转换为新表的行）
INSERT INTO stock_earnings_forecast
    (stock_code, institution_name, publish_date, forecast_year, forecast_eps, forecast_pe)
SELECT
    stock_code, institution_name, publish_date, 2025, forecast_eps_2025, forecast_pe_2025
FROM stock_analyst_expectation
WHERE forecast_eps_2025 IS NOT NULL OR forecast_pe_2025 IS NOT NULL
ON DUPLICATE KEY UPDATE
    forecast_eps = VALUES(forecast_eps),
    forecast_pe = VALUES(forecast_pe);

INSERT INTO stock_earnings_forecast
    (stock_code, institution_name, publish_date, forecast_year, forecast_eps, forecast_pe)
SELECT
    stock_code, institution_name, publish_date, 2026, forecast_eps_2026, forecast_pe_2026
FROM stock_analyst_expectation
WHERE forecast_eps_2026 IS NOT NULL OR forecast_pe_2026 IS NOT NULL
ON DUPLICATE KEY UPDATE
    forecast_eps = VALUES(forecast_eps),
    forecast_pe = VALUES(forecast_pe);

INSERT INTO stock_earnings_forecast
    (stock_code, institution_name, publish_date, forecast_year, forecast_eps, forecast_pe)
SELECT
    stock_code, institution_name, publish_date, 2027, forecast_eps_2027, forecast_pe_2027
FROM stock_analyst_expectation
WHERE forecast_eps_2027 IS NOT NULL OR forecast_pe_2027 IS NOT NULL
ON DUPLICATE KEY UPDATE
    forecast_eps = VALUES(forecast_eps),
    forecast_pe = VALUES(forecast_pe);

-- 5. 重命名表
RENAME TABLE
    stock_analyst_expectation TO stock_analyst_expectation_old,
    stock_analyst_expectation_new TO stock_analyst_expectation;

-- 6. 验证
SELECT 'analyst_expectation' as table_name, COUNT(*) as cnt FROM stock_analyst_expectation
UNION ALL
SELECT 'earnings_forecast', COUNT(*) FROM stock_earnings_forecast;
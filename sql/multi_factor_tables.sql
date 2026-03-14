-- =====================================================
-- 多因子模型扩展表结构
-- 创建时间：2026-03-14
-- =====================================================

USE stock;

-- =====================================================
-- 1. 资金流向表
-- =====================================================
CREATE TABLE IF NOT EXISTS stock_capital_flow (
    id INT AUTO_INCREMENT PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL COMMENT '股票代码',
    stock_date DATE NOT NULL COMMENT '交易日期',
    main_net_in DECIMAL(15,2) DEFAULT 0 COMMENT '主力净流入（万元）',
    sm_net_in DECIMAL(15,2) DEFAULT 0 COMMENT '小单净流入（万元）',
    mm_net_in DECIMAL(15,2) DEFAULT 0 COMMENT '中单净流入（万元）',
    bm_net_in DECIMAL(15,2) DEFAULT 0 COMMENT '大单净流入（万元）',
    north_hold DECIMAL(15,2) DEFAULT NULL COMMENT '北向资金持仓（万股）',
    north_net_in DECIMAL(15,2) DEFAULT 0 COMMENT '北向资金净流入（万股）',
    margin_balance DECIMAL(15,2) DEFAULT NULL COMMENT '融资余额（万元）',
    market_type VARCHAR(10) COMMENT '市场类型',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_code_date (stock_code, stock_date),
    KEY idx_stock_date (stock_code, stock_date),
    KEY idx_main_net (main_net_in),
    KEY idx_north_net (north_net_in)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='股票资金流向表';

-- =====================================================
-- 2. 分析师预期表
-- =====================================================
CREATE TABLE IF NOT EXISTS stock_analyst_expectation (
    id INT AUTO_INCREMENT PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL COMMENT '股票代码',
    publish_date DATE NOT NULL COMMENT '发布日期',
    forecast_type VARCHAR(20) DEFAULT NULL COMMENT '业绩预告类型：预增/预减/略增/略减/续盈/首亏/续亏/扭亏',
    forecast_content TEXT COMMENT '业绩预告内容',
    analyst_rating VARCHAR(10) DEFAULT NULL COMMENT '分析师评级：买入/增持/中性/减持/卖出',
    analyst_count INT DEFAULT 0 COMMENT '分析师人数',
    target_price DECIMAL(10,2) DEFAULT NULL COMMENT '目标价',
    consensus_eps DECIMAL(10,4) DEFAULT NULL COMMENT '一致预期 EPS',
    consensus_pe DECIMAL(10,2) DEFAULT NULL COMMENT '一致预期 PE',
    rating_score DECIMAL(5,2) DEFAULT NULL COMMENT '评级打分（买入=5,增持=4,中性=3,减持=2,卖出=1）',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_code_date (stock_code, publish_date),
    KEY idx_stock_date (stock_code, publish_date),
    KEY idx_rating (analyst_rating),
    KEY idx_rating_score (rating_score)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='分析师预期与评级表';

-- =====================================================
-- 3. 股东筹码表（季度更新）
-- =====================================================
CREATE TABLE IF NOT EXISTS stock_shareholder_info (
    id INT AUTO_INCREMENT PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL COMMENT '股票代码',
    report_date DATE NOT NULL COMMENT '报告日期（季度末）',
    shareholder_count INT DEFAULT NULL COMMENT '股东总人数',
    shareholder_change DECIMAL(10,2) DEFAULT NULL COMMENT '股东人数变化率（%）',
    avg_hold_per_household DECIMAL(15,2) DEFAULT NULL COMMENT '户均持股数',
    institution_hold_ratio DECIMAL(10,2) DEFAULT NULL COMMENT '机构持仓比例（%）',
    fund_hold_ratio DECIMAL(10,2) DEFAULT NULL COMMENT '基金持仓比例（%）',
    executive_hold DECIMAL(15,2) DEFAULT NULL COMMENT '高管持股数（万股）',
    executive_hold_ratio DECIMAL(10,2) DEFAULT NULL COMMENT '高管持股比例（%）',
    top10_hold_ratio DECIMAL(10,2) DEFAULT NULL COMMENT '前 10 大股东持股比例（%）',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_code_date (stock_code, report_date),
    KEY idx_stock_date (stock_code, report_date),
    KEY idx_shareholder_change (shareholder_change)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='股东筹码信息表';

-- =====================================================
-- 4. 概念板块表
-- =====================================================
CREATE TABLE IF NOT EXISTS stock_concept (
    id INT AUTO_INCREMENT PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL COMMENT '股票代码',
    concept_name VARCHAR(50) NOT NULL COMMENT '概念名称',
    concept_type VARCHAR(20) DEFAULT NULL COMMENT '概念类型：行业/主题/风格',
    is_hot TINYINT DEFAULT 0 COMMENT '是否热点概念（1=是，0=否）',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_code_concept (stock_code, concept_name),
    KEY idx_stock (stock_code),
    KEY idx_concept (concept_name),
    KEY idx_hot (is_hot)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='股票概念板块表';

-- =====================================================
-- 5. 多因子打分表（每日更新）
-- =====================================================
CREATE TABLE IF NOT EXISTS stock_factor_score (
    id INT AUTO_INCREMENT PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL COMMENT '股票代码',
    stock_date DATE NOT NULL COMMENT '交易日期',
    
    -- 价值因子
    value_score DECIMAL(10,4) DEFAULT 0 COMMENT '价值因子得分',
    pe_percentile DECIMAL(10,4) DEFAULT NULL COMMENT 'PE 历史分位数（%）',
    pb_percentile DECIMAL(10,4) DEFAULT NULL COMMENT 'PB 历史分位数（%）',
    
    -- 质量因子
    quality_score DECIMAL(10,4) DEFAULT 0 COMMENT '质量因子得分',
    roe_score DECIMAL(10,4) DEFAULT NULL COMMENT 'ROE 得分',
    margin_score DECIMAL(10,4) DEFAULT NULL COMMENT '毛利率得分',
    
    -- 成长因子
    growth_score DECIMAL(10,4) DEFAULT 0 COMMENT '成长因子得分',
    revenue_growth DECIMAL(10,4) DEFAULT NULL COMMENT '营收增速（%）',
    profit_growth DECIMAL(10,4) DEFAULT NULL COMMENT '净利润增速（%）',
    
    -- 动量因子
    momentum_score DECIMAL(10,4) DEFAULT 0 COMMENT '动量因子得分',
    momentum_60d DECIMAL(10,4) DEFAULT NULL COMMENT '60 日动量（%）',
    reversal_5d DECIMAL(10,4) DEFAULT NULL COMMENT '5 日反转（%）',
    
    -- 资金流向因子
    capital_score DECIMAL(10,4) DEFAULT 0 COMMENT '资金流向得分',
    main_net_ratio DECIMAL(10,4) DEFAULT NULL COMMENT '主力净流入/流通市值（%）',
    north_net_ratio DECIMAL(10,4) DEFAULT NULL COMMENT '北向净流入/流通市值（%）',
    
    -- 分析师预期因子
    expectation_score DECIMAL(10,4) DEFAULT 0 COMMENT '分析师预期得分',
    rating_score DECIMAL(10,4) DEFAULT NULL COMMENT '评级打分',
    eps_surprise DECIMAL(10,4) DEFAULT NULL COMMENT 'EPS 超预期（%）',
    
    -- 综合得分
    total_score DECIMAL(10,4) DEFAULT 0 COMMENT '综合得分',
    total_rank INT DEFAULT NULL COMMENT '全市场排名',
    industry_rank INT DEFAULT NULL COMMENT '行业内排名',
    
    -- 因子权重配置
    value_weight DECIMAL(5,4) DEFAULT 0.25 COMMENT '价值因子权重',
    quality_weight DECIMAL(5,4) DEFAULT 0.25 COMMENT '质量因子权重',
    growth_weight DECIMAL(5,4) DEFAULT 0.20 COMMENT '成长因子权重',
    momentum_weight DECIMAL(5,4) DEFAULT 0.15 COMMENT '动量因子权重',
    capital_weight DECIMAL(5,4) DEFAULT 0.10 COMMENT '资金流向权重',
    expectation_weight DECIMAL(5,4) DEFAULT 0.05 COMMENT '分析师预期权重',
    
    market_type VARCHAR(10) COMMENT '市场类型',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_code_date (stock_code, stock_date),
    KEY idx_stock_date (stock_code, stock_date),
    KEY idx_total_score (total_score),
    KEY idx_total_rank (total_rank),
    KEY idx_industry_rank (industry_rank)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='多因子打分表';

-- =====================================================
-- 6. 因子 IC 值记录表（用于回测）
-- =====================================================
CREATE TABLE IF NOT EXISTS stock_factor_ic (
    id INT AUTO_INCREMENT PRIMARY KEY,
    factor_name VARCHAR(50) NOT NULL COMMENT '因子名称',
    calc_date DATE NOT NULL COMMENT '计算日期',
    ic_value DECIMAL(10,6) DEFAULT NULL COMMENT 'IC 值（Rank IC）',
    ic_ir DECIMAL(10,4) DEFAULT NULL COMMENT 'IC IR（IC 均值/标准差）',
    ic_tvalue DECIMAL(10,4) DEFAULT NULL COMMENT 'IC T 值',
    ic_pvalue DECIMAL(10,6) DEFAULT NULL COMMENT 'IC P 值',
    period_1d DECIMAL(10,6) DEFAULT NULL COMMENT '1 日收益 IC',
    period_5d DECIMAL(10,6) DEFAULT NULL COMMENT '5 日收益 IC',
    period_10d DECIMAL(10,6) DEFAULT NULL COMMENT '10 日收益 IC',
    period_20d DECIMAL(10,6) DEFAULT NULL COMMENT '20 日收益 IC',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_factor_date (factor_name, calc_date),
    KEY idx_factor (factor_name),
    KEY idx_ic_value (ic_value)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='因子 IC 值记录表';

-- =====================================================
-- 7. 选股结果表
-- =====================================================
CREATE TABLE IF NOT EXISTS stock_selection_result (
    id INT AUTO_INCREMENT PRIMARY KEY,
    strategy_name VARCHAR(50) NOT NULL COMMENT '策略名称',
    select_date DATE NOT NULL COMMENT '选股日期',
    stock_code VARCHAR(10) NOT NULL COMMENT '股票代码',
    stock_name VARCHAR(50) COMMENT '股票名称',
    total_score DECIMAL(10,4) COMMENT '综合得分',
    total_rank INT COMMENT '排名',
    industry VARCHAR(50) COMMENT '所属行业',
    concept VARCHAR(100) COMMENT '所属概念',
    close_price DECIMAL(10,2) COMMENT '选股日收盘价',
    weight DECIMAL(10,4) DEFAULT NULL COMMENT '建议权重（%）',
    hold_period INT DEFAULT 5 COMMENT '建议持有期（天）',
    stop_loss DECIMAL(10,2) DEFAULT NULL COMMENT '止损价',
    stop_profit DECIMAL(10,2) DEFAULT NULL COMMENT '止盈价',
    status VARCHAR(20) DEFAULT 'pending' COMMENT '状态：pending/holding/sold/stopped',
    sell_date DATE DEFAULT NULL COMMENT '卖出日期',
    sell_price DECIMAL(10,2) DEFAULT NULL COMMENT '卖出价格',
    return_rate DECIMAL(10,4) DEFAULT NULL COMMENT '收益率（%）',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_strategy_date_stock (strategy_name, select_date, stock_code),
    KEY idx_strategy_date (strategy_name, select_date),
    KEY idx_select_date (select_date),
    KEY idx_status (status),
    KEY idx_return (return_rate)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='选股结果表';

-- =====================================================
-- 初始化概念数据（示例）
-- =====================================================
INSERT INTO stock_concept (stock_code, concept_name, concept_type, is_hot) VALUES
('000001', '银行', '行业', 0),
('000001', '金融', '行业', 0),
('000001', '粤港澳大湾区', '主题', 1),
('000002', '房地产', '行业', 0),
('000002', '央企改革', '主题', 1),
('002080', '建材', '行业', 0),
('002080', '玻璃纤维', '主题', 0),
('002080', '风电概念', '主题', 1),
('002080', '新能源汽车', '主题', 1),
('600000', '银行', '行业', 0),
('600000', '上海自贸区', '主题', 1),
('600036', '银行', '行业', 0),
('600036', '金融科技', '主题', 1),
('600519', '白酒', '行业', 0),
('600519', '消费', '行业', 0),
('600519', '贵州国资', '主题', 0),
('300750', '新能源汽车', '主题', 1),
('300750', '锂电池', '主题', 1),
('300750', '创业板指', '风格', 0)
ON DUPLICATE KEY UPDATE update_time=CURRENT_TIMESTAMP;

-- =====================================================
-- 创建视图：多因子选股视图（方便查询）
-- =====================================================
CREATE OR REPLACE VIEW v_stock_factor_ranking AS
SELECT 
    s.stock_code,
    s.stock_name,
    f.stock_date,
    f.total_score,
    f.total_rank,
    f.industry_rank,
    i.industry,
    f.value_score,
    f.quality_score,
    f.growth_score,
    f.momentum_score,
    f.capital_score,
    f.expectation_score,
    h.close_price,
    h.rolling_p as pe_ttm,
    h.pb_ratio,
    p.roe_avg,
    p.eps_ttm
FROM stock_factor_score f
JOIN stock_basic s ON f.stock_code = s.stock_code
LEFT JOIN stock_industry i ON f.stock_code = i.stock_code
LEFT JOIN stock_history_date_price h ON f.stock_code = h.stock_code AND f.stock_date = h.stock_date
LEFT JOIN stock_profit_data p ON f.stock_code = p.stock_code
WHERE f.stock_date = (SELECT MAX(stock_date) FROM stock_factor_score)
  AND s.stock_status = 1
ORDER BY f.total_score DESC;

-- =====================================================
-- 完成提示
-- =====================================================
SELECT '多因子模型表结构创建完成！' as message;

-- =====================================================
-- 龙虎榜、基金持仓、融资融券数据表
-- 数据源: AKShare
-- 创建时间: 2026-04-02
-- =====================================================

SET NAMES utf8mb4;
USE stock;

-- =====================================================
-- 1. 龙虎榜明细表
-- =====================================================
DROP TABLE IF EXISTS `stock_lhb_detail`;

CREATE TABLE `stock_lhb_detail` (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    `stock_code` VARCHAR(10) NOT NULL COMMENT '股票代码',
    `stock_name` VARCHAR(50) DEFAULT NULL COMMENT '股票名称',
    `trade_date` DATE NOT NULL COMMENT '上榜日期',
    `close_price` DECIMAL(10, 2) DEFAULT NULL COMMENT '收盘价',
    `change_pct` DECIMAL(10, 4) DEFAULT NULL COMMENT '涨跌幅(%)',
    
    -- 龙虎榜金额
    `net_buy_amount` DECIMAL(20, 2) DEFAULT NULL COMMENT '龙虎榜净买额',
    `buy_amount` DECIMAL(20, 2) DEFAULT NULL COMMENT '龙虎榜买入额',
    `sell_amount` DECIMAL(20, 2) DEFAULT NULL COMMENT '龙虎榜卖出额',
    `turnover_amount` DECIMAL(20, 2) DEFAULT NULL COMMENT '龙虎榜成交额',
    `market_amount` DECIMAL(20, 2) DEFAULT NULL COMMENT '市场总成交额',
    
    -- 占比
    `net_buy_ratio` DECIMAL(10, 4) DEFAULT NULL COMMENT '净买额占总成交比(%)',
    `turnover_ratio` DECIMAL(10, 4) DEFAULT NULL COMMENT '成交额占总成交比(%)',
    `turnover_rate` DECIMAL(10, 4) DEFAULT NULL COMMENT '换手率(%)',
    
    -- 其他
    `float_mv` DECIMAL(20, 2) DEFAULT NULL COMMENT '流通市值',
    `reason` VARCHAR(500) DEFAULT NULL COMMENT '上榜原因',
    `interpretation` VARCHAR(200) DEFAULT NULL COMMENT '解读',
    
    -- 上榜后表现
    `after_1d` DECIMAL(10, 4) DEFAULT NULL COMMENT '上榜后1日涨跌幅(%)',
    `after_2d` DECIMAL(10, 4) DEFAULT NULL COMMENT '上榜后2日涨跌幅(%)',
    `after_5d` DECIMAL(10, 4) DEFAULT NULL COMMENT '上榜后5日涨跌幅(%)',
    `after_10d` DECIMAL(10, 4) DEFAULT NULL COMMENT '上榜后10日涨跌幅(%)',
    
    `data_source` VARCHAR(20) DEFAULT 'akshare' COMMENT '数据来源',
    `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY `uk_stock_date` (`stock_code`, `trade_date`),
    KEY `idx_trade_date` (`trade_date`),
    KEY `idx_stock_code` (`stock_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='龙虎榜明细表';

-- =====================================================
-- 2. 机构龙虎榜统计表
-- =====================================================
DROP TABLE IF EXISTS `stock_lhb_institution`;

CREATE TABLE `stock_lhb_institution` (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    `stock_code` VARCHAR(10) NOT NULL COMMENT '股票代码',
    `stock_name` VARCHAR(50) DEFAULT NULL COMMENT '股票名称',
    `close_price` DECIMAL(10, 2) DEFAULT NULL COMMENT '收盘价',
    `change_pct` DECIMAL(10, 4) DEFAULT NULL COMMENT '涨跌幅(%)',
    
    -- 龙虎榜数据
    `total_amount` DECIMAL(20, 2) DEFAULT NULL COMMENT '龙虎榜成交金额',
    `appear_count` INT DEFAULT NULL COMMENT '上榜次数',
    
    -- 机构数据
    `inst_buy_amount` DECIMAL(20, 2) DEFAULT NULL COMMENT '机构买入额',
    `inst_buy_count` INT DEFAULT NULL COMMENT '机构买入次数',
    `inst_sell_amount` DECIMAL(20, 2) DEFAULT NULL COMMENT '机构卖出额',
    `inst_sell_count` INT DEFAULT NULL COMMENT '机构卖出次数',
    `inst_net_buy` DECIMAL(20, 2) DEFAULT NULL COMMENT '机构净买额',
    
    -- 区间涨跌幅
    `change_1m` DECIMAL(10, 4) DEFAULT NULL COMMENT '近1个月涨跌幅(%)',
    `change_3m` DECIMAL(10, 4) DEFAULT NULL COMMENT '近3个月涨跌幅(%)',
    `change_6m` DECIMAL(10, 4) DEFAULT NULL COMMENT '近6个月涨跌幅(%)',
    `change_1y` DECIMAL(10, 4) DEFAULT NULL COMMENT '近1年涨跌幅(%)',
    
    `stat_date` DATE DEFAULT NULL COMMENT '统计日期',
    `data_source` VARCHAR(20) DEFAULT 'akshare' COMMENT '数据来源',
    `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY `uk_stock_date` (`stock_code`, `stat_date`),
    KEY `idx_stat_date` (`stat_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='机构龙虎榜统计表';

-- =====================================================
-- 3. 基金持仓表
-- =====================================================
DROP TABLE IF EXISTS `stock_fund_hold`;

CREATE TABLE `stock_fund_hold` (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    `stock_code` VARCHAR(10) NOT NULL COMMENT '股票代码',
    `stock_name` VARCHAR(50) DEFAULT NULL COMMENT '股票名称',
    `report_date` VARCHAR(10) NOT NULL COMMENT '报告期(如20210331)',
    
    -- 持仓数据
    `fund_count` INT DEFAULT NULL COMMENT '持有基金家数',
    `hold_shares` DECIMAL(20, 2) DEFAULT NULL COMMENT '持股总数',
    `hold_value` DECIMAL(20, 2) DEFAULT NULL COMMENT '持股市值',
    
    -- 变动数据
    `change_type` VARCHAR(10) DEFAULT NULL COMMENT '持股变化(增仓/减仓/新进/不变)',
    `change_shares` DECIMAL(20, 2) DEFAULT NULL COMMENT '持股变动数值',
    `change_ratio` DECIMAL(10, 4) DEFAULT NULL COMMENT '持股变动比例(%)',
    
    `data_source` VARCHAR(20) DEFAULT 'akshare' COMMENT '数据来源',
    `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY `uk_stock_report` (`stock_code`, `report_date`),
    KEY `idx_report_date` (`report_date`),
    KEY `idx_fund_count` (`fund_count`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='基金持仓表';

-- =====================================================
-- 4. 个股基金持仓明细表
-- =====================================================
DROP TABLE IF EXISTS `stock_fund_hold_detail`;

CREATE TABLE `stock_fund_hold_detail` (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    `stock_code` VARCHAR(10) NOT NULL COMMENT '股票代码',
    `stock_name` VARCHAR(50) DEFAULT NULL COMMENT '股票名称',
    
    -- 持仓数据
    `hold_shares` DECIMAL(20, 2) DEFAULT NULL COMMENT '持股数',
    `hold_value` DECIMAL(20, 2) DEFAULT NULL COMMENT '持股市值',
    `total_ratio` DECIMAL(10, 4) DEFAULT NULL COMMENT '占总股本比例(%)',
    `float_ratio` DECIMAL(10, 4) DEFAULT NULL COMMENT '占流通股本比例(%)',
    
    `stat_date` DATE DEFAULT NULL COMMENT '统计日期',
    `data_source` VARCHAR(20) DEFAULT 'akshare' COMMENT '数据来源',
    `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY `uk_stock_date` (`stock_code`, `stat_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='个股基金持仓明细表';

-- =====================================================
-- 5. 融资融券明细表
-- =====================================================
DROP TABLE IF EXISTS `stock_margin_detail`;

CREATE TABLE `stock_margin_detail` (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    `stock_code` VARCHAR(10) NOT NULL COMMENT '证券代码',
    `stock_name` VARCHAR(50) DEFAULT NULL COMMENT '证券简称',
    `trade_date` DATE NOT NULL COMMENT '交易日期',
    
    -- 融资数据
    `margin_balance` DECIMAL(20, 2) DEFAULT NULL COMMENT '融资余额',
    `margin_buy` DECIMAL(20, 2) DEFAULT NULL COMMENT '融资买入额',
    `margin_repay` DECIMAL(20, 2) DEFAULT NULL COMMENT '融资偿还额',
    
    -- 融券数据
    `short_balance` DECIMAL(20, 2) DEFAULT NULL COMMENT '融券余量',
    `short_sell` DECIMAL(20, 2) DEFAULT NULL COMMENT '融券卖出量',
    `short_repay` DECIMAL(20, 2) DEFAULT NULL COMMENT '融券偿还量',
    
    `data_source` VARCHAR(20) DEFAULT 'akshare' COMMENT '数据来源',
    `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY `uk_stock_date` (`stock_code`, `trade_date`),
    KEY `idx_trade_date` (`trade_date`),
    KEY `idx_stock_code` (`stock_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='融资融券明细表';

-- =====================================================
-- 完成提示
-- =====================================================
SELECT '龙虎榜、基金持仓、融资融券表创建完成！' AS message;

SHOW TABLES LIKE 'stock_lhb%';
SHOW TABLES LIKE 'stock_fund%';
SHOW TABLES LIKE 'stock_margin%';
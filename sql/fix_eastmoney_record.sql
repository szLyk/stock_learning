-- =====================================================
-- 修复东方财富数据采集记录表乱码
-- 创建时间：2026-03-15 00:10
-- =====================================================

SET NAMES utf8mb4;

USE stock;

-- 删除旧表
DROP TABLE IF EXISTS update_eastmoney_record;

-- 重新创建表（确保字符集正确）
CREATE TABLE update_eastmoney_record (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    stock_code VARCHAR(10) NOT NULL COMMENT '股票代码',
    stock_name VARCHAR(50) DEFAULT NULL COMMENT '股票名称',
    market_type VARCHAR(10) DEFAULT NULL COMMENT '市场类型',
    update_moneyflow DATE DEFAULT NULL COMMENT '资金流向最后更新日期',
    update_north DATE DEFAULT NULL COMMENT '北向资金最后更新日期',
    update_shareholder DATE DEFAULT NULL COMMENT '股东人数最后更新日期',
    update_concept DATE DEFAULT NULL COMMENT '概念板块最后更新日期',
    update_analyst DATE DEFAULT NULL COMMENT '分析师评级最后更新日期',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_stock (stock_code),
    KEY idx_update_moneyflow (update_moneyflow),
    KEY idx_update_north (update_north)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='东方财富数据采集记录表';

-- 验证
SHOW CREATE TABLE update_eastmoney_record\G

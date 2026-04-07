-- 修复 shareholder_change_rate 字段范围问题
-- 将 DECIMAL(10,2) 改为 DECIMAL(15,4)，支持更大数值

USE stock;

-- 修改 shareholder_change_rate 字段（如果存在）
ALTER TABLE stock_shareholder_info
MODIFY COLUMN shareholder_change_rate DECIMAL(15,4) DEFAULT NULL COMMENT '股东人数变化率（%）';

-- 如果字段不存在，添加它
-- ALTER TABLE stock_shareholder_info
-- ADD COLUMN shareholder_change_rate DECIMAL(15,4) DEFAULT NULL COMMENT '股东人数变化率（%）' AFTER shareholder_change;

-- 同时修改 shareholder_change 字段
ALTER TABLE stock_shareholder_info
MODIFY COLUMN shareholder_change DECIMAL(15,4) DEFAULT NULL COMMENT '股东人数变化（%）';

-- 确认修改
SELECT COLUMN_NAME, COLUMN_TYPE FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = 'stock_shareholder_info'
AND COLUMN_NAME IN ('shareholder_change', 'shareholder_change_rate');
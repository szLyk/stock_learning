#!/bin/bash
# 添加缺失的字段

MYSQL_CMD="mysql -h 192.168.1.109 -P 3306 -u root -p123456 stock"

echo "======================================================"
echo "添加缺失的字段"
echo "======================================================"

# stock_balance_data
echo ""
echo "=== stock_balance_data ==="
$MYSQL_CMD -e "ALTER TABLE stock_balance_data ADD COLUMN current_ratio DECIMAL(10,4) DEFAULT NULL COMMENT '流动比率' AFTER undistributed_profit;" 2>&1 | grep -v "Duplicate"
$MYSQL_CMD -e "ALTER TABLE stock_balance_data ADD COLUMN quick_ratio DECIMAL(10,4) DEFAULT NULL COMMENT '速动比率' AFTER current_ratio;" 2>&1 | grep -v "Duplicate"
$MYSQL_CMD -e "ALTER TABLE stock_balance_data ADD COLUMN cash_ratio DECIMAL(10,4) DEFAULT NULL COMMENT '现金比率' AFTER quick_ratio;" 2>&1 | grep -v "Duplicate"
$MYSQL_CMD -e "ALTER TABLE stock_balance_data ADD COLUMN yoy_liability DECIMAL(10,4) DEFAULT NULL COMMENT '负债同比增长率' AFTER cash_ratio;" 2>&1 | grep -v "Duplicate"
$MYSQL_CMD -e "ALTER TABLE stock_balance_data ADD COLUMN liability_to_asset DECIMAL(10,4) DEFAULT NULL COMMENT '资产负债率' AFTER yoy_liability;" 2>&1 | grep -v "Duplicate"
$MYSQL_CMD -e "ALTER TABLE stock_balance_data ADD COLUMN asset_to_equity DECIMAL(10,4) DEFAULT NULL COMMENT '资产/权益' AFTER liability_to_asset;" 2>&1 | grep -v "Duplicate"

# stock_growth_data
echo ""
echo "=== stock_growth_data ==="
$MYSQL_CMD -e "ALTER TABLE stock_growth_data ADD COLUMN yoy_equity DECIMAL(10,4) DEFAULT NULL COMMENT '净资产同比增长率' AFTER total_equity_yoy;" 2>&1 | grep -v "Duplicate"
$MYSQL_CMD -e "ALTER TABLE stock_growth_data ADD COLUMN yoy_asset DECIMAL(10,4) DEFAULT NULL COMMENT '总资产同比增长率' AFTER yoy_equity;" 2>&1 | grep -v "Duplicate"
$MYSQL_CMD -e "ALTER TABLE stock_growth_data ADD COLUMN yoy_ni DECIMAL(10,4) DEFAULT NULL COMMENT '净利润同比增长率' AFTER yoy_asset;" 2>&1 | grep -v "Duplicate"
$MYSQL_CMD -e "ALTER TABLE stock_growth_data ADD COLUMN yoy_eps_basic DECIMAL(10,4) DEFAULT NULL COMMENT '基本 EPS 同比增长率' AFTER yoy_ni;" 2>&1 | grep -v "Duplicate"
$MYSQL_CMD -e "ALTER TABLE stock_growth_data ADD COLUMN yoy_pni DECIMAL(10,4) DEFAULT NULL COMMENT '归属母公司净利润同比增长率' AFTER yoy_eps_basic;" 2>&1 | grep -v "Duplicate"

# stock_operation_data
echo ""
echo "=== stock_operation_data ==="
$MYSQL_CMD -e "ALTER TABLE stock_operation_data ADD COLUMN nr_turn_ratio DECIMAL(10,4) DEFAULT NULL COMMENT '营业收入周转率' AFTER total_assets_turnover;" 2>&1 | grep -v "Duplicate"
$MYSQL_CMD -e "ALTER TABLE stock_operation_data ADD COLUMN nr_turn_days DECIMAL(10,4) DEFAULT NULL COMMENT '营业收入周转天数' AFTER nr_turn_ratio;" 2>&1 | grep -v "Duplicate"
$MYSQL_CMD -e "ALTER TABLE stock_operation_data ADD COLUMN inv_turn_ratio DECIMAL(10,4) DEFAULT NULL COMMENT '存货周转率' AFTER nr_turn_days;" 2>&1 | grep -v "Duplicate"
$MYSQL_CMD -e "ALTER TABLE stock_operation_data ADD COLUMN inv_turn_days DECIMAL(10,4) DEFAULT NULL COMMENT '存货周转天数' AFTER inv_turn_ratio;" 2>&1 | grep -v "Duplicate"
$MYSQL_CMD -e "ALTER TABLE stock_operation_data ADD COLUMN ca_turn_ratio DECIMAL(10,4) DEFAULT NULL COMMENT '流动资产周转率' AFTER inv_turn_days;" 2>&1 | grep -v "Duplicate"
$MYSQL_CMD -e "ALTER TABLE stock_operation_data ADD COLUMN asset_turn_ratio DECIMAL(10,4) DEFAULT NULL COMMENT '总资产周转率' AFTER ca_turn_ratio;" 2>&1 | grep -v "Duplicate"

# stock_dupont_data
echo ""
echo "=== stock_dupont_data ==="
$MYSQL_CMD -e "ALTER TABLE stock_dupont_data ADD COLUMN dupont_roe DECIMAL(10,4) DEFAULT NULL COMMENT 'ROE(杜邦分析)' AFTER equity_multiplier;" 2>&1 | grep -v "Duplicate"
$MYSQL_CMD -e "ALTER TABLE stock_dupont_data ADD COLUMN dupont_asset_sto_equity DECIMAL(10,4) DEFAULT NULL COMMENT '资产/权益' AFTER dupont_roe;" 2>&1 | grep -v "Duplicate"
$MYSQL_CMD -e "ALTER TABLE stock_dupont_data ADD COLUMN dupont_asset_turn DECIMAL(10,4) DEFAULT NULL COMMENT '资产周转率' AFTER dupont_asset_sto_equity;" 2>&1 | grep -v "Duplicate"
$MYSQL_CMD -e "ALTER TABLE stock_dupont_data ADD COLUMN dupont_pnitoni DECIMAL(10,4) DEFAULT NULL COMMENT '净利润/总收入' AFTER dupont_asset_turn;" 2>&1 | grep -v "Duplicate"
$MYSQL_CMD -e "ALTER TABLE stock_dupont_data ADD COLUMN dupont_nitogr DECIMAL(10,4) DEFAULT NULL COMMENT '净利润/营业收入' AFTER dupont_pnitoni;" 2>&1 | grep -v "Duplicate"
$MYSQL_CMD -e "ALTER TABLE stock_dupont_data ADD COLUMN dupont_tax_burden DECIMAL(10,4) DEFAULT NULL COMMENT '税负比率' AFTER dupont_nitogr;" 2>&1 | grep -v "Duplicate"
$MYSQL_CMD -e "ALTER TABLE stock_dupont_data ADD COLUMN dupont_int_burden DECIMAL(10,4) DEFAULT NULL COMMENT '利息负担比率' AFTER dupont_tax_burden;" 2>&1 | grep -v "Duplicate"
$MYSQL_CMD -e "ALTER TABLE stock_dupont_data ADD COLUMN dupont_ebit_to_gr DECIMAL(10,4) DEFAULT NULL COMMENT 'EBIT/营业收入' AFTER dupont_int_burden;" 2>&1 | grep -v "Duplicate"

# stock_cash_flow_data (创建表)
echo ""
echo "=== stock_cash_flow_data ==="
$MYSQL_CMD -e "DROP TABLE IF EXISTS stock_cash_flow_data;"
$MYSQL_CMD -e "
CREATE TABLE stock_cash_flow_data (
  id INT AUTO_INCREMENT PRIMARY KEY,
  stock_code VARCHAR(10) NOT NULL,
  publish_date DATE DEFAULT NULL,
  statistic_date DATE DEFAULT NULL,
  season INT DEFAULT NULL,
  cfo_to_or DECIMAL(10,4) DEFAULT NULL,
  cfo_to_np DECIMAL(10,4) DEFAULT NULL,
  cfo_to_gr DECIMAL(10,4) DEFAULT NULL,
  ca_to_asset DECIMAL(10,4) DEFAULT NULL,
  nca_to_asset DECIMAL(10,4) DEFAULT NULL,
  tangible_asset_to_asset DECIMAL(10,4) DEFAULT NULL,
  ebit_to_interest DECIMAL(10,4) DEFAULT NULL,
  create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
  update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_stock_date (stock_code, statistic_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;"

# 验证
echo ""
echo "=== 验证关键字段 ==="
$MYSQL_CMD -e "
SELECT table_name, column_name 
FROM information_schema.columns 
WHERE table_schema = 'stock' 
  AND table_name IN ('stock_balance_data', 'stock_growth_data', 'stock_operation_data', 'stock_dupont_data')
  AND column_name IN ('current_ratio', 'yoy_equity', 'nr_turn_ratio', 'dupont_roe')
ORDER BY table_name;
"

echo ""
echo "完成！"

#!/bin/bash
# =====================================================
# Baostock 财务数据修复 - 快速执行脚本
# =====================================================

set -e

MYSQL_HOST="192.168.1.109"
MYSQL_PORT="3306"
MYSQL_USER="root"
MYSQL_DB="stock"
WORKSPACE="/home/fan/.openclaw/workspace/stock_learning"

echo "======================================================"
echo "Baostock 财务数据修复"
echo "======================================================"
echo ""

# 步骤 1：同步数据库表结构
echo "[1/3] 同步数据库表结构..."
mysql -h $MYSQL_HOST -P $MYSQL_PORT -u $MYSQL_USER -p $MYSQL_DB < $WORKSPACE/sql/sync_baostock_tables.sql
echo "✅ 表结构同步完成"
echo ""

# 步骤 2：验证关键字段
echo "[2/3] 验证关键字段..."
mysql -h $MYSQL_HOST -P $MYSQL_PORT -u $MYSQL_USER -p $MYSQL_DB -e "
SELECT 
    table_name,
    column_name,
    data_type
FROM information_schema.columns 
WHERE table_schema = '$MYSQL_DB' 
  AND table_name IN ('stock_balance_data', 'stock_growth_data', 'stock_operation_data', 'stock_dupont_data')
  AND column_name IN ('current_ratio', 'yoy_equity', 'nr_turn_ratio', 'dupont_roe')
ORDER BY table_name;
"
echo ""

# 步骤 3：运行接口测试（可选）
echo "[3/3] 运行接口测试..."
read -p "是否运行 Baostock 接口测试？(y/n): " confirm
if [ "$confirm" = "y" ]; then
    cd $WORKSPACE
    python tests/test_baostock_interfaces.py
else
    echo "⚠️  跳过接口测试"
fi
echo ""

echo "======================================================"
echo "修复完成！"
echo "======================================================"
echo ""
echo "下一步："
echo "1. 检查上述输出，确认所有字段已添加"
echo "2. 运行数据采集：cd $WORKSPACE && python src/utils/baostock_extension.py"
echo "3. 查看日志：tail -f $WORKSPACE/logs/baostock_extension.log"
echo ""

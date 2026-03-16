#!/bin/bash
# =====================================================
# 财务数据采集问题修复脚本
# 功能：
# 1. 更新数据库表结构
# 2. 验证表结构
# 3. 清理 Redis 缓存
# 4. 运行测试
# =====================================================

set -e

# 配置
MYSQL_HOST="192.168.1.109"
MYSQL_PORT="3306"
MYSQL_USER="root"
MYSQL_DB="stock"
REDIS_KEY="baostock:extension"
WORKSPACE="/home/fan/.openclaw/workspace/stock_learning"

echo "======================================================"
echo "财务数据采集问题修复脚本"
echo "======================================================"
echo ""

# 步骤 1：更新数据库表结构
echo "[1/5] 更新数据库表结构..."
echo "执行 SQL: update_financial_tables.sql"
mysql -h $MYSQL_HOST -P $MYSQL_PORT -u $MYSQL_USER -p $MYSQL_DB < $WORKSPACE/sql/update_financial_tables.sql
echo "✅ 表结构更新完成"
echo ""

# 步骤 2：验证表结构
echo "[2/5] 验证表结构..."
mysql -h $MYSQL_HOST -P $MYSQL_PORT -u $MYSQL_USER -p $MYSQL_DB < $WORKSPACE/sql/verify_financial_tables.sql
echo ""

# 步骤 3：清理 Redis 缓存（可选）
echo "[3/5] 清理 Redis 缓存..."
read -p "是否清理 Redis 中的待处理股票缓存？(y/n): " confirm
if [ "$confirm" = "y" ]; then
    DATE=$(date +%Y-%m-%d)
    redis-cli DEL "${REDIS_KEY}:stock_data:${DATE}:unprocessed"
    echo "✅ Redis 缓存已清理"
else
    echo "⚠️  跳过 Redis 缓存清理"
fi
echo ""

# 步骤 4：运行数据清洗测试
echo "[4/5] 运行数据清洗测试..."
cd $WORKSPACE
python tests/test_data_cleaning.py --clean
echo ""

# 步骤 5：运行单只股票测试（可选）
echo "[5/5] 运行单只股票测试..."
read -p "是否运行单只股票采集测试？(y/n): " confirm
if [ "$confirm" = "y" ]; then
    read -p "输入测试股票代码 (默认 sh.600000): " stock_code
    stock_code=${stock_code:-sh.600000}
    python tests/test_data_cleaning.py --stock $stock_code
else
    echo "⚠️  跳过单只股票测试"
fi
echo ""

echo "======================================================"
echo "修复完成！"
echo "======================================================"
echo ""
echo "后续步骤："
echo "1. 检查测试输出，确认所有测试通过"
echo "2. 运行完整数据采集：python src/utils/baostock_extension.py"
echo "3. 查看日志确认无错误：tail -f logs/baostock_extension.log"
echo ""

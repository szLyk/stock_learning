#!/bin/bash
#
# XXL-JOB 执行器部署脚本
#

set -e

echo "========================================"
echo "XXL-JOB 股票数据采集执行器 - 部署脚本"
echo "========================================"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 路径配置
WORKSPACE="/home/fan/.openclaw/workspace/stock_learning"
XXLJOB_DIR="${WORKSPACE}/xxljob"
LOG_DIR="${WORKSPACE}/logs/xxljob"
SERVICE_FILE="/etc/systemd/system/stock-xxljob-executor.service"

echo -e "${YELLOW}[1/6] 创建日志目录...${NC}"
mkdir -p ${LOG_DIR}
echo -e "${GREEN}✓ 日志目录已创建：${LOG_DIR}${NC}"

echo -e "${YELLOW}[2/6] 安装 Python 依赖...${NC}"
cd ${XXLJOB_DIR}
pip3 install -r requirements.txt
echo -e "${GREEN}✓ 依赖安装完成${NC}"

echo -e "${YELLOW}[3/6] 配置环境变量...${NC}"
cat > ${XXLJOB_DIR}/.env << EOF
# XXL-JOB 调度中心地址
XXL_JOB_ADMIN_ADDRESS=http://localhost:8080/xxl-job-admin

# 执行器配置
EXECUTOR_PORT=9999
EXECUTOR_LOG_PATH=${LOG_DIR}

# 数据库配置
DB_HOST=192.168.1.109
DB_PORT=3306
DB_USER=open_claw
DB_PASSWORD=xK7#pL9!mN2\$vQ5@
DB_NAME=stock

# 告警配置
ALERT_ENABLED=true
ALERT_EMAIL=admin@example.com

# 运行环境
ENVIRONMENT=production
EOF
echo -e "${GREEN}✓ 环境变量已配置：${XXLJOB_DIR}/.env${NC}"

echo -e "${YELLOW}[4/6] 安装系统服务...${NC}"
cp ${XXLJOB_DIR}/stock-xxljob-executor.service ${SERVICE_FILE}
systemctl daemon-reload
echo -e "${GREEN}✓ 系统服务已安装${NC}"

echo -e "${YELLOW}[5/6] 启动服务...${NC}"
systemctl start stock-xxljob-executor
systemctl enable stock-xxljob-executor
echo -e "${GREEN}✓ 服务已启动并设置开机自启${NC}"

echo -e "${YELLOW}[6/6] 检查服务状态...${NC}"
sleep 2
systemctl status stock-xxljob-executor --no-pager

echo ""
echo "========================================"
echo -e "${GREEN}✓ 部署完成！${NC}"
echo "========================================"
echo ""
echo "服务管理命令："
echo "  启动服务：sudo systemctl start stock-xxljob-executor"
echo "  停止服务：sudo systemctl stop stock-xxljob-executor"
echo "  重启服务：sudo systemctl restart stock-xxljob-executor"
echo "  查看状态：sudo systemctl status stock-xxljob-executor"
echo "  查看日志：sudo journalctl -u stock-xxljob-executor -f"
echo ""
echo "下一步："
echo "  1. 启动 XXL-JOB 调度中心"
echo "  2. 登录 XXL-JOB 管理后台 (http://localhost:8080/xxl-job-admin)"
echo "  3. 配置执行器：stock-data-executor"
echo "  4. 创建定时任务（参考 README.md）"
echo ""

#!/bin/bash
#
# XXL-JOB 执行器启动脚本（开机自启）
#

set -e

# 路径配置
WORKSPACE="/home/fan/.openclaw/workspace/stock_learning"
XXLJOB_DIR="${WORKSPACE}/xxljob"
LOG_DIR="${WORKSPACE}/logs/xxljob"
PID_FILE="${XXLJOB_DIR}/executor.pid"

# 创建日志目录
mkdir -p ${LOG_DIR}

# 进入工作目录
cd ${XXLJOB_DIR}

# 加载环境变量
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# 检查是否已在运行
if [ -f ${PID_FILE} ]; then
    OLD_PID=$(cat ${PID_FILE})
    if ps -p ${OLD_PID} > /dev/null 2>&1; then
        echo "XXL-JOB 执行器已在运行 (PID: ${OLD_PID})"
        exit 0
    else
        echo "清理旧的 PID 文件"
        rm -f ${PID_FILE}
    fi
fi

# 启动执行器
echo "启动 XXL-JOB 执行器..."
nohup python3 ${XXLJOB_DIR}/executor_server.py > ${LOG_DIR}/executor.log 2>&1 &

# 保存 PID
echo $! > ${PID_FILE}

echo "XXL-JOB 执行器已启动 (PID: $(cat ${PID_FILE}))"
echo "日志文件：${LOG_DIR}/executor.log"

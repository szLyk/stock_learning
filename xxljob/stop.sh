#!/bin/bash
#
# XXL-JOB 执行器停止脚本
#

PID_FILE="/home/fan/.openclaw/workspace/stock_learning/xxljob/executor.pid"

if [ -f ${PID_FILE} ]; then
    PID=$(cat ${PID_FILE})
    if ps -p ${PID} > /dev/null 2>&1; then
        echo "停止 XXL-JOB 执行器 (PID: ${PID})..."
        kill ${PID}
        rm -f ${PID_FILE}
        echo "已停止"
    else
        echo "进程不存在，清理 PID 文件"
        rm -f ${PID_FILE}
    fi
else
    echo "PID 文件不存在，尝试查找进程..."
    PID=$(pgrep -f "executor_server.py")
    if [ -n "${PID}" ]; then
        echo "找到进程 (PID: ${PID})，停止中..."
        kill ${PID}
        echo "已停止"
    else
        echo "未找到运行中的 XXL-JOB 执行器"
    fi
fi

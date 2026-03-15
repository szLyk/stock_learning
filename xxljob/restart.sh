#!/bin/bash
#
# XXL-JOB 执行器重启脚本
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "重启 XXL-JOB 执行器..."
${SCRIPT_DIR}/stop.sh
sleep 2
${SCRIPT_DIR}/start.sh

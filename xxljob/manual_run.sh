#!/bin/bash
# XXL-JOB 任务手动执行脚本

cd /home/fan/.openclaw/workspace/stock_learning

echo "=========================================="
echo "XXL-JOB 任务手动执行"
echo "=========================================="
echo ""
echo "用法："
echo "  ./manual_run.sh [任务类型] [数据类型]"
echo ""
echo "任务类型："
echo "  akshare    - AKShare 数据采集"
echo "  financial  - 财务数据采集"
echo "  daily      - 日线数据采集"
echo ""
echo "数据类型："
echo "  AKShare: moneyflow, shareholder, concept, analyst"
echo "  财务：profit, balance, cashflow, growth, operation, dupont, forecast, dividend"
echo ""
echo "示例："
echo "  ./manual_run.sh akshare analyst"
echo "  ./manual_run.sh akshare moneyflow"
echo "  ./manual_run.sh financial profit"
echo ""
echo "=========================================="
echo ""

if [ -z "$1" ]; then
    echo "❌ 请指定任务类型"
    exit 1
fi

TASK_TYPE=$1
DATA_TYPE=${2:-analyst}

case $TASK_TYPE in
    akshare)
        echo "▶️  执行 AKShare 数据采集：$DATA_TYPE"
        python3 xxljob/executor.py run_akshare_collection --data_type=$DATA_TYPE
        ;;
    financial)
        echo "▶️  执行财务数据采集：$DATA_TYPE"
        python3 xxljob/executor.py run_financial_collection --data_type=$DATA_TYPE
        ;;
    daily)
        echo "▶️  执行日线数据采集"
        python3 xxljob/executor.py run_daily_collection --date_type=d
        ;;
    *)
        echo "❌ 未知任务类型：$TASK_TYPE"
        exit 1
        ;;
esac

echo ""
echo "=========================================="
echo "✅ 执行完成"
echo "=========================================="

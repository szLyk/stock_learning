# -*- coding: utf-8 -*-
"""
XXL-JOB 执行器服务器
基于 xxl-job-python 库
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from xxljob import XxlJobExecutor
from config import EXECUTOR_CONFIG, XXL_JOB_ADMIN_ADDRESS
from executor import StockDataExecutor

# 创建执行器实例
executor_instance = StockDataExecutor()

# 初始化 XXL-JOB 执行器
executor = XxlJobExecutor(
    admin_addresses=XXL_JOB_ADMIN_ADDRESS,
    app_name=EXECUTOR_CONFIG['app_name'],
    executor_ip=EXECUTOR_CONFIG['executor_ip'] or None,
    executor_port=EXECUTOR_CONFIG['executor_port'],
    executor_log_path=EXECUTOR_CONFIG['log_path'],
)

# =====================================================
# 注册任务处理函数
# =====================================================

@executor.route('run_daily_collection')
def handle_daily_collection(job_param):
    """
    日线/周线/月线采集任务
    job_param: 任务参数，如 "date_type=d"
    """
    try:
        # 解析参数
        params = {}
        if job_param:
            for item in job_param.split('&'):
                if '=' in item:
                    key, value = item.split('=', 1)
                    params[key] = value
        
        date_type = params.get('date_type', 'd')
        result = executor_instance.run_daily_collection(date_type)
        return f"执行成功：{result}"
    except Exception as e:
        return f"执行失败：{str(e)}"


@executor.route('run_min_collection')
def handle_min_collection(job_param):
    """
    分钟线采集任务
    """
    try:
        result = executor_instance.run_min_collection()
        return f"执行成功：{result}"
    except Exception as e:
        return f"执行失败：{str(e)}"


@executor.route('run_financial_collection')
def handle_financial_collection(job_param):
    """
    财务数据采集任务
    job_param: 如 "data_type=profit"
    """
    try:
        params = {}
        if job_param:
            for item in job_param.split('&'):
                if '=' in item:
                    key, value = item.split('=', 1)
                    params[key] = value
        
        data_type = params.get('data_type', 'profit')
        result = executor_instance.run_financial_collection(data_type)
        return f"执行成功：{result}"
    except Exception as e:
        return f"执行失败：{str(e)}"


@executor.route('run_eastmoney_collection')
def handle_eastmoney_collection(job_param):
    """
    东方财富数据采集任务
    job_param: 如 "data_type=north"
    """
    try:
        params = {}
        if job_param:
            for item in job_param.split('&'):
                if '=' in item:
                    key, value = item.split('=', 1)
                    params[key] = value
        
        data_type = params.get('data_type', 'moneyflow')
        result = executor_instance.run_eastmoney_collection(data_type)
        return f"执行成功：{result}"
    except Exception as e:
        return f"执行失败：{str(e)}"


@executor.route('run_indicator_calculation')
def handle_indicator_calculation(job_param):
    """
    技术指标计算任务
    job_param: 如 "indicator_type=all"
    """
    try:
        params = {}
        if job_param:
            for item in job_param.split('&'):
                if '=' in item:
                    key, value = item.split('=', 1)
                    params[key] = value
        
        indicator_type = params.get('indicator_type', 'all')
        result = executor_instance.run_indicator_calculation(indicator_type)
        return f"执行成功：{result}"
    except Exception as e:
        return f"执行失败：{str(e)}"


@executor.route('run_multi_factor')
def handle_multi_factor(job_param):
    """
    多因子打分任务
    """
    try:
        result = executor_instance.run_multi_factor()
        return f"执行成功：{result}"
    except Exception as e:
        return f"执行失败：{str(e)}"


# =====================================================
# 启动执行器
# =====================================================

if __name__ == '__main__':
    print(f"启动 XXL-JOB 执行器：{EXECUTOR_CONFIG['app_name']}")
    print(f"调度中心地址：{XXL_JOB_ADMIN_ADDRESS}")
    print(f"执行器端口：{EXECUTOR_CONFIG['executor_port']}")
    print(f"日志路径：{EXECUTOR_CONFIG['log_path']}")
    
    executor.start()

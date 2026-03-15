# -*- coding: utf-8 -*-
"""
XXL-JOB 执行器配置
"""

import os

# XXL-JOB 调度中心地址
XXL_JOB_ADMIN_ADDRESS = os.getenv('XXL_JOB_ADMIN_ADDRESS', 'http://xxl-job-admin:8080/xxl-job-admin')

# 宿主机 IP（用于 Admin 访问执行器）
HOST_IP = os.getenv('HOST_IP', '192.168.1.109')

# 执行器配置
EXECUTOR_CONFIG = {
    # 执行器 AppName（与 XXL-JOB 后台配置一致）
    'app_name': 'stock-data-executor',
    
    # 执行器名称
    'executor_name': '股票数据采集执行器',
    
    # 执行器 IP（自动注册时可留空）
    'executor_ip': os.getenv('EXECUTOR_IP', ''),
    
    # 执行器端口
    'executor_port': int(os.getenv('EXECUTOR_PORT', 9999)),
    
    # 执行器日志路径
    'log_path': os.getenv('EXECUTOR_LOG_PATH', '/home/fan/.openclaw/workspace/stock_learning/logs/xxljob'),
    
    # 执行器日志保留天数
    'log_retention_days': 30,
}

# 数据库配置（从环境变量或配置文件读取）
DATABASE_CONFIG = {
    'host': os.getenv('DB_HOST', '192.168.1.109'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'user': os.getenv('DB_USER', 'open_claw'),
    'password': os.getenv('DB_PASSWORD', 'xK7#pL9!mN2$vQ5@'),
    'database': os.getenv('DB_NAME', 'stock'),
}

# 任务超时配置（秒）
TASK_TIMEOUT = {
    'daily_collection': 3600,      # 日线采集：1 小时
    'min_collection': 1800,        # 分钟线采集：30 分钟
    'financial_collection': 7200,  # 财务数据：2 小时
    'eastmoney_collection': 3600,  # 东方财富：1 小时
    'indicator_calculation': 3600, # 指标计算：1 小时
    'multi_factor': 1800,          # 多因子：30 分钟
}

# 重试配置
RETRY_CONFIG = {
    'max_retries': 3,              # 最大重试次数
    'retry_delay': 60,             # 重试间隔（秒）
}

# 告警配置
ALERT_CONFIG = {
    'enabled': os.getenv('ALERT_ENABLED', 'true').lower() == 'true',
    'email': os.getenv('ALERT_EMAIL', '').split(','),
    'dingtalk_webhook': os.getenv('DINGTALK_WEBHOOK', ''),
    'wechat_webhook': os.getenv('WECHAT_WEBHOOK', ''),
}

# 运行环境
ENVIRONMENT = os.getenv('ENVIRONMENT', 'production')  # development / production

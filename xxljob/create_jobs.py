#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XXL-JOB 任务批量创建脚本
自动在 Admin 中配置所有 24 个任务
"""

import json
import urllib.request
import urllib.error

# XXL-JOB Admin 地址
ADMIN_URL = 'http://xxl-job-admin:8080/xxl-job-admin'

# 执行器 ID（需要先确认，默认 1）
EXECUTOR_ID = 1

# 任务列表
JOBS = [
    # ========== 第 1 层：基础行情 ==========
    {
        'job_desc': '股票日线数据采集',
        'job_handler': 'run_daily_collection',
        'cron': '0 0 18 * * ?',
        'executor_param': 'date_type=d',
        'executor_timeout': 3600,
    },
    {
        'job_desc': '股票周线数据采集',
        'job_handler': 'run_daily_collection',
        'cron': '0 30 18 * * ?',
        'executor_param': 'date_type=w',
        'executor_timeout': 3600,
    },
    {
        'job_desc': '股票月线数据采集',
        'job_handler': 'run_daily_collection',
        'cron': '0 0 19 * * ?',
        'executor_param': 'date_type=m',
        'executor_timeout': 3600,
    },
    {
        'job_desc': '股票分钟线数据采集',
        'job_handler': 'run_min_collection',
        'cron': '0 */30 9-15 * * ?',
        'executor_param': '',
        'executor_timeout': 1800,
    },
    
    # ========== 第 2 层：财务数据 ==========
    {
        'job_desc': '利润表数据采集',
        'job_handler': 'run_financial_collection',
        'cron': '0 0 20 * * ?',
        'executor_param': 'data_type=profit',
        'executor_timeout': 7200,
    },
    {
        'job_desc': '资产负债表数据采集',
        'job_handler': 'run_financial_collection',
        'cron': '0 0 20 * * ?',
        'executor_param': 'data_type=balance',
        'executor_timeout': 7200,
    },
    {
        'job_desc': '现金流量表数据采集',
        'job_handler': 'run_financial_collection',
        'cron': '0 0 20 * * ?',
        'executor_param': 'data_type=cashflow',
        'executor_timeout': 7200,
    },
    {
        'job_desc': '成长能力数据采集',
        'job_handler': 'run_financial_collection',
        'cron': '0 0 20 * * ?',
        'executor_param': 'data_type=growth',
        'executor_timeout': 7200,
    },
    {
        'job_desc': '运营能力数据采集',
        'job_handler': 'run_financial_collection',
        'cron': '0 0 20 * * ?',
        'executor_param': 'data_type=operation',
        'executor_timeout': 7200,
    },
    {
        'job_desc': '杜邦分析数据采集',
        'job_handler': 'run_financial_collection',
        'cron': '0 0 20 * * ?',
        'executor_param': 'data_type=dupont',
        'executor_timeout': 7200,
    },
    {
        'job_desc': '业绩预告数据采集',
        'job_handler': 'run_financial_collection',
        'cron': '0 0 20 * * ?',
        'executor_param': 'data_type=forecast',
        'executor_timeout': 7200,
    },
    {
        'job_desc': '分红送配数据采集',
        'job_handler': 'run_financial_collection',
        'cron': '0 0 20 * * ?',
        'executor_param': 'data_type=dividend',
        'executor_timeout': 7200,
    },
    
    # ========== 第 3 层：AKShare 数据（资金流向/股东/概念/评级） ==========
    {
        'job_desc': '资金流向数据采集（AKShare）',
        'job_handler': 'run_akshare_collection',
        'cron': '0 0 21 * * ?',
        'executor_param': 'data_type=moneyflow',
        'executor_timeout': 3600,
    },
    {
        'job_desc': '股东人数数据采集（AKShare）',
        'job_handler': 'run_akshare_collection',
        'cron': '0 0 21 * * ?',
        'executor_param': 'data_type=shareholder',
        'executor_timeout': 3600,
    },
    {
        'job_desc': '概念板块数据采集（AKShare）',
        'job_handler': 'run_akshare_collection',
        'cron': '0 0 21 * * ?',
        'executor_param': 'data_type=concept',
        'executor_timeout': 3600,
    },
    {
        'job_desc': '分析师评级数据采集（AKShare）',
        'job_handler': 'run_akshare_collection',
        'cron': '0 0 21 * * ?',
        'executor_param': 'data_type=analyst',
        'executor_timeout': 3600,
    },
    
    # ========== 第 4 层：指标计算 ==========
    {
        'job_desc': '技术指标计算（MACD/RSI/BOLL 等）',
        'job_handler': 'run_indicator_calculation',
        'cron': '0 0 22 * * ?',
        'executor_param': 'indicator_type=all',
        'executor_timeout': 3600,
    },
    
    # ========== 第 5 层：多因子打分 ==========
    {
        'job_desc': '多因子打分',
        'job_handler': 'run_multi_factor',
        'cron': '0 0 23 * * ?',
        'executor_param': '',
        'executor_timeout': 1800,
    },
]


def api_request(url, data=None, method='GET'):
    """发送 API 请求"""
    try:
        if data:
            data = json.dumps(data).encode('utf-8')
        
        req = urllib.request.Request(url, data=data, method=method)
        if data:
            req.add_header('Content-Type', 'application/json')
        
        # 添加 Cookie（如果需要登录）
        # req.add_header('Cookie', 'XXL_JOB_LOGIN_IDENTITY=...')
        
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        print(f"请求失败：{e}")
        return None


def get_executor_id():
    """获取执行器 ID"""
    result = api_request(f'{ADMIN_URL}/jobinfo/getExecutorIdByName?appName=stock-data-executor')
    if result and result.get('code') == 200:
        return result.get('content')
    return EXECUTOR_ID  # 默认返回 1


def create_job(job_config):
    """创建单个任务"""
    data = {
        'jobGroup': EXECUTOR_ID,
        'jobDesc': job_config['job_desc'],
        'author': 'admin',
        'scheduleType': 'CRON',
        'scheduleConf': job_config['cron'],
        'misfireStrategy': 'DO_NOTHING',
        'executorRouteStrategy': 'FIRST',
        'executorHandler': job_config['job_handler'],
        'executorParam': job_config.get('executor_param', ''),
        'executorBlockStrategy': 'SERIAL_EXECUTION',
        'executorTimeout': job_config.get('executor_timeout', 3600),
        'executorFailRetryCount': 3,
        'glueType': 'BEAN',
        'triggerStatus': 0,  # 0-停止，1-运行
    }
    
    result = api_request(f'{ADMIN_URL}/jobinfo/add', data=data, method='POST')
    return result


def main():
    print("=" * 60)
    print("XXL-JOB 任务批量创建脚本")
    print("=" * 60)
    
    # 获取执行器 ID
    executor_id = get_executor_id()
    print(f"执行器 ID: {executor_id}")
    
    if not executor_id:
        print("❌ 未找到执行器，请先在 Admin 中创建执行器：stock-data-executor")
        return
    
    # 创建任务
    success_count = 0
    fail_count = 0
    
    for i, job in enumerate(JOBS, 1):
        print(f"\n[{i}/{len(JOBS)}] 创建任务：{job['job_desc']}")
        result = create_job(job)
        
        if result and result.get('code') == 200:
            print(f"  ✅ 创建成功")
            success_count += 1
        else:
            print(f"  ❌ 创建失败：{result}")
            fail_count += 1
    
    print("\n" + "=" * 60)
    print(f"创建完成：成功 {success_count} 个，失败 {fail_count} 个")
    print("=" * 60)
    
    print("\n下一步：")
    print("1. 登录 XXL-JOB Admin: http://<宿主机 IP>:8080/xxl-job-admin")
    print("2. 进入 任务管理 查看创建的任务")
    print("3. 点击 执行一次 测试任务")
    print("4. 确认无误后 启动 任务")


if __name__ == '__main__':
    main()

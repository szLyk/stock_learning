#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XXL-JOB 任务批量创建脚本（直接写入数据库）
"""

import pymysql
import datetime

# 数据库配置
DB_CONFIG = {
    'host': 'mysql',
    'port': 3306,
    'user': 'root',
    'password': '123456',
    'database': 'xxl_job',
    'charset': 'utf8mb4'
}

# 执行器 ID（从 xxl_job_group 表获取）
EXECUTOR_ID = 1

# 任务列表（19 个任务）
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
    
    # ========== 第 3 层：东方财富数据 ==========
    {
        'job_desc': '资金流向数据采集',
        'job_handler': 'run_eastmoney_collection',
        'cron': '0 0 21 * * ?',
        'executor_param': 'data_type=moneyflow',
        'executor_timeout': 3600,
    },
    {
        'job_desc': '北向资金数据采集',
        'job_handler': 'run_eastmoney_collection',
        'cron': '0 0 21 * * ?',
        'executor_param': 'data_type=north',
        'executor_timeout': 3600,
    },
    {
        'job_desc': '股东人数数据采集',
        'job_handler': 'run_eastmoney_collection',
        'cron': '0 0 21 * * ?',
        'executor_param': 'data_type=shareholder',
        'executor_timeout': 3600,
    },
    {
        'job_desc': '概念板块数据采集',
        'job_handler': 'run_eastmoney_collection',
        'cron': '0 0 21 * * ?',
        'executor_param': 'data_type=concept',
        'executor_timeout': 3600,
    },
    {
        'job_desc': '分析师评级数据采集',
        'job_handler': 'run_eastmoney_collection',
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


def create_job(cursor, job_config):
    """创建单个任务"""
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    sql = """
    INSERT INTO xxl_job_info (
        job_group, job_desc, author, alarm_email, schedule_type, schedule_conf,
        misfire_strategy, executor_route_strategy, executor_handler, executor_param,
        executor_block_strategy, executor_timeout, executor_fail_retry_count,
        glue_type, glue_source, glue_remark, glue_updatetime, child_jobid,
        trigger_status, trigger_last_time, trigger_next_time,
        add_time, update_time
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
    )
    """
    
    values = (
        EXECUTOR_ID,                              # job_group
        job_config['job_desc'],                   # job_desc
        'admin',                                  # author
        '',                                       # alarm_email
        'CRON',                                   # schedule_type
        job_config['cron'],                       # schedule_conf
        'DO_NOTHING',                             # misfire_strategy
        'FIRST',                                  # executor_route_strategy
        job_config['job_handler'],                # executor_handler
        job_config.get('executor_param', ''),     # executor_param
        'SERIAL_EXECUTION',                       # executor_block_strategy
        job_config.get('executor_timeout', 3600), # executor_timeout
        3,                                        # executor_fail_retry_count
        'BEAN',                                   # glue_type
        '',                                       # glue_source
        '',                                       # glue_remark
        now,                                      # glue_updatetime
        '',                                       # child_jobid
        0,                                        # trigger_status (0-停止)
        0,                                        # trigger_last_time
        0,                                        # trigger_next_time
        now,                                      # add_time
        now                                       # update_time
    )
    
    cursor.execute(sql, values)
    return cursor.lastrowid


def main():
    print("=" * 70)
    print("XXL-JOB 任务批量创建脚本")
    print("=" * 70)
    
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # 检查执行器是否存在
        cursor.execute("SELECT id, app_name, title FROM xxl_job_group WHERE id = %s", (EXECUTOR_ID,))
        executor = cursor.fetchone()
        
        if not executor:
            print(f"❌ 执行器 ID={EXECUTOR_ID} 不存在，请先在 Admin 中创建执行器")
            return
        
        print(f"✅ 执行器：{executor[1]} - {executor[2]} (ID={executor[0]})")
        
        # 创建任务
        success_count = 0
        fail_count = 0
        
        for i, job in enumerate(JOBS, 1):
            try:
                job_id = create_job(cursor, job)
                print(f"[{i}/{len(JOBS)}] ✅ {job['job_desc']} (ID={job_id})")
                success_count += 1
            except Exception as e:
                print(f"[{i}/{len(JOBS)}] ❌ {job['job_desc']} 失败：{e}")
                fail_count += 1
        
        conn.commit()
        
        print("\n" + "=" * 70)
        print(f"创建完成：成功 {success_count} 个，失败 {fail_count} 个")
        print("=" * 70)
        
        if success_count > 0:
            print("\n✅ 任务已创建成功！")
            print("\n下一步：")
            print("1. 登录 Admin: http://192.168.1.109:8080/xxl-job-admin")
            print("2. 进入 任务管理 查看创建的 {success_count} 个任务")
            print("3. 点击 执行一次 测试任务")
            print("4. 确认无误后 启动 任务")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ 错误：{e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()

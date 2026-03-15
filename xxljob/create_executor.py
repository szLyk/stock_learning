#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
在 XXL-JOB Admin 中创建执行器配置
"""

import json
import urllib.request
import urllib.error
import http.cookiejar

ADMIN_URL = 'http://xxl-job-admin:8080/xxl-job-admin'
USERNAME = 'admin'
PASSWORD = '123456'

def login():
    """登录 Admin"""
    cookie = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie))
    
    # 登录
    login_data = urllib.parse.urlencode({
        'userName': USERNAME,
        'password': PASSWORD
    }).encode()
    
    try:
        req = urllib.request.Request(f'{ADMIN_URL}/login', data=login_data, method='POST')
        with opener.open(req, timeout=10) as resp:
            if resp.geturl().endswith('/toLogin'):
                print('❌ 登录失败，账号密码错误')
                return None, None
            print('✅ 登录成功')
            return opener, cookie
    except Exception as e:
        print(f'❌ 登录失败：{e}')
        return None, None


def create_executor(opener):
    """创建执行器"""
    data = urllib.parse.urlencode({
        'appname': 'stock-data-executor',
        'title': '股票数据采集执行器',
        'addressType': '0',  # 0=自动注册，1=手动录入
        'addressList': '172.18.0.2:9999',
    }).encode()
    
    try:
        req = urllib.request.Request(f'{ADMIN_URL}/jobgroup/save', data=data, method='POST')
        with opener.open(req, timeout=10) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            if result.get('code') == 200:
                print('✅ 执行器创建成功')
                return result.get('content')
            else:
                print(f'❌ 创建失败：{result.get("msg")}')
                return None
    except Exception as e:
        print(f'❌ 请求失败：{e}')
        return None


def main():
    print("=" * 60)
    print("XXL-JOB 执行器创建脚本")
    print("=" * 60)
    
    # 登录
    opener, cookie = login()
    if not opener:
        print("\n请手动创建执行器：")
        print("1. 登录：http://<宿主机 IP>:8080/xxl-job-admin")
        print("2. 进入 执行器管理 → 新增执行器")
        print("3. 填写：")
        print("   - AppName: stock-data-executor")
        print("   - 名称：股票数据采集执行器")
        print("   - 执行器类型：手动录入")
        print("   - 地址列表：172.18.0.2:9999")
        return
    
    # 创建执行器
    executor_id = create_executor(opener)
    
    if executor_id:
        print(f"\n执行器 ID: {executor_id}")
        print("\n下一步：")
        print("1. 刷新 Admin 网页端")
        print("2. 进入 执行器管理 查看")
        print("3. 开始创建任务")
    else:
        print("\n请手动创建执行器（见上方说明）")


if __name__ == '__main__':
    import urllib.parse
    main()

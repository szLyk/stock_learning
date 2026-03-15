# -*- coding: utf-8 -*-
"""
XXL-JOB 执行器服务器（简化版 - 不依赖 xxl-job-python 库）
通过 HTTP API 与 XXL-JOB Admin 通信
"""

import sys
import os
import json
import time
import socket
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入配置（同一目录下）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import EXECUTOR_CONFIG, XXL_JOB_ADMIN_ADDRESS
from executor import StockDataExecutor

# 创建执行器实例
executor_instance = StockDataExecutor()

# 执行器配置
EXECUTOR_APP_NAME = EXECUTOR_CONFIG['app_name']
EXECUTOR_PORT = EXECUTOR_CONFIG['executor_port']
EXECUTOR_LOG_PATH = EXECUTOR_CONFIG['log_path']

# 确保日志目录存在
os.makedirs(EXECUTOR_LOG_PATH, exist_ok=True)


def log_message(level, message):
    """日志输出"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_line = f"{timestamp} - {level} - {message}"
    print(log_line)
    
    # 写入日志文件
    log_file = os.path.join(EXECUTOR_LOG_PATH, 'executor.log')
    with open(log_file, 'a') as f:
        f.write(log_line + '\n')


def get_local_ip():
    """获取本机 IP"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return '127.0.0.1'


def register_to_admin():
    """注册到 XXL-JOB Admin"""
    import urllib.request
    import urllib.error
    
    admin_url = XXL_JOB_ADMIN_ADDRESS.rstrip('/')
    local_ip = get_local_ip()
    
    # 构建注册参数
    data = {
        'appName': EXECUTOR_APP_NAME,
        'address': f'{local_ip}:{EXECUTOR_PORT}',
        'registryType': 'EXECUTOR'
    }
    
    try:
        # XXL-JOB 注册接口
        registry_url = f'{admin_url}/registry'
        req = urllib.request.Request(
            registry_url,
            data=json.dumps(data).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        
        with urllib.request.urlopen(req, timeout=5) as response:
            result = json.loads(response.read().decode('utf-8'))
            if result.get('code') == 200:
                log_message('INFO', f'✅ 成功注册到 XXL-JOB Admin: {local_ip}:{EXECUTOR_PORT}')
                return True
            else:
                log_message('WARNING', f'注册失败：{result}')
                return False
    except Exception as e:
        log_message('ERROR', f'注册到 XXL-JOB Admin 失败：{e}')
        return False


class JobHandler:
    """任务处理器"""
    
    @staticmethod
    def run_daily_collection(params):
        """日线/周线/月线采集"""
        date_type = params.get('date_type', 'd')
        result = executor_instance.run_daily_collection(date_type)
        return f"执行成功：{result}"
    
    @staticmethod
    def run_min_collection(params):
        """分钟线采集"""
        result = executor_instance.run_min_collection()
        return f"执行成功：{result}"
    
    @staticmethod
    def run_financial_collection(params):
        """财务数据采集"""
        data_type = params.get('data_type', 'profit')
        result = executor_instance.run_financial_collection(data_type)
        return f"执行成功：{result}"
    
    @staticmethod
    def run_eastmoney_collection(params):
        """东方财富数据采集"""
        data_type = params.get('data_type', 'moneyflow')
        result = executor_instance.run_eastmoney_collection(data_type)
        return f"执行成功：{result}"
    
    @staticmethod
    def run_indicator_calculation(params):
        """指标计算"""
        indicator_type = params.get('indicator_type', 'all')
        result = executor_instance.run_indicator_calculation(indicator_type)
        return f"执行成功：{result}"
    
    @staticmethod
    def run_multi_factor(params):
        """多因子打分"""
        result = executor_instance.run_multi_factor()
        return f"执行成功：{result}"


# 任务映射
JOB_HANDLERS = {
    'run_daily_collection': JobHandler.run_daily_collection,
    'run_min_collection': JobHandler.run_min_collection,
    'run_financial_collection': JobHandler.run_financial_collection,
    'run_eastmoney_collection': JobHandler.run_eastmoney_collection,
    'run_indicator_calculation': JobHandler.run_indicator_calculation,
    'run_multi_factor': JobHandler.run_multi_factor,
}


class ExecutorHandler(BaseHTTPRequestHandler):
    """HTTP 请求处理器"""
    
    def log_message(self, format, *args):
        """自定义日志"""
        log_message('INFO', f"HTTP: {args[0]}")
    
    def do_POST(self):
        """处理 POST 请求"""
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        
        try:
            request_data = json.loads(body) if body else {}
        except:
            request_data = {}
        
        # 解析路径
        parsed = urlparse(self.path)
        path = parsed.path
        
        log_message('INFO', f'收到请求：{path}, 参数：{request_data}')
        
        # 健康检查
        if path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'UP', 'timestamp': datetime.now().isoformat()}).encode())
            return
        
        # 任务执行
        if path == '/run':
            job_handler = request_data.get('jobHandler')
            executor_params = request_data.get('executorParams', '')
            
            if not job_handler:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'code': 500, 'msg': 'jobHandler is required'}).encode())
                return
            
            # 解析参数
            params = {}
            if executor_params:
                for item in executor_params.split('&'):
                    if '=' in item:
                        key, value = item.split('=', 1)
                        params[key] = value
            
            log_message('INFO', f'执行任务：{job_handler}, 参数：{params}')
            
            try:
                # 调用对应的处理函数
                handler = JOB_HANDLERS.get(job_handler)
                if handler:
                    result = handler(params)
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        'code': 200,
                        'msg': 'success',
                        'content': result
                    }).encode())
                    log_message('INFO', f'任务完成：{job_handler}')
                else:
                    self.send_response(404)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        'code': 500,
                        'msg': f'JobHandler not found: {job_handler}'
                    }).encode())
                    log_message('ERROR', f'未找到 JobHandler: {job_handler}')
            except Exception as e:
                log_message('ERROR', f'任务执行失败：{e}')
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'code': 500,
                    'msg': str(e)
                }).encode())
            return
        
        # 未知路径
        self.send_response(404)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'code': 404, 'msg': 'Not found'}).encode())


def heartbeat_thread():
    """心跳线程（定期注册）"""
    while True:
        time.sleep(30)
        register_to_admin()


def main():
    """主函数"""
    log_message('INFO', '=' * 50)
    log_message('INFO', '启动 XXL-JOB 执行器')
    log_message('INFO', f'AppName: {EXECUTOR_APP_NAME}')
    log_message('INFO', f'端口：{EXECUTOR_PORT}')
    log_message('INFO', f'XXL-JOB Admin: {XXL_JOB_ADMIN_ADDRESS}')
    log_message('INFO', f'日志路径：{EXECUTOR_LOG_PATH}')
    log_message('INFO', '=' * 50)
    
    # 注册到 Admin
    time.sleep(3)  # 等待网络就绪
    register_to_admin()
    
    # 启动心跳线程
    heartbeat = threading.Thread(target=heartbeat_thread, daemon=True)
    heartbeat.start()
    
    # 启动 HTTP 服务器
    server = HTTPServer(('0.0.0.0', EXECUTOR_PORT), ExecutorHandler)
    log_message('INFO', f'执行器已启动，监听端口：{EXECUTOR_PORT}')
    log_message('INFO', '等待 XXL-JOB Admin 调度任务...')
    
    # 保存 PID
    pid_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'executor.pid')
    with open(pid_file, 'w') as f:
        f.write(str(os.getpid()))
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log_message('INFO', '执行器停止')
        server.shutdown()


if __name__ == '__main__':
    main()

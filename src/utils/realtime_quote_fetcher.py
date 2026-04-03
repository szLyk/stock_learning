# -*- coding: utf-8 -*-
"""
实时行情获取工具 - 多接口轮换版

支持的数据源：
1. 新浪财经（主接口）
2. 腾讯财经（备用接口）

特性：
- 自动轮换接口，避免单接口被封
- 失败自动切换备用接口
- 请求频率控制

Author: Xiao Luo
Date: 2026-04-03
"""

import time
import random
import requests
import pandas as pd
from typing import List, Dict, Optional
from logs.logger import LogManager


class RealtimeQuoteFetcher:
    """实时行情获取器 - 多接口轮换"""

    def __init__(self):
        self.logger = LogManager.get_logger("realtime_quote")

        # 请求头
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Connection': 'keep-alive',
        }

        # 新浪请求头
        self.sina_headers = self.headers.copy()
        self.sina_headers['Referer'] = 'http://finance.sina.com.cn/'

        # 腾讯请求头
        self.tencent_headers = self.headers.copy()
        self.tencent_headers['Referer'] = 'https://gu.qq.com/'

        # 接口配置
        self.interfaces = ['sina', 'tencent']
        self.current_interface = 0  # 当前使用的接口索引
        self.interface_fail_count = {'sina': 0, 'tencent': 0}
        self.interface_ban_threshold = 5  # 连续失败5次后切换

        # 请求控制
        self.min_interval = 0.5  # 最小请求间隔
        self.last_request_time = 0
        self.request_count = 0

    def _get_symbol_code(self, stock_code: str, interface: str) -> str:
        """转换股票代码格式"""
        # 转换为字符串
        stock_code = str(stock_code)

        # 去除可能的前缀
        stock_code = stock_code.replace('SH', '').replace('SZ', '').replace('sh', '').replace('sz', '')

        # 补齐6位
        stock_code = stock_code.zfill(6)

        if stock_code.startswith('6'):
            if interface == 'sina':
                return f'sh{stock_code}'
            else:
                return f'sh{stock_code}'
        else:
            if interface == 'sina':
                return f'sz{stock_code}'
            else:
                return f'sz{stock_code}'

    def _control_rate(self):
        """请求频率控制"""
        current = time.time()
        elapsed = current - self.last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_request_time = time.time()
        self.request_count += 1

    def _switch_interface(self):
        """切换接口"""
        self.current_interface = (self.current_interface + 1) % len(self.interfaces)
        new_interface = self.interfaces[self.current_interface]
        self.logger.info(f"切换接口: {new_interface}")
        return new_interface

    def _fetch_sina(self, stock_codes: List[str]) -> Dict[str, dict]:
        """新浪接口获取"""
        codes = [self._get_symbol_code(c, 'sina') for c in stock_codes]
        url = f"http://hq.sinajs.cn/list={','.join(codes)}"

        try:
            self._control_rate()
            resp = requests.get(url, headers=self.sina_headers, timeout=10)
            resp.encoding = 'gbk'

            if resp.status_code != 200:
                return None

            result = {}
            for line in resp.text.strip().split('\n'):
                if 'hq_str_' not in line or '=' not in line:
                    continue

                # 解析
                code_part = line.split('hq_str_')[1].split('=')[0]
                data_part = line.split('"')[1]

                if not data_part:
                    continue

                # 恢复原始代码
                original_code = code_part.replace('sh', '').replace('sz', '')
                fields = data_part.split(',')

                if len(fields) >= 32:
                    result[original_code] = {
                        'code': original_code,
                        'name': fields[0],
                        'open': float(fields[1]) if fields[1] else 0,
                        'pre_close': float(fields[2]) if fields[2] else 0,
                        'current': float(fields[3]) if fields[3] else 0,
                        'high': float(fields[4]) if fields[4] else 0,
                        'low': float(fields[5]) if fields[5] else 0,
                        'volume': int(float(fields[8])) if fields[8] else 0,
                        'amount': float(fields[9]) if fields[9] else 0,
                        'change_pct': round((float(fields[3]) - float(fields[2])) / float(fields[2]) * 100, 2) if fields[2] and float(fields[2]) > 0 else 0,
                        'source': 'sina'
                    }

            # 重置失败计数
            self.interface_fail_count['sina'] = 0
            return result

        except Exception as e:
            self.logger.warning(f"新浪接口失败: {e}")
            self.interface_fail_count['sina'] += 1
            return None

    def _fetch_tencent(self, stock_codes: List[str]) -> Dict[str, dict]:
        """腾讯接口获取"""
        codes = [self._get_symbol_code(c, 'tencent') for c in stock_codes]
        url = f"https://web.sqt.gtimg.cn/q={','.join(codes)}"

        try:
            self._control_rate()
            resp = requests.get(url, headers=self.tencent_headers, timeout=10)
            resp.encoding = 'gbk'

            if resp.status_code != 200:
                return None

            result = {}
            for line in resp.text.strip().split('\n'):
                if 'v_' not in line or '=' not in line:
                    continue

                # 解析: v_sz000001="51~平安银行~000001~11.12~..."
                code_part = line.split('v_')[1].split('=')[0]
                data_part = line.split('"')[1]

                if not data_part:
                    continue

                # 恢复原始代码
                original_code = code_part.replace('sh', '').replace('sz', '')
                fields = data_part.split('~')

                if len(fields) >= 33:
                    try:
                        current = float(fields[3]) if fields[3] else 0
                        pre_close = float(fields[4]) if fields[4] else 0
                        result[original_code] = {
                            'code': original_code,
                            'name': fields[1],
                            'open': float(fields[5]) if fields[5] else 0,
                            'pre_close': pre_close,
                            'current': current,
                            'high': float(fields[33]) if len(fields) > 33 and fields[33] else float(fields[31]) if len(fields) > 31 else 0,
                            'low': float(fields[34]) if len(fields) > 34 and fields[34] else float(fields[32]) if len(fields) > 32 else 0,
                            'volume': int(float(fields[6])) if fields[6] else 0,
                            'amount': float(fields[37]) if len(fields) > 37 else 0,
                            'change_pct': float(fields[32]) if len(fields) > 32 else 0,
                            'source': 'tencent'
                        }
                        # 计算涨跌幅（腾讯接口有时不准确）
                        if pre_close > 0:
                            result[original_code]['change_pct'] = round((current - pre_close) / pre_close * 100, 2)
                    except:
                        continue

            self.interface_fail_count['tencent'] = 0
            return result

        except Exception as e:
            self.logger.warning(f"腾讯接口失败: {e}")
            self.interface_fail_count['tencent'] += 1
            return None

    def fetch_quotes(self, stock_codes: List[str]) -> Dict[str, dict]:
        """
        获取实时行情（自动轮换接口）

        Args:
            stock_codes: 股票代码列表，如 ['000001', '600000']

        Returns:
            字典 {股票代码: 行情数据}
        """
        if not stock_codes:
            return {}

        # 分批获取（每批最多300只）
        batch_size = 300
        all_result = {}

        for i in range(0, len(stock_codes), batch_size):
            batch = stock_codes[i:i+batch_size]

            # 尝试获取
            result = None
            tried_interfaces = []

            for _ in range(len(self.interfaces)):
                interface = self.interfaces[self.current_interface]
                tried_interfaces.append(interface)

                # 检查是否被"封禁"
                if self.interface_fail_count[interface] >= self.interface_ban_threshold:
                    self.logger.warning(f"接口 {interface} 连续失败次数过多，跳过")
                    self._switch_interface()
                    continue

                # 尝试获取
                if interface == 'sina':
                    result = self._fetch_sina(batch)
                else:
                    result = self._fetch_tencent(batch)

                if result is not None:
                    break

                # 失败，切换接口
                self._switch_interface()
                time.sleep(1)

            if result:
                all_result.update(result)
            else:
                self.logger.error(f"所有接口均失败，批次: {batch[:3]}...")

            # 批次间隔
            if i + batch_size < len(stock_codes):
                time.sleep(random.uniform(1, 2))

        return all_result

    def fetch_single(self, stock_code: str) -> Optional[dict]:
        """获取单只股票行情"""
        result = self.fetch_quotes([stock_code])
        return result.get(stock_code)

    def get_status(self) -> dict:
        """获取接口状态"""
        return {
            'current_interface': self.interfaces[self.current_interface],
            'fail_count': self.interface_fail_count.copy(),
            'total_requests': self.request_count,
        }


# 测试入口
if __name__ == '__main__':
    fetcher = RealtimeQuoteFetcher()

    # 测试多只股票
    codes = ['000001', '000002', '600000', '600519', '300750']
    print("=== 测试多接口轮换 ===")
    print(f"请求股票: {codes}")
    print()

    result = fetcher.fetch_quotes(codes)

    print(f"成功获取: {len(result)} 只")
    print()
    for code, data in result.items():
        print(f"{code} {data['name']}")
        print(f"  当前: {data['current']}  涨幅: {data['change_pct']}%")
        print(f"  来源: {data['source']}")
        print()

    print("接口状态:", fetcher.get_status())
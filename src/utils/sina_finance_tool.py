# -*- coding: utf-8 -*-
"""
新浪财经数据采集工具
数据源：http://vip.stock.finance.sina.com.cn/

优势：
- 完全免费，无需注册
- 数据稳定可靠
- 接口简单易用

支持的数据类型：
1. 资金流向（主力流入/流出）
2. 北向资金持仓
3. 个股行情
4. 板块资金流向
5. 龙虎榜数据
"""

import datetime
import pandas as pd
import time
import random
import requests
from logs.logger import LogManager
from src.utils.mysql_tool import MySQLUtil
from src.utils.redis_tool import RedisUtil


class SinaFinanceFetcher:
    """新浪财经数据采集器"""
    
    def __init__(self):
        self.logger = LogManager.get_logger("sina_finance")
        self.mysql_manager = MySQLUtil()
        self.mysql_manager.connect()
        self.redis_manager = RedisUtil() if RedisUtil else None
        self.now_date = datetime.datetime.now().strftime('%Y-%m-%d')
        
        # 新浪财经 API 基础 URL
        self.base_url = "http://vip.stock.finance.sina.com.cn"
        self.quote_url = "http://quotes.sina.cn"
        
        # 请求头
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'http://finance.sina.com.cn/',
            'Accept': 'application/json, text/plain, */*'
        }
        
        # 请求频率控制
        self.request_count = 0
        self.last_request_time = 0
        self.min_request_interval = 0.5
        self.max_retry = 3
        self.retry_delay = 2
    
    def _get_symbol(self, stock_code):
        """获取新浪财经股票代码格式"""
        if stock_code.startswith('6'):
            return f"sh{stock_code}"
        elif stock_code.startswith('0') or stock_code.startswith('3'):
            return f"sz{stock_code}"
        else:
            return f"sh{stock_code}"
    
    def _control_request_rate(self):
        """控制请求频率"""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        
        if elapsed < self.min_request_interval:
            sleep_time = self.min_request_interval - elapsed
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
        self.request_count += 1
        
        # 每 100 次请求暂停
        if self.request_count % 100 == 0:
            pause_time = random.uniform(3, 5)
            self.logger.info(f"已请求 {self.request_count} 次，暂停 {pause_time:.1f} 秒")
            time.sleep(pause_time)
    
    def _request_with_retry(self, url, params=None, headers=None):
        """带重试机制的 HTTP 请求"""
        for retry in range(self.max_retry):
            try:
                self._control_request_rate()
                
                req_headers = self.headers.copy()
                if headers:
                    req_headers.update(headers)
                
                resp = requests.get(url, params=params, headers=req_headers, timeout=10)
                resp.raise_for_status()
                
                return resp
            
            except requests.exceptions.RequestException as e:
                if retry < self.max_retry - 1:
                    delay = self.retry_delay * (retry + 1) + random.uniform(0, 1)
                    self.logger.warning(f"请求失败，{delay:.1f}秒后重试（第{retry+1}/{self.max_retry}次）: {e}")
                    time.sleep(delay)
                else:
                    self.logger.error(f"请求失败，已达最大重试次数：{e}")
                    raise
        
        return None
    
    # =====================================================
    # 资金流向数据
    # =====================================================
    
    def fetch_moneyflow(self, stock_code, trade_date=None):
        """
        获取个股资金流向数据（新浪财经）
        
        API: http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getMoneyFlow
        
        参数:
            stock_code: 股票代码（如 000001）
            trade_date: 交易日期（如 2026-03-16）
        
        返回:
            DataFrame with columns:
            - stock_code: 股票代码
            - stock_date: 交易日期
            - main_net_in: 主力净流入 (万元)
            - sm_net_in: 小单净流入 (万元)
            - mm_net_in: 中单净流入 (万元)
            - bm_net_in: 大单净流入 (万元)
            - main_net_in_rate: 主力净流入率 (%)
            - close_price: 收盘价
            - change_rate: 涨跌幅 (%)
            - turnover_rate: 换手率 (%)
        """
        symbol = self._get_symbol(stock_code)
        
        url = f"{self.base_url}/quotes_service/api/json_v2.php/CN_MarketData.getMoneyFlow"
        params = {
            'symbol': symbol,
            'num': '100',  # 返回最近 100 天数据
        }
        
        try:
            resp = self._request_with_retry(url, params=params)
            if resp is None:
                return pd.DataFrame()
            
            data = resp.json()
            
            if not data or len(data) == 0:
                return pd.DataFrame()
            
            # 解析数据
            columns = ['trade_date', 'close_price', 'change_rate', 'main_net_in', 
                      'sm_net_in', 'mm_net_in', 'bm_net_in', 'main_net_in_rate',
                      'sm_net_in_rate', 'mm_net_in_rate', 'bm_net_in_rate', 'turnover_rate']
            
            df = pd.DataFrame(data, columns=columns)
            
            # 数据清洗
            df['stock_code'] = stock_code
            df['stock_date'] = pd.to_datetime(df['trade_date']).dt.date
            df['main_net_in'] = pd.to_numeric(df['main_net_in'], errors='coerce')
            df['sm_net_in'] = pd.to_numeric(df['sm_net_in'], errors='coerce')
            df['mm_net_in'] = pd.to_numeric(df['mm_net_in'], errors='coerce')
            df['bm_net_in'] = pd.to_numeric(df['bm_net_in'], errors='coerce')
            df['close_price'] = pd.to_numeric(df['close_price'], errors='coerce')
            df['change_rate'] = pd.to_numeric(df['change_rate'], errors='coerce')
            df['turnover_rate'] = pd.to_numeric(df['turnover_rate'], errors='coerce')
            
            # 按日期筛选
            if trade_date:
                df = df[df['stock_date'] == pd.to_datetime(trade_date).date()]
            
            # 返回需要的字段
            return df[['stock_code', 'stock_date', 'main_net_in', 'sm_net_in', 
                      'mm_net_in', 'bm_net_in', 'main_net_in_rate', 
                      'close_price', 'change_rate', 'turnover_rate']]
            
        except Exception as e:
            self.logger.error(f"获取资金流向失败 {stock_code}: {e}")
            return pd.DataFrame()
    
    # =====================================================
    # 北向资金数据
    # =====================================================
    
    def fetch_north_holding(self, stock_code, start_date=None, end_date=None):
        """
        获取北向资金持仓数据（新浪财经）
        
        API: http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getNorthFund
        
        参数:
            stock_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
        
        返回:
            DataFrame with columns:
            - stock_code: 股票代码
            - stock_date: 交易日期
            - north_hold: 北向资金持仓 (万股)
            - north_net_in: 北向资金净流入 (万股)
        """
        symbol = self._get_symbol(stock_code)
        
        url = f"{self.base_url}/quotes_service/api/json_v2.php/CN_MarketData.getNorthFund"
        params = {
            'symbol': symbol,
            'num': '100',
        }
        
        try:
            resp = self._request_with_retry(url, params=params)
            if resp is None:
                return pd.DataFrame()
            
            data = resp.json()
            
            if not data or len(data) == 0:
                return pd.DataFrame()
            
            # 解析数据
            columns = ['trade_date', 'north_hold', 'north_net_in', 'hold_ratio']
            df = pd.DataFrame(data, columns=columns)
            
            df['stock_code'] = stock_code
            df['stock_date'] = pd.to_datetime(df['trade_date']).dt.date
            df['north_hold'] = pd.to_numeric(df['north_hold'], errors='coerce')
            df['north_net_in'] = pd.to_numeric(df['north_net_in'], errors='coerce')
            
            if start_date:
                df = df[df['stock_date'] >= pd.to_datetime(start_date).date()]
            if end_date:
                df = df[df['stock_date'] <= pd.to_datetime(end_date).date()]
            
            return df[['stock_code', 'stock_date', 'north_hold', 'north_net_in']]
            
        except Exception as e:
            self.logger.error(f"获取北向资金失败 {stock_code}: {e}")
            return pd.DataFrame()
    
    # =====================================================
    # 板块资金流向
    # =====================================================
    
    def fetch_sector_moneyflow(self, sector_type='hy'):
        """
        获取板块资金流向
        
        参数:
            sector_type: 板块类型
                - 'hy': 行业板块
                - 'gn': 概念板块
                - 'dy': 地域板块
        
        返回:
            DataFrame with columns:
            - sector_name: 板块名称
            - main_net_in: 主力净流入 (万元)
            - main_net_in_rate: 主力净流入率 (%)
            - change_rate: 涨跌幅 (%)
        """
        url = f"{self.base_url}/quotes_service/api/json_v2.php/CN_MarketData.getSectorMoneyFlow"
        params = {
            'type': sector_type,
            'num': '100',
        }
        
        try:
            resp = self._request_with_retry(url, params=params)
            if resp is None:
                return pd.DataFrame()
            
            data = resp.json()
            
            if not data or len(data) == 0:
                return pd.DataFrame()
            
            columns = ['sector_name', 'main_net_in', 'main_net_in_rate', 
                      'change_rate', 'total_turnover']
            df = pd.DataFrame(data, columns=columns)
            
            df['main_net_in'] = pd.to_numeric(df['main_net_in'], errors='coerce')
            df['main_net_in_rate'] = pd.to_numeric(df['main_net_in_rate'], errors='coerce')
            df['change_rate'] = pd.to_numeric(df['change_rate'], errors='coerce')
            
            return df
            
        except Exception as e:
            self.logger.error(f"获取板块资金流向失败：{e}")
            return pd.DataFrame()
    
    # =====================================================
    # 龙虎榜数据
    # =====================================================
    
    def fetch_billboard(self, trade_date=None):
        """
        获取龙虎榜数据
        
        API: http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getBillboard
        
        参数:
            trade_date: 交易日期
        
        返回:
            DataFrame with columns:
            - stock_code: 股票代码
            - stock_name: 股票名称
            - stock_date: 交易日期
            - close_price: 收盘价
            - change_rate: 涨跌幅 (%)
            - turnover_rate: 换手率 (%)
            - buy_amount: 买入总额 (万元)
            - sell_amount: 卖出总额 (万元)
            - net_amount: 净额 (万元)
        """
        if not trade_date:
            trade_date = self.now_date
        
        url = f"{self.base_url}/quotes_service/api/json_v2.php/CN_MarketData.getBillboard"
        params = {
            'date': trade_date,
        }
        
        try:
            resp = self._request_with_retry(url, params=params)
            if resp is None:
                return pd.DataFrame()
            
            data = resp.json()
            
            if not data or len(data) == 0:
                return pd.DataFrame()
            
            columns = ['symbol', 'name', 'trade_date', 'close_price', 'change_rate',
                      'turnover_rate', 'buy_amount', 'sell_amount', 'net_amount']
            df = pd.DataFrame(data, columns=columns)
            
            df = df.rename(columns={
                'symbol': 'stock_code',
                'name': 'stock_name',
                'trade_date': 'stock_date'
            })
            
            # 清理股票代码
            df['stock_code'] = df['stock_code'].str.replace(r'[a-zA-Z]', '', regex=True)
            
            numeric_cols = ['close_price', 'change_rate', 'turnover_rate', 
                          'buy_amount', 'sell_amount', 'net_amount']
            for col in numeric_cols:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            return df
            
        except Exception as e:
            self.logger.error(f"获取龙虎榜失败：{e}")
            return pd.DataFrame()
    
    # =====================================================
    # 批量采集
    # =====================================================
    
    def fetch_moneyflow_batch(self, stock_codes, max_retries=3):
        """批量采集资金流向数据"""
        self.logger.info(f"=== 开始采集资金流向（新浪财经），共 {len(stock_codes)} 只股票 ===")
        
        success_count = 0
        fail_count = 0
        
        for i, stock_code in enumerate(stock_codes, 1):
            try:
                df = self.fetch_moneyflow(stock_code)
                if not df.empty:
                    self.mysql_manager.batch_insert_or_update('stock_capital_flow', df, ['stock_code', 'stock_date'])
                    success_count += 1
                    
                    if (i + 1) % 50 == 0:
                        self.logger.info(f"已处理 {i}/{len(stock_codes)}，成功 {success_count}")
                
            except Exception as e:
                fail_count += 1
                self.logger.error(f"处理 {stock_code} 失败：{e}")
            
            # 每 10 只股票暂停一下
            if i % 10 == 0:
                time.sleep(random.uniform(1, 2))
        
        self.logger.info(f"资金流向采集完成：成功 {success_count}/{len(stock_codes)}，失败 {fail_count}")
        return success_count
    
    def close(self):
        """关闭连接"""
        self.mysql_manager.close()


# =====================================================
# 测试入口
# =====================================================
if __name__ == '__main__':
    fetcher = SinaFinanceFetcher()
    
    # 测试单只股票
    print("测试资金流向接口...")
    df = fetcher.fetch_moneyflow('000001')
    if not df.empty:
        print(f"✅ 成功！{len(df)} 条数据")
        print(df.head())
    else:
        print("❌ 无数据")
    
    print("\n测试北向资金接口...")
    df = fetcher.fetch_north_holding('000001')
    if not df.empty:
        print(f"✅ 成功！{len(df)} 条数据")
        print(df.head())
    else:
        print("⚠️  无数据（可能该股无北向资金）")
    
    fetcher.close()

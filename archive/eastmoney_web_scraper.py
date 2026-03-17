# -*- coding: utf-8 -*-
"""
东方财富网页爬虫
爬取：资金流向、股东人数、概念板块、分析师评级

目标 URL:
- 资金流向：http://data.eastmoney.com/zjlx/000001.html
- 股东人数：http://data.eastmoney.com/gdgc/000001.html
- 概念板块：http://quote.eastmoney.com/sz000001.html
- 分析师评级：http://quote.eastmoney.com/sz000001.html#research
"""

import datetime
import pandas as pd
import time
import random
import requests
from bs4 import BeautifulSoup
from logs.logger import LogManager
from src.utils.mysql_tool import MySQLUtil


class EastMoneyWebScraper:
    """东方财富网页爬虫"""
    
    def __init__(self):
        self.logger = LogManager.get_logger("eastmoney_web_scraper")
        self.mysql_manager = MySQLUtil()
        self.mysql_manager.connect()
        
        # 基础 URL
        self.base_url = "http://data.eastmoney.com"
        self.quote_url = "http://quote.eastmoney.com"
        
        # 请求头
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
        }
        
        # 请求频率控制
        self.request_count = 0
        self.last_request_time = 0
        self.min_request_interval = 2.0  # 2 秒间隔
        self.max_retry = 3
    
    def _get_symbol(self, stock_code):
        """获取股票代码格式"""
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
        
        # 每 20 次请求暂停
        if self.request_count % 20 == 0:
            pause_time = random.uniform(5, 10)
            self.logger.info(f"已请求 {self.request_count} 次，暂停 {pause_time:.1f} 秒")
            time.sleep(pause_time)
    
    def _request_with_retry(self, url, headers=None):
        """带重试机制的 HTTP 请求"""
        for retry in range(self.max_retry):
            try:
                self._control_request_rate()
                
                req_headers = self.headers.copy()
                if headers:
                    req_headers.update(headers)
                
                resp = requests.get(url, headers=req_headers, timeout=15)
                resp.raise_for_status()
                
                # 检查是否被反爬
                if '验证' in resp.text or '安全' in resp.text:
                    self.logger.warning(f"可能触发反爬机制：{url}")
                    time.sleep(random.uniform(5, 10))
                    continue
                
                return resp
            
            except requests.exceptions.RequestException as e:
                if retry < self.max_retry - 1:
                    delay = 3 * (retry + 1) + random.uniform(2, 5)
                    self.logger.warning(f"请求失败，{delay:.1f}秒后重试（第{retry+1}/{self.max_retry}次）: {e}")
                    time.sleep(delay)
                else:
                    self.logger.error(f"请求失败，已达最大重试次数：{e}")
                    raise
        
        return None
    
    # =====================================================
    # 资金流向爬虫
    # =====================================================
    
    def fetch_moneyflow_web(self, stock_code):
        """
        爬取东方财富资金流向数据
        
        URL: http://data.eastmoney.com/zjlx/000001.html
        
        返回字段:
        - stock_code, stock_date
        - main_net_in, sm_net_in, mm_net_in, bm_net_in
        - main_net_in_rate, close_price, change_rate, turnover_rate
        """
        symbol = self._get_symbol(stock_code)
        url = f"{self.base_url}/zjlx/{symbol}.html"
        
        self.logger.info(f"爬取资金流向：{stock_code}")
        
        try:
            resp = self._request_with_retry(url)
            if resp is None:
                return pd.DataFrame()
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # 查找资金流向表格
            # 东方财富的表格通常在 class="table" 或 class="tbl" 中
            table = soup.find('table', {'class': lambda x: x and ('table' in x or 'tbl' in x)})
            
            if not table:
                self.logger.warning(f"未找到资金流向表格：{stock_code}")
                return pd.DataFrame()
            
            # 解析表格数据
            data = []
            rows = table.find_all('tr')
            
            for row in rows[1:]:  # 跳过表头
                cols = row.find_all('td')
                if len(cols) >= 9:
                    try:
                        row_data = {
                            'stock_date': cols[0].text.strip(),
                            'main_net_in': cols[1].text.strip().replace(',', ''),
                            'sm_net_in': cols[2].text.strip().replace(',', ''),
                            'mm_net_in': cols[3].text.strip().replace(',', ''),
                            'bm_net_in': cols[4].text.strip().replace(',', ''),
                            'main_net_in_rate': cols[5].text.strip().replace('%', ''),
                            'close_price': cols[6].text.strip().replace(',', ''),
                            'change_rate': cols[7].text.strip().replace('%', ''),
                            'turnover_rate': cols[8].text.strip().replace('%', ''),
                        }
                        data.append(row_data)
                    except Exception as e:
                        self.logger.debug(f"解析行失败：{e}")
                        continue
            
            if not data:
                return pd.DataFrame()
            
            df = pd.DataFrame(data)
            
            # 添加股票代码
            df['stock_code'] = stock_code
            
            # 数据清洗
            df['stock_date'] = pd.to_datetime(df['stock_date']).dt.date
            numeric_cols = ['main_net_in', 'sm_net_in', 'mm_net_in', 'bm_net_in',
                          'main_net_in_rate', 'close_price', 'change_rate', 'turnover_rate']
            
            for col in numeric_cols:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 选择需要的字段
            result_cols = ['stock_code', 'stock_date', 'main_net_in', 'sm_net_in',
                          'mm_net_in', 'bm_net_in', 'main_net_in_rate',
                          'close_price', 'change_rate', 'turnover_rate']
            
            # 只保留存在的列
            result_cols = [col for col in result_cols if col in df.columns]
            
            self.logger.info(f"成功爬取 {stock_code} 资金流向：{len(df)} 条")
            return df[result_cols]
            
        except Exception as e:
            self.logger.error(f"爬取资金流向失败 {stock_code}: {e}")
            return pd.DataFrame()
    
    # =====================================================
    # 股东人数爬虫
    # =====================================================
    
    def fetch_shareholder_web(self, stock_code):
        """
        爬取东方财富股东人数数据
        
        URL: http://data.eastmoney.com/gdgc/000001.html
        
        返回字段:
        - stock_code, stock_name, report_date
        - shareholder_count, shareholder_change
        - avg_hold_per_household, avg_hold_change
        - freehold_shares, freehold_ratio
        """
        symbol = self._get_symbol(stock_code)
        url = f"{self.base_url}/gdgc/{symbol}.html"
        
        self.logger.info(f"爬取股东人数：{stock_code}")
        
        try:
            resp = self._request_with_retry(url)
            if resp is None:
                return pd.DataFrame()
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # 查找股东人数表格
            table = soup.find('table', {'class': lambda x: x and ('table' in x or 'tbl' in x)})
            
            if not table:
                self.logger.warning(f"未找到股东人数表格：{stock_code}")
                return pd.DataFrame()
            
            # 解析表格数据
            data = []
            rows = table.find_all('tr')
            
            for row in rows[1:]:  # 跳过表头
                cols = row.find_all('td')
                if len(cols) >= 7:
                    try:
                        row_data = {
                            'report_date': cols[0].text.strip(),
                            'shareholder_count': cols[1].text.strip().replace(',', ''),
                            'shareholder_change': cols[2].text.strip().replace('%', ''),
                            'avg_hold_per_household': cols[3].text.strip().replace(',', ''),
                            'avg_hold_change': cols[4].text.strip().replace('%', ''),
                            'freehold_shares': cols[5].text.strip().replace(',', ''),
                            'freehold_ratio': cols[6].text.strip().replace('%', ''),
                        }
                        data.append(row_data)
                    except Exception as e:
                        self.logger.debug(f"解析行失败：{e}")
                        continue
            
            if not data:
                return pd.DataFrame()
            
            df = pd.DataFrame(data)
            
            # 添加股票代码
            df['stock_code'] = stock_code
            
            # 数据清洗
            df['report_date'] = pd.to_datetime(df['report_date']).dt.date
            numeric_cols = ['shareholder_count', 'shareholder_change',
                          'avg_hold_per_household', 'avg_hold_change',
                          'freehold_shares', 'freehold_ratio']
            
            for col in numeric_cols:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            result_cols = ['stock_code', 'report_date', 'shareholder_count',
                          'shareholder_change', 'avg_hold_per_household',
                          'avg_hold_change', 'freehold_shares', 'freehold_ratio']
            
            result_cols = [col for col in result_cols if col in df.columns]
            
            self.logger.info(f"成功爬取 {stock_code} 股东人数：{len(df)} 条")
            return df[result_cols]
            
        except Exception as e:
            self.logger.error(f"爬取股东人数失败 {stock_code}: {e}")
            return pd.DataFrame()
    
    # =====================================================
    # 概念板块爬虫
    # =====================================================
    
    def fetch_concept_web(self, stock_code):
        """
        爬取同花顺概念板块数据
        
        URL: http://stockpage.10jqka.com.cn/000001/
        
        返回字段:
        - stock_code, stock_name, concept_name, concept_type, is_hot
        """
        url = f"http://stockpage.10jqka.com.cn/{stock_code}/"
        
        self.logger.info(f"爬取概念板块：{stock_code}")
        
        try:
            resp = self._request_with_retry(url)
            if resp is None:
                return pd.DataFrame()
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # 同花顺的概念板块通常在某个特定的 div 中
            # 需要查找包含"概念"或"板块"的标签
            concept_list = []
            
            # 尝试多种方式查找概念
            for tag in soup.find_all(['a', 'span', 'div']):
                text = tag.get_text()
                if tag.name == 'a' and 'href' in tag.attrs:
                    href = tag['href']
                    if 'concept' in href or 'block' in href or 'plate' in href:
                        concept_list.append(text.strip())
            
            if not concept_list:
                self.logger.warning(f"未找到概念板块：{stock_code}")
                return pd.DataFrame()
            
            # 去重
            concept_list = list(set(concept_list))
            
            data = []
            for concept in concept_list:
                if concept and len(concept) > 1:  # 过滤空值和单字符
                    data.append({
                        'stock_code': stock_code,
                        'concept_name': concept,
                        'concept_type': '主题',
                        'is_hot': 0,
                    })
            
            if not data:
                return pd.DataFrame()
            
            df = pd.DataFrame(data)
            
            result_cols = ['stock_code', 'concept_name', 'concept_type', 'is_hot']
            result_cols = [col for col in result_cols if col in df.columns]
            
            self.logger.info(f"成功爬取 {stock_code} 概念板块：{len(df)} 个")
            return df
            
        except Exception as e:
            self.logger.error(f"爬取概念板块失败 {stock_code}: {e}")
            return pd.DataFrame()
    
    # =====================================================
    # 批量采集
    # =====================================================
    
    def fetch_moneyflow_batch(self, stock_codes):
        """批量爬取资金流向"""
        self.logger.info(f"=== 开始批量爬取资金流向，共 {len(stock_codes)} 只股票 ===")
        
        success_count = 0
        fail_count = 0
        
        for i, stock_code in enumerate(stock_codes, 1):
            try:
                df = self.fetch_moneyflow_web(stock_code)
                if not df.empty:
                    # 入库
                    rows = self.mysql_manager.batch_insert_or_update(
                        'stock_capital_flow', df, ['stock_code', 'stock_date'])
                    if rows:
                        success_count += 1
                        if i % 10 == 0:
                            self.logger.info(f"已处理 {i}/{len(stock_codes)}，成功 {success_count}")
                    else:
                        fail_count += 1
                else:
                    fail_count += 1
            except Exception as e:
                fail_count += 1
                self.logger.error(f"处理 {stock_code} 失败：{e}")
            
            # 每 10 只股票暂停
            if i % 10 == 0:
                time.sleep(random.uniform(3, 5))
        
        self.logger.info(f"资金流向爬取完成：成功 {success_count}/{len(stock_codes)}，失败 {fail_count}")
        return success_count
    
    def fetch_shareholder_batch(self, stock_codes):
        """批量爬取股东人数"""
        self.logger.info(f"=== 开始批量爬取股东人数，共 {len(stock_codes)} 只股票 ===")
        
        success_count = 0
        fail_count = 0
        
        for i, stock_code in enumerate(stock_codes, 1):
            try:
                df = self.fetch_shareholder_web(stock_code)
                if not df.empty:
                    rows = self.mysql_manager.batch_insert_or_update(
                        'stock_shareholder_info', df, ['stock_code', 'report_date'])
                    if rows:
                        success_count += 1
                        if i % 10 == 0:
                            self.logger.info(f"已处理 {i}/{len(stock_codes)}，成功 {success_count}")
                    else:
                        fail_count += 1
                else:
                    fail_count += 1
            except Exception as e:
                fail_count += 1
                self.logger.error(f"处理 {stock_code} 失败：{e}")
            
            if i % 10 == 0:
                time.sleep(random.uniform(3, 5))
        
        self.logger.info(f"股东人数爬取完成：成功 {success_count}/{len(stock_codes)}，失败 {fail_count}")
        return success_count
    
    def close(self):
        """关闭连接"""
        self.mysql_manager.close()


# =====================================================
# 测试入口
# =====================================================
if __name__ == '__main__':
    scraper = EastMoneyWebScraper()
    
    # 测试单只股票
    print("=" * 80)
    print("测试 1: 爬取资金流向")
    print("=" * 80)
    df = scraper.fetch_moneyflow_web('000001')
    if not df.empty:
        print(f"✅ 成功！{len(df)} 条数据")
        print(df.head(3))
    else:
        print("❌ 无数据")
    
    print("\n" + "=" * 80)
    print("测试 2: 爬取股东人数")
    print("=" * 80)
    df = scraper.fetch_shareholder_web('000001')
    if not df.empty:
        print(f"✅ 成功！{len(df)} 条数据")
        print(df.head(3))
    else:
        print("❌ 无数据")
    
    print("\n" + "=" * 80)
    print("测试 3: 爬取概念板块")
    print("=" * 80)
    df = scraper.fetch_concept_web('000001')
    if not df.empty:
        print(f"✅ 成功！{len(df)} 个概念")
        print(df['concept_name'].tolist()[:5])
    else:
        print("❌ 无数据")
    
    scraper.close()
    print("\n测试完成！")

# -*- coding: utf-8 -*-
"""
东方财富 Selenium 爬虫 v2 - 使用 JavaScript 获取数据
"""

import datetime
import pandas as pd
import time
import random
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from logs.logger import LogManager
from src.utils.mysql_tool import MySQLUtil


class EastMoneySeleniumScraperV2:
    """东方财富 Selenium 爬虫 v2 - 通过 JS 获取数据"""
    
    def __init__(self, headless=True):
        self.logger = LogManager.get_logger("eastmoney_selenium_v2")
        self.mysql_manager = MySQLUtil()
        self.mysql_manager.connect()
        
        self.headless = headless
        self.driver = self._init_driver()
        
        self.request_count = 0
        self.last_request_time = 0
    
    def _init_driver(self):
        """初始化 Chrome 浏览器"""
        options = Options()
        
        if self.headless:
            options.add_argument('--headless=new')
        
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        try:
            service = Service('/usr/bin/chromedriver')
            driver = webdriver.Chrome(service=service, options=options)
            self.logger.info("Chrome 浏览器初始化成功")
            return driver
        except Exception as e:
            self.logger.error(f"Chrome 初始化失败：{e}")
            raise
    
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
        
        if elapsed < 3.0:
            time.sleep(3.0 - elapsed)
        
        self.last_request_time = time.time()
        self.request_count += 1
        
        if self.request_count % 10 == 0:
            pause_time = random.uniform(10, 20)
            self.logger.info(f"已请求 {self.request_count} 次，暂停 {pause_time:.1f} 秒")
            time.sleep(pause_time)
    
    def fetch_moneyflow_js(self, stock_code):
        """
        通过执行 JavaScript 获取资金流向数据
        
        东方财富的数据存储在 JavaScript 变量中
        """
        symbol = self._get_symbol(stock_code)
        url = f"http://data.eastmoney.com/zjlx/{symbol}.html"
        
        self.logger.info(f"Selenium+JS 爬取资金流向：{stock_code}")
        
        try:
            self._control_request_rate()
            
            self.driver.get(url)
            time.sleep(8)  # 等待 JavaScript 加载数据
            
            # 尝试通过 JavaScript 获取数据
            # 东方财富的数据通常在某个 JavaScript 变量或 DOM 元素中
            
            # 方法 1: 查找页面中的表格数据
            script = """
                var tables = document.querySelectorAll('table');
                var result = [];
                for (var i = 0; i < tables.length; i++) {
                    var rows = tables[i].querySelectorAll('tr');
                    if (rows.length > 10) {  // 数据表格通常有很多行
                        var tableData = [];
                        for (var j = 0; j < rows.length; j++) {
                            var cols = rows[j].querySelectorAll('td');
                            var rowData = [];
                            for (var k = 0; k < cols.length; k++) {
                                rowData.push(cols[k].innerText);
                            }
                            if (rowData.length > 0) {
                                tableData.push(rowData);
                            }
                        }
                        if (tableData.length > 10) {
                            result.push(tableData);
                        }
                    }
                }
                return JSON.stringify(result);
            """
            
            tables_data = self.driver.execute_script(script)
            
            if tables_data and tables_data != '[]':
                tables = json.loads(tables_data)
                
                # 处理第一个表格（通常是资金流向数据）
                if len(tables) > 0:
                    data = []
                    for row in tables[0][1:]:  # 跳过表头
                        if len(row) >= 9:
                            try:
                                row_data = {
                                    'stock_date': row[0].strip() if row[0] else '',
                                    'main_net_in': row[1].strip().replace(',', '').replace('--', '') if row[1] else '',
                                    'sm_net_in': row[2].strip().replace(',', '').replace('--', '') if row[2] else '',
                                    'mm_net_in': row[3].strip().replace(',', '').replace('--', '') if row[3] else '',
                                    'bm_net_in': row[4].strip().replace(',', '').replace('--', '') if row[4] else '',
                                    'main_net_in_rate': row[5].strip().replace('%', '').replace('--', '') if row[5] else '',
                                    'close_price': row[6].strip().replace(',', '').replace('--', '') if row[6] else '',
                                    'change_rate': row[7].strip().replace('%', '').replace('--', '') if row[7] else '',
                                    'turnover_rate': row[8].strip().replace('%', '').replace('--', '') if row[8] else '',
                                }
                                data.append(row_data)
                            except Exception as e:
                                self.logger.debug(f"解析行失败：{e}")
                                continue
                    
                    if data:
                        df = pd.DataFrame(data)
                        df['stock_code'] = stock_code
                        
                        df['stock_date'] = pd.to_datetime(df['stock_date']).dt.date
                        numeric_cols = ['main_net_in', 'sm_net_in', 'mm_net_in', 'bm_net_in',
                                      'main_net_in_rate', 'close_price', 'change_rate', 'turnover_rate']
                        
                        for col in numeric_cols:
                            df[col] = pd.to_numeric(df[col], errors='coerce')
                        
                        result_cols = ['stock_code', 'stock_date', 'main_net_in', 'sm_net_in',
                                      'mm_net_in', 'bm_net_in', 'main_net_in_rate',
                                      'close_price', 'change_rate', 'turnover_rate']
                        
                        result_cols = [col for col in result_cols if col in df.columns]
                        
                        self.logger.info(f"成功爬取 {stock_code} 资金流向：{len(df)} 条")
                        return df[result_cols]
            
            self.logger.warning(f"未获取到资金流向数据：{stock_code}")
            return pd.DataFrame()
            
        except Exception as e:
            self.logger.error(f"爬取资金流向失败 {stock_code}: {e}")
            return pd.DataFrame()
    
    def close(self):
        """关闭浏览器和连接"""
        if self.driver:
            self.driver.quit()
            self.logger.info("Chrome 浏览器已关闭")
        self.mysql_manager.close()


# =====================================================
# 测试入口
# =====================================================
if __name__ == '__main__':
    scraper = EastMoneySeleniumScraperV2(headless=True)
    
    try:
        print("=" * 80)
        print("测试：Selenium+JS 爬取资金流向")
        print("=" * 80)
        
        df = scraper.fetch_moneyflow_js('000001')
        
        if not df.empty:
            print(f"✅ 成功！{len(df)} 条数据")
            print(df[['stock_code', 'stock_date', 'main_net_in', 'close_price']].head(3))
        else:
            print("❌ 无数据")
        
    finally:
        scraper.close()
    
    print("\n测试完成！")

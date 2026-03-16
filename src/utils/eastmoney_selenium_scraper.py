# -*- coding: utf-8 -*-
"""
东方财富 Selenium 爬虫
使用 Selenium 控制浏览器，执行 JavaScript 获取动态加载的数据

爬取目标:
- 资金流向：http://data.eastmoney.com/zjlx/000001.html
- 股东人数：http://data.eastmoney.com/gdgc/000001.html
- 概念板块：http://quote.eastmoney.com/sz000001.html
"""

import datetime
import pandas as pd
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from logs.logger import LogManager
from src.utils.mysql_tool import MySQLUtil


class EastMoneySeleniumScraper:
    """东方财富 Selenium 爬虫"""
    
    def __init__(self, headless=True):
        self.logger = LogManager.get_logger("eastmoney_selenium")
        self.mysql_manager = MySQLUtil()
        self.mysql_manager.connect()
        
        # 浏览器配置
        self.headless = headless
        self.driver = self._init_driver()
        
        # 请求频率控制
        self.request_count = 0
        self.last_request_time = 0
    
    def _init_driver(self):
        """初始化 Chrome 浏览器"""
        options = Options()
        
        # 无头模式
        if self.headless:
            options.add_argument('--headless=new')
        
        # 基础配置
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        
        # 伪装成真实浏览器
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # 禁用自动化特征（避免被检测）
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)
        
        # 禁用图片加载（加快速度）
        # options.add_argument('--blink-settings=imagesEnabled=false')
        
        try:
            service = Service('/usr/bin/chromedriver')
            driver = webdriver.Chrome(service=service, options=options)
            
            # 执行 CDP 命令隐藏 webdriver 特征
            driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    })
                '''
            })
            
            self.logger.info("Chrome 浏览器初始化成功")
            return driver
            
        except Exception as e:
            self.logger.error(f"Chrome 浏览器初始化失败：{e}")
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
        
        if elapsed < 3.0:  # 至少间隔 3 秒
            sleep_time = 3.0 - elapsed
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
        self.request_count += 1
        
        # 每 10 次请求暂停
        if self.request_count % 10 == 0:
            pause_time = random.uniform(10, 20)
            self.logger.info(f"已请求 {self.request_count} 次，暂停 {pause_time:.1f} 秒")
            time.sleep(pause_time)
    
    def _wait_for_element(self, by, value, timeout=15):
        """等待元素加载"""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return True
        except TimeoutException:
            self.logger.warning(f"等待元素超时：{value}")
            return False
    
    def _wait_for_table(self, timeout=15):
        """等待表格数据加载"""
        # 等待常见的表格类名
        table_classes = [
            'table', 'tbl', 'data-table', 'grid',
            'list-table', 'content-table'
        ]
        
        for class_name in table_classes:
            try:
                WebDriverWait(self.driver, timeout/len(table_classes)).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, f'table.{class_name}'))
                )
                return True
            except TimeoutException:
                continue
        
        return False
    
    # =====================================================
    # 资金流向爬虫
    # =====================================================
    
    def fetch_moneyflow_selenium(self, stock_code, days=30):
        """
        使用 Selenium 爬取东方财富资金流向数据
        
        URL: http://data.eastmoney.com/zjlx/000001.html
        
        参数:
            stock_code: 股票代码
            days: 获取天数
        
        返回:
            DataFrame with columns:
            - stock_code, stock_date
            - main_net_in, sm_net_in, mm_net_in, bm_net_in
            - main_net_in_rate, close_price, change_rate, turnover_rate
        """
        symbol = self._get_symbol(stock_code)
        url = f"http://data.eastmoney.com/zjlx/{symbol}.html"
        
        self.logger.info(f"Selenium 爬取资金流向：{stock_code}")
        
        try:
            self._control_request_rate()
            
            # 访问页面
            self.driver.get(url)
            
            # 等待页面加载（等待表格出现）
            time.sleep(5)  # 给 JavaScript 执行时间
            
            # 尝试多种方式查找表格
            table = None
            selectors = [
                'table.table',
                'table.tbl',
                'table.data-table',
                '.dataList table',
                '#datalist table',
            ]
            
            for selector in selectors:
                try:
                    table = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if table:
                        self.logger.debug(f"找到表格：{selector}")
                        break
                except:
                    continue
            
            if not table:
                # 尝试通过 XPath 查找
                try:
                    table = self.driver.find_element(By.XPATH, '//table[contains(@class, "table") or contains(@class, "tbl")]')
                except:
                    pass
            
            if not table:
                self.logger.warning(f"未找到资金流向表格：{stock_code}")
                # 保存页面源码调试
                with open(f'/tmp/eastmoney_{stock_code}.html', 'w', encoding='utf-8') as f:
                    f.write(self.driver.page_source)
                self.logger.info(f"页面源码已保存：/tmp/eastmoney_{stock_code}.html")
                return pd.DataFrame()
            
            # 解析表格数据
            rows = table.find_elements(By.TAG_NAME, 'tr')
            
            data = []
            for row in rows[1:]:  # 跳过表头
                try:
                    cols = row.find_elements(By.TAG_NAME, 'td')
                    if len(cols) >= 9:
                        row_data = {
                            'stock_date': cols[0].text.strip(),
                            'main_net_in': cols[1].text.strip().replace(',', '').replace('--', ''),
                            'sm_net_in': cols[2].text.strip().replace(',', '').replace('--', ''),
                            'mm_net_in': cols[3].text.strip().replace(',', '').replace('--', ''),
                            'bm_net_in': cols[4].text.strip().replace(',', '').replace('--', ''),
                            'main_net_in_rate': cols[5].text.strip().replace('%', '').replace('--', ''),
                            'close_price': cols[6].text.strip().replace(',', '').replace('--', ''),
                            'change_rate': cols[7].text.strip().replace('%', '').replace('--', ''),
                            'turnover_rate': cols[8].text.strip().replace('%', '').replace('--', ''),
                        }
                        data.append(row_data)
                except Exception as e:
                    self.logger.debug(f"解析行失败：{e}")
                    continue
            
            if not data:
                self.logger.warning(f"未解析到数据：{stock_code}")
                return pd.DataFrame()
            
            df = pd.DataFrame(data)
            df['stock_code'] = stock_code
            
            # 数据清洗
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
            
        except WebDriverException as e:
            self.logger.error(f"WebDriver 错误 {stock_code}: {e}")
            return pd.DataFrame()
        except Exception as e:
            self.logger.error(f"爬取资金流向失败 {stock_code}: {e}")
            return pd.DataFrame()
    
    # =====================================================
    # 股东人数爬虫
    # =====================================================
    
    def fetch_shareholder_selenium(self, stock_code):
        """
        使用 Selenium 爬取东方财富股东人数数据
        
        URL: http://data.eastmoney.com/gdgc/000001.html
        
        返回:
            DataFrame with columns:
            - stock_code, stock_name, report_date
            - shareholder_count, shareholder_change
            - avg_hold_per_household, avg_hold_change
            - freehold_shares, freehold_ratio
        """
        symbol = self._get_symbol(stock_code)
        url = f"http://data.eastmoney.com/gdgc/{symbol}.html"
        
        self.logger.info(f"Selenium 爬取股东人数：{stock_code}")
        
        try:
            self._control_request_rate()
            
            self.driver.get(url)
            time.sleep(5)
            
            # 查找表格
            table = None
            selectors = ['table.table', 'table.tbl', '.dataList table']
            
            for selector in selectors:
                try:
                    table = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if table:
                        break
                except:
                    continue
            
            if not table:
                self.logger.warning(f"未找到股东人数表格：{stock_code}")
                return pd.DataFrame()
            
            # 解析表格
            rows = table.find_elements(By.TAG_NAME, 'tr')
            
            data = []
            for row in rows[1:]:
                try:
                    cols = row.find_elements(By.TAG_NAME, 'td')
                    if len(cols) >= 7:
                        row_data = {
                            'report_date': cols[0].text.strip(),
                            'shareholder_count': cols[1].text.strip().replace(',', ''),
                            'shareholder_change': cols[2].text.strip().replace('%', '').replace('--', ''),
                            'avg_hold_per_household': cols[3].text.strip().replace(',', ''),
                            'avg_hold_change': cols[4].text.strip().replace('%', '').replace('--', ''),
                            'freehold_shares': cols[5].text.strip().replace(',', ''),
                            'freehold_ratio': cols[6].text.strip().replace('%', '').replace('--', ''),
                        }
                        data.append(row_data)
                except Exception as e:
                    self.logger.debug(f"解析行失败：{e}")
                    continue
            
            if not data:
                return pd.DataFrame()
            
            df = pd.DataFrame(data)
            df['stock_code'] = stock_code
            
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
    
    def fetch_concept_selenium(self, stock_code):
        """
        使用 Selenium 爬取同花顺概念板块数据
        
        URL: http://stockpage.10jqka.com.cn/000001/
        
        返回:
            DataFrame with columns:
            - stock_code, stock_name, concept_name, concept_type, is_hot
        """
        url = f"http://stockpage.10jqka.com.cn/{stock_code}/"
        
        self.logger.info(f"Selenium 爬取概念板块：{stock_code}")
        
        try:
            self._control_request_rate()
            
            self.driver.get(url)
            time.sleep(5)
            
            # 查找概念板块链接
            concepts = []
            
            # 尝试多种方式查找
            selectors = [
                'a[href*="concept"]',
                'a[href*="block"]',
                '.concept-item a',
                '.plate-link a',
            ]
            
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in elements:
                        text = elem.text.strip()
                        if text and len(text) > 1 and text not in concepts:
                            concepts.append(text)
                except:
                    continue
            
            if not concepts:
                # 尝试从页面文本中提取
                page_text = self.driver.page_source
                # 简单提取可能的概念名称
                # 这里需要根据实际页面结构调整
                
                self.logger.warning(f"未找到概念板块：{stock_code}")
                return pd.DataFrame()
            
            data = []
            for concept in concepts[:20]:  # 限制最多 20 个概念
                data.append({
                    'stock_code': stock_code,
                    'concept_name': concept,
                    'concept_type': '主题',
                    'is_hot': 0,
                })
            
            df = pd.DataFrame(data)
            
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
        self.logger.info(f"=== Selenium 批量爬取资金流向，共 {len(stock_codes)} 只股票 ===")
        
        success_count = 0
        fail_count = 0
        
        for i, stock_code in enumerate(stock_codes, 1):
            try:
                df = self.fetch_moneyflow_selenium(stock_code)
                if not df.empty:
                    rows = self.mysql_manager.batch_insert_or_update(
                        'stock_capital_flow', df, ['stock_code', 'stock_date'])
                    if rows:
                        success_count += 1
                        if i % 5 == 0:
                            self.logger.info(f"已处理 {i}/{len(stock_codes)}，成功 {success_count}")
                    else:
                        fail_count += 1
                else:
                    fail_count += 1
            except Exception as e:
                fail_count += 1
                self.logger.error(f"处理 {stock_code} 失败：{e}")
            
            # 每 5 只股票暂停
            if i % 5 == 0:
                time.sleep(random.uniform(5, 10))
        
        self.logger.info(f"资金流向爬取完成：成功 {success_count}/{len(stock_codes)}，失败 {fail_count}")
        return success_count
    
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
    scraper = EastMoneySeleniumScraper(headless=True)
    
    try:
        print("=" * 80)
        print("测试 1: Selenium 爬取资金流向")
        print("=" * 80)
        df = scraper.fetch_moneyflow_selenium('000001')
        if not df.empty:
            print(f"✅ 成功！{len(df)} 条数据")
            print(df[['stock_code', 'stock_date', 'main_net_in', 'close_price']].head(3))
        else:
            print("❌ 无数据")
        
        print("\n" + "=" * 80)
        print("测试 2: Selenium 爬取股东人数")
        print("=" * 80)
        df = scraper.fetch_shareholder_selenium('000001')
        if not df.empty:
            print(f"✅ 成功！{len(df)} 条数据")
            print(df.head(3))
        else:
            print("❌ 无数据")
        
        print("\n" + "=" * 80)
        print("测试 3: Selenium 爬取概念板块")
        print("=" * 80)
        df = scraper.fetch_concept_selenium('000001')
        if not df.empty:
            print(f"✅ 成功！{len(df)} 个概念")
            print(df['concept_name'].tolist()[:5])
        else:
            print("❌ 无数据")
        
    finally:
        scraper.close()
    
    print("\n测试完成！")

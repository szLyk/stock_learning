# -*- coding: utf-8 -*-
"""
东方财富数据采集工具（带 Redis 断点重试）
功能：资金流向、北向资金、股东人数、概念板块、分析师评级

Redis 任务队列：
- eastmoney:moneyflow - 资金流向待采集
- eastmoney:north - 北向资金待采集
- eastmoney:shareholder - 股东人数待采集
- eastmoney:concept - 概念板块待采集
- eastmoney:analyst - 分析师评级待采集
"""

import datetime
import pandas as pd
import time
import requests
from logs.logger import LogManager
from src.utils.mysql_tool import MySQLUtil
from src.utils.redis_tool import RedisUtil


class EastMoneyFetcher:
    """东方财富数据采集器（支持 Redis 断点重试）"""
    
    def __init__(self):
        self.logger = LogManager.get_logger("eastmoney_fetcher")
        self.mysql_manager = MySQLUtil()
        self.mysql_manager.connect()
        self.redis_manager = RedisUtil() if RedisUtil else None
        self.now_date = datetime.datetime.now().strftime('%Y-%m-%d')
        
        # 东方财富 API 基础 URL
        self.base_url = "http://push2.eastmoney.com"
        self.datacenter_url = "http://datacenter-web.eastmoney.com"
        
        # 请求头
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'http://quote.eastmoney.com/',
            'Accept': 'application/json, text/plain, */*'
        }
    
    def _get_secid(self, stock_code):
        """获取证券 ID（东方财富格式）"""
        if stock_code.startswith('6'):
            return f"1.{stock_code}"
        elif stock_code.startswith('0') or stock_code.startswith('3'):
            return f"0.{stock_code}"
        else:
            return f"1.{stock_code}"
    
    # =====================================================
    # 数据获取接口
    # =====================================================
    
    def fetch_moneyflow(self, stock_code, start_date=None, end_date=None, limit=1000):
        """获取个股资金流向数据"""
        secid = self._get_secid(stock_code)
        
        url = f"{self.base_url}/api/qt/stock/fflow/daykline/get"
        params = {
            'lmt': limit,
            'klt': 1,
            'fields1': 'f1,f2,f3,f7',
            'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65',
            'ut': 'b2884a393a59ad64002292a3e90d46a5',
            'secid': secid
        }
        
        try:
            resp = requests.get(url, params=params, headers=self.headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            if data.get('data') is None or data['data'].get('klines') is None:
                return pd.DataFrame()
            
            klines = data['data']['klines']
            columns = ['trade_date', 'main_net_in', 'sm_net_in', 'mm_net_in', 'bm_net_in',
                      'main_net_in_rate', 'sm_net_in_rate', 'mm_net_in_rate', 'bm_net_in_rate',
                      'close_price', 'change_rate', 'turnover_rate', 'total_turnover',
                      'main_buy_vol', 'main_sell_vol']
            
            df = pd.DataFrame([line.split(',') for line in klines], columns=columns)
            
            df['stock_code'] = stock_code
            df['stock_date'] = pd.to_datetime(df['trade_date']).dt.date
            df['main_net_in'] = pd.to_numeric(df['main_net_in'], errors='coerce')
            df['sm_net_in'] = pd.to_numeric(df['sm_net_in'], errors='coerce')
            df['mm_net_in'] = pd.to_numeric(df['mm_net_in'], errors='coerce')
            df['bm_net_in'] = pd.to_numeric(df['bm_net_in'], errors='coerce')
            df['close_price'] = pd.to_numeric(df['close_price'], errors='coerce')
            df['change_rate'] = pd.to_numeric(df['change_rate'], errors='coerce')
            df['turnover_rate'] = pd.to_numeric(df['turnover_rate'], errors='coerce')
            
            if start_date:
                df = df[df['stock_date'] >= pd.to_datetime(start_date).date()]
            if end_date:
                df = df[df['stock_date'] <= pd.to_datetime(end_date).date()]
            
            return df[['stock_code', 'stock_date', 'main_net_in', 'sm_net_in', 'mm_net_in', 'bm_net_in',
                      'main_net_in_rate', 'close_price', 'change_rate', 'turnover_rate']]
            
        except Exception as e:
            self.logger.error(f"获取资金流向失败 {stock_code}: {e}")
            return pd.DataFrame()
    
    def fetch_north_moneyflow(self, stock_code, start_date=None, end_date=None, limit=1000):
        """获取北向资金持仓数据"""
        secid = self._get_secid(stock_code)
        
        url = f"{self.base_url}/api/qt/stock/fflow/kline/get"
        params = {
            'lmt': limit,
            'klt': 1,
            'fields1': 'f1,f2,f3,f7',
            'fields2': 'f51,f52,f53',
            'ut': 'b2884a393a59ad64002292a3e90d46a5',
            'secid': secid
        }
        
        try:
            resp = requests.get(url, params=params, headers=self.headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            if data.get('data') is None or data['data'].get('klines') is None:
                return pd.DataFrame()
            
            klines = data['data']['klines']
            df = pd.DataFrame([line.split(',') for line in klines], columns=['trade_date', 'north_hold', 'north_net_in'])
            
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
    
    def fetch_shareholder_count(self, stock_code):
        """获取股东人数（季度数据）"""
        url = f"{self.datacenter_url}/api/data/v1/get"
        params = {
            'reportName': 'RPT_F10_EH_EQUITY',
            'columns': 'SECUCODE,SECURITY_CODE,SECURITY_NAME_ABBR,END_DATE,HOLDER_TOTAL_NUM,HOLDER_TOTAL_NUMCHANGE,AVG_HOLD,AVG_HOLD_CHANGE,FREEHOLD_SHARES,FREEHOLD_RATIO',
            'filter': f'(SECURITY_CODE="{stock_code}")',
            'pageNumber': '1',
            'pageSize': '20',
            'sortTypes': '-1',
            'sortColumns': 'END_DATE',
            'source': 'HSF10',
            'client': 'WEB'
        }
        
        try:
            resp = requests.get(url, params=params, headers=self.headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            if data.get('result') is None or data['result'].get('data') is None:
                return pd.DataFrame()
            
            df = pd.DataFrame(data['result']['data'])
            df = df.rename(columns={
                'SECURITY_CODE': 'stock_code',
                'SECURITY_NAME_ABBR': 'stock_name',
                'END_DATE': 'report_date',
                'HOLDER_TOTAL_NUM': 'shareholder_count',
                'HOLDER_TOTAL_NUMCHANGE': 'shareholder_change',
                'AVG_HOLD': 'avg_hold_per_household',
                'AVG_HOLD_CHANGE': 'avg_hold_change',
                'FREEHOLD_SHARES': 'freehold_shares',
                'FREEHOLD_RATIO': 'freehold_ratio'
            })
            
            df['report_date'] = pd.to_datetime(df['report_date']).dt.date
            
            return df[['stock_code', 'stock_name', 'report_date', 'shareholder_count',
                      'shareholder_change', 'avg_hold_per_household', 'avg_hold_change',
                      'freehold_shares', 'freehold_ratio']]
            
        except Exception as e:
            self.logger.error(f"获取股东人数失败 {stock_code}: {e}")
            return pd.DataFrame()
    
    def fetch_concept(self, stock_code):
        """获取股票所属概念板块"""
        secid = self._get_secid(stock_code)
        
        url = f"{self.base_url}/api/qt/stock/get"
        params = {
            'fields': 'f12,f13,f14,f152',
            'secid': secid
        }
        
        try:
            resp = requests.get(url, params=params, headers=self.headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            if data.get('data') is None:
                return pd.DataFrame()
            
            stock_data = data['data']
            concept_raw = stock_data.get('f152', '')
            
            if isinstance(concept_raw, int):
                return pd.DataFrame()
            elif isinstance(concept_raw, str):
                concept_str = concept_raw
            else:
                concept_str = str(concept_raw)
            
            if not concept_str or concept_str == '-':
                return pd.DataFrame()
            
            concepts = concept_str.split(',')
            df = pd.DataFrame([{
                'stock_code': stock_code,
                'stock_name': stock_data.get('f14', ''),
                'concept_name': c.strip()
            } for c in concepts if c.strip() and c.strip() != '-'])
            
            if df.empty:
                return pd.DataFrame()
            
            df['concept_type'] = '主题'
            df['is_hot'] = 0
            
            return df[['stock_code', 'stock_name', 'concept_name', 'concept_type', 'is_hot']]
            
        except Exception as e:
            self.logger.error(f"获取概念板块失败 {stock_code}: {e}")
            return pd.DataFrame()
    
    def fetch_analyst_rating(self, stock_code, start_date=None, end_date=None, limit=100):
        """获取分析师评级和研报"""
        url = f"{self.datacenter_url}/api/data/v1/get"
        params = {
            'reportName': 'RPT_RES_REPORT_INDEX',
            'columns': 'SECURITY_CODE,SECURITY_NAME_ABBR,PUBLISH_DATE,ORGANISM_CODE,ORGANISM_NAME,ANALYST_NAME,RATING_TYPE,FORECAST_EPS_1Y,FORECAST_EPS_2Y,TARGET_PRICE',
            'filter': f'(SECURITY_CODE="{stock_code}")',
            'pageNumber': '1',
            'pageSize': limit,
            'sortTypes': '-1',
            'sortColumns': 'PUBLISH_DATE',
            'source': 'WEB'
        }
        
        try:
            resp = requests.get(url, params=params, headers=self.headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            if data.get('result') is None or data['result'].get('data') is None:
                return pd.DataFrame()
            
            df = pd.DataFrame(data['result']['data'])
            df = df.rename(columns={
                'SECURITY_CODE': 'stock_code',
                'SECURITY_NAME_ABBR': 'stock_name',
                'PUBLISH_DATE': 'publish_date',
                'ORGANISM_NAME': 'institution_name',
                'ANALYST_NAME': 'analyst_name',
                'RATING_TYPE': 'rating_type',
                'TARGET_PRICE': 'target_price'
            })
            
            df['publish_date'] = pd.to_datetime(df['publish_date']).dt.date
            
            rating_map = {'买入': 5.0, '增持': 4.0, '中性': 3.0, '减持': 2.0, '卖出': 1.0}
            df['rating_score'] = df['rating_type'].map(rating_map).fillna(3.0)
            
            return df[['stock_code', 'stock_name', 'publish_date', 'institution_name',
                      'analyst_name', 'rating_type', 'rating_score', 'target_price']]
            
        except Exception as e:
            self.logger.error(f"获取分析师评级失败 {stock_code}: {e}")
            return pd.DataFrame()
    
    # =====================================================
    # Redis 断点重试机制
    # =====================================================
    
    def get_pending_stocks(self, data_type):
        """从 Redis 或数据库获取待采集股票（支持断点续传）"""
        if self.redis_manager is None:
            return self._get_pending_stocks_from_db(data_type)
        
        # Redis key 格式：eastmoney:north:stock_data:2026-03-15:unprocessed
        redis_key = f"eastmoney:{data_type}"
        
        # 1. 优先从 Redis 获取待处理股票（剩余的）
        pending = self.redis_manager.get_unprocessed_stocks(self.now_date, redis_key)
        
        if pending:
            # Redis 中有待处理股票，直接返回（断点续传）
            self.logger.info(f"📌 从 Redis 获取 {len(pending)} 只待处理股票（断点续传）")
            return pending
        
        # 2. Redis 为空，从数据库获取并初始化（首次执行）
        stocks_df = self._get_pending_stocks_from_db(data_type)
        if stocks_df is not None and len(stocks_df) > 0:
            self.redis_manager.add_unprocessed_stocks(stocks_df, self.now_date, redis_key)
            self.logger.info(f"✅ Redis 初始化完成：{len(stocks_df)}只股票（首次执行）")
            return stocks_df
        
        # 3. 数据库也为空
        self.logger.info("⚠️ 未找到待采集股票")
        return None
    
    def _get_pending_stocks_from_db(self, data_type):
        """从数据库获取待采集股票"""
        date_column_map = {
            'moneyflow': 'update_moneyflow',
            'north': 'update_north',
            'shareholder': 'update_shareholder',
            'concept': 'update_concept',
            'analyst': 'update_analyst'
        }
        
        date_column = date_column_map.get(data_type, 'update_moneyflow')
        
        # 获取 30 天内未更新的股票
        sql = f"""
        SELECT a.stock_code, b.stock_name, a.market_type 
        FROM update_eastmoney_record a
        LEFT JOIN stock_basic b ON a.stock_code = b.stock_code
        WHERE ({date_column} IS NULL OR {date_column} < DATE_SUB(CURDATE(), INTERVAL 30 DAY))
          AND b.stock_status = 1
        """
        
        result = self.mysql_manager.query_all(sql)
        if not result:
            # 如果是新表，从 stock_basic 获取所有股票
            sql = "SELECT stock_code, stock_name, market_type FROM stock_basic WHERE stock_status = 1"
            result = self.mysql_manager.query_all(sql)
        
        if not result:
            return []
        
        df = pd.DataFrame(result)
        df['stock_code'] = df['market_type'] + '.' + df['stock_code']
        return df['stock_code'].tolist()
    
    def update_record(self, stock_code, data_type, update_date):
        """更新采集记录"""
        date_column_map = {
            'moneyflow': 'update_moneyflow',
            'north': 'update_north',
            'shareholder': 'update_shareholder',
            'concept': 'update_concept',
            'analyst': 'update_analyst'
        }
        
        date_column = date_column_map.get(data_type)
        if not date_column:
            return
        
        sql = f"""
        INSERT INTO update_eastmoney_record (stock_code, {date_column})
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE {date_column} = VALUES({date_column})
        """
        self.mysql_manager.execute(sql, (stock_code, update_date))
    
    def mark_as_processed(self, stock_code, data_type):
        """标记股票为已处理（从 Redis unprocessed 集合中移除）"""
        if self.redis_manager is None:
            return
        
        # Redis key 格式：eastmoney:north:stock_data:2026-03-15:unprocessed
        redis_key = f"eastmoney:{data_type}"
        # 从 unprocessed 集合中移除（表示已处理）
        self.redis_manager.remove_unprocessed_stocks([stock_code], self.now_date, redis_key)
    
    # =====================================================
    # 批量采集
    # =====================================================
    
    # =====================================================
    # 独立数据采集任务（每个类型一个方法）
    # =====================================================
    
    def fetch_moneyflow_batch(self, max_retries=5):
        """批量采集资金流向数据"""
        self.logger.info("=== 开始采集资金流向 (moneyflow) ===")
        retry_count = 0
        while retry_count <= max_retries:
            stock_codes = self.get_pending_stocks('moneyflow')
            if not stock_codes:
                self.logger.info("✅ 资金流向采集完成" if retry_count == 0 else "✅ 资金流向补采完成")
                return
            total = len(stock_codes)
            self.logger.info(f"第 {retry_count + 1} 轮：共 {total} 只股票待处理")
            success_count = 0
            for i, stock_code in enumerate(stock_codes):
                try:
                    df = self.fetch_moneyflow(stock_code[-6:], start_date='2026-01-01')
                    if not df.empty:
                        self.mysql_manager.batch_insert_or_update('stock_capital_flow', df, ['stock_code', 'stock_date'])
                        self.update_record(stock_code[-6:], 'moneyflow', df['stock_date'].max())
                        success_count += 1
                    self.mark_as_processed(stock_code, 'moneyflow')
                    if (i + 1) % 50 == 0:
                        self.logger.info(f"已处理 {i+1}/{total}，成功 {success_count}")
                    if (i + 1) % 10 == 0:
                        time.sleep(0.3)
                except Exception as e:
                    self.logger.error(f"处理 {stock_code} 失败：{e}")
            self.logger.info(f"本轮完成：成功 {success_count}/{total}")
            remaining = self.get_pending_stocks('moneyflow')
            if not remaining:
                self.logger.info("✅ 资金流向全部采集完成")
                return
            retry_count += 1
            if retry_count <= max_retries:
                self.logger.info(f"⚠️ 仍有 {len(remaining)} 只股票未处理，5 秒后重试...")
                time.sleep(5)
        self.logger.error("❌ 达到最大重试次数，资金流向采集结束")
    
    def fetch_north_batch(self, max_retries=5):
        """批量采集北向资金数据"""
        self.logger.info("=== 开始采集北向资金 (north) ===")
        retry_count = 0
        while retry_count <= max_retries:
            stock_codes = self.get_pending_stocks('north')
            if not stock_codes:
                self.logger.info("✅ 北向资金采集完成" if retry_count == 0 else "✅ 北向资金补采完成")
                return
            total = len(stock_codes)
            self.logger.info(f"第 {retry_count + 1} 轮：共 {total} 只股票待处理")
            success_count = 0
            for i, stock_code in enumerate(stock_codes):
                try:
                    df = self.fetch_north_moneyflow(stock_code[-6:], limit=100)
                    if not df.empty:
                        self.mysql_manager.batch_insert_or_update('stock_capital_flow', df, ['stock_code', 'stock_date'])
                        self.update_record(stock_code[-6:], 'north', df['stock_date'].max())
                        success_count += 1
                    self.mark_as_processed(stock_code, 'north')
                    if (i + 1) % 50 == 0:
                        self.logger.info(f"已处理 {i+1}/{total}，成功 {success_count}")
                    if (i + 1) % 10 == 0:
                        time.sleep(0.3)
                except Exception as e:
                    self.logger.error(f"处理 {stock_code} 失败：{e}")
            self.logger.info(f"本轮完成：成功 {success_count}/{total}")
            remaining = self.get_pending_stocks('north')
            if not remaining:
                self.logger.info("✅ 北向资金全部采集完成")
                return
            retry_count += 1
            if retry_count <= max_retries:
                self.logger.info(f"⚠️ 仍有 {len(remaining)} 只股票未处理，5 秒后重试...")
                time.sleep(5)
        self.logger.error("❌ 达到最大重试次数，北向资金采集结束")
    
    def fetch_shareholder_batch(self, max_retries=5):
        """批量采集股东人数数据"""
        self.logger.info("=== 开始采集股东人数 (shareholder) ===")
        retry_count = 0
        while retry_count <= max_retries:
            stock_codes = self.get_pending_stocks('shareholder')
            if not stock_codes:
                self.logger.info("✅ 股东人数采集完成" if retry_count == 0 else "✅ 股东人数补采完成")
                return
            total = len(stock_codes)
            self.logger.info(f"第 {retry_count + 1} 轮：共 {total} 只股票待处理")
            success_count = 0
            for i, stock_code in enumerate(stock_codes):
                try:
                    df = self.fetch_shareholder_count(stock_code[-6:])
                    if not df.empty:
                        self.mysql_manager.batch_insert_or_update('stock_shareholder_info', df, ['stock_code', 'report_date'])
                        self.update_record(stock_code[-6:], 'shareholder', df['report_date'].max())
                        success_count += 1
                    self.mark_as_processed(stock_code, 'shareholder')
                    if (i + 1) % 50 == 0:
                        self.logger.info(f"已处理 {i+1}/{total}，成功 {success_count}")
                    if (i + 1) % 10 == 0:
                        time.sleep(0.3)
                except Exception as e:
                    self.logger.error(f"处理 {stock_code} 失败：{e}")
            self.logger.info(f"本轮完成：成功 {success_count}/{total}")
            remaining = self.get_pending_stocks('shareholder')
            if not remaining:
                self.logger.info("✅ 股东人数全部采集完成")
                return
            retry_count += 1
            if retry_count <= max_retries:
                self.logger.info(f"⚠️ 仍有 {len(remaining)} 只股票未处理，5 秒后重试...")
                time.sleep(5)
        self.logger.error("❌ 达到最大重试次数，股东人数采集结束")
    
    def fetch_concept_batch(self, max_retries=5):
        """批量采集概念板块数据"""
        self.logger.info("=== 开始采集概念板块 (concept) ===")
        retry_count = 0
        while retry_count <= max_retries:
            stock_codes = self.get_pending_stocks('concept')
            if not stock_codes:
                self.logger.info("✅ 概念板块采集完成" if retry_count == 0 else "✅ 概念板块补采完成")
                return
            total = len(stock_codes)
            self.logger.info(f"第 {retry_count + 1} 轮：共 {total} 只股票待处理")
            success_count = 0
            for i, stock_code in enumerate(stock_codes):
                try:
                    df = self.fetch_concept(stock_code[-6:])
                    if not df.empty:
                        self.mysql_manager.batch_insert_or_update('stock_concept', df, ['stock_code', 'concept_name'])
                        self.update_record(stock_code[-6:], 'concept', self.now_date)
                        success_count += 1
                    self.mark_as_processed(stock_code, 'concept')
                    if (i + 1) % 50 == 0:
                        self.logger.info(f"已处理 {i+1}/{total}，成功 {success_count}")
                    if (i + 1) % 10 == 0:
                        time.sleep(0.3)
                except Exception as e:
                    self.logger.error(f"处理 {stock_code} 失败：{e}")
            self.logger.info(f"本轮完成：成功 {success_count}/{total}")
            remaining = self.get_pending_stocks('concept')
            if not remaining:
                self.logger.info("✅ 概念板块全部采集完成")
                return
            retry_count += 1
            if retry_count <= max_retries:
                self.logger.info(f"⚠️ 仍有 {len(remaining)} 只股票未处理，5 秒后重试...")
                time.sleep(5)
        self.logger.error("❌ 达到最大重试次数，概念板块采集结束")
    
    def fetch_analyst_batch(self, max_retries=5):
        """批量采集分析师评级数据"""
        self.logger.info("=== 开始采集分析师评级 (analyst) ===")
        retry_count = 0
        while retry_count <= max_retries:
            stock_codes = self.get_pending_stocks('analyst')
            if not stock_codes:
                self.logger.info("✅ 分析师评级采集完成" if retry_count == 0 else "✅ 分析师评级补采完成")
                return
            total = len(stock_codes)
            self.logger.info(f"第 {retry_count + 1} 轮：共 {total} 只股票待处理")
            success_count = 0
            for i, stock_code in enumerate(stock_codes):
                try:
                    df = self.fetch_analyst_rating(stock_code[-6:], limit=50)
                    if not df.empty:
                        self.mysql_manager.batch_insert_or_update('stock_analyst_expectation', df, ['stock_code', 'publish_date'])
                        self.update_record(stock_code[-6:], 'analyst', df['publish_date'].max())
                        success_count += 1
                    self.mark_as_processed(stock_code, 'analyst')
                    if (i + 1) % 50 == 0:
                        self.logger.info(f"已处理 {i+1}/{total}，成功 {success_count}")
                    if (i + 1) % 10 == 0:
                        time.sleep(0.3)
                except Exception as e:
                    self.logger.error(f"处理 {stock_code} 失败：{e}")
            self.logger.info(f"本轮完成：成功 {success_count}/{total}")
            remaining = self.get_pending_stocks('analyst')
            if not remaining:
                self.logger.info("✅ 分析师评级全部采集完成")
                return
            retry_count += 1
            if retry_count <= max_retries:
                self.logger.info(f"⚠️ 仍有 {len(remaining)} 只股票未处理，5 秒后重试...")
                time.sleep(5)
        self.logger.error("❌ 达到最大重试次数，分析师评级采集结束")
    
    def run_full_collection(self):
        """运行完整的数据采集流程"""
        self.logger.info("=== 开始东方财富完整数据采集 ===")
        
        # 依次采集各类型数据
        try:
            self.fetch_moneyflow_batch(max_retries=3)
        except Exception as e:
            self.logger.error(f"moneyflow 采集中断：{e}")
        time.sleep(2)
        
        try:
            self.fetch_north_batch(max_retries=3)
        except Exception as e:
            self.logger.error(f"north 采集中断：{e}")
        time.sleep(2)
        
        try:
            self.fetch_concept_batch(max_retries=3)
        except Exception as e:
            self.logger.error(f"concept 采集中断：{e}")
        time.sleep(2)
        
        try:
            self.fetch_shareholder_batch(max_retries=3)
        except Exception as e:
            self.logger.error(f"shareholder 采集中断：{e}")
        time.sleep(2)
        
        try:
            self.fetch_analyst_batch(max_retries=3)
        except Exception as e:
            self.logger.error(f"analyst 采集中断：{e}")
        
        self.logger.info("=== 数据采集完成 ===")
    
    def close(self):
        """关闭连接"""
        self.mysql_manager.close()


# =====================================================
# 主程序入口
# =====================================================
if __name__ == '__main__':
    import sys
    
    fetcher = EastMoneyFetcher()
    
    if len(sys.argv) > 1:
        # 指定采集类型
        data_type = sys.argv[1]
        batch_methods = {
            'moneyflow': fetcher.fetch_moneyflow_batch,
            'north': fetcher.fetch_north_batch,
            'shareholder': fetcher.fetch_shareholder_batch,
            'concept': fetcher.fetch_concept_batch,
            'analyst': fetcher.fetch_analyst_batch,
        }
        method = batch_methods.get(data_type)
        if method:
            method(max_retries=3)
        else:
            print(f"未知数据类型：{data_type}")
            print("支持的类型：moneyflow, north, shareholder, concept, analyst")
    else:
        # 运行完整采集
        fetcher.run_full_collection()
    
    fetcher.close()

# -*- coding: utf-8 -*-
"""
东方财富数据采集工具
功能：资金流向、股东人数、概念板块、分析师评级等

API 文档参考：
- 资金流向：http://push2.eastmoney.com/api/qt/stock/fflow/daykline/get
- 股东人数：http://datacenter-web.eastmoney.com/api/data/v1/get
- 概念板块：http://push2.eastmoney.com/api/qt/stock/get
- 北向资金：http://push2.eastmoney.com/api/qt/stock/fflow/kline/get
"""

import requests
import pandas as pd
import time
from datetime import datetime, timedelta
from logs.logger import LogManager
from src.utils.mysql_tool import MySQLUtil


class EastMoneyFetcher:
    """东方财富数据采集器"""
    
    def __init__(self):
        self.logger = LogManager.get_logger("eastmoney_fetcher")
        self.mysql_manager = MySQLUtil()
        self.mysql_manager.connect()
        self.now_date = datetime.now().strftime('%Y-%m-%d')
        
        # 东方财富 API 基础 URL
        self.base_url = "http://push2.eastmoney.com"
        self.datacenter_url = "http://datacenter-web.eastmoney.com"
        
        # 请求头（模拟浏览器）
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'http://quote.eastmoney.com/',
            'Accept': 'application/json, text/plain, */*'
        }
    
    def _get_secid(self, stock_code):
        """
        获取证券 ID（东方财富格式）
        :param stock_code: 股票代码（如 601398）
        :return: secid (如 1.601398)
        """
        if stock_code.startswith('6'):
            return f"1.{stock_code}"  # 沪市
        elif stock_code.startswith('0') or stock_code.startswith('3'):
            return f"0.{stock_code}"  # 深市
        else:
            return f"1.{stock_code}"
    
    # =====================================================
    # 资金流向数据
    # =====================================================
    
    def fetch_moneyflow(self, stock_code, start_date=None, end_date=None, limit=1000):
        """
        获取个股资金流向数据（日频）
        :param stock_code: 股票代码（如 601398）
        :param start_date: 开始日期（YYYY-MM-DD）
        :param end_date: 结束日期（YYYY-MM-DD）
        :param limit: 返回数据条数
        :return: DataFrame
        """
        secid = self._get_secid(stock_code)
        
        url = f"{self.base_url}/api/qt/stock/fflow/daykline/get"
        params = {
            'lmt': limit,
            'klt': 1,  # 1=日，5=5 日，10=10 日
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
            
            # 解析数据
            klines = data['data']['klines']
            columns = ['trade_date', 'main_net_in', 'sm_net_in', 'mm_net_in', 'bm_net_in',
                      'main_net_in_rate', 'sm_net_in_rate', 'mm_net_in_rate', 'bm_net_in_rate',
                      'close_price', 'change_rate', 'turnover_rate', 'total_turnover',
                      'main_buy_vol', 'main_sell_vol']
            
            df = pd.DataFrame([line.split(',') for line in klines], columns=columns)
            
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
            
            # 筛选日期范围
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
        """
        获取北向资金持仓数据
        :param stock_code: 股票代码
        :param start_date: 开始日期
        :param end_date: 结束日期
        :return: DataFrame
        """
        secid = self._get_secid(stock_code)
        
        url = f"{self.base_url}/api/qt/stock/fflow/kline/get"
        params = {
            'lmt': limit,
            'klt': 1,
            'fields1': 'f1,f2,f3,f7',
            'fields2': 'f51,f52,f53',  # 日期，北向持仓，北向增持
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
            
            return df[['stock_code', 'stock_date', 'north_hold', 'north_net_in']]
            
        except Exception as e:
            self.logger.error(f"获取北向资金失败 {stock_code}: {e}")
            return pd.DataFrame()
    
    # =====================================================
    # 股东人数数据
    # =====================================================
    
    def fetch_shareholder_count(self, stock_code, year=None):
        """
        获取股东人数（季度数据）
        :param stock_code: 股票代码
        :param year: 年份
        :return: DataFrame
        """
        if not year:
            year = datetime.now().year
        
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
            
            # 重命名
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
    
    # =====================================================
    # 概念板块数据
    # =====================================================
    
    def fetch_concept(self, stock_code):
        """
        获取股票所属概念板块
        :param stock_code: 股票代码
        :return: DataFrame
        """
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
            
            # 处理不同类型的数据
            if isinstance(concept_raw, int):
                # 如果是整数，说明没有概念数据
                return pd.DataFrame()
            elif isinstance(concept_raw, str):
                concept_str = concept_raw
            else:
                concept_str = str(concept_raw)
            
            if not concept_str or concept_str == '-':
                return pd.DataFrame()
            
            # 解析概念（格式："概念 A,概念 B,概念 C"）
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
    
    # =====================================================
    # 分析师评级数据
    # =====================================================
    
    def fetch_analyst_rating(self, stock_code, start_date=None, end_date=None, limit=100):
        """
        获取分析师评级和研报
        :param stock_code: 股票代码
        :param start_date: 开始日期
        :param end_date: 结束日期
        :param limit: 返回条数
        :return: DataFrame
        """
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
            
            # 重命名
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
            
            # 评级打分
            rating_map = {'买入': 5.0, '增持': 4.0, '中性': 3.0, '减持': 2.0, '卖出': 1.0}
            df['rating_score'] = df['rating_type'].map(rating_map).fillna(3.0)
            
            return df[['stock_code', 'stock_name', 'publish_date', 'institution_name',
                      'analyst_name', 'rating_type', 'rating_score', 'target_price']]
            
        except Exception as e:
            self.logger.error(f"获取分析师评级失败 {stock_code}: {e}")
            return pd.DataFrame()
    
    # =====================================================
    # 批量采集
    # =====================================================
    
    def batch_fetch_moneyflow(self, stock_codes, start_date=None, end_date=None):
        """批量获取资金流向数据"""
        self.logger.info(f"开始批量获取资金流向，共 {len(stock_codes)} 只股票")
        
        all_dfs = []
        for i, stock_code in enumerate(stock_codes):
            df = self.fetch_moneyflow(stock_code, start_date, end_date)
            if not df.empty:
                all_dfs.append(df)
            
            if (i + 1) % 50 == 0:
                self.logger.info(f"已处理 {i+1}/{len(stock_codes)} 只股票")
            
            # 避免请求过快
            if (i + 1) % 10 == 0:
                time.sleep(0.3)
        
        if all_dfs:
            result = pd.concat(all_dfs, ignore_index=True)
            self.logger.info(f"资金流向采集完成，共 {len(result)} 条记录")
            return result
        else:
            self.logger.warning("资金流向采集结果为空")
            return pd.DataFrame()
    
    def batch_fetch_concept(self, stock_codes):
        """批量获取概念板块"""
        self.logger.info(f"开始批量获取概念板块，共 {len(stock_codes)} 只股票")
        
        all_dfs = []
        for i, stock_code in enumerate(stock_codes):
            df = self.fetch_concept(stock_code)
            if not df.empty:
                all_dfs.append(df)
            
            if (i + 1) % 100 == 0:
                self.logger.info(f"已处理 {i+1}/{len(stock_codes)} 只股票")
            
            if (i + 1) % 20 == 0:
                time.sleep(0.3)
        
        if all_dfs:
            result = pd.concat(all_dfs, ignore_index=True)
            self.logger.info(f"概念板块采集完成，共 {len(result)} 条记录")
            return result
        else:
            return pd.DataFrame()
    
    def save_to_db(self, df, table_name, unique_keys):
        """保存数据到数据库"""
        if df.empty:
            return 0
        
        rows = self.mysql_manager.batch_insert_or_update(
            table_name=table_name,
            df=df,
            unique_keys=unique_keys
        )
        self.logger.info(f"保存 {table_name} {rows} 条记录")
        return rows
    
    def close(self):
        """关闭连接"""
        self.mysql_manager.close()


# =====================================================
# 测试入口
# =====================================================
if __name__ == '__main__':
    fetcher = EastMoneyFetcher()
    
    # 测试资金流向
    print("\n=== 测试资金流向 ===")
    df = fetcher.fetch_moneyflow('601398', start_date='2026-03-01', end_date='2026-03-14')
    if not df.empty:
        print(f"获取到 {len(df)} 条记录")
        print(df.head())
    else:
        print("无数据")
    
    # 测试北向资金
    print("\n=== 测试北向资金 ===")
    df = fetcher.fetch_north_moneyflow('601398', limit=30)
    if not df.empty:
        print(f"获取到 {len(df)} 条记录")
        print(df.head())
    else:
        print("无数据")
    
    # 测试股东人数
    print("\n=== 测试股东人数 ===")
    df = fetcher.fetch_shareholder_count('601398', year=2025)
    if not df.empty:
        print(f"获取到 {len(df)} 条记录")
        print(df.head())
    else:
        print("无数据")
    
    # 测试概念板块
    print("\n=== 测试概念板块 ===")
    df = fetcher.fetch_concept('601398')
    if not df.empty:
        print(f"获取到 {len(df)} 条记录")
        print(df.to_string())
    else:
        print("无数据")
    
    # 测试分析师评级
    print("\n=== 测试分析师评级 ===")
    df = fetcher.fetch_analyst_rating('601398', limit=10)
    if not df.empty:
        print(f"获取到 {len(df)} 条记录")
        print(df.head())
    else:
        print("无数据")
    
    fetcher.close()

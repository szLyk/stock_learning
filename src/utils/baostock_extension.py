# -*- coding: utf-8 -*-
"""
Baostock 扩展工具类
功能：资金流向、分析师预期、股东筹码数据采集
"""

import datetime
import pandas as pd
import baostock as bs
from logs.logger import LogManager
from src.utils.mysql_tool import MySQLUtil
from src.utils.redis_tool import RedisUtil


class BaostockExtension:
    """Baostock 扩展数据采集器"""
    
    def __init__(self):
        self.logger = LogManager.get_logger("baostock_extension")
        self.now_date = datetime.datetime.now().strftime('%Y-%m-%d')
        self.login()
        self.mysql_manager = MySQLUtil()
        self.mysql_manager.connect()
        self.redis_manager = RedisUtil() if RedisUtil else None
    
    def login(self):
        """登录 baostock"""
        lg = bs.login()
        if lg.error_code != '0':
            raise Exception(f"Baostock login failed: {lg.error_msg}")
        self.logger.info("Baostock 登录成功")
    
    def logout(self):
        """登出 baostock"""
        bs.logout()
        self.logger.info("Baostock 已登出")
    
    # =====================================================
    # 资金流向数据采集
    # =====================================================
    
    def fetch_cash_flow_data(self, stock_code, year=None):
        """
        获取现金流量表数据（baostock 支持）
        :param stock_code: 股票代码（带市场前缀，如 sh.601398）
        :param year: 年份
        :return: DataFrame
        """
        if not year:
            year = datetime.datetime.now().year
        
        try:
            rs = bs.query_cash_flow_data(code=stock_code, year=year)
            
            if rs.error_code != '0':
                return pd.DataFrame()
            
            data_list = []
            while rs.next():
                data_list.append(rs.get_row_data())
            
            if not data_list:
                return pd.DataFrame()
            
            df = pd.DataFrame(data_list, columns=rs.fields)
            df['stock_code'] = df['code'].apply(lambda x: x[-6:] if x else x)
            return df
            
        except Exception as e:
            self.logger.error(f"获取现金流量表异常 {stock_code}: {e}")
            return pd.DataFrame()
    
    def batch_fetch_cash_flow(self, stock_codes, year=None):
        """
        批量获取现金流量表数据
        :param stock_codes: 股票代码列表
        :param year: 年份
        """
        if not year:
            year = datetime.datetime.now().year
        
        self.logger.info(f"开始批量获取现金流量表，共 {len(stock_codes)} 只股票")
        
        total_inserted = 0
        for i, stock_code in enumerate(stock_codes):
            if stock_code.startswith('6'):
                full_code = f'sh.{stock_code}'
            elif stock_code.startswith('0') or stock_code.startswith('3'):
                full_code = f'sz.{stock_code}'
            else:
                full_code = stock_code
            
            df = self.fetch_cash_flow_data(full_code, year)
            
            if not df.empty:
                self.logger.debug(f"获取 {stock_code} 现金流量表成功，{len(df)} 条")
                total_inserted += len(df)
            
            if (i + 1) % 100 == 0:
                self.logger.info(f"已处理 {i+1}/{len(stock_codes)} 只股票")
            
            # 避免请求过快
            if (i + 1) % 10 == 0:
                import time
                time.sleep(0.3)
        
        self.logger.info(f"现金流量表采集完成，共 {total_inserted} 条记录")
        return total_inserted
    
    # =====================================================
    # 分析师预期数据采集
    # =====================================================
    
    def fetch_forecast_report(self, stock_code, year=None):
        """
        获取业绩预告报告（baostock 支持）
        :param stock_code: 股票代码
        :param year: 年份
        :return: DataFrame
        """
        if not year:
            year = datetime.datetime.now().year
        
        try:
            rs = bs.query_forecast_report(code=stock_code, year=year)
            
            if rs.error_code != '0':
                return pd.DataFrame()
            
            data_list = []
            while rs.next():
                data_list.append(rs.get_row_data())
            
            if not data_list:
                return pd.DataFrame()
            
            df = pd.DataFrame(data_list, columns=rs.fields)
            df['stock_code'] = df['code'].apply(lambda x: x[-6:] if x else x)
            return df
            
        except Exception as e:
            self.logger.error(f"获取业绩预告异常 {stock_code}: {e}")
            return pd.DataFrame()
    
    def fetch_analyst_rating(self, stock_code, start_date=None, end_date=None):
        """
        获取分析师评级数据
        :param stock_code: 股票代码
        :param start_date: 开始日期
        :param end_date: 结束日期
        :return: DataFrame
        """
        if not start_date:
            start_date = '2020-01-01'
        if not end_date:
            end_date = self.now_date
        
        try:
            rs = bs.query_analyst_rating_data(stock_code=stock_code, start_date=start_date, end_date=end_date)
            
            if rs.error_code != '0':
                return pd.DataFrame()
            
            data_list = []
            while rs.next():
                data_list.append(rs.get_row_data())
            
            if not data_list:
                return pd.DataFrame()
            
            df = pd.DataFrame(data_list, columns=rs.fields)
            
            # 重命名
            df = df.rename(columns={
                'code': 'stock_code',
                'pubDate': 'publish_date',
                'rating': 'analyst_rating',
                'count': 'analyst_count',
                'targetPrice': 'target_price',
                'consensusEPS': 'consensus_eps',
                'consensusPE': 'consensus_pe'
            })
            
            df['stock_code'] = df['stock_code'].apply(lambda x: x[-6:] if x else x)
            
            # 计算评级打分
            rating_map = {
                '买入': 5.0,
                '增持': 4.0,
                '中性': 3.0,
                '减持': 2.0,
                '卖出': 1.0
            }
            df['rating_score'] = df['analyst_rating'].map(rating_map).fillna(3.0)
            
            # 数值转换
            numeric_cols = ['target_price', 'consensus_eps', 'consensus_pe', 'analyst_count']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            return df
            
        except Exception as e:
            self.logger.error(f"获取分析师评级异常 {stock_code}: {e}")
            return pd.DataFrame()
    
    def batch_fetch_forecast(self, stock_codes, year=None):
        """批量获取业绩预告数据"""
        if not year:
            year = datetime.datetime.now().year
        
        self.logger.info(f"开始批量获取业绩预告，共 {len(stock_codes)} 只股票")
        
        total_count = 0
        for i, stock_code in enumerate(stock_codes):
            if stock_code.startswith('6'):
                full_code = f'sh.{stock_code}'
            elif stock_code.startswith('0') or stock_code.startswith('3'):
                full_code = f'sz.{stock_code}'
            else:
                full_code = stock_code
            
            forecast_df = self.fetch_forecast_report(full_code, year)
            if not forecast_df.empty:
                total_count += len(forecast_df)
            
            if (i + 1) % 100 == 0:
                self.logger.info(f"已处理 {i+1}/{len(stock_codes)} 只股票")
            
            if (i + 1) % 10 == 0:
                import time
                time.sleep(0.3)
        
        self.logger.info(f"业绩预告采集完成：共 {total_count} 条")
        return total_count
    
    # =====================================================
    # 股东筹码数据采集
    # =====================================================
    
    def fetch_shareholder_info(self, stock_code):
        """
        获取股东信息（需要 baostock 支持，如无则返回空）
        注意：baostock 可能不直接提供股东人数数据
        """
        # baostock 不直接提供股东人数，可通过其他数据源补充
        # 这里预留接口
        return pd.DataFrame()
    
    def calculate_shareholder_from_basic(self):
        """
        从 stock_profit_data 计算股东相关信息
        """
        sql = """
        SELECT 
            stock_code,
            publish_date as report_date,
            total_share,
            liqa_share
        FROM stock.stock_profit_data
        WHERE publish_date <= %s
        ORDER BY stock_code, publish_date DESC
        """
        result = self.mysql_manager.query_all(sql, (self.now_date,))
        if not result:
            return pd.DataFrame()
        
        df = pd.DataFrame(result)
        
        # 计算户均持股（需要股东人数，这里先留空）
        df['avg_hold_per_household'] = None
        
        return df
    
    # =====================================================
    # 综合数据采集入口
    # =====================================================
    
    def run_full_collection(self, year=None):
        """运行完整的数据采集流程"""
        if not year:
            year = datetime.datetime.now().year
        
        self.logger.info("=== 开始扩展数据采集 ===")
        
        # 获取待采集的股票列表
        sql = """
        SELECT stock_code FROM stock.update_stock_record 
        WHERE stock_code IS NOT NULL 
        LIMIT 500
        """
        result = self.mysql_manager.query_all(sql)
        if not result:
            self.logger.warning("未找到待采集股票")
            return
        
        stock_codes = [r['stock_code'] for r in result]
        self.logger.info(f"待采集股票：{len(stock_codes)} 只")
        
        # 1. 采集现金流量表
        self.logger.info("\n[1/2] 采集现金流量表...")
        cash_count = self.batch_fetch_cash_flow(stock_codes, year=year)
        
        # 2. 采集业绩预告
        self.logger.info("\n[2/2] 采集业绩预告...")
        forecast_count = self.batch_fetch_forecast(stock_codes, year=year)
        
        self.logger.info("\n=== 数据采集完成 ===")
        self.logger.info(f"现金流量表：{cash_count} 条")
        self.logger.info(f"业绩预告：{forecast_count} 条")
    
    def close(self):
        """关闭连接"""
        self.logout()
        self.mysql_manager.close()


# =====================================================
# 测试入口
# =====================================================
if __name__ == '__main__':
    ext = BaostockExtension()
    
    # 测试单只股票
    print("测试单只股票现金流量表...")
    df = ext.fetch_cash_flow_data('sh.601398', 2025)
    if not df.empty:
        print(df.head())
    else:
        print("无数据")
    
    # 运行完整采集
    # ext.run_full_collection(year=2025)
    
    ext.close()

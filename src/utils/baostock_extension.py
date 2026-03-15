# -*- coding: utf-8 -*-
"""
Baostock 扩展工具类
功能：财务数据、业绩预告、成长能力等数据采集

⚠️ 重要：所有 baostock 接口必须先查阅 docs/BAOSTOCK_API_REFERENCE.md 确认存在！
不存在的接口：
- query_money_flow_data() ❌
- query_analyst_rating_data() ❌
- query_shareholder_data() ❌
- query_concept_data() ❌
"""

import datetime
import pandas as pd
import baostock as bs
from logs.logger import LogManager
from src.utils.mysql_tool import MySQLUtil
from src.utils.redis_tool import RedisUtil
import datetime


class BaostockExtension:
    """
    Baostock 扩展数据采集器
    
    ✅ 支持的接口:
    - query_cash_flow_data() - 现金流量表
    - query_forecast_report() - 业绩预告
    - query_profit_data() - 利润表
    - query_balance_data() - 资产负债表
    - query_growth_data() - 成长能力
    - query_operation_data() - 运营能力
    - query_dupont_data() - 杜邦分析
    
    ❌ 不支持的接口 (需其他数据源):
    - 资金流向
    - 分析师评级
    - 股东人数
    - 概念板块
    """
    
    def __init__(self):
        self.logger = LogManager.get_logger("baostock_extension")
        self.now_date = datetime.datetime.now().strftime('%Y-%m-%d')
        self.login()
        self.mysql_manager = MySQLUtil()
        self.mysql_manager.connect()
        self.redis_manager = RedisUtil() if RedisUtil else None
    
    # =====================================================
    # Redis 断点续传机制
    # =====================================================
    
    def get_pending_stocks(self, data_type='extension'):
        """从 Redis 或数据库获取待采集股票（支持断点续传）"""
        if self.redis_manager is None:
            return self._get_pending_stocks_from_db()
        
        redis_key = f"baostock:{data_type}"
        
        # 1. 优先从 Redis 获取待处理股票
        pending = self.redis_manager.get_unprocessed_stocks(self.now_date, redis_key)
        
        if not pending:
            # 2. Redis 为空，从数据库获取并初始化
            stocks_df = self._get_pending_stocks_from_db()
            if not stocks_df.empty:
                stock_list = stocks_df['stock_code'].tolist()
                self.redis_manager.add_unprocessed_stocks(stock_list, self.now_date, redis_key)
                self.logger.info(f"✅ Redis 初始化完成：{len(stock_list)}只股票")
            return stocks_df
        
        # 3. Redis 中有待处理股票
        return pending
    
    def _get_pending_stocks_from_db(self):
        """从数据库获取待采集股票"""
        sql = """
        SELECT stock_code FROM stock.update_stock_record 
        WHERE stock_code IS NOT NULL
        """
        result = self.mysql_manager.query_all(sql)
        if not result:
            self.logger.warning("未找到待采集股票")
            return None
        
        df = pd.DataFrame(result)
        df['stock_code'] = 'sh.' + df['stock_code']  # 默认加上市场前缀
        return df
    
    def mark_as_processed(self, stock_code, data_type='extension'):
        """标记股票为已处理（从 Redis 移除）"""
        if self.redis_manager is None:
            return
        
        redis_key = f"baostock:{data_type}"
        self.redis_manager.remove_unprocessed_stocks([stock_code], self.now_date, redis_key)
    
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
    
    def fetch_financial_data(self, stock_code, year=None, quarter=None):
        """
        获取财务数据（利润表 + 资产负债表 + 现金流量表 + 成长能力 + 运营能力 + 杜邦分析）
        :param stock_code: 股票代码（带市场前缀，如 sh.601398）
        :param year: 年份
        :param quarter: 季度 (1-4)，None 表示全部季度
        :return: dict of DataFrame
        """
        if not year:
            year = datetime.datetime.now().year
        
        results = {}
        
        # 1. 利润表
        try:
            if quarter:
                rs = bs.query_profit_data(code=stock_code, year=year, quarter=quarter)
            else:
                rs = bs.query_profit_data(code=stock_code, year=year)
            
            if rs.error_code == '0':
                data_list = []
                while rs.next():
                    data_list.append(rs.get_row_data())
                if data_list:
                    df = pd.DataFrame(data_list, columns=rs.fields)
                    df['stock_code'] = df['code'].apply(lambda x: x[-6:] if x else x)
                    results['profit'] = df
        except Exception as e:
            self.logger.error(f"获取利润表异常 {stock_code}: {e}")
        
        # 2. 资产负债表
        try:
            if quarter:
                rs = bs.query_balance_data(code=stock_code, year=year, quarter=quarter)
            else:
                rs = bs.query_balance_data(code=stock_code, year=year)
            
            if rs.error_code == '0':
                data_list = []
                while rs.next():
                    data_list.append(rs.get_row_data())
                if data_list:
                    df = pd.DataFrame(data_list, columns=rs.fields)
                    df['stock_code'] = df['code'].apply(lambda x: x[-6:] if x else x)
                    results['balance'] = df
        except Exception as e:
            self.logger.error(f"获取资产负债表异常 {stock_code}: {e}")
        
        # 3. 现金流量表
        try:
            if quarter:
                rs = bs.query_cash_flow_data(code=stock_code, year=year, quarter=quarter)
            else:
                rs = bs.query_cash_flow_data(code=stock_code, year=year)
            
            if rs.error_code == '0':
                data_list = []
                while rs.next():
                    data_list.append(rs.get_row_data())
                if data_list:
                    df = pd.DataFrame(data_list, columns=rs.fields)
                    df['stock_code'] = df['code'].apply(lambda x: x[-6:] if x else x)
                    results['cash_flow'] = df
        except Exception as e:
            self.logger.error(f"获取现金流量表异常 {stock_code}: {e}")
        
        # 4. 成长能力
        try:
            if quarter:
                rs = bs.query_growth_data(code=stock_code, year=year, quarter=quarter)
            else:
                rs = bs.query_growth_data(code=stock_code, year=year)
            
            if rs.error_code == '0':
                data_list = []
                while rs.next():
                    data_list.append(rs.get_row_data())
                if data_list:
                    df = pd.DataFrame(data_list, columns=rs.fields)
                    df['stock_code'] = df['code'].apply(lambda x: x[-6:] if x else x)
                    results['growth'] = df
        except Exception as e:
            self.logger.error(f"获取成长能力异常 {stock_code}: {e}")
        
        # 5. 运营能力
        try:
            if quarter:
                rs = bs.query_operation_data(code=stock_code, year=year, quarter=quarter)
            else:
                rs = bs.query_operation_data(code=stock_code, year=year)
            
            if rs.error_code == '0':
                data_list = []
                while rs.next():
                    data_list.append(rs.get_row_data())
                if data_list:
                    df = pd.DataFrame(data_list, columns=rs.fields)
                    df['stock_code'] = df['code'].apply(lambda x: x[-6:] if x else x)
                    results['operation'] = df
        except Exception as e:
            self.logger.error(f"获取运营能力异常 {stock_code}: {e}")
        
        # 6. 杜邦分析
        try:
            if quarter:
                rs = bs.query_dupont_data(code=stock_code, year=year, quarter=quarter)
            else:
                rs = bs.query_dupont_data(code=stock_code, year=year)
            
            if rs.error_code == '0':
                data_list = []
                while rs.next():
                    data_list.append(rs.get_row_data())
                if data_list:
                    df = pd.DataFrame(data_list, columns=rs.fields)
                    df['stock_code'] = df['code'].apply(lambda x: x[-6:] if x else x)
                    results['dupont'] = df
        except Exception as e:
            self.logger.error(f"获取杜邦分析异常 {stock_code}: {e}")
        
        return results
    
    def batch_fetch_financial_data(self, stock_codes, year=None, quarter=None):
        """
        批量获取财务数据（利润表 + 资产负债表 + 现金流量表 + 成长 + 运营 + 杜邦）
        :param stock_codes: 股票代码列表
        :param year: 年份
        :param quarter: 季度 (1-4)
        """
        if not year:
            year = datetime.datetime.now().year
        
        self.logger.info(f"开始批量获取财务数据，共 {len(stock_codes)} 只股票")
        
        total_count = 0
        for i, stock_code in enumerate(stock_codes):
            if stock_code.startswith('6'):
                full_code = f'sh.{stock_code}'
            elif stock_code.startswith('0') or stock_code.startswith('3'):
                full_code = f'sz.{stock_code}'
            else:
                full_code = stock_code
            
            results = self.fetch_financial_data(full_code, year=year, quarter=quarter)
            
            for table_name, df in results.items():
                if not df.empty:
                    self.logger.debug(f"获取 {stock_code} {table_name} 成功，{len(df)} 条")
                    total_count += len(df)
            
            if (i + 1) % 50 == 0:
                self.logger.info(f"已处理 {i+1}/{len(stock_codes)} 只股票")
            
            # 避免请求过快
            if (i + 1) % 5 == 0:
                import time
                time.sleep(0.5)
        
        self.logger.info(f"财务数据采集完成，共 {total_count} 条记录")
        return total_count
    
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
    
    def run_full_collection(self, year=None, quarter=None):
        """
        运行完整的数据采集流程（财务数据 + 业绩预告，支持 Redis 断点续传）
        :param year: 年份
        :param quarter: 季度 (1-4)，None 表示全部季度
        """
        if not year:
            year = datetime.datetime.now().year
        
        self.logger.info("=== 开始扩展数据采集（支持断点续传）===")
        
        # 获取待采集的股票列表（从 Redis 或数据库）
        stocks_df = self.get_pending_stocks('extension')
        
        if stocks_df is None or stocks_df.empty:
            self.logger.warning("未找到待采集股票")
            return
        
        stock_list = stocks_df['stock_code'].tolist()
        total = len(stock_list)
        self.logger.info(f"待采集股票：{total} 只")
        
        success_count = 0
        
        # 1. 采集财务数据（利润表 + 资产负债表 + 现金流量表 + 成长 + 运营 + 杜邦）
        self.logger.info("\n[1/2] 采集财务数据...")
        for i, stock_code in enumerate(stock_list, 1):
            try:
                results = self.fetch_financial_data(stock_code, year=year, quarter=quarter)
                if any(not df.empty for df in results.values()):
                    success_count += 1
                    self.mark_as_processed(stock_code, 'extension')
                
                if i % 10 == 0:
                    self.logger.info(f"已处理 {i}/{total}，成功 {success_count}")
            except Exception as e:
                self.logger.error(f"{stock_code} 采集失败：{e}")
        
        self.logger.info(f"财务数据采集完成：{success_count}/{total}")
        
        # 2. 采集业绩预告
        self.logger.info("\n[2/2] 采集业绩预告...")
        forecast_success = 0
        for i, stock_code in enumerate(stock_list, 1):
            try:
                df = self.fetch_forecast_report(stock_code, year=year)
                if not df.empty:
                    forecast_success += 1
            except Exception as e:
                self.logger.error(f"{stock_code} 业绩预告采集失败：{e}")
        
        self.logger.info(f"业绩预告采集完成：{forecast_success}/{total}")
        self.logger.info("\n=== 数据采集完成 ===")
    
    def close(self):
        """关闭连接"""
        self.logout()
        self.mysql_manager.close()


# =====================================================
# 测试入口
# =====================================================
if __name__ == '__main__':
    ext = BaostockExtension()
    
    # 测试单只股票财务数据
    print("测试单只股票财务数据...")
    results = ext.fetch_financial_data('sh.601398', year=2025)
    for table_name, df in results.items():
        if not df.empty:
            print(f"\n{table_name}: {len(df)} 条")
            print(df.head(2))
        else:
            print(f"\n{table_name}: 无数据")
    
    # 运行完整采集
    # ext.run_full_collection(year=2025)
    
    ext.close()

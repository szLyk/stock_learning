# -*- coding: utf-8 -*-
"""
Baostock 财务数据采集工具
功能：利润表、资产负债表、现金流量表、成长能力、运营能力、杜邦分析、业绩预告、分红送配

Redis 任务队列：
- baostock:profit - 利润表待采集
- baostock:balance - 资产负债表待采集
- baostock:cashflow - 现金流量表待采集
- baostock:growth - 成长能力待采集
- baostock:operation - 运营能力待采集
- baostock:dupont - 杜邦分析待采集
- baostock:forecast - 业绩预告待采集
- baostock:dividend - 分红送配待采集
"""

import datetime
import pandas as pd
import time
import baostock as bs
from logs.logger import LogManager
from src.utils.mysql_tool import MySQLUtil
from src.utils.redis_tool import RedisUtil


class BaostockFinancialFetcher:
    """Baostock 财务数据采集器（支持 Redis 断点重试）"""
    
    def __init__(self):
        self.logger = LogManager.get_logger("baostock_financial")
        self.mysql_manager = MySQLUtil()
        self.mysql_manager.connect()
        self.redis_manager = RedisUtil() if RedisUtil else None
        self.now_date = datetime.datetime.now().strftime('%Y-%m-%d')
        self.current_year = datetime.datetime.now().year
        
        # 登录 baostock
        self.login()
    
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
    
    def _get_stock_code(self, code_with_market):
        """提取纯股票代码"""
        if '.' in code_with_market:
            return code_with_market.split('.')[-1]
        return code_with_market
    
    # =====================================================
    # 财务数据采集接口
    # =====================================================
    
    def fetch_profit_data(self, stock_code, year=None):
        """
        获取利润表数据
        :param stock_code: 股票代码（如 sh.601398）
        :param year: 年份
        :return: DataFrame
        """
        if not year:
            year = self.current_year
        
        try:
            rs = bs.query_profit_data(code=stock_code, year=year)
            
            if rs.error_code != '0':
                return pd.DataFrame()
            
            data_list = []
            while rs.next():
                data_list.append(rs.get_row_data())
            
            if not data_list:
                return pd.DataFrame()
            
            df = pd.DataFrame(data_list, columns=rs.fields)
            
            # 重命名和清洗
            # 动态重命名（处理字段缺失和大小写问题）
            rename_map = {
                'code': 'stock_code',
                'pubDate': 'publish_date',
                'statDate': 'statistic_date'
            }
            
            # 检查并映射存在的字段（处理大小写）
            field_mapping = {
                'roeAvg': 'roe_avg', 'npMargin': 'np_margin', 'gpMargin': 'gp_margin',
                'netProfit': 'net_profit', 'epsTTM': 'eps_ttm',
                'MBRevenue': 'mb_revenue', 'totalShare': 'total_share', 'liqaShare': 'liqa_share'
            }
            
            for src, dst in field_mapping.items():
                if src in df.columns:
                    rename_map[src] = dst
            
            df = df.rename(columns=rename_map)
            
            df['stock_code'] = df['stock_code'].apply(lambda x: x[-6:] if x else x)
            df['publish_date'] = pd.to_datetime(df['publish_date']).dt.date
            df['statistic_date'] = pd.to_datetime(df['statistic_date']).dt.date
            
            # 计算季度
            df['season'] = pd.to_datetime(df['statistic_date']).dt.quarter
            
            # 数值转换
            numeric_cols = ['roe_avg', 'np_margin', 'gp_margin', 'net_profit', 'eps_ttm', 'mb_revenue', 'total_share', 'liqa_share']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            return df[['stock_code', 'publish_date', 'statistic_date', 'roe_avg', 'np_margin', 
                      'gp_margin', 'net_profit', 'eps_ttm', 'mb_revenue', 'total_share', 
                      'liqa_share', 'season']]
            
        except Exception as e:
            self.logger.error(f"获取利润表失败 {stock_code}: {e}")
            return pd.DataFrame()
    
    def fetch_balance_data(self, stock_code, year=None):
        """获取资产负债表数据"""
        if not year:
            year = self.current_year
        
        try:
            rs = bs.query_balance_data(code=stock_code, year=year)
            
            if rs.error_code != '0':
                return pd.DataFrame()
            
            data_list = []
            while rs.next():
                data_list.append(rs.get_row_data())
            
            if not data_list:
                return pd.DataFrame()
            
            df = pd.DataFrame(data_list, columns=rs.fields)
            df = df.rename(columns={
                'code': 'stock_code',
                'pubDate': 'publish_date',
                'statDate': 'statistic_date'
            })
            
            df['stock_code'] = df['stock_code'].apply(lambda x: x[-6:] if x else x)
            df['publish_date'] = pd.to_datetime(df['publish_date']).dt.date
            df['statistic_date'] = pd.to_datetime(df['statistic_date']).dt.date
            df['season'] = pd.to_datetime(df['statistic_date']).dt.quarter
            
            return df
            
        except Exception as e:
            self.logger.error(f"获取资产负债表失败 {stock_code}: {e}")
            return pd.DataFrame()
    
    def fetch_cash_flow_data(self, stock_code, year=None):
        """获取现金流量表数据"""
        if not year:
            year = self.current_year
        
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
            df = df.rename(columns={
                'code': 'stock_code',
                'pubDate': 'publish_date',
                'statDate': 'statistic_date'
            })
            
            df['stock_code'] = df['stock_code'].apply(lambda x: x[-6:] if x else x)
            df['publish_date'] = pd.to_datetime(df['publish_date']).dt.date
            df['statistic_date'] = pd.to_datetime(df['statistic_date']).dt.date
            df['season'] = pd.to_datetime(df['statistic_date']).dt.quarter
            
            return df
            
        except Exception as e:
            self.logger.error(f"获取现金流量表失败 {stock_code}: {e}")
            return pd.DataFrame()
    
    def fetch_growth_data(self, stock_code, year=None):
        """获取成长能力数据"""
        if not year:
            year = self.current_year
        
        try:
            rs = bs.query_growth_data(code=stock_code, year=year)
            
            if rs.error_code != '0':
                return pd.DataFrame()
            
            data_list = []
            while rs.next():
                data_list.append(rs.get_row_data())
            
            if not data_list:
                return pd.DataFrame()
            
            df = pd.DataFrame(data_list, columns=rs.fields)
            df = df.rename(columns={
                'code': 'stock_code',
                'pubDate': 'publish_date',
                'statDate': 'statistic_date'
            })
            
            df['stock_code'] = df['stock_code'].apply(lambda x: x[-6:] if x else x)
            df['publish_date'] = pd.to_datetime(df['publish_date']).dt.date
            df['statistic_date'] = pd.to_datetime(df['statistic_date']).dt.date
            df['season'] = pd.to_datetime(df['statistic_date']).dt.quarter
            
            return df
            
        except Exception as e:
            self.logger.error(f"获取成长能力失败 {stock_code}: {e}")
            return pd.DataFrame()
    
    def fetch_operation_data(self, stock_code, year=None):
        """获取运营能力数据"""
        if not year:
            year = self.current_year
        
        try:
            rs = bs.query_operation_data(code=stock_code, year=year)
            
            if rs.error_code != '0':
                return pd.DataFrame()
            
            data_list = []
            while rs.next():
                data_list.append(rs.get_row_data())
            
            if not data_list:
                return pd.DataFrame()
            
            df = pd.DataFrame(data_list, columns=rs.fields)
            df = df.rename(columns={
                'code': 'stock_code',
                'pubDate': 'publish_date',
                'statDate': 'statistic_date'
            })
            
            df['stock_code'] = df['stock_code'].apply(lambda x: x[-6:] if x else x)
            df['publish_date'] = pd.to_datetime(df['publish_date']).dt.date
            df['statistic_date'] = pd.to_datetime(df['statistic_date']).dt.date
            df['season'] = pd.to_datetime(df['statistic_date']).dt.quarter
            
            return df
            
        except Exception as e:
            self.logger.error(f"获取运营能力失败 {stock_code}: {e}")
            return pd.DataFrame()
    
    def fetch_dupont_data(self, stock_code, year=None):
        """获取杜邦分析数据"""
        if not year:
            year = self.current_year
        
        try:
            rs = bs.query_dupont_data(code=stock_code, year=year)
            
            if rs.error_code != '0':
                return pd.DataFrame()
            
            data_list = []
            while rs.next():
                data_list.append(rs.get_row_data())
            
            if not data_list:
                return pd.DataFrame()
            
            df = pd.DataFrame(data_list, columns=rs.fields)
            df = df.rename(columns={
                'code': 'stock_code',
                'pubDate': 'publish_date',
                'statDate': 'statistic_date'
            })
            
            df['stock_code'] = df['stock_code'].apply(lambda x: x[-6:] if x else x)
            df['publish_date'] = pd.to_datetime(df['publish_date']).dt.date
            df['statistic_date'] = pd.to_datetime(df['statistic_date']).dt.date
            df['season'] = pd.to_datetime(df['statistic_date']).dt.quarter
            
            return df
            
        except Exception as e:
            self.logger.error(f"获取杜邦分析失败 {stock_code}: {e}")
            return pd.DataFrame()
    
    def fetch_forecast_report(self, stock_code, year=None):
        """获取业绩预告"""
        if not year:
            year = self.current_year
        
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
            df = df.rename(columns={
                'code': 'stock_code',
                'pubDate': 'publish_date',
                'statDate': 'statistic_date'
            })
            
            df['stock_code'] = df['stock_code'].apply(lambda x: x[-6:] if x else x)
            df['publish_date'] = pd.to_datetime(df['publish_date']).dt.date
            df['statistic_date'] = pd.to_datetime(df['statistic_date']).dt.date
            
            return df
            
        except Exception as e:
            self.logger.error(f"获取业绩预告失败 {stock_code}: {e}")
            return pd.DataFrame()
    
    def fetch_dividend_data(self, stock_code, year=None):
        """获取分红送配数据"""
        if not year:
            year = self.current_year
        
        try:
            rs = bs.query_dividend_data(code=stock_code, year=year)
            
            if rs.error_code != '0':
                return pd.DataFrame()
            
            data_list = []
            while rs.next():
                data_list.append(rs.get_row_data())
            
            if not data_list:
                return pd.DataFrame()
            
            df = pd.DataFrame(data_list, columns=rs.fields)
            df = df.rename(columns={
                'code': 'stock_code',
                'dividendAnnYear': 'dividend_year',
                'dividendAnnTime': 'announce_date',
                'exDividendDate': 'ex_dividend_date',
                'dividend': 'cash_dividend',
                'bonusShares': 'bonus_shares',
                'reservedPerShare': 'reserved_per_share'
            })
            
            df['stock_code'] = df['stock_code'].apply(lambda x: x[-6:] if x else x)
            
            return df
            
        except Exception as e:
            self.logger.error(f"获取分红送配失败 {stock_code}: {e}")
            return pd.DataFrame()
    
    # =====================================================
    # Redis 断点重试机制
    # =====================================================
    
    def get_pending_stocks(self, data_type):
        """从 Redis 或数据库获取待采集股票"""
        if self.redis_manager is None:
            return self._get_pending_stocks_from_db(data_type)
        
        redis_key = f"baostock:{data_type}"
        pending = self.redis_manager.get_unprocessed_stocks(self.now_date, redis_key)
        
        if not pending:
            return self._get_pending_stocks_from_db(data_type)
        
        return pending
    
    def _get_pending_stocks_from_db(self, data_type):
        """从数据库获取待采集股票（包含上次采集日期）"""
        date_column_map = {
            'profit': 'update_profit_date',
            'balance': 'update_balance_date',
            'cashflow': 'update_cashflow_date',
            'growth': 'update_growth_date',
            'operation': 'update_operation_date',
            'dupont': 'update_dupont_date',
            'forecast': 'update_forecast_date',
            'dividend': 'update_dividend_date'
        }
        
        date_column = date_column_map.get(data_type, 'update_profit_date')
        
        # 获取所有股票及其上次采集日期
        sql = f"""
        SELECT a.stock_code, b.stock_name, a.market_type, 
               COALESCE({date_column}, '1990-01-01') as last_update_date
        FROM stock_performance_update_record a
        LEFT JOIN stock_basic b ON a.stock_code = b.stock_code
        WHERE b.stock_status = 1
        """
        
        result = self.mysql_manager.query_all(sql)
        if not result:
            sql = "SELECT stock_code, stock_name, market_type FROM stock_basic WHERE stock_status = 1"
            result = self.mysql_manager.query_all(sql)
            if not result:
                return []
            df = pd.DataFrame(result)
            df['last_update_date'] = '1990-01-01'
        else:
            df = pd.DataFrame(result)
        
        df['stock_code'] = df['market_type'] + '.' + df['stock_code']
        return df
    
    def update_record(self, stock_code, data_type, update_date):
        """更新采集记录"""
        date_column_map = {
            'profit': 'update_profit_date',
            'balance': 'update_balance_date',
            'cashflow': 'update_cashflow_date',
            'growth': 'update_growth_date',
            'operation': 'update_operation_date',
            'dupont': 'update_dupont_date',
            'forecast': 'update_forecast_date',
            'dividend': 'update_dividend_date'
        }
        
        date_column = date_column_map.get(data_type)
        if not date_column:
            return
        
        pure_code = self._get_stock_code(stock_code)
        
        sql = f"""
        INSERT INTO stock_performance_update_record (stock_code, {date_column})
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE {date_column} = VALUES({date_column})
        """
        self.mysql_manager.execute(sql, (pure_code, update_date))
    
    def mark_as_processed(self, stock_code, data_type):
        """标记股票为已处理"""
        if self.redis_manager is None:
            return
        
        redis_key = f"baostock:{data_type}"
        self.redis_manager.remove_unprocessed_stocks([stock_code], self.now_date, redis_key)
    
    # =====================================================
    # 批量采集
    # =====================================================
    
    # =====================================================
    # 独立财务数据采集任务（每个类型一个方法）
    # =====================================================
    
    def _get_years_to_fetch(self, last_update_date):
        """根据上次更新日期，计算需要采集的年份"""
        if not last_update_date or last_update_date == '1990-01-01':
            # 第一次采集，获取所有年份（从 2007 年到当前年）
            return list(range(2007, self.current_year + 1))
        
        # 解析上次更新日期
        try:
            if isinstance(last_update_date, str):
                last_date = datetime.datetime.strptime(last_update_date, '%Y-%m-%d')
            else:
                last_date = last_update_date
        except:
            return list(range(2007, self.current_year + 1))
        
        # 只采集上次日期之后的年份
        start_year = last_date.year
        # 如果上次采集了完整年份，从今年开始；否则从去年开始（确保不遗漏）
        if start_year >= self.current_year:
            return [self.current_year]
        elif start_year >= self.current_year - 1:
            return [self.current_year]
        else:
            # 采集从 last_year+1 到当前年的所有年份
            return list(range(start_year + 1, self.current_year + 1))
    
    def _fetch_single_type_batch(self, data_type, table_name, fetch_func, date_field, max_retries):
        """通用批量采集方法（根据记录表动态决定采集年份）"""
        self.logger.info(f"=== 开始采集 {data_type} ===")
        retry_count = 0
        while retry_count <= max_retries:
            stocks_df = self.get_pending_stocks(data_type)
            if not stocks_df:
                self.logger.info(f"✅ {data_type} 采集完成" if retry_count == 0 else f"✅ {data_type} 补采完成")
                return
            total = len(stocks_df)
            self.logger.info(f"第 {retry_count + 1} 轮：共 {total} 只股票待处理")
            success_count = 0
            
            for i, row in stocks_df.iterrows():
                stock_code = row['stock_code']
                last_update_date = row.get('last_update_date', '1990-01-01')
                
                try:
                    # 根据上次更新日期，计算需要采集的年份
                    years_to_fetch = self._get_years_to_fetch(last_update_date)
                    
                    if not years_to_fetch:
                        # 不需要采集新数据
                        success_count += 1
                        continue
                    
                    rows_inserted = 0
                    latest_date = None
                    
                    for year in years_to_fetch:
                        df = fetch_func(stock_code, year)
                        if not df.empty:
                            self.mysql_manager.batch_insert_or_update(
                                table_name, df, 
                                ['stock_code', 'statistic_date'] if 'statistic_date' in df.columns 
                                else ['stock_code', 'publish_date'] if 'publish_date' in df.columns 
                                else ['stock_code', 'announce_date']
                            )
                            rows_inserted += len(df)
                            if latest_date is None or df[date_field].max() > latest_date:
                                latest_date = df[date_field].max()
                        time.sleep(0.2)
                    
                    if rows_inserted > 0:
                        success_count += 1
                        self.update_record(stock_code, data_type, latest_date)
                        self.mark_as_processed(stock_code, data_type)
                    elif latest_date:
                        # 即使没有新数据，也更新记录（避免重复检查）
                        self.update_record(stock_code, data_type, latest_date)
                    
                    if (i + 1) % 50 == 0:
                        self.logger.info(f"已处理 {i+1}/{total}，成功 {success_count}")
                    if (i + 1) % 10 == 0:
                        time.sleep(0.3)
                        
                except Exception as e:
                    self.logger.error(f"处理 {stock_code} 失败：{e}")
            
            self.logger.info(f"本轮完成：成功 {success_count}/{total}")
            
            # 检查是否还有剩余
            remaining = self.get_pending_stocks(data_type)
            if not remaining:
                self.logger.info(f"✅ {data_type} 全部采集完成")
                return
            
            retry_count += 1
            if retry_count <= max_retries:
                self.logger.info(f"⚠️ 仍有 {len(remaining)} 只股票未处理，5 秒后重试...")
                time.sleep(5)
        
        self.logger.error(f"❌ 达到最大重试次数，{data_type} 采集结束")
    
    def fetch_profit_batch(self, max_retries=5):
        """批量采集利润表数据"""
        self._fetch_single_type_batch('profit', 'stock_profit_data', self.fetch_profit_data, 'publish_date', max_retries)
    
    def fetch_balance_batch(self, max_retries=5):
        """批量采集资产负债表数据"""
        self._fetch_single_type_batch('balance', 'stock_balance_data', self.fetch_balance_data, 'publish_date', max_retries)
    
    def fetch_cashflow_batch(self, max_retries=5):
        """批量采集现金流量表数据"""
        self._fetch_single_type_batch('cashflow', 'stock_cash_flow_data', self.fetch_cash_flow_data, 'publish_date', max_retries)
    
    def fetch_growth_batch(self, max_retries=5):
        """批量采集成长能力数据"""
        self._fetch_single_type_batch('growth', 'stock_growth_data', self.fetch_growth_data, 'publish_date', max_retries)
    
    def fetch_operation_batch(self, max_retries=5):
        """批量采集运营能力数据"""
        self._fetch_single_type_batch('operation', 'stock_operation_data', self.fetch_operation_data, 'publish_date', max_retries)
    
    def fetch_dupont_batch(self, max_retries=5):
        """批量采集杜邦分析数据"""
        self._fetch_single_type_batch('dupont', 'stock_dupont_data', self.fetch_dupont_data, 'publish_date', max_retries)
    
    def fetch_forecast_batch(self, max_retries=5):
        """批量采集业绩预告数据"""
        self._fetch_single_type_batch('forecast', 'stock_forecast_report', self.fetch_forecast_report, 'publish_date', max_retries)
    
    def fetch_dividend_batch(self, max_retries=5):
        """批量采集分红送配数据"""
        self._fetch_single_type_batch('dividend', 'stock_dividend_data', self.fetch_dividend_data, 'announce_date', max_retries)
    
    def run_full_collection(self):
        """运行完整的财务数据采集流程"""
        self.logger.info("=== 开始 Baostock 财务数据完整采集 ===")
        
        # 采集顺序：基础财务 → 能力分析 → 预告分红
        try:
            self.logger.info("\n[profit] 采集利润表...")
            self.fetch_profit_batch(max_retries=3)
        except Exception as e:
            self.logger.error(f"profit 采集中断：{e}")
        time.sleep(2)
        
        try:
            self.logger.info("\n[balance] 采集资产负债表...")
            self.fetch_balance_batch(max_retries=3)
        except Exception as e:
            self.logger.error(f"balance 采集中断：{e}")
        time.sleep(2)
        
        try:
            self.logger.info("\n[cashflow] 采集现金流量表...")
            self.fetch_cashflow_batch(max_retries=3)
        except Exception as e:
            self.logger.error(f"cashflow 采集中断：{e}")
        time.sleep(2)
        
        try:
            self.logger.info("\n[growth] 采集成长能力...")
            self.fetch_growth_batch(max_retries=3)
        except Exception as e:
            self.logger.error(f"growth 采集中断：{e}")
        time.sleep(2)
        
        try:
            self.logger.info("\n[operation] 采集运营能力...")
            self.fetch_operation_batch(max_retries=3)
        except Exception as e:
            self.logger.error(f"operation 采集中断：{e}")
        time.sleep(2)
        
        try:
            self.logger.info("\n[dupont] 采集杜邦分析...")
            self.fetch_dupont_batch(max_retries=3)
        except Exception as e:
            self.logger.error(f"dupont 采集中断：{e}")
        time.sleep(2)
        
        try:
            self.logger.info("\n[forecast] 采集业绩预告...")
            self.fetch_forecast_batch(max_retries=3)
        except Exception as e:
            self.logger.error(f"forecast 采集中断：{e}")
        time.sleep(2)
        
        try:
            self.logger.info("\n[dividend] 采集分红送配...")
            self.fetch_dividend_batch(max_retries=3)
        except Exception as e:
            self.logger.error(f"dividend 采集中断：{e}")
        
        self.logger.info("\n=== 财务数据采集完成 ===")
    
    def close(self):
        """关闭连接"""
        self.logout()
        self.mysql_manager.close()


# =====================================================
# 主程序入口
# =====================================================
if __name__ == '__main__':
    import sys
    
    fetcher = BaostockFinancialFetcher()
    
    if len(sys.argv) > 1:
        data_type = sys.argv[1]
        batch_methods = {
            'profit': fetcher.fetch_profit_batch,
            'balance': fetcher.fetch_balance_batch,
            'cashflow': fetcher.fetch_cashflow_batch,
            'growth': fetcher.fetch_growth_batch,
            'operation': fetcher.fetch_operation_batch,
            'dupont': fetcher.fetch_dupont_batch,
            'forecast': fetcher.fetch_forecast_batch,
            'dividend': fetcher.fetch_dividend_batch,
        }
        method = batch_methods.get(data_type)
        if method:
            method(max_retries=3)
        else:
            print(f"未知数据类型：{data_type}")
            print("支持的类型：profit, balance, cashflow, growth, operation, dupont, forecast, dividend")
    else:
        fetcher.run_full_collection()
    
    fetcher.close()

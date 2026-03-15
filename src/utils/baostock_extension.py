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
        
        # Redis key 格式：baostock:extension:stock_data:2026-03-15:unprocessed
        redis_key = f"baostock:{data_type}"
        
        # 1. 优先从 Redis 获取待处理股票（剩余的）
        pending = self.redis_manager.get_unprocessed_stocks(self.now_date, redis_key)
        
        if pending:
            # Redis 中有待处理股票，直接返回（断点续传）
            self.logger.info(f"📌 从 Redis 获取 {len(pending)} 只待处理股票（断点续传）")
            self.logger.debug(f"Redis key: {redis_key}:stock_data:{self.now_date}:unprocessed")
            return pending
        
        # 2. Redis 为空，从数据库获取并初始化（首次执行）
        stocks_df = self._get_pending_stocks_from_db()
        if stocks_df is not None and not stocks_df.empty:
            stock_list = stocks_df['stock_code'].tolist()
            self.redis_manager.add_unprocessed_stocks(stock_list, self.now_date, redis_key)
            self.logger.info(f"✅ Redis 初始化完成：{len(stock_list)}只股票（首次执行）")
            self.logger.debug(f"Redis key: {redis_key}:stock_data:{self.now_date}:unprocessed")
            return stocks_df
        
        # 3. 数据库也为空
        self.logger.info("⚠️ 未找到待采集股票")
        return None
    
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
        """标记股票为已处理（从 Redis unprocessed 集合中移除）"""
        if self.redis_manager is None:
            return
        
        # Redis key 格式：baostock:extension:stock_data:2026-03-15:unprocessed
        # remove_unprocessed_stocks 会自动拼接：{redis_key}:stock_data:{date}:unprocessed
        redis_key = f"baostock:{data_type}"
        # 从 unprocessed 集合中移除（表示已处理）
        self.redis_manager.remove_unprocessed_stocks([stock_code], self.now_date, redis_key)
        self.logger.debug(f"✅ {stock_code} 已从 Redis unprocessed 移除")
    
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
        """
        提取纯股票代码（去除市场前缀）
        :param code_with_market: 带市场前缀的代码，如 sh.601398
        :return: 纯股票代码，如 601398
        """
        if '.' in code_with_market:
            return code_with_market.split('.')[-1]
        return code_with_market
    
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
        运行完整的数据采集流程（财务数据 + 业绩预告，支持 Redis 断点续传和历史数据初始化）
        :param year: 年份，None 表示根据记录表自动判断
        :param quarter: 季度 (1-4)，None 表示全部季度
        """
        current_year = datetime.datetime.now().year
        
        self.logger.info("=== 开始扩展数据采集（支持断点续传）===")
        
        # 获取待采集的股票列表（从 Redis 或数据库）
        result = self.get_pending_stocks('extension')
        
        # 统一处理：可能是 list（Redis）或 DataFrame（数据库）
        if result is None:
            self.logger.warning("未找到待采集股票")
            return
        
        if isinstance(result, list):
            stock_list = result
        else:
            # DataFrame
            stock_list = result['stock_code'].tolist()
        
        total = len(stock_list)
        self.logger.info(f"待采集股票：{total} 只")
        
        success_count = 0
        
        # 1. 采集财务数据（利润表 + 资产负债表 + 现金流量表 + 成长 + 运营 + 杜邦）
        self.logger.info("\n[1/2] 采集财务数据...")
        for i, stock_code in enumerate(stock_list, 1):
            try:
                # 如果不指定年份，需要根据记录表判断采集范围
                if year is None:
                    # 从记录表获取该股票的上次更新时间
                    pure_code = self._get_stock_code(stock_code)
                    query = """
                    SELECT update_profit_date FROM stock_performance_update_record 
                    WHERE stock_code = %s
                    """
                    record = self.mysql_manager.query_all(query, [pure_code])
                    
                    if not record or not record[0]['update_profit_date']:
                        # 首次采集：遍历 2007 年到当前年（财务数据从 2007 年开始）
                        years_to_fetch = list(range(2007, current_year + 1))
                        self.logger.debug(f"{stock_code}: 首次采集，年份范围 2007-{current_year}")
                    else:
                        # 有记录：只采集更新后的年份
                        last_date = record[0]['update_profit_date']
                        # 处理默认值 1990-01-01 的情况
                        if last_date == '1990-01-01' or (isinstance(last_date, datetime.date) and last_date.year == 1990):
                            years_to_fetch = list(range(2007, current_year + 1))
                            self.logger.debug(f"{stock_code}: 默认日期 1990-01-01，采集年份范围 2007-{current_year}")
                        else:
                            last_year = last_date.year if isinstance(last_date, datetime.date) else datetime.datetime.strptime(last_date, '%Y-%m-%d').year
                            if last_year >= current_year:
                                years_to_fetch = [current_year]
                            else:
                                years_to_fetch = list(range(last_year + 1, current_year + 1))
                            self.logger.debug(f"{stock_code}: 上次更新 {last_date}，采集年份 {years_to_fetch}")
                else:
                    # 指定了年份，只采集指定年份
                    years_to_fetch = [year] if isinstance(year, int) else year
                
                # 遍历年份采集
                all_results = {}
                for fetch_year in years_to_fetch:
                    results = self.fetch_financial_data(stock_code, year=fetch_year, quarter=quarter)
                    # 合并结果
                    for table_name, df in results.items():
                        if not df.empty:
                            if table_name in all_results:
                                all_results[table_name] = pd.concat([all_results[table_name], df], ignore_index=True)
                            else:
                                all_results[table_name] = df
                
                # 写入数据库（只写入已存在的表）
                rows_inserted = 0
                table_mapping = {
                    'profit': 'stock_profit_data',
                    'balance': 'stock_balance_data',
                    'cashflow': 'stock_cash_flow_data',
                    'growth': 'stock_growth_data',
                    'operation': 'stock_operation_data',
                    'dupont': 'stock_dupont_data'
                }
                
                for table_name, df in all_results.items():
                    if not df.empty:
                        target_table = table_mapping.get(table_name)
                        if not target_table:
                            continue
                        
                        # 删除不需要的列（code 列）
                        if 'code' in df.columns:
                            df = df.drop(columns=['code'])
                        
                        # 检查表是否存在
                        check_query = """
                        SELECT table_name FROM information_schema.tables 
                        WHERE table_schema = 'stock' AND table_name = %s
                        """
                        table_exists = self.mysql_manager.query_all(check_query, [target_table])
                        
                        if not table_exists:
                            self.logger.warning(f"表 {target_table} 不存在，跳过 {table_name} 数据入库")
                            continue
                        
                        # 入库
                        try:
                            rows = self.mysql_manager.batch_insert_or_update(target_table, df, ['stock_code', 'statistic_date'])
                            rows_inserted += rows if rows else len(df)
                        except Exception as e:
                            self.logger.error(f"{pure_code}: {table_name} 入库失败：{e}")
                
                if rows_inserted > 0:
                    success_count += 1
                    self.mark_as_processed(stock_code, 'extension')
                    if i % 50 == 0:
                        self.logger.info(f"股票 {stock_code} 入库成功：{rows_inserted}条")
                
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

import time

import baostock as bs
import pandas as pd
from datetime import datetime, timedelta
from logs.logger import LogManager
from src.utils.redis_tool import RedisUtil
from src.utils.mysql_tool import MySQLUtil
from config.baostock_config import *
from src.utils import time_tool
from src.utils.time_tool import get_last_some_time


class BaostockFetcher:
    def __init__(self):
        self.login()
        self.redis_manager = RedisUtil()
        self.mysql_manager = MySQLUtil()
        self.mysql_manager.connect()
        self.bs_config = BAOSTOCK_CONFIG().get_config()
        self.now_date = datetime.now().strftime('%Y-%m-%d')
        self.logger = LogManager.get_logger("baostock_fetcher")

    def login(self):
        lg = bs.login()
        if lg.error_code != '0':
            raise Exception(f"Baostock login failed: {lg.error_msg}")

    def logout(self):
        bs.logout()

    def get_daily_type(self, date_type='d'):
        # 返回一个字典 默认字典是 update_column=update_stock_date date_files=date_stock_fields
        if date_type == 'w':
            return {
                'update_column': 'update_stock_week',
                'date_files': 'week_stock_fields',
                'update_table': 'stock_history_week_price',
                'files': get_stock_week_fields(),
                'frequency': 'week_frequency',
                'update_record_table': 'update_stock_record'
            }
        if date_type == 'm':
            return {
                'update_column': 'update_stock_month',
                'date_files': 'month_stock_fields',
                'update_table': 'stock_history_month_price',
                'files': get_stock_month_fields(),
                'frequency': 'month_frequency',
                'update_record_table': 'update_stock_record'
            }
        if date_type == 'km':
            return {
                'update_column': 'update_index_stock_month',
                'date_files': 'month_index_stock_fields',
                'update_table': 'index_stock_history_month_price',
                'files': get_index_stock_month_fields(),
                'frequency': 'month_frequency',
                'update_record_table': 'update_index_stock_record'
            }
        if date_type == 'kw':
            return {
                'update_column': 'update_index_stock_week',
                'date_files': 'week_index_stock_fields',
                'update_table': 'index_stock_history_week_price',
                'files': get_index_stock_week_fields(),
                'frequency': 'week_frequency',
                'update_record_table': 'update_index_stock_record'
            }
        if date_type == 'kd':
            return {
                'update_column': 'update_index_stock_date',
                'date_files': 'date_index_stock_fields',
                'update_table': 'index_stock_history_date_price',
                'files': get_index_stock_date_fields(),
                'frequency': 'day_frequency',
                'update_record_table': 'update_index_stock_record'
            }
        if date_type == 'min':
            return {
                'update_column': 'update_stock_min',
                'date_files': 'min_stock_fields',
                'update_table': 'stock_history_min_price',
                'files': get_stock_min_fields(),
                'frequency': 'min_frequency',
                'update_record_table': 'update_stock_record'
            }
        return {
            'update_column': 'update_stock_date',
            'date_files': 'date_stock_fields',
            'update_table': 'stock_history_date_price',
            'files': get_stock_daly_fields(),
            'frequency': 'day_frequency',
            'update_record_table': 'update_stock_record'
        }

    def fetch_daily_data(self, daily_type: dict, stock_code, start_date=None, end_date=None):
        """获取日线数据，支持断点续传"""
        code = stock_code[-6:]
        if not start_date:
            # 获取最后更新日期
            query_sql = f"SELECt CAST({daily_type['update_column']} as CHAR) as {daily_type['update_column']} FROM {daily_type['update_record_table']} WHERE stock_code = %s"
            last_update_date = self.mysql_manager.query_one(query_sql, code)
            last_update_date = last_update_date[daily_type['update_column']]
            if daily_type['date_files'] == 'min_stock_fields':
                start_date = get_last_some_time(30)
            else:
                if not last_update_date:
                    start_date = '1990-01-01'
                else:
                    start_date = last_update_date

        # 如果没有指定结束日期，使用当前日期作为结束日期
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')

        print(f"开始获取 {stock_code} 数据：{start_date} ~ {end_date}")
        rs = bs.query_history_k_data_plus(
            code=stock_code,
            fields=f"{self.bs_config[daily_type['date_files']]}",
            start_date=f'{start_date}',
            end_date=f'{end_date}',
            frequency=f"{self.bs_config[daily_type['frequency']]}",
            adjustflag=f"{self.bs_config['adjustflag']}"
        )

        # 关键：判断rs是否为None（接口调用失败）
        if rs is None:
            raise RuntimeError(f"调用Baostock接口失败：{stock_code}，日期：{start_date} ~ {end_date}")

        # 检查接口返回错误
        if rs.error_code != '0':
            raise RuntimeError(f"获取K线数据失败：{rs.error_msg}（股票代码：{stock_code}，日期：{start_date} ~ {end_date}）")

        data_list = []
        while (rs.error_code == '0') & rs.next():
            data_list.append(rs.get_row_data())

        df = pd.DataFrame(data_list, columns=rs.fields) \
            .rename(columns=daily_type['files']) \
            .replace(r'^\s*$', None, regex=True)
        if df.empty:
            self.logger.warning(f"股票 {stock_code} 获取数据为空 请求日期为 {start_date} ~ {end_date}")
        return df

    def batch_fetch_daily_data(self, stock_codes, date_type, update_record_table='update_stock_record'):
        """批量获取日线数据"""
        for stock_code in stock_codes:
            # 随机休眠3秒
            time.sleep(1)
            df = self.process_stock(stock_code, date_type, update_record_table)
            if not df.empty:
                print(f"股票 {stock_code} 处理完成")

    # 批量处理股票数据
    def batch_process_stock_data(self, date_type: str, update_record_table: str = 'update_stock_record'):
        # 更新股票信息
        self.update_stock_basic()
        self.update_stock_industry()
        # 获取待处理的股票代码
        pending_stocks = self.get_pending_stocks(date_type=date_type, update_record_table=update_record_table)
        # 批量处理股票数据
        self.batch_fetch_daily_data(pending_stocks, date_type, update_record_table)
        # 初始化股票周月日期数据
        self.init_stock_date_week_month()

    def get_pending_stocks(self, date_type: str, column_name: str = 'stock_code',
                           update_record_table: str = 'update_stock_record'):
        """从Redis中获取待处理的股票代码"""
        pending_stocks = self.redis_manager.get_unprocessed_stocks(self.now_date, date_type)
        if not pending_stocks:
            # 如果Redis中没有待处理的股票代码，从MySQL中获取
            pending_stocks = self.get_pending_stocks_from_mysql(update_record_table)
            self.redis_manager.add_unprocessed_stocks(pending_stocks[column_name].tolist(), self.now_date, date_type)
            # 把df转成列表
            pending_stocks = pending_stocks[column_name].tolist()
        return pending_stocks

    def get_pending_stocks_from_mysql(self, record_table='update_stock_record'):
        """从MySQL中获取待处理的股票代码"""
        query = f"SELECT a.stock_code as stock,a.market_type FROM {record_table} a join stock_basic b on a.stock_code = b.stock_code where b.stock_status = 1"
        result = self.mysql_manager.query_all(query, ())
        df = pd.DataFrame(result)
        df['stock_code'] = df['market_type'] + '.' + df['stock']
        return df

    # 不开多线程爬取 防止封IP
    def process_stock(self, stock_code, date_type='d', update_record_table='update_stock_record'):
        # 获取字典
        daily_type = self.get_daily_type(date_type)
        """处理单只股票的数据"""
        try:
            # 获取日线数据
            df = self.fetch_daily_data(daily_type, stock_code)
            if not df.empty:
                # 处理日线数据
                df['market_type'] = df['stock_code'].apply(lambda x: x[:2])
                df['stock_code'] = df['stock_code'].apply(lambda x: x[-6:])
                rows = self.mysql_manager.batch_insert_or_update(daily_type['update_table'], df,
                                                                 ['stock_code', 'stock_date'])
                if rows > 0:
                    print(f"股票 {stock_code} 插入数据库成功！")
                    self.update_stock_record(df['stock_code'].iloc[0], daily_type['update_column'],
                                             df['stock_date'].max(), update_record_table)
                    self.redis_manager.remove_unprocessed_stocks([stock_code], self.now_date, date_type)
                else:
                    self.logger.error(
                        f"股票 {stock_code} 插入{daily_type['update_table']}失败,插入日期：{df['stock_date'].min()} → {df['stock_date'].max()}")
            return df

        except Exception as e:
            print(f"股票 {stock_code} 处理失败: {e}")

    # 标记已处理股票
    def mark_stock_as_processed(self, stock_code, update_column, update_date, date_type):
        """标记股票为已处理"""
        query = f"UPDATE update_stock_record SET {update_column} = %s WHERE stock_code = %s"
        rows = self.mysql_manager.execute(query, (update_date, stock_code))
        if rows > 0:
            print(f"股票 {stock_code} 已处理!")
            if stock_code.startwith('00') or stock_code.startwith('30'):
                stock_code = 'sz.' + stock_code
            else:
                stock_code = 'sh.' + stock_code
            self.redis_manager.remove_unprocessed_stocks([stock_code], self.now_date, date_type)
        else:
            print(f"股票 {stock_code} 处理失败!")

    def close(self):
        """关闭连接"""
        self.logout()
        self.mysql_manager.close()

    # 更新股票行业信息
    def update_stock_industry(self):
        """更新股票行业信息"""
        rs = bs.query_stock_industry()

        # 检查接口返回错误
        if rs.error_code != '0':
            raise RuntimeError(f"获取行业数据失败：{rs.error_msg}")

        data_list = []
        while (rs.error_code == '0') & rs.next():
            data_list.append(rs.get_row_data())

        df = pd.DataFrame(data_list, columns=rs.fields) \
            .rename(columns=get_stock_industry_fields()) \
            .replace(r'^\s*$', None, regex=True)
        df['market_type'] = df['stock_code'].apply(lambda x: x[:2])
        df['stock_code'] = df['stock_code'].apply(lambda x: x[-6:])
        df['update_date'] = get_last_some_time(0)
        table_name = 'stock_industry'
        # 创建 SQLAlchemy 引擎
        self.mysql_manager.batch_insert_or_update(table_name, df, ['stock_code'])
        return df

    # 更新股票基础信息
    def update_stock_basic(self):
        # 获取行业分类数据
        rs = bs.query_stock_basic()
        data_list = []
        while (rs.error_code == '0') & rs.next():
            # 获取一条记录，将记录合并在一起
            data_list.append(rs.get_row_data())
        result = pd.DataFrame(data_list, columns=rs.fields)
        df = result.rename(columns={
            'code': 'stock_code',
            'code_name': 'stock_name',
            'ipoDate': 'ipo_date',
            'outDate': 'out_date',
            'type': 'stock_type',
            'status': 'stock_status'
        }).replace(r'^\s*$', None, regex=True)
        df['update_date'] = get_last_some_time(0)
        df['market_type'] = df['stock_code'].apply(lambda x: x[:2])
        df['stock_code'] = df['stock_code'].apply(lambda x: x[-6:])
        # # 使用 to_sql 方法将 DataFrame 写入数据库
        table_name = 'stock_basic'
        # 创建 SQLAlchemy 引擎
        self.mysql_manager.batch_insert_or_update(table_name, df, ['stock_code'])
        # 过滤掉df中状态stock_type不为1的数据 建立一个新的数据集
        stock_record = df[df['stock_type'] == '1']
        self.mysql_manager.batch_insert_or_update('update_stock_record',
                                                  stock_record[['stock_code', 'stock_name', 'market_type']],
                                                  ['stock_code'])
        stock_record = df[df['stock_type'].isin(['2', '5'])]
        self.mysql_manager.batch_insert_or_update('update_index_stock_record',
                                                  stock_record[
                                                      ['stock_code', 'stock_name', 'market_type', 'stock_type']],
                                                  ['stock_code'])
        return df

    def update_stock_record(self, stock_code, update_column, update_date, update_record_table='update_stock_record'):
        sql = f"UPDATE {update_record_table} SET {update_column} = %s WHERE stock_code = %s"
        rows = self.mysql_manager.execute(sql, (update_date, stock_code))
        if rows > 0:
            print(f"股票 {stock_code} 记录表更新成功!")
            return True
        else:
            self.logger.warning(f"股票 {stock_code} 记录表更新失败! 记录或已更新过！")
            return False

    # 计算非完整月股票月线价格
    def calculate_stock_month_price(self):
        """
        计算非完整月股票月线价格（修复%符号冲突+参数化时间+增强健壮性）
        """
        try:
            # 1. 提前计算时间参数（替代SQL中的CURRENT_DATE/CURRENT_TIME，增强灵活性）
            import datetime
            current_date = datetime.datetime.now().strftime("%Y-%m-%d")  # 当前日期

            self.logger.info("开始计算股票月线价格（非完整月）")

            # 2. 核心修复：转义%为%%，时间条件改为参数占位符%s
            calculate_sql = '''
            WITH month_open_price AS (
                SELECT a.stock_code, a.open_price, a.close_price, c.close_price last_close_price
                FROM stock.stock_history_date_price a
                JOIN (
                    SELECT MIN(stock_date) stock_date, stock_code
                    FROM stock.stock_history_date_price
                    WHERE DATE_FORMAT(stock_date, '%%Y-%%m') = DATE_FORMAT(%s, '%%Y-%%m')
                    GROUP BY stock_code
                ) b ON a.stock_date = b.stock_date AND a.stock_code = b.stock_code
                JOIN (
                    SELECT close_price, stock_code
                    FROM stock.stock_history_month_price
                    WHERE DATE_FORMAT(stock_date, '%%Y-%%m') = DATE_FORMAT(DATE_SUB(%s, INTERVAL 1 MONTH), '%%Y-%%m')
                ) c ON a.stock_code = c.stock_code
            ),
            month_close_price AS (
                SELECT a.stock_code, a.close_price, a.stock_date
                FROM stock.stock_history_date_price a
                JOIN (
                    SELECT MAX(stock_date) stock_date, stock_code
                    FROM stock.stock_history_date_price
                    WHERE DATE_FORMAT(stock_date, '%%Y-%%m') = DATE_FORMAT(%s, '%%Y-%%m')
                    GROUP BY stock_code
                ) b ON a.stock_date = b.stock_date AND a.stock_code = b.stock_code
            )
            SELECT 
                a.stock_code,
                c.stock_date,
                b.open_price,
                a.high_price,
                a.low_price,
                c.close_price,
                a.trading_volume,
                a.trading_amount,
                2 AS adjust_flag,
                a.turn,
                ROUND(((c.close_price - b.last_close_price)/b.last_close_price) * 100, 4) ups_and_downs,
                d.market_type
            FROM (
                SELECT 
                    stock_code,
                    SUM(trading_volume) trading_volume,
                    SUM(trading_amount) trading_amount,
                    MIN(low_price) low_price,
                    MAX(high_price) high_price,
                    SUM(turn) turn
                FROM stock.stock_history_date_price
                WHERE DATE_FORMAT(stock_date, '%%Y-%%m') = DATE_FORMAT(%s, '%%Y-%%m')
                GROUP BY stock_code
            ) a
            JOIN month_open_price b ON a.stock_code = b.stock_code
            JOIN month_close_price c ON a.stock_code = c.stock_code
            JOIN stock_basic d ON d.stock_code = a.stock_code AND d.stock_status = 1
            '''

            # 3. 构造参数列表（按SQL中%s的顺序传入）
            sql_params = (
                current_date,  # month_open_price子查询：当前月
                current_date,  # month_open_price关联子查询：上月（通过DATE_SUB计算）
                current_date,  # month_close_price子查询：当前月
                current_date  # 主聚合查询：当前月
            )

            # 4. 执行查询（传入参数，避免硬编码）
            result = self.mysql_manager.query_all(calculate_sql, sql_params)

            # 5. 空结果处理（优化：更严谨的空值判断）
            if not result or len(result) == 0:
                self.logger.warning("未查询到当月股票日线数据，跳过月线价格计算")
                return

            # 6. 转换为DataFrame并数据清洗
            df = pd.DataFrame(result)
            self.logger.debug(f"查询到 {len(df)} 只股票的当月日线数据")

            # 过滤空值行（避免后续映射失败）
            df = df.dropna(subset=['stock_date'])
            if df.empty:
                self.logger.warning("清洗后无有效月线数据，跳过入库")
                return

            # 构造更新用的DataFrame（重命名列）
            update_df = df[['stock_code', 'stock_date']].rename(
                columns={'stock_date': 'update_stock_month'}
            )
            # 7. 修正月最后交易日
            df['stock_date'] = df['stock_date'].map(time_tool.find_last_trading_day_of_month)

            # 8. 批量插入/更新月线表
            cnt = self.mysql_manager.batch_insert_or_update(
                table_name='stock_history_month_price',
                df=df,
                unique_keys=['stock_code', 'stock_date']  # 唯一键：股票代码+月最后交易日
            )

            # 9. 更新股票记录表里的月更新时间
            if cnt > 0:
                self.logger.info(f"成功写入 {cnt} 条月线数据到stock_history_month_price")
                # 批量更新记录
                update_cnt = self.mysql_manager.batch_insert_or_update(
                    table_name='update_stock_record',
                    df=update_df,
                    unique_keys=['stock_code']
                )
                self.logger.info(f"成功更新 {update_cnt} 条股票的月更新时间")
            else:
                self.logger.warning("无月线数据需要写入（可能数据已存在）")
        except Exception as e:
            self.logger.error("计算股票月线价格失败", exc_info=True)
            raise

    # 计算当前未完整周的收、开盘价以及涨跌幅度
    def calculate_stock_week_price(self, date_table='stock_history_date_price',
                                   week_table='stock_history_week_price'):
        """
        计算股票周线价格
        """
        try:
            # 1. 获取时间参数（提前计算，避免SQL中硬编码）
            today = time_tool.get_last_some_time(0)
            first_trade_week = time_tool.find_first_trading_day_of_week(today)
            last_trade_week = time_tool.find_last_trading_day_of_week(today)
            last_week_trade_day = time_tool.find_last_trading_day_of_week(
                time_tool.get_last_some_time(7))

            self.logger.info(f"开始计算股票周线价格，时间范围：{first_trade_week} ~ {last_trade_week}")

            # 2. 修复核心：SQL中的%替换为%%（转义），日期参数用%s占位（防注入）
            calculate_sql = f'''
                with week_open_price as (
                SELECT  a.stock_code,a.open_price,a.close_price,
                c.close_price last_close_price
                from stock.{date_table} a
                join (
                SELECT min(stock_date) stock_date,stock_code
                from stock.{date_table}
                where  date_format(stock_date,'%%Y-%%m-%%d') >= %s
                and date_format(stock_date,'%%Y-%%m-%%d') <= %s
                GROUP BY stock_code
                ) b on a.stock_date = b.stock_date
                and a.stock_code = b.stock_code
                join (
                SELECT close_price,stock_code
                from stock.{week_table}
                where date_format(stock_date,'%%Y-%%m-%%d') = %s
                ) c on a.stock_code = c.stock_code
                ),
                week_close_price as (
                SELECT a.stock_code,a.close_price,a.stock_date
                from stock.{date_table} a
                join (
                SELECT max(stock_date) stock_date,stock_code
                from stock.{date_table}
                where date_format(stock_date,'%%Y-%%m-%%d') >= %s
                and date_format(stock_date,'%%Y-%%m-%%d') <= %s
                GROUP BY stock_code
                ) b on a.stock_date = b.stock_date
                and a.stock_code = b.stock_code)
                select a.stock_code,c.stock_date,b.open_price,a.high_price,a.low_price,
                    c.close_price,a.trading_volume,a.trading_amount,
                    2 as adjust_flag,turn,round(((c.close_price - last_close_price)/last_close_price) * 100,4) ups_and_downs,
                    d.market_type
                from
                (SELECT stock_code,sum(trading_volume) trading_volume ,
                sum(trading_amount)trading_amount,min(low_price)low_price,
                max(high_price) high_price,sum(turn) turn
                from stock.{date_table}
                where date_format(stock_date,'%%Y-%%m-%%d') >= %s
                and date_format(stock_date,'%%Y-%%m-%%d') <= %s
                GROUP BY stock_code) a join
                week_open_price b on a.stock_code = b.stock_code
                join
                week_close_price c on a.stock_code = c.stock_code
                join stock_basic d on a.stock_code = d.stock_code;
            '''

            # 3. 构造参数（按SQL中%s的顺序传入，避免硬编码）
            sql_params = (
                first_trade_week, last_trade_week,  # week_open_price子查询
                last_week_trade_day,  # week_open_price关联子查询
                first_trade_week, last_trade_week,  # week_close_price子查询
                first_trade_week, last_trade_week  # 主聚合查询
            )

            # 4. 执行查询（传入参数，避免SQL注入）
            result = self.mysql_manager.query_all(calculate_sql, sql_params)
            # 5. 结果处理
            if not result:
                self.logger.warning("未查询到周线价格计算数据")
                return

            df = pd.DataFrame(result)
            self.logger.info(f"周线价格计算完成，共获取 {len(df)} 条数据")

        except Exception as e:
            self.logger.error("计算股票周线价格失败", exc_info=True)
            raise  # 可选：抛出异常让上层处理
        if len(df) == 0:
            return
        update_df = df[['stock_code', 'stock_date']].rename(
            columns={'stock_code': 'stock_code', 'stock_date': 'update_stock_week'})
        df['stock_date'] = df['stock_date'].map(time_tool.find_last_trading_day_of_week)
        cnt = self.mysql_manager.batch_insert_or_update('stock_history_week_price', df, ['stock_code', 'stock_date'])
        if cnt > 0:
            self.mysql_manager.batch_insert_or_update('update_stock_record', update_df, ['stock_code'])

    # 获取所有不同日期的股票类型
    def batch_process_stock_data_all_time_period(self):
        for time_period in ['d', 'w', 'm', 'kd']:
            if time_period == 'd':
                self.batch_process_stock_data(time_period)
            elif time_period == 'w':
                if time_tool.is_weekend(time_tool.get_last_some_time(0)):
                    self.batch_process_stock_data(time_period)
                else:
                    self.calculate_stock_week_price()
            elif time_period == 'kd':
                self.batch_process_stock_data(date_type='kd', update_record_table='update_index_stock_record')
                self.calculate_index_stock_week_price()
                self.calculate_index_stock_month_price()
            else:
                if time_tool.is_last_day_of_month(time_tool.get_last_some_time(0)):
                    self.batch_process_stock_data(time_period)
                else:
                    self.calculate_stock_month_price()

    # 计算股票交易日对应的周月日期
    def init_stock_date_week_month(self):
        sql = f'''
        select stock_date from stock_history_date_price group by stock_date;
        '''
        result = self.mysql_manager.query_all(sql)
        df = pd.DataFrame(result)
        df['stock_week_date'] = df['stock_date'].map(time_tool.find_last_trading_day_of_week)
        df['stock_month_date'] = df['stock_date'].map(time_tool.find_last_trading_day_of_month)
        if len(df) > 0:
            self.mysql_manager.batch_insert_or_update('stock_date_week_month', df, 'stock_date')

    def calculate_index_stock_week_price(self):
        """
        计算股票周线价格
        """
        try:
            # 1. 修复核心：SQL中的%替换为%%（转义），日期参数用%s占位（防注入）
            calculate_sql = f'''
                WITH weekly_data AS (
                    SELECT
                        a.stock_code,
                        a.market_type,
                        b.stock_week_date,
                        a.stock_date,
                        a.open_price,
                        a.high_price,
                        a.low_price,
                        a.close_price,
                        a.trading_volume,
                        a.trading_amount,
                        a.ups_and_downs,
                        c.stock_type
                    FROM
                        index_stock_history_date_price a
                    JOIN
                        stock_date_week_month b ON a.stock_date = b.stock_date
                    JOIN 
                        stock_basic c ON c.stock_code = a.stock_code and c.market_type = a.market_type
                ),
                weekly_agg AS (
                    SELECT
                        stock_code,
                        stock_week_date,
                        market_type,
                                stock_type,
                        MAX(high_price) AS high_price,
                        MIN(low_price) AS low_price,
                        SUM(trading_volume) AS trading_volume,
                        SUM(trading_amount) AS trading_amount
                    FROM
                        weekly_data
                    GROUP BY
                        stock_code,
                        stock_week_date,
                        market_type,
                                stock_type
                ),
                weekly_open_close AS (
                    SELECT
                        stock_code,
                        stock_week_date,
                        market_type,
                        FIRST_VALUE(open_price) OVER (
                            PARTITION BY stock_code, stock_week_date
                            ORDER BY stock_date
                        ) AS open_price,
                        LAST_VALUE(close_price) OVER (
                            PARTITION BY stock_code, stock_week_date
                            ORDER BY stock_date
                            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
                        ) AS close_price
                    FROM
                        weekly_data
                )
                SELECT
                    a.stock_code,
                    a.stock_week_date AS stock_date,
                    b.open_price,
                    a.high_price,
                    a.low_price,
                    b.close_price,
                    a.trading_volume,
                    a.trading_amount,
                    CASE
                        WHEN LAG(b.close_price) OVER (
                            PARTITION BY a.stock_code
                            ORDER BY a.stock_week_date
                        ) IS NULL THEN ((b.close_price - b.open_price) / b.open_price) * 100
                        ELSE (b.close_price - LAG(b.close_price) OVER (
                            PARTITION BY a.stock_code
                            ORDER BY a.stock_week_date
                        )) / LAG(b.close_price) OVER (
                            PARTITION BY a.stock_code
                            ORDER BY a.stock_week_date
                        ) * 100
                    END AS ups_and_downs,
                    a.market_type,
                    a.stock_type
                FROM
                    weekly_agg a
                JOIN
                    weekly_open_close b ON a.stock_code = b.stock_code AND a.stock_week_date = b.stock_week_date AND a.market_type = b.market_type
                GROUP BY
                    a.stock_code,
                    a.stock_week_date,
                    a.market_type,
                    b.open_price,
                    a.high_price,
                    a.low_price,
                    b.close_price,
                    a.trading_volume,
                    a.trading_amount
                ORDER BY
                    a.stock_week_date;
            '''

            # 4. 执行查询（传入参数，避免SQL注入）
            result = self.mysql_manager.query_all(calculate_sql, ())
            # 5. 结果处理
            if not result:
                self.logger.warning("未查询到周线价格计算数据")
                return

            df = pd.DataFrame(result)
            self.logger.info(f"周线价格计算完成，共获取 {len(df)} 条数据")

        except Exception as e:
            self.logger.error("计算股票周线价格失败", exc_info=True)
            raise  # 可选：抛出异常让上层处理
        if len(df) == 0:
            return
        update_df = df[['stock_code', 'stock_date', 'stock_type', 'market_type']].rename(
            columns={'stock_code': 'stock_code', 'stock_date': 'update_index_stock_week'})

        cnt = self.mysql_manager.batch_insert_or_update('index_stock_history_week_price',
                                                        df.drop(columns=['stock_type']),
                                                        ['stock_code', 'stock_date'])
        if cnt > 0:
            self.mysql_manager.batch_insert_or_update('update_index_stock_record', update_df, ['stock_code'])

    def calculate_index_stock_month_price(self):
        """
        计算股票月线价格
        """
        try:
            # 1. 修复核心：SQL中的%替换为%%（转义），日期参数用%s占位（防注入）
            calculate_sql = f'''
                WITH monthly_data AS (
                    SELECT
                        a.stock_code,
                        a.market_type,
                        b.stock_month_date,
                        a.stock_date,
                        a.open_price,
                        a.high_price,
                        a.low_price,
                        a.close_price,
                        a.trading_volume,
                        a.trading_amount,
                        a.ups_and_downs,
                        c.stock_type
                    FROM
                        index_stock_history_date_price a
                    JOIN
                        stock_date_week_month b ON a.stock_date = b.stock_date
                    JOIN
                        stock_basic c ON c.stock_code = a.stock_code and c.market_type = a.market_type
                ),
                monthly_agg AS (
                    SELECT
                        stock_code,
                        stock_month_date,
                        market_type,
                                stock_type,
                        MAX(high_price) AS high_price,
                        MIN(low_price) AS low_price,
                        SUM(trading_volume) AS trading_volume,
                        SUM(trading_amount) AS trading_amount
                    FROM
                        monthly_data
                    GROUP BY
                        stock_code,
                        stock_month_date,
                        market_type,
                                stock_type
                ),
                monthly_open_close AS (
                    SELECT
                        stock_code,
                        stock_month_date,
                        market_type,
                        FIRST_VALUE(open_price) OVER (
                            PARTITION BY stock_code, stock_month_date
                            ORDER BY stock_date
                        ) AS open_price,
                        LAST_VALUE(close_price) OVER (
                            PARTITION BY stock_code, stock_month_date
                            ORDER BY stock_date
                            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
                        ) AS close_price
                    FROM
                        monthly_data
                )
                SELECT
                    a.stock_code,
                    a.stock_month_date AS stock_date,
                    b.open_price,
                    a.high_price,
                    a.low_price,
                    b.close_price,
                    a.trading_volume,
                    a.trading_amount,
                    CASE
                        WHEN LAG(b.close_price) OVER (
                            PARTITION BY a.stock_code
                            ORDER BY a.stock_month_date
                        ) IS NULL THEN ((b.close_price - b.open_price) / b.open_price) * 100
                        ELSE (b.close_price - LAG(b.close_price) OVER (
                            PARTITION BY a.stock_code
                            ORDER BY a.stock_month_date
                        )) / LAG(b.close_price) OVER (
                            PARTITION BY a.stock_code
                            ORDER BY a.stock_month_date
                        ) * 100
                    END AS ups_and_downs,
                    a.market_type,
                    a.stock_type
                FROM
                    monthly_agg a
                JOIN
                    monthly_open_close b ON a.stock_code = b.stock_code AND a.stock_month_date = b.stock_month_date AND a.market_type = b.market_type
                GROUP BY
                    a.stock_code,
                    a.stock_month_date,
                    a.market_type,
                    b.open_price,
                    a.high_price,
                    a.low_price,
                    b.close_price,
                    a.trading_volume,
                    a.trading_amount
                ORDER BY
                    a.stock_month_date;
            '''

            # 4. 执行查询（传入参数，避免SQL注入）
            result = self.mysql_manager.query_all(calculate_sql, ())
            # 5. 结果处理
            if not result:
                self.logger.warning("未查询到周线价格计算数据")
                return

            df = pd.DataFrame(result)
            self.logger.info(f"周线价格计算完成，共获取 {len(df)} 条数据")

        except Exception as e:
            self.logger.error("计算股票周线价格失败", exc_info=True)
            raise  # 可选：抛出异常让上层处理
        if len(df) == 0:
            return
        update_df = df[['stock_code', 'stock_date', 'stock_type', 'market_type']].rename(
            columns={'stock_code': 'stock_code', 'stock_date': 'update_index_stock_month'})

        cnt = self.mysql_manager.batch_insert_or_update('index_stock_history_month_price',
                                                        df.drop(columns=['stock_type']),
                                                        ['stock_code', 'stock_date'])
        if cnt > 0:
            self.mysql_manager.batch_insert_or_update('update_index_stock_record', update_df, ['stock_code'])


if __name__ == '__main__':
    fetcher = BaostockFetcher()
    df = fetcher.process_stock(stock_code='sz.002080', date_type='min')
    print(df.to_string())
    fetcher.close()

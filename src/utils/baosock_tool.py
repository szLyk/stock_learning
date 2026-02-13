import time

import baostock as bs
import pandas as pd
from datetime import datetime, timedelta
from redis_tool import RedisUtil
from mysql_tool import MySQLUtil
from config.baostock_config import BAOSTOCK_CONFIG, get_stock_daly_fields, get_stock_industry_fields
from time_tool import get_last_some_time


class BaostockFetcher:
    def __init__(self):
        self.login()
        self.redis_manager = RedisUtil()
        self.redis_manager.connect()
        self.mysql_manager = MySQLUtil()
        self.mysql_manager.connect()
        self.bs_config = BAOSTOCK_CONFIG().get_config()
        self.now_date = datetime.now().strftime('%Y-%m-%d')

    def login(self):
        lg = bs.login()
        if lg.error_code != '0':
            raise Exception(f"Baostock login failed: {lg.error_msg}")

    def logout(self):
        bs.logout()

    def fetch_daily_data(self, stock_code, start_date=None, end_date=None):
        """获取日线数据，支持断点续传"""
        code = stock_code[-6:]
        if not start_date:
            # 获取最后更新日期
            query_sql = "SELECt CAST(update_stock_date as CHAR) as update_stock_date FROM update_stock_record WHERE stock_code = %s"
            last_update_date = self.mysql_manager.query_one(query_sql, code)
            last_update_date = last_update_date['update_stock_date']
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
            fields=self.bs_config['stock_fields'],
            start_date=f'{start_date}',
            end_date=f'{end_date}',
            frequency=self.bs_config['day_frequency'],
            adjustflag=self.bs_config['adjustflag']
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
            .rename(columns=get_stock_daly_fields()) \
            .replace(r'^\s*$', None, regex=True)
        return df

    def batch_fetch_daily_data(self, stock_codes):
        """批量获取日线数据"""
        for stock_code in stock_codes:
            # 随机休眠3秒
            time.sleep(3)
            df = self.process_stock(stock_code)
            if not df.empty:
                print(f"股票 {stock_code} 处理完成")

    # 批量处理股票数据
    def batch_process_stock_data(self):
        while True:
            # 获取待处理的股票代码
            pending_stocks = self.get_pending_stocks()
            # 批量处理股票数据
            self.batch_fetch_daily_data(pending_stocks)

    def get_pending_stocks(self):
        """从Redis中获取待处理的股票代码"""
        pending_stocks = self.redis_manager.get_unprocessed_stocks(self.now_date)
        if not pending_stocks:
            # 如果Redis中没有待处理的股票代码，从MySQL中获取
            pending_stocks = self.get_pending_stocks_from_mysql()
            self.redis_manager.add_unprocessed_stocks(pending_stocks['stock_code'].tolist(), self.now_date)
            # 把df转成列表
            pending_stocks = pending_stocks['stock_code'].tolist()
        return pending_stocks

    def get_pending_stocks_from_mysql(self):
        """从MySQL中获取待处理的股票代码"""
        query = f"SELECT stock_code as stock,market_type FROM update_stock_record;"
        result = self.mysql_manager.query_all(query, ())
        df = pd.DataFrame(result)
        df['stock_code'] = df['market_type'] + '.' + df['stock']
        return df

    def process_stock(self, stock_code):
        """处理单只股票的数据"""
        try:
            # 获取日线数据
            df = self.fetch_daily_data(stock_code)
            # 处理日线数据
            df['market_type'] = df['stock_code'].apply(lambda x: x[:2])
            df['stock_code'] = df['stock_code'].apply(lambda x: x[-6:])
            self.mysql_manager.batch_insert_or_update('stock_history_date_price', df, ['stock_code', 'stock_date'])
            self.redis_manager.remove_unprocessed_stocks([stock_code], self.now_date)
            print(f"股票 {stock_code} 处理完成")
            return df
        except Exception as e:
            print(f"股票 {stock_code} 处理失败: {e}")

    def mark_stock_as_processed(self, stock_code, update_column, update_date):
        """标记股票为已处理"""
        query = f"UPDATE update_stock_record SET {update_column} = %s WHERE stock_code = %s"
        rows = self.mysql_manager.execute(query, (update_date, stock_code))
        if rows > 0:
            print(f"股票 {stock_code} 已处理!")
            if stock_code.startwith('00') or stock_code.startwith('30'):
                stock_code = 'sz.' + stock_code
            else:
                stock_code = 'sh.' + stock_code
            self.redis_manager.remove_unprocessed_stocks([stock_code], self.now_date)
        else:
            print(f"股票 {stock_code} 处理失败!")

    def close(self):
        """关闭连接"""
        self.logout()
        self.mysql_manager.close()

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
        record = df[df['stock_type'] == '1']
        self.mysql_manager.batch_insert_or_update('update_stock_record',
                                                  record[['stock_code', 'stock_name', 'market_type']],
                                                  ['stock_code'])
        return df

    def update_stock_record(self, stock_code, update_column, update_date):
        sql = f"UPDATE update_stock_record SET {update_column} = %s WHERE stock_code = %s"
        rows = self.mysql_manager.execute(sql, (update_date, stock_code))
        if rows > 0:
            print(f"股票 {stock_code} 已处理!")
        else:
            print(f"股票 {stock_code} 处理失败!")


if __name__ == '__main__':
    fetcher = BaostockFetcher()
    fetcher.batch_process_stock_data()
    fetcher.close()

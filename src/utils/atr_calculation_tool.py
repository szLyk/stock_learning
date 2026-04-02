"""
ATR 指标计算工具（支持日/周/月多周期）
使用 TA-Lib 库计算 ATR 指标
"""

import threading
import datetime
import time
from concurrent.futures import as_completed, ThreadPoolExecutor

import numpy as np
import pandas as pd
import talib

from config.Indicator_config import INDICATOR_CONFIG
from logs.logger import LogManager
from src.utils.baosock_tool import BaostockFetcher
from src.utils.mysql_tool import MySQLUtil
from src.utils.redis_tool import RedisUtil


class ATRCalculator:
    """ATR 指标计算器（支持日/周/月多周期）"""

    def __init__(self):
        self.redis_manager = RedisUtil()
        self.logger = LogManager.get_logger("atr_calculation")
        self.now_date = datetime.datetime.now().strftime('%Y-%m-%d')
        self.indicator_config = INDICATOR_CONFIG()

    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """
        使用 TA-Lib 计算 ATR 指标
        :param df: 包含 OHLC 数据的 DataFrame
        :param period: ATR 周期，默认 14
        :return: 包含 ATR 的 DataFrame
        """
        try:
            high = df['high_price'].values.astype(np.float64)
            low = df['low_price'].values.astype(np.float64)
            close = df['close_price'].values.astype(np.float64)

            # 使用 TA-Lib 计算 TR（真实波动幅度）
            df['tr'] = talib.TRANGE(high, low, close)

            # 使用 TA-Lib 计算 ATR（平均真实波动幅度）
            df['atr'] = talib.ATR(high, low, close, timeperiod=period)

            # 使用 TA-Lib 计算 NATR（归一化 ATR，便于跨股票比较）
            df['natr'] = talib.NATR(high, low, close, timeperiod=period)

            self.logger.info(f"ATR 计算完成，周期={period}")

        except Exception as e:
            self.logger.error(f"计算 ATR 时出错：{e}")

        return df

    def process_single_stock_atr(self, stock_code: str, daily_type: dict):
        """
        增量计算单只股票的 ATR（每个线程使用独立连接）
        :param stock_code: 股票代码
        :param daily_type: 计算周期配置
        """
        # 每个线程使用独立的数据库连接（线程安全）
        with MySQLUtil() as mysql_manager:
            try:
                update_table = daily_type['update_table']
                update_column = daily_type['update_column']
                update_record_table = daily_type['update_record_table']
                data_table = daily_type['data_table']
                tradestatus = daily_type.get('tradestatus', '')
                frequency = daily_type.get('frequency', 14)

                # 1. 获取该股票上次计算 ATR 的日期
                query_last = f"""
                    SELECT {update_column}
                    FROM {update_record_table}
                    WHERE stock_code = %s
                """
                last_result = mysql_manager.query_all(query_last, (stock_code,))
                last_date = str(last_result[0][update_column]) if last_result and len(last_result) > 0 else '1990-01-01'

                # 2. 确定需要查询的数据范围（多取 period 天作为缓冲）
                start_date_for_query = (
                        datetime.datetime.strptime(last_date, '%Y-%m-%d') -
                        datetime.timedelta(days=frequency * 2)
                ).strftime('%Y-%m-%d')

                # 3. 查询历史数据
                query_data = f"""
                    SELECT stock_code, stock_date, high_price, low_price, close_price
                    FROM {data_table}
                    WHERE stock_code = %s
                      {tradestatus}
                      AND stock_date >= %s
                    ORDER BY stock_date ASC
                """
                result = mysql_manager.query_all(query_data, [stock_code, start_date_for_query])

                if not result:
                    self.logger.warning(f"股票 {stock_code} 无有效数据")
                    return 0

                df = pd.DataFrame(result,
                                  columns=['stock_code', 'stock_date', 'high_price', 'low_price', 'close_price'])

                if df.empty:
                    self.logger.warning(f"股票 {stock_code} 无有效交易数据")
                    return 0

                # 检查数据量是否足够
                if len(df) < frequency:
                    self.logger.info(f"股票 {stock_code} 数据不足{frequency}天（{len(df)}天），无法计算 ATR，跳过")
                    return 0

                # 4. 计算 ATR
                df = self.calculate_atr(df, period=frequency)

                # 5. 只保留 > last_date 的新数据
                df['stock_date'] = pd.to_datetime(df['stock_date'])
                last_dt = pd.to_datetime(last_date)
                new_df = df[df['stock_date'] > last_dt].copy()

                if new_df.empty:
                    self.logger.info(f"股票 {stock_code} 无需更新 ATR（已计算到 {last_date}）")
                    return 0

                # 6. 清理无效值（TA-Lib 前 N 天返回 NaN）
                final_df = new_df[['stock_code', 'stock_date', 'tr', 'atr', 'natr']].copy()
                final_df = final_df.dropna(subset=['atr'], how='any').reset_index(drop=True)

                if final_df.empty:
                    self.logger.info(f"股票 {stock_code} 计算 ATR 后无有效数据")
                    return 0

                # 替换 NaN 为 None（MySQL 兼容）
                final_df = final_df.replace({np.nan: None})

                # 7. 入库（使用闭包捕获 mysql_manager）
                cnt = mysql_manager.batch_insert_or_update(
                    table_name=update_table,
                    df=final_df,
                    unique_keys=['stock_code', 'stock_date']
                )

                if cnt > 0:
                    max_date = final_df['stock_date'].max()

                    # 更新记录表
                    sql = f"""
                        INSERT INTO {update_record_table} (stock_code, {update_column})
                        VALUES (%s, %s)
                        ON DUPLICATE KEY UPDATE {update_column} = VALUES({update_column})
                    """
                    mysql_manager.execute(sql, (stock_code, max_date))
                    self.logger.info(f"✅ 股票 {stock_code} 新增 {cnt} 条 ATR，更新至 {max_date}")
                    return cnt

                return 0

            except Exception as e:
                self.logger.error(f"❌ 股票 {stock_code} ATR 计算失败：{e}", exc_info=True)
                return 0

    def run_batch_atr_multithread(self, max_workers: int = 6, date_type='d', max_auto_retries=10):
        """
        多线程批量计算 ATR，支持自动重试直到 Redis 清空
        :param max_workers: 线程数
        :param date_type: 周期类型 ('d' 日线，'w' 周线，'m' 月线)
        :param max_auto_retries: 最大自动重试轮数
        """
        daily_type = self.indicator_config.get_atr_type(date_type)
        redis_key = f'atr:{date_type}'
        retry_count = 0

        while retry_count <= max_auto_retries:
            stock = BaostockFetcher()
            if retry_count == 0:
                stock_codes = stock.get_pending_stocks(redis_key, 'stock')
            else:
                stock_codes = stock.redis_manager.get_unprocessed_stocks(self.now_date, redis_key)

            self.logger.info(f"第 {retry_count} 轮重试：正在处理股票 ATR")

            if not stock_codes:
                if retry_count == 0:
                    self.logger.warning("未找到有效股票数据")
                else:
                    self.logger.info("✅ 所有待处理股票 ATR 已计算完毕")
                return

            total = len(stock_codes)
            if retry_count == 0:
                self.logger.info(f"启动多线程 ATR 计算，共 {total} 只股票，线程数：{max_workers}")
            else:
                self.logger.info(f"第 {retry_count + 1} 轮重试：仍有 {total} 只股票待处理")

            success_count = 0
            fail_count = 0

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(self.process_single_stock_atr, stock_code, daily_type): stock_code
                    for stock_code in stock_codes
                }

                for future in as_completed(futures):
                    stock_code = futures[future]
                    try:
                        cnt = future.result()
                        if cnt > 0:
                            success_count += 1
                        else:
                            fail_count += 1
                    except Exception as e:
                        self.logger.error(f"股票 {stock_code} ATR 计算异常：{e}")
                        fail_count += 1

            self.logger.info(f"ATR 计算完成：成功{success_count}只，失败{fail_count}只")

            if fail_count == 0 or retry_count >= max_auto_retries:
                self.logger.info(f"ATR 计算结束，退出重试循环")
                break

            retry_count += 1
            time.sleep(1)

        self.logger.info("ATR 批量计算完成")

    def calculate_all_stocks_atr(self, date_type='d'):
        """
        计算所有股票的 ATR（不使用 Redis，直接遍历所有股票）
        :param date_type: 周期类型 ('d' 日线，'w' 周线，'m' 月线)
        """
        daily_type = self.indicator_config.get_atr_type(date_type)

        # 获取所有股票列表（使用独立连接）
        with MySQLUtil() as mysql_manager:
            query_stocks = """
                SELECT DISTINCT stock_code
                FROM stock_history_date_price
                WHERE tradestatus = 1
            """
            stocks_result = mysql_manager.query_all(query_stocks)
            stocks = [stock['stock_code'] for stock in stocks_result] if stocks_result else []

        self.logger.info(f"开始计算 {len(stocks)} 只股票的 ATR 指标（{date_type}线）")

        success_count = 0
        fail_count = 0

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {
                executor.submit(self.process_single_stock_atr, stock_code, daily_type): stock_code
                for stock_code in stocks
            }

            for future in as_completed(futures):
                try:
                    cnt = future.result()
                    if cnt > 0:
                        success_count += 1
                except Exception as e:
                    self.logger.error(f"股票 {futures[future]} ATR 计算异常：{e}")
                    fail_count += 1

        self.logger.info(f"ATR 计算完成：成功{success_count}只，失败{fail_count}只")


# 便捷函数
def calculate_atr_for_stock(stock_code: str, date_type='d'):
    """
    计算单只股票的 ATR
    :param stock_code: 股票代码
    :param date_type: 周期类型
    """
    calculator = ATRCalculator()
    daily_type = calculator.indicator_config.get_atr_type(date_type)
    calculator.process_single_stock_atr(stock_code, daily_type)


def calculate_atr_for_all_stocks(date_type='d'):
    """
    计算所有股票的 ATR
    :param date_type: 周期类型
    """
    calculator = ATRCalculator()
    calculator.calculate_all_stocks_atr(date_type)


def run_batch_ma_all_time_period():
    """批量处理所有时间段"""
    for date_type in ['d', 'w', 'm']:
        calculate_atr_for_all_stocks(date_type=date_type)


if __name__ == '__main__':
    # 测试：计算所有股票的日线 ATR
    print("开始计算日线 ATR...")
    calculate_atr_for_all_stocks(date_type='d')

    # 测试：计算所有股票的周线 ATR
    print("开始计算周线 ATR...")
    calculate_atr_for_all_stocks(date_type='w')

    # 测试：计算所有股票的月线 ATR
    print("开始计算月线 ATR...")
    calculate_atr_for_all_stocks(date_type='m')

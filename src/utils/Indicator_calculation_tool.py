import threading
from concurrent.futures import as_completed
from concurrent.futures.thread import ThreadPoolExecutor
import time  # ✅ 正确：time.sleep() 可用
import datetime  # 如果需要 datetime，单独导入

import numpy as np
import pandas as pd
from dateutil.relativedelta import relativedelta

from config.Indicator_config import INDICATOR_CONFIG
from logs.logger import LogManager
from src.utils.baosock_tool import BaostockFetcher
from src.utils.mysql_tool import MySQLUtil
from src.utils.redis_tool import RedisUtil


# 指标计算
class IndicatorCalculator:
    def __init__(self):
        self.redis_manager = RedisUtil()
        self.redis_manager.connect()
        self.mysql_manager = MySQLUtil()
        self.mysql_manager.connect()
        self.ma_windows = [3, 5, 6, 7, 9, 10, 12, 20, 24, 26, 30, 60, 70, 125, 250]
        self.logger = LogManager.get_logger("indicator_calculation")
        self.now_date = datetime.datetime.now().strftime('%Y-%m-%d')
        self.indicator_config = INDICATOR_CONFIG()

    def _execute_with_deadlock_retry(self, func, max_retries=3):
        """
        执行数据库写操作，遇到 MySQL 死锁 (1213) 自动重试。
        :param func: 无参可调用对象，执行具体的数据库操作并返回结果
        :param max_retries: 最大重试次数（含首次）
        :return: func() 的返回值
        """
        for attempt in range(max_retries):
            try:
                return func()
            except Exception as e:
                error_msg = str(e)
                # 检查是否为 MySQL 死锁错误 (1213)
                if "Deadlock found" in error_msg or "(1213," in error_msg:
                    if attempt < max_retries - 1:
                        # 指数退避：0.1s, 0.2s, 0.4s...
                        sleep_time = 0.1 * (2 ** attempt)
                        time.sleep(sleep_time)
                        # 确保回滚当前事务（清理连接状态）
                        if hasattr(self, 'mysql_manager') and self.mysql_manager.conn:
                            self.mysql_manager.conn.rollback()
                        continue
                # 非死锁错误 或 重试耗尽，直接抛出
                raise

    def calculate_moving_averages(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算各种均线
        :param df: 包含收盘价数据的DataFrame
        :return: 包含均线数据的DataFrame
        """
        try:
            # 计算各种均线
            df['stock_ma3'] = df['close_price'].rolling(window=3).mean()
            df['stock_ma5'] = df['close_price'].rolling(window=5).mean()
            df['stock_ma6'] = df['close_price'].rolling(window=6).mean()
            df['stock_ma7'] = df['close_price'].rolling(window=7).mean()
            df['stock_ma9'] = df['close_price'].rolling(window=9).mean()
            df['stock_ma10'] = df['close_price'].rolling(window=10).mean()
            df['stock_ma12'] = df['close_price'].rolling(window=12).mean()
            df['stock_ma20'] = df['close_price'].rolling(window=20).mean()
            df['stock_ma24'] = df['close_price'].rolling(window=24).mean()
            df['stock_ma26'] = df['close_price'].rolling(window=26).mean()
            df['stock_ma30'] = df['close_price'].rolling(window=30).mean()
            df['stock_ma60'] = df['close_price'].rolling(window=60).mean()
            df['stock_ma70'] = df['close_price'].rolling(window=70).mean()
            df['stock_ma125'] = df['close_price'].rolling(window=125).mean()
            df['stock_ma250'] = df['close_price'].rolling(window=250).mean()

        except Exception as e:
            self.logger.error(f"计算均线时出错: {e}")

        return df

    def process_single_stock(self, stock_code: str, daily_type: dict):
        """
        增量计算单只股票的均线
        :param daily_type: 计算周期配置
        :param stock_code: 股票代码
        """

        try:
            # 1. 获取该股票上次计算到的日期
            query_last = f"""
                SELECT {daily_type['update_column']} 
                FROM update_stock_record 
                WHERE stock_code = %s
            """
            last_result = self.mysql_manager.query_all(query_last, (stock_code,))
            last_date = str(last_result[0][daily_type['update_column']]) if last_result else '1990-01-01'

            # 2. 确定需要查询的数据范围（多取250天作为缓冲）
            start_date_for_query = (datetime.datetime.strptime(last_date, '%Y-%m-%d') -
                                    relativedelta(years=daily_type['frequency'])).strftime(
                '%Y-%m-%d')
            # 3. 查询足够历史数据
            query_data = f"""
                SELECT stock_code, stock_date, close_price
                FROM {daily_type['data_table']} 
                WHERE stock_code = %s 
                  {daily_type['tradestatus']}
                  AND stock_date >= %s
            """
            result = self.mysql_manager.query_all(query_data, [stock_code, start_date_for_query])
            df = pd.DataFrame(result, columns=['stock_code', 'stock_date', 'close_price'])

            if df.empty:
                self.logger.warning(f"股票 {stock_code} 无有效交易数据")
                return 0

            # 4. 计算均线（自动处理不足天数）
            df = self.calculate_moving_averages(df)

            # 5. 只保留 > last_date 的新数据
            df['stock_date'] = pd.to_datetime(df['stock_date'])
            last_dt = pd.to_datetime(last_date)
            new_df = df[df['stock_date'] >= last_dt].copy()

            if new_df.empty:
                self.logger.info(f"股票 {stock_code} 无需更新（已计算到 {last_date}）")
                return 0

            # 6. 入库均线数据
            def _do_batch_insert():
                return self.mysql_manager.batch_insert_or_update(
                    daily_type['update_table'],
                    new_df,
                    ['stock_code', 'stock_date']
                )

            cnt = self._execute_with_deadlock_retry(_do_batch_insert)
            if cnt > 0:
                # 7. 更新记录表
                max_new_date = new_df['stock_date'].max()

                def _do_update_record():
                    update_sql = f"""
                        INSERT INTO update_stock_record (stock_code, {daily_type['update_column']})
                        VALUES (%s, %s)
                        ON DUPLICATE KEY UPDATE {daily_type['update_column']} = VALUES({daily_type['update_column']})
                    """
                    return self.mysql_manager.execute(update_sql, (stock_code, max_new_date))

                self._execute_with_deadlock_retry(_do_update_record)
                self.logger.info(f"✅ 股票 {stock_code} 新增 {cnt} 条均线，更新至 {max_new_date}")
                return cnt
            else:
                return 0

        except Exception as e:
            self.logger.error(f"❌ 处理股票 {stock_code} 失败: {e}", exc_info=True)
            return 0

    def close(self):
        """关闭连接"""
        self.mysql_manager.close()

    def run_batch_ma_multithread(self, max_workers: int = 8, date_type='d', max_auto_retries=10):
        """
        多线程批量计算均线（支持自动重试直到 Redis 清空）
        :param max_workers: 线程数
        :param date_type: 周期类型 ('d', 'w', 'm')
        :param max_auto_retries: 最大自动重试轮数（防死循环，默认10轮）
        """
        daily_type = self.indicator_config.get_ma_type(date_type)
        redis_key = f'average:{date_type}'
        now_day = datetime.datetime.now().strftime('%Y-%m-%d')
        retry_count = 0

        while retry_count <= max_auto_retries:
            stock = BaostockFetcher()
            if retry_count == 0:
                stock_codes = stock.get_pending_stocks(redis_key, 'stock')
            else:
                stock_codes = stock.redis_manager.get_unprocessed_stocks(now_day, redis_key)

            if not stock_codes:
                if retry_count == 0:
                    self.logger.warning("未找到有效股票数据")
                else:
                    self.logger.info("✅ 所有待处理股票已计算完毕，均线任务结束")
                return

            total = len(stock_codes)
            if retry_count == 0:
                self.logger.info(f"启动多线程均线计算，共 {total} 只股票，线程数: {max_workers}")
            else:
                self.logger.info(f"第 {retry_count + 1} 轮重试：仍有 {total} 只股票待处理")

            def worker(stock_code):
                """每个线程独立处理一只股票"""
                processor = None
                try:
                    processor = IndicatorCalculator()
                    rows = processor.process_single_stock(stock_code, daily_type)
                    if rows > 0:
                        processor.redis_manager.remove_unprocessed_stocks([stock_code], self.now_date, redis_key)
                except Exception as e:
                    self.logger.error(f"[线程{threading.get_ident()}] 股票 {stock_code} 均线计算失败: {e}",
                                      exc_info=True)
                finally:
                    if processor:
                        processor.close()

            # 启动线程池执行本轮任务
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(worker, code) for code in stock_codes]
                for i, _ in enumerate(as_completed(futures), 1):
                    if i % 50 == 0 or i == total:
                        self.logger.info(f"已完成 {i}/{total} 只股票")

            # 本轮结束，准备检查是否还有剩余
            retry_count += 1

            # 再次检查 Redis 是否清空
            stock_codes_after = self.redis_manager.get_unprocessed_stocks(now_day, redis_key)
            if not stock_codes_after:
                self.logger.info("✅ 所有股票处理完成，均线任务结束")
                return

            # 如果还有剩余且未达最大重试次数，则等待后继续
            if retry_count <= max_auto_retries:
                wait_seconds = 5
                self.logger.info(
                    f"⚠️ 仍有 {len(stock_codes_after)} 只股票未处理，{wait_seconds} 秒后启动第 {retry_count + 1} 轮...")
                time.sleep(wait_seconds)
            else:
                self.logger.error(
                    f"❌ 达到最大重试轮数 ({max_auto_retries})，仍有 {len(stock_codes_after)} 只股票MA未处理，任务终止")
                return

    # 计算所有时间段的均线
    def run_batch_ma_all_time_period(self):
        """批量处理所有时间段"""
        for date_type in ['d', 'w', 'm']:
            self.run_batch_ma_multithread(date_type=date_type)

    # 计算MACD
    def process_single_stock_macd(self, stock_code: str, daily_type: dict):
        """
        处理单只股票的MACD计算（线程安全版本）

        :param stock_code: 股票代码
        :param daily_type: 字典表
        :return: 是否成功计算
        """
        update_column = daily_type['update_column']
        data_table = daily_type['data_table']
        update_table = daily_type['update_table']

        try:
            # 2. 获取更新日期
            last_date_sql = f"SELECT {update_column} FROM update_stock_record WHERE stock_code = %s"
            last_date = self.mysql_manager.query_one(last_date_sql, (stock_code,))[update_column]
            if str(last_date) == '1990-01-01':
                sql = f"""
                SELECT min(stock_date) as min_stock_date
                FROM stock.{data_table}
                WHERE stock_code = %s
                """
                last_date = self.mysql_manager.query_one(sql, (stock_code,))['min_stock_date']

            # 4. 获取需要计算的数据（更新日期之后）
            price_sql = f"""
            SELECT stock_code, stock_date, close_price
            FROM stock.{data_table}
            WHERE stock_code = %s
              AND stock_date >= %s
            ORDER BY stock_date
            """
            price_df = self.mysql_manager.query_all(price_sql, (stock_code, last_date))
            if not price_df:
                return 0

            # 5. 转换为DataFrame
            price_df = pd.DataFrame(price_df, columns=['stock_code', 'stock_date', 'close_price'])
            price_df['stock_date'] = pd.to_datetime(price_df['stock_date'])

            # 6. 获取更新日期当天的MACD状态（用于增量计算）
            status_sql = f"""
            SELECT ema_12, ema_26, dea, diff, macd
            FROM stock.{update_table}
            WHERE stock_code = %s AND stock_date = %s
            """
            status = self.mysql_manager.query_one(status_sql, (stock_code, last_date))
            status_dict = {
                'ema_12': status['ema_12'],
                'ema_26': status['ema_26'],
                'dea': status['dea'],
                'diff': status['diff'],
                'macd': status['macd']
            } if status else {}

            alpha_12 = 2 / (1 + 12)
            alpha_26 = 2 / (1 + 26)
            alpha_9 = 2 / (1 + 9)

            # 7. 计算MACD（核心逻辑）
            # 向量化计算函数
            def calculate_macd(group):
                code = group['stock_code'].iloc[0]
                group = group.sort_values(by='stock_date', ascending=True).reset_index(drop=True)

                closes = group['close_price'].astype(float).values
                dates = group['stock_date'].values

                # 初始化数组
                n = len(closes)
                ema12 = np.empty(n)
                ema26 = np.empty(n)
                diff = np.empty(n)
                dea = np.empty(n)
                macd = np.empty(n)

                # 判断初始化状态
                if not status_dict:
                    # 全新初始化
                    ema12[0] = ema26[0] = group['close_price'].iloc[0]
                    diff[0] = dea[0] = 0.0
                else:
                    # 增量计算
                    ema12[0] = status['ema_12']
                    ema26[0] = status['ema_26']
                    diff[0] = status['diff']
                    dea[0] = status['dea']
                    macd[0] = status.get('macd')

                # 向量化迭代计算
                for i in range(1, n):
                    ema12[i] = alpha_12 * closes[i] + (1 - alpha_12) * ema12[i - 1]
                    ema26[i] = alpha_26 * closes[i] + (1 - alpha_26) * ema26[i - 1]
                    diff[i] = ema12[i] - ema26[i]
                    dea[i] = alpha_9 * diff[i] + (1 - alpha_9) * dea[i - 1]
                    macd[i] = (diff[i] - dea[i]) * 2

                return pd.DataFrame({
                    'stock_code': code,
                    'stock_date': dates,
                    'close_price': closes,
                    'ema_12': ema12,
                    'ema_26': ema26,
                    'diff': diff,
                    'dea': dea,
                    'macd': macd
                })

            # 8. 执行计算
            macd_df = calculate_macd(price_df)
            if macd_df.empty:
                return 0

            # 9. 批量入库
            def _do_batch_insert():
                return self.mysql_manager.batch_insert_or_update(
                    table_name=update_table,
                    df=macd_df,
                    unique_keys=['stock_code', 'stock_date']
                )

            rows = self._execute_with_deadlock_retry(_do_batch_insert)

            # 10. 更新记录表
            if rows > 0:
                max_date = macd_df['stock_date'].max()

                def _do_update_record():
                    update_sql = f"""
                    INSERT INTO update_stock_record (stock_code, {update_column})
                    VALUES (%s, %s)
                    ON DUPLICATE KEY UPDATE {update_column} = VALUES({update_column})
                    """
                    return self.mysql_manager.execute(update_sql, (stock_code, max_date.strftime('%Y-%m-%d')))

                self._execute_with_deadlock_retry(_do_update_record)
                self.logger.info(f"✅ 股票 {stock_code} 新增 {rows} 条MACD，更新至 {max_date}")
                return rows
            return 0

        except Exception as e:
            self.logger.error(f"MACD计算失败 [股票: {stock_code}]: {str(e)}", exc_info=True)
            return 0

    def run_batch_macd_multithread(self, max_workers: int = 4, date_type='d', max_auto_retries=10):
        """
        多线程批量计算MACD（支持自动重试直到 Redis 清空）
        :param max_workers: 线程数
        :param date_type: 周期类型 ('d', 'w', 'm')
        :param max_auto_retries: 最大自动重试轮数（防死循环）
        """
        daily_type = self.indicator_config.get_macd_type(date_type)
        redis_key = f'macd:{date_type}'
        now_day = datetime.datetime.now().strftime('%Y-%m-%d')
        retry_count = 0

        while retry_count <= max_auto_retries:
            stock = BaostockFetcher()
            if retry_count == 0:
                stock_codes = stock.get_pending_stocks(redis_key, 'stock')
            else:
                stock_codes = stock.redis_manager.get_unprocessed_stocks(now_day, redis_key)

            if not stock_codes:
                if retry_count == 0:
                    self.logger.warning("未找到有效股票数据")
                else:
                    self.logger.info("✅ 所有待处理股票已计算完毕，MACD任务结束")
                return  # 正常退出

            total = len(stock_codes)
            if retry_count == 0:
                self.logger.info(f"启动多线程MACD计算，共 {total} 只股票，线程数: {max_workers}")
            else:
                self.logger.info(f"第 {retry_count + 1} 轮重试：仍有 {total} 只股票待处理")

            def worker(stock_code):
                """每个线程独立处理一只股票"""
                processor = None
                try:
                    processor = IndicatorCalculator()
                    rows = processor.process_single_stock_macd(stock_code, daily_type)
                    if rows > 0:
                        processor.redis_manager.remove_unprocessed_stocks([stock_code], self.now_date, redis_key)
                except Exception as e:
                    self.logger.error(f"[线程{threading.get_ident()}] 股票 {stock_code} MACD计算失败: {e}",
                                      exc_info=True)
                finally:
                    if processor:
                        processor.close()

            # 启动线程池执行本轮任务
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(worker, code) for code in stock_codes]
                for i, _ in enumerate(as_completed(futures), 1):
                    if i % 50 == 0 or i == total:
                        self.logger.info(f"已完成 {i}/{total} 只股票")

            # 本轮结束，准备下一轮检查
            retry_count += 1

            # 再次检查是否还有剩余
            stock_codes_after = self.redis_manager.get_unprocessed_stocks(now_day, redis_key)
            if not stock_codes_after:
                self.logger.info("✅ 所有股票处理完成，MACD任务结束")
                return

            # 如果还有剩余且未达最大重试次数，则等待后继续
            if retry_count <= max_auto_retries:
                wait_seconds = 5
                self.logger.info(
                    f"⚠️ 仍有 {len(stock_codes_after)} 只股票未处理，{wait_seconds} 秒后启动第 {retry_count + 1} 轮...")
                time.sleep(wait_seconds)
            else:
                self.logger.error(
                    f"❌ 达到最大重试轮数 ({max_auto_retries})，仍有 {len(stock_codes_after)} 只股票MACD未处理，任务终止")
                # 可选：发送告警、写监控指标等
                return

    # 计算所有时间段的MACD
    def run_batch_macd_all_time_period(self):
        """批量处理所有时间段"""
        for date_type in ['d', 'w', 'm']:
            self.run_batch_macd_multithread(date_type=date_type)

    # 计算布林线
    def process_single_stock_boll(self, stock_code: str, daily_type: dict) -> int:
        """
        处理单只股票的BOLL计算（线程安全 + 死锁重试）
        """
        update_column = daily_type['update_column']
        data_table = daily_type['data_table']
        update_table = daily_type['update_table']
        moving_table = daily_type['ma_table']  # 应该是已计算好的 MA 表
        trade_status = daily_type['tradestatus']
        frequency = daily_type['frequency']

        try:
            # 1. 获取上次更新日期
            last_date_sql = f"SELECT {update_column} FROM update_stock_record WHERE stock_code = %s"
            last_result = self.mysql_manager.query_one(last_date_sql, (stock_code,))
            last_date = last_result[update_column] if last_result else '1990-01-01'

            if str(last_date) == '1990-01-01':
                sql = f"SELECT MIN(stock_date) AS min_stock_date FROM stock.{data_table} WHERE stock_code = %s"
                min_result = self.mysql_manager.query_one(sql, (stock_code,))
                last_date = min_result['min_stock_date'] if min_result else '1990-01-01'

            start_date_for_query = (datetime.datetime.strptime(str(last_date), '%Y-%m-%d') -
                                    relativedelta(months=frequency)).strftime(
                '%Y-%m-%d')
            # 2. 查询所需数据（需 join MA20）
            price_sql = f"""
                SELECT a.stock_code, a.stock_date, a.close_price, b.stock_ma20
                FROM (
                    SELECT stock_code, stock_date, close_price
                    FROM stock.{data_table}
                    WHERE stock_code = %s AND stock_date >= %s {trade_status}
                ) a
                JOIN stock.{moving_table} b
                  ON a.stock_code = b.stock_code AND a.stock_date = b.stock_date
                ORDER BY a.stock_date
            """
            raw_data = self.mysql_manager.query_all(price_sql, (stock_code, start_date_for_query))
            if not raw_data:
                return 0

            df = pd.DataFrame(raw_data, columns=['stock_code', 'stock_date', 'close_price', 'stock_ma20'])
            df['stock_date'] = pd.to_datetime(df['stock_date'])

            # 4. 向量化计算 BOLL（使用总体标准差 ddof=0）
            close_prices = df['close_price'].values.astype(np.float64)
            n = len(close_prices)
            window = 20
            num_std = 2

            if n < window:
                # 不足20天，无法计算有效BOLL
                return 0

            # 使用 pandas rolling 更简洁（且自动对齐）
            series = pd.Series(close_prices)
            ma20 = series.rolling(window=window, min_periods=window).mean()
            std20 = series.rolling(window=window, min_periods=window).std(ddof=0)  # ← 关键：ddof=0

            upper = ma20 + num_std * std20
            lower = ma20 - num_std * std20

            # 对齐到原 DataFrame
            df['boll_twenty'] = ma20.values
            df['upper_rail'] = upper.values
            df['lower_rail'] = lower.values

            # 去掉前19个 NaN
            new_df = df.dropna(subset=['upper_rail']).copy()
            if new_df.empty:
                return 0
            # 3. 只处理 > last_date 的新数据（避免重复）
            last_dt = pd.to_datetime(last_date)
            final_df = new_df[new_df['stock_date'] >= last_dt].copy()
            if final_df.empty:
                return 0

            # 5. 入库（带死锁重试）
            def _do_insert():
                return self.mysql_manager.batch_insert_or_update(
                    table_name=update_table,
                    df=final_df[['stock_code', 'stock_date', 'boll_twenty', 'upper_rail', 'lower_rail']],
                    unique_keys=['stock_code', 'stock_date']
                )

            cnt = self._execute_with_deadlock_retry(_do_insert)

            if cnt > 0:
                max_date = final_df['stock_date'].max()

                def _do_update():
                    sql = f"""
                        INSERT INTO update_stock_record (stock_code, {update_column})
                        VALUES (%s, %s)
                        ON DUPLICATE KEY UPDATE {update_column} = VALUES({update_column})
                    """
                    return self.mysql_manager.execute(sql, (stock_code, max_date))

                self._execute_with_deadlock_retry(_do_update)
                self.logger.info(f"✅ 股票 {stock_code} 新增 {cnt} 条BOLL，更新至 {max_date}")
                return cnt

            return 0

        except Exception as e:
            self.logger.error(f"❌ 处理股票 {stock_code} BOLL失败: {e}", exc_info=True)
            return 0

    def run_batch_boll_multithread(self, max_workers: int = 4, date_type='d', max_auto_retries=10):
        """
        多线程批量计算BOLL（布林线），支持自动重试直到 Redis 清空
        :param max_workers: 线程数
        :param date_type: 周期类型 ('d' 日线, 'w' 周线, 'm' 月线)
        :param max_auto_retries: 最大自动重试轮数（防死循环）
        """
        daily_type = self.indicator_config.get_boll_type(date_type)  # 假设您有 get_boll_type 方法
        redis_key = f'boll:{date_type}'
        now_day = datetime.datetime.now().strftime('%Y-%m-%d')
        retry_count = 0

        while retry_count <= max_auto_retries:
            stock = BaostockFetcher()
            if retry_count == 0:
                stock_codes = stock.get_pending_stocks(redis_key, 'stock')
            else:
                stock_codes = stock.redis_manager.get_unprocessed_stocks(now_day, redis_key)

            self.logger.info(f"第 {retry_count} 轮重试：正在处理股票BOLL")

            if not stock_codes:
                if retry_count == 0:
                    self.logger.warning("未找到有效股票数据")
                else:
                    self.logger.info("✅ 所有待处理股票BOLL已计算完毕")
                return

            total = len(stock_codes)
            if retry_count == 0:
                self.logger.info(f"启动多线程BOLL计算，共 {total} 只股票，线程数: {max_workers}")
            else:
                self.logger.info(f"第 {retry_count + 1} 轮重试：仍有 {total} 只股票待处理")

            def worker(stock_code):
                """每个线程独立处理一只股票"""
                processor = None
                try:
                    # ✅ 创建全新实例（避免连接共享）
                    processor = IndicatorCalculator()
                    if retry_count > 0:
                        sql = f"SELECT COUNT(*) AS cnt FROM stock.{daily_type['data_table']} WHERE stock_code = %s"
                        result = processor.mysql_manager.query_one(sql, (stock_code,))
                        cnt = result['cnt'] if result else 0
                        if cnt < 20:
                            self.logger.info(f"股票 {stock_code} 交易日不满20天 无法计算布林线，跳过")
                            processor.redis_manager.remove_unprocessed_stocks([stock_code], self.now_date, redis_key)
                            return
                    rows = processor.process_single_stock_boll(stock_code, daily_type)
                    if rows > 0:
                        processor.redis_manager.remove_unprocessed_stocks([stock_code], self.now_date, redis_key)
                except Exception as e:
                    self.logger.error(f"[线程{threading.get_ident()}] 股票 {stock_code} BOLL计算失败: {e}",
                                      exc_info=True)
                finally:
                    if processor:
                        processor.close()  # 关闭子线程的 DB/Redis 连接

            # 启动线程池执行本轮任务
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(worker, code) for code in stock_codes]
                for i, _ in enumerate(as_completed(futures), 1):
                    if i % 50 == 0 or i == total:
                        self.logger.info(f"已完成 {i}/{total} 只股票")

            # 检查是否还有剩余任务
            retry_count += 1
            remaining = self.redis_manager.get_unprocessed_stocks(now_day, redis_key)

            if not remaining:
                self.logger.info("✅ 所有BOLL任务处理完成")
                return

            if retry_count <= max_auto_retries:
                wait_sec = 5
                self.logger.info(f"⚠️ 仍有 {len(remaining)} 只股票未处理，{wait_sec} 秒后启动第 {retry_count + 1} 轮...")
                time.sleep(wait_sec)
            else:
                self.logger.error(f"❌ 达到最大重试轮数 ({max_auto_retries})，仍有 {len(remaining)} 只股票BOLL未处理")
                return

    # 计算所有时间段的BOLL
    def run_batch_boll_all_time_period(self):
        """批量处理所有时间段"""
        for date_type in ['d', 'w', 'm']:
            self.run_batch_boll_multithread(date_type=date_type)

    def process_single_stock_obv(self, stock_code: str, daily_type: dict) -> int:
        """
        处理单只股票的 OBV 与 MAOBV 计算（线程安全 + 死锁重试）
        """
        update_column = daily_type['update_column']
        data_table = daily_type['data_table']
        update_table = daily_type['update_table']
        trade_status = daily_type['tradestatus']

        try:
            # 2. 查询所需数据（按日期排序）
            price_sql = f"""
                SELECT stock_code, stock_date, close_price, open_price, trading_volume
                FROM stock.{data_table}
                WHERE stock_code = %s 
                ORDER BY stock_date
            """
            raw_data = self.mysql_manager.query_all(price_sql, (stock_code,))
            if not raw_data:
                return 0

            df = pd.DataFrame(raw_data)

            # 数据清洗与类型转换
            for col in ['open_price', 'close_price', 'trading_volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')

            df = df.dropna(subset=['close_price', 'trading_volume']).copy()
            df['stock_date'] = pd.to_datetime(df['stock_date'])

            # 确保按日期排序（即使SQL已排序，双重保险）
            df = df.sort_values('stock_date').reset_index(drop=True)

            if df.empty:
                return 0

            # === 核心：标准 OBV 计算（无需分组！）===
            # 1. 计算价格变化方向（与前一日比较）
            price_diff = df['close_price'].diff()
            direction = np.sign(price_diff)

            # 2. 首日特殊处理：OBV[0] = trading_volume[0]
            direction[0] = 0  # 首日无比较，方向设为0（但OBV值需单独赋值）

            # 3. 计算带符号的成交量
            signed_volume = direction * df['trading_volume']

            # 4. 累计 OBV（首日需修正）
            obv = signed_volume.cumsum()
            obv.iloc[0] = df['trading_volume'].iloc[0]  # 关键修正：首日 OBV = 首日成交量

            # 5. 添加 OBV 列
            df['obv'] = obv

            # 6. 计算 30日 MAOBV（需30天数据）
            df['30ma_obv'] = df['obv'].rolling(window=30, min_periods=30).mean()

            # 7. 只保留有效数据（MAOBV 有值的行）
            final_df = df[['stock_code', 'stock_date', 'obv', '30ma_obv']].copy()
            final_df = final_df[final_df['30ma_obv'].notna()].copy()

            if final_df.empty:
                return 0

            # 9. 入库（只处理新数据）
            def _do_insert():
                return self.mysql_manager.batch_insert_or_update(
                    table_name=update_table,
                    df=final_df[['stock_code', 'stock_date', 'obv', '30ma_obv']],
                    unique_keys=['stock_code', 'stock_date']
                )

            cnt = self._execute_with_deadlock_retry(_do_insert)

            if cnt > 0:
                max_date = final_df['stock_date'].max()

                def _do_update():
                    sql = f"""
                        INSERT INTO update_stock_record (stock_code, {update_column})
                        VALUES (%s, %s)
                        ON DUPLICATE KEY UPDATE {update_column} = VALUES({update_column})
                    """
                    return self.mysql_manager.execute(sql, (stock_code, max_date))

                self._execute_with_deadlock_retry(_do_update)
                self.logger.info(f"✅ 股票 {stock_code} 新增 {cnt} 条 OBV，更新至 {max_date}")
                return cnt

            return 0
        except Exception as e:
            self.logger.error(f"❌ 处理股票 {stock_code} OBV 失败: {e}", exc_info=True)
            return 0

    def run_batch_obv_multithread(self, max_workers: int = 4, date_type='d', max_auto_retries=10):
        """
        多线程批量计算OBV（能量潮），支持自动重试直到Redis清空
        :param max_workers: 线程数
        :param date_type: 周期类型 ('d' 日线, 'w' 周线, 'm' 月线)
        :param max_auto_retries: 最大自动重试轮数（防死循环）
        """
        # 获取OBV配置（与BOLL类似，但需确保配置正确）
        daily_type = self.indicator_config.get_obv_type(date_type)  # 确保有这个方法
        redis_key = f'obv:{date_type}'
        now_day = datetime.datetime.now().strftime('%Y-%m-%d')
        retry_count = 0

        while retry_count <= max_auto_retries:
            stock = BaostockFetcher()
            if retry_count == 0:
                stock_codes = stock.get_pending_stocks(redis_key, 'stock')
            else:
                stock_codes = stock.redis_manager.get_unprocessed_stocks(now_day, redis_key)

            self.logger.info(f"第 {retry_count} 轮重试：正在处理股票OBV")

            if not stock_codes:
                if retry_count == 0:
                    self.logger.warning("未找到有效股票数据")
                else:
                    self.logger.info("✅ 所有待处理股票OBV已计算完毕")
                return

            total = len(stock_codes)
            if retry_count == 0:
                self.logger.info(f"启动多线程OBV计算，共 {total} 只股票，线程数: {max_workers}")
            else:
                self.logger.info(f"第 {retry_count + 1} 轮重试：仍有 {total} 只股票待处理")

            def worker(stock_code):
                """每个线程独立处理一只股票（线程安全）"""
                processor = None
                try:
                    # ✅ 创建全新IndicatorCalculator实例（避免连接共享）
                    processor = IndicatorCalculator()

                    # ✅ 重要：检查数据量（OBV需要至少30个交易日计算MAOBV）
                    sql = f"SELECT COUNT(*) AS cnt FROM stock.{daily_type['data_table']} WHERE stock_code = %s"
                    result = processor.mysql_manager.query_one(sql, (stock_code,))
                    cnt = result['cnt'] if result else 0

                    if cnt < 30:  # OBV需要30日数据
                        processor.logger.info(f"股票 {stock_code} 交易日不足30天（{cnt}天），无法计算OBV，跳过")
                        processor.redis_manager.remove_unprocessed_stocks([stock_code], self.now_date, redis_key)
                        return

                    # ✅ 执行OBV计算（使用标准逻辑）
                    rows = processor.process_single_stock_obv(stock_code, daily_type)
                    if rows > 0:
                        processor.redis_manager.remove_unprocessed_stocks([stock_code], self.now_date, redis_key)

                except Exception as e:
                    # ✅ 使用processor的日志（而非self.logger）
                    processor.logger.error(f"[线程{threading.get_ident()}] 股票 {stock_code} OBV计算失败: {e}",
                                           exc_info=True)
                finally:
                    if processor:
                        processor.close()  # 关闭子线程的DB/Redis连接

            # 启动线程池执行本轮任务
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(worker, code) for code in stock_codes]
                for i, _ in enumerate(as_completed(futures), 1):
                    if i % 50 == 0 or i == total:
                        self.logger.info(f"✅ 已完成 {i}/{total} 只股票OBV计算")

            # 检查是否还有剩余任务
            retry_count += 1
            remaining = self.redis_manager.get_unprocessed_stocks(now_day, redis_key)

            if not remaining:
                self.logger.info("✅ 所有OBV任务处理完成")
                return

            if retry_count <= max_auto_retries:
                wait_sec = 5
                self.logger.info(f"⚠️ 仍有 {len(remaining)} 只股票未处理，{wait_sec}秒后启动第 {retry_count + 1} 轮...")
                time.sleep(wait_sec)
            else:
                self.logger.error(f"❌ 达到最大重试轮数 ({max_auto_retries})，仍有 {len(remaining)} 只股票OBV未处理")
                return

    # 计算所有时间段的OBV
    def run_batch_obv_all_time_period(self):
        """批量处理所有时间段"""
        for date_type in ['d', 'w', 'm']:
            self.run_batch_obv_multithread(date_type=date_type)

    def compute_all_rsi(self, close_prices, windows=[6, 12, 24]):
        n = len(close_prices)
        if n == 0:
            return {f'rsi_{window}': np.array([]) for window in windows}

        delta = np.zeros(n)
        delta[1:] = np.diff(close_prices)

        gain = np.where(delta > 0, delta, 0.0)
        loss = np.where(delta < 0, -delta, 0.0)

        rsis = {}

        for window in windows:
            if n < window:
                rsi = np.full(n, np.nan)
            else:
                avg_gain = np.zeros(n)
                avg_loss = np.zeros(n)

                # 初始SMA（第window-1天）
                start = window - 1
                avg_gain[start] = np.mean(gain[:window])
                avg_loss[start] = np.mean(loss[:window])

                alpha = (window - 1) / window
                beta = 1 / window

                # 从第window天开始计算EMA（原代码为range(window, n)）
                for i in range(window, n):
                    avg_gain[i] = avg_gain[i - 1] * alpha + gain[i] * beta
                    avg_loss[i] = avg_loss[i - 1] * alpha + loss[i] * beta

                rs = np.divide(avg_gain, avg_loss, out=np.zeros_like(avg_gain), where=avg_loss != 0)
                rsi = 100 - (100 / (1 + rs))
                rsi[:window - 1] = np.nan  # 仅前window-1天无效

            rsis[f'rsi_{window}'] = rsi

        return rsis

    # 处理RSI
    def process_single_stock_rsi(self, stock_code: str, daily_type: dict) -> int:
        """
        处理单只股票的 RSI 计算（线程安全 + 增量更新）
        """
        update_column = daily_type['update_column']
        data_table = daily_type['data_table']
        update_table = daily_type['update_table']
        trade_status = daily_type['tradestatus']
        frequency = daily_type['frequency']

        try:
            # 1. 获取上次更新日期（关键：必须使用增量查询）
            last_date_sql = f"SELECT {update_column} FROM update_stock_record WHERE stock_code = %s"
            last_result = self.mysql_manager.query_one(last_date_sql, (stock_code,))
            last_date = last_result[update_column] if last_result else '1990-01-01'
            start_date_for_query = (datetime.datetime.strptime(str(last_date), '%Y-%m-%d') -
                                    relativedelta(months=frequency)).strftime(
                '%Y-%m-%d')

            # 2. 查询增量数据（必须包含 stock_date >= last_date）
            price_sql = f"""
                SELECT stock_code, stock_date, close_price
                FROM stock.{data_table}
                WHERE stock_code = %s 
                  AND stock_date >= %s 
                  {trade_status}
                ORDER BY stock_date
            """
            raw_data = self.mysql_manager.query_all(price_sql, (stock_code, start_date_for_query))
            if not raw_data:
                return 0

            df = pd.DataFrame(raw_data)
            if df.empty:
                return 0

            # 数据清洗与类型转换
            df['close_price'] = pd.to_numeric(df['close_price'], errors='coerce')
            df = df.dropna(subset=['close_price']).copy()
            df['stock_date'] = pd.to_datetime(df['stock_date'])
            df = df.sort_values('stock_date').reset_index(drop=True)

            # ✅ 关键修正：检查数据量（RSI需要至少6天）
            if len(df) < 6:
                self.logger.info(f"股票 {stock_code} 交易日不足6天（{len(df)}天），无法计算RSI，跳过")
                return 0

            # 3. 计算RSI（使用标准方法）
            close_prices = df['close_price'].values.astype(float)
            # 调用RSI计算（假设已实现 compute_all_rsi）
            rsis = self.compute_all_rsi(close_prices, windows=[6, 12, 24])

            # 4. 添加RSI列到DataFrame
            for window in [6, 12, 24]:
                df[f'rsi_{window}'] = rsis[f'rsi_{window}']

            # 5. 准备入库数据（只保留有效RSI值）
            final_df = df[['stock_code', 'stock_date', 'rsi_6', 'rsi_12', 'rsi_24']].copy()
            # 将NaN替换为None（数据库兼容性）
            final_df = final_df.replace({np.nan: None})

            # 6. 入库（关键：使用batch_insert_or_update）
            def _do_insert():
                return self.mysql_manager.batch_insert_or_update(
                    table_name=update_table,
                    df=final_df,
                    unique_keys=['stock_code', 'stock_date']
                )

            cnt = self._execute_with_deadlock_retry(_do_insert)

            if cnt > 0:
                max_date = final_df['stock_date'].max()

                # 更新更新记录
                def _do_update():
                    sql = f"""
                        INSERT INTO update_stock_record (stock_code, {update_column})
                        VALUES (%s, %s)
                        ON DUPLICATE KEY UPDATE {update_column} = VALUES({update_column})
                    """
                    return self.mysql_manager.execute(sql, (stock_code, max_date))

                self._execute_with_deadlock_retry(_do_update)
                self.logger.info(f"✅ 股票 {stock_code} 新增 {cnt} 条 RSI，更新至 {max_date}")
                return cnt

            return 0

        except Exception as e:
            self.logger.error(f"❌ 处理股票 {stock_code} RSI 失败: {e}", exc_info=True)
            return 0

    # 批量处理RSI
    def run_batch_rsi_multithread(self, max_workers: int = 6, date_type='d', max_auto_retries=10):
        """
        多线程批量计算RSI（相对强弱指标），支持自动重试直到Redis清空
        :param max_workers: 线程数
        :param date_type: 周期类型 ('d' 日线, 'w' 周线, 'm' 月线)
        :param max_auto_retries: 最大自动重试轮数（防死循环）
        """
        # 获取RSI配置（与BOLL类似，但需确保有get_rsi_type方法）
        daily_type = self.indicator_config.get_rsi_type(date_type)
        redis_key = f'rsi:{date_type}'
        now_day = datetime.datetime.now().strftime('%Y-%m-%d')
        retry_count = 0

        while retry_count <= max_auto_retries:
            stock = BaostockFetcher()
            if retry_count == 0:
                stock_codes = stock.get_pending_stocks(redis_key, 'stock')
            else:
                stock_codes = stock.redis_manager.get_unprocessed_stocks(now_day, redis_key)

            self.logger.info(f"第 {retry_count} 轮重试：正在处理股票RSI")

            if not stock_codes:
                if retry_count == 0:
                    self.logger.warning("未找到有效股票数据")
                else:
                    self.logger.info("✅ 所有待处理股票RSI已计算完毕")
                return

            total = len(stock_codes)
            if retry_count == 0:
                self.logger.info(f"启动多线程RSI计算，共 {total} 只股票，线程数: {max_workers}")
            else:
                self.logger.info(f"第 {retry_count + 1} 轮重试：仍有 {total} 只股票待处理")

            def worker(stock_code):
                """每个线程独立处理一只股票（线程安全）"""
                processor = None
                try:
                    # ✅ 创建全新IndicatorCalculator实例（避免连接共享）
                    processor = IndicatorCalculator()

                    # ✅ 检查数据量（RSI需要至少6天，不是BOLL的20天！）
                    sql = f"SELECT COUNT(*) AS cnt FROM stock.{daily_type['data_table']} WHERE stock_code = %s"
                    result = processor.mysql_manager.query_one(sql, (stock_code,))
                    cnt = result['cnt'] if result else 0

                    if cnt < 6:  # ✅ RSI最小窗口=6天
                        processor.logger.info(f"股票 {stock_code} 交易日不足6天（{cnt}天），无法计算RSI，跳过")
                        processor.redis_manager.remove_unprocessed_stocks([stock_code], self.now_date, redis_key)
                        return

                    # ✅ 执行RSI计算（使用标准逻辑）
                    rows = processor.process_single_stock_rsi(stock_code, daily_type)
                    if rows > 0:
                        processor.redis_manager.remove_unprocessed_stocks([stock_code], self.now_date, redis_key)

                except Exception as e:
                    # ✅ 使用processor.logger（而非self.logger）记录错误
                    processor.logger.error(f"[线程{threading.get_ident()}] 股票 {stock_code} RSI计算失败: {e}",
                                           exc_info=True)
                finally:
                    if processor:
                        processor.close()  # 关闭子线程的DB/Redis连接

            # 启动线程池执行本轮任务
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(worker, code) for code in stock_codes]
                for i, _ in enumerate(as_completed(futures), 1):
                    if i % 50 == 0 or i == total:
                        self.logger.info(f"✅ 已完成 {i}/{total} 只股票RSI计算")

            # 检查是否还有剩余任务
            retry_count += 1
            remaining = self.redis_manager.get_unprocessed_stocks(now_day, redis_key)

            if not remaining:
                self.logger.info("✅ 所有RSI任务处理完成")
                return

            if retry_count <= max_auto_retries:
                wait_sec = 5
                self.logger.info(f"⚠️ 仍有 {len(remaining)} 只股票未处理，{wait_sec}秒后启动第 {retry_count + 1} 轮...")
                time.sleep(wait_sec)
            else:
                self.logger.error(f"❌ 达到最大重试轮数 ({max_auto_retries})，仍有 {len(remaining)} 只股票RSI未处理")
                return

    # 计算所有时间段的OBV
    def run_batch_rsi_all_time_period(self):
        """批量处理所有时间段"""
        for date_type in ['d', 'w', 'm']:
            self.run_batch_rsi_multithread(date_type=date_type)

    # 处理单只股票的 CCI
    def process_single_stock_cci(self, stock_code: str, daily_type: dict) -> int:
        """
        处理单只股票的 CCI 计算（线程安全 + 增量更新）
        """
        update_column = daily_type['update_column']
        data_table = daily_type['data_table']
        update_table = daily_type['update_table']  # 更新记录表
        trade_status = daily_type['tradestatus']
        frequency = daily_type['frequency']

        try:
            # 1. 获取上次更新日期
            last_date_sql = f"SELECT {update_column} FROM update_stock_record WHERE stock_code = %s"
            last_result = self.mysql_manager.query_one(last_date_sql, (stock_code,))
            last_date = str(last_result[update_column] if last_result else '1990-01-01')
            start_date_for_query = (datetime.datetime.strptime(last_date, '%Y-%m-%d') -
                                    relativedelta(years=frequency)).strftime(
                '%Y-%m-%d')

            # 2. 查询增量数据（必须包含 stock_date >= last_date）
            price_sql = f"""
                SELECT stock_code,stock_date, close_price, open_price, high_price, low_price
                FROM stock.{data_table}
                WHERE stock_code = %s 
                  AND stock_date >= %s 
                  {trade_status}
                ORDER BY stock_date
            """
            raw_data = self.mysql_manager.query_all(price_sql, (stock_code, start_date_for_query))
            if not raw_data:
                return 0

            df = pd.DataFrame(raw_data, columns=['stock_code', 'stock_date', 'close_price', 'open_price', 'high_price',
                                                 'low_price'])
            if df.empty:
                return 0

            df['close_price'] = df['close_price'].values.astype(float)
            df['open_price'] = df['open_price'].values.astype(float)
            df['high_price'] = df['high_price'].values.astype(float)
            df['low_price'] = df['low_price'].values.astype(float)

            # 数据清洗与类型转换
            df['stock_date'] = pd.to_datetime(df['stock_date'])
            df = df.sort_values('stock_date').reset_index(drop=True)

            # ✅ 关键修正：检查数据量（CCI需要至少14天）
            if len(df) < 14:
                self.logger.info(f"股票 {stock_code} 交易日不足14天（{len(df)}天），无法计算CCI，跳过")
                return 0

            # 3. 计算CCI（使用标准14日窗口）
            # 计算典型价格 (TP)
            df['tp'] = (df['high_price'] + df['low_price'] + df['close_price']) / 3

            # 计算14日SMA
            df['sma14'] = df['tp'].rolling(window=14, min_periods=14).mean()

            # 计算14日MAD（平均绝对差）
            df['mad'] = df['tp'].rolling(window=14, min_periods=14).apply(
                lambda x: np.mean(np.abs(x - np.mean(x)))
            )

            # 计算CCI
            df['cci'] = (df['tp'] - df['sma14']) / (0.015 * df['mad'])

            # 4. 准备入库数据（只保留有效CCI值）
            # ✅ 仅计算从第14天开始的日期（前13天无法计算）
            df_calculate = df.iloc[13:].copy()  # 从第14行开始（索引13）
            df_calculate = df_calculate[df_calculate['cci'].notna()]

            if df_calculate.empty:
                self.logger.info(f"股票 {stock_code} 计算CCI后无有效数据")
                return 0

            # 将NaN替换为None（数据库兼容性）
            final_df = df_calculate[['stock_code', 'stock_date', 'cci', 'mad', 'tp']].copy()
            final_df = final_df.replace({np.nan: None})

            # 5. 入库（关键：使用batch_insert_or_update）
            def _do_insert():
                return self.mysql_manager.batch_insert_or_update(
                    table_name=update_table,
                    df=final_df,
                    unique_keys=['stock_code', 'stock_date']  # CCI表主键
                )

            cnt = self._execute_with_deadlock_retry(_do_insert)

            if cnt > 0:
                max_date = final_df['stock_date'].max()

                # 更新更新记录
                def _do_update():
                    sql = f"""
                        INSERT INTO update_stock_record (stock_code, {update_column})
                        VALUES (%s, %s)
                        ON DUPLICATE KEY UPDATE {update_column} = VALUES({update_column})
                    """
                    return self.mysql_manager.execute(sql, (stock_code, max_date))

                self._execute_with_deadlock_retry(_do_update)
                self.logger.info(f"✅ 股票 {stock_code} 新增 {cnt} 条 CCI，更新至 {max_date}")
                return cnt

            return 0

        except Exception as e:
            self.logger.error(f"❌ 处理股票 {stock_code} CCI 失败: {e}", exc_info=True)
            return 0

    def run_batch_cci_multithread(self, max_workers: int = 6, date_type='d', max_auto_retries=10):
        """
        多线程批量计算CCI（商品通道指数），支持自动重试直到Redis清空
        :param max_workers: 线程数
        :param date_type: 周期类型 ('d' 日线, 'w' 周线, 'm' 月线)
        :param max_auto_retries: 最大自动重试轮数（防死循环）
        """
        # ✅ 关键修正：获取CCI配置（类似RSI的get_rsi_type）
        daily_type = self.indicator_config.get_cci_type(date_type)
        redis_key = f'cci:{date_type}'
        now_day = datetime.datetime.now().strftime('%Y-%m-%d')
        retry_count = 0

        while retry_count <= max_auto_retries:
            stock = BaostockFetcher()
            if retry_count == 0:
                stock_codes = stock.get_pending_stocks(redis_key, 'stock')
            else:
                stock_codes = stock.redis_manager.get_unprocessed_stocks(now_day, redis_key)

            self.logger.info(f"第 {retry_count} 轮重试：正在处理股票CCI")

            if not stock_codes:
                if retry_count == 0:
                    self.logger.warning("未找到有效股票数据")
                else:
                    self.logger.info("✅ 所有待处理股票CCI已计算完毕")
                return

            total = len(stock_codes)
            if retry_count == 0:
                self.logger.info(f"启动多线程CCI计算，共 {total} 只股票，线程数: {max_workers}")
            else:
                self.logger.info(f"第 {retry_count + 1} 轮重试：仍有 {total} 只股票待处理")

            def worker(stock_code):
                """每个线程独立处理一只股票（线程安全）"""
                processor = None
                try:
                    # ✅ 创建全新IndicatorCalculator实例（避免连接共享）
                    processor = IndicatorCalculator()

                    # ✅ 检查数据量（CCI需要至少14天，不是RSI的6天！）
                    sql = f"SELECT COUNT(*) AS cnt FROM stock.{daily_type['data_table']} WHERE stock_code = %s"
                    result = processor.mysql_manager.query_one(sql, (stock_code,))
                    cnt = result['cnt'] if result else 0

                    if cnt < 14:  # ✅ CCI最小窗口=14天
                        processor.logger.info(f"股票 {stock_code} 交易日不足14天（{cnt}天），无法计算CCI，跳过")
                        processor.redis_manager.remove_unprocessed_stocks([stock_code], self.now_date, redis_key)
                        return

                    # ✅ 执行CCI计算（使用标准逻辑）
                    rows = processor.process_single_stock_cci(stock_code, daily_type)
                    if rows > 0:
                        processor.redis_manager.remove_unprocessed_stocks([stock_code], self.now_date, redis_key)

                except Exception as e:
                    # ✅ 使用processor.logger（而非self.logger）记录错误
                    processor.logger.error(f"[线程{threading.get_ident()}] 股票 {stock_code} CCI计算失败: {e}",
                                           exc_info=True)
                finally:
                    if processor:
                        processor.close()  # 关闭子线程的DB/Redis连接

            # 启动线程池执行本轮任务
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(worker, code) for code in stock_codes]
                for i, _ in enumerate(as_completed(futures), 1):
                    if i % 50 == 0 or i == total:
                        self.logger.info(f"✅ 已完成 {i}/{total} 只股票CCI计算")

            # 检查是否还有剩余任务
            retry_count += 1
            remaining = self.redis_manager.get_unprocessed_stocks(now_day, redis_key)

            if not remaining:
                self.logger.info("✅ 所有CCI任务处理完成")
                return

            if retry_count <= max_auto_retries:
                wait_sec = 5
                self.logger.info(f"⚠️ 仍有 {len(remaining)} 只股票未处理，{wait_sec}秒后启动第 {retry_count + 1} 轮...")
                time.sleep(wait_sec)
            else:
                self.logger.error(f"❌ 达到最大重试轮数 ({max_auto_retries})，仍有 {len(remaining)} 只股票CCI未处理")
                return

    # 计算所有时间段的CCI
    def run_batch_cci_all_time_period(self):
        """批量处理所有时间段"""
        for date_type in ['d', 'w', 'm']:
            self.run_batch_cci_multithread(date_type=date_type)


if __name__ == '__main__':
    # 创建实例
    indicator_calculator = IndicatorCalculator()
    indicator_calculator.process_single_stock_cci('600000', indicator_calculator.indicator_config.get_cci_type('d'))
    indicator_calculator.close()

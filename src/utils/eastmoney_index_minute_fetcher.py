"""
东方财富指数分钟线数据采集器
创建日期：2026-04-10

功能：
- 从东方财富 API 爬取指数分钟线历史数据
- 支持分段请求、断点续传
- 严格频率控制（10-30秒随机间隔）
- 异常重试机制
"""

import json
import os
import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd
import requests

from logs.logger import LogManager
from src.utils.mysql_tool import MySQLUtil


class EastmoneyIndexMinuteFetcher:
    """东方财富指数分钟线数据采集器"""

    # 东方财富 API 地址（支持 HTTPS）
    API_URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"

    # 请求头（模拟浏览器，避免被拦截）
    REQUEST_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": "https://quote.eastmoney.com/",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Connection": "keep-alive",
    }

    # 待爬取指数清单
    INDEX_LIST = [
        {"code": "000001", "name": "上证指数", "market": "sh", "secid": "1.000001"},
        {"code": "000300", "name": "沪深300", "market": "sh", "secid": "1.000300"},
        {"code": "000016", "name": "上证50", "market": "sh", "secid": "1.000016"},
        {"code": "000905", "name": "中证500", "market": "sh", "secid": "1.000905"},
        {"code": "399001", "name": "深证成指", "market": "sz", "secid": "0.399001"},
        {"code": "399006", "name": "创业板指", "market": "sz", "secid": "0.399006"},
        {"code": "399005", "name": "中小板指", "market": "sz", "secid": "0.399005"},
    ]

    # 分钟线类型映射
    MIN_TYPE_MAP = {
        5: "5分钟",
        15: "15分钟",
        30: "30分钟",
        60: "60分钟",
    }

    # 起始日期
    START_DATE = "2010-01-01"

    # 每次请求最大条数（约50条，东方财富限制）
    MAX_LIMIT = 50

    # 频率控制参数
    MIN_WAIT_SECONDS = 15
    MAX_WAIT_SECONDS = 45
    
    # 代理配置
    PROXY_HOST = "192.168.0.103"
    PROXY_PORT = 7890
    PROXIES = {
        "http": f"http://{PROXY_HOST}:{PROXY_PORT}",
        "https": f"http://{PROXY_HOST}:{PROXY_PORT}"
    }
    
    # 关键参数（东方财富加密令牌）
    UT_TOKEN = "fa5fd1943c7b386f1722ccf10f5e7e8a"

    # 重试参数
    MAX_RETRIES = 3
    RETRY_WAIT_SECONDS = 60  # 重试等待时间更长

    def __init__(self):
        self.mysql_util = MySQLUtil()
        self.mysql_util.connect()
        self.logger = LogManager.get_logger("eastmoney_index_minute_fetcher")

        # 进度文件路径
        self.progress_file = "logs/index_minute_progress.json"
        os.makedirs("logs", exist_ok=True)

        # 加载进度
        self.progress = self._load_progress()

    def _load_progress(self) -> Dict:
        """加载进度文件"""
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"加载进度文件失败: {e}")
        return {}

    def _save_progress(self):
        """保存进度文件"""
        try:
            with open(self.progress_file, "w", encoding="utf-8") as f:
                json.dump(self.progress, f, ensure_ascii=False, indent=2)
            self.logger.info(f"进度已保存到 {self.progress_file}")
        except Exception as e:
            self.logger.error(f"保存进度文件失败: {e}")

    def _wait_random(self, min_sec: int = None, max_sec: int = None):
        """随机等待，遵守频率限制"""
        min_sec = min_sec or self.MIN_WAIT_SECONDS
        max_sec = max_sec or self.MAX_WAIT_SECONDS
        wait_seconds = random.randint(min_sec, max_sec)
        self.logger.info(f"频率控制：等待 {wait_seconds} 秒...")
        time.sleep(wait_seconds)

    def _build_request_url(
        self,
        secid: str,
        min_type: int,
        limit: int,
        start_date: Optional[str] = None,
    ) -> str:
        """构建请求 URL"""
        params = {
            "secid": secid,
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57",
            "klt": min_type,  # K线类型
            "fqt": 1,  # 不复权
            "lmt": min(limit, 50),  # 返回条数，最大50条
            "end": "20500101",  # 结束日期（设置远期以获取全部历史）
            "ut": self.UT_TOKEN,  # 关键参数：加密令牌
        }

        if start_date:
            params["beg"] = start_date.replace("-", "")

        param_str = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{self.API_URL}?{param_str}"

    def _fetch_kline_data(
        self, secid: str, min_type: int, limit: int, start_date: Optional[str] = None
    ) -> Optional[List]:
        """请求 K 线数据，带重试机制"""
        url = self._build_request_url(secid, min_type, limit, start_date)

        for retry_count in range(self.MAX_RETRIES):
            try:
                self.logger.info(
                    f"请求 URL: {url} (尝试 {retry_count + 1}/{self.MAX_RETRIES})"
                )

                response = requests.get(
                    url,
                    headers=self.REQUEST_HEADERS,
                    timeout=30,
                    verify=True,  # SSL 验证
                    proxies=self.PROXIES  # 使用代理
                )
                response.raise_for_status()

                data = response.json()

                # 检查返回数据
                if data.get("data") and data["data"].get("klines"):
                    klines = data["data"]["klines"]
                    self.logger.info(f"获取到 {len(klines)} 条数据")
                    return klines

                # 无数据
                self.logger.warning(f"返回数据为空: {data}")
                return []

            except requests.exceptions.SSLError as e:
                self.logger.error(f"SSL 错误: {e}")
                # SSL 错误可能是因为网络代理，尝试不验证 SSL
                if retry_count < self.MAX_RETRIES - 1:
                    self.logger.info("尝试不验证 SSL...")
                    try:
                        response = requests.get(
                            url,
                            headers=self.REQUEST_HEADERS,
                            timeout=30,
                            verify=False,
                            proxies=self.PROXIES  # 使用代理
                        )
                        response.raise_for_status()
                        data = response.json()
                        if data.get("data") and data["data"].get("klines"):
                            return data["data"]["klines"]
                    except Exception as inner_e:
                        self.logger.error(f"不验证 SSL 也失败: {inner_e}")
                        time.sleep(self.RETRY_WAIT_SECONDS)
                else:
                    return None

            except requests.exceptions.ConnectionError as e:
                self.logger.error(f"连接错误: {e}")
                self.logger.error("请检查网络连接，确保可以访问东方财富 API")
                self.logger.error("可能原因：1. 网络防火墙限制 2. 代理配置问题 3. DNS 解析失败")
                if retry_count < self.MAX_RETRIES - 1:
                    self.logger.info(f"等待 {self.RETRY_WAIT_SECONDS} 秒后重试...")
                    time.sleep(self.RETRY_WAIT_SECONDS)
                else:
                    self.logger.error(f"重试 {self.MAX_RETRIES} 次后仍失败")
                    return None

            except requests.exceptions.Timeout as e:
                self.logger.error(f"请求超时: {e}")
                if retry_count < self.MAX_RETRIES - 1:
                    self.logger.info(f"等待 {self.RETRY_WAIT_SECONDS} 秒后重试...")
                    time.sleep(self.RETRY_WAIT_SECONDS)
                else:
                    return None

            except requests.exceptions.RequestException as e:
                self.logger.error(f"请求失败: {e}")
                if retry_count < self.MAX_RETRIES - 1:
                    self.logger.info(f"等待 {self.RETRY_WAIT_SECONDS} 秒后重试...")
                    time.sleep(self.RETRY_WAIT_SECONDS)
                else:
                    self.logger.error(f"重试 {self.MAX_RETRIES} 次后仍失败")
                    return None

            except Exception as e:
                self.logger.error(f"解析数据失败: {e}")
                return None

        return None

    def _parse_kline_data(
        self, klines: List[str], stock_code: str, market_type: str, min_type: int
    ) -> pd.DataFrame:
        """解析 K 线数据为 DataFrame"""
        if not klines:
            return pd.DataFrame()

        records = []
        for kline in klines:
            # 东方财富返回格式：日期,开盘,收盘,最高,最低,成交量,成交额,振幅,涨跌幅,涨跌额,换手率
            parts = kline.split(",")
            if len(parts) < 10:
                continue

            # 解析日期和时间
            date_str = parts[0]
            # 日期格式可能是：2024-01-01 或 2024-01-01 09:30
            if " " in date_str:
                date_part, time_part = date_str.split(" ")
            else:
                date_part = date_str
                time_part = parts[0].split("-")[-1] if "-" in parts[0] else "00:00"

            # 对于分钟线，时间格式需要处理
            # 东方财富返回格式：2026-04-10 09:35 格式
            try:
                if " " in parts[0]:
                    full_datetime = parts[0]
                    dt = datetime.strptime(full_datetime, "%Y-%m-%d %H:%M")
                    date_part = dt.strftime("%Y-%m-%d")
                    time_part = dt.strftime("%H:%M")
                else:
                    # 如果只有日期，根据 min_type 推算时间点
                    date_part = date_str
                    time_part = "15:00"  # 默认收盘时间
            except Exception as e:
                self.logger.warning(f"解析日期失败: {date_str}, {e}")
                continue

            record = {
                "stock_code": stock_code,
                "stock_date": date_part,
                "stock_time": time_part,
                "min_type": min_type,
                "open_price": float(parts[1]) if parts[1] else None,
                "close_price": float(parts[2]) if parts[2] else None,
                "high_price": float(parts[3]) if parts[3] else None,
                "low_price": float(parts[4]) if parts[4] else None,
                "trading_volume": float(parts[5]) if parts[5] else None,
                "trading_amount": float(parts[6]) if parts[6] else None,
                "amplitude": float(parts[7]) if parts[7] else None,
                "change_pct": float(parts[8]) if parts[8] else None,
                "change_amt": float(parts[9]) if parts[9] else None,
                "market_type": market_type,
            }
            records.append(record)

        df = pd.DataFrame(records)
        return df

    def _save_to_mysql(self, df: pd.DataFrame) -> int:
        """保存数据到 MySQL"""
        if df.empty:
            return 0

        table_name = "index_stock_history_min_price"
        unique_keys = ["stock_code", "market_type", "stock_date", "stock_time", "min_type"]

        try:
            rows = self.mysql_util.batch_insert_or_update(table_name, df, unique_keys)
            self.logger.info(f"成功入库 {rows} 条数据到 {table_name}")
            return rows
        except Exception as e:
            self.logger.error(f"入库失败: {e}")
            return 0

    def _update_progress_db(
        self,
        stock_code: str,
        market_type: str,
        min_type: int,
        last_date: str,
        last_time: str,
        total_records: int,
        status: str,
        error_msg: Optional[str] = None,
    ):
        """更新进度到数据库"""
        sql = """
            INSERT INTO index_minute_progress
            (stock_code, market_type, min_type, last_fetch_date, last_fetch_time,
             total_records, status, error_msg)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                last_fetch_date = VALUES(last_fetch_date),
                last_fetch_time = VALUES(last_fetch_time),
                total_records = total_records + VALUES(total_records),
                status = VALUES(status),
                error_msg = VALUES(error_msg),
                update_time = CURRENT_TIMESTAMP
        """

        try:
            self.mysql_util.execute(
                sql,
                (stock_code, market_type, min_type, last_date, last_time,
                 total_records, status, error_msg)
            )
            self.logger.info(f"进度已更新到数据库: {stock_code} {min_type}分钟")
        except Exception as e:
            self.logger.error(f"更新进度到数据库失败: {e}")

    def fetch_index_minute_data(
        self,
        index_info: Dict,
        min_type: int,
        start_date: Optional[str] = None,
        test_mode: bool = False,
    ) -> Tuple[int, bool]:
        """
        爬取单个指数的单种分钟线数据

        Args:
            index_info: 指数信息字典
            min_type: 分钟线类型 (5/15/30/60)
            start_date: 起始日期（可选，用于断点续传）
            test_mode: 测试模式（仅爬取少量数据）

        Returns:
            (total_records, success)
        """
        stock_code = index_info["code"]
        market_type = index_info["market"]
        secid = index_info["secid"]
        index_name = index_info["name"]

        self.logger.info(
            f"开始爬取 {index_name}({stock_code}) {self.MIN_TYPE_MAP[min_type]}线数据"
        )

        # 确定起始日期
        if not start_date:
            # 从进度文件获取上次爬取的最后日期
            progress_key = f"{stock_code}_{market_type}_{min_type}"
            if progress_key in self.progress:
                last_date = self.progress[progress_key].get("last_date")
                if last_date:
                    start_date = last_date
                    self.logger.info(f"断点续传，从 {start_date} 开始")
            else:
                start_date = self.START_DATE
                self.logger.info(f"首次爬取，从 {start_date} 开始")

        total_records = 0
        current_start = start_date
        has_more_data = True
        segment_count = 0

        while has_more_data:
            segment_count += 1

            # 测试模式下限制分段数量
            if test_mode and segment_count > 2:
                self.logger.info("测试模式：仅爬取2个分段，停止爬取")
                break

            self.logger.info(f"分段 {segment_count}: 从 {current_start} 开始")

            # 请求数据
            klines = self._fetch_kline_data(secid, min_type, self.MAX_LIMIT, current_start)

            if klines is None:
                # 请求失败
                self.logger.error(f"分段 {segment_count} 请求失败")
                return total_records, False

            if len(klines) == 0:
                # 无更多数据
                self.logger.info("已获取全部数据，无更多记录")
                has_more_data = False
                break

            # 解析数据
            df = self._parse_kline_data(klines, stock_code, market_type, min_type)

            if df.empty:
                self.logger.warning(f"分段 {segment_count} 解析数据为空")
                has_more_data = False
                break

            # 保存到数据库
            saved_rows = self._save_to_mysql(df)
            total_records += saved_rows

            # 更新进度
            last_date = df["stock_date"].max()
            last_time = df["stock_time"].max()

            # 更新进度文件
            progress_key = f"{stock_code}_{market_type}_{min_type}"
            self.progress[progress_key] = {
                "last_date": last_date,
                "last_time": last_time,
                "total_records": total_records,
                "status": "running",
                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            self._save_progress()

            # 更新数据库进度
            self._update_progress_db(
                stock_code, market_type, min_type, last_date, last_time,
                saved_rows, "running"
            )

            # 计算下一段起始日期
            # 从最后一条数据的日期开始，避免重复
            current_start = last_date

            # 频率控制：每次请求后等待
            self._wait_random()

        # 爬取完成
        status = "completed"
        self._update_progress_db(
            stock_code, market_type, min_type, last_date, last_time,
            total_records, status
        )

        progress_key = f"{stock_code}_{market_type}_{min_type}"
        self.progress[progress_key]["status"] = "completed"
        self._save_progress()

        self.logger.info(
            f"{index_name}({stock_code}) {self.MIN_TYPE_MAP[min_type]}线爬取完成，"
            f"共 {total_records} 条数据，{segment_count} 个分段"
        )

        return total_records, True

    def fetch_all_index_minute_data(
        self,
        min_types: List[int] = [5, 15, 30, 60],
        test_mode: bool = False,
        test_index: Optional[str] = None,
    ):
        """
        爬取所有指数的所有分钟线数据

        Args:
            min_types: 分钟线类型列表
            test_mode: 测试模式
            test_index: 测试特定指数代码（可选）
        """
        # 筛选指数
        if test_index:
            index_list = [idx for idx in self.INDEX_LIST if idx["code"] == test_index]
            if not index_list:
                self.logger.error(f"未找到指数 {test_index}")
                return
        else:
            index_list = self.INDEX_LIST

        total_start_time = datetime.now()
        self.logger.info(
            f"开始爬取 {len(index_list)} 个指数，"
            f"分钟线类型: {min_types}, "
            f"测试模式: {test_mode}"
        )

        for index_info in index_list:
            for min_type in min_types:
                try:
                    records, success = self.fetch_index_minute_data(
                        index_info, min_type, test_mode=test_mode
                    )

                    if not success:
                        self.logger.error(
                            f"{index_info['name']} {min_type}分钟线爬取失败"
                        )
                        # 等待更长时间后继续下一个
                        self._wait_random(min_sec=60, max_sec=120)

                except Exception as e:
                    self.logger.error(
                        f"爬取 {index_info['name']} {min_type}分钟线异常: {e}"
                    )
                    # 等待更长时间后继续
                    self._wait_random(min_sec=60, max_sec=120)

        total_end_time = datetime.now()
        total_duration = (total_end_time - total_start_time).total_seconds() / 60

        self.logger.info(f"全部爬取完成，总耗时: {total_duration:.1f} 分钟")

    def close(self):
        """关闭连接"""
        self.mysql_util.close()


# ===== 便捷命令行入口 =====
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="东方财富指数分钟线数据采集器")
    parser.add_argument(
        "--index", type=str, default=None, help="指定指数代码（如 000001）"
    )
    parser.add_argument(
        "--min-type", type=int, nargs="+", default=[5],
        help="分钟线类型（5/15/30/60），默认5分钟"
    )
    parser.add_argument(
        "--test", action="store_true", help="测试模式（仅爬取少量数据）"
    )
    parser.add_argument(
        "--all", action="store_true", help="爬取全部指数和全部分钟线类型"
    )

    args = parser.parse_args()

    fetcher = EastmoneyIndexMinuteFetcher()

    try:
        if args.all:
            # 爬取全部
            fetcher.fetch_all_index_minute_data(
                min_types=[5, 15, 30, 60],
                test_mode=args.test
            )
        elif args.index:
            # 爬取指定指数
            fetcher.fetch_all_index_minute_data(
                min_types=args.min_type,
                test_mode=args.test,
                test_index=args.index
            )
        else:
            # 默认：爬取上证指数5分钟线（测试模式）
            fetcher.fetch_all_index_minute_data(
                min_types=[5],
                test_mode=True,
                test_index="000001"
            )

    finally:
        fetcher.close()
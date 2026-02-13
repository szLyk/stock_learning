import redis
from typing import Optional, Dict, List
from datetime import datetime
from config.redis_config import get_redis_config


class RedisUtil:
    """Redis工具类（补充username参数，兼容高低版本）"""

    def __init__(self):
        self.config = get_redis_config()
        self.client: Optional[redis.Redis] = None

    def connect(self):
        """建立Redis连接（新增username参数）"""
        try:
            self.client = redis.Redis(
                host=self.config["host"],
                port=self.config["port"],
                username=self.config["username"],
                password=self.config["password"],
                db=self.config["db"],
                max_connections=self.config["max_connections"],
                socket_timeout=self.config["socket_timeout"],
                decode_responses=self.config["decode_responses"]
            )
            # 测试连接
            self.client.ping()
            print("Redis连接成功！")
        except Exception as e:
            raise RuntimeError(f"Redis连接失败：{str(e)}")

    def add_unprocessed_stocks(self, stock_list: List[str], date=datetime.now().strftime("%Y-%m-%d")):
        """批量添加未处理的股票代码"""
        key = f"stock_data:{date}:unprocessed"
        self.client.sadd(key, *stock_list)

    def add_processed_stocks(self, stock_list: List[str], date=datetime.now().strftime("%Y-%m-%d")):
        """批量添加已处理的股票代码"""
        key = f"stock_data:{date}:processed"
        self.client.sadd(key, *stock_list)

    def remove_unprocessed_stocks(self, stock_list: List[str], date=datetime.now().strftime("%Y-%m-%d")):
        """批量移除未处理的股票代码"""
        key = f"stock_data:{date}:unprocessed"
        self.client.srem(key, *stock_list)

    def remove_processed_stocks(self, stock_list: List[str], date=datetime.now().strftime("%Y-%m-%d")):
        """批量移除已处理的股票代码"""
        key = f"stock_data:{date}:processed"
        self.client.srem(key, *stock_list)

    def get_unprocessed_stocks(self, date=datetime.now().strftime("%Y-%m-%d")) -> List[str]:
        """获取未处理的股票代码列表（修复decode错误，兼容bytes/str类型）"""
        key = f"stock_data:{date}:unprocessed"
        # 先获取Redis中的原始数据
        raw_stocks = self.client.smembers(key)
        # 兼容处理：如果是bytes则decode，已是str则直接使用
        processed_stocks = []
        for stock in raw_stocks:
            if isinstance(stock, bytes):
                processed_stocks.append(stock.decode('utf-8'))
            elif isinstance(stock, str):
                processed_stocks.append(stock.strip())  # 去空格，避免无效字符
            else:
                # 非字符串/字节类型，转为字符串
                processed_stocks.append(str(stock))
        return processed_stocks

    def get_processed_stocks(self, date=datetime.now().strftime("%Y-%m-%d")) -> List[str]:
        """获取已处理的股票代码列表（修复decode错误，兼容str/bytes类型）"""
        key = f"stock_data:{date}:processed"
        # 获取Redis中的原始数据
        raw_stocks = self.client.smembers(key)
        processed_stocks = []

        for stock in raw_stocks:
            # 兼容处理：bytes类型则解码，str类型则直接使用，其他类型转为字符串
            if isinstance(stock, bytes):
                # 解码时加容错，避免编码错误导致崩溃
                processed_stocks.append(stock.decode('utf-8', errors='ignore').strip())
            elif isinstance(stock, str):
                # 字符串类型直接去空格，过滤空值
                stock_str = stock.strip()
                if stock_str:  # 只保留非空字符串
                    processed_stocks.append(stock_str)
            else:
                # 极少数情况（如数字/None），转为字符串并过滤空值
                stock_str = str(stock).strip()
                if stock_str:
                    processed_stocks.append(stock_str)

        # 去重+排序（可选，提升数据整洁度）
        processed_stocks = list(set(processed_stocks))
        processed_stocks.sort()

        return processed_stocks

    def is_stock_processed(self, stock_code: str, date=datetime.now().strftime("%Y-%m-%d")) -> bool:
        """检查股票是否已处理"""
        key = f"stock_data:{date}:processed"
        return self.client.sismember(key, stock_code)

    def set_last_update_time(self, stock_code: str, update_time: Optional[str] = None,
                             date=datetime.now().strftime("%Y-%m-%d")):
        """设置股票的最后更新时间"""
        if not update_time:
            update_time = datetime.now().isoformat()
        key = f"stock_data:{date}:{stock_code}:last_update"
        self.client.set(key, update_time)

    def get_last_update_time(self, stock_code: str, date=datetime.now().strftime("%Y-%m-%d")) -> Optional[str]:
        """获取股票的最后更新时间"""
        key = f"stock_data:{date}:{stock_code}:last_update"
        update_time = self.client.get(key)
        if update_time:
            return update_time.decode('utf-8')
        return None

"""
数据适配层
连接数据库与缠论分析器

功能：
1. 从数据库读取日线数据
2. 转换为缠论RawBar格式
3. 支持增量更新
"""

import pymysql
from pymysql.cursors import DictCursor
from datetime import datetime
from typing import List, Optional
from chanlun.objects import RawBar


class StockDataAdapter:
    """
    股票数据适配器
    
    连接stock数据库，将数据转换为缠论格式
    
    数据库表：stock_history_date_price
    字段映射：
    - stock_code → symbol
    - stock_date → dt
    - open_price → open
    - high_price → high
    - low_price → low
    - close_price → close
    - trading_volume → vol
    - trading_amount → amount
    """
    
    def __init__(
        self,
        host: str = "192.168.1.128",
        port: int = 3306,
        user: str = "root",
        password: str = "123456",
        database: str = "stock",
    ):
        """初始化数据库连接"""
        self.db_config = {
            'host': host,
            'port': port,
            'user': user,
            'password': password,
            'database': database,
            'charset': 'utf8mb4',
            'cursorclass': DictCursor,
        }
        
    def _connect(self):
        """建立数据库连接"""
        return pymysql.connect(**self.db_config)
    
    def fetch_bars(
        self,
        stock_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[RawBar]:
        """
        获取股票日线数据
        
        Args:
            stock_code: 股票代码（如 '000001'）
            start_date: 开始日期（如 '2024-01-01'）
            end_date: 结束日期（如 '2024-12-31'）
            limit: 限制条数
            
        Returns:
            RawBar列表
        """
        conn = self._connect()
        cursor = conn.cursor()
        
        # 构建SQL
        sql = """
            SELECT 
                stock_code, stock_date, open_price, high_price, 
                low_price, close_price, trading_volume, trading_amount,
                pre_close, ups_and_downs, turn
            FROM stock_history_date_price
            WHERE stock_code = %s
        """
        params = [stock_code]
        
        if start_date:
            sql += " AND stock_date >= %s"
            params.append(start_date)
        
        if end_date:
            sql += " AND stock_date <= %s"
            params.append(end_date)
        
        sql += " ORDER BY stock_date ASC"
        
        if limit:
            sql += f" LIMIT {limit}"
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        # 转换为RawBar
        bars = []
        for i, row in enumerate(rows):
            bar = RawBar(
                symbol=row['stock_code'],
                dt=datetime.strptime(str(row['stock_date']), '%Y-%m-%d'),
                open=float(row['open_price']),
                close=float(row['close_price']),
                high=float(row['high_price']),
                low=float(row['low_price']),
                vol=float(row['trading_volume']),
                amount=float(row['trading_amount']),
                pre_close=float(row['pre_close']) if row['pre_close'] else 0,
                change_pct=float(row['ups_and_downs']) if row['ups_and_downs'] else 0,
                turn=float(row['turn']) if row['turn'] else 0,
            )
            bars.append(bar)
        
        return bars
    
    def fetch_all_stocks(self) -> List[str]:
        """获取所有股票代码"""
        conn = self._connect()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT stock_code 
            FROM stock_history_date_price
            ORDER BY stock_code
        """)
        
        codes = [row['stock_code'] for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        return codes
    
    def fetch_latest_date(self, stock_code: str) -> Optional[datetime]:
        """获取股票最新数据日期"""
        conn = self._connect()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT MAX(stock_date) as max_date
            FROM stock_history_date_price
            WHERE stock_code = %s
        """, [stock_code])
        
        row = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if row and row['max_date']:
            return datetime.strptime(str(row['max_date']), '%Y-%m-%d')
        return None
    
    def fetch_data_range(self, stock_code: str) -> tuple:
        """获取股票数据时间范围"""
        conn = self._connect()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT MIN(stock_date) as min_date, MAX(stock_date) as max_date, COUNT(*) as cnt
            FROM stock_history_date_price
            WHERE stock_code = %s
        """, [stock_code])
        
        row = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return (
            str(row['min_date']) if row['min_date'] else None,
            str(row['max_date']) if row['max_date'] else None,
            row['cnt'] if row['cnt'] else 0,
        )
    
    @staticmethod
    def convert_to_rawbar(row: dict) -> RawBar:
        """
        单行数据转换为RawBar
        
        Args:
            row: 数据库查询结果字典
            
        Returns:
            RawBar对象
        """
        return RawBar(
            symbol=row['stock_code'],
            dt=datetime.strptime(str(row['stock_date']), '%Y-%m-%d'),
            open=float(row['open_price']),
            close=float(row['close_price']),
            high=float(row['high_price']),
            low=float(row['low_price']),
            vol=float(row['trading_volume']),
            amount=float(row['trading_amount']),
            pre_close=float(row.get('pre_close', 0) or 0),
            change_pct=float(row.get('ups_and_downs', 0) or 0),
            turn=float(row.get('turn', 0) or 0),
        )


class MultiStockAnalyzer:
    """
    多股票缠论分析器
    
    支持批量分析多只股票
    """
    
    def __init__(self, adapter: StockDataAdapter):
        self.adapter = adapter
        self.analyzers = {}  # stock_code -> ChanAnalyzer
        
    def analyze_stock(self, stock_code: str, **kwargs) -> dict:
        """
        分析单只股票
        
        Args:
            stock_code: 股票代码
            **kwargs: fetch_bars参数
            
        Returns:
            分析结果摘要
        """
        from chanlun.analyze import ChanAnalyzer
        
        # 获取数据
        bars = self.adapter.fetch_bars(stock_code, **kwargs)
        
        if not bars:
            return {'error': '无数据', 'stock_code': stock_code}
        
        # 执行分析
        analyzer = ChanAnalyzer()
        analyzer.update(bars)
        
        # 保存分析器
        self.analyzers[stock_code] = analyzer
        
        return analyzer.get_summary()
    
    def analyze_all(self, stock_codes: List[str] = None, **kwargs) -> List[dict]:
        """
        批量分析
        
        Args:
            stock_codes: 股票代码列表（None则分析全部）
            **kwargs: fetch_bars参数
            
        Returns:
            分析结果列表
        """
        if stock_codes is None:
            stock_codes = self.adapter.fetch_all_stocks()
        
        results = []
        for code in stock_codes[:100]:  # 限制100只避免超时
            result = self.analyze_stock(code, **kwargs)
            results.append(result)
        
        return results
    
    def get_analyzer(self, stock_code: str):
        """获取指定股票的分析器"""
        return self.analyzers.get(stock_code)
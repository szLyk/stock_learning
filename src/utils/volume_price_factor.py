# -*- coding: utf-8 -*-
"""
量价因子计算工具（改进版）
功能：基于成交量和价格计算量价因子，科学评估量价关系

核心逻辑：量价组合矩阵评分（而非简单乘法）

量价组合判断：
  放量上涨 → 强多信号（主力进场）
  缩量上涨 → 中多信号（筹码锁定，轻松拉升）
  放量下跌 → 强空信号（主力出货/恐慌抛售）
  缩量下跌 → 中空/中性（下跌动能衰竭，可能反弹）

因子组成：
  1. 成交量因子：放量程度（相对20日均量）
  2. 价格因子：涨跌幅度 + 趋势强度
  3. OBV因子：能量潮方向确认
  4. 综合评分：矩阵组合 + OBV确认
"""

import datetime
import pandas as pd
import numpy as np
from concurrent.futures import as_completed, ThreadPoolExecutor
from logs.logger import LogManager
from src.utils.mysql_tool import MySQLUtil


class VolumePriceFactor:
    """量价因子计算器（改进版：矩阵评分逻辑）"""

    # 量价组合评分矩阵（基础分）
    # 行：成交量状态（放量/正常/缩量），列：价格状态（大涨/小涨/小跌/大跌）
    VP_MATRIX = {
        'volume_high':   {'price_big_up': 90, 'price_small_up': 75, 'price_small_down': 35, 'price_big_down': 15},  # 放量
        'volume_normal': {'price_big_up': 70, 'price_small_up': 60, 'price_small_down': 40, 'price_big_down': 25},  # 正常
        'volume_low':    {'price_big_up': 80, 'price_small_up': 65, 'price_small_down': 45, 'price_big_down': 30},  # 缩量
    }

    # 成交量状态阈值
    VOL_HIGH_THRESHOLD = 1.5   # 放量：成交量比 > 1.5
    VOL_LOW_THRESHOLD = 0.7    # 缩量：成交量比 < 0.7

    # 价格变化阈值（百分比）
    PRICE_BIG_UP_THRESHOLD = 3.0    # 大涨：> 3%
    PRICE_SMALL_UP_THRESHOLD = 0.5  # 小涨：> 0.5%

    def __init__(self):
        self.logger = LogManager.get_logger("volume_price_factor")
        self.now_date = datetime.datetime.now().strftime('%Y-%m-%d')

    def _classify_volume_state(self, volume_ratio: float) -> str:
        """判断成交量状态"""
        if volume_ratio > self.VOL_HIGH_THRESHOLD:
            return 'volume_high'   # 放量
        elif volume_ratio < self.VOL_LOW_THRESHOLD:
            return 'volume_low'    # 缩量
        else:
            return 'volume_normal' # 正常

    def _classify_price_state(self, price_change_pct: float) -> str:
        """判断价格状态"""
        if price_change_pct > self.PRICE_BIG_UP_THRESHOLD:
            return 'price_big_up'
        elif price_change_pct > self.PRICE_SMALL_UP_THRESHOLD:
            return 'price_small_up'
        elif price_change_pct < -self.PRICE_BIG_UP_THRESHOLD:
            return 'price_big_down'
        elif price_change_pct < -self.PRICE_SMALL_UP_THRESHOLD:
            return 'price_small_down'
        else:
            return 'price_small_down'  # 微跌或持平归为小跌

    def calculate_single_stock(self, stock_code: str) -> dict:
        """
        计算单只股票的量价因子（每个线程使用独立连接）
        :param stock_code: 股票代码
        :return: 量价因子结果字典
        """
        with MySQLUtil() as db:
            try:
                # 1. 查询最近30天的日线数据（用于计算均量和涨跌幅）
                sql_price = """
                    SELECT stock_date, close_price, pre_close, trading_volume, turn
                    FROM stock_history_date_price
                    WHERE stock_code = %s AND tradestatus = 1
                    ORDER BY stock_date DESC
                    LIMIT 30
                """
                result = db.query_all(sql_price, (stock_code,))

                if not result or len(result) < 20:
                    self.logger.warning(f"{stock_code}: 数据不足20天，跳过")
                    return None

                df = pd.DataFrame(result)
                df = df.sort_values('stock_date').reset_index(drop=True)

                # 数据清洗
                df['close_price'] = pd.to_numeric(df['close_price'], errors='coerce')
                df['pre_close'] = pd.to_numeric(df['pre_close'], errors='coerce')
                df['trading_volume'] = pd.to_numeric(df['trading_volume'], errors='coerce')
                df = df.dropna(subset=['close_price', 'trading_volume'])

                if df.empty or len(df) < 20:
                    return None

                # 2. 计算成交量比率
                df['vol_ma_20'] = df['trading_volume'].rolling(window=20).mean()
                df['volume_ratio'] = df['trading_volume'] / df['vol_ma_20']
                latest_vol_ratio = df['volume_ratio'].iloc[-1]

                if pd.isna(latest_vol_ratio) or latest_vol_ratio <= 0:
                    latest_vol_ratio = 1.0

                # 3. 计算价格变化率（今日涨幅）
                latest_close = df['close_price'].iloc[-1]
                latest_pre_close = df['pre_close'].iloc[-1] if df['pre_close'].iloc[-1] else df['close_price'].iloc[-2]
                price_change_pct = (latest_close - latest_pre_close) / latest_pre_close * 100

                if pd.isna(price_change_pct):
                    price_change_pct = 0.0

                # 4. 计算5日趋势强度（连续上涨/下跌）
                df['price_change_5d'] = df['close_price'].pct_change(periods=5).iloc[-1] * 100
                trend_5d = df['price_change_5d'].iloc[-1] if not pd.isna(df['price_change_5d'].iloc[-1]) else 0.0

                # 5. 查询OBV数据
                sql_obv = """
                    SELECT obv, 30ma_obv
                    FROM stock_date_obv
                    WHERE stock_code = %s
                    ORDER BY stock_date DESC
                    LIMIT 5
                """
                obv_result = db.query_all(sql_obv, (stock_code,))
                obv_signal = 0
                obv_change = 0.0

                if obv_result and len(obv_result) >= 2:
                    obv_df = pd.DataFrame(obv_result)
                    obv_df['obv'] = pd.to_numeric(obv_df['obv'], errors='coerce')
                    obv_df['30ma_obv'] = pd.to_numeric(obv_df['30ma_obv'], errors='coerce')

                    # OBV方向：当前OBV vs 30日均OBV
                    latest_obv = obv_df['obv'].iloc[0]
                    obv_ma = obv_df['30ma_obv'].iloc[0]
                    if not pd.isna(latest_obv) and not pd.isna(obv_ma) and obv_ma > 0:
                        obv_signal = 1 if latest_obv > obv_ma else -1
                        obv_change = (latest_obv - obv_df['obv'].iloc[-1]) / obv_df['obv'].iloc[-1] * 100 if obv_df['obv'].iloc[-1] else 0

                # 6. 查询换手率
                latest_turnover = df['turn'].iloc[-1] if 'turn' in df.columns else 0
                if pd.isna(latest_turnover):
                    latest_turnover = 0.0
                else:
                    latest_turnover = float(latest_turnover)

                # 7. 矩阵评分
                vol_state = self._classify_volume_state(float(latest_vol_ratio))
                price_state = self._classify_price_state(float(price_change_pct))
                base_score = self.VP_MATRIX[vol_state][price_state]

                # 8. OBV修正（±5分）
                obv_adjust = obv_signal * 5
                final_score = base_score + obv_adjust

                # 9. 趋势修正（5日趋势加强/减弱）
                if trend_5d > 5:
                    final_score += 3  # 强势趋势加分
                elif trend_5d < -5:
                    final_score -= 3  # 弱势趋势减分

                # 限制在0-100范围
                final_score = max(0, min(100, final_score))

                # 10. 构建结果
                result = {
                    'stock_code': stock_code,
                    'calc_date': self.now_date,
                    'volume_price_score': round(final_score, 2),
                    'volume_ratio': round(float(latest_vol_ratio), 4),
                    'price_change': round(float(price_change_pct), 4),
                    'turnover_rate': round(latest_turnover, 4),
                    'obv_change': round(float(obv_change), 4),
                    'vol_state': vol_state,
                    'price_state': price_state,
                    'obv_signal': obv_signal,
                    'trend_5d': round(float(trend_5d), 4)
                }

                self.logger.info(f"{stock_code}: 评分={final_score:.1f} "
                               f"(量={vol_state} {latest_vol_ratio:.2f}, "
                               f"价={price_state} {price_change_pct:.2f}%, "
                               f"OBV={obv_signal})")

                return result

            except Exception as e:
                self.logger.error(f"{stock_code} 计算失败: {e}")
                return None

    def calculate_batch(self, max_workers: int = 10, save_to_db: bool = True) -> int:
        """
        批量计算量价因子（多线程）
        :param max_workers: 线程数
        :param save_to_db: 是否保存到数据库
        :return: 成功计算的数量
        """
        # 获取股票列表（独立连接）
        with MySQLUtil() as db:
            sql_stocks = """
                SELECT DISTINCT stock_code
                FROM stock_history_date_price
                WHERE tradestatus = 1
            """
            stocks_result = db.query_all(sql_stocks)
            stock_codes = [s['stock_code'] for s in stocks_result] if stocks_result else []

        total = len(stock_codes)
        self.logger.info(f"开始计算 {total} 只股票的量价因子")

        success_count = 0
        results = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self.calculate_single_stock, code): code
                for code in stock_codes
            }

            for future in as_completed(futures):
                code = futures[future]
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                        success_count += 1
                except Exception as e:
                    self.logger.error(f"{code} 异常: {e}")

        self.logger.info(f"计算完成: 成功 {success_count}/{total}")

        # 保存到数据库
        if save_to_db and results:
            self._save_results(results)

        return success_count

    def _save_results(self, results: list):
        """保存结果到数据库"""
        if not results:
            return

        df = pd.DataFrame(results)

        # 只保留表需要的字段
        columns = ['stock_code', 'calc_date', 'volume_price_score',
                   'volume_ratio', 'price_change', 'turnover_rate', 'obv_change']
        df_save = df[columns].copy()

        with MySQLUtil() as db:
            rows = db.batch_insert_or_update(
                'stock_factor_volume_price',
                df_save,
                ['stock_code', 'calc_date']
            )
            self.logger.info(f"✅ 保存 {rows} 条数据到 stock_factor_volume_price")


def calculate_volume_price_factor():
    """便捷函数：计算所有股票的量价因子"""
    calculator = VolumePriceFactor()
    calculator.calculate_batch(save_to_db=True)


if __name__ == '__main__':
    print("开始计算量价因子...")
    calculate_volume_price_factor()
    print("完成!")
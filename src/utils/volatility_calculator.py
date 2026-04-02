#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
波动率因子计算工具（严谨实现）

包含：
    1. 历史波动率 (Historical Volatility)
    2. Parkinson 波动率 (基于日内高低价)
    3. Garman-Klass 波动率 (基于OHLC)
    4. GARCH(1,1) 模型 (波动率预测)

参考文献：
    - Parkinson, M. (1980). "The Extreme Value Method for Estimating the Variance of the Rate of Return"
    - Garman, M.B., Klass, M.J. (1980). "On the Estimation of Security Price Volatilities from Historical Data"
    - Bollerslev, T. (1986). "Generalized Autoregressive Conditional Heteroskedasticity"

Author: Xiao Luo
Date: 2026-04-02
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import warnings
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Tuple, Optional, Dict
from scipy import stats

from src.utils.mysql_tool import MySQLUtil
from src.utils.redis_tool import RedisUtil
from logs.logger import LogManager

# 忽略一些警告
warnings.filterwarnings('ignore')

# 年化因子
TRADING_DAYS_PER_YEAR = 252


class VolatilityCalculator:
    """
    波动率计算器（严谨实现）
    
    所有波动率均为年化波动率，单位为百分比（如 0.25 表示 25%）
    """
    
    def __init__(self):
        self.mysql = MySQLUtil()
        self.mysql.connect()
        self.redis = RedisUtil() if RedisUtil else None
        self.logger = LogManager.get_logger("volatility_calculator")
        self.now_date = datetime.now().strftime('%Y-%m-%d')
    
    def close(self):
        self.mysql.close()
    
    # =====================================================
    # 基础波动率计算方法
    # =====================================================
    
    @staticmethod
    def historical_volatility(returns: np.ndarray, annualize: bool = True) -> float:
        """
        计算历史波动率（基于收益率标准差）
        
        公式: σ = std(returns) × √N
        
        Args:
            returns: 收益率序列（小数形式，如 0.01 表示 1%）
            annualize: 是否年化
        
        Returns:
            波动率（年化）
        """
        if len(returns) < 2:
            return np.nan
        
        # 转换为 float
        returns = np.array(returns, dtype=np.float64)
        
        # 使用无偏估计 (n-1)
        vol = np.std(returns, ddof=1)
        
        if annualize:
            vol = vol * np.sqrt(TRADING_DAYS_PER_YEAR)
        
        return float(vol)
    
    @staticmethod
    def parkinson_volatility(
        high: np.ndarray, 
        low: np.ndarray, 
        annualize: bool = True
    ) -> float:
        """
        计算 Parkinson 波动率（1980）
        
        公式: σ_p = √(1/(4n·ln2) · Σ(ln(H_i/L_i))²)
        
        优点：
            - 只使用高低价，信息量更大
            - 估计效率是历史波动率的 5 倍
            - 不受日内价格反转影响
        
        Args:
            high: 最高价序列
            low: 最低价序列
            annualize: 是否年化
        
        Returns:
            Parkinson 波动率（年化）
        """
        if len(high) < 2 or len(low) < 2:
            return np.nan
        
        # 转换为 float
        high = np.array(high, dtype=np.float64)
        low = np.array(low, dtype=np.float64)
        
        n = len(high)
        
        # 计算 ln(H/L)
        hl_ratio = np.log(high / low)
        
        # 检查无效值
        valid_mask = np.isfinite(hl_ratio)
        if valid_mask.sum() < 2:
            return np.nan
        
        hl_ratio = hl_ratio[valid_mask]
        n_valid = len(hl_ratio)
        
        # Parkinson 公式
        variance = (1 / (4 * n_valid * np.log(2))) * np.sum(hl_ratio ** 2)
        
        vol = np.sqrt(variance)
        
        if annualize:
            vol = vol * np.sqrt(TRADING_DAYS_PER_YEAR)
        
        return float(vol)
    
    @staticmethod
    def garman_klass_volatility(
        high: np.ndarray,
        low: np.ndarray,
        open_price: np.ndarray,
        close: np.ndarray,
        annualize: bool = True
    ) -> float:
        """
        计算 Garman-Klass 波动率（1980）
        
        公式: σ²_GK = 1/n × Σ[0.5·ln(H/L)² - (2ln2-1)·ln(C/O)²]
        
        优点：
            - 使用 OHLC 全部信息
            - 估计效率是历史波动率的 7 倍
            - 考虑了开盘跳空和日内波动
        
        Args:
            high: 最高价序列
            low: 最低价序列
            open_price: 开盘价序列
            close: 收盘价序列
            annualize: 是否年化
        
        Returns:
            Garman-Klass 波动率（年化）
        """
        # 转换为 float
        high = np.array(high, dtype=np.float64)
        low = np.array(low, dtype=np.float64)
        open_price = np.array(open_price, dtype=np.float64)
        close = np.array(close, dtype=np.float64)
        
        n = len(high)
        if n < 2:
            return np.nan
        
        # 计算 ln(H/L) 和 ln(C/O)
        hl_log = np.log(high / low)
        co_log = np.log(close / open_price)
        
        # 检查无效值
        valid_mask = np.isfinite(hl_log) & np.isfinite(co_log)
        if valid_mask.sum() < 2:
            return np.nan
        
        hl_log = hl_log[valid_mask]
        co_log = co_log[valid_mask]
        n_valid = len(hl_log)
        
        # Garman-Klass 公式
        variance = (1 / n_valid) * np.sum(
            0.5 * hl_log ** 2 - (2 * np.log(2) - 1) * co_log ** 2
        )
        
        # 确保方差非负
        variance = max(variance, 0)
        
        vol = np.sqrt(variance)
        
        if annualize:
            vol = vol * np.sqrt(TRADING_DAYS_PER_YEAR)
        
        return float(vol)
    
    @staticmethod
    def atr(
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        period: int = 14
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        计算 ATR (Average True Range)
        
        TR = max(H-L, |H-前C|, |L-前C|)
        ATR = TR 的 N 日移动平均
        NATR = ATR / C × 100
        
        Args:
            high: 最高价序列
            low: 最低价序列
            close: 收盘价序列
            period: ATR 周期
        
        Returns:
            (ATR序列, NATR序列)
        """
        # 转换为 float
        high = np.array(high, dtype=np.float64)
        low = np.array(low, dtype=np.float64)
        close = np.array(close, dtype=np.float64)
        
        n = len(high)
        if n < period:
            return np.array([np.nan]), np.array([np.nan])
        
        # 计算 True Range
        tr = np.zeros(n)
        tr[0] = high[0] - low[0]  # 第一天用 H-L
        
        for i in range(1, n):
            tr[i] = max(
                high[i] - low[i],
                abs(high[i] - close[i-1]),
                abs(low[i] - close[i-1])
            )
        
        # 计算 ATR（使用 EMA）
        atr_values = np.zeros(n)
        atr_values[:period] = np.nan
        atr_values[period-1] = np.mean(tr[:period])
        
        multiplier = 2 / (period + 1)
        for i in range(period, n):
            atr_values[i] = (tr[i] - atr_values[i-1]) * multiplier + atr_values[i-1]
        
        # 计算 NATR
        natr_values = (atr_values / close) * 100
        
        return atr_values, natr_values
    
    # =====================================================
    # GARCH(1,1) 模型
    # =====================================================
    
    def garch_estimate(
        self, 
        returns: np.ndarray,
        max_iter: int = 1000,
        tol: float = 1e-6
    ) -> Optional[Dict]:
        """
        使用极大似然估计拟合 GARCH(1,1) 模型
        
        模型：
            r_t = μ + ε_t
            ε_t = σ_t × z_t,  z_t ~ N(0,1)
            σ²_t = ω + α·ε²_(t-1) + β·σ²_(t-1)
        
        约束条件：
            ω > 0, α ≥ 0, β ≥ 0, α + β < 1
        
        Args:
            returns: 收益率序列
            max_iter: 最大迭代次数
            tol: 收敛阈值
        
        Returns:
            {
                'omega': 长期方差项,
                'alpha': ARCH 项系数,
                'beta': GARCH 项系数,
                'persistence': 持续性 (α+β),
                'long_run_vol': 长期均衡波动率,
                'conditional_vol': 条件波动率序列,
                'forecast': 预测波动率
            }
        """
        # 数据预处理
        returns = np.asarray(returns, dtype=np.float64)
        returns = returns[~np.isnan(returns)]
        
        n = len(returns)
        if n < 100:
            self.logger.warning(f"数据量不足 (n={n})，GARCH 需要至少100个观测值")
            return None
        
        # 去除均值
        mu = np.mean(returns)
        residuals = returns - mu
        
        # 初始参数估计
        var_init = np.var(residuals, ddof=1)
        
        # 初始值：使用经验值
        omega_init = var_init * 0.05
        alpha_init = 0.10
        beta_init = 0.85
        
        # 参数向量
        params = np.array([omega_init, alpha_init, beta_init])
        
        def garch_likelihood(params):
            """计算负对数似然函数"""
            omega, alpha, beta = params
            
            # 约束检查
            if omega <= 0 or alpha < 0 or beta < 0 or alpha + beta >= 1:
                return 1e10
            
            # 计算条件方差
            cond_var = np.zeros(n)
            cond_var[0] = var_init
            
            for i in range(1, n):
                cond_var[i] = omega + alpha * residuals[i-1]**2 + beta * cond_var[i-1]
                
                # 确保方差为正
                if cond_var[i] <= 0:
                    return 1e10
            
            # 对数似然（正态分布假设）
            ll = -0.5 * np.sum(np.log(2 * np.pi) + np.log(cond_var) + residuals**2 / cond_var)
            
            return -ll  # 返回负值用于最小化
        
        # 使用数值优化
        from scipy.optimize import minimize
        
        try:
            result = minimize(
                garch_likelihood,
                params,
                method='L-BFGS-B',
                bounds=[
                    (1e-10, None),    # omega > 0
                    (0, 0.5),          # 0 <= alpha < 0.5
                    (0, 0.99)          # 0 <= beta < 0.99
                ],
                options={'maxiter': max_iter, 'ftol': tol}
            )
            
            if not result.success:
                self.logger.warning(f"GARCH 优化失败: {result.message}")
                return None
            
            omega, alpha, beta = result.x
            
            # 重新计算条件方差
            cond_var = np.zeros(n)
            cond_var[0] = var_init
            for i in range(1, n):
                cond_var[i] = omega + alpha * residuals[i-1]**2 + beta * cond_var[i-1]
            
            cond_vol = np.sqrt(cond_var)
            
            # 长期均衡波动率
            long_run_var = omega / (1 - alpha - beta)
            long_run_vol = np.sqrt(long_run_var * TRADING_DAYS_PER_YEAR) if long_run_var > 0 else np.nan
            
            # 预测未来波动率（5天）
            persistence = alpha + beta
            forecast_var = cond_var[-1]
            for _ in range(5):
                forecast_var = omega + persistence * forecast_var
            forecast_vol = np.sqrt(forecast_var * TRADING_DAYS_PER_YEAR)
            
            # 年化当前条件波动率
            current_vol = cond_vol[-1] * np.sqrt(TRADING_DAYS_PER_YEAR)
            
            return {
                'omega': omega,
                'alpha': alpha,
                'beta': beta,
                'persistence': persistence,
                'long_run_vol': long_run_vol,
                'conditional_vol': current_vol,
                'forecast_5d': forecast_vol,
                'n_obs': n
            }
            
        except Exception as e:
            self.logger.error(f"GARCH 拟合异常: {e}")
            return None
    
    # =====================================================
    # 单只股票完整计算
    # =====================================================
    
    def calculate_single_stock(
        self, 
        stock_code: str,
        min_days: int = 60,
        garch_min_days: int = 500
    ) -> Optional[pd.DataFrame]:
        """
        计算单只股票的所有波动率指标
        
        Args:
            stock_code: 股票代码
            min_days: 最小数据天数
            garch_min_days: GARCH 模型最小数据天数
        
        Returns:
            包含波动率指标的 DataFrame
        """
        # 1. 获取行情数据
        sql = """
            SELECT stock_date, open_price, high_price, low_price, close_price, pre_close
            FROM stock_history_date_price
            WHERE stock_code = %s AND tradestatus = 1
            ORDER BY stock_date ASC
        """
        result = self.mysql.query_all(sql, (stock_code,))
        
        if not result or len(result) < min_days:
            self.logger.warning(f"{stock_code}: 数据不足 ({len(result) if result else 0} < {min_days})")
            return None
        
        df = pd.DataFrame(result)
        
        # 2. 计算收益率
        df['returns'] = df['close_price'].pct_change()
        
        # 3. 按日期计算滚动波动率
        results = []
        
        # 从第60天开始计算
        for i in range(59, len(df)):
            row_data = {
                'stock_code': stock_code,
                'stock_date': df.iloc[i]['stock_date']
            }
            
            # 20天窗口
            if i >= 19:
                window_20 = df.iloc[i-19:i+1]
                
                # 历史波动率
                returns_20 = window_20['returns'].dropna().values
                row_data['hist_vol_20'] = self.historical_volatility(returns_20)
                
                # Parkinson 波动率
                row_data['parkinson_vol_20'] = self.parkinson_volatility(
                    window_20['high_price'].values,
                    window_20['low_price'].values
                )
                
                # Garman-Klass 波动率
                row_data['gk_vol_20'] = self.garman_klass_volatility(
                    window_20['high_price'].values,
                    window_20['low_price'].values,
                    window_20['open_price'].values,
                    window_20['close_price'].values
                )
            
            # 60天窗口
            if i >= 59:
                window_60 = df.iloc[i-59:i+1]
                
                returns_60 = window_60['returns'].dropna().values
                row_data['hist_vol_60'] = self.historical_volatility(returns_60)
                
                row_data['parkinson_vol_60'] = self.parkinson_volatility(
                    window_60['high_price'].values,
                    window_60['low_price'].values
                )
            
            # ATR
            if i >= 13:
                window_atr = df.iloc[i-13:i+1]
                atr_vals, natr_vals = self.atr(
                    window_atr['high_price'].values,
                    window_atr['low_price'].values,
                    window_atr['close_price'].values,
                    period=14
                )
                row_data['atr_14'] = atr_vals[-1]
                row_data['natr_14'] = natr_vals[-1]
            
            results.append(row_data)
        
        if not results:
            return None
        
        result_df = pd.DataFrame(results)
        
        # 4. 计算 GARCH（只对最近数据）
        if len(df) >= garch_min_days:
            returns = df['returns'].dropna().values[-1000:]  # 使用最近1000天
            garch_result = self.garch_estimate(returns)
            
            if garch_result:
                # 只更新最新一天
                result_df.loc[result_df.index[-1], 'garch_vol'] = garch_result['conditional_vol']
                result_df.loc[result_df.index[-1], 'garch_forecast_5d'] = garch_result['forecast_5d']
                result_df.loc[result_df.index[-1], 'garch_persistence'] = garch_result['persistence']
        
        # 5. 计算波动率变化
        if len(result_df) > 5:
            result_df['vol_change_5d'] = result_df['parkinson_vol_20'].pct_change(5) * 100
        if len(result_df) > 20:
            result_df['vol_change_20d'] = result_df['parkinson_vol_20'].pct_change(20) * 100
        
        # 6. 清理无效值
        result_df = result_df.replace({np.nan: None, np.inf: None, -np.inf: None})
        
        return result_df
    
    # =====================================================
    # 批量计算（支持断点续传）
    # =====================================================
    
    def calculate_batch(
        self, 
        batch_size: int = 50,
        delay: float = 0.3,
        max_retries: int = 3
    ):
        """
        批量计算所有股票的波动率
        
        Args:
            batch_size: 每批处理数量
            delay: 请求间隔
            max_retries: 最大重试次数
        """
        self.logger.info("=== 开始批量计算波动率 ===")
        
        retry_count = 0
        
        while retry_count <= max_retries:
            # 获取待处理股票
            if self.redis:
                redis_key = "volatility:calculation"
                pending = self.redis.get_unprocessed_stocks(self.now_date, redis_key)
                
                if not pending:
                    # 从数据库初始化
                    sql = """
                        SELECT DISTINCT stock_code 
                        FROM stock_history_date_price 
                        WHERE tradestatus = 1
                    """
                    result = self.mysql.query_all(sql)
                    pending = [row['stock_code'] for row in result]
                    self.redis.add_unprocessed_stocks(pending, self.now_date, redis_key)
                    self.logger.info(f"初始化 {len(pending)} 只股票")
                else:
                    self.logger.info(f"断点续传: {len(pending)} 只待处理")
            else:
                sql = """
                    SELECT DISTINCT stock_code 
                    FROM stock_history_date_price 
                    WHERE tradestatus = 1
                """
                result = self.mysql.query_all(sql)
                pending = [row['stock_code'] for row in result]
            
            if not pending:
                self.logger.info("✅ 所有股票已处理完成")
                return
            
            total = len(pending)
            success = 0
            failed = 0
            
            for i, stock_code in enumerate(pending):
                try:
                    # 计算波动率
                    df = self.calculate_single_stock(stock_code)
                    
                    if df is not None and not df.empty:
                        # 清理 NaN
                        df = df.replace({np.nan: None})
                        
                        # 保存到数据库
                        count = self.mysql.batch_insert_or_update(
                            'stock_date_volatility',
                            df,
                            ['stock_code', 'stock_date']
                        )
                        
                        if count > 0:
                            success += 1
                            
                            # 更新记录表
                            max_date = df['stock_date'].max()
                            garch_fitted = 1 if df['garch_vol'].notna().any() else 0
                            
                            sql = """
                                INSERT INTO stock_volatility_record 
                                (stock_code, update_date_vol, garch_fitted, data_days)
                                VALUES (%s, %s, %s, %s)
                                ON DUPLICATE KEY UPDATE 
                                    update_date_vol = VALUES(update_date_vol),
                                    garch_fitted = VALUES(garch_fitted),
                                    data_days = VALUES(data_days)
                            """
                            self.mysql.execute(sql, (stock_code, max_date, garch_fitted, len(df)))
                    
                    # 标记已处理
                    if self.redis:
                        self.redis.remove_unprocessed_stocks([stock_code], self.now_date, "volatility:calculation")
                    
                    # 进度报告
                    if (i + 1) % batch_size == 0:
                        self.logger.info(f"进度: {i+1}/{total}, 成功: {success}, 失败: {failed}")
                    
                    time.sleep(delay)
                    
                except Exception as e:
                    self.logger.error(f"{stock_code} 计算失败: {e}")
                    failed += 1
            
            self.logger.info(f"本轮完成: 成功 {success}, 失败 {failed}")
            
            # 检查是否还有剩余
            if self.redis:
                remaining = self.redis.get_unprocessed_stocks(self.now_date, "volatility:calculation")
            else:
                remaining = []
            
            if not remaining:
                self.logger.info("✅ 全部计算完成")
                return
            
            retry_count += 1
            if retry_count <= max_retries:
                self.logger.info(f"仍有 {len(remaining)} 只待处理，5秒后重试...")
                time.sleep(5)
        
        self.logger.warning("达到最大重试次数")


def main():
    """测试入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='波动率因子计算')
    parser.add_argument('--test', type=str, help='测试单只股票')
    parser.add_argument('--all', action='store_true', help='计算所有股票')
    
    args = parser.parse_args()
    
    calc = VolatilityCalculator()
    
    try:
        if args.test:
            # 测试单只股票
            print(f"\n=== 测试 {args.test} 波动率计算 ===\n")
            df = calc.calculate_single_stock(args.test)
            
            if df is not None:
                print(f"计算成功，共 {len(df)} 条记录")
                print("\n最新10条数据:")
                print(df.tail(10).to_string())
                
                # 统计
                print(f"\n统计信息:")
                print(f"  Parkinson 20日波动率: {df['parkinson_vol_20'].mean():.2%}")
                print(f"  GARCH 当前波动率: {df['garch_vol'].dropna().iloc[-1] if not df['garch_vol'].dropna().empty else 'N/A'}")
            else:
                print("计算失败")
        
        elif args.all:
            calc.calculate_batch()
        
        else:
            # 默认测试
            calc.calculate_single_stock('000001')
    
    finally:
        calc.close()


if __name__ == '__main__':
    main()
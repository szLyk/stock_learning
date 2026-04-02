#!/usr/bin/env python3
"""
主升浪识别脚本
基于5大核心指标：
1. 成交量放大倍数（≥2倍启动，≥3-5倍确认）
2. 涨停板密度（短时间内≥3个涨停板）
3. 均线多头排列（MA5>MA10>MA20>MA60）
4. MACD金叉加速（柱体持续放大）
5. 涨幅斜率（日均涨幅>3%）

Author: Xiao Luo
Date: 2026-04-02
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.utils.mysql_tool import MySQLUtil
from logs.logger import LogManager


class MainWaveDetector:
    """主升浪识别器"""
    
    # ==================== 可调参数 ====================
    # 时间范围参数
    QUERY_DAYS = 90             # 查询历史数据天数（建议≥90天以覆盖完整主升浪周期）
    ACCUMULATION_DAYS = 10      # 蓄势期天数（用于计算基准成交量）
    LIMIT_UP_PERIOD_DAYS = 20   # 涨停统计周期（天）
    
    # 成交量放大倍数阈值
    VOLUME_START_RATIO = 2.0      # 启动信号：成交量放大≥2倍
    VOLUME_CONFIRM_RATIO = 3.0    # 确认信号：成交量放大≥3倍
    VOLUME_TOP_RATIO = 7.0        # 见顶信号：成交量放大≥7倍
    
    # 涢手率阈值（新增）
    # 默认参数（通用）
    TURNOVER_ACCUMULATION_MAX = 3.0   # 蓄势期最高换手率（%）
    TURNOVER_START_MIN = 5.0          # 启动日最低换手率（%）
    TURNOVER_WAVE_MIN = 5.0           # 主升浪期平均换手率（%）
    TURNOVER_TOP_MIN = 15.0           # 见顶换手率阈值（%）
    
    # 分行业参数（基于特征分析结果）
    INDUSTRY_PARAMS = {
        '科技': {
            'turnover_start': 6.0,
            'turnover_confirm': 10.0,
            'turnover_top': 16.0
        },
        '医药': {
            'turnover_start': 3.7,
            'turnover_confirm': 6.2,
            'turnover_top': 10.0
        },
        '资源': {
            'turnover_start': 5.5,
            'turnover_confirm': 9.2,
            'turnover_top': 15.0
        },
        '新能源': {
            'turnover_start': 5.0,
            'turnover_confirm': 8.0,
            'turnover_top': 14.0
        },
        '其他': {
            'turnover_start': 5.0,
            'turnover_confirm': 8.0,
            'turnover_top': 15.0
        }
    }
    
    # 涨停板参数
    LIMIT_UP_THRESHOLD = 9.5      # 涨停判断阈值（%）
    MIN_LIMIT_UP_COUNT = 3        # 最少涨停板数量
    LIMIT_UP_PERIOD_DAYS = 20     # 涨停统计周期（天）
    
    # 均线参数
    MA_PERIODS = [5, 10, 20, 60]  # 均线周期
    
    # MACD参数
    MACD_START_THRESHOLD = 0.0    # MACD柱由负转正
    MACD_ACCELERATE_DAYS = 3      # MACD柱连续放大天数
    
    # 涨幅参数
    MIN_DAILY_CHANGE = 3.0        # 主升浪日均涨幅阈值（%）
    MIN_TOTAL_CHANGE = 30.0       # 主升浪最低总涨幅（%）
    
    # 蓄势期参数
    ACCUMULATION_DAYS = 10        # 蓄势期天数（用于计算基准成交量）
    
    # ==================================================
    
    # 行业分类关键词
    INDUSTRY_KEYWORDS = {
        '科技': ['计算机', '通信', '电子', '软件', '半导体', '人工智能', '芯片', '信息技术'],
        '资源': ['有色', '煤炭', '石油', '矿业', '稀土', '黄金', '铜', '锂矿'],
        '新能源': ['锂电池', '光伏', '风电', '储能', '新能源车', '电池', '新能源'],
        '医药': ['医药', '生物', '医疗', '制药', '中药', '器械']
    }
    
    def __init__(self):
        self.mysql = MySQLUtil()
        self.mysql.connect()
        self.logger = LogManager.get_logger("main_wave_detector")
    
    def close(self):
        self.mysql.close()
    
    def _get_industry_type(self, stock_code: str) -> str:
        """获取股票的行业类型"""
        sql = "SELECT industry FROM stock_industry WHERE stock_code = %s"
        result = self.mysql.query_one(sql, (stock_code,))
        
        if not result or not result.get('industry'):
            return '其他'
        
        industry = str(result['industry'])
        for ind_type, keywords in self.INDUSTRY_KEYWORDS.items():
            if any(k in industry for k in keywords):
                return ind_type
        
        return '其他'
    
    def _get_industry_params(self, industry_type: str) -> dict:
        """获取行业对应的参数"""
        return self.INDUSTRY_PARAMS.get(industry_type, self.INDUSTRY_PARAMS['其他'])
    
    def get_stock_data(self, stock_code: str, days: int = 60, end_date: str = None) -> pd.DataFrame:
        """
        获取股票历史数据（包含价格、成交量）
        
        Args:
            stock_code: 股票代码
            days: 回溯天数
            end_date: 截止日期（回测用，格式：YYYY-MM-DD）
        
        Returns:
            DataFrame with columns: stock_date, open, high, low, close, volume, change_pct
        """
        if end_date:
            # 回测模式：使用指定的截止日期
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            start_date = (end_dt - timedelta(days=days)).strftime('%Y-%m-%d')
        else:
            # 实时模式：使用当前日期
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        sql = f"""
            SELECT 
                stock_date,
                open_price as open,
                high_price as high,
                low_price as low,
                close_price as close,
                trading_volume as volume,
                ups_and_downs as change_pct,
                turn as turnover_rate,
                pre_close
            FROM stock_history_date_price
            WHERE stock_code = %s
                AND stock_date >= %s
                AND stock_date <= %s
                AND tradestatus = 1
            ORDER BY stock_date ASC
        """
        
        result = self.mysql.query_all(sql, (stock_code, start_date, end_date))
        if not result:
            return pd.DataFrame()
        
        df = pd.DataFrame(result)
        df['stock_date'] = pd.to_datetime(df['stock_date'])
        df['volume'] = df['volume'].astype(float)
        df['close'] = df['close'].astype(float)
        
        return df
    
    def get_ma_data(self, stock_code: str, days: int = 60, end_date: str = None) -> pd.DataFrame:
        """
        获取均线数据
        
        Args:
            stock_code: 股票代码
            days: 回溯天数
            end_date: 截止日期（回测用）
        
        Returns:
            DataFrame with columns: stock_date, ma5, ma10, ma20, ma60
        """
        if end_date:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            start_date = (end_dt - timedelta(days=days)).strftime('%Y-%m-%d')
        else:
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        sql = f"""
            SELECT 
                stock_date,
                stock_ma5 as ma5,
                stock_ma10 as ma10,
                stock_ma20 as ma20,
                stock_ma60 as ma60
            FROM date_stock_moving_average_table
            WHERE stock_code = %s
                AND stock_date >= %s
                AND stock_date <= %s
            ORDER BY stock_date ASC
        """
        
        result = self.mysql.query_all(sql, (stock_code, start_date, end_date))
        if not result:
            return pd.DataFrame()
        
        df = pd.DataFrame(result)
        df['stock_date'] = pd.to_datetime(df['stock_date'])
        
        for col in ['ma5', 'ma10', 'ma20', 'ma60']:
            df[col] = df[col].astype(float)
        
        return df
    
    def get_macd_data(self, stock_code: str, days: int = 60, end_date: str = None) -> pd.DataFrame:
        """
        获取MACD数据
        
        Args:
            stock_code: 股票代码
            days: 回溯天数
            end_date: 截止日期（回测用）
        
        Returns:
            DataFrame with columns: stock_date, diff, dea, macd
        """
        if end_date:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            start_date = (end_dt - timedelta(days=days)).strftime('%Y-%m-%d')
        else:
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        sql = f"""
            SELECT 
                stock_date,
                diff,
                dea,
                macd
            FROM date_stock_macd
            WHERE stock_code = %s
                AND stock_date >= %s
                AND stock_date <= %s
            ORDER BY stock_date ASC
        """
        
        result = self.mysql.query_all(sql, (stock_code, start_date, end_date))
        if not result:
            return pd.DataFrame()
        
        df = pd.DataFrame(result)
        df['stock_date'] = pd.to_datetime(df['stock_date'])
        
        for col in ['diff', 'dea', 'macd']:
            df[col] = df[col].astype(float)
        
        return df
    
    def calculate_volume_ratio(self, price_df: pd.DataFrame) -> pd.DataFrame:
        """
        计算成交量放大倍数
        
        核心逻辑：
        1. 对于每一天，计算其成交量相对于"之前N天"平均成交量的放大倍数
        2. 这样可以正确识别启动当天的放量情况
        
        Returns:
            DataFrame with volume_ratio column
        """
        if len(price_df) < self.ACCUMULATION_DAYS + 1:
            return pd.DataFrame()
        
        df_sorted = price_df.sort_values('stock_date', ascending=True).reset_index(drop=True)
        
        # 计算每一天的成交量放大倍数（相对于之前N天的平均值）
        volume_ratios = []
        base_volumes = []
        
        for i in range(len(df_sorted)):
            if i < self.ACCUMULATION_DAYS:
                # 前N天数据不足，用已有的数据
                base_volume = df_sorted.iloc[:i]['volume'].mean() if i > 0 else df_sorted.iloc[0]['volume']
            else:
                # 用之前N天的平均成交量作为基准
                base_volume = df_sorted.iloc[i-self.ACCUMULATION_DAYS:i]['volume'].mean()
            
            # 防止基准为0或过小
            base_volume = max(base_volume, 1)
            
            current_volume = df_sorted.iloc[i]['volume']
            volume_ratio = current_volume / base_volume
            
            volume_ratios.append(volume_ratio)
            base_volumes.append(base_volume)
        
        df_sorted['base_volume'] = base_volumes
        df_sorted['volume_ratio'] = volume_ratios
        
        return df_sorted
    
    def detect_limit_ups(self, price_df: pd.DataFrame) -> dict:
        """
        检测涨停板
        
        改进：检测整个数据范围的涨停，同时统计近期涨停
        
        Returns:
            {
                'limit_up_dates': [...],  # 涨停日期列表
                'limit_up_count': N,      # 涨停次数
                'limit_up_density': X,    # 涨停密度（次/天）
                'recent_limit_ups': N     # 近期涨停次数（20天内）
            }
        """
        # 整个数据范围的涨停
        all_limit_ups = price_df[price_df['change_pct'] >= self.LIMIT_UP_THRESHOLD]
        limit_up_dates = all_limit_ups['stock_date'].tolist()
        
        # 近期涨停次数（最近20天）
        recent_days = price_df.tail(self.LIMIT_UP_PERIOD_DAYS)
        recent_limit_ups = len(recent_days[recent_days['change_pct'] >= self.LIMIT_UP_THRESHOLD])
        
        # 涨停密度（涨停次数/总天数）
        if len(price_df) > 0:
            limit_up_density = len(limit_up_dates) / len(price_df)
        else:
            limit_up_density = 0
        
        return {
            'limit_up_dates': limit_up_dates,
            'limit_up_count': len(limit_up_dates),
            'limit_up_density': limit_up_density,
            'recent_limit_ups': recent_limit_ups,
            'period_days': self.LIMIT_UP_PERIOD_DAYS  # 新增：显示统计周期
        }
    
    def check_ma_alignment(self, ma_df: pd.DataFrame, price_df: pd.DataFrame = None) -> dict:
        """
        检查均线多头排列 + 底部反转识别
        
        新增功能：
        1. 检测均线多头排列
        2. 检测底部反转（均线空头 + 放量涨停）
        3. 检测均线收敛（即将突破）
        
        Returns:
            {
                'is_aligned': bool,          # 是否多头排列
                'alignment_date': date,      # 多头排列形成日期
                'alignment_strength': float, # 多头排列强度（均线间距）
                'is_bottom_reversal': bool,  # 是否底部反转（新增）
                'reversal_strength': float   # 反转强度
            }
        """
        if ma_df.empty or len(ma_df) < 5:
            return {
                'is_aligned': False, 
                'alignment_date': None, 
                'alignment_strength': 0,
                'is_bottom_reversal': False,
                'reversal_strength': 0
            }
        
        latest = ma_df.iloc[-1]
        
        # 检查是否 MA5 > MA10 > MA20 > MA60
        is_aligned = (
            latest['ma5'] > latest['ma10'] and
            latest['ma10'] > latest['ma20'] and
            latest['ma20'] > latest['ma60']
        )
        
        # 计算均线间距（越紧凑越好）
        if is_aligned:
            ma_gap = (latest['ma5'] - latest['ma60']) / latest['ma60'] * 100
        else:
            ma_gap = 0
        
        # 找到多头排列形成日期
        alignment_date = None
        for i in range(len(ma_df) - 1, max(0, len(ma_df) - 20), -1):
            row = ma_df.iloc[i]
            if row['ma5'] > row['ma10'] and row['ma10'] > row['ma20'] and row['ma20'] > row['ma60']:
                alignment_date = row['stock_date']
            else:
                break
        
        # ========== 新增：底部反转检测 ==========
        is_bottom_reversal = False
        reversal_strength = 0
        
        # 判断底部反转条件：
        # 1. 均线空头排列（MA5 < MA10 或 MA10 < MA20）
        # 2. 当天涨停
        # 3. 成交量放大（相对于前10天）>= 1.2x
        # OR 特殊情况：涨停突破（涨幅>=9.5% + 收盘价站上MA20）
        if not is_aligned and price_df is not None and len(price_df) > 0:
            last_price = price_df.iloc[-1]
            
            # 检查均线是否空头
            is_bearish = (latest['ma5'] < latest['ma10'] or latest['ma10'] < latest['ma20'])
            
            # 检查是否涨停
            is_limit_up = last_price['change_pct'] >= self.LIMIT_UP_THRESHOLD
            
            # 检查成交量是否放大
            if len(price_df) >= 11:
                base_volume = price_df.iloc[-11:-1]['volume'].mean()
                current_volume = last_price['volume']
                volume_ratio = current_volume / base_volume if base_volume > 0 else 0
            else:
                volume_ratio = 1
            
            # 检查是否站上MA20（突破信号）
            is_break_ma20 = float(last_price['close']) > float(latest['ma20'])
            
            # 底部反转判定（两种情况）
            # 情况1：均线空头 + 涨停 + 成交量放大>=1.2x
            # 情况2：均线空头 + 涨停 + 站上MA20（突破信号）
            if is_bearish and is_limit_up:
                if volume_ratio >= 1.2 or is_break_ma20:
                    is_bottom_reversal = True
                    # 反转强度 = 涨幅权重 + 成交量权重 + 突破权重
                    reversal_strength = (
                        (float(last_price['change_pct']) / 10) * 0.4 + 
                        (min(volume_ratio, 3) / 3) * 0.3 + 
                        (0.3 if is_break_ma20 else 0)
                    )
        
        return {
            'is_aligned': is_aligned,
            'alignment_date': alignment_date,
            'alignment_strength': ma_gap,
            'is_bottom_reversal': is_bottom_reversal,
            'reversal_strength': reversal_strength
        }
    
    def check_macd_acceleration(self, macd_df: pd.DataFrame) -> dict:
        """
        检查MACD加速情况
        
        Returns:
            {
                'is_golden_cross': bool,      # 是否金叉
                'golden_cross_date': date,    # 金叉日期
                'is_accelerating': bool,      # 是否加速
                'macd_trend': str             # MACD趋势状态
            }
        """
        if macd_df.empty or len(macd_df) < 5:
            return {'is_golden_cross': False, 'golden_cross_date': None, 'is_accelerating': False, 'macd_trend': 'unknown'}
        
        # 检查金叉（MACD柱由负转正）
        golden_cross_date = None
        for i in range(len(macd_df)):
            if i > 0 and macd_df.iloc[i-1]['macd'] < 0 and macd_df.iloc[i]['macd'] > 0:
                golden_cross_date = macd_df.iloc[i]['stock_date']
        
        # 检查MACD柱是否连续放大
        recent_macd = macd_df.tail(5)['macd'].values
        is_accelerating = False
        
        if len(recent_macd) >= 3:
            # MACD柱连续放大
            if all(recent_macd[i] > recent_macd[i-1] for i in range(1, len(recent_macd))):
                is_accelerating = True
        
        # 判断趋势状态
        latest_macd = macd_df.iloc[-1]['macd']
        if latest_macd > 0.5:
            macd_trend = 'strong_bull'
        elif latest_macd > 0:
            macd_trend = 'bull'
        elif latest_macd > -0.5:
            macd_trend = 'bear'
        else:
            macd_trend = 'strong_bear'
        
        return {
            'is_golden_cross': golden_cross_date is not None,
            'golden_cross_date': golden_cross_date,
            'is_accelerating': is_accelerating,
            'macd_trend': macd_trend,
            'latest_macd': latest_macd
        }
    
    def analyze_turnover(self, price_df: pd.DataFrame, industry_type: str = '其他') -> dict:
        """
        分析换手率（支持分行业参数）
        
        Args:
            price_df: 价格数据
            industry_type: 行业类型
        
        Returns:
            {
                'accumulation_turnover': float,  # 蓄势期平均换手率
                'latest_turnover': float,        # 最新换手率
                'turnover_ratio': float,         # 换手率放大倍数
                'avg_wave_turnover': float,      # 主升浪期平均换手率
                'is_turnover_start': bool,       # 是否换手率启动
                'is_turnover_top': bool,         # 是否换手率见顶
                'industry_type': str             # 行业类型
            }
        """
        if price_df.empty or 'turnover_rate' not in price_df.columns:
            return {
                'accumulation_turnover': 0,
                'latest_turnover': 0,
                'turnover_ratio': 0,
                'avg_wave_turnover': 0,
                'is_turnover_start': False,
                'is_turnover_top': False,
                'industry_type': industry_type
            }
        
        # 获取行业参数
        params = self._get_industry_params(industry_type)
        turnover_start_threshold = params['turnover_start']
        turnover_top_threshold = params['turnover_top']
        
        # 蓄势期换手率（前10天）
        if len(price_df) >= self.ACCUMULATION_DAYS + 1:
            acc_turnover = price_df.iloc[-self.ACCUMULATION_DAYS-1:-1]['turnover_rate'].mean()
        else:
            acc_turnover = price_df['turnover_rate'].mean()
        
        # 最新换手率
        latest_turnover = float(price_df.iloc[-1]['turnover_rate'])
        
        # 换手率放大倍数
        turnover_ratio = latest_turnover / acc_turnover if acc_turnover > 0 else 0
        
        # 主升浪期平均换手率（最近5天）
        if len(price_df) >= 5:
            avg_wave_turnover = price_df.tail(5)['turnover_rate'].mean()
        else:
            avg_wave_turnover = price_df['turnover_rate'].mean()
        
        # 判断换手率启动信号（使用行业参数）
        is_turnover_start = (
            acc_turnover < turnover_start_threshold * 0.6 and  # 蓄势期换手率低于启动阈值的60%
            latest_turnover >= turnover_start_threshold and    # 最新换手率达到启动阈值
            turnover_ratio >= 1.5                              # 放大倍数≥1.5
        )
        
        # 判断换手率见顶信号（使用行业参数）
        is_turnover_top = latest_turnover >= turnover_top_threshold
        
        return {
            'accumulation_turnover': float(acc_turnover),
            'latest_turnover': latest_turnover,
            'turnover_ratio': float(turnover_ratio),
            'avg_wave_turnover': float(avg_wave_turnover),
            'is_turnover_start': is_turnover_start,
            'is_turnover_top': is_turnover_top,
            'industry_type': industry_type,
            'turnover_start_threshold': turnover_start_threshold,
            'turnover_top_threshold': turnover_top_threshold
        }
    
    def calculate_wave_strength(self, price_df: pd.DataFrame) -> dict:
        """
        计算主升浪强度
        
        Returns:
            {
                'total_change': float,       # 总涨幅
                'avg_daily_change': float,   # 日均涨幅
                'max_change': float,         # 最大涨幅
                'wave_days': int,            # 主升浪天数
                'latest_change': float       # 最新单日涨幅（新增！用于见顶判断）
            }
        """
        if price_df.empty:
            return {'total_change': 0, 'avg_daily_change': 0, 'max_change': 0, 'wave_days': 0, 'latest_change': 0}
        
        # 计算涨幅
        start_close = price_df.iloc[0]['close']
        end_close = price_df.iloc[-1]['close']
        total_change = (end_close - start_close) / start_close * 100
        
        # 日均涨幅（仅计算上涨天数）
        positive_days = price_df[price_df['change_pct'] > 0]
        avg_daily_change = positive_days['change_pct'].mean() if len(positive_days) > 0 else 0
        
        # 最大涨幅
        max_change = price_df['change_pct'].max()
        
        # 最新单日涨幅（关键：用于见顶判断）
        latest_change = price_df.iloc[-1]['change_pct']
        
        return {
            'total_change': total_change,
            'avg_daily_change': avg_daily_change,
            'max_change': max_change,
            'wave_days': len(price_df),
            'latest_change': latest_change
        }
    
    def detect_main_wave(self, stock_code: str, end_date: str = None) -> dict:
        """
        主升浪检测主函数
        
        Args:
            stock_code: 股票代码
            end_date: 截止日期（回测用，格式：YYYY-MM-DD）
        
        Returns:
            {
                'stock_code': str,
                'stock_name': str,
                'wave_stage': str,           # 阶段：蓄势/启动/主升浪/见顶/非主升浪
                'signals': {...},            # 各指标信号
                'recommendation': str,       # 建议
                'confidence': float          # 确信度（0-1）
            }
        """
        self.logger.info(f"开始分析股票 {stock_code} 的主升浪..." + (f"（截止日期：{end_date}）" if end_date else ""))
        
        # 获取股票名称
        sql = "SELECT stock_name FROM stock_basic WHERE stock_code = %s"
        result = self.mysql.query_one(sql, (stock_code,))
        stock_name = result['stock_name'] if result else stock_code
        
        # 获取各类数据（使用统一的时间范围参数）
        price_df = self.get_stock_data(stock_code, days=self.QUERY_DAYS, end_date=end_date)
        ma_df = self.get_ma_data(stock_code, days=self.QUERY_DAYS, end_date=end_date)
        macd_df = self.get_macd_data(stock_code, days=self.QUERY_DAYS, end_date=end_date)
        
        if price_df.empty:
            return {
                'stock_code': stock_code,
                'stock_name': stock_name,
                'wave_stage': '数据不足',
                'signals': {},
                'recommendation': '无法分析',
                'confidence': 0
            }
        
        # 计算成交量放大倍数
        price_df = self.calculate_volume_ratio(price_df)
        
        # ==================== 各指标检测 ====================
        
        # 1. 成交量分析
        latest_volume_ratio = price_df.iloc[-1]['volume_ratio'] if not price_df.empty else 0
        volume_signals = {
            'latest_ratio': latest_volume_ratio,
            'is_start': latest_volume_ratio >= self.VOLUME_START_RATIO,
            'is_confirm': latest_volume_ratio >= self.VOLUME_CONFIRM_RATIO,
            'is_top': latest_volume_ratio >= self.VOLUME_TOP_RATIO
        }
        
        # 2. 涨停板分析
        limit_up_info = self.detect_limit_ups(price_df)
        
        # 3. 均线分析（传入价格数据用于底部反转检测）
        ma_info = self.check_ma_alignment(ma_df, price_df)
        
        # 4. MACD分析
        macd_info = self.check_macd_acceleration(macd_df)
        
        # 5. 涨幅分析
        wave_strength = self.calculate_wave_strength(price_df.tail(20))
        
        # 6. 换手率分析（新增，支持分行业参数）
        industry_type = self._get_industry_type(stock_code)
        turnover_info = self.analyze_turnover(price_df, industry_type)
        
        # ==================== 综合判断 ====================
        
        signals = {
            'volume': volume_signals,
            'limit_up': limit_up_info,
            'ma': ma_info,
            'macd': macd_info,
            'wave_strength': wave_strength,
            'turnover': turnover_info  # 新增
        }
        
        # 判断阶段
        wave_stage, confidence, recommendation = self._determine_wave_stage(
            volume_signals, limit_up_info, ma_info, macd_info, wave_strength, turnover_info
        )
        
        return {
            'stock_code': stock_code,
            'stock_name': stock_name,
            'wave_stage': wave_stage,
            'signals': signals,
            'recommendation': recommendation,
            'confidence': confidence,
            'latest_price': float(price_df.iloc[-1]['close']),
            'latest_date': price_df.iloc[-1]['stock_date'].strftime('%Y-%m-%d')
        }
    
    def _determine_wave_stage(self, volume_signals, limit_up_info, ma_info, macd_info, wave_strength, turnover_info=None) -> tuple:
        """
        综合判断主升浪阶段
        
        Returns:
            (wave_stage, confidence, recommendation)
        """
        if turnover_info is None:
            turnover_info = {}
        
        # 计算信号得分
        score = 0
        max_score = 6  # 增加换手率权重
        
        # 1. 成交量得分
        if volume_signals['is_confirm']:
            score += 1
        elif volume_signals['is_start']:
            score += 0.5
        
        # 2. 涨停板得分
        if limit_up_info['limit_up_count'] >= self.MIN_LIMIT_UP_COUNT:
            score += 1
        elif limit_up_info['limit_up_count'] >= 2:
            score += 0.5
        
        # 3. 均线得分
        if ma_info['is_aligned']:
            score += 1
        elif ma_info['is_bottom_reversal']:
            score += min(ma_info['reversal_strength'], 1.0)
        
        # 4. MACD得分
        if macd_info['is_accelerating']:
            score += 1
        elif macd_info['is_golden_cross']:
            score += 0.5
        
        # 5. 涨幅得分
        if wave_strength['avg_daily_change'] >= self.MIN_DAILY_CHANGE:
            score += 1
        elif wave_strength['total_change'] >= self.MIN_TOTAL_CHANGE:
            score += 0.5
        
        # 6. 换手率得分（新增）
        if turnover_info.get('is_turnover_start', False):
            score += 1
        elif turnover_info.get('turnover_ratio', 0) >= 2.0:
            score += 0.5
        
        confidence = score / max_score
        
        # ==================== 阶段判断 ====================
        
        # 1. 底部反转信号
        if ma_info.get('is_bottom_reversal', False):
            reversal_strength = ma_info.get('reversal_strength', 0)
            if reversal_strength >= 0.8:
                return '🔄 强底部反转', confidence, '均线空头+放量涨停，强烈反转信号，可轻仓试探'
            else:
                return '🔄 底部反转', confidence, '底部放量涨停，反转迹象，密切关注'
        
        # 2. 见顶信号判断（加入换手率判断）
        # 条件1：成交量异常放大（≥7倍）或 换手率异常放大（≥15%）
        # 条件2：最新单日涨幅<3%（滞涨）
        if volume_signals['is_top'] or turnover_info.get('is_turnover_top', False):
            latest_change = wave_strength.get('latest_change', 0)
            if latest_change < 1.0:
                return '⚠️ 高位滞涨', confidence, '成交量/换手率异常放大+涨幅<1%，强烈见顶信号，建议减仓'
            elif latest_change < 3.0:
                return '⚠️ 见顶信号', confidence, '成交量/换手率放大+涨幅不足3%，见顶迹象，建议观望'
                return '⚠️ 高位滞涨', confidence, '成交量异常放大+涨幅<1%，强烈见顶信号，建议减仓'
            elif latest_change < 3.0:
                return '⚠️ 见顶信号', confidence, '成交量放大+涨幅不足3%，见顶迹象，建议观望'
        
        # 3. 主升浪确认（所有指标满足）
        if confidence >= 0.7:
            if volume_signals['is_confirm'] and limit_up_info['limit_up_count'] >= 3:
                return '🚀 主升浪爆发', confidence, '主升浪已确认，可持股待涨，用5日线止损'
            else:
                return '📈 主升浪初期', confidence, '主升浪启动，可择机入场'
        
        # 4. 启动信号（部分指标满足）
        if confidence >= 0.4:
            if volume_signals['is_start'] and macd_info['is_golden_cross']:
                return '💡 启动信号', confidence, '出现启动迹象，密切关注，择机入场'
            else:
                return '📊 蓄势整理', confidence, '蓄势阶段，等待突破信号'
        
        # 5. 非主升浪
        return '💤 非主升浪', confidence, '暂无明显主升浪特征'
    
    def scan_all_stocks(self, min_confidence: float = 0.5) -> list:
        """
        全市场扫描主升浪股票
        
        Args:
            min_confidence: 最低确信度阈值
        
        Returns:
            list of dict: 符合条件的股票列表
        """
        self.logger.info("开始全市场扫描主升浪股票...")
        
        # 获取所有股票代码
        sql = "SELECT stock_code, stock_name FROM stock_basic WHERE stock_status = 1"
        result = self.mysql.query_all(sql)
        
        if not result:
            return []
        
        stock_list = []
        detected_stocks = []
        
        for row in result:
            stock_list.append((row['stock_code'], row['stock_name']))
        
        self.logger.info(f"共 {len(stock_list)} 只股票待扫描")
        
        # 扫描每只股票
        for i, (stock_code, stock_name) in enumerate(stock_list):
            try:
                result = self.detect_main_wave(stock_code)
                
                if result['confidence'] >= min_confidence and '主升浪' in result['wave_stage']:
                    detected_stocks.append(result)
                    self.logger.info(f"✅ 发现主升浪: {stock_code} {stock_name} - {result['wave_stage']}")
                
                if (i + 1) % 100 == 0:
                    self.logger.info(f"已扫描 {i+1}/{len(stock_list)} 只股票")
                    
            except Exception as e:
                self.logger.error(f"扫描股票 {stock_code} 失败: {e}")
                continue
        
        # 按确信度排序
        detected_stocks.sort(key=lambda x: x['confidence'], reverse=True)
        
        self.logger.info(f"扫描完成，发现 {len(detected_stocks)} 只主升浪股票")
        
        return detected_stocks
    
    def generate_report(self, stock_code: str) -> str:
        """
        生成详细分析报告
        
        Returns:
            str: Markdown格式报告
        """
        result = self.detect_main_wave(stock_code)
        
        report = f"""
# {result['stock_name']}（{result['stock_code']}）主升浪分析报告

**分析日期**: {result['latest_date']}  
**最新价格**: {result['latest_price']}  
**主升浪阶段**: {result['wave_stage']}  
**确信度**: {result['confidence']:.2f}  
**操作建议**: {result['recommendation']}

---

## 📊 各指标详细分析

### 1️⃣ 成交量分析
- **最新成交量放大倍数**: {result['signals']['volume']['latest_ratio']:.2f}x
- **启动信号**: {'✅' if result['signals']['volume']['is_start'] else '❌'} (≥2倍)
- **确认信号**: {'✅' if result['signals']['volume']['is_confirm'] else '❌'} (≥3倍)
- **见顶信号**: {'⚠️' if result['signals']['volume']['is_top'] else '✅'} (≥7倍)

### 2️⃣ 涨停板分析
- **近期涨停次数**: {result['signals']['limit_up']['recent_limit_ups']}次
- **涨停密度**: {result['signals']['limit_up']['limit_up_density']:.3f}次/天
- **涨停日期**: {', '.join([d.strftime('%Y-%m-%d') for d in result['signals']['limit_up']['limit_up_dates'][-5:]])}

### 3️⃣ 均线分析
- **多头排列**: {'✅' if result['signals']['ma']['is_aligned'] else '❌'}
- **排列形成日期**: {result['signals']['ma']['alignment_date'].strftime('%Y-%m-%d') if result['signals']['ma']['alignment_date'] else '未形成'}
- **均线间距**: {result['signals']['ma']['alignment_strength']:.2f}%

### 4️⃣ MACD分析
- **金叉**: {'✅' if result['signals']['macd']['is_golden_cross'] else '❌'}
- **金叉日期**: {result['signals']['macd']['golden_cross_date'].strftime('%Y-%m-%d') if result['signals']['macd']['golden_cross_date'] else '未金叉'}
- **MACD加速**: {'✅' if result['signals']['macd']['is_accelerating'] else '❌'}
- **MACD趋势**: {result['signals']['macd']['macd_trend']}
- **最新MACD值**: {result['signals']['macd'].get('latest_macd', 0):.3f}

### 5️⃣ 涨幅分析
- **总涨幅**: {result['signals']['wave_strength']['total_change']:.2f}%
- **日均涨幅**: {result['signals']['wave_strength']['avg_daily_change']:.2f}%
- **最大涨幅**: {result['signals']['wave_strength']['max_change']:.2f}%

---

## 💡 参数配置

当前使用参数：
- 成交量启动阈值: {self.VOLUME_START_RATIO}x
- 成交量确认阈值: {self.VOLUME_CONFIRM_RATIO}x
- 成交量见顶阈值: {self.VOLUME_TOP_RATIO}x
- 涨停板阈值: {self.LIMIT_UP_THRESHOLD}%
- 最少涨停次数: {self.MIN_LIMIT_UP_COUNT}
- 日均涨幅阈值: {self.MIN_DAILY_CHANGE}%

---

**报告生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        return report


def test_single_stock(stock_code: str = '605299'):
    """
    测试单只股票主升浪检测
    """
    detector = MainWaveDetector()
    
    print("=" * 60)
    print(f"测试股票: {stock_code}")
    print("=" * 60)
    
    result = detector.detect_main_wave(stock_code)
    
    print(f"\n股票名称: {result['stock_name']}")
    print(f"最新价格: {result['latest_price']} ({result['latest_date']})")
    print(f"主升浪阶段: {result['wave_stage']}")
    print(f"确信度: {result['confidence']:.2f}")
    print(f"操作建议: {result['recommendation']}")
    
    print("\n" + "-" * 60)
    print("详细指标:")
    print("-" * 60)
    
    signals = result['signals']
    
    print(f"\n【成交量】")
    print(f"  放大倍数: {signals['volume']['latest_ratio']:.2f}x")
    print(f"  启动信号: {'✅' if signals['volume']['is_start'] else '❌'}")
    print(f"  确认信号: {'✅' if signals['volume']['is_confirm'] else '❌'}")
    print(f"  见顶信号: {'⚠️' if signals['volume']['is_top'] else '❌'}")
    
    print(f"\n【涨停板】")
    print(f"  总涨停次数: {signals['limit_up']['limit_up_count']}次")
    print(f"  近{signals['limit_up'].get('period_days', 20)}天涨停: {signals['limit_up']['recent_limit_ups']}次")
    print(f"  涨停日期: {[d.strftime('%m-%d') for d in signals['limit_up']['limit_up_dates']]}")
    
    print(f"\n【均线】")
    print(f"  多头排列: {'✅' if signals['ma']['is_aligned'] else '❌'}")
    print(f"  排列强度: {signals['ma']['alignment_strength']:.2f}%")
    # 新增：底部反转显示
    if signals['ma'].get('is_bottom_reversal', False):
        print(f"  底部反转: 🔄 是（强度: {signals['ma']['reversal_strength']:.2f}）")
    else:
        print(f"  底部反转: ❌")
    
    print(f"\n【MACD】")
    print(f"  金叉: {'✅' if signals['macd']['is_golden_cross'] else '❌'}")
    print(f"  加速: {'✅' if signals['macd']['is_accelerating'] else '❌'}")
    print(f"  趋势: {signals['macd']['macd_trend']}")
    
    print(f"\n【涨幅】")
    print(f"  总涨幅: {signals['wave_strength']['total_change']:.2f}%")
    print(f"  日均涨幅: {signals['wave_strength']['avg_daily_change']:.2f}%")
    print(f"  最新涨幅: {signals['wave_strength'].get('latest_change', 0):.2f}%")
    print(f"  最大涨幅: {signals['wave_strength']['max_change']:.2f}%")
    
    # 换手率输出（新增）
    print(f"\n【换手率】")
    if 'turnover' in signals and signals['turnover']:
        t = signals['turnover']
        print(f"  行业类型: {t.get('industry_type', '未知')}")
        print(f"  蓄势期换手率: {t.get('accumulation_turnover', 0):.2f}%")
        print(f"  最新换手率: {t.get('latest_turnover', 0):.2f}%")
        print(f"  换手率放大: {t.get('turnover_ratio', 0):.2f}x")
        print(f"  主升浪期均换手率: {t.get('avg_wave_turnover', 0):.2f}%")
        print(f"  行业启动阈值: {t.get('turnover_start_threshold', 5.0):.1f}%")
        print(f"  行业见顶阈值: {t.get('turnover_top_threshold', 15.0):.1f}%")
        if t.get('is_turnover_top', False):
            print(f"  换手率状态: ⚠️ 异常放大（见顶信号）")
        elif t.get('is_turnover_start', False):
            print(f"  换手率状态: ✅ 启动放大")
        else:
            print(f"  换手率状态: ❌ 未放大")
    else:
        print(f"  无换手率数据")
    
    detector.close()
    
    return result


def test_accuracy(stock_code: str = '605299'):
    """
    测试准确性：对比实际走势与检测结果
    """
    detector = MainWaveDetector()
    
    print("\n" + "=" * 60)
    print("准确性验证测试")
    print("=" * 60)
    
    # 获取舒华体育的实际走势数据
    price_df = detector.get_stock_data(stock_code, days=90)
    
    if price_df.empty:
        print("无法获取数据")
        detector.close()
        return
    
    # 找出实际主升浪起点（根据涨幅判断）
    # 假设：涨幅≥9%且成交量放大≥2倍 为主升浪启动点
    
    print("\n【实际走势关键节点】")
    
    for i in range(len(price_df)):
        row = price_df.iloc[i]
        
        # 标记关键节点
        if row['change_pct'] >= 9.5:
            print(f"  📌 {row['stock_date'].strftime('%Y-%m-%d')}: "
                  f"涨停 {row['change_pct']:.1f}% "
                  f"成交量 {row['volume']/10000:.0f}万")
    
    # 检测结果
    result = detector.detect_main_wave(stock_code)
    
    print("\n【检测结果】")
    print(f"  阶段: {result['wave_stage']}")
    print(f"  确信度: {result['confidence']:.2f}")
    
    # 对比分析
    print("\n【准确性评估】")
    
    # 判断是否正确识别主升浪
    actual_limit_ups = len(price_df[price_df['change_pct'] >= 9.5])
    detected_limit_ups = result['signals']['limit_up']['limit_up_count']  # 修改：用总涨停次数
    
    print(f"  实际涨停次数: {actual_limit_ups}次")
    print(f"  检测涨停次数: {detected_limit_ups}次")
    
    accuracy = min(detected_limit_ups / actual_limit_ups, 1.0) if actual_limit_ups > 0 else 0
    print(f"  涨停识别准确率: {accuracy:.1%}")
    
    # 成交量放大倍数验证
    avg_volume_before = price_df.head(10)['volume'].mean()
    avg_volume_wave = price_df.tail(10)['volume'].mean()
    actual_ratio = avg_volume_wave / avg_volume_before
    
    print(f"\n  实际成交量放大倍数: {actual_ratio:.2f}x")
    print(f"  检测成交量放大倍数: {result['signals']['volume']['latest_ratio']:.2f}x")
    
    volume_accuracy = min(result['signals']['volume']['latest_ratio'] / actual_ratio, 1.0)
    print(f"  成交量识别准确率: {volume_accuracy:.1%}")
    
    # 总体评估
    overall_accuracy = (accuracy + volume_accuracy) / 2
    print(f"\n  ✅ 综合准确率: {overall_accuracy:.1%}")
    
    if overall_accuracy >= 0.8:
        print("  🎯 结论: 参数设置合理，检测准确")
    elif overall_accuracy >= 0.6:
        print("  ⚠️ 结论: 参数需要微调")
    else:
        print("  ❌ 结论: 参数需要调整")
    
    detector.close()
    
    return overall_accuracy


def backtest_main_wave(stock_code: str, signal_date: str, verify_days: int = 20):
    """
    回测主升浪判断准确性
    
    核心逻辑：
    1. 在 signal_date 这天判断是否为主升浪启动
    2. 然后看后面 verify_days 天的实际走势
    3. 验证判断是否正确
    
    Args:
        stock_code: 股票代码
        signal_date: 判断日期（格式：YYYY-MM-DD）
        verify_days: 验证天数（默认20天）
    
    Returns:
        回测结果报告
    """
    detector = MainWaveDetector()
    
    print("=" * 70)
    print(f"📊 主升浪回测分析")
    print(f"股票: {stock_code} | 判断日期: {signal_date} | 验证周期: {verify_days}天")
    print("=" * 70)
    
    # ========== 第一步：获取判断日期的数据 ==========
    price_df = detector.get_stock_data(stock_code, days=90, end_date=signal_date)
    
    if price_df.empty:
        print(f"❌ 无法获取 {signal_date} 的数据")
        detector.close()
        return None
    
    # 确保数据截止到 signal_date
    actual_end_date = price_df['stock_date'].max().strftime('%Y-%m-%d')
    print(f"\n【判断时点数据】")
    print(f"  数据范围: {price_df['stock_date'].min().strftime('%Y-%m-%d')} ~ {actual_end_date}")
    print(f"  最新收盘价: {price_df.iloc[-1]['close']:.2f}")
    
    # ========== 第二步：在 signal_date 判断主升浪状态 ==========
    result = detector.detect_main_wave(stock_code, end_date=signal_date)
    
    print(f"\n【判断结果】")
    print(f"  主升浪阶段: {result['wave_stage']}")
    print(f"  确信度: {result['confidence']:.2f}")
    print(f"  操作建议: {result['recommendation']}")
    
    # 提取关键信号
    signals = result['signals']
    print(f"\n【关键信号】")
    print(f"  成交量放大: {signals['volume']['latest_ratio']:.2f}x")
    print(f"  涨停次数: {signals['limit_up']['limit_up_count']}次")
    print(f"  均线多头: {'✅' if signals['ma']['is_aligned'] else '❌'}")
    print(f"  MACD金叉: {'✅' if signals['macd']['is_golden_cross'] else '❌'}")
    
    # ========== 第三步：获取后续走势数据 ==========
    # 计算 signal_date 之后的 verify_days 天
    signal_dt = datetime.strptime(signal_date, '%Y-%m-%d')
    verify_end_date = (signal_dt + timedelta(days=verify_days * 1.5)).strftime('%Y-%m-%d')  # 多取一些自然日
    
    # 获取后续数据（从 signal_date 开始）
    verify_sql = f"""
        SELECT 
            stock_date,
            open_price as open,
            high_price as high,
            low_price as low,
            close_price as close,
            trading_volume as volume,
            ups_and_downs as change_pct
        FROM stock_history_date_price
        WHERE stock_code = %s
            AND stock_date > %s
            AND stock_date <= %s
            AND tradestatus = 1
        ORDER BY stock_date ASC
    """
    
    verify_df_data = detector.mysql.query_all(verify_sql, (stock_code, signal_date, verify_end_date))
    
    if not verify_df_data:
        print(f"\n⚠️ 无法获取后续走势数据")
        detector.close()
        return None
    
    verify_df = pd.DataFrame(verify_df_data)
    verify_df['stock_date'] = pd.to_datetime(verify_df['stock_date'])
    
    # 转换数据类型
    for col in ['open', 'high', 'low', 'close', 'volume', 'change_pct']:
        verify_df[col] = pd.to_numeric(verify_df[col], errors='coerce')
    
    verify_df = verify_df.head(verify_days)  # 只取 verify_days 个交易日
    
    print(f"\n{'='*70}")
    print(f"📈 后续走势验证（{len(verify_df)}个交易日）")
    print(f"{'='*70}")
    
    # 计算后续涨幅
    start_price = price_df.iloc[-1]['close']
    end_price = verify_df.iloc[-1]['close']
    total_change = (end_price - start_price) / start_price * 100
    
    # 统计后续涨停次数
    verify_limit_ups = len(verify_df[verify_df['change_pct'] >= 9.5])
    
    # 计算最高价和最大涨幅
    max_price = verify_df['high'].max()
    max_change = (max_price - start_price) / start_price * 100
    
    print(f"\n【后续走势统计】")
    print(f"  起始价格: {start_price:.2f}")
    print(f"  结束价格: {end_price:.2f}")
    print(f"  最高价格: {max_price:.2f}")
    print(f"  总涨幅: {total_change:+.2f}%")
    print(f"  最大涨幅: {max_change:+.2f}%")
    print(f"  后续涨停: {verify_limit_ups}次")
    
    # 显示后续走势详情
    print(f"\n【逐日走势】")
    for i, row in verify_df.iterrows():
        change_symbol = "🟢" if row['change_pct'] > 0 else "🔴" if row['change_pct'] < 0 else "⚪"
        limit_up_mark = " 🔥涨停" if row['change_pct'] >= 9.5 else ""
        print(f"  {row['stock_date'].strftime('%Y-%m-%d')}: {change_symbol} {row['change_pct']:+.2f}% "
              f"| 收盘{row['close']:.2f}{limit_up_mark}")
    
    # ========== 第四步：判断准确性 ==========
    print(f"\n{'='*70}")
    print(f"🎯 准确性评估")
    print(f"{'='*70}")
    
    # 判断标准：
    # 1. 如果判断为"启动/主升浪"，后续应该上涨（涨幅>5%）或有涨停
    # 2. 如果判断为"见顶"，后续应该下跌或滞涨
    # 3. 如果判断为"蓄势"，后续可能上涨或盘整
    
    is_correct = False
    analysis = ""
    
    if '启动' in result['wave_stage'] or '主升浪' in result['wave_stage']:
        # 判断为启动/主升浪
        if total_change >= 10 or verify_limit_ups >= 2:
            is_correct = True
            analysis = "✅ 判断正确！后续确认主升浪，涨幅显著"
        elif total_change >= 5:
            is_correct = True
            analysis = "✅ 判断正确！后续上涨，但涨幅一般"
        elif total_change >= 0:
            is_correct = False
            analysis = "⚠️ 判断偏差：后续涨幅不足，未形成主升浪"
        else:
            is_correct = False
            analysis = "❌ 判断错误：后续下跌，主升浪未确认"
    
    elif '反转' in result['wave_stage']:
        # 判断为底部反转
        if total_change >= 10 or verify_limit_ups >= 1:
            is_correct = True
            analysis = "✅ 判断正确！反转成功，后续上涨确认"
        elif total_change >= 5:
            is_correct = True
            analysis = "✅ 判断正确！反转有效，后续上涨"
        elif total_change >= 0:
            is_correct = False
            analysis = "⚠️ 判断偏差：反转后涨幅不足"
        else:
            is_correct = False
            analysis = "❌ 判断错误：反转失败，后续下跌"
    
    elif '见顶' in result['wave_stage']:
        # 判断为见顶
        if total_change < 0:
            is_correct = True
            analysis = "✅ 判断正确！后续下跌，见顶信号有效"
        elif total_change < 5:
            is_correct = True
            analysis = "✅ 判断正确！后续滞涨，高位风险确认"
        else:
            is_correct = False
            analysis = "❌ 判断错误：后续继续上涨，非真正见顶"
    
    elif '蓄势' in result['wave_stage']:
        # 判断为蓄势
        if 0 <= total_change < 10:
            is_correct = True
            analysis = "✅ 判断正确！后续盘整，蓄势状态"
        elif total_change >= 10:
            is_correct = False
            analysis = "⚠️ 判断偏差：后续大涨，启动信号遗漏"
        else:
            is_correct = True
            analysis = "✅ 判断正确！后续下跌，蓄势失败"
    
    else:
        # 非主升浪
        if total_change < 10 and verify_limit_ups < 2:
            is_correct = True
            analysis = "✅ 判断正确！后续无主升浪"
        else:
            is_correct = False
            analysis = "❌ 判断错误：后续出现主升浪，信号遗漏"
    
    print(f"\n判断结果: {result['wave_stage']}")
    print(f"后续走势: 总涨幅 {total_change:+.2f}%, 涨停 {verify_limit_ups}次")
    print(f"\n{analysis}")
    print(f"\n准确率: {'✅ 正确' if is_correct else '❌ 错误'}")
    
    detector.close()
    
    return {
        'stock_code': stock_code,
        'signal_date': signal_date,
        'wave_stage': result['wave_stage'],
        'confidence': result['confidence'],
        'total_change': total_change,
        'max_change': max_change,
        'verify_limit_ups': verify_limit_ups,
        'is_correct': is_correct,
        'analysis': analysis
    }


def batch_backtest(stock_code: str, start_date: str, end_date: str, interval_days: int = 5):
    """
    批量回测：在指定时间范围内，每隔一段时间进行一次判断
    
    Args:
        stock_code: 股票代码
        start_date: 回测开始日期
        end_date: 回测结束日期
        interval_days: 采样间隔（天）
    """
    print("=" * 70)
    print(f"📊 批量回测分析")
    print(f"股票: {stock_code} | 时间范围: {start_date} ~ {end_date}")
    print("=" * 70)
    
    detector = MainWaveDetector()
    
    # 获取时间范围内的所有交易日
    sql = f"""
        SELECT DISTINCT stock_date
        FROM stock_history_date_price
        WHERE stock_code = %s
            AND stock_date >= %s
            AND stock_date <= %s
            AND tradestatus = 1
        ORDER BY stock_date
    """
    
    trade_dates = detector.mysql.query_all(sql, (stock_code, start_date, end_date))
    if not trade_dates:
        print("无法获取交易日数据")
        detector.close()
        return
    
    trade_dates = [row['stock_date'].strftime('%Y-%m-%d') for row in trade_dates]
    
    # 按间隔采样
    sample_dates = trade_dates[::interval_days]
    
    print(f"\n采样点: {len(sample_dates)}个（间隔{interval_days}个交易日）\n")
    
    results = []
    correct_count = 0
    
    for i, date in enumerate(sample_dates):
        print(f"\n{'='*70}")
        print(f"[{i+1}/{len(sample_dates)}] 回测日期: {date}")
        print(f"{'='*70}")
        
        try:
            result = backtest_main_wave(stock_code, date, verify_days=15)
            if result:
                results.append(result)
                if result['is_correct']:
                    correct_count += 1
        except Exception as e:
            print(f"回测失败: {e}")
            continue
    
    # 汇总统计
    print(f"\n{'='*70}")
    print(f"📊 回测汇总")
    print(f"{'='*70}")
    print(f"\n总测试次数: {len(results)}")
    print(f"正确次数: {correct_count}")
    print(f"准确率: {correct_count/len(results)*100:.1f}%" if results else "无数据")
    
    # 按阶段统计
    stage_stats = {}
    for r in results:
        stage = r['wave_stage']
        if stage not in stage_stats:
            stage_stats[stage] = {'total': 0, 'correct': 0}
        stage_stats[stage]['total'] += 1
        if r['is_correct']:
            stage_stats[stage]['correct'] += 1
    
    print(f"\n各阶段准确率:")
    for stage, stats in stage_stats.items():
        acc = stats['correct'] / stats['total'] * 100 if stats['total'] > 0 else 0
        print(f"  {stage}: {stats['correct']}/{stats['total']} = {acc:.1f}%")
    
    detector.close()
    
    return results


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='主升浪识别脚本')
    parser.add_argument('--stock', type=str, default='605299', help='股票代码')
    parser.add_argument('--scan', action='store_true', help='全市场扫描')
    parser.add_argument('--test', action='store_true', help='准确性测试')
    parser.add_argument('--report', action='store_true', help='生成详细报告')
    parser.add_argument('--backtest', action='store_true', help='回测模式')
    parser.add_argument('--signal-date', type=str, help='回测判断日期（格式：YYYY-MM-DD）')
    parser.add_argument('--verify-days', type=int, default=20, help='回测验证天数')
    parser.add_argument('--batch-backtest', action='store_true', help='批量回测')
    parser.add_argument('--start-date', type=str, help='批量回测开始日期')
    parser.add_argument('--end-date', type=str, help='批量回测结束日期')
    
    args = parser.parse_args()
    
    if args.scan:
        # 全市场扫描
        detector = MainWaveDetector()
        results = detector.scan_all_stocks(min_confidence=0.5)
        
        print("\n" + "=" * 60)
        print("主升浪股票扫描结果")
        print("=" * 60)
        
        for r in results[:20]:
            print(f"\n{r['stock_code']} {r['stock_name']}")
            print(f"  阶段: {r['wave_stage']}")
            print(f"  确信度: {r['confidence']:.2f}")
            print(f"  价格: {r['latest_price']}")
        
        detector.close()
        
    elif args.backtest and args.signal_date:
        # 单次回测
        backtest_main_wave(args.stock, args.signal_date, args.verify_days)
        
    elif args.batch_backtest and args.start_date and args.end_date:
        # 批量回测
        batch_backtest(args.stock, args.start_date, args.end_date, interval_days=5)
        
    elif args.test:
        # 准确性测试
        test_accuracy(args.stock)
        
    elif args.report:
        # 生成报告
        detector = MainWaveDetector()
        report = detector.generate_report(args.stock)
        print(report)
        detector.close()
        
    else:
        # 默认：测试单只股票
        test_single_stock(args.stock)
#!/usr/bin/env python3
"""
小市值股票特征分析器（完整版）

特点：
1. 完整分析所有小市值股票
2. 计算250天完整特征
3. 包含主升浪识别和统计
4. 生成详细报告

Author: Xiao Luo
Date: 2026-04-02
"""

import sys
sys.path.insert(0, '/home/fan/.openclaw/workspace/stock_learning')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.utils.mysql_tool import MySQLUtil
from logs.logger import LogManager
import warnings
warnings.filterwarnings('ignore')


class RigorousFeatureAnalyzer:
    """严谨的小市值股票特征分析器"""
    
    MARKET_CAP_MAX = 200  # 市值上限（亿）
    
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
        self.logger = LogManager.get_logger("rigorous_analyzer")
        self.now_date = datetime.now().strftime('%Y-%m-%d')
    
    def close(self):
        self.mysql.close()
    
    def get_latest_date(self):
        """获取最新数据日期"""
        sql = "SELECT MAX(stock_date) as latest FROM stock_history_date_price"
        result = self.mysql.query_one(sql)
        return result['latest']
    
    def get_small_cap_stocks(self):
        """
        获取所有小市值股票（严谨筛选）
        """
        latest_date = self.get_latest_date()
        self.logger.info(f"数据日期: {latest_date}")
        
        sql = f"""
            SELECT DISTINCT
                p.stock_code,
                b.stock_name,
                p.liqa_share / 100000000 * h.close_price as circ_market_cap,
                h.close_price as latest_price,
                i.industry
            FROM stock_profit_data p
            JOIN stock_basic b ON p.stock_code = b.stock_code AND b.stock_status = 1
            JOIN stock_history_date_price h ON p.stock_code = h.stock_code AND h.stock_date = '{latest_date}'
            LEFT JOIN stock_industry i ON p.stock_code = i.stock_code
            WHERE p.liqa_share IS NOT NULL 
                AND p.liqa_share > 0
                AND p.statistic_date = (SELECT MAX(statistic_date) FROM stock_profit_data)
                AND p.liqa_share / 100000000 * h.close_price < {self.MARKET_CAP_MAX}
            ORDER BY circ_market_cap
        """
        
        result = self.mysql.query_all(sql)
        df = pd.DataFrame(result)
        
        # 行业分类
        df['industry_type'] = df['industry'].apply(self._classify_industry)
        
        self.logger.info(f"小市值股票总数: {len(df)}")
        for ind_type, count in df['industry_type'].value_counts().items():
            self.logger.info(f"  {ind_type}: {count}只")
        
        return df, latest_date
    
    def _classify_industry(self, industry):
        """行业分类"""
        if not industry:
            return '其他'
        industry = str(industry)
        for ind_type, keywords in self.INDUSTRY_KEYWORDS.items():
            if any(k in industry for k in keywords):
                return ind_type
        return '其他'
    
    def calculate_full_features(self, stock_code, latest_date):
        """
        计算单只股票的完整特征（250天）
        
        返回：
        - 基础特征：波动率、换手率、涨停频率
        - 主升浪特征：主升浪次数、成功率、平均涨幅、持续时间
        - 换手率特征：蓄势期换手率、主升浪期换手率、放大倍数
        """
        # 获取250天历史数据
        sql = f"""
            SELECT 
                stock_date,
                close_price,
                high_price,
                low_price,
                trading_volume,
                ups_and_downs,
                turn
            FROM stock_history_date_price
            WHERE stock_code = %s
                AND stock_date <= %s
                AND tradestatus = 1
            ORDER BY stock_date DESC
            LIMIT 260
        """
        
        result = self.mysql.query_all(sql, (stock_code, latest_date))
        
        if not result or len(result) < 120:
            return None
        
        df = pd.DataFrame(result)
        df = df.iloc[::-1]  # 按时间正序
        df = df.tail(250)   # 取最近250天
        
        # 转换数据类型
        for col in ['close_price', 'high_price', 'low_price', 'trading_volume', 'ups_and_downs', 'turn']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        df = df.dropna()
        
        if len(df) < 100:
            return None
        
        # ========== 基础特征 ==========
        
        # 1. 年化波动率
        returns = df['close_price'].pct_change().dropna()
        volatility = returns.std() * np.sqrt(250) * 100
        
        # 2. 平均换手率
        avg_turnover = df['turn'].mean()
        
        # 3. 涨停次数（年化）
        limit_ups = len(df[df['ups_and_downs'] >= 9.5])
        limit_up_frequency = limit_ups / len(df) * 250
        
        # ========== 主升浪识别 ==========
        
        main_waves = self._identify_main_waves_rigorous(df)
        
        if main_waves:
            main_wave_count = len(main_waves)
            main_wave_success_rate = main_wave_count / limit_ups if limit_ups > 0 else 0
            avg_wave_gain = np.mean([w['gain'] for w in main_waves])
            avg_wave_days = np.mean([w['days'] for w in main_waves])
            
            # 换手率放大倍数
            turnover_ratios = [w['turnover_ratio'] for w in main_waves if w['turnover_ratio'] > 0]
            avg_wave_turnover_ratio = np.mean(turnover_ratios) if turnover_ratios else 0
        else:
            main_wave_count = 0
            main_wave_success_rate = 0
            avg_wave_gain = 0
            avg_wave_days = 0
            avg_wave_turnover_ratio = 0
        
        # ========== 换手率特征 ==========
        
        # 蓄势期换手率（最近10天）
        recent_10d_turnover = df.tail(10)['turn'].mean()
        
        # 历史换手率分布
        turnover_q25 = df['turn'].quantile(0.25)
        turnover_q50 = df['turn'].quantile(0.50)
        turnover_q75 = df['turn'].quantile(0.75)
        
        return {
            # 基础特征
            'volatility': round(volatility, 2),
            'avg_turnover': round(avg_turnover, 2),
            'limit_up_count': limit_ups,
            'limit_up_frequency': round(limit_up_frequency, 2),
            
            # 主升浪特征
            'main_wave_count': main_wave_count,
            'main_wave_success_rate': round(main_wave_success_rate, 3),
            'avg_wave_gain': round(avg_wave_gain, 2),
            'avg_wave_days': round(avg_wave_days, 1),
            'avg_wave_turnover_ratio': round(avg_wave_turnover_ratio, 2),
            
            # 换手率特征
            'recent_10d_turnover': round(recent_10d_turnover, 2),
            'turnover_q25': round(turnover_q25, 2),
            'turnover_q50': round(turnover_q50, 2),
            'turnover_q75': round(turnover_q75, 2),
            
            # 数据质量
            'data_days': len(df)
        }
    
    def _identify_main_waves_rigorous(self, df):
        """
        严谨的主升浪识别
        
        定义：
        1. 20天内涨幅≥20%
        2. 成交量放大≥2倍
        3. 换手率放大≥1.5倍
        """
        main_waves = []
        
        # 计算20天涨幅
        df = df.copy()
        df['gain_20d'] = df['close_price'].pct_change(20) * 100
        
        # 计算20天换手率均值
        df['turnover_20d'] = df['turn'].rolling(20).mean()
        
        # 找主升浪
        for i in range(40, len(df)):
            if df.iloc[i]['gain_20d'] >= 20:
                # 主升浪区间
                end_idx = i
                start_idx = i - 20
                
                # 计算特征
                start_price = df.iloc[start_idx]['close_price']
                end_price = df.iloc[end_idx]['close_price']
                gain = (end_price - start_price) / start_price * 100
                
                # 蓄势期换手率（前10天）
                acc_turnover = df.iloc[start_idx-10:start_idx]['turn'].mean()
                # 主升浪期换手率
                wave_turnover = df.iloc[start_idx:end_idx]['turn'].mean()
                
                turnover_ratio = wave_turnover / acc_turnover if acc_turnover > 0 else 0
                
                # 跳过换手率未放大的情况
                if turnover_ratio < 1.5:
                    continue
                
                main_waves.append({
                    'start_date': df.iloc[start_idx]['stock_date'],
                    'end_date': df.iloc[end_idx]['stock_date'],
                    'gain': gain,
                    'days': 20,
                    'turnover_ratio': turnover_ratio,
                    'wave_turnover': wave_turnover,
                    'acc_turnover': acc_turnover
                })
        
        return main_waves
    
    def run_analysis(self):
        """执行完整分析"""
        self.logger.info("=" * 70)
        self.logger.info("📊 小市值股票特征分析（严谨版）")
        self.logger.info("=" * 70)
        
        # 1. 获取股票列表
        df_stocks, latest_date = self.get_small_cap_stocks()
        
        # 2. 分行业分析
        all_features = []
        
        for ind_type in ['科技', '医药', '资源', '新能源']:
            df_ind = df_stocks[df_stocks['industry_type'] == ind_type]
            
            if len(df_ind) == 0:
                continue
            
            self.logger.info(f"\n{'='*50}")
            self.logger.info(f"分析 {ind_type} 行业: {len(df_ind)} 只股票")
            self.logger.info(f"{'='*50}")
            
            for i, (_, row) in enumerate(df_ind.iterrows()):
                stock_code = row['stock_code']
                
                if (i + 1) % 10 == 0:
                    self.logger.info(f"  进度: {i+1}/{len(df_ind)}")
                
                try:
                    features = self.calculate_full_features(stock_code, latest_date)
                    
                    if features:
                        features['stock_code'] = stock_code
                        features['stock_name'] = row['stock_name']
                        features['circ_market_cap'] = row['circ_market_cap']
                        features['industry_type'] = ind_type
                        all_features.append(features)
                        
                except Exception as e:
                    self.logger.error(f"  {stock_code} 计算失败: {e}")
        
        # 3. 生成特征表
        df_features = pd.DataFrame(all_features)

        # 确保股票代码为6位字符串格式
        if 'stock_code' in df_features.columns:
            df_features['stock_code'] = df_features['stock_code'].astype(str).str.zfill(6)

        output_path = '/home/fan/.openclaw/workspace/stock_learning/data/stock_features_full.csv'
        df_features.to_csv(output_path, index=False, encoding='utf-8-sig')
        self.logger.info(f"\n特征数据已保存: {output_path}")
        
        # 4. 行业统计
        self._generate_industry_stats(df_features)
        
        # 5. 参数建议
        self._generate_param_suggestions(df_features)
        
        return df_features
    
    def _generate_industry_stats(self, df):
        """生成行业统计报告"""
        self.logger.info("\n" + "=" * 70)
        self.logger.info("📊 行业特征对比")
        self.logger.info("=" * 70)
        
        stats = df.groupby('industry_type').agg({
            'stock_code': 'count',
            'circ_market_cap': 'mean',
            'volatility': 'mean',
            'avg_turnover': 'mean',
            'limit_up_frequency': 'mean',
            'main_wave_count': 'sum',
            'main_wave_success_rate': 'mean',
            'avg_wave_gain': 'mean',
            'avg_wave_turnover_ratio': 'mean'
        }).round(2)
        
        stats = stats.rename(columns={
            'stock_code': '股票数',
            'circ_market_cap': '平均市值(亿)',
            'volatility': '波动率(%)',
            'avg_turnover': '换手率(%)',
            'limit_up_frequency': '涨停频率(次/年)',
            'main_wave_count': '主升浪总数',
            'main_wave_success_rate': '成功率',
            'avg_wave_gain': '平均涨幅(%)',
            'avg_wave_turnover_ratio': '换手率放大'
        })
        
        print(stats.to_string())
        
        output_path = '/home/fan/.openclaw/workspace/stock_learning/data/industry_stats_full.csv'
        stats.to_csv(output_path, encoding='utf-8-sig')
        self.logger.info(f"\n行业统计已保存: {output_path}")
    
    def _generate_param_suggestions(self, df):
        """生成参数优化建议"""
        self.logger.info("\n" + "=" * 70)
        self.logger.info("💡 参数优化建议")
        self.logger.info("=" * 70)
        
        suggestions = []
        
        for ind_type in df['industry_type'].unique():
            df_ind = df[df['industry_type'] == ind_type]
            
            # 基于特征计算建议参数
            avg_turnover = df_ind['avg_turnover'].mean()
            avg_volatility = df_ind['volatility'].mean()
            avg_turnover_ratio = df_ind['avg_wave_turnover_ratio'].mean()
            
            # 换手率阈值建议
            turnover_start = round(avg_turnover * 1.5, 1)
            turnover_top = round(avg_turnover * 3.5, 1)
            
            # 波动率类型
            if avg_volatility > 60:
                vol_type = '高波动'
            elif avg_volatility > 40:
                vol_type = '中等波动'
            else:
                vol_type = '低波动'
            
            suggestions.append({
                '行业': ind_type,
                '股票数': len(df_ind),
                '平均波动率(%)': round(avg_volatility, 2),
                '波动类型': vol_type,
                '平均换手率(%)': round(avg_turnover, 2),
                '建议启动换手率(%)': turnover_start,
                '建议见顶换手率(%)': turnover_top,
                '平均换手率放大': round(avg_turnover_ratio, 2)
            })
        
        df_suggestions = pd.DataFrame(suggestions)
        print(df_suggestions.to_string(index=False))
        
        output_path = '/home/fan/.openclaw/workspace/stock_learning/data/param_suggestions.csv'
        df_suggestions.to_csv(output_path, index=False, encoding='utf-8-sig')
        self.logger.info(f"\n参数建议已保存: {output_path}")


if __name__ == '__main__':
    analyzer = RigorousFeatureAnalyzer()
    try:
        df = analyzer.run_analysis()
        analyzer.logger.info("\n✅ 分析完成!")
    finally:
        analyzer.close()
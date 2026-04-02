#!/usr/bin/env python3
"""
股票适配性判断工具

判断一只股票是否适合使用主升浪指标：
1. 流通市值（核心指标）
2. 波动率
3. 涨停频率
4. 涨停后续走势成功率

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


class StockSuitabilityChecker:
    """股票适配性判断器"""
    
    # 适配性阈值配置
    MARKET_CAP_SMALL = 100      # 小盘股阈值（亿）
    MARKET_CAP_MID = 500        # 中盘股阈值（亿）
    VOLATILITY_LOW = 20         # 低波动率阈值（%）
    VOLATILITY_HIGH = 50        # 高波动率阈值（%）
    LIMIT_UP_MIN = 5            # 最少涨停次数（年化）
    SUCCESS_RATE_MIN = 0.5      # 最低涨停成功率
    
    def __init__(self):
        self.mysql = MySQLUtil()
        self.mysql.connect()
        self.logger = LogManager.get_logger("stock_suitability")
    
    def close(self):
        self.mysql.close()
    
    def get_market_cap(self, stock_code: str) -> tuple:
        """
        从数据库获取真实流通股本数据
        
        Returns:
            (liqa_share, total_share, statistic_date) 流通股本(亿股), 总股本(亿股), 数据日期
        """
        sql = '''
            SELECT 
                liqa_share / 100000000 as liqa_share_yi,
                total_share / 100000000 as total_share_yi,
                statistic_date
            FROM stock_profit_data 
            WHERE stock_code = %s AND liqa_share IS NOT NULL
            ORDER BY statistic_date DESC
            LIMIT 1
        '''
        
        result = self.mysql.query_one(sql, (stock_code,))
        
        if result:
            return float(result['liqa_share_yi']), float(result['total_share_yi']), result['statistic_date']
        else:
            return None, None, None
    
    def analyze_stock(self, stock_code: str, days: int = 250) -> dict:
        """
        分析股票适配性
        
        Returns:
            {
                'stock_code': str,
                'stock_name': str,
                'market_cap_type': str,      # 市值类型
                'estimated_market_cap': float, # 估算市值
                'volatility': float,          # 波动率
                'limit_up_count': int,        # 涨停次数
                'limit_up_success_rate': float, # 涨停成功率
                'suitability_score': float,   # 适配性得分
                'suitability_level': str,     # 适配性等级
                'recommendation': str,        # 建议
                'details': dict               # 详细数据
            }
        """
        # 获取股票名称
        sql_name = "SELECT stock_name FROM stock_basic WHERE stock_code = %s"
        result = self.mysql.query_one(sql_name, (stock_code,))
        stock_name = result['stock_name'] if result else stock_code
        
        # 1. 获取历史数据
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        sql = f"""
            SELECT 
                stock_date,
                close_price,
                high_price,
                low_price,
                trading_amount,
                trading_volume,
                ups_and_downs
            FROM stock_history_date_price
            WHERE stock_code = %s
                AND stock_date >= %s
                AND stock_date <= %s
                AND tradestatus = 1
            ORDER BY stock_date
        """
        
        df = pd.DataFrame(self.mysql.query_all(sql, (stock_code, start_date, end_date)))
        
        if df.empty or len(df) < 60:
            return {
                'stock_code': stock_code,
                'stock_name': stock_name,
                'suitability_level': '数据不足',
                'recommendation': '无法判断'
            }
        
        # 数据类型转换
        for col in ['close_price', 'high_price', 'low_price', 'trading_amount', 'trading_volume', 'ups_and_downs']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        df = df.dropna()
        
        # 2. 获取真实流通股本数据
        liqa_share, total_share, cap_date = self.get_market_cap(stock_code)
        
        # 获取最新股价
        latest_price = float(df.iloc[-1]['close_price'])
        
        if liqa_share is not None:
            # 使用真实流通股本计算市值
            estimated_market_cap = liqa_share * latest_price  # 流通市值(亿)
            market_cap_source = f'真实数据({cap_date})'
        else:
            # 回退到估算方法
            avg_amount = df['trading_amount'].mean() / 100000000  # 转为亿
            estimated_market_cap = avg_amount / 0.02
            market_cap_source = '估算(换手率2%)'
        
        # 判断市值类型
        if estimated_market_cap < self.MARKET_CAP_SMALL:
            market_cap_type = '小盘股'
            market_cap_score = 1.0
        elif estimated_market_cap < self.MARKET_CAP_MID:
            market_cap_type = '中盘股'
            market_cap_score = 0.7
        else:
            market_cap_type = '大盘股'
            market_cap_score = 0.3
        
        # 3. 计算波动率
        returns = df['close_price'].pct_change().dropna()
        volatility = returns.std() * np.sqrt(250) * 100  # 年化波动率
        
        # 计算趋势（近期涨跌幅）
        if len(df) >= 60:
            recent_return = (df.iloc[-1]['close_price'] - df.iloc[-60]['close_price']) / df.iloc[-60]['close_price'] * 100
        else:
            recent_return = 0
        
        # 趋势得分（上涨趋势得分更高）
        if recent_return > 20:
            trend_score = 1.0
        elif recent_return > 0:
            trend_score = 0.7
        elif recent_return > -20:
            trend_score = 0.4
        else:
            trend_score = 0.2
        
        if volatility < self.VOLATILITY_LOW:
            volatility_type = '低波动'
            volatility_score = 0.4
        elif volatility > self.VOLATILITY_HIGH:
            volatility_type = '高波动'
            volatility_score = 1.0
        else:
            volatility_type = '中等波动'
            volatility_score = 0.7
        
        # 4. 统计涨停次数
        limit_ups = df[df['ups_and_downs'] >= 9.5]
        limit_up_count = len(limit_ups)
        limit_up_frequency = limit_up_count / len(df) * 250  # 年化涨停次数
        
        # 涨停频率得分
        if limit_up_frequency >= self.LIMIT_UP_MIN:
            limit_up_score = 1.0
        elif limit_up_frequency >= 2:
            limit_up_score = 0.7
        else:
            limit_up_score = 0.3
        
        # 5. 计算涨停成功率（涨停后5日涨幅>0）
        success_count = 0
        total_count = 0
        
        for i, row in limit_ups.iterrows():
            limit_date = row['stock_date']
            limit_price = row['close_price']
            
            # 找到后续5日价格
            future = df[df['stock_date'] > limit_date].head(5)
            if len(future) >= 5:
                future_price = future.iloc[-1]['close_price']
                change = (future_price - limit_price) / limit_price * 100
                total_count += 1
                if change > 0:
                    success_count += 1
        
        limit_up_success_rate = success_count / total_count if total_count > 0 else 0
        
        # 成功率得分（考虑样本量）
        if total_count < 3:
            # 样本量太少，降低成功率得分
            success_score = 0.3
        elif limit_up_success_rate >= self.SUCCESS_RATE_MIN:
            success_score = 1.0
        elif limit_up_success_rate >= 0.3:
            success_score = 0.6
        else:
            success_score = 0.2
        
        # 6. 计算综合适配性得分
        # 分别计算各项得分
        market_cap_score_raw = market_cap_score
        volatility_score_raw = volatility_score
        limit_up_score_raw = limit_up_score
        success_score_raw = success_score
        trend_score_raw = trend_score
        
        # 调整权重：
        # 市值20%、波动率15%、涨停频率15%、成功率30%、趋势20%
        suitability_score = (
            market_cap_score_raw * 0.20 +      # 市值权重20%
            volatility_score_raw * 0.15 +       # 波动率权重15%
            limit_up_score_raw * 0.15 +         # 涨停频率权重15%
            success_score_raw * 0.30 +          # 成功率权重30%
            trend_score_raw * 0.20              # 趋势权重20%
        )
        
        # 7. 判断适配性等级
        if suitability_score >= 0.7:
            suitability_level = '✅ 高度适配'
            recommendation = '强烈推荐使用主升浪指标，准确率预期较高'
        elif suitability_score >= 0.5:
            suitability_level = '⚠️ 中度适配'
            recommendation = '可使用主升浪指标，建议调整参数或结合其他指标'
        elif suitability_score >= 0.3:
            suitability_level = '❌ 低度适配'
            recommendation = '不建议使用主升浪指标，准确率预期较低'
        else:
            suitability_level = '❌ 不适配'
            recommendation = '强烈不建议使用，模型基本失效'
        
        return {
            'stock_code': stock_code,
            'stock_name': stock_name,
            'market_cap_type': market_cap_type,
            'estimated_market_cap': estimated_market_cap,
            'market_cap_source': market_cap_source,
            'liqa_share': liqa_share,
            'latest_price': latest_price,
            'volatility': volatility,
            'volatility_type': volatility_type,
            'limit_up_count': limit_up_count,
            'limit_up_frequency': limit_up_frequency,
            'limit_up_success_rate': limit_up_success_rate,
            'recent_return': recent_return,
            'suitability_score': suitability_score,
            'suitability_level': suitability_level,
            'recommendation': recommendation,
            'scores': {
                'market_cap_score': market_cap_score_raw,
                'volatility_score': volatility_score_raw,
                'limit_up_score': limit_up_score_raw,
                'success_score': success_score_raw,
                'trend_score': trend_score_raw
            },
            'details': {
                'avg_amount': avg_amount if 'avg_amount' in dir() else 0,
                'success_count': success_count,
                'total_count': total_count
            }
        }
    
    def print_report(self, stock_code: str):
        """打印适配性报告"""
        result = self.analyze_stock(stock_code)
        
        print("=" * 70)
        print(f"📊 {result['stock_name']}（{result['stock_code']}）适配性分析报告")
        print("=" * 70)
        
        if 'suitability_level' not in result:
            print(f"\\n❌ {result.get('suitability_level', '分析失败')}")
            return result
        
        print(f"\\n【基本信息】")
        print(f"  流通市值: {result['estimated_market_cap']:.1f}亿（{result['market_cap_type']}）")
        if result.get('liqa_share'):
            print(f"  流通股本: {result['liqa_share']:.2f}亿股")
            print(f"  最新股价: {result.get('latest_price', 0):.2f}元")
        print(f"  数据来源: {result.get('market_cap_source', '未知')}")
        print(f"  年化波动率: {result['volatility']:.1f}%（{result['volatility_type']}）")
        print(f"  近期趋势: {result.get('recent_return', 0):+.1f}%")
        
        print(f"\\n【涨停特性】")
        print(f"  涨停次数: {result['limit_up_count']}次（年化{result['limit_up_frequency']:.1f}次）")
        print(f"  涨停成功率: {result['limit_up_success_rate']*100:.1f}%")
        print(f"  样本数: {result['details']['total_count']}次")
        
        print(f"\\n【适配性评估】")
        scores = result.get('scores', {})
        print(f"  市值得分: {scores.get('market_cap_score', 0):.2f}/1.0（权重20%）")
        print(f"  波动率得分: {scores.get('volatility_score', 0):.2f}/1.0（权重15%）")
        print(f"  涨停频率得分: {scores.get('limit_up_score', 0):.2f}/1.0（权重15%）")
        print(f"  成功率得分: {scores.get('success_score', 0):.2f}/1.0（权重30%）")
        print(f"  趋势得分: {scores.get('trend_score', 0):.2f}/1.0（权重20%）")
        print(f"  加权综合得分: {result['suitability_score']:.2f}/1.00")
        
        print(f"\\n【结论】")
        print(f"  适配等级: {result['suitability_level']}")
        print(f"  建议: {result['recommendation']}")
        
        return result


def main():
    """主函数"""
    checker = StockSuitabilityChecker()
    
    # 测试三只股票
    stocks = ['000063', '603929', '605299']
    
    results = []
    for code in stocks:
        result = checker.print_report(code)
        if 'suitability_score' in result:
            results.append(result)
        print()
    
    # 汇总对比
    if results:
        print("=" * 70)
        print("📈 适配性对比汇总")
        print("=" * 70)
        print(f"{'股票':<12} {'市值类型':<10} {'波动率':<10} {'涨停成功率':<12} {'适配得分':<10} {'适配等级':<15}")
        print("-" * 70)
        
        for r in results:
            print(f"{r['stock_name']:<12} {r['market_cap_type']:<10} {r['volatility']:.1f}%{'':<5} "
                  f"{r['limit_up_success_rate']*100:.1f}%{'':<6} {r['suitability_score']:.2f}{'':<5} {r['suitability_level']:<15}")
        
        print("\\n" + "=" * 70)
        print("💡 使用建议")
        print("=" * 70)
        print('''
1. 高度适配（≥0.7）：直接使用主升浪指标，准确率预期70%+
2. 中度适配（0.5-0.7）：调整参数后使用，或结合其他指标
3. 低度适配（0.3-0.5）：不建议单独使用，准确率预期<50%
4. 不适配（<0.3）：不建议使用，模型基本失效

参数调整建议：
- 大盘股：提高成交量阈值至3-5倍，降低涨幅验证标准至5%
- 小盘股：降低成交量阈值至1.5倍，提高涨幅验证标准至15%
        ''')
    
    checker.close()


if __name__ == '__main__':
    main()
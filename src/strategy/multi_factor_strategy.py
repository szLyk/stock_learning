# -*- coding: utf-8 -*-
"""
多因子选股策略主程序
功能：因子分析、选股、调仓、回测
"""

import datetime
import pandas as pd
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.multi_factor_tool import MultiFactorAnalyzer
from src.utils.baostock_extension import BaostockExtension
from src.utils.mysql_tool import MySQLUtil
from logs.logger import LogManager


class MultiFactorStrategy:
    """多因子选股策略"""
    
    def __init__(self, strategy_name='multi_factor_v1'):
        self.strategy_name = strategy_name
        self.analyzer = MultiFactorAnalyzer()
        self.mysql_manager = MySQLUtil()
        self.mysql_manager.connect()
        self.logger = LogManager.get_logger("multi_factor_strategy")
        self.now_date = datetime.datetime.now().strftime('%Y-%m-%d')
    
    def daily_run(self, collect_data=True, analyze=True, select_stocks=True):
        """
        每日运行流程
        :param collect_data: 是否采集新数据
        :param analyze: 是否运行因子分析
        :param select_stocks: 是否选股
        """
        self.logger.info(f"=== 多因子策略每日运行 {self.now_date} ===")
        
        # 1. 采集新数据（资金流向、分析师预期）
        if collect_data:
            self.logger.info("\n[步骤 1] 采集扩展数据...")
            try:
                ext = BaostockExtension()
                ext.run_full_collection()
                ext.close()
            except Exception as e:
                self.logger.error(f"数据采集失败：{e}")
        
        # 2. 运行因子分析
        if analyze:
            self.logger.info("\n[步骤 2] 运行因子分析...")
            try:
                factor_df = self.analyzer.run_factor_analysis(save_to_db=True)
                self.logger.info(f"因子分析完成：{len(factor_df)} 只股票")
            except Exception as e:
                self.logger.error(f"因子分析失败：{e}")
                factor_df = pd.DataFrame()
        
        # 3. 选股
        if select_stocks and not factor_df.empty:
            self.logger.info("\n[步骤 3] 执行选股...")
            try:
                selected = self.analyzer.select_stocks(top_n=50, min_score=60)
                if not selected.empty:
                    self.analyzer.save_selection_result(selected, self.strategy_name)
                    self.logger.info(f"选股完成：{len(selected)} 只股票")
                    self._print_selection_summary(selected)
                else:
                    self.logger.warning("未找到符合条件的股票")
            except Exception as e:
                self.logger.error(f"选股失败：{e}")
        
        self.logger.info("\n=== 每日运行完成 ===")
    
    def _print_selection_summary(self, df):
        """打印选股摘要"""
        print("\n" + "="*60)
        print(f"策略：{self.strategy_name}")
        print(f"日期：{df['stock_date'].iloc[0]}")
        print(f"选股数量：{len(df)}")
        print("="*60)
        print(f"{'代码':<10} {'名称':<15} {'得分':>8} {'排名':>6} {'价格':>8} {'权重':>8}")
        print("-"*60)
        
        for _, row in df.head(20).iterrows():
            print(f"{row['stock_code']:<10} {row['stock_name']:<15} {row['total_score']:>8.2f} {row['total_rank']:>6} {row['close_price']:>8.2f} {row['weight']:>7.2f}%")
        
        print("="*60)
    
    def backtest(self, start_date, end_date, top_n=50, hold_days=5):
        """
        简单回测
        :param start_date: 回测开始日期
        :param end_date: 回测结束日期
        :param top_n: 每次选股数量
        :param hold_days: 持有天数
        :return: 回测结果
        """
        self.logger.info(f"=== 开始回测 {start_date} ~ {end_date} ===")
        
        # 获取所有交易日
        sql = """
        SELECT DISTINCT stock_date 
        FROM stock.stock_history_date_price 
        WHERE stock_date BETWEEN %s AND %s 
        ORDER BY stock_date
        """
        result = self.mysql_manager.query_all(sql, (start_date, end_date))
        if not result:
            self.logger.error("未找到交易日数据")
            return None
        
        trade_dates = [r['stock_date'] for r in result]
        self.logger.info(f"回测交易日：{len(trade_dates)} 天")
        
        # 模拟回测
        initial_capital = 1000000
        capital = initial_capital
        positions = {}  # 持仓
        trades = []  # 交易记录
        
        for i, trade_date in enumerate(trade_dates):
            self.now_date = trade_date.strftime('%Y-%m-%d')
            
            # 1. 检查是否有到期的持仓需要卖出
            sell_list = []
            for stock_code, pos in positions.items():
                if pos['hold_days'] >= hold_days:
                    sell_list.append(stock_code)
            
            # 卖出
            if sell_list:
                sell_prices = self._get_prices(sell_list, trade_date)
                for stock_code in sell_list:
                    if stock_code in sell_prices:
                        sell_price = sell_prices[stock_code]
                        pos = positions[stock_code]
                        profit = (sell_price - pos['buy_price']) * pos['shares']
                        capital += sell_price * pos['shares']
                        
                        trades.append({
                            'trade_date': trade_date,
                            'stock_code': stock_code,
                            'action': 'sell',
                            'price': sell_price,
                            'shares': pos['shares'],
                            'profit': profit
                        })
                        
                        self.logger.debug(f"卖出 {stock_code}: {pos['buy_price']} → {sell_price}, 盈亏 {profit:.2f}")
                
                # 清除已卖出的持仓
                for code in sell_list:
                    if code in positions:
                        del positions[code]
            
            # 2. 选股
            try:
                factor_df = self.analyzer.run_factor_analysis(save_to_db=False)
                if factor_df.empty:
                    continue
                
                selected = self.analyzer.select_stocks(top_n=top_n, min_score=50)
                if selected.empty:
                    continue
                
                # 3. 买入（等权重）
                buy_stocks = selected.head(top_n)
                position_per_stock = capital / len(buy_stocks)
                
                buy_prices = self._get_prices(buy_stocks['stock_code'].tolist(), trade_date)
                
                for _, row in buy_stocks.iterrows():
                    stock_code = row['stock_code']
                    if stock_code in buy_prices and stock_code not in positions:
                        price = buy_prices[stock_code]
                        shares = int(position_per_stock / price / 100) * 100  # 100 股的整数倍
                        
                        if shares > 0:
                            cost = price * shares
                            capital -= cost
                            
                            positions[stock_code] = {
                                'buy_date': trade_date,
                                'buy_price': price,
                                'shares': shares,
                                'hold_days': 0
                            }
                            
                            trades.append({
                                'trade_date': trade_date,
                                'stock_code': stock_code,
                                'action': 'buy',
                                'price': price,
                                'shares': shares
                            })
            except Exception as e:
                self.logger.error(f"选股失败 {trade_date}: {e}")
            
            # 4. 更新持仓天数
            for pos in positions.values():
                pos['hold_days'] += 1
        
        # 清仓
        if positions:
            last_date = trade_dates[-1]
            sell_prices = self._get_prices(list(positions.keys()), last_date)
            for stock_code, pos in positions.items():
                if stock_code in sell_prices:
                    sell_price = sell_prices[stock_code]
                    profit = (sell_price - pos['buy_price']) * pos['shares']
                    capital += sell_price * pos['shares']
        
        # 计算回测指标
        total_return = (capital - initial_capital) / initial_capital * 100
        
        result = {
            'initial_capital': initial_capital,
            'final_capital': capital,
            'total_return': total_return,
            'trade_days': len(trade_dates),
            'total_trades': len(trades),
            'trades': pd.DataFrame(trades)
        }
        
        self.logger.info(f"\n=== 回测结果 ===")
        self.logger.info(f"初始资金：{initial_capital:,.0f}")
        self.logger.info(f"最终资金：{capital:,.0f}")
        self.logger.info(f"总收益率：{total_return:.2f}%")
        self.logger.info(f"交易天数：{len(trade_dates)}")
        self.logger.info(f"总交易次数：{len(trades)}")
        
        return result
    
    def _get_prices(self, stock_codes, trade_date):
        """获取股票价格"""
        if not stock_codes:
            return {}
        
        codes_str = ','.join([f"'{c}'" for c in stock_codes])
        sql = f"""
        SELECT stock_code, close_price 
        FROM stock.stock_history_date_price 
        WHERE stock_code IN ({codes_str}) 
          AND stock_date = %s
        """
        result = self.mysql_manager.query_all(sql, (trade_date,))
        if not result:
            return {}
        
        return {r['stock_code']: float(r['close_price']) for r in result}
    
    def close(self):
        """关闭连接"""
        self.analyzer.close()
        self.mysql_manager.close()


# =====================================================
# 主程序入口
# =====================================================
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='多因子选股策略')
    parser.add_argument('--mode', type=str, default='daily', choices=['daily', 'backtest'],
                       help='运行模式：daily(每日运行) 或 backtest(回测)')
    parser.add_argument('--start-date', type=str, help='回测开始日期 (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, help='回测结束日期 (YYYY-MM-DD)')
    parser.add_argument('--top-n', type=int, default=50, help='选股数量')
    parser.add_argument('--hold-days', type=int, default=5, help='持有天数')
    parser.add_argument('--no-collect', action='store_true', help='不采集新数据')
    parser.add_argument('--no-analyze', action='store_true', help='不运行因子分析')
    
    args = parser.parse_args()
    
    strategy = MultiFactorStrategy()
    
    try:
        if args.mode == 'daily':
            strategy.daily_run(
                collect_data=not args.no_collect,
                analyze=not args.no_analyze,
                select_stocks=True
            )
        elif args.mode == 'backtest':
            if not args.start_date or not args.end_date:
                print("回测模式需要指定 --start-date 和 --end-date")
                sys.exit(1)
            
            strategy.backtest(
                start_date=args.start_date,
                end_date=args.end_date,
                top_n=args.top_n,
                hold_days=args.hold_days
            )
    finally:
        strategy.close()

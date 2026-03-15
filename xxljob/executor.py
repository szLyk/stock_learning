# -*- coding: utf-8 -*-
"""
XXL-JOB 执行器 - 股票数据采集调度
"""

import sys
import os
import datetime
import logging

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.baosock_tool import BaostockFetcher
from src.utils.baostock_financial import BaostockFinancialFetcher
from src.utils.eastmoney_tool import EastMoneyFetcher
from src.utils.indicator_calculation_tool import IndicatorCalculator
from src.utils.multi_factor_tool import MultiFactorAnalyzer
from logs.logger import LogManager


class StockDataExecutor:
    """股票数据采集执行器"""
    
    def __init__(self):
        self.logger = LogManager.get_logger("xxljob_executor")
    
    # =====================================================
    # 第 1 层：基础行情数据
    # =====================================================
    
    def run_daily_collection(self, date_type='d'):
        """
        采集股票日线/周线/月线数据
        :param date_type: d=日线，w=周线，m=月线
        """
        self.logger.info(f"=== 开始采集{date_type}线数据 ===")
        fetcher = BaostockFetcher()
        try:
            # 获取所有股票
            pending_stocks = fetcher.get_pending_stocks_from_mysql()
            total = len(pending_stocks)
            self.logger.info(f"待采集股票：{total} 只")
            
            success_count = 0
            for i, row in pending_stocks.iterrows():
                stock_code = row['stock_code']
                try:
                    df = fetcher.process_stock(stock_code, date_type=date_type)
                    if not df.empty:
                        success_count += 1
                    if (i + 1) % 100 == 0:
                        self.logger.info(f"已处理 {i+1}/{total}，成功 {success_count}")
                except Exception as e:
                    self.logger.error(f"处理 {stock_code} 失败：{e}")
            
            self.logger.info(f"✅ 采集完成：成功 {success_count}/{total}")
            return {"total": total, "success": success_count}
        except Exception as e:
            self.logger.error(f"采集失败：{e}")
            raise
        finally:
            fetcher.close()
    
    def run_min_collection(self):
        """采集股票分钟线数据（交易日运行）"""
        today = datetime.datetime.now()
        # 判断是否为交易日（简单判断：工作日）
        if today.weekday() >= 5:
            self.logger.info("今日非交易日，跳过分钟线采集")
            return {"skipped": True, "reason": "non_trading_day"}
        
        self.logger.info("=== 开始采集分钟线数据 ===")
        fetcher = BaostockFetcher()
        try:
            pending_stocks = fetcher.get_pending_stocks_from_mysql()
            total = len(pending_stocks)
            success_count = 0
            
            for i, row in pending_stocks.iterrows():
                stock_code = row['stock_code']
                try:
                    df = fetcher.process_stock(stock_code, date_type='min')
                    if not df.empty:
                        success_count += 1
                except Exception as e:
                    self.logger.error(f"处理 {stock_code} 失败：{e}")
            
            self.logger.info(f"✅ 分钟线采集完成：成功 {success_count}/{total}")
            return {"total": total, "success": success_count}
        finally:
            fetcher.close()
    
    # =====================================================
    # 第 2 层：财务数据
    # =====================================================
    
    def run_financial_collection(self, data_type):
        """
        采集财务数据
        :param data_type: profit/balance/cashflow/growth/operation/dupont/forecast/dividend
        """
        self.logger.info(f"=== 开始采集财务数据：{data_type} ===")
        fetcher = BaostockFinancialFetcher()
        try:
            batch_methods = {
                'profit': fetcher.fetch_profit_batch,
                'balance': fetcher.fetch_balance_batch,
                'cashflow': fetcher.fetch_cashflow_batch,
                'growth': fetcher.fetch_growth_batch,
                'operation': fetcher.fetch_operation_batch,
                'dupont': fetcher.fetch_dupont_batch,
                'forecast': fetcher.fetch_forecast_batch,
                'dividend': fetcher.fetch_dividend_batch,
            }
            
            method = batch_methods.get(data_type)
            if not method:
                raise ValueError(f"未知数据类型：{data_type}")
            
            method(max_retries=3)
            self.logger.info(f"✅ 财务数据{data_type}采集完成")
            return {"data_type": data_type, "status": "success"}
        except Exception as e:
            self.logger.error(f"财务数据采集失败：{e}")
            raise
        finally:
            fetcher.close()
    
    # =====================================================
    # 第 3 层：东方财富扩展数据
    # =====================================================
    
    def run_eastmoney_collection(self, data_type):
        """
        采集东方财富数据
        :param data_type: moneyflow/north/shareholder/concept/analyst
        """
        self.logger.info(f"=== 开始采集东方财富数据：{data_type} ===")
        fetcher = EastMoneyFetcher()
        try:
            batch_methods = {
                'moneyflow': fetcher.fetch_moneyflow_batch,
                'north': fetcher.fetch_north_batch,
                'shareholder': fetcher.fetch_shareholder_batch,
                'concept': fetcher.fetch_concept_batch,
                'analyst': fetcher.fetch_analyst_batch,
            }
            
            method = batch_methods.get(data_type)
            if not method:
                raise ValueError(f"未知数据类型：{data_type}")
            
            method(max_retries=3)
            self.logger.info(f"✅ 东方财富数据{data_type}采集完成")
            return {"data_type": data_type, "status": "success"}
        except Exception as e:
            self.logger.error(f"东方财富数据采集失败：{e}")
            raise
        finally:
            fetcher.close()
    
    # =====================================================
    # 第 4 层：技术指标计算
    # =====================================================
    
    def run_indicator_calculation(self, indicator_type='all'):
        """
        计算技术指标
        :param indicator_type: all/macd/rsi/boll/cci/obv/adx
        """
        self.logger.info(f"=== 开始计算技术指标：{indicator_type} ===")
        calculator = IndicatorCalculator()
        try:
            if indicator_type == 'all':
                # 计算所有指标
                indicators = ['macd', 'rsi', 'boll', 'cci', 'obv', 'adx']
                results = {}
                for ind in indicators:
                    try:
                        self._calculate_single_indicator(calculator, ind)
                        results[ind] = "success"
                    except Exception as e:
                        self.logger.error(f"计算{ind}失败：{e}")
                        results[ind] = f"failed: {e}"
                return results
            else:
                self._calculate_single_indicator(calculator, indicator_type)
                return {"indicator": indicator_type, "status": "success"}
        except Exception as e:
            self.logger.error(f"指标计算失败：{e}")
            raise
        finally:
            calculator.close()
    
    def _calculate_single_indicator(self, calculator, indicator_type):
        """计算单个指标"""
        # 获取所有股票
        stocks = calculator.mysql_manager.query_all(
            "SELECT stock_code, market_type FROM stock_basic WHERE stock_status = 1"
        )
        total = len(stocks)
        success_count = 0
        
        for i, stock in enumerate(stocks):
            stock_code = stock['stock_code']
            try:
                # 调用对应的计算方法
                method_name = f"process_single_stock_{indicator_type.upper()}"
                if hasattr(calculator, method_name):
                    getattr(calculator, method_name)(stock_code)
                    success_count += 1
                if (i + 1) % 100 == 0:
                    self.logger.info(f"已计算 {i+1}/{total}，成功 {success_count}")
            except Exception as e:
                self.logger.error(f"计算 {stock_code} 的{indicator_type}失败：{e}")
        
        self.logger.info(f"✅ {indicator_type}计算完成：成功 {success_count}/{total}")
    
    # =====================================================
    # 第 5 层：多因子打分
    # =====================================================
    
    def run_multi_factor(self):
        """计算多因子打分"""
        self.logger.info("=== 开始计算多因子打分 ===")
        analyzer = MultiFactorAnalyzer()
        try:
            # 获取所有股票
            stocks = analyzer.mysql_manager.query_all(
                "SELECT stock_code, market_type FROM stock_basic WHERE stock_status = 1"
            )
            total = len(stocks)
            success_count = 0
            
            for i, stock in enumerate(stocks):
                stock_code = stock['stock_code']
                try:
                    analyzer.calculate_stock_score(stock_code)
                    success_count += 1
                    if (i + 1) % 100 == 0:
                        self.logger.info(f"已计算 {i+1}/{total}，成功 {success_count}")
                except Exception as e:
                    self.logger.error(f"计算 {stock_code} 多因子打分失败：{e}")
            
            self.logger.info(f"✅ 多因子打分完成：成功 {success_count}/{total}")
            return {"total": total, "success": success_count}
        except Exception as e:
            self.logger.error(f"多因子打分失败：{e}")
            raise
        finally:
            analyzer.close()


# =====================================================
# XXL-JOB 任务入口
# =====================================================

if __name__ == '__main__':
    """
    XXL-JOB 调用示例：
    
    # 日线采集
    python3 executor.py run_daily_collection --date_type=d
    
    # 财务数据采集
    python3 executor.py run_financial_collection --data_type=profit
    
    # 东方财富数据采集
    python3 executor.py run_eastmoney_collection --data_type=north
    
    # 指标计算
    python3 executor.py run_indicator_calculation --indicator_type=all
    
    # 多因子打分
    python3 executor.py run_multi_factor
    """
    
    import argparse
    
    parser = argparse.ArgumentParser(description='XXL-JOB 股票数据采集执行器')
    subparsers = parser.add_subparsers(dest='command', help='任务类型')
    
    # 日线采集
    daily_parser = subparsers.add_parser('run_daily_collection', help='采集日线/周线/月线')
    daily_parser.add_argument('--date_type', default='d', help='d=日线，w=周线，m=月线')
    
    # 分钟线采集
    min_parser = subparsers.add_parser('run_min_collection', help='采集分钟线')
    
    # 财务数据采集
    financial_parser = subparsers.add_parser('run_financial_collection', help='采集财务数据')
    financial_parser.add_argument('--data_type', required=True, 
                                  help='profit/balance/cashflow/growth/operation/dupont/forecast/dividend')
    
    # 东方财富数据采集
    eastmoney_parser = subparsers.add_parser('run_eastmoney_collection', help='采集东方财富数据')
    eastmoney_parser.add_argument('--data_type', required=True,
                                  help='moneyflow/north/shareholder/concept/analyst')
    
    # 指标计算
    indicator_parser = subparsers.add_parser('run_indicator_calculation', help='计算技术指标')
    indicator_parser.add_argument('--indicator_type', default='all',
                                  help='all/macd/rsi/boll/cci/obv/adx')
    
    # 多因子打分
    factor_parser = subparsers.add_parser('run_multi_factor', help='多因子打分')
    
    args = parser.parse_args()
    
    executor = StockDataExecutor()
    
    try:
        if args.command == 'run_daily_collection':
            executor.run_daily_collection(args.date_type)
        elif args.command == 'run_min_collection':
            executor.run_min_collection()
        elif args.command == 'run_financial_collection':
            executor.run_financial_collection(args.data_type)
        elif args.command == 'run_eastmoney_collection':
            executor.run_eastmoney_collection(args.data_type)
        elif args.command == 'run_indicator_calculation':
            executor.run_indicator_calculation(args.indicator_type)
        elif args.command == 'run_multi_factor':
            executor.run_multi_factor()
        else:
            parser.print_help()
    except Exception as e:
        executor.logger.error(f"任务执行失败：{e}")
        sys.exit(1)

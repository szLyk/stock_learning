#!/usr/bin/env python3
"""
股票财务数据采集脚本（带断点续传）

数据源: AkShare - stock_financial_abstract
功能: 获取财务摘要数据（80个指标）
特性: 支持断点续传，异常中断后可继续采集

Author: Xiao Luo
Date: 2026-04-02
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import pandas as pd
import akshare as ak
from datetime import datetime
from src.utils.mysql_tool import MySQLUtil
from src.utils.redis_tool import RedisUtil
from logs.logger import LogManager


class FinancialDataFetcher:
    """财务数据采集器"""
    
    DATA_TYPE = 'financial_summary'
    
    def __init__(self):
        self.mysql = MySQLUtil()
        self.mysql.connect()
        self.redis = RedisUtil() if RedisUtil else None
        self.logger = LogManager.get_logger("financial_fetcher")
        self.now_date = datetime.now().strftime('%Y-%m-%d')
    
    def close(self):
        self.mysql.close()
    
    def fetch_single_stock(self, stock_code: str) -> dict:
        """获取单只股票的财务数据"""
        try:
            df = ak.stock_financial_abstract(symbol=stock_code)
            
            if df.empty:
                return None
            
            # 解析数据：每行是一个指标，列是不同报告期
            results = []
            cols = df.columns.tolist()
            date_cols = [c for c in cols if c not in ['选项', '指标']]
            
            for date_col in date_cols:
                # 提取该报告期的所有指标
                row_data = {'report_date': date_col, 'stock_code': stock_code}
                
                for _, row in df.iterrows():
                    indicator = row['指标']
                    value = row[date_col]
                    
                    # 映射指标名到字段名（完整 67 个字段）
                    field_map = {
                        # 利润指标
                        '归母净利润': 'parent_net_profit',
                        '营业总收入': 'total_revenue',
                        '营业成本': 'operating_cost',
                        '净利润': 'net_profit',
                        '扣非净利润': 'deduct_net_profit',
                        
                        # 资产指标
                        '股东权益合计(净资产)': 'net_assets',
                        '商誉': 'goodwill',
                        
                        # 现金流指标
                        '经营现金流量净额': 'operating_cash_flow',
                        
                        # 每股指标
                        '基本每股收益': 'eps_basic',
                        '稀释每股收益': 'eps_diluted',
                        '摊薄每股收益_最新股数': 'eps_diluted_latest',
                        '摊薄每股净资产_期末股数': 'bvps_diluted',
                        '调整每股净资产_期末股数': 'bvps_adjusted',
                        '每股净资产_最新股数': 'bvps_latest',
                        '每股经营现金流': 'cfps',
                        '每股现金流量净额': 'cash_flow_per_share',
                        '每股企业自由现金流量': 'fcff_per_share',
                        '每股股东自由现金流量': 'fcfe_per_share',
                        '每股未分配利润': 'retained_earnings_per_share',
                        '每股资本公积金': 'capital_reserve_per_share',
                        '每股盈余公积金': 'surplus_reserve_per_share',
                        '每股留存收益': 'retained_per_share',
                        '每股营业收入': 'revenue_per_share',
                        '每股营业总收入': 'total_revenue_per_share',
                        '每股息税前利润': 'ebit_per_share',
                        
                        # 盈利能力指标
                        '净资产收益率(ROE)': 'roe',
                        '摊薄净资产收益率': 'roe_diluted',
                        '净资产收益率_平均': 'roe_avg',
                        '净资产收益率_平均_扣除非经常损益': 'roe_avg_deduct',
                        '摊薄净资产收益率_扣除非经常损益': 'roe_diluted_deduct',
                        '息税前利润率': 'ebit_margin',
                        '总资产报酬率': 'roa',
                        '总资本回报率': 'rota',
                        '投入资本回报率': 'roic',
                        '息前税后总资产报酬率_平均': 'roa_avg_after_tax',
                        '毛利率': 'gross_margin',
                        '销售净利率': 'net_margin',
                        '成本费用利润率': 'cost_profit_ratio',
                        '营业利润率': 'operating_margin',
                        '总资产净利率_平均': 'roa_avg',
                        '总资产净利率_平均(含少数股东损益)': 'roa_avg_minority',
                        
                        # 成长能力指标
                        '营业总收入增长率': 'revenue_growth',
                        '归属母公司净利润增长率': 'profit_growth',
                        
                        # 运营能力指标
                        '经营活动净现金/销售收入': 'cash_to_revenue',
                        '经营性现金净流量/营业总收入': 'cash_to_total_revenue',
                        '成本费用率': 'cost_ratio',
                        '期间费用率': 'expense_ratio',
                        '销售成本率': 'cost_of_sales_ratio',
                        '经营活动净现金/归属母公司的净利润': 'cash_to_profit',
                        '所得税/利润总额': 'tax_to_profit',
                        
                        # 偿债能力指标
                        '流动比率': 'current_ratio',
                        '速动比率': 'quick_ratio',
                        '保守速动比率': 'conservative_quick_ratio',
                        '资产负债率': 'debt_ratio',
                        '权益乘数': 'equity_multiplier',
                        '权益乘数(含少数股权的净资产)': 'equity_multiplier_minority',
                        '产权比率': 'debt_equity_ratio',
                        '现金比率': 'cash_ratio',
                        
                        # 周转能力指标
                        '应收账款周转率': 'ar_turnover',
                        '应收账款周转天数': 'ar_turnover_days',
                        '存货周转率': 'inventory_turnover',
                        '存货周转天数': 'inventory_turnover_days',
                        '总资产周转率': 'asset_turnover',
                        '总资产周转天数': 'asset_turnover_days',
                        '流动资产周转率': 'current_asset_turnover',
                        '流动资产周转天数': 'current_asset_turnover_days',
                        '应付账款周转率': 'ap_turnover',
                    }
                    
                    if indicator in field_map:
                        field_name = field_map[indicator]
                        try:
                            row_data[field_name] = float(value) if value else None
                        except:
                            row_data[field_name] = None
                
                results.append(row_data)
            
            return results
            
        except Exception as e:
            self.logger.error(f"获取 {stock_code} 财务数据失败: {e}")
            return None
    
    def save_to_db(self, data_list: list) -> int:
        """保存到数据库"""
        if not data_list:
            return 0
        
        sql = """
            INSERT INTO stock_financial_summary 
            (stock_code, report_date, 
             parent_net_profit, total_revenue, operating_cost, net_profit, deduct_net_profit,
             net_assets, goodwill, operating_cash_flow,
             eps_basic, eps_diluted, eps_diluted_latest, bvps_diluted, bvps_adjusted, bvps_latest,
             cfps, cash_flow_per_share, fcff_per_share, fcfe_per_share,
             retained_earnings_per_share, capital_reserve_per_share, surplus_reserve_per_share,
             retained_per_share, revenue_per_share, total_revenue_per_share, ebit_per_share,
             roe, roe_diluted, roe_avg, roe_avg_deduct, roe_diluted_deduct,
             ebit_margin, roa, rota, roic, roa_avg_after_tax,
             gross_margin, net_margin, cost_profit_ratio, operating_margin, roa_avg, roa_avg_minority,
             revenue_growth, profit_growth,
             cash_to_revenue, cash_to_total_revenue, cost_ratio, expense_ratio,
             cost_of_sales_ratio, cash_to_profit, tax_to_profit,
             current_ratio, quick_ratio, conservative_quick_ratio, debt_ratio,
             equity_multiplier, equity_multiplier_minority, debt_equity_ratio, cash_ratio,
             ar_turnover, ar_turnover_days, inventory_turnover, inventory_turnover_days,
             asset_turnover, asset_turnover_days, current_asset_turnover, current_asset_turnover_days, ap_turnover)
            VALUES (%(stock_code)s, %(report_date)s,
                    %(parent_net_profit)s, %(total_revenue)s, %(operating_cost)s, %(net_profit)s, %(deduct_net_profit)s,
                    %(net_assets)s, %(goodwill)s, %(operating_cash_flow)s,
                    %(eps_basic)s, %(eps_diluted)s, %(eps_diluted_latest)s, %(bvps_diluted)s, %(bvps_adjusted)s, %(bvps_latest)s,
                    %(cfps)s, %(cash_flow_per_share)s, %(fcff_per_share)s, %(fcfe_per_share)s,
                    %(retained_earnings_per_share)s, %(capital_reserve_per_share)s, %(surplus_reserve_per_share)s,
                    %(retained_per_share)s, %(revenue_per_share)s, %(total_revenue_per_share)s, %(ebit_per_share)s,
                    %(roe)s, %(roe_diluted)s, %(roe_avg)s, %(roe_avg_deduct)s, %(roe_diluted_deduct)s,
                    %(ebit_margin)s, %(roa)s, %(rota)s, %(roic)s, %(roa_avg_after_tax)s,
                    %(gross_margin)s, %(net_margin)s, %(cost_profit_ratio)s, %(operating_margin)s, %(roa_avg)s, %(roa_avg_minority)s,
                    %(revenue_growth)s, %(profit_growth)s,
                    %(cash_to_revenue)s, %(cash_to_total_revenue)s, %(cost_ratio)s, %(expense_ratio)s,
                    %(cost_of_sales_ratio)s, %(cash_to_profit)s, %(tax_to_profit)s,
                    %(current_ratio)s, %(quick_ratio)s, %(conservative_quick_ratio)s, %(debt_ratio)s,
                    %(equity_multiplier)s, %(equity_multiplier_minority)s, %(debt_equity_ratio)s, %(cash_ratio)s,
                    %(ar_turnover)s, %(ar_turnover_days)s, %(inventory_turnover)s, %(inventory_turnover_days)s,
                    %(asset_turnover)s, %(asset_turnover_days)s, %(current_asset_turnover)s, %(current_asset_turnover_days)s, %(ap_turnover)s)
            ON DUPLICATE KEY UPDATE
                parent_net_profit = VALUES(parent_net_profit),
                total_revenue = VALUES(total_revenue),
                net_profit = VALUES(net_profit),
                roe = VALUES(roe),
                gross_margin = VALUES(gross_margin),
                update_time = NOW()
        """
        
        import numpy as np
        
        count = 0
        for data in data_list:
            try:
                # 将NaN转换为None
                clean_data = {}
                for key, value in data.items():
                    if isinstance(value, float) and (np.isnan(value) or value is None):
                        clean_data[key] = None
                    else:
                        clean_data[key] = value
                
                self.mysql.execute(sql, clean_data)
                count += 1
            except Exception as e:
                self.logger.error(f"保存数据失败: {e}")
        
        return count
    
    def get_pending_stocks(self) -> list:
        """获取待采集股票列表（支持断点续传）"""
        if self.redis:
            pending = self.redis.get_unprocessed_stocks(self.now_date, self.DATA_TYPE)
            if pending:
                self.logger.info(f"📌 Redis断点续传: {len(pending)}只待处理")
                return pending
        
        # 从数据库获取全部股票
        sql = "SELECT stock_code FROM stock_basic WHERE stock_status = 1"
        result = self.mysql.query_all(sql)
        
        if not result:
            return []
        
        stock_list = [row['stock_code'] for row in result]
        
        # 初始化Redis
        if self.redis:
            self.redis.add_unprocessed_stocks(stock_list, self.now_date, self.DATA_TYPE)
            self.logger.info(f"✅ Redis初始化: {len(stock_list)}只股票")
        
        return stock_list
    
    def mark_as_processed(self, stock_code: str):
        """标记为已处理"""
        if self.redis:
            self.redis.remove_unprocessed_stocks([stock_code], self.now_date, self.DATA_TYPE)
    
    def test_fetch(self, test_count: int = 5):
        """测试模式：采集少量股票"""
        self.logger.info(f"=== 测试模式: 采集{test_count}只股票 ===")
        
        # 获取测试股票
        sql = f"SELECT stock_code FROM stock_basic WHERE stock_status = 1 LIMIT {test_count}"
        result = self.mysql.query_all(sql)
        
        if not result:
            self.logger.error("无法获取股票列表")
            return
        
        test_stocks = [row['stock_code'] for row in result]
        
        success = 0
        failed = 0
        
        for i, stock_code in enumerate(test_stocks):
            self.logger.info(f"[{i+1}/{len(test_stocks)}] 获取 {stock_code}...")
            
            data_list = self.fetch_single_stock(stock_code)
            
            if data_list:
                count = self.save_to_db(data_list)
                if count > 0:
                    success += 1
                    self.logger.info(f"  ✅ 保存{count}期数据")
                else:
                    failed += 1
            else:
                failed += 1
            
            time.sleep(1)
        
        self.logger.info(f"\n测试完成: 成功{success}, 失败{failed}")
    
    def fetch_all(self, batch_size: int = 50, delay: float = 0.5):
        """全量采集"""
        self.logger.info("=== 开始全量采集财务数据 ===")
        
        pending = self.get_pending_stocks()
        
        if not pending:
            self.logger.info("✅ 所有股票已采集完成")
            return
        
        total = len(pending)
        success = 0
        failed = 0
        
        for i, stock_code in enumerate(pending):
            try:
                data_list = self.fetch_single_stock(stock_code)
                
                if data_list:
                    count = self.save_to_db(data_list)
                    if count > 0:
                        success += 1
                        self.mark_as_processed(stock_code)
                else:
                    failed += 1
                
                if (i + 1) % batch_size == 0:
                    self.logger.info(f"进度: {i+1}/{total}, 成功{success}, 失败{failed}")
                
                time.sleep(delay)
                
            except Exception as e:
                self.logger.error(f"处理 {stock_code} 失败: {e}")
                failed += 1
        
        self.logger.info(f"采集完成: 总计{total}, 成功{success}, 失败{failed}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='财务数据采集')
    parser.add_argument('--test', action='store_true', help='测试模式')
    parser.add_argument('--test-count', type=int, default=5, help='测试数量')
    parser.add_argument('--all', action='store_true', help='全量采集')
    parser.add_argument('--batch', type=int, default=50, help='批次大小')
    
    args = parser.parse_args()
    
    fetcher = FinancialDataFetcher()
    
    try:
        if args.test:
            fetcher.test_fetch(args.test_count)
        elif args.all:
            fetcher.fetch_all(batch_size=args.batch)
        else:
            fetcher.test_fetch(5)
    finally:
        fetcher.close()


if __name__ == '__main__':
    main()
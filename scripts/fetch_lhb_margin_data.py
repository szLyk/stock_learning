#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
龙虎榜、基金持仓、融资融券数据采集脚本（支持断点续传）

数据源: AKShare
功能:
    1. 龙虎榜明细采集 (stock_lhb_detail_em)
    2. 机构龙虎榜统计 (stock_lhb_jgstatistic_em)
    3. 基金持仓 (stock_report_fund_hold)
    4. 融资融券明细 (stock_margin_detail_sse)

断点续传机制:
    - 使用 Redis 记录已处理的日期/股票
    - 中断后重新运行会自动跳过已处理的数据
    - 数据库使用 INSERT ... ON DUPLICATE KEY UPDATE 保证幂等性

使用方法:
    # 采集龙虎榜（最近3天）
    python scripts/fetch_lhb_margin_data.py --lhb
    
    # 采集基金持仓
    python scripts/fetch_lhb_margin_data.py --fund
    
    # 采集融资融券
    python scripts/fetch_lhb_margin_data.py --margin
    
    # 全部采集
    python scripts/fetch_lhb_margin_data.py --all
    
    # 清除断点记录（重新采集）
    python scripts/fetch_lhb_margin_data.py --clear

Author: Xiao Luo
Date: 2026-04-02
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import argparse
import pandas as pd
import numpy as np
import akshare as ak
from datetime import datetime, timedelta
from typing import Optional, Set
from src.utils.mysql_tool import MySQLUtil
from src.utils.redis_tool import RedisUtil
from logs.logger import LogManager


class LHBMarginFetcher:
    """龙虎榜、基金持仓、融资融券数据采集器（支持断点续传）"""
    
    def __init__(self):
        self.mysql = MySQLUtil()
        self.mysql.connect()
        self.redis = RedisUtil() if RedisUtil else None
        self.logger = LogManager.get_logger("lhb_margin_fetcher")
        self.now_date = datetime.now().strftime('%Y-%m-%d')
    
    def close(self):
        self.mysql.close()
    
    # =====================================================
    # Redis 断点续传机制
    # =====================================================
    
    def _get_redis_key(self, data_type: str) -> str:
        """获取 Redis key"""
        return f"akshare:{data_type}"
    
    def _get_processed_dates(self, data_type: str) -> Set[str]:
        """获取已处理的日期列表（从 Redis）"""
        if not self.redis:
            return set()
        
        key = f"{self._get_redis_key(data_type)}:stock_data:{self.now_date}:processed"
        try:
            return set(self.redis.client.smembers(key))
        except Exception as e:
            self.logger.warning(f"获取 Redis 数据失败: {e}")
            return set()
    
    def _mark_date_processed(self, date_str: str, data_type: str):
        """标记日期为已处理"""
        if not self.redis:
            return
        
        key = f"{self._get_redis_key(data_type)}:stock_data:{self.now_date}:processed"
        try:
            self.redis.client.sadd(key, date_str)
        except Exception as e:
            self.logger.warning(f"写入 Redis 失败: {e}")
    
    def _clear_processed_marks(self, data_type: str = None):
        """清除已处理标记（用于重新采集）"""
        if not self.redis:
            return
        
        data_types = [data_type] if data_type else ['lhb_detail', 'lhb_institution', 'fund_hold', 'margin_detail']
        
        for dt in data_types:
            key = f"{self._get_redis_key(dt)}:stock_data:{self.now_date}:processed"
            try:
                self.redis.client.delete(key)
                self.logger.info(f"✅ 已清除 {dt} 断点记录")
            except Exception as e:
                self.logger.warning(f"清除 Redis 失败: {e}")
    
    # =====================================================
    # 龙虎榜数据采集
    # =====================================================
    
    def fetch_lhb_detail(self, start_date: str, end_date: str) -> int:
        """
        采集龙虎榜明细（支持断点续传）
        
        龙虎榜接口本身返回的是全量数据，使用数据库的 ON DUPLICATE KEY UPDATE 
        保证幂等性，不需要额外的断点续传检查。
        
        Args:
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
        
        Returns:
            插入记录数
        """
        self.logger.info(f"=== 采集龙虎榜明细: {start_date} ~ {end_date} ===")
        
        try:
            df = ak.stock_lhb_detail_em(start_date=start_date, end_date=end_date)
            
            if df.empty:
                self.logger.warning("无龙虎榜数据")
                return 0
            
            # 列名映射
            rename_map = {
                '代码': 'stock_code',
                '名称': 'stock_name',
                '上榜日': 'trade_date',
                '收盘价': 'close_price',
                '涨跌幅': 'change_pct',
                '龙虎榜净买额': 'net_buy_amount',
                '龙虎榜买入额': 'buy_amount',
                '龙虎榜卖出额': 'sell_amount',
                '龙虎榜成交额': 'turnover_amount',
                '市场总成交额': 'market_amount',
                '净买额占总成交比': 'net_buy_ratio',
                '成交额占总成交比': 'turnover_ratio',
                '换手率': 'turnover_rate',
                '流通市值': 'float_mv',
                '上榜原因': 'reason',
                '解读': 'interpretation',
                '上榜后1日': 'after_1d',
                '上榜后2日': 'after_2d',
                '上榜后5日': 'after_5d',
                '上榜后10日': 'after_10d',
            }
            
            existing_cols = {k: v for k, v in rename_map.items() if k in df.columns}
            df = df.rename(columns=existing_cols)
            
            # 数据清洗
            df['trade_date'] = pd.to_datetime(df['trade_date']).dt.date
            
            numeric_cols = ['close_price', 'change_pct', 'net_buy_amount', 'buy_amount',
                          'sell_amount', 'turnover_amount', 'market_amount',
                          'net_buy_ratio', 'turnover_ratio', 'turnover_rate', 'float_mv',
                          'after_1d', 'after_2d', 'after_5d', 'after_10d']
            
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 数据清洗：将 NaN 转换为 None
            df = df.replace({np.nan: None})
            df = df.where(pd.notnull(df), None)
            
            # 只保留需要的列
            result_cols = ['stock_code', 'stock_name', 'trade_date', 'close_price', 'change_pct',
                          'net_buy_amount', 'buy_amount', 'sell_amount', 'turnover_amount', 'market_amount',
                          'net_buy_ratio', 'turnover_ratio', 'turnover_rate', 'float_mv',
                          'reason', 'interpretation', 'after_1d', 'after_2d', 'after_5d', 'after_10d']
            result_cols = [col for col in result_cols if col in df.columns]
            df = df[result_cols]
            
            # 保存到数据库
            count = self.mysql.batch_insert_or_update(
                'stock_lhb_detail', df, ['stock_code', 'trade_date'])
            
            self.logger.info(f"✅ 龙虎榜明细采集完成: {count} 条")
            return count
            
        except Exception as e:
            self.logger.error(f"采集龙虎榜明细失败: {e}")
            return 0
    
    def fetch_lhb_institution(self) -> int:
        """
        采集机构龙虎榜统计（支持断点续传）
        
        机构龙虎榜接口返回的是统计汇总数据，使用数据库的 ON DUPLICATE KEY UPDATE
        保证幂等性。
        
        Returns:
            插入记录数
        """
        self.logger.info("=== 采集机构龙虎榜统计 ===")
        
        try:
            df = ak.stock_lhb_jgstatistic_em()
            
            if df.empty:
                self.logger.warning("无机构龙虎榜数据")
                return 0
            
            # 列名映射
            rename_map = {
                '代码': 'stock_code',
                '名称': 'stock_name',
                '收盘价': 'close_price',
                '涨跌幅': 'change_pct',
                '龙虎榜成交金额': 'total_amount',
                '上榜次数': 'appear_count',
                '机构买入额': 'inst_buy_amount',
                '机构买入次数': 'inst_buy_count',
                '机构卖出额': 'inst_sell_amount',
                '机构卖出次数': 'inst_sell_count',
                '机构净买额': 'inst_net_buy',
                '近1个月涨跌幅': 'change_1m',
                '近3个月涨跌幅': 'change_3m',
                '近6个月涨跌幅': 'change_6m',
                '近1年涨跌幅': 'change_1y',
            }
            
            existing_cols = {k: v for k, v in rename_map.items() if k in df.columns}
            df = df.rename(columns=existing_cols)
            
            # 添加统计日期
            df['stat_date'] = datetime.now().date()
            
            # 数据清洗
            numeric_cols = ['close_price', 'change_pct', 'total_amount', 'appear_count',
                          'inst_buy_amount', 'inst_buy_count', 'inst_sell_amount',
                          'inst_sell_count', 'inst_net_buy',
                          'change_1m', 'change_3m', 'change_6m', 'change_1y']
            
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 数据清洗：将 NaN 转换为 None
            df = df.replace({np.nan: None})
            df = df.where(pd.notnull(df), None)
            
            # 只保留需要的列
            result_cols = ['stock_code', 'stock_name', 'close_price', 'change_pct',
                          'total_amount', 'appear_count',
                          'inst_buy_amount', 'inst_buy_count', 'inst_sell_amount', 'inst_sell_count', 'inst_net_buy',
                          'change_1m', 'change_3m', 'change_6m', 'change_1y', 'stat_date']
            result_cols = [col for col in result_cols if col in df.columns]
            df = df[result_cols]
            
            count = self.mysql.batch_insert_or_update(
                'stock_lhb_institution', df, ['stock_code', 'stat_date'])
            
            self.logger.info(f"✅ 机构龙虎榜统计采集完成: {count} 条")
            return count
            
        except Exception as e:
            self.logger.error(f"采集机构龙虎榜统计失败: {e}")
            return 0
    
    # =====================================================
    # 基金持仓数据采集
    # =====================================================
    
    def fetch_fund_hold(self, date: str = None) -> int:
        """
        采集基金持仓列表（支持断点续传）
        
        基金持仓接口返回的是全量数据，使用数据库的 ON DUPLICATE KEY UPDATE
        保证幂等性。
        
        Args:
            date: 报告期 (如 20210331)，默认最新
        
        Returns:
            插入记录数
        """
        self.logger.info("=== 采集基金持仓列表 ===")
        
        try:
            if date:
                df = ak.stock_report_fund_hold(symbol='基金持仓', date=date)
            else:
                df = ak.stock_report_fund_hold()
            
            if df.empty:
                self.logger.warning("无基金持仓数据")
                return 0
            
            # 列名映射
            rename_map = {
                '股票代码': 'stock_code',
                '股票简称': 'stock_name',
                '持有基金家数': 'fund_count',
                '持股总数': 'hold_shares',
                '持股市值': 'hold_value',
                '持股变化': 'change_type',
                '持股变动数值': 'change_shares',
                '持股变动比例': 'change_ratio',
            }
            
            existing_cols = {k: v for k, v in rename_map.items() if k in df.columns}
            df = df.rename(columns=existing_cols)
            
            # 添加报告期
            if 'report_date' not in df.columns:
                df['report_date'] = date if date else datetime.now().strftime('%Y%m%d')
            
            # 数据清洗
            numeric_cols = ['fund_count', 'hold_shares', 'hold_value', 'change_shares', 'change_ratio']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 数据清洗：将 NaN 转换为 None
            df = df.replace({np.nan: None})
            df = df.where(pd.notnull(df), None)
            
            # 只保留需要的列
            result_cols = ['stock_code', 'stock_name', 'report_date',
                          'fund_count', 'hold_shares', 'hold_value',
                          'change_type', 'change_shares', 'change_ratio']
            result_cols = [col for col in result_cols if col in df.columns]
            df = df[result_cols]
            
            # 保存到数据库
            count = self.mysql.batch_insert_or_update(
                'stock_fund_hold', df, ['stock_code', 'report_date'])
            
            self.logger.info(f"✅ 基金持仓采集完成: {count} 条")
            return count
            
        except Exception as e:
            self.logger.error(f"采集基金持仓失败: {e}")
            return 0
    
    def fetch_fund_hold_detail(self, stock_code: str) -> int:
        """采集个股基金持仓明细"""
        try:
            df = ak.stock_report_fund_hold_detail(symbol=stock_code)
            
            if df.empty:
                return 0
            
            # 列名映射
            rename_map = {
                '股票代码': 'stock_code',
                '股票简称': 'stock_name',
                '持股数': 'hold_shares',
                '持股市值': 'hold_value',
                '占总股本比例': 'total_ratio',
                '占流通股本比例': 'float_ratio',
            }
            
            existing_cols = {k: v for k, v in rename_map.items() if k in df.columns}
            df = df.rename(columns=existing_cols)
            
            df['stat_date'] = datetime.now().date()
            
            # 数据清洗
            numeric_cols = ['hold_shares', 'hold_value', 'total_ratio', 'float_ratio']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            df = df.replace({np.nan: None})
            df = df.where(pd.notnull(df), None)
            
            count = self.mysql.batch_insert_or_update(
                'stock_fund_hold_detail', df, ['stock_code', 'stat_date'])
            
            return count
            
        except Exception as e:
            self.logger.error(f"采集 {stock_code} 基金持仓明细失败: {e}")
            return 0
    
    def fetch_fund_hold_batch(self, limit: int = 100):
        """批量采集个股基金持仓明细"""
        self.logger.info(f"=== 批量采集基金持仓明细 ===")
        
        sql = f"""
        SELECT stock_code FROM stock_fund_hold 
        WHERE fund_count > 10 
        ORDER BY fund_count DESC 
        LIMIT {limit}
        """
        result = self.mysql.query_all(sql)
        
        if not result:
            self.logger.warning("无股票列表，请先采集基金持仓列表")
            return
        
        total = len(result)
        success = 0
        
        for i, row in enumerate(result):
            stock_code = row['stock_code']
            count = self.fetch_fund_hold_detail(stock_code)
            if count > 0:
                success += 1
            
            if (i + 1) % 20 == 0:
                self.logger.info(f"进度: {i+1}/{total}, 成功: {success}")
            
            time.sleep(0.3)
        
        self.logger.info(f"✅ 基金持仓明细采集完成: {success}/{total}")
    
    # =====================================================
    # 融资融券数据采集（带断点续传）
    # =====================================================
    
    def fetch_margin_detail(self, date: str = None) -> int:
        """
        采集融资融券明细（支持断点续传）
        
        按日期采集，使用 Redis 记录已处理的日期。
        
        Args:
            date: 日期 (YYYYMMDD)，默认今天
        
        Returns:
            插入记录数
        """
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
        
        self.logger.info(f"=== 采集融资融券明细: {date} ===")
        
        # 断点续传检查：检查该日期是否已处理
        data_type = 'margin_detail'
        processed = self._get_processed_dates(data_type)
        
        if date in processed:
            self.logger.info(f"📅 {date} 已处理，跳过（断点续传）")
            return 0
        
        try:
            df = ak.stock_margin_detail_sse(date=date)
            
            if df.empty:
                self.logger.warning(f"无融资融券数据: {date}")
                # 标记为已处理（避免重复检查空数据）
                self._mark_date_processed(date, data_type)
                return 0
            
            # 列名映射
            rename_map = {
                '信用交易日期': 'trade_date',
                '标的证券代码': 'stock_code',
                '标的证券简称': 'stock_name',
                '融资余额': 'margin_balance',
                '融资买入额': 'margin_buy',
                '融资偿还额': 'margin_repay',
                '融券余量': 'short_balance',
                '融券卖出量': 'short_sell',
                '融券偿还量': 'short_repay',
            }
            
            existing_cols = {k: v for k, v in rename_map.items() if k in df.columns}
            df = df.rename(columns=existing_cols)
            
            # 数据清洗
            if 'trade_date' in df.columns:
                df['trade_date'] = pd.to_datetime(df['trade_date'].astype(str), format='%Y%m%d').dt.date
            else:
                df['trade_date'] = datetime.strptime(date, '%Y%m%d').date
            
            numeric_cols = ['margin_balance', 'margin_buy', 'margin_repay',
                          'short_balance', 'short_sell', 'short_repay']
            
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 过滤非股票（ETF等）
            if 'stock_code' in df.columns:
                df = df[df['stock_code'].str.match(r'^\d{6}$')]
            
            # 数据清洗：将 NaN 转换为 None
            df = df.replace({np.nan: None})
            df = df.where(pd.notnull(df), None)
            
            # 只保留需要的列
            result_cols = ['stock_code', 'stock_name', 'trade_date',
                          'margin_balance', 'margin_buy', 'margin_repay',
                          'short_balance', 'short_sell', 'short_repay']
            result_cols = [col for col in result_cols if col in df.columns]
            df = df[result_cols]
            
            # 保存到数据库
            count = self.mysql.batch_insert_or_update(
                'stock_margin_detail', df, ['stock_code', 'trade_date'])
            
            # 标记该日期为已处理
            self._mark_date_processed(date, data_type)
            
            self.logger.info(f"✅ 融资融券明细采集完成: {count} 条")
            return count
            
        except Exception as e:
            self.logger.error(f"采集融资融券明细失败: {e}")
            return 0
    
    def fetch_margin_history(self, days: int = 30):
        """采集历史融资融券数据（带断点续传）"""
        self.logger.info(f"=== 采集历史融资融券数据（最近{days}天）===")
        
        total = 0
        skipped = 0
        
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y%m%d')
            count = self.fetch_margin_detail(date)
            
            if count == 0:
                skipped += 1
            else:
                total += count
            
            time.sleep(0.5)
        
        self.logger.info(f"✅ 历史融资融券采集完成: 新增 {total} 条，跳过 {skipped} 天")
    
    # =====================================================
    # 综合采集
    # =====================================================
    
    def fetch_all(self, lhb_days: int = 3, margin_days: int = 7):
        """
        综合采集所有数据
        
        Args:
            lhb_days: 龙虎榜采集天数
            margin_days: 融资融券采集天数
        """
        self.logger.info("=" * 60)
        self.logger.info("开始综合数据采集（支持断点续传）")
        self.logger.info("=" * 60)
        
        # 1. 龙虎榜
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=lhb_days)).strftime('%Y%m%d')
        
        self.fetch_lhb_detail(start_date, end_date)
        time.sleep(1)
        
        self.fetch_lhb_institution()
        time.sleep(1)
        
        # 2. 基金持仓
        self.fetch_fund_hold()
        time.sleep(1)
        
        # 3. 融资融券（带断点续传）
        self.fetch_margin_history(days=margin_days)
        
        self.logger.info("=" * 60)
        self.logger.info("✅ 综合数据采集完成")
        self.logger.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(description='龙虎榜、基金持仓、融资融券数据采集（支持断点续传）')
    
    parser.add_argument('--lhb', action='store_true', help='采集龙虎榜数据')
    parser.add_argument('--lhb-days', type=int, default=3, help='龙虎榜采集天数')
    
    parser.add_argument('--fund', action='store_true', help='采集基金持仓数据')
    parser.add_argument('--fund-detail', action='store_true', help='采集基金持仓明细')
    
    parser.add_argument('--margin', action='store_true', help='采集融资融券数据')
    parser.add_argument('--margin-days', type=int, default=7, help='融资融券采集天数')
    parser.add_argument('--margin-date', type=str, help='融资融券指定日期(YYYYMMDD)')
    
    parser.add_argument('--all', action='store_true', help='全部采集')
    
    parser.add_argument('--clear', action='store_true', help='清除断点记录（重新采集）')
    parser.add_argument('--clear-type', type=str, help='清除指定类型的断点记录')
    
    args = parser.parse_args()
    
    fetcher = LHBMarginFetcher()
    
    try:
        if args.clear:
            fetcher._clear_processed_marks(args.clear_type)
            return
        
        if args.all:
            fetcher.fetch_all(lhb_days=args.lhb_days, margin_days=args.margin_days)
        else:
            if args.lhb:
                end_date = datetime.now().strftime('%Y%m%d')
                start_date = (datetime.now() - timedelta(days=args.lhb_days)).strftime('%Y%m%d')
                fetcher.fetch_lhb_detail(start_date, end_date)
                fetcher.fetch_lhb_institution()
            
            if args.fund:
                fetcher.fetch_fund_hold()
            
            if args.fund_detail:
                fetcher.fetch_fund_hold_batch()
            
            if args.margin:
                if args.margin_date:
                    fetcher.fetch_margin_detail(args.margin_date)
                else:
                    fetcher.fetch_margin_history(days=args.margin_days)
        
        if not any([args.lhb, args.fund, args.fund_detail, args.margin, args.all, args.clear]):
            parser.print_help()
    
    finally:
        fetcher.close()


if __name__ == '__main__':
    main()
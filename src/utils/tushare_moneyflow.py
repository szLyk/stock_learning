# -*- coding: utf-8 -*-
"""
Tushare 资金流向数据采集工具
功能：个股资金流向数据采集（带 Redis 断点续传）

接口：pro.moneyflow
积分要求：120 积分
调用频率：500 次/分钟（建议控制在 30 次/分钟）
"""

import datetime
import pandas as pd
import time
import tushare as ts
from logs.logger import LogManager
from src.utils.mysql_tool import MySQLUtil
from src.utils.redis_tool import RedisUtil


class TushareMoneyflowFetcher:
    """Tushare 资金流向数据采集器（支持 Redis 断点续传）"""
    
    def __init__(self, token=None):
        self.logger = LogManager.get_logger("tushare_moneyflow")
        self.mysql_manager = MySQLUtil()
        self.mysql_manager.connect()
        self.redis_manager = RedisUtil() if RedisUtil else None
        self.now_date = datetime.datetime.now().strftime('%Y-%m-%d')
        
        # 初始化 Tushare
        if token:
            ts.set_token(token)
        self.pro = ts.pro_api()
        
        # 请求频率控制
        self.request_count = 0
        self.last_request_time = 0
        self.min_request_interval = 2.0  # 最小请求间隔（秒）- 保守设置
        
    # =====================================================
    # Redis 断点续传机制
    # =====================================================
    
    def get_pending_stocks(self, date=None):
        """
        从 Redis 或数据库获取待采集股票（支持断点续传）
        :param date: 日期字符串（YYYY-MM-DD），None 表示使用当前日期
        """
        if self.redis_manager is None:
            return self._get_pending_stocks_from_db()
        
        # 使用传入的日期或当前日期
        target_date = date if date else self.now_date
        
        # Redis key 格式：tushare:moneyflow:stock_data:2026-03-17:unprocessed
        redis_key = "tushare:moneyflow"
        
        # 1. 优先从 Redis 获取待处理股票（剩余的）
        pending = self.redis_manager.get_unprocessed_stocks(target_date, redis_key)
        
        if pending:
            # Redis 中有待处理股票，直接返回（断点续传）
            self.logger.info(f"📌 从 Redis 获取 {len(pending)} 只待处理股票（断点续传）")
            return pending
        
        # 2. Redis 为空，从数据库获取并初始化（首次执行）
        stock_list = self._get_pending_stocks_from_db()
        if stock_list and len(stock_list) > 0:
            self.redis_manager.add_unprocessed_stocks(stock_list, target_date, redis_key)
            self.logger.info(f"✅ Redis 初始化完成：{len(stock_list)}只股票（首次执行）")
            
            # 重新从 Redis 获取（确保初始化成功）
            pending_after_init = self.redis_manager.get_unprocessed_stocks(target_date, redis_key)
            self.logger.info(f"验证：Redis 初始化后有 {len(pending_after_init)} 只股票")
            
            return stock_list
        
        # 3. 数据库也为空
        self.logger.info("⚠️ 未找到待采集股票")
        return None
    
    def _get_pending_stocks_from_db(self):
        """从数据库获取待采集股票（30 天内未更新的）"""
        # 获取 30 天内未更新的股票
        sql = """
        SELECT a.ts_code, b.name 
        FROM update_tushare_record a
        LEFT JOIN stock_basic b ON a.ts_code = b.ts_code
        WHERE (a.update_moneyflow IS NULL OR a.update_moneyflow < DATE_SUB(CURDATE(), INTERVAL 30 DAY))
          AND b.list_status = 'L'
        """
        
        result = self.mysql_manager.query_all(sql)
        if not result:
            # 如果是新表，从 stock_basic 获取所有股票
            sql = "SELECT ts_code, name FROM stock_basic WHERE list_status = 'L'"
            result = self.mysql_manager.query_all(sql)
        
        if not result:
            return []
        
        return [r['ts_code'] for r in result]
    
    def update_record(self, ts_code, trade_date):
        """更新采集记录表"""
        sql = """
        INSERT INTO update_tushare_record (ts_code, update_moneyflow)
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE update_moneyflow = VALUES(update_moneyflow)
        """
        self.mysql_manager.execute(sql, (ts_code, trade_date))
    
    def mark_as_processed(self, ts_code):
        """标记股票为已处理（从 Redis unprocessed 集合中移除）"""
        if self.redis_manager is None:
            return
        
        redis_key = "tushare:moneyflow"
        self.redis_manager.remove_unprocessed_stocks([ts_code], self.now_date, redis_key)
        self.logger.debug(f"✅ {ts_code} 已从 Redis unprocessed 移除")
    
    # =====================================================
    # 数据采集
    # =====================================================
    
    def fetch_moneyflow(self, ts_code, start_date=None, end_date=None):
        """
        获取个股资金流向数据（Tushare）
        
        接口：pro.moneyflow
        
        参数:
            ts_code: TS 代码（如 600000.SH）
            start_date: 开始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）
        
        返回:
            DataFrame with columns:
            - ts_code, trade_date
            - buy_sm_amount, sell_sm_amount（小单）
            - buy_md_amount, sell_md_amount（中单）
            - buy_lg_amount, sell_lg_amount（大单）
            - buy_elg_amount, sell_elg_amount（特大单）
            - net_mf_amount, net_mf_rate（净流入）
        """
        self.logger.info(f"Tushare 获取资金流向：{ts_code}")
        
        # 控制请求频率
        self._control_request_rate()
        
        try:
            # Tushare 接口
            df = self.pro.moneyflow(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )
            
            if df is None or df.empty:
                self.logger.warning(f"Tushare 无资金流向数据：{ts_code}")
                return pd.DataFrame()
            
            # 数据清洗
            df = self._clean_dataframe(df)
            
            self.logger.info(f"Tushare 成功获取 {ts_code} 资金流向：{len(df)} 条")
            return df
            
        except Exception as e:
            self.logger.error(f"Tushare 获取资金流向失败 {ts_code}: {e}")
            return pd.DataFrame()
    
    def _control_request_rate(self):
        """控制请求频率"""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        
        if elapsed < self.min_request_interval:
            sleep_time = self.min_request_interval - elapsed
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
        self.request_count += 1
        
        # 每 10 次请求，暂停一下
        if self.request_count % 10 == 0:
            pause_time = 5.0
            self.logger.info(f"已请求 {self.request_count} 次，暂停 {pause_time} 秒")
            time.sleep(pause_time)
    
    def _clean_dataframe(self, df):
        """
        清洗 DataFrame，将空字符串、'None' 等无效值转换为 None
        """
        for col in df.columns:
            # 将空字符串、'None' 字符串转换为 None
            df[col] = df[col].apply(lambda x: None if (isinstance(x, str) and (x == '' or x == 'None' or x.lower() == 'nan')) or (isinstance(x, float) and pd.isna(x)) else x)
        return df
    
    # =====================================================
    # 批量采集（带 Redis 断点续传）
    # =====================================================
    
    def fetch_moneyflow_batch(self, start_date=None, end_date=None, max_retries=3):
        """
        批量获取资金流向（支持断点续传）
        
        :param start_date: 开始日期（YYYYMMDD），默认获取最近 30 天
        :param end_date: 结束日期（YYYYMMDD），默认今天
        :param max_retries: 最大重试次数
        """
        # 默认获取最近 30 天
        if not end_date:
            end_date = self.now_date.replace('-', '')
        if not start_date:
            # 计算 30 天前的日期
            date_obj = datetime.datetime.now() - datetime.timedelta(days=30)
            start_date = date_obj.strftime('%Y%m%d')
        
        retry_count = 0
        while retry_count <= max_retries:
            stock_codes = self.get_pending_stocks()
            if not stock_codes:
                self.logger.info("✅ 资金流向采集完成" if retry_count == 0 else "✅ 资金流向补采完成")
                return
            
            total = len(stock_codes)
            self.logger.info(f"第 {retry_count + 1} 轮：共 {total} 只股票待处理")
            success_count = 0
            
            for i, ts_code in enumerate(stock_codes, 1):
                try:
                    df = self.fetch_moneyflow(ts_code, start_date, end_date)
                    if not df.empty:
                        # 入库
                        self.mysql_manager.batch_insert_or_update('stock_moneyflow', df, ['ts_code', 'trade_date'])
                        
                        # 更新记录表
                        if 'trade_date' in df.columns:
                            max_date = df['trade_date'].max()
                            if isinstance(max_date, str):
                                max_date = max_date.replace('-', '')
                            self.update_record(ts_code, max_date)
                        
                        success_count += 1
                    
                    # 标记为已处理
                    self.mark_as_processed(ts_code)
                    
                    if i % 50 == 0:
                        self.logger.info(f"已处理 {i}/{total}，成功 {success_count}")
                    
                except Exception as e:
                    self.logger.error(f"处理 {ts_code} 失败：{e}")
            
            self.logger.info(f"本轮完成：成功 {success_count}/{total}")
            
            # 检查是否还有剩余
            remaining = self.get_pending_stocks()
            if not remaining:
                self.logger.info("✅ 资金流向全部采集完成")
                return
            
            retry_count += 1
            if retry_count <= max_retries:
                self.logger.info(f"⚠️ 仍有 {len(remaining)} 只股票未处理，5 秒后重试...")
                time.sleep(5)
        
        self.logger.error("❌ 达到最大重试次数，资金流向采集结束")
    
    def close(self):
        """关闭连接"""
        self.mysql_manager.close()


# =====================================================
# 测试入口
# =====================================================
if __name__ == '__main__':
    # Token 从 TOOLS.md 读取
    TUSHARE_TOKEN = 'db6f63e5ad93cc28f9150c3b7338a6bffe8034db743095ebb3f847ae'
    
    fetcher = TushareMoneyflowFetcher(token=TUSHARE_TOKEN)
    
    print("=" * 80)
    print("测试 Tushare 资金流向采集")
    print("=" * 80)
    
    # 测试单只股票
    print("\n【测试 1】单只股票采集")
    print("-" * 80)
    df = fetcher.fetch_moneyflow('600000.SH', '20260301', '20260317')
    if not df.empty:
        print(f"✅ 成功：{len(df)} 条")
        print(f"   列名：{list(df.columns)[:5]}...")
    else:
        print("⚠️ 无数据")
    
    fetcher.close()
    print("\n测试完成！")

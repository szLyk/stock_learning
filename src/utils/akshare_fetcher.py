# -*- coding: utf-8 -*-
"""
AkShare 数据采集工具
替代东方财富 API，获取资金流向、股东人数、概念板块等数据

优势:
- 完全免费，无需注册
- 无需 Token，安装即用
- 数据源稳定（东方财富、新浪等）
- 维护活跃

数据覆盖:
1. 资金流向 - stock_individual_fund_flow
2. 股东人数 - stock_hold_num
3. 概念板块 - stock_board_concept_name_em
4. 分析师评级 - stock_research_report_em
"""

import datetime
import pandas as pd
import time
import akshare as ak
from logs.logger import LogManager
from src.utils.mysql_tool import MySQLUtil
from src.utils.redis_tool import RedisUtil


class AkShareFetcher:
    """AkShare 数据采集器（支持 Redis 断点续传）"""
    
    def __init__(self):
        self.logger = LogManager.get_logger("akshare_fetcher")
        self.mysql_manager = MySQLUtil()
        self.mysql_manager.connect()
        self.redis_manager = RedisUtil() if RedisUtil else None
        self.now_date = datetime.datetime.now().strftime('%Y-%m-%d')
    
    # =====================================================
    # 资金流向数据
    # =====================================================
    
    def fetch_moneyflow(self, stock_code, start_date=None, end_date=None):
        """
        获取个股资金流向数据（AkShare）
        
        接口：ak.stock_fund_flow_individual
        
        参数:
            stock_code: 股票代码（如 000001）
            start_date: 开始日期
            end_date: 结束日期
        
        返回:
            DataFrame with columns:
            - stock_code, stock_date
            - main_net_in（主力净流入）, sm_net_in（小单）, mm_net_in（中单）, bm_net_in（大单）
            - main_net_in_rate（主力净流入率）, close_price, change_rate, turnover_rate
        """
        self.logger.info(f"AkShare 获取资金流向：{stock_code}")
        
        try:
            # AkShare 接口（库本身可能有 bug，需要捕获列数不匹配错误）
            try:
                df = ak.stock_fund_flow_individual(symbol=stock_code)
            except ValueError as ve:
                # AKShare 库内部列数不匹配错误
                if "Length mismatch" in str(ve):
                    self.logger.warning(f"AkShare 库 bug（列数不匹配）：{stock_code}，跳过")
                    return pd.DataFrame()
                raise
            
            if df.empty:
                self.logger.warning(f"AkShare 无资金流向数据：{stock_code}")
                return pd.DataFrame()
            
            # 重命名列（匹配数据库字段）
            rename_map = {
                '日期': 'stock_date',
                '主力净流入 - 净额': 'main_net_in',
                '小单净流入 - 净额': 'sm_net_in',
                '中单净流入 - 净额': 'mm_net_in',
                '大单净流入 - 净额': 'bm_net_in',
                '主力净流入 - 净占比': 'main_net_in_rate',
                '收盘价': 'close_price',
                '涨跌幅': 'change_rate',
                '换手率': 'turnover_rate',
            }
            
            # 只重命名存在的列
            existing_cols = {k: v for k, v in rename_map.items() if k in df.columns}
            df = df.rename(columns=existing_cols)
            
            # 添加股票代码
            df['stock_code'] = stock_code
            
            # 数据清洗
            if 'stock_date' in df.columns:
                df['stock_date'] = pd.to_datetime(df['stock_date']).dt.date
            
            numeric_cols = ['main_net_in', 'sm_net_in', 'mm_net_in', 'bm_net_in',
                          'main_net_in_rate', 'close_price', 'change_rate', 'turnover_rate']
            
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 选择需要的字段
            result_cols = ['stock_code', 'stock_date', 'main_net_in', 'sm_net_in',
                          'mm_net_in', 'bm_net_in', 'main_net_in_rate',
                          'close_price', 'change_rate', 'turnover_rate']
            
            result_cols = [col for col in result_cols if col in df.columns]
            
            # 日期筛选
            if start_date and 'stock_date' in df.columns:
                df = df[df['stock_date'] >= pd.to_datetime(start_date).date()]
            if end_date and 'stock_date' in df.columns:
                df = df[df['stock_date'] <= pd.to_datetime(end_date).date()]
            
            self.logger.info(f"AkShare 成功获取 {stock_code} 资金流向：{len(df)} 条")
            return df[result_cols] if result_cols else pd.DataFrame()
            
        except Exception as e:
            self.logger.error(f"AkShare 获取资金流向失败 {stock_code}: {e}")
            return pd.DataFrame()
    
    # =====================================================
    # 股东人数数据
    # =====================================================
    
    def fetch_shareholder(self, stock_code):
        """
        获取股东人数数据（AkShare）
        
        接口：ak.stock_shareholder_change_ths
        
        参数:
            stock_code: 股票代码
        
        返回:
            DataFrame with columns:
            - stock_code, stock_name, report_date
            - shareholder_count, shareholder_change
            - avg_hold_per_household, avg_hold_change
            - freehold_shares, freehold_ratio
        """
        self.logger.info(f"AkShare 获取股东人数：{stock_code}")
        
        try:
            # AkShare 接口
            df = ak.stock_shareholder_change_ths(stock=stock_code)
            
            if df.empty:
                self.logger.warning(f"AkShare 无股东人数数据：{stock_code}")
                return pd.DataFrame()
            
            # 重命名列（匹配数据库字段）
            rename_map = {
                '股东日期': 'report_date',
                '股东人数': 'shareholder_count',
                '股东人数增长率': 'shareholder_change',
                '户均持股': 'avg_hold_per_household',
                '户均持股增长率': 'avg_hold_change',
                '流通股本': 'freehold_shares',
                '流通股本比例': 'freehold_ratio',
            }
            
            # 只重命名存在的列
            existing_cols = {k: v for k, v in rename_map.items() if k in df.columns}
            df = df.rename(columns=existing_cols)
            
            # 添加股票代码
            df['stock_code'] = stock_code
            
            # 数据清洗
            df['report_date'] = pd.to_datetime(df['report_date']).dt.date
            
            numeric_cols = ['shareholder_count', 'shareholder_change',
                          'avg_hold_per_household', 'avg_hold_change',
                          'freehold_shares', 'freehold_ratio']
            
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            result_cols = ['stock_code', 'report_date', 'shareholder_count',
                          'shareholder_change', 'avg_hold_per_household',
                          'avg_hold_change', 'freehold_shares', 'freehold_ratio']
            
            result_cols = [col for col in result_cols if col in df.columns]
            
            self.logger.info(f"AkShare 成功获取 {stock_code} 股东人数：{len(df)} 条")
            return df[result_cols]
            
        except Exception as e:
            self.logger.error(f"AkShare 获取股东人数失败 {stock_code}: {e}")
            return pd.DataFrame()
    
    # =====================================================
    # 概念板块数据
    # =====================================================
    
    def fetch_concept(self, stock_code=None):
        """
        获取概念板块数据（AkShare）
        
        接口：ak.stock_board_concept_name_em
        
        参数:
            stock_code: 股票代码（可选，不传则获取所有概念）
        
        返回:
            DataFrame with columns:
            - stock_code, stock_name, concept_name, concept_type, is_hot
        """
        self.logger.info(f"AkShare 获取概念板块：{stock_code if stock_code else '全部'}")
        
        try:
            if stock_code:
                # 获取个股所属概念
                df = ak.stock_individual_info(stock=stock_code)
                
                if df.empty:
                    return pd.DataFrame()
                
                # 查找概念板块字段
                concept_rows = df[df['item'].str.contains('概念|板块', na=False)]
                
                if concept_rows.empty:
                    self.logger.warning(f"AkShare 无概念板块数据：{stock_code}")
                    return pd.DataFrame()
                
                # 构建 DataFrame
                data = []
                for _, row in concept_rows.iterrows():
                    concepts = str(row['value']).split(',')
                    for concept in concepts:
                        if concept and concept.strip():
                            data.append({
                                'stock_code': stock_code,
                                'concept_name': concept.strip(),
                                'concept_type': '主题',
                                'is_hot': 0,
                            })
                
                df = pd.DataFrame(data)
                
            else:
                # 获取所有概念板块
                df = ak.stock_board_concept_name_em()
                
                if df.empty:
                    return pd.DataFrame()
            
            self.logger.info(f"AkShare 成功获取概念板块：{len(df)} 个")
            return df
            
        except Exception as e:
            self.logger.error(f"AkShare 获取概念板块失败：{e}")
            return pd.DataFrame()
    
    # =====================================================
    # 分析师评级数据
    # =====================================================
    
    def fetch_analyst_rating(self, stock_code, start_date=None, end_date=None):
        """
        获取分析师评级数据（AkShare）
        
        接口：ak.stock_research_report_em
        
        参数:
            stock_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
        
        返回:
            DataFrame with columns:
            - stock_code, stock_name, publish_date
            - institution_name, analyst_name, rating_type, rating_score, target_price
        """
        self.logger.info(f"AkShare 获取分析师评级：{stock_code}")
        
        try:
            # AkShare 接口（个股研报）
            df = ak.stock_research_report_em(symbol=stock_code)
            
            if df.empty:
                self.logger.warning(f"AkShare 无分析师评级数据：{stock_code}")
                return pd.DataFrame()
            
            # 重命名列（AKShare 接口列名可能变化）
            rename_map = {
                '日期': 'publish_date',
                '报告日期': 'publish_date',
                '机构': 'institution_name',
                '机构名称': 'institution_name',
                '分析师': 'analyst_name',
                '东财评级': 'rating_type',
                '评级': 'rating_type',
                '目标价': 'target_price',
            }
            
            existing_cols = {k: v for k, v in rename_map.items() if k in df.columns}
            df = df.rename(columns=existing_cols)
            
            # 添加股票代码
            if 'stock_code' not in df.columns and '股票代码' in df.columns:
                df['stock_code'] = df['股票代码'].astype(str).str.zfill(6)
            else:
                df['stock_code'] = stock_code
            
            # 数据清洗
            if 'publish_date' in df.columns:
                df['publish_date'] = pd.to_datetime(df['publish_date']).dt.date
            
            # 评级打分映射
            rating_map = {'买入': 5.0, '增持': 4.0, '中性': 3.0, '减持': 2.0, '卖出': 1.0}
            if 'rating_type' in df.columns:
                df['rating_score'] = df['rating_type'].map(rating_map).fillna(3.0)
            
            numeric_cols = ['target_price', 'rating_score']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            result_cols = ['stock_code', 'publish_date', 'institution_name',
                          'analyst_name', 'rating_type', 'rating_score', 'target_price']
            
            result_cols = [col for col in result_cols if col in df.columns]
            
            # 日期筛选
            if start_date:
                df = df[df['publish_date'] >= pd.to_datetime(start_date).date()]
            if end_date:
                df = df[df['publish_date'] <= pd.to_datetime(end_date).date()]
            
            self.logger.info(f"AkShare 成功获取 {stock_code} 分析师评级：{len(df)} 条")
            return df[result_cols]
            
        except Exception as e:
            self.logger.error(f"AkShare 获取分析师评级失败 {stock_code}: {e}")
            return pd.DataFrame()
    
    # =====================================================
    # Redis 断点续传机制（参考 Baostock）
    # =====================================================
    
    def get_pending_stocks(self, data_type='moneyflow', date=None):
        """
        从 Redis 或数据库获取待采集股票（支持断点续传）
        :param data_type: 数据类型 (moneyflow/shareholder/concept/analyst)
        :param date: 日期字符串（YYYY-MM-DD），None 表示使用当前日期
        """
        if self.redis_manager is None:
            return self._get_pending_stocks_from_db(data_type)
        
        # 使用传入的日期或当前日期
        target_date = date if date else self.now_date
        
        # Redis key 格式：{update_type}:stock_data:{date}:unprocessed
        # update_type = akshare:{data_type}
        update_type = f"akshare:{data_type}"
        
        # 1. 优先从 Redis 获取待处理股票（剩余的）
        pending = self.redis_manager.get_unprocessed_stocks(target_date, update_type)
        
        if pending:
            # Redis 中有待处理股票，直接返回（断点续传）
            self.logger.info(f"📌 从 Redis 获取 {len(pending)} 只待处理股票（断点续传）")
            self.logger.debug(f"Redis key: {update_type}:stock_data:{target_date}:unprocessed")
            return pending
        
        # 2. Redis 为空，从数据库获取并初始化（首次执行）
        stock_list = self._get_pending_stocks_from_db(data_type)
        if stock_list and len(stock_list) > 0:
            self.redis_manager.add_unprocessed_stocks(stock_list, target_date, update_type)
            self.logger.info(f"✅ Redis 初始化完成：{len(stock_list)}只股票（首次执行）")
            self.logger.debug(f"Redis key: {update_type}:stock_data:{target_date}:unprocessed")
            
            # 重新从 Redis 获取（确保初始化成功）
            pending_after_init = self.redis_manager.get_unprocessed_stocks(target_date, update_type)
            self.logger.info(f"验证：Redis 初始化后有 {len(pending_after_init)} 只股票")
            
            return stock_list
        
        # 3. 数据库也为空
        self.logger.info("⚠️ 未找到待采集股票")
        return None
    
    def _get_pending_stocks_from_db(self, data_type):
        """从数据库获取待采集股票（30 天内未更新的）"""
        date_column_map = {
            'moneyflow': 'update_moneyflow',
            'shareholder': 'update_shareholder',
            'concept': 'update_concept',
            'analyst': 'update_analyst'
        }
        
        date_column = date_column_map.get(data_type, 'update_moneyflow')
        
        # 获取 30 天内未更新的股票
        sql = f"""
        SELECT a.stock_code, b.stock_name, a.market_type 
        FROM update_eastmoney_record a
        LEFT JOIN stock_basic b ON a.stock_code = b.stock_code
        WHERE ({date_column} IS NULL OR {date_column} < DATE_SUB(CURDATE(), INTERVAL 30 DAY))
          AND b.stock_status = 1
        """
        
        result = self.mysql_manager.query_all(sql)
        if not result:
            # 如果是新表，从 stock_basic 获取所有股票
            sql = "SELECT stock_code, stock_name, market_type FROM stock_basic WHERE stock_status = 1"
            result = self.mysql_manager.query_all(sql)
        
        if not result:
            return []
        
        df = pd.DataFrame(result)
        df['stock_code'] = df['stock_code']  # 不需要加前缀，AKShare 直接用纯代码
        return df['stock_code'].tolist()
    
    def update_record(self, stock_code, data_type, update_date):
        """更新采集记录表"""
        date_column_map = {
            'moneyflow': 'update_moneyflow',
            'shareholder': 'update_shareholder',
            'concept': 'update_concept',
            'analyst': 'update_analyst'
        }
        
        date_column = date_column_map.get(data_type)
        if not date_column:
            return
        
        sql = f"""
        INSERT INTO update_eastmoney_record (stock_code, {date_column})
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE {date_column} = VALUES({date_column})
        """
        self.mysql_manager.execute(sql, (stock_code, update_date))
    
    def mark_as_processed(self, stock_code, data_type):
        """标记股票为已处理（从 Redis unprocessed 集合中移除）"""
        if self.redis_manager is None:
            return
        
        # Redis key 格式：{update_type}:stock_data:{date}:unprocessed
        # update_type = akshare:{data_type}
        update_type = f"akshare:{data_type}"
        self.redis_manager.remove_unprocessed_stocks([stock_code], self.now_date, update_type)
        self.logger.debug(f"✅ {stock_code} 已从 Redis unprocessed 移除（类型：{data_type}）")
    
    # =====================================================
    # 批量采集（带 Redis 断点续传）
    # =====================================================
    
    def fetch_moneyflow_batch(self, stock_codes=None, max_retries=3):
        """
        批量获取资金流向（支持断点续传）
        
        :param stock_codes: 股票代码列表，None 表示自动从 Redis/数据库获取
        :param max_retries: 最大重试次数，默认 3 次
        """
        retry_count = 0
        while retry_count <= max_retries:
            # 如果没有传入股票列表，自动获取
            if stock_codes is None:
                stock_codes = self.get_pending_stocks('moneyflow')
            
            if not stock_codes:
                self.logger.info("✅ 资金流向采集完成" if retry_count == 0 else "✅ 资金流向补采完成")
                return
            
            total = len(stock_codes)
            self.logger.info(f"第 {retry_count + 1} 轮：共 {total} 只股票待处理")
            success_count = 0
            
            for i, stock_code in enumerate(stock_codes, 1):
                try:
                    df = self.fetch_moneyflow(stock_code)
                    if not df.empty:
                        self.mysql_manager.batch_insert_or_update('stock_capital_flow', df, ['stock_code', 'stock_date'])
                        if 'stock_date' in df.columns:
                            self.update_record(stock_code, 'moneyflow', df['stock_date'].max())
                        success_count += 1
                    self.mark_as_processed(stock_code, 'moneyflow')
                    
                    if i % 50 == 0:
                        self.logger.info(f"已处理 {i}/{total}，成功 {success_count}")
                    if i % 10 == 0:
                        time.sleep(1)
                except Exception as e:
                    self.logger.error(f"处理 {stock_code} 失败：{e}")
            
            self.logger.info(f"本轮完成：成功 {success_count}/{total}")
            
            # 检查是否还有剩余
            remaining = self.get_pending_stocks('moneyflow')
            if not remaining:
                self.logger.info("✅ 资金流向全部采集完成")
                return
            
            retry_count += 1
            if retry_count <= max_retries:
                self.logger.info(f"⚠️ 仍有 {len(remaining)} 只股票未处理，5 秒后重试...")
                time.sleep(5)
        
        self.logger.error("❌ 达到最大重试次数，资金流向采集结束")
    
    def fetch_shareholder_batch(self, stock_codes=None, max_retries=3):
        """
        批量获取股东人数（支持断点续传）
        
        :param stock_codes: 股票代码列表，None 表示自动从 Redis/数据库获取
        :param max_retries: 最大重试次数，默认 3 次
        """
        retry_count = 0
        while retry_count <= max_retries:
            # 如果没有传入股票列表，自动获取
            if stock_codes is None:
                stock_codes = self.get_pending_stocks('shareholder')
            
            if not stock_codes:
                self.logger.info("✅ 股东人数采集完成" if retry_count == 0 else "✅ 股东人数补采完成")
                return
            
            total = len(stock_codes)
            self.logger.info(f"第 {retry_count + 1} 轮：共 {total} 只股票待处理")
            success_count = 0
            
            for i, stock_code in enumerate(stock_codes, 1):
                try:
                    df = self.fetch_shareholder(stock_code)
                    if not df.empty:
                        self.mysql_manager.batch_insert_or_update('stock_shareholder_info', df, ['stock_code', 'report_date'])
                        if 'report_date' in df.columns:
                            self.update_record(stock_code, 'shareholder', df['report_date'].max())
                        success_count += 1
                    self.mark_as_processed(stock_code, 'shareholder')
                    
                    if i % 50 == 0:
                        self.logger.info(f"已处理 {i}/{total}，成功 {success_count}")
                    if i % 10 == 0:
                        time.sleep(1)
                except Exception as e:
                    self.logger.error(f"处理 {stock_code} 失败：{e}")
            
            self.logger.info(f"本轮完成：成功 {success_count}/{total}")
            
            remaining = self.get_pending_stocks('shareholder')
            if not remaining:
                self.logger.info("✅ 股东人数全部采集完成")
                return
            
            retry_count += 1
            if retry_count <= max_retries:
                self.logger.info(f"⚠️ 仍有 {len(remaining)} 只股票未处理，5 秒后重试...")
                time.sleep(5)
        
        self.logger.error("❌ 达到最大重试次数，股东人数采集结束")
    
    def fetch_concept_batch(self, stock_codes=None, max_retries=3):
        """
        批量获取概念板块（支持断点续传）
        
        :param stock_codes: 股票代码列表，None 表示自动从 Redis/数据库获取
        :param max_retries: 最大重试次数，默认 3 次
        """
        retry_count = 0
        while retry_count <= max_retries:
            # 如果没有传入股票列表，自动获取
            if stock_codes is None:
                stock_codes = self.get_pending_stocks('concept')
            
            if not stock_codes:
                self.logger.info("✅ 概念板块采集完成" if retry_count == 0 else "✅ 概念板块补采完成")
                return
            
            total = len(stock_codes)
            self.logger.info(f"第 {retry_count + 1} 轮：共 {total} 只股票待处理")
            success_count = 0
            
            for i, stock_code in enumerate(stock_codes, 1):
                try:
                    df = self.fetch_concept(stock_code)
                    if not df.empty:
                        self.mysql_manager.batch_insert_or_update('stock_concept', df, ['stock_code', 'concept_name'])
                        self.update_record(stock_code, 'concept', self.now_date)
                        success_count += 1
                    self.mark_as_processed(stock_code, 'concept')
                    
                    if i % 50 == 0:
                        self.logger.info(f"已处理 {i}/{total}，成功 {success_count}")
                    if i % 10 == 0:
                        time.sleep(1)
                except Exception as e:
                    self.logger.error(f"处理 {stock_code} 失败：{e}")
            
            self.logger.info(f"本轮完成：成功 {success_count}/{total}")
            
            remaining = self.get_pending_stocks('concept')
            if not remaining:
                self.logger.info("✅ 概念板块全部采集完成")
                return
            
            retry_count += 1
            if retry_count <= max_retries:
                self.logger.info(f"⚠️ 仍有 {len(remaining)} 只股票未处理，5 秒后重试...")
                time.sleep(5)
        
        self.logger.error("❌ 达到最大重试次数，概念板块采集结束")
    
    def fetch_analyst_batch(self, stock_codes=None, max_retries=3):
        """
        批量获取分析师评级（支持断点续传）
        
        :param stock_codes: 股票代码列表，None 表示自动从 Redis/数据库获取
        :param max_retries: 最大重试次数，默认 3 次
        """
        retry_count = 0
        while retry_count <= max_retries:
            # 如果没有传入股票列表，自动获取
            if stock_codes is None:
                stock_codes = self.get_pending_stocks('analyst')
            
            if not stock_codes:
                self.logger.info("✅ 分析师评级采集完成" if retry_count == 0 else "✅ 分析师评级补采完成")
                return
            
            total = len(stock_codes)
            self.logger.info(f"第 {retry_count + 1} 轮：共 {total} 只股票待处理")
            success_count = 0
            
            for i, stock_code in enumerate(stock_codes, 1):
                try:
                    df = self.fetch_analyst_rating(stock_code)
                    if not df.empty:
                        self.mysql_manager.batch_insert_or_update('stock_analyst_expectation', df, ['stock_code', 'publish_date'])
                        if 'publish_date' in df.columns:
                            self.update_record(stock_code, 'analyst', df['publish_date'].max())
                        success_count += 1
                    self.mark_as_processed(stock_code, 'analyst')
                    
                    if i % 50 == 0:
                        self.logger.info(f"已处理 {i}/{total}，成功 {success_count}")
                    if i % 10 == 0:
                        time.sleep(1)
                except Exception as e:
                    self.logger.error(f"处理 {stock_code} 失败：{e}")
            
            self.logger.info(f"本轮完成：成功 {success_count}/{total}")
            
            remaining = self.get_pending_stocks('analyst')
            if not remaining:
                self.logger.info("✅ 分析师评级全部采集完成")
                return
            
            retry_count += 1
            if retry_count <= max_retries:
                self.logger.info(f"⚠️ 仍有 {len(remaining)} 只股票未处理，5 秒后重试...")
                time.sleep(5)
        
        self.logger.error("❌ 达到最大重试次数，分析师评级采集结束")
    
    def close(self):
        """关闭连接"""
        self.mysql_manager.close()


# =====================================================
# 测试入口
# =====================================================
if __name__ == '__main__':
    fetcher = AkShareFetcher()
    
    print("=" * 80)
    print("测试 1: AkShare 获取资金流向")
    print("=" * 80)
    df = fetcher.fetch_moneyflow('000001')
    if not df.empty:
        print(f"✅ 成功！{len(df)} 条数据")
        print(df[['stock_code', 'stock_date', 'main_net_in', 'close_price']].head(3))
    else:
        print("❌ 无数据")
    
    print("\n" + "=" * 80)
    print("测试 2: AkShare 获取股东人数")
    print("=" * 80)
    df = fetcher.fetch_shareholder('000001')
    if not df.empty:
        print(f"✅ 成功！{len(df)} 条数据")
        print(df.head(3))
    else:
        print("❌ 无数据")
    
    print("\n" + "=" * 80)
    print("测试 3: AkShare 获取概念板块")
    print("=" * 80)
    df = fetcher.fetch_concept('000001')
    if not df.empty:
        print(f"✅ 成功！{len(df)} 个概念")
        print(df['concept_name'].tolist()[:5])
    else:
        print("❌ 无数据")
    
    print("\n" + "=" * 80)
    print("测试 4: AkShare 获取分析师评级")
    print("=" * 80)
    df = fetcher.fetch_analyst_rating('000001')
    if not df.empty:
        print(f"✅ 成功！{len(df)} 条")
        print(df[['stock_code', 'publish_date', 'institution_name', 'rating_type']].head(3))
    else:
        print("❌ 无数据")
    
    fetcher.close()
    print("\n测试完成！")

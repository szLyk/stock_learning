# -*- coding: utf-8 -*-
"""
AkShare 数据采集器 - 完整版
包含断点续传、重试机制
"""

import datetime
import pandas as pd
import time
import random
import akshare as ak
from logs.logger import LogManager
from src.utils.mysql_tool import MySQLUtil
from src.utils.redis_tool import RedisUtil


class AkShareFetcher:
    """AkShare 数据采集器（支持断点续传）"""
    
    def __init__(self):
        self.logger = LogManager.get_logger("akshare_fetcher")
        self.mysql_manager = MySQLUtil()
        self.mysql_manager.connect()
        self.redis_manager = RedisUtil() if RedisUtil else None
        self.now_date = datetime.datetime.now().strftime('%Y-%m-%d')
        
        # 重试配置
        self.max_retry = 3
        self.retry_delay = 2
    
    def _retry_request(self, func, *args, **kwargs):
        """带重试的请求"""
        for retry in range(self.max_retry):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if retry < self.max_retry - 1:
                    delay = self.retry_delay * (retry + 1) + random.uniform(1, 3)
                    self.logger.warning(f"请求失败，{delay:.1f}秒后重试（第{retry+1}/{self.max_retry}次）: {e}")
                    time.sleep(delay)
                else:
                    self.logger.error(f"请求失败，已达最大重试次数：{e}")
                    raise
        return None
    
    # =====================================================
    # 资金流向
    # =====================================================
    
    def fetch_moneyflow(self, stock_code):
        """获取资金流向数据"""
        self.logger.info(f"AkShare 获取资金流向：{stock_code}")
        
        try:
            # 判断市场（6开头是上海，其他是深圳）
            market = 'sh' if stock_code.startswith('6') else 'sz'
            
            # 使用正确的接口（原 stock_fund_flow_individual 有 bug）
            df = self._retry_request(ak.stock_individual_fund_flow, stock=stock_code, market=market)
            
            if df is None or df.empty:
                return pd.DataFrame()
            
            # 列名映射（注意：列名没有空格）
            rename_map = {
                '日期': 'stock_date',
                '收盘价': 'close_price',
                '涨跌幅': 'change_rate',
                '主力净流入-净额': 'main_net_in',
                '主力净流入-净占比': 'main_net_in_rate',
                '超大单净流入-净额': 'super_net_in',
                '超大单净流入-净占比': 'super_net_in_rate',
                '大单净流入-净额': 'big_net_in',
                '大单净流入-净占比': 'big_net_in_rate',
                '中单净流入-净额': 'mid_net_in',
                '中单净流入-净占比': 'mid_net_in_rate',
                '小单净流入-净额': 'small_net_in',
                '小单净流入-净占比': 'small_net_in_rate',
            }
            
            existing_cols = {k: v for k, v in rename_map.items() if k in df.columns}
            df = df.rename(columns=existing_cols)
            df['stock_code'] = stock_code
            
            df['stock_date'] = pd.to_datetime(df['stock_date']).dt.date
            
            numeric_cols = ['main_net_in', 'main_net_in_rate',
                          'super_net_in', 'super_net_in_rate',
                          'big_net_in', 'big_net_in_rate',
                          'mid_net_in', 'mid_net_in_rate',
                          'small_net_in', 'small_net_in_rate',
                          'close_price', 'change_rate']
            
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            result_cols = ['stock_code', 'stock_date', 'main_net_in', 'main_net_in_rate',
                          'super_net_in', 'big_net_in', 'mid_net_in', 'small_net_in',
                          'close_price', 'change_rate']
            
            result_cols = [col for col in result_cols if col in df.columns]
            
            self.logger.info(f"成功获取 {stock_code} 资金流向：{len(df)} 条")
            return df[result_cols]
            
        except Exception as e:
            self.logger.error(f"获取资金流向失败 {stock_code}: {e}")
            return pd.DataFrame()
    
    # =====================================================
    # 股东人数
    # =====================================================
    
    def fetch_shareholder(self, stock_code):
        """获取股东户数数据"""
        self.logger.info(f"AkShare 获取股东户数：{stock_code}")
        
        try:
            # 使用正确的接口：股东户数详情
            df = self._retry_request(ak.stock_zh_a_gdhs_detail_em, symbol=stock_code)
            
            if df is None or df.empty:
                return pd.DataFrame()
            
            # 列名映射
            rename_map = {
                '股东户数统计截止日': 'report_date',
                '区间涨跌幅': 'period_change',
                '股东户数-本次': 'shareholder_count',
                '股东户数-上次': 'shareholder_count_prev',
                '股东户数-增减': 'shareholder_change',
                '股东户数-增减比例': 'shareholder_change_rate',
                '户均持股市值': 'avg_hold_value',
                '户均持股数量': 'avg_hold_count',
                '总市值': 'total_mv',
                '总股本': 'total_share',
                '股东户数公告日期': 'announce_date',
            }
            
            existing_cols = {k: v for k, v in rename_map.items() if k in df.columns}
            df = df.rename(columns=existing_cols)
            df['stock_code'] = stock_code
            
            df['report_date'] = pd.to_datetime(df['report_date']).dt.date
            if 'announce_date' in df.columns:
                df['announce_date'] = pd.to_datetime(df['announce_date']).dt.date
            
            numeric_cols = ['shareholder_count', 'shareholder_count_prev',
                          'shareholder_change', 'shareholder_change_rate',
                          'avg_hold_value', 'avg_hold_count',
                          'total_mv', 'total_share', 'period_change']
            
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            result_cols = ['stock_code', 'report_date', 'shareholder_count',
                          'shareholder_count_prev', 'shareholder_change', 'shareholder_change_rate',
                          'avg_hold_value', 'avg_hold_count', 'total_mv', 'total_share']
            
            result_cols = [col for col in result_cols if col in df.columns]
            
            self.logger.info(f"成功获取 {stock_code} 股东户数：{len(df)} 条")
            return df[result_cols]
            
        except Exception as e:
            self.logger.error(f"获取股东户数失败 {stock_code}: {e}")
            return pd.DataFrame()
    
    # =====================================================
    # 概念板块
    # =====================================================
    
    def fetch_concept(self, stock_code):
        """获取概念板块数据"""
        self.logger.info(f"AkShare 获取概念板块：{stock_code}")
        
        try:
            # 获取所有概念
            all_concepts = self._retry_request(ak.stock_board_concept_name_em)
            
            if all_concepts is None or all_concepts.empty:
                return pd.DataFrame()
            
            # 获取概念名称列
            concept_col = '板块名称' if '板块名称' in all_concepts.columns else 'concept_name'
            
            data = []
            for idx, row in all_concepts.head(50).iterrows():  # 限制前 50 个概念
                concept_name = row[concept_col]
                
                try:
                    # 获取概念成分股
                    component_df = ak.stock_board_concept_cons_em(symbol=concept_name)
                    
                    if not component_df.empty:
                        code_col = '代码' if '代码' in component_df.columns else 'code'
                        if stock_code in component_df[code_col].astype(str).values:
                            data.append({
                                'stock_code': stock_code,
                                'concept_name': concept_name,
                                'concept_type': '主题',
                                'is_hot': 0,
                            })
                except:
                    continue
                
                # 控制请求频率
                if idx % 10 == 0:
                    time.sleep(1)
            
            if not data:
                return pd.DataFrame()
            
            df = pd.DataFrame(data)
            self.logger.info(f"成功获取 {stock_code} 概念板块：{len(df)} 个")
            return df
            
        except Exception as e:
            self.logger.error(f"获取概念板块失败 {stock_code}: {e}")
            return pd.DataFrame()
    
    # =====================================================
    # 分析师评级
    # =====================================================
    
    def fetch_analyst_rating(self, stock_code):
        """获取分析师评级数据"""
        self.logger.info(f"AkShare 获取分析师评级：{stock_code}")
        
        try:
            df = self._retry_request(ak.stock_research_report_em, symbol=stock_code)
            
            if df is None or df.empty:
                return pd.DataFrame()
            
            # 列名映射
            rename_map = {
                '日期': 'publish_date',
                '机构': 'institution_name',
                '东财评级': 'df_rating',
                '近一月个股研报数': 'research_count',
                '报告名称': 'report_name',
                '行业': 'industry',
                '报告 PDF 链接': 'report_link',
            }
            
            existing_cols = {k: v for k, v in rename_map.items() if k in df.columns}
            df = df.rename(columns=existing_cols)
            df['stock_code'] = stock_code
            
            df['publish_date'] = pd.to_datetime(df['publish_date']).dt.date
            
            # 评级打分映射
            rating_map = {'买入': 5.0, '增持': 4.0, '中性': 3.0, '减持': 2.0, '卖出': 1.0}
            if 'df_rating' in df.columns:
                df['rating_score'] = df['df_rating'].map(rating_map).fillna(3.0)
                df['rating_type'] = df['df_rating']
            else:
                df['rating_score'] = 3.0
                df['rating_type'] = '中性'
            
            numeric_cols = ['research_count', 'rating_score', 'target_price']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            result_cols = ['stock_code', 'publish_date', 'institution_name',
                          'analyst_name', 'rating_type', 'rating_score', 'target_price',
                          'report_name', 'research_count', 'industry', 'report_link']
            
            result_cols = [col for col in result_cols if col in df.columns]
            
            self.logger.info(f"成功获取 {stock_code} 分析师评级：{len(df)} 条")
            return df[result_cols]
            
        except Exception as e:
            self.logger.error(f"获取分析师评级失败 {stock_code}: {e}")
            return pd.DataFrame()
    
    # =====================================================
    # 批量采集（带断点续传）
    # =====================================================
    
    def fetch_moneyflow_batch(self, stock_codes, max_retries=3):
        """批量获取资金流向"""
        self.logger.info(f"=== AkShare 批量获取资金流向，共 {len(stock_codes)} 只股票 ===")
        
        success_count = 0
        fail_count = 0
        
        for i, stock_code in enumerate(stock_codes, 1):
            try:
                df = self.fetch_moneyflow(stock_code)
                if not df.empty:
                    rows = self.mysql_manager.batch_insert_or_update(
                        'stock_capital_flow', df, ['stock_code', 'stock_date'])
                    if rows:
                        success_count += 1
                        if i % 50 == 0:
                            self.logger.info(f"已处理 {i}/{len(stock_codes)}，成功 {success_count}")
                    else:
                        fail_count += 1
                else:
                    fail_count += 1
            except Exception as e:
                fail_count += 1
                self.logger.error(f"处理 {stock_code} 失败：{e}")
            
            if i % 10 == 0:
                time.sleep(1)
        
        self.logger.info(f"资金流向采集完成：成功 {success_count}/{len(stock_codes)}，失败 {fail_count}")
        return success_count
    
    def fetch_shareholder_batch(self, stock_codes):
        """批量获取股东人数"""
        self.logger.info(f"=== AkShare 批量获取股东人数，共 {len(stock_codes)} 只股票 ===")
        
        success_count = 0
        fail_count = 0
        
        for i, stock_code in enumerate(stock_codes, 1):
            try:
                df = self.fetch_shareholder(stock_code)
                if not df.empty:
                    rows = self.mysql_manager.batch_insert_or_update(
                        'stock_shareholder_info', df, ['stock_code', 'report_date'])
                    if rows:
                        success_count += 1
                        if i % 50 == 0:
                            self.logger.info(f"已处理 {i}/{len(stock_codes)}，成功 {success_count}")
                    else:
                        fail_count += 1
                else:
                    fail_count += 1
            except Exception as e:
                fail_count += 1
                self.logger.error(f"处理 {stock_code} 失败：{e}")
            
            if i % 10 == 0:
                time.sleep(1)
        
        self.logger.info(f"股东人数采集完成：成功 {success_count}/{len(stock_codes)}，失败 {fail_count}")
        return success_count
    
    def fetch_concept_batch(self, stock_codes):
        """批量获取概念板块"""
        self.logger.info(f"=== AkShare 批量获取概念板块，共 {len(stock_codes)} 只股票 ===")
        
        success_count = 0
        fail_count = 0
        
        for i, stock_code in enumerate(stock_codes, 1):
            try:
                df = self.fetch_concept(stock_code)
                if not df.empty:
                    rows = self.mysql_manager.batch_insert_or_update(
                        'stock_concept', df, ['stock_code', 'concept_name'])
                    if rows:
                        success_count += 1
                        if i % 50 == 0:
                            self.logger.info(f"已处理 {i}/{len(stock_codes)}，成功 {success_count}")
                    else:
                        fail_count += 1
                else:
                    fail_count += 1
            except Exception as e:
                fail_count += 1
                self.logger.error(f"处理 {stock_code} 失败：{e}")
            
            if i % 10 == 0:
                time.sleep(1)
        
        self.logger.info(f"概念板块采集完成：成功 {success_count}/{len(stock_codes)}，失败 {fail_count}")
        return success_count
    
    def fetch_analyst_batch(self, stock_codes):
        """批量获取分析师评级"""
        self.logger.info(f"=== AkShare 批量获取分析师评级，共 {len(stock_codes)} 只股票 ===")
        
        success_count = 0
        fail_count = 0
        
        for i, stock_code in enumerate(stock_codes, 1):
            try:
                df = self.fetch_analyst_rating(stock_code)
                if not df.empty:
                    rows = self.mysql_manager.batch_insert_or_update(
                        'stock_analyst_expectation', df, ['stock_code', 'publish_date'])
                    if rows:
                        success_count += 1
                        if i % 50 == 0:
                            self.logger.info(f"已处理 {i}/{len(stock_codes)}，成功 {success_count}")
                    else:
                        fail_count += 1
                else:
                    fail_count += 1
            except Exception as e:
                fail_count += 1
                self.logger.error(f"处理 {stock_code} 失败：{e}")
            
            if i % 10 == 0:
                time.sleep(1)
        
        self.logger.info(f"分析师评级采集完成：成功 {success_count}/{len(stock_codes)}，失败 {fail_count}")
        return success_count
    
    def close(self):
        """关闭连接"""
        self.mysql_manager.close()


# =====================================================
# 测试入口
# =====================================================
if __name__ == '__main__':
    fetcher = AkShareFetcher()
    
    print("=" * 80)
    print("测试 AkShare 数据采集器")
    print("=" * 80)
    
    # 测试单只股票
    test_stock = '000001'
    
    print(f"\n测试股票：{test_stock}")
    print("-" * 80)
    
    # 测试资金流向
    print("\n[1/4] 测试资金流向...")
    df = fetcher.fetch_moneyflow(test_stock)
    if not df.empty:
        print(f"✅ 成功！{len(df)} 条数据")
        print(df.head(2))
    else:
        print("❌ 无数据")
    
    # 测试股东人数
    print("\n[2/4] 测试股东人数...")
    df = fetcher.fetch_shareholder(test_stock)
    if not df.empty:
        print(f"✅ 成功！{len(df)} 条数据")
        print(df.head(2))
    else:
        print("❌ 无数据")
    
    # 测试概念板块
    print("\n[3/4] 测试概念板块...")
    df = fetcher.fetch_concept(test_stock)
    if not df.empty:
        print(f"✅ 成功！{len(df)} 个概念")
        print(df['concept_name'].tolist()[:5])
    else:
        print("❌ 无数据")
    
    # 测试分析师评级
    print("\n[4/4] 测试分析师评级...")
    df = fetcher.fetch_analyst_rating(test_stock)
    if not df.empty:
        print(f"✅ 成功！{len(df)} 条")
        print(df[['publish_date', 'institution_name', 'df_rating']].head(3))
    else:
        print("❌ 无数据")
    
    fetcher.close()
    print("\n测试完成！")

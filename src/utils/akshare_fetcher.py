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


class AkShareFetcher:
    """AkShare 数据采集器"""
    
    def __init__(self):
        self.logger = LogManager.get_logger("akshare_fetcher")
        self.mysql_manager = MySQLUtil()
        self.mysql_manager.connect()
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
            # AkShare 接口
            df = ak.stock_fund_flow_individual(symbol=stock_code)
            
            if df.empty:
                self.logger.warning(f"AkShare 无资金流向数据：{stock_code}")
                return pd.DataFrame()
            
            # 重命名列（匹配数据库字段）
            rename_map = {
                '日期': 'stock_date',
                '主力净流入-净额': 'main_net_in',
                '小单净流入-净额': 'sm_net_in',
                '中单净流入-净额': 'mm_net_in',
                '大单净流入-净额': 'bm_net_in',
                '主力净流入-净占比': 'main_net_in_rate',
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
            if start_date:
                df = df[df['stock_date'] >= pd.to_datetime(start_date).date()]
            if end_date:
                df = df[df['stock_date'] <= pd.to_datetime(end_date).date()]
            
            self.logger.info(f"AkShare 成功获取 {stock_code} 资金流向：{len(df)} 条")
            return df[result_cols]
            
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
            
            # 重命名列
            rename_map = {
                '报告日期': 'publish_date',
                '机构名称': 'institution_name',
                '分析师': 'analyst_name',
                '评级': 'rating_type',
                '目标价': 'target_price',
            }
            
            existing_cols = {k: v for k, v in rename_map.items() if k in df.columns}
            df = df.rename(columns=existing_cols)
            
            # 添加股票代码
            df['stock_code'] = stock_code
            
            # 数据清洗
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
    # 批量采集
    # =====================================================
    
    def fetch_moneyflow_batch(self, stock_codes):
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
            
            # 每 10 只股票暂停
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

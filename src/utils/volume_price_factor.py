# -*- coding: utf-8 -*-
"""
量价因子计算工具
功能：基于成交量和价格计算量价因子，替代资金流向因子

数据源：Baostock（免费）
因子逻辑：成交量放大 + 价格上涨 = 主力买入

因子公式：
  量价因子 = 成交量比率 × 价格变化
  成交量比率 = 当前成交量 / 20 日平均成交量
  价格变化 = (今日收盘价 - 昨日收盘价) / 昨日收盘价
"""

import datetime
import pandas as pd
import numpy as np
from logs.logger import LogManager
from src.utils.mysql_tool import MySQLUtil
from src.utils.baosock_tool import BaostockFetcher


class VolumePriceFactor:
    """量价因子计算器"""
    
    def __init__(self):
        self.logger = LogManager.get_logger("volume_price_factor")
        self.mysql_manager = MySQLUtil()
        self.mysql_manager.connect()
        self.baostock = BaostockFetcher()
        self.now_date = datetime.datetime.now().strftime('%Y-%m-%d')
    
    # =====================================================
    # 量价因子计算
    # =====================================================
    
    def calculate_volume_ratio(self, stock_code, window=20):
        """
        计算成交量比率
        :param stock_code: 股票代码（纯代码，如 600000）
        :param window: 均量窗口
        :return: 成交量比率
        """
        try:
            # 添加市场前缀
            if stock_code.startswith('6'):
                ts_code = f'sh.{stock_code}'
            else:
                ts_code = f'sz.{stock_code}'
            
            # 获取日线数据
            daily_type = self.baostock.get_daily_type('d')
            df = self.baostock.fetch_daily_data(
                daily_type=daily_type,
                stock_code=ts_code,
                start_date=(datetime.datetime.now() - datetime.timedelta(days=window*2)).strftime('%Y-%m-%d'),
                end_date=self.now_date
            )
            
            if df is None or df.empty:
                return None
            
            # 计算成交量均值
            df['volume_ma'] = df['volume'].rolling(window=window).mean()
            
            # 成交量比率
            df['volume_ratio'] = df['volume'] / df['volume_ma']
            
            # 返回最新值
            latest_ratio = df['volume_ratio'].iloc[-1]
            
            if pd.isna(latest_ratio) or latest_ratio == np.inf:
                return 1.0  # 默认值
            
            return latest_ratio
            
        except Exception as e:
            self.logger.error(f"计算成交量比率失败 {stock_code}: {e}")
            return 1.0
    
    def calculate_price_change(self, stock_code, window=1):
        """
        计算价格变化率
        :param stock_code: 股票代码
        :param window: 计算 N 日变化率
        :return: 价格变化率（百分比）
        """
        try:
            # 获取日线数据
            daily_type = self.baostock.get_daily_type('d')
            df = self.baostock.fetch_daily_data(
                daily_type=daily_type,
                stock_code=stock_code,
                start_date=(datetime.datetime.now() - datetime.timedelta(days=30)).strftime('%Y-%m-%d'),
                end_date=self.now_date
            )
            
            if df is None or df.empty:
                return 0.0
            
            # 价格变化率
            df['price_change'] = df['close'].pct_change(periods=window)
            
            # 返回最新值
            latest_change = df['price_change'].iloc[-1]
            
            if pd.isna(latest_change):
                return 0.0
            
            return latest_change * 100  # 转换为百分比
            
        except Exception as e:
            self.logger.error(f"计算价格变化率失败 {stock_code}: {e}")
            return 0.0
    
    def calculate_turnover_rate(self, stock_code):
        """
        计算换手率
        :param stock_code: 股票代码
        :return: 换手率（百分比）
        """
        try:
            # 获取日线数据
            daily_type = self.baostock.get_daily_type('d')
            df = self.baostock.fetch_daily_data(
                daily_type=daily_type,
                stock_code=stock_code,
                start_date=(datetime.datetime.now() - datetime.timedelta(days=30)).strftime('%Y-%m-%d'),
                end_date=self.now_date
            )
            
            if df is None or df.empty:
                return 0.0
            
            # 返回最新换手率
            latest_turnover = df['turn'].iloc[-1]
            
            if pd.isna(latest_turnover):
                return 0.0
            
            return float(latest_turnover)
            
        except Exception as e:
            self.logger.error(f"计算换手率失败 {stock_code}: {e}")
            return 0.0
    
    def calculate_obv(self, stock_code, window=20):
        """
        计算 OBV 能量潮
        :param stock_code: 股票代码
        :param window: 计算 N 日 OBV 变化率
        :return: OBV 变化率
        """
        try:
            # 获取日线数据
            daily_type = self.baostock.get_daily_type('d')
            df = self.baostock.fetch_daily_data(
                daily_type=daily_type,
                stock_code=stock_code,
                start_date=(datetime.datetime.now() - datetime.timedelta(days=60)).strftime('%Y-%m-%d'),
                end_date=self.now_date
            )
            
            if df is None or df.empty:
                return 0.0
            
            # 计算 OBV
            obv = 0
            obv_list = []
            
            for i in range(len(df)):
                if i == 0:
                    obv = df['volume'].iloc[0]
                else:
                    if df['close'].iloc[i] > df['close'].iloc[i-1]:
                        obv += df['volume'].iloc[i]
                    elif df['close'].iloc[i] < df['close'].iloc[i-1]:
                        obv -= df['volume'].iloc[i]
                    # 平盘不计
                obv_list.append(obv)
            
            df['obv'] = obv_list
            
            # OBV 变化率
            df['obv_change'] = df['obv'].pct_change(periods=window)
            
            latest_obv_change = df['obv_change'].iloc[-1]
            
            if pd.isna(latest_obv_change):
                return 0.0
            
            return latest_obv_change * 100  # 转换为百分比
            
        except Exception as e:
            self.logger.error(f"计算 OBV 失败 {stock_code}: {e}")
            return 0.0
    
    def calculate_volume_price_factor(self, stock_code):
        """
        计算量价因子（综合得分）
        
        公式：
        量价因子 = 成交量比率 × 价格变化 × 100
        
        :param stock_code: 股票代码（纯代码）
        :return: 量价因子得分（标准化为 0-100）
        """
        self.logger.info(f"计算量价因子：{stock_code}")
        
        try:
            # 1. 计算成交量比率
            volume_ratio = self.calculate_volume_ratio(stock_code)
            
            # 2. 计算价格变化率
            price_change = self.calculate_price_change(stock_code)
            
            # 3. 计算换手率
            turnover_rate = self.calculate_turnover_rate(stock_code)
            
            # 4. 计算 OBV 变化率
            obv_change = self.calculate_obv(stock_code)
            
            # 5. 综合计算量价因子
            # 基础公式：量价因子 = 成交量比率 × 价格变化
            vp_raw = volume_ratio * price_change
            
            # 加入换手率修正（高换手率放大信号）
            turnover_adjustment = 1 + (turnover_rate / 100) * 0.1
            vp_adjusted = vp_raw * turnover_adjustment
            
            # 加入 OBV 确认（OBV 为正加强信号）
            obv_adjustment = 1 + (obv_change / 100) * 0.1
            vp_final = vp_adjusted * obv_adjustment
            
            # 6. 标准化为 0-100 分
            # 假设正常范围：-10 到 +10，映射到 0-100
            vp_score = 50 + vp_final * 5
            vp_score = max(0, min(100, vp_score))  # 限制在 0-100
            
            self.logger.info(f"{stock_code}: 量价因子={vp_score:.2f} "
                           f"(VR={volume_ratio:.2f}, PC={price_change:.2f}%, "
                           f"TR={turnover_rate:.2f}%, OBV={obv_change:.2f}%)")
            
            return {
                'stock_code': stock_code,
                'volume_price_score': vp_score,
                'volume_ratio': volume_ratio,
                'price_change': price_change,
                'turnover_rate': turnover_rate,
                'obv_change': obv_change,
                'calc_date': self.now_date
            }
            
        except Exception as e:
            self.logger.error(f"计算量价因子失败 {stock_code}: {e}")
            return None
    
    # =====================================================
    # 批量计算
    # =====================================================
    
    def get_stock_list(self):
        """获取股票列表"""
        sql = """
        SELECT stock_code, stock_name 
        FROM stock_basic 
        WHERE stock_status = 1 
        ORDER BY stock_code
        """
        result = self.mysql_manager.query_all(sql)
        if not result:
            return []
        return result
    
    def calculate_batch(self, stock_codes=None):
        """
        批量计算量价因子
        :param stock_codes: 股票代码列表，None 表示全部
        """
        if stock_codes is None:
            stock_list = self.get_stock_list()
            stock_codes = [s['stock_code'] for s in stock_list]
        
        total = len(stock_codes)
        self.logger.info(f"开始批量计算量价因子，共 {total} 只股票")
        
        results = []
        success_count = 0
        
        for i, stock_code in enumerate(stock_codes, 1):
            try:
                result = self.calculate_volume_price_factor(stock_code)
                if result:
                    results.append(result)
                    success_count += 1
                
                if i % 100 == 0:
                    self.logger.info(f"已处理 {i}/{total}，成功 {success_count}")
                
                # 控制频率（Baostock 限制）
                if i % 50 == 0:
                    import time
                    time.sleep(1)
                    
            except Exception as e:
                self.logger.error(f"处理 {stock_code} 失败：{e}")
        
        self.logger.info(f"量价因子计算完成：成功 {success_count}/{total}")
        
        return results
    
    # =====================================================
    # 数据库操作
    # =====================================================
    
    def save_to_db(self, results):
        """
        保存量价因子到数据库
        :param results: 计算结果列表
        """
        if not results:
            return
        
        self.logger.info(f"保存 {len(results)} 条量价因子数据到数据库")
        
        # 转换为 DataFrame
        df = pd.DataFrame(results)
        
        # 批量插入或更新
        try:
            rows = self.mysql_manager.batch_insert_or_update(
                'stock_factor_volume_price',
                df,
                ['stock_code', 'calc_date']
            )
            self.logger.info(f"✅ 成功保存 {rows} 条数据")
        except Exception as e:
            self.logger.error(f"保存数据失败：{e}")
            raise
    
    def close(self):
        """关闭连接"""
        self.mysql_manager.close()
        self.baostock.close()


# =====================================================
# 测试入口
# =====================================================
if __name__ == '__main__':
    analyzer = VolumePriceFactor()
    
    print("=" * 80)
    print("测试量价因子计算")
    print("=" * 80)
    
    # 测试单只股票
    test_stocks = ['600000', '000001', '300750']
    
    for stock in test_stocks:
        print(f"\n【测试】{stock}")
        print("-" * 80)
        result = analyzer.calculate_volume_price_factor(stock)
        if result:
            print(f"  量价因子得分：{result['volume_price_score']:.2f}")
            print(f"  成交量比率：{result['volume_ratio']:.2f}")
            print(f"  价格变化：{result['price_change']:.2f}%")
            print(f"  换手率：{result['turnover_rate']:.2f}%")
            print(f"  OBV 变化：{result['obv_change']:.2f}%")
    
    analyzer.close()
    print("\n测试完成！")

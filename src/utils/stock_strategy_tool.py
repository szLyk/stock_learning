import talib as ta
import numpy as np
import pandas as pd
from mysql_tool import MySQLUtil
from typing import Tuple


def get_stock_data(
        stock_code: str,
        market_type: str
) -> pd.DataFrame:
    """
    从数据库获取股票数据
    """
    with MySQLUtil() as db:
        sql = """
            SELECT 
                stock_date,
                open_price,
                high_price,
                low_price,
                close_price,
                trading_volume
            FROM stock_history_date_price
            WHERE stock_code = %s 
              AND market_type = %s
              AND tradestatus = 1
              AND adjust_flag = 2   -- 确保使用前复权数据
              AND close_price IS NOT NULL
              AND open_price IS NOT NULL
              AND high_price IS NOT NULL
              AND low_price IS NOT NULL
              AND trading_volume IS NOT NULL
            ORDER BY stock_date ASC
        """
        rows = db.query_all(sql, (stock_code, market_type))
        data_df = pd.DataFrame(rows)
        if not rows:
            print(f"⚠️ 未找到 {stock_code} 的有效前复权数据")
            return pd.DataFrame()
        return data_df


# ==================== TA-Lib 技术指标计算函数 ====================
def talib_rsi(prices, period=14):
    """RSI相对强弱指标"""
    return ta.RSI(prices, timeperiod=period)


def talib_macd(prices, fast=12, slow=26, signal=9):
    """MACD指标"""
    return ta.MACD(prices, fastperiod=fast, slowperiod=slow, signalperiod=signal)


def talib_bollinger(prices, period=20, std_dev=2):
    """布林带"""
    return ta.BBANDS(prices, timeperiod=period, nbdevup=std_dev, nbdevdn=std_dev, matype=0)


def talib_kdj(high, low, close, n=9, m1=3, m2=3):
    """KDJ随机指标"""
    k, d = ta.STOCH(high, low, close, fastk_period=n, slowk_period=m1, slowk_matype=0, slowd_period=m2,
                    slowd_matype=0)
    j = 3 * k - 2 * d
    return k, d, j


def talib_cci(high, low, close, period=20):
    """CCI商品通道指数"""
    return ta.CCI(high, low, close, timeperiod=period)


def talib_williams_r(high, low, close, period=14):
    """Williams %R威廉指标"""
    return ta.WILLR(high, low, close, timeperiod=period)


def talib_mfi(high, low, close, volume, period=14):
    """MFI资金流量指标"""
    return ta.MFI(high, low, close, volume, timeperiod=period)


def talib_adx(high, low, close, period=14):
    """ADX平均趋向指数"""
    adx = ta.ADX(high, low, close, timeperiod=period)
    plus_di = ta.PLUS_DI(high, low, close, timeperiod=period)
    minus_di = ta.MINUS_DI(high, low, close, timeperiod=period)
    return adx, plus_di, minus_di


def talib_obv(close, volume):
    """OBV能量潮"""
    return ta.OBV(close, volume)


def talib_sar(high, low, af=0.02, max_af=0.2):
    """SAR抛物线转向指标"""
    return ta.SAR(high, low, acceleration=af, maximum=max_af)


def calculate_top_score(
        open: np.ndarray,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        volume: np.ndarray,
        ma_period: int = 20
) -> Tuple[np.ndarray, dict]:
    """
    计算顶部风险评分（0~100分）
    """
    n = len(close)
    if n < 50:
        return np.zeros(n), {}

    # 初始化组件得分
    components = {
        'rsi_score': np.zeros(n),
        'kdj_score': np.zeros(n),
        'cci_score': np.zeros(n),
        'willr_score': np.zeros(n),
        'macd_div_score': np.zeros(n),
        'macd_vol_score': np.zeros(n),
        'ma_deviation_score': np.zeros(n),
        'upper_shadow_score': np.zeros(n),
        'doji_score': np.zeros(n),
        'boll_score': np.zeros(n),
        'volume_stagnant_score': np.zeros(n),
        'volume_new_high_score': np.zeros(n),
    }

    # ===== 1. 动量超买指标 =====
    rsi6 = ta.RSI(close, timeperiod=6)
    rsi14 = ta.RSI(close, timeperiod=14)
    rsi24 = ta.RSI(close, timeperiod=24)

    # 调整RSI的权重
    components['rsi_score'] = (
            np.where(rsi6 > 80, 10, 0) +
            np.where(rsi14 > 75, 10, 0) +
            np.where(rsi24 > 70, 10, 0)
    )

    k, d = ta.STOCH(high, low, close, fastk_period=9, slowk_period=3, slowd_period=3)
    j = 3 * k - 2 * d
    components['kdj_score'] = np.where(j > 90, 10, 0)

    cci = ta.CCI(high, low, close, timeperiod=14)
    components['cci_score'] = np.where(cci > 150, 10, 0)

    willr = ta.WILLR(high, low, close, timeperiod=14)
    components['willr_score'] = np.where(willr > -10, 5, 0)

    # ===== 2. 趋势衰竭 =====
    macd, macd_signal, macd_hist = ta.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)

    # 顶背离：价格新高但 MACD 柱未新高
    price_new_high = (close == ta.MAX(close, timeperiod=20))
    macd_not_new_high = (macd_hist < ta.MAX(macd_hist, timeperiod=20))
    components['macd_div_score'] = np.where(price_new_high & macd_not_new_high, 20, 0)

    # MACD 柱连续3日缩小
    if n >= 3:
        decreasing = (macd_hist[:-2] > macd_hist[1:-1]) & (macd_hist[1:-1] > macd_hist[2:])
        components['macd_vol_score'][2:] = np.where(decreasing, 10, 0)

    # 均线偏离度
    ma20 = ta.SMA(close, timeperiod=ma_period)
    deviation_pct = (close - ma20) / ma20 * 100
    components['ma_deviation_score'] = np.where(deviation_pct > 15, 10, 0)

    # ===== 3. 价格形态 =====
    body = np.abs(close - open)
    upper_shadow = high - np.maximum(open, close)
    long_upper = (upper_shadow > 2 * body) & (upper_shadow / close > 0.025)
    components['upper_shadow_score'] = np.where(long_upper, 10, 0)

    doji = body / close < 0.005
    components['doji_score'] = np.where(doji, 5, 0)

    boll_upper, _, _ = ta.BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2)
    components['boll_score'] = np.where(close > boll_upper, 10, 0)

    # ===== 4. 成交量 =====
    vol_ma5 = ta.SMA(volume.astype(float), timeperiod=5)
    price_change_pct = (close - open) / open * 100

    # 放量滞涨
    stagnant = (volume > vol_ma5 * 1.5) & (price_change_pct < 2)
    components['volume_stagnant_score'] = np.where(stagnant, 10, 0)

    # 缩量新高
    new_high = price_new_high
    shrinking_vol = volume < vol_ma5 * 0.8
    components['volume_new_high_score'] = np.where(new_high & shrinking_vol, 10, 0)

    # 总分
    total_score = sum(components.values())
    total_score = np.clip(total_score, 0, 100)

    return total_score, components


def get_top_risk_level(score: np.ndarray) -> np.ndarray:
    level = np.zeros_like(score, dtype=int)
    level[(score >= 45) & (score < 65)] = 1  # 黄色警告
    level[(score >= 65) & (score < 85)] = 2  # 橙色强顶
    level[score >= 85] = 3  # 红色极端顶
    return level


def analyze_stock_top_by_code(df: pd.DataFrame, smooth_days: int = 3) -> pd.DataFrame:
    """
    根据股票代码和市场类型，从数据库获取前复权数据并分析顶部风险

    参数:
        df: 包含原始数据的 DataFrame
        smooth_days: 对 top_score 进行移动平均的天数，默认 3 天。设为 1 则不平滑。

    返回:
        包含原始数据 + top_score + risk_level 的 DataFrame
    """
    # 数据类型转换
    numeric_cols = ['open_price', 'high_price', 'low_price', 'close_price', 'trading_volume']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # 去除缺失值
    df = df.dropna(subset=numeric_cols)

    if len(df) < 50:
        print(f"⚠️ 数据不足50天，无法可靠计算顶部评分（当前{len(df)}天）")
        return df

    # 排序并重置索引（确保时间顺序）
    df = df.sort_values('stock_date').reset_index(drop=True)

    # 提取数组
    open_ = df['open_price'].values
    high = df['high_price'].values
    low = df['low_price'].values
    close = df['close_price'].values
    volume = df['trading_volume'].values

    # 计算原始评分
    top_score_raw, _ = calculate_top_score(open_, high, low, close, volume)

    # 平滑处理
    if smooth_days > 1:
        # 使用 rolling mean，前 smooth_days-1 天为 NaN，用原始值填充或保留 NaN
        top_score = pd.Series(top_score_raw).rolling(window=smooth_days, min_periods=1).mean().values
    else:
        top_score = top_score_raw

    # 计算风险等级
    risk_level = get_top_risk_level(top_score)

    # 写回 DataFrame
    df['top_score_raw'] = top_score_raw  # 保留原始分（可选）
    df['top_score'] = top_score
    df['risk_level'] = risk_level

    return df


# 计算指标
def calculate_indicators(df: pd.DataFrame):
    close = df['close_price'].values.astype(np.float64)
    high = df['high_price'].values.astype(np.float64)
    low = df['low_price'].values.astype(np.float64)
    volume = df['trading_volume'].values.astype(np.float64)

    # ==================== 计算所有技术指标 ====================
    # 价格趋势指标
    df['RSI_6'] = talib_rsi(close, 6)
    df['RSI_14'] = talib_rsi(close, 14)
    df['RSI_24'] = talib_rsi(close, 24)

    macd, macd_signal, macd_hist = talib_macd(close)
    df['MACD'] = macd
    df['MACD_Signal'] = macd_signal
    df['MACD_Hist'] = macd_hist

    upper, middle, lower = talib_bollinger(close)
    df['BB_Upper'] = upper
    df['BB_Middle'] = middle
    df['BB_Lower'] = lower

    # KDJ
    k, d, j = talib_kdj(high, low, close)
    df['KDJ_K'] = k
    df['KDJ_D'] = d
    df['KDJ_J'] = j

    # 其他震荡指标
    df['CCI'] = talib_cci(high, low, close)
    df['Williams_R'] = talib_williams_r(high, low, close)
    df['MFI'] = talib_mfi(high, low, close, volume)

    # 趋势指标
    df['ADX'], df['PLUS_DI'], df['MINUS_DI'] = talib_adx(high, low, close)
    df['SAR'] = talib_sar(high, low)

    # 成交量指标
    df['OBV'] = talib_obv(close, volume)
    df['Volume_MA5'] = df['trading_volume'].rolling(5).mean()
    df['Volume_MA20'] = df['trading_volume'].rolling(20).mean()

    # 将trading_volume转换为float类型
    df['trading_volume'] = df['trading_volume'].astype(float)

    # 计算Volume_Ratio
    df['Volume_Ratio'] = df['trading_volume'] / df['Volume_MA20']

    # 均线指标
    df['MA5'] = df['close_price'].rolling(5).mean()
    df['MA10'] = df['close_price'].rolling(10).mean()
    df['MA20'] = df['close_price'].rolling(20).mean()
    df['MA60'] = df['close_price'].rolling(60).mean()

    # 价格变化
    df['Price_Change'] = df['close_price'].pct_change() * 100
    df['Price_Change_5d'] = df['close_price'].pct_change(5) * 100

    print("所有技术指标计算完成")
    print(f"数据列数: {len(df.columns)}")
    return df


# 重新定义完整的买入策略函数
def comprehensive_buy_strategy(df: pd.DataFrame):
    df = calculate_indicators(df)
    """综合买入策略系统 - 基于TA-Lib多指标共振"""

    signals = pd.DataFrame(index=df.index)
    signals['Date'] = df['stock_date']
    signals['Close'] = df['close_price']

    # 策略1: 超跌反弹
    signals['Oversold_RSI'] = df['RSI_14'] < 30
    signals['Oversold_RSI6'] = df['RSI_6'] < 20
    signals['BB_Lower_Touch'] = df['close_price'] < df['BB_Lower'] * 1.02
    signals['Reversal_Bottom'] = (signals['Oversold_RSI'] | signals['Oversold_RSI6']) & \
                                 signals['BB_Lower_Touch']

    # 策略2: 趋势启动
    macd_golden = (df['MACD'] > df['MACD_Signal']) & (df['MACD'].shift(1) <= df['MACD_Signal'].shift(1))
    price_above_ma = df['close_price'] > df['MA5']
    rsi_bounce = (df['RSI_14'] > df['RSI_14'].shift(1)) & (df['RSI_14'].shift(1) < 35)
    signals['Trend_Start'] = macd_golden & price_above_ma & rsi_bounce

    # 策略3: 均线多头排列
    ma_bull = (df['MA5'] > df['MA10']) & (df['MA10'] > df['MA20'])
    ma_cross = (df['MA5'] > df['MA10']) & (df['MA5'].shift(1) <= df['MA10'].shift(1))
    vol_expand = df['Volume_Ratio'] > 1.2
    signals['MA_Bull_Buy'] = ma_bull & ma_cross & vol_expand

    # 策略4: 布林带突破
    bb_break = (df['close_price'] > df['BB_Middle']) & (df['close_price'].shift(1) <= df['BB_Middle'].shift(1))
    signals['BB_Break_Buy'] = bb_break & (df['MACD'] > 0) & (df['Volume_Ratio'] > 1.0)

    # 策略5: KDJ金叉
    kdj_golden = (df['KDJ_K'] > df['KDJ_D']) & (df['KDJ_K'].shift(1) <= df['KDJ_D'].shift(1))
    signals['KDJ_Buy'] = kdj_golden & (df['KDJ_J'] < 80) & (df['KDJ_J'] > 20)

    # 策略6: CCI反弹
    cci_bounce = (df['CCI'] > df['CCI'].shift(1)) & (df['CCI'].shift(1) < -100)
    signals['CCI_Bounce'] = cci_bounce & (df['CCI'] < 0)

    # 策略7: 量价齐升
    price_up = df['close_price'] > df['close_price'].shift(1)
    vol_up = df['Volume_Ratio'] > 1.5
    macd_expand = df['MACD_Hist'] > df['MACD_Hist'].shift(1)
    signals['Vol_Price_Up'] = price_up & vol_up & macd_expand & (df['MACD_Hist'] > 0)

    # 策略8: 威廉反弹
    wr_bounce = (df['Williams_R'] > df['Williams_R'].shift(1)) & (df['Williams_R'].shift(1) < -80)
    signals['WR_Bounce'] = wr_bounce

    # 策略9: 趋势跟踪
    signals['Trend_Follow'] = (df['ADX'] > 25) & (df['PLUS_DI'] > df['MINUS_DI']) & (df['close_price'] > df['MA20'])

    # 策略10: 底背离
    price_low = df['close_price'] <= df['close_price'].rolling(20).min() * 1.02
    rsi_not_low = df['RSI_14'] > df['RSI_14'].rolling(20).min() * 1.1
    signals['Divergence_Buy'] = price_low & rsi_not_low & (df['RSI_14'] < 40)

    # 综合评分
    score = 0
    score += signals['Reversal_Bottom'].astype(int) * 20
    score += signals['Trend_Start'].astype(int) * 25
    score += signals['MA_Bull_Buy'].astype(int) * 20
    score += signals['BB_Break_Buy'].astype(int) * 15
    score += signals['KDJ_Buy'].astype(int) * 15
    score += signals['CCI_Bounce'].astype(int) * 15
    score += signals['Vol_Price_Up'].astype(int) * 20
    score += signals['WR_Bounce'].astype(int) * 10
    score += signals['Trend_Follow'].astype(int) * 15
    score += signals['Divergence_Buy'].astype(int) * 25

    signals['Buy_Score'] = score
    signals['Buy_Signal'] = score >= 30
    signals['Strong_Buy'] = score >= 50
    signals['Extreme_Buy'] = score >= 70

    # 生成描述
    descriptions = []
    for idx, row in signals.iterrows():
        desc = []
        if row['Reversal_Bottom']: desc.append('超跌反弹')
        if row['Trend_Start']: desc.append('趋势启动')
        if row['MA_Bull_Buy']: desc.append('均线多头')
        if row['BB_Break_Buy']: desc.append('布林突破')
        if row['KDJ_Buy']: desc.append('KDJ金叉')
        if row['CCI_Bounce']: desc.append('CCI反弹')
        if row['Vol_Price_Up']: desc.append('量价齐升')
        if row['WR_Bounce']: desc.append('威廉反弹')
        if row['Trend_Follow']: desc.append('趋势跟踪')
        if row['Divergence_Buy']: desc.append('底背离')
        descriptions.append(', '.join(desc) if desc else '-')

    signals['Description'] = descriptions

    return signals


# 4. 买入策略构建
def build_buy_strategy(df):
    """构建综合买入策略"""
    signals = pd.DataFrame(index=df.index)

    # 策略1: 超跌反弹
    signals['Reversal_Bottom'] = ((df['RSI_14'] < 30) | (df['RSI_6'] < 20)) & \
                                 (df['close_price'] < df['BB_Lower'] * 1.02)

    # 策略2: 趋势启动 (MACD金叉)
    macd_golden = (df['MACD'] > df['MACD_Signal']) & (df['MACD'].shift(1) <= df['MACD_Signal'].shift(1))
    signals['Trend_Start'] = macd_golden & (df['close_price'] > df['MA5']) & \
                             (df['RSI_14'] > df['RSI_14'].shift(1)) & (df['RSI_14'].shift(1) < 35)

    # 策略3: 均线多头
    ma_cross = (df['MA5'] > df['MA10']) & (df['MA5'].shift(1) <= df['MA10'].shift(1))
    signals['MA_Bull'] = (df['MA5'] > df['MA10']) & (df['MA10'] > df['MA20']) & ma_cross & \
                         (df['Volume_Ratio'] > 1.2)

    # 策略4: 布林带突破
    bb_break = (df['close_price'] > df['BB_Middle']) & (df['close_price'].shift(1) <= df['BB_Middle'].shift(1))
    signals['BB_Break'] = bb_break & (df['MACD'] > 0) & (df['Volume_Ratio'] > 1.0)

    # 策略5: KDJ金叉
    kdj_golden = (df['KDJ_K'] > df['KDJ_D']) & (df['KDJ_K'].shift(1) <= df['KDJ_D'].shift(1))
    signals['KDJ_Buy'] = kdj_golden & (df['KDJ_J'] < 80) & (df['KDJ_J'] > 20)

    # 策略6: CCI反弹
    signals['CCI_Bounce'] = (df['CCI'] > df['CCI'].shift(1)) & (df['CCI'].shift(1) < -100) & (df['CCI'] < 0)

    # 策略7: 量价齐升
    signals['Vol_Price_Up'] = (df['close_price'] > df['close_price'].shift(1)) & \
                              (df['Volume_Ratio'] > 1.5) & \
                              (df['MACD_Hist'] > df['MACD_Hist'].shift(1)) & \
                              (df['MACD_Hist'] > 0)

    # 策略8: 威廉反弹
    signals['WR_Bounce'] = (df['Williams_R'] > df['Williams_R'].shift(1)) & (df['Williams_R'].shift(1) < -80)

    # 策略9: 底背离
    price_low = df['close_price'] <= df['close_price'].rolling(20).min() * 1.02
    rsi_not_low = df['RSI_14'] > df['RSI_14'].rolling(20).min() * 1.1
    signals['Divergence'] = price_low & rsi_not_low & (df['RSI_14'] < 40)

    # 综合评分
    score = (signals['Reversal_Bottom'].astype(int) * 20 +
             signals['Trend_Start'].astype(int) * 25 +
             signals['MA_Bull'].astype(int) * 20 +
             signals['BB_Break'].astype(int) * 15 +
             signals['KDJ_Buy'].astype(int) * 15 +
             signals['CCI_Bounce'].astype(int) * 15 +
             signals['Vol_Price_Up'].astype(int) * 20 +
             signals['WR_Bounce'].astype(int) * 10 +
             signals['Divergence'].astype(int) * 25)

    signals['Buy_Score'] = score
    signals['Buy_Signal'] = score >= 30
    signals['Strong_Buy'] = score >= 50
    signals['Extreme_Buy'] = score >= 70

    # 描述
    descriptions = []
    for idx, row in signals.iterrows():
        desc = []
        if row['Reversal_Bottom']: desc.append('超跌反弹')
        if row['Trend_Start']: desc.append('趋势启动')
        if row['MA_Bull']: desc.append('均线多头')
        if row['BB_Break']: desc.append('布林突破')
        if row['KDJ_Buy']: desc.append('KDJ金叉')
        if row['CCI_Bounce']: desc.append('CCI反弹')
        if row['Vol_Price_Up']: desc.append('量价齐升')
        if row['WR_Bounce']: desc.append('威廉反弹')
        if row['Divergence']: desc.append('底背离')
        descriptions.append(', '.join(desc) if desc else '-')
    signals['Description'] = descriptions

    return signals


if __name__ == "__main__":
    # 分析中材科技
    df = get_stock_data('002080', 'sz')
    # result_df = analyze_stock_top_by_code(df)
    # 执行策略
    buy_signals = comprehensive_buy_strategy(df)

    # 合并到df
    df['Buy_Score'] = buy_signals['Buy_Score'].values
    df['Buy_Signal'] = buy_signals['Buy_Signal'].values
    df['Strong_Buy'] = buy_signals['Strong_Buy'].values
    df['Extreme_Buy'] = buy_signals['Extreme_Buy'].values
    df['Buy_Desc'] = buy_signals['Description'].values

    print("✅ 买入策略系统构建完成!")
    print(f"数据形状: {df.shape}")
    print(f"数据形状: {df[['stock_date','Buy_Signal','Buy_Score', 'Buy_Desc']].where(df['Buy_Score']>=70).dropna().to_string()}")

    # if not result_df.empty:
    #     # 👇 关键修复：确保 stock_date 是 datetime 类型
    #     result_df['stock_date'] = pd.to_datetime(result_df['stock_date'])
    #
    #     # 打印近期信号
    #     recent_signals = result_df[result_df['top_score'] >= 45].tail(10)
    #     print("近期顶部信号（>=45分）:")
    #     print(recent_signals[['stock_date', 'close_price', 'top_score', 'risk_level']])
    #
    #     # 特别检查 2021-09
    #     sept_2021 = result_df[
    #         (result_df['stock_date'] >= '2021-09-01') &
    #         (result_df['stock_date'] <= '2021-09-30')
    #         ]
    #     if not sept_2021.empty:
    #         print("\n2021年9月详细分析:")
    #         print(sept_2021[['stock_date', 'close_price', 'top_score', 'risk_level']])
    #     else:
    #         print("\n⚠️ 2021年9月无数据或评分 < 45")
    # else:
    #     print("❌ 未获取到有效数据")
    #
    # print(result_df[result_df['risk_level'] == 3].to_string(index=False))

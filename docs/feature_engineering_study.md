# 股票特征工程学习报告

## 一、业界常用的股票特征分类

### 1. 动量/趋势因子（Trend/Momentum Factors）

#### 常用特征
| 特征名称 | 计算方法 | 用途 |
|---------|---------|------|
| **动量因子** | 过去N天累计收益率 | 捕捉价格趋势 |
| **均线偏离** | (价格 - MA)/MA | 超买超卖判断 |
| **价格斜率** | 线性回归斜率 | 趋势强度 |
| **突破信号** | 价格突破N日高点 | 突破形态 |
| **RSI** | 相对强弱指标 | 超买超卖 |
| **MACD** | 指数平滑异同移动平均线 | 趋势方向 |
| **KDJ** | 随机指标 | 短期超买超卖 |

**计算公式示例**：
```python
# 动量因子
momentum_5d = (close[-1] - close[-5]) / close[-5]
momentum_20d = (close[-1] - close[-20]) / close[-20]

# 均线偏离
bias_5 = (close - MA5) / MA5 * 100
bias_20 = (close - MA20) / MA20 * 100

# 价格斜率
from scipy.stats import linregress
slope, _, _, _, _ = linregress(range(20), close[-20:])
```

---

### 2. 波动率因子（Volatility Factors）

#### 常用特征
| 特征名称 | 计算方法 | 用途 |
|---------|---------|------|
| **历史波动率** | 收益率标准差 × √N | 风险水平 |
| **Parkinson波动率** | 高低价波动率 | 极值波动 |
| **ATR** | 真实波动幅度 | 波动强度 |
| **波动率偏斜** | 上行vs下行波动 | 不对称风险 |
| **波动率聚类** | GARCH模型预测 | 波动预测 |

**计算公式示例**：
```python
# 历史波动率
volatility_20d = returns[-20:].std() * np.sqrt(252)

# ATR（Average True Range）
tr = np.maximum(high - low, 
                np.abs(high - pre_close), 
                np.abs(low - pre_close))
atr_14 = tr.rolling(14).mean()

# Parkinson波动率
parkinson_vol = np.sqrt(
    1/(4*n*np.log(2)) * np.sum(np.log(high/low)**2)
) * np.sqrt(252)
```

---

### 3. 流动性因子（Liquidity Factors）

#### 常用特征
| 特征名称 | 计算方法 | 用途 |
|---------|---------|------|
| **换手率** | 成交量/流通股本 | 交易活跃度 |
| **Amihud非流动性** | abs(return)/volume | 价格冲击 |
| **买卖价差** | (ask - bid) / mid | 交易成本 |
| **成交量加权价格** | VWAP | 均衡价格 |
| **量价相关性** | corr(volume, return) | 量价关系 |

**计算公式示例**：
```python
# 换手率
turnover = volume / circulating_shares * 100

# Amihud非流动性指标
amihud = abs(return) / volume

# VWAP
vwap = (close * volume).cumsum() / volume.cumsum()

# 量价相关性
volume_return_corr = volume.rolling(20).corr(return)
```

---

### 4. 估值因子（Valuation Factors）

#### 常用特征
| 特征名称 | 计算方法 | 用途 |
|---------|---------|------|
| **市盈率PE** | 股价/每股收益 | 估值水平 |
| **市净率PB** | 股价/每股净资产 | 估值水平 |
| **市销率PS** | 市值/营收 | 成长股估值 |
| **PEG** | PE/增长率 | 成长性估值 |
| **股息率** | 每股股息/股价 | 分红回报 |
| **EV/EBITDA** | 企业价值/税息折旧前利润 | 整体估值 |

---

### 5. 质量/财务因子（Quality/Fundamental Factors）

#### 常用特征
| 特征名称 | 计算方法 | 用途 |
|---------|---------|------|
| **ROE** | 净利润/净资产 | 盈利能力 |
| **ROA** | 净利润/总资产 | 资产效率 |
| **毛利率** | (营收-成本)/营收 | 盈利质量 |
| **净利率** | 净利润/营收 | 盈利能力 |
| **资产负债率** | 负债/资产 | 财务风险 |
| **现金流质量** | 经营现金流/净利润 | 盈利质量 |
| **营业收入增长率** | (本期-上期)/上期 | 成长性 |

---

### 6. 情绪/另类因子（Sentiment/Alternative Factors）

#### 常用特征
| 特征名称 | 数据来源 | 用途 |
|---------|---------|------|
| **北向资金** | 沪深港通 | 外资动向 |
| **融资融券** | 两融数据 | 杠杆情绪 |
| **主力资金** | 大单净流入 | 机构动向 |
| **分析师评级** | 研报评级 | 专业预期 |
| **新闻情绪** | NLP分析 | 市场情绪 |
| **搜索指数** | 百度/微信指数 | 关注度 |

---

### 7. 技术/形态因子（Technical/Pattern Factors）

#### 常用特征
| 特征名称 | 计算方法 | 用途 |
|---------|---------|------|
| **涨停次数** | 涨幅≥9.5%次数 | 强势特征 |
| **连板数** | 连续涨停天数 | 极端强势 |
| **突破形态** | 突破N日高点 | 技术突破 |
| **回撤幅度** | 最高价回撤 | 风险控制 |
| **波动突破** | ATR突破 | 波动异动 |
| **缺口** | 开盘跳空 | 情绪强度 |

**计算公式示例**：
```python
# 涨停次数
limit_up_count = (return >= 9.5).sum()

# 连板数
consecutive_limit = 0
for r in returns:
    if r >= 9.5:
        consecutive_limit += 1
    else:
        break

# 回撤幅度
drawdown = (cummax - close) / cummax * 100

# 波动突破
atr_breakout = (close - MA_close) / ATR
```

---

## 二、业界主流多因子模型

### 1. Barra模型（摩根斯坦利）

**10大风险因子**：
```
1. 市值因子（Size）
2. Beta因子
3. 动量因子（Momentum）
4. 盈利变动因子（Earnings Yield）
5. 波动率因子（Volatility）
6. 价值因子（Value）
7. 杠杆因子（Leverage）
8. 流动性因子（Liquidity）
9. 成长因子（Growth）
10. 分红因子（Dividend Yield）
```

---

### 2. Fama-French三因子/五因子模型

**三因子模型**：
```
1. 市场因子（Market）
2. 规模因子（SMB - Small Minus Big）
3. 价值因子（HML - High Minus Low）
```

**五因子模型（扩展）**：
```
4. 盈利因子（RMW - Robust Minus Weak）
5. 投资因子（CMA - Conservative Minus Aggressive）
```

---

### 3. A股常用因子分类

**国泰君安因子体系**：
```
技术因子（40+）：
- 动量、反转、波动率、流动性、量价关系等

基本面因子（30+）：
- 估值、盈利、成长、财务质量、现金流等

情绪因子（10+）：
- 北向资金、融资融券、机构持仓等
```

---

## 三、特征工程方法

### 1. 特征构建方法

#### a) 滚动窗口特征
```python
# 移动平均
ma_5 = close.rolling(5).mean()
ma_20 = close.rolling(20).mean()

# 滚动标准差
vol_20 = close.pct_change().rolling(20).std()

# 滚动最大最小值
max_20 = close.rolling(20).max()
min_20 = close.rolling(20).min()

# 滚动相关性
corr_20 = volume.rolling(20).corr(close)
```

#### b) 差分/变化特征
```python
# 价格变化
price_change_1d = close.pct_change(1)
price_change_5d = close.pct_change(5)

# 成交量变化
volume_change = volume.pct_change()

# 换手率变化
turnover_change = turnover.diff()
```

#### c) 比率特征
```python
# 价格/均线
price_ma_ratio = close / ma_20

# 成交量/平均成交量
volume_avg_ratio = volume / volume.rolling(20).mean()

# 高低点比率
high_low_ratio = high / low
```

#### d) 排名/分位特征
```python
# 行业内排名
rank_in_industry = metric.groupby('industry').rank(pct=True)

# 时间序列排名
rank_ts = metric.rolling(20).rank(pct=True)

# 分位数
quantile_25 = metric.rolling(20).quantile(0.25)
quantile_75 = metric.rolling(20).quantile(0.75)
```

---

### 2. 特征变换方法

#### a) 标准化
```python
# Z-score标准化
z_score = (x - x.mean()) / x.std()

# Min-Max标准化
minmax = (x - x.min()) / (x.max() - x.min())
```

#### b) 去极值
```python
# MAD方法
median = x.median()
mad = (x - median).abs().median()
upper = median + 3 * mad
lower = median - 3 * mad
x_winsorized = x.clip(lower, upper)

# 分位数方法
lower = x.quantile(0.025)
upper = x.quantile(0.975)
x_winsorized = x.clip(lower, upper)
```

#### c) 行业中性化
```python
# 行业均值作为基准
industry_mean = x.groupby('industry').transform('mean')
x_neutral = x - industry_mean
```

---

### 3. 特征选择方法

#### a) 统计方法
```python
# 相关性筛选
corr_with_target = features.corrwith(target)
selected = corr_with_target[abs(corr_with_target) > 0.1].index

# 互信息
from sklearn.feature_selection import mutual_info_regression
mi = mutual_info_regression(features, target)
```

#### b) 模型方法
```python
# 特征重要性
from sklearn.ensemble import RandomForestRegressor
model = RandomForestRegressor()
model.fit(features, target)
importance = model.feature_importances_

# LASSO正则化
from sklearn.linear_model import Lasso
model = Lasso(alpha=0.01)
model.fit(features, target)
selected = features.columns[model.coef_ != 0]
```

---

## 四、我们的特征与业界对比

### 对比表

| 维度 | 业界常用特征 | 我们当前使用的特征 | 差距 |
|------|------------|------------------|------|
| **趋势** | 动量、均线偏离、RSI、MACD、KDJ | 成交量放大、换手率放大 | 缺少RSI、KDJ等 |
| **波动** | 历史波动率、ATR、GARCH | 年化波动率 | 缺少ATR、GARCH |
| **流动性** | 换手率、Amihud、VWAP | 平均换手率、换手率放大 | 缺少VWAP、Amihud |
| **估值** | PE、PB、PS、PEG | 无 | 完全缺失 |
| **财务** | ROE、ROA、毛利率 | 无 | 完全缺失 |
| **情绪** | 北向资金、两融、机构 | 涨停频率 | 缺少资金流向 |
| **技术** | 涨停、连板、突破、缺口 | 涨停频率、均线排列 | 缺少连板、缺口 |
| **行业** | 行业轮动、行业动量 | 行业分类、分行业参数 | 缺少行业轮动 |

---

### 我们的优势
1. **主升浪特征**：创新的20天涨幅+换手率放大判断
2. **分行业参数**：基于特征分析的差异化参数
3. **换手率放大**：独特的启动/见顶判断
4. **底部反转**：均线空头+涨停突破识别

### 我们的不足
1. **缺少财务因子**：无PE、PB、ROE等
2. **缺少情绪因子**：无北向资金、两融数据
3. **缺少ATR**：波动率指标单一
4. **缺少VWAP**：成交量分析不够深入

---

## 五、改进建议

### 短期（1周内可完成）
```python
# 1. 添加ATR特征
tr = np.maximum(high - low, 
                np.abs(high - pre_close), 
                np.abs(low - pre_close))
atr_14 = tr.rolling(14).mean()

# 2. 添加RSI特征
delta = close.diff()
gain = delta.where(delta > 0, 0)
loss = (-delta).where(delta < 0, 0)
avg_gain = gain.rolling(14).mean()
avg_loss = loss.rolling(14).mean()
rs = avg_gain / avg_loss
rsi = 100 - (100 / (1 + rs))

# 3. 添加连板特征
consecutive_limit = count_consecutive(returns >= 9.5)

# 4. 添加KDJ特征
low_9 = low.rolling(9).min()
high_9 = high.rolling(9).max()
rsv = (close - low_9) / (high_9 - low_9) * 100
k = rsv.ewm(com=2).mean()
d = k.ewm(com=2).mean()
j = 3 * k - 2 * d
```

### 中期（需要数据支持）
1. **财务因子**：连接财务数据接口
2. **资金流向**：接入北向资金、两融数据
3. **行业轮动**：分析行业动量
4. **VWAP**：分钟数据支持

### 长期（需要基础设施）
1. **另类数据**：新闻情绪、搜索指数
2. **高频因子**：分钟/Tick级别特征
3. **机器学习**：因子组合优化

---

## 六、学习结论

### 核心发现

1. **业界特征数量多**：常用100+特征，我们仅8个核心特征
2. **分类更系统**：7-10个大类，我们集中在趋势/流动性
3. **数据处理严谨**：标准化、去极值、中性化是标配
4. **组合使用**：多因子组合，而非单一指标

### 行动建议

| 优先级 | 行动项 | 预期效果 |
|--------|--------|---------|
| ⭐⭐⭐ | 添加ATR、RSI、KDJ | 技术指标完善 |
| ⭐⭐⭐ | 添加连板、缺口特征 | 强势股识别提升 |
| ⭐⭐ | 添加财务因子 | 基本面维度 |
| ⭐⭐ | 添加资金流向 | 情绪维度 |
| ⭐ | 特征标准化 | 数据质量提升 |

---

**学习完成！关键是要在现有主升浪特征基础上，逐步补充缺失的特征维度。**
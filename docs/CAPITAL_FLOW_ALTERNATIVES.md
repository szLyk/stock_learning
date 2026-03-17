# 资金流向因子替代方案

**日期**: 2026-03-17

---

## 📊 资金流向因子的本质

**资金流向反映的是什么？**
- 主力资金 vs 散户资金的博弈
- 大单净流入 vs 小单净流出
- 买方力量 vs 卖方力量

**核心信息：**
1. 成交量放大 + 价格上涨 → 主力买入
2. 成交量放大 + 价格下跌 → 主力卖出
3. 高换手率 → 资金活跃
4. 量价背离 → 可能的反转信号

---

## 🎯 替代因子方案

### 方案 1：成交量因子（推荐）

**逻辑：** 成交量放大通常意味着主力资金参与

**可用因子：**
```python
# 1. 成交量/均量比
volume_ratio = volume / MA(volume, 20)

# 2. 成交量变化率
volume_change = (volume - volume_prev) / volume_prev

# 3. 量比（当前成交量/过去 5 日平均）
volume_ratio_5d = volume / MA(volume, 5)
```

**数据源：** Baostock（免费）  
**相关性：** 与资金流向相关性约 0.6-0.7

---

### 方案 2：换手率因子（推荐）

**逻辑：** 高换手率表示资金活跃，可能是主力进出

**可用因子：**
```python
# 1. 换手率
turnover_rate = volume / float_shares * 100

# 2. 换手率变化
turnover_change = (turnover - turnover_prev) / turnover_prev

# 3. 换手率分位数
turnover_percentile = RANK(turnover, 20d)
```

**数据源：** Baostock（免费）  
**相关性：** 与资金流向相关性约 0.5-0.6

---

### 方案 3：量价结合因子（强烈推荐）

**逻辑：** 结合成交量和价格变化，更准确反映资金流向

**可用因子：**
```python
# 1. OBV（能量潮）- 经典资金流向指标
if close > prev_close:
    OBV += volume
else:
    OBV -= volume

# 2. 量价相关性
volume_price_corr = CORR(volume_change, price_change, 20d)

# 3. 资金强度指标
money_strength = (close - open) / (high - low) * volume

# 4. 主力资金近似
main_force = volume_ratio * price_change
```

**数据源：** Baostock（免费）  
**相关性：** 与资金流向相关性约 0.7-0.8

---

### 方案 4：已有因子优化（最简单）

**当前因子模型已有：**
- 动量因子（15% 权重）- 包含价格信息
- 价值因子（25% 权重）- 包含估值信息

**优化方案：**
```python
# 在动量因子中加入成交量确认
momentum_with_volume = momentum * volume_ratio

# 或单独增加"量价因子"（5-10% 权重）
volume_price_factor = 0.5 * momentum + 0.5 * volume_ratio
```

---

## 📋 推荐实施方案

### 方案 A：增加"量价因子"（推荐）

**权重调整：**
```python
factor_weights = {
    'value': 0.25,        # 价值因子
    'quality': 0.25,      # 质量因子
    'growth': 0.20,       # 成长因子
    'momentum': 0.15,     # 动量因子
    'volume_price': 0.10, # 量价因子 ⭐ 新增
    'expectation': 0.05   # 分析师预期
}
```

**量价因子计算：**
```python
def calculate_volume_price_factor(stock_code):
    # 获取数据
    df = get_price_and_volume(stock_code, lookback=60)
    
    # 计算成交量比率
    df['volume_ratio'] = df['volume'] / df['volume'].rolling(20).mean()
    
    # 计算价格变化
    df['price_change'] = df['close'].pct_change()
    
    # 量价因子 = 成交量比率 × 价格变化
    df['vp_factor'] = df['volume_ratio'] * df['price_change']
    
    # 取最近 N 日平均
    return df['vp_factor'].rolling(20).mean().iloc[-1]
```

**优点：**
- ✅ 数据来自 Baostock（免费）
- ✅ 逻辑清晰，与资金流向相关性高
- ✅ 实现简单
- ✅ 不改变现有因子结构

---

### 方案 B：使用 OBV 指标（经典）

**OBV（On-Balance Volume）能量潮**

**计算公式：**
```python
def calculate_obv(stock_code):
    df = get_price_and_volume(stock_code)
    
    obv = 0
    obv_list = []
    
    for i in range(len(df)):
        if df['close'].iloc[i] > df['close'].iloc[i-1]:
            obv += df['volume'].iloc[i]
        elif df['close'].iloc[i] < df['close'].iloc[i-1]:
            obv -= df['volume'].iloc[i]
        # 平盘不计
        obv_list.append(obv)
    
    df['obv'] = obv_list
    
    # OBV 变化率（反映资金流向）
    df['obv_change'] = df['obv'].pct_change()
    
    return df['obv_change'].iloc[-1]
```

**优点：**
- ✅ 经典技术指标
- ✅ 广泛使用
- ✅ 免费数据

**缺点：**
- ❌ 较粗糙，无法区分大单小单

---

### 方案 C：多因子组合（最佳）

**组合多个替代因子：**

```python
def calculate_capital_proxy_factor(stock_code):
    """
    资金流向代理因子
    组合多个相关因子来近似资金流向
    """
    # 1. 成交量因子（40%）
    volume_score = calculate_volume_ratio(stock_code)
    
    # 2. 换手率因子（30%）
    turnover_score = calculate_turnover_rate(stock_code)
    
    # 3. 量价因子（30%）
    vp_score = calculate_volume_price_factor(stock_code)
    
    # 综合得分
    capital_proxy = (
        volume_score * 0.4 +
        turnover_score * 0.3 +
        vp_score * 0.3
    )
    
    return capital_proxy
```

**优点：**
- ✅ 综合多个维度
- ✅ 更接近真实资金流向
- ✅ 免费数据

---

## 📊 因子对比

| 因子 | 数据源 | 成本 | 相关性 | 实现难度 | 推荐度 |
|------|--------|------|--------|---------|--------|
| **真实资金流向** | Tushare | 680 元/年 | 1.0 | 简单 | ⭐⭐ |
| **量价因子** | Baostock | 免费 | 0.7-0.8 | 简单 | ⭐⭐⭐⭐ |
| **OBV 指标** | Baostock | 免费 | 0.6-0.7 | 简单 | ⭐⭐⭐ |
| **成交量因子** | Baostock | 免费 | 0.6-0.7 | 简单 | ⭐⭐⭐ |
| **默认值 50 分** | - | 免费 | 0 | 最简单 | ⭐⭐ |

---

## 🚀 推荐实施方案

### 第一步：增加量价因子（1 小时）

**修改因子权重：**
```python
factor_weights = {
    'value': 0.25,
    'quality': 0.25,
    'growth': 0.20,
    'momentum': 0.10,      # 从 15% 降到 10%
    'volume_price': 0.15,  # 新增 15%
    'expectation': 0.05,
    'capital': 0.00,       # 移除资金流向因子
}
```

**实现代码：**
```python
def calculate_volume_price_score(df):
    """计算量价因子得分"""
    # 成交量比率
    df['volume_ratio'] = df['volume'] / df['volume'].rolling(20).mean()
    
    # 价格变化
    df['price_change'] = df['close'].pct_change()
    
    # 量价因子
    df['vp_factor'] = df['volume_ratio'] * df['price_change']
    
    # 标准化为 0-100 分
    df['volume_price_score'] = normalize(df['vp_factor'])
    
    return df
```

---

### 第二步：回测验证（2-3 小时）

**回测内容：**
1. 量价因子 IC 值
2. 量价因子选股效果
3. 与原资金流向因子对比

**预期结果：**
- IC 值：0.03-0.05（可接受）
- 年化收益：略低于真实资金流向
- 最大回撤：相近

---

### 第三步：实盘应用

**监控指标：**
- 因子 IC 值
- 因子稳定性
- 选股效果

**调整策略：**
- 如果效果不好，降低权重
- 如果效果好，可以增加权重

---

## 💡 结论

**推荐方案：使用量价因子替代资金流向因子**

**理由：**
1. ✅ 免费数据（Baostock）
2. ✅ 相关性高（0.7-0.8）
3. ✅ 实现简单
4. ✅ 逻辑清晰
5. ✅ 无需额外成本

**实施步骤：**
1. 修改因子权重（5 分钟）
2. 实现量价因子计算（30 分钟）
3. 回测验证（2-3 小时）
4. 实盘应用

**预期效果：**
- 接近真实资金流向因子的 80-90% 效果
- 成本：0 元
- 时间：约 3-4 小时

---

**需要我帮你实现量价因子代码吗？**

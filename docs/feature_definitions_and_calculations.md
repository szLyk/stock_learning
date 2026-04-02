# 小市值股票特征定义与计算方法

## 一、基础特征

### 1. 年化波动率（Volatility）

**定义**：股票价格在一年内的波动程度，反映风险水平

**计算公式**：
```
波动率 = 日收益率标准差 × √250 × 100

其中：
- 日收益率 = (今日收盘价 - 昨日收盘价) / 昨日收盘价
- √250 = 年化因子（一年约250个交易日）
```

**计算代码**：
```python
returns = df['close_price'].pct_change().dropna()
volatility = returns.std() * np.sqrt(250) * 100
```

**意义**：
- >60%：高波动（科技股常见）
- 40-60%：中等波动
- <40%：低波动（医药股常见）

---

### 2. 平均换手率（Avg Turnover）

**定义**：一定时期内股票转手买卖的频率，反映市场活跃度

**计算公式**：
```
平均换手率 = Σ(每日换手率) / 交易天数
```

**计算代码**：
```python
avg_turnover = df['turn'].mean()  # turn字段来自数据库
```

**意义**：
- >4%：高换手（科技股活跃）
- 2-4%：中等换手
- <2%：低换手（医药股不活跃）

---

### 3. 涨停频率（Limit Up Frequency）

**定义**：一年内出现涨停板的次数

**计算公式**：
```
涨停频率 = 涨停次数 / 分析天数 × 250

其中涨停定义：单日涨幅 ≥ 9.5%
```

**计算代码**：
```python
limit_ups = len(df[df['ups_and_downs'] >= 9.5])
limit_up_frequency = limit_ups / len(df) * 250
```

**意义**：
- >5次/年：高涨停频率
- 2-5次/年：中等频率
- <2次/年：低频率

---

## 二、主升浪特征

### 4. 主升浪识别（Main Wave Identification）

**定义**：股价在短时间内快速上涨的阶段

**识别标准**：
```
1. 20个交易日内涨幅 ≥ 20%
2. 换手率放大倍数 ≥ 1.5倍
   （主升浪期平均换手率 / 蓄势期平均换手率）
```

**计算代码**：
```python
# 计算20天涨幅
df['gain_20d'] = df['close_price'].pct_change(20) * 100

# 蓄势期换手率（前10天）
acc_turnover = df.iloc[start_idx-10:start_idx]['turn'].mean()

# 主升浪期换手率（20天）
wave_turnover = df.iloc[start_idx:start_idx+20]['turn'].mean()

# 换手率放大倍数
turnover_ratio = wave_turnover / acc_turnover

# 主升浪判定
is_main_wave = (gain_20d >= 20) and (turnover_ratio >= 1.5)
```

---

### 5. 主升浪成功率（Main Wave Success Rate）

**定义**：涨停板后形成主升浪的概率

**计算公式**：
```
主升浪成功率 = 主升浪次数 / 涨停次数

意义：每次涨停后，有多少概率会形成主升浪
```

**计算代码**：
```python
main_wave_success_rate = main_wave_count / limit_up_count
```

**行业对比**：
- 科技：2.99（每次涨停平均触发3次主升浪判断）
- 医药：1.83
- 资源：1.59

---

### 6. 主升浪平均涨幅（Avg Wave Gain）

**定义**：主升浪期间的平均涨幅

**计算公式**：
```
主升浪涨幅 = (终点价 - 起点价) / 起点价 × 100%
```

**计算代码**：
```python
start_price = df.iloc[start_idx]['close_price']
end_price = df.iloc[end_idx]['close_price']
gain = (end_price - start_price) / start_price * 100
```

---

### 7. 主升浪持续天数（Wave Days）

**定义**：主升浪从启动到结束的天数

**计算方法**：
```
持续天数 = 终点索引 - 起点索引
```

**行业对比**：
- 科技：平均17.2天
- 医药：平均13.8天
- 资源：平均13.6天

---

### 8. 换手率放大倍数（Turnover Ratio）

**定义**：主升浪期换手率相对于蓄势期的放大程度

**计算公式**：
```
换手率放大倍数 = 主升浪期平均换手率 / 蓄势期平均换手率

其中：
- 蓄势期：主升浪启动前10天
- 主升浪期：主升浪期间（通常20天）
```

**计算代码**：
```python
# 蓄势期换手率
acc_turnover = df.iloc[start_idx-10:start_idx]['turn'].mean()

# 主升浪期换手率
wave_turnover = df.iloc[start_idx:start_idx+20]['turn'].mean()

turnover_ratio = wave_turnover / acc_turnover
```

**意义**：
- ≥2.0x：强烈启动信号
- 1.5-2.0x：中等信号
- <1.5x：无效信号

---

## 三、换手率特征

### 9. 蓄势期换手率（Accumulation Turnover）

**定义**：主升浪启动前的低换手率期

**计算方法**：
```
蓄势期换手率 = 主升浪启动前10天的平均换手率
```

**意义**：
- <3%：正常蓄势
- >3%：蓄势不充分

---

### 10. 最新换手率（Latest Turnover）

**定义**：最近一个交易日的换手率

**计算方法**：
```
最新换手率 = 最近一天的turn字段值
```

**意义**：
- 结合蓄势期换手率，计算放大倍数

---

### 11. 主升浪期平均换手率（Wave Avg Turnover）

**定义**：主升浪期间的平均换手率

**计算方法**：
```
主升浪期均换手率 = 主升浪期间每日换手率之和 / 持续天数
```

---

## 四、特征计算完整代码

```python
def calculate_full_features(self, stock_code, latest_date):
    """计算单只股票的完整特征"""
    
    # 获取250天历史数据
    sql = """
        SELECT 
            stock_date,
            close_price,
            ups_and_downs,
            turn
        FROM stock_history_date_price
        WHERE stock_code = %s
        ORDER BY stock_date DESC
        LIMIT 260
    """
    
    df = pd.DataFrame(self.mysql.query_all(sql, (stock_code,)))
    df = df.iloc[::-1].tail(250)  # 最近250天
    
    # ===== 基础特征 =====
    
    # 1. 年化波动率
    returns = df['close_price'].pct_change().dropna()
    volatility = returns.std() * np.sqrt(250) * 100
    
    # 2. 平均换手率
    avg_turnover = df['turn'].mean()
    
    # 3. 涨停频率
    limit_ups = len(df[df['ups_and_downs'] >= 9.5])
    limit_up_frequency = limit_ups / len(df) * 250
    
    # ===== 主升浪特征 =====
    
    # 识别主升浪
    main_waves = []
    df['gain_20d'] = df['close_price'].pct_change(20) * 100
    
    for i in range(40, len(df)):
        if df.iloc[i]['gain_20d'] >= 20:
            # 蓄势期换手率
            acc_turn = df.iloc[i-30:i-20]['turn'].mean()
            # 主升浪期换手率
            wave_turn = df.iloc[i-20:i]['turn'].mean()
            # 放大倍数
            turnover_ratio = wave_turn / acc_turn if acc_turn > 0 else 0
            
            if turnover_ratio >= 1.5:
                gain = (df.iloc[i]['close_price'] - df.iloc[i-20]['close_price']) / df.iloc[i-20]['close_price'] * 100
                main_waves.append({
                    'gain': gain,
                    'days': 20,
                    'turnover_ratio': turnover_ratio
                })
    
    # 计算主升浪统计
    if main_waves:
        main_wave_count = len(main_waves)
        main_wave_success_rate = main_wave_count / limit_ups
        avg_wave_gain = np.mean([w['gain'] for w in main_waves])
        avg_wave_days = np.mean([w['days'] for w in main_waves])
        avg_wave_turnover_ratio = np.mean([w['turnover_ratio'] for w in main_waves])
    else:
        main_wave_count = 0
        main_wave_success_rate = 0
        avg_wave_gain = 0
        avg_wave_days = 0
        avg_wave_turnover_ratio = 0
    
    return {
        'volatility': round(volatility, 2),
        'avg_turnover': round(avg_turnover, 2),
        'limit_up_frequency': round(limit_up_frequency, 2),
        'main_wave_count': main_wave_count,
        'main_wave_success_rate': round(main_wave_success_rate, 2),
        'avg_wave_gain': round(avg_wave_gain, 2),
        'avg_wave_days': round(avg_wave_days, 1),
        'avg_wave_turnover_ratio': round(avg_wave_turnover_ratio, 2)
    }
```

---

## 五、特征应用示例

### 科技股（如：603929 亚翔集成）
```
波动率: 57.09%  ← 高波动
换手率: 4.10%   ← 高换手
涨停频率: 4.94次/年 ← 活跃
主升浪成功率: 2.99 ← 成功率高
主升浪涨幅: 28.51%  ← 涨幅大
换手率放大: 2.11x   ← 放大明显
```

### 医药股（如：002821 凯莱英）
```
波动率: 39.69%  ← 低波动
换手率: 2.48%   ← 低换手
涨停频率: 2.69次/年 ← 不活跃
主升浪成功率: 1.83 ← 成功率中等
主升浪涨幅: 21.77%  ← 涨幅中等
换手率放大: 2.00x   ← 放大一般
```

---

## 六、特征选择原则

| 特征类型 | 特征名称 | 为什么重要 |
|---------|---------|-----------|
| **风险** | 波动率 | 决定参数激进程度 |
| **活跃度** | 换手率 | 主升浪启动判断基础 |
| **强势** | 涨停频率 | 主升浪成功率分母 |
| **成功率** | 主升浪成功率 | 核心判断指标 |
| **收益** | 主升浪涨幅 | 收益预期 |
| **时间** | 持续天数 | 持仓周期 |
| **信号** | 换手率放大 | 启动/见顶判断 |
# 量价因子数据来源说明

**日期**: 2026-03-17

---

## ✅ 是的！完全基于数据库现有数据

量价因子的所有计算都基于 **Baostock 采集的日线数据**，这些数据已经存储在数据库中。

---

## 📊 数据来源

### 1. 成交量（Volume）

**来源表**: `stock_daily_price`（或其他日线表）

**字段**:
- `trading_volume` - 成交量
- `trading_amount` - 成交额

**用途**:
- 计算成交量比率
- 计算 OBV 能量潮

---

### 2. 价格（Price）

**来源表**: `stock_daily_price`

**字段**:
- `close_price` - 收盘价
- `open_price` - 开盘价
- `high_price` - 最高价
- `low_price` - 最低价

**用途**:
- 计算价格变化率
- 计算 OBV 方向

---

### 3. 换手率（Turnover Rate）

**来源表**: `stock_daily_price`

**字段**:
- `turn` - 换手率（%）

**用途**:
- 换手率修正因子
- 反映资金活跃度

---

## 🔧 计算逻辑

### 量价因子公式

```python
# 1. 成交量比率
volume_ratio = 当前成交量 / 20 日平均成交量

# 2. 价格变化率
price_change = (今日收盘价 - 昨日收盘价) / 昨日收盘价

# 3. 换手率修正
turnover_adjustment = 1 + (换手率 / 100) * 0.1

# 4. OBV 能量潮
if 今日收盘价 > 昨日收盘价:
    OBV += 今日成交量
else:
    OBV -= 今日成交量

obv_adjustment = 1 + (OBV 变化率 / 100) * 0.1

# 5. 综合量价因子
volume_price_factor = volume_ratio * price_change * turnover_adjustment * obv_adjustment

# 6. 标准化为 0-100 分
volume_price_score = 50 + volume_price_factor * 5
volume_price_score = max(0, min(100, volume_price_score))
```

---

## 📋 数据依赖

| 因子组件 | 依赖字段 | 来源表 | 是否已有 |
|---------|---------|--------|---------|
| 成交量比率 | trading_volume | stock_daily_price | ✅ |
| 价格变化 | close_price | stock_daily_price | ✅ |
| 换手率 | turn | stock_daily_price | ✅ |
| OBV | close_price, trading_volume | stock_daily_price | ✅ |

**结论：** 所有数据都已存在于数据库中，无需额外采集！

---

## 🚀 计算流程

```
1. 从数据库读取日线数据
   ↓
2. 计算成交量比率、价格变化、换手率、OBV
   ↓
3. 综合计算量价因子
   ↓
4. 标准化为 0-100 分
   ↓
5. 保存到 stock_factor_volume_price 表
```

---

## 💡 优势

### 1. 无需额外数据源

- ✅ 使用已有的 Baostock 日线数据
- ✅ 不需要购买 Tushare 会员
- ✅ 不需要采集资金流向数据

### 2. 计算简单

- ✅ 纯数学计算
- ✅ 无外部依赖
- ✅ 计算快速

### 3. 数据稳定

- ✅ Baostock 数据稳定
- ✅ 每日更新
- ✅ 历史数据完整

---

## 📊 数据库表关系

```
stock_daily_price (日线表)
  ├── trading_volume  → 成交量比率、OBV
  ├── close_price     → 价格变化、OBV
  └── turn            → 换手率修正
       ↓
       ↓ (计算)
       ↓
stock_factor_volume_price (量价因子表)
  ├── volume_price_score
  ├── volume_ratio
  ├── price_change
  ├── turnover_rate
  └── obv_change
```

---

## 🔍 验证方法

### 检查数据是否存在

```sql
-- 检查日线数据
SELECT stock_code, trading_date, trading_volume, close_price, turn
FROM stock_daily_price
WHERE stock_code = '600000'
ORDER BY trading_date DESC
LIMIT 10;

-- 检查量价因子表
SELECT stock_code, calc_date, volume_price_score, volume_ratio, price_change
FROM stock_factor_volume_price
WHERE calc_date = CURDATE()
ORDER BY volume_price_score DESC
LIMIT 10;
```

---

## ✅ 总结

**量价因子完全基于数据库现有数据计算：**

1. ✅ 成交量 - 来自日线表
2. ✅ 价格 - 来自日线表
3. ✅ 换手率 - 来自日线表
4. ✅ OBV - 由成交价格和成交量计算

**无需额外数据采集，直接计算即可！**

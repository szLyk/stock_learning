# Baostock API 接口完整参考

**文档生成时间:** 2026-03-14  
**Baostock 版本:** 通过 `dir(baostock)` 获取

---

## ⚠️ 重要提示

**本文档列出的接口是 baostock 实际支持的接口。**  
在编写数据采集代码前，**必须**在此文档中确认接口存在。

---

## 📡 基础接口

| 接口 | 说明 | 参数示例 |
|------|------|----------|
| `login()` | 登录 baostock | `lg = bs.login()` |
| `logout()` | 登出 | `bs.logout()` |

---

## 📈 K 线数据接口

### `query_history_k_data_plus()` ⭐ 核心接口
**功能:** 获取历史 K 线数据（日/周/月/分钟线）

```python
rs = bs.query_history_k_data_plus(
    code="sh.601398",
    fields="date,code,open,high,low,close,preclose,volume,amount,adjustflag,turn,pctChg,peTTM,pbMRQ,psTTM,pcfNcfTTM,isST",
    start_date="2025-01-01",
    end_date="2025-12-31",
    frequency="d",      # d=日，w=周，m=月，5/15/30/60=分钟
    adjustflag="3"      # 3=定点复权
)
```

**返回字段:**
- `date`, `code`, `open`, `high`, `low`, `close`, `preclose`
- `volume`, `amount`, `adjustflag`, `turn`, `pctChg`
- `peTTM` (市盈率 TTM), `pbMRQ` (市净率), `psTTM` (市销率)
- `pcfNcfTTM` (市现率), `isST` (是否 ST)

---

## 📊 基本面数据接口

### `query_profit_data()` ⭐
**功能:** 获取利润表数据

```python
rs = bs.query_profit_data(code="sh.601398", year=2025, quarter=1)
```

**返回字段:**
- `code`, `pubDate`, `statDate`
- `roeAvg`, `npMargin`, `gpMargin`
- `netProfit`, `epsTTM`, `mbRevenue`
- `totalShare`, `liqaShare`

### `query_balance_data()` ⭐
**功能:** 获取资产负债表数据

```python
rs = bs.query_balance_data(code="sh.601398", year=2025, quarter=1)
```

**返回字段:**
- `code`, `pubDate`, `statDate`
- `totalAssets`, `totalLiab`
- `totalShare`, `liqaShare`, `totalHldr`

### `query_cash_flow_data()` ⭐
**功能:** 获取现金流量表数据

```python
rs = bs.query_cash_flow_data(code="sh.601398", year=2025, quarter=1)
```

**返回字段:**
- `code`, `pubDate`, `statDate`
- `saleCash`, `operateCF`, `investCash`
- `financeCF`, `cashEquiEnd`, `CFOToNP`

### `query_growth_data()` ⭐
**功能:** 获取成长能力数据

```python
rs = bs.query_growth_data(code="sh.601398", year=2025, quarter=1)
```

**返回字段:**
- `code`, `pubDate`, `statDate`
- `incomeYOY`, `netProfitYOY`
- `netProfitGR`, `operateProfitGR`

### `query_operation_data()` ⭐
**功能:** 获取运营能力数据

```python
rs = bs.query_operation_data(code="sh.601398", year=2025, quarter=1)
```

**返回字段:**
- `code`, `pubDate`, `statDate`
- `turnDays`, `assetTurn`, `currentTurn`
- `invTurn`, `arTurn`

### `query_dupont_data()` ⭐
**功能:** 获取杜邦分析数据

```python
rs = bs.query_dupont_data(code="sh.601398", year=2025, quarter=1)
```

**返回字段:**
- `code`, `pubDate`, `statDate`
- `roe`, `netMargin`, `assetTurn`
- `equityMultiplier`

---

## 📋 业绩预告接口

### `query_forecast_report()` ⭐
**功能:** 获取业绩预告报告

```python
rs = bs.query_forecast_report(code="sh.601398", year=2025)
```

**返回字段:**
- `code`, `pubDate`, `statDate`
- `type` (预告类型), `content` (预告内容)

### `query_performance_express_report()` ⭐
**功能:** 获取业绩快报

```python
rs = bs.query_performance_express_report(code="sh.601398", year=2025)
```

---

## 💰 分红送配接口

### `query_dividend_data()` ⭐
**功能:** 获取分红送配数据

```python
rs = bs.query_dividend_data(code="sh.601398", year=2025)
```

**返回字段:**
- `code`, `dividendAnnYear`, `dividendAnnTime`
- `exDividendDate`, `dividend`, `bonusShares`
- `reservedPerShare`

---

## 🏦 指数成分股接口

### `query_hs300_stocks()` ⭐
**功能:** 获取沪深 300 成分股

```python
rs = bs.query_hs300_stocks(date="2025-03-14")
```

### `query_sz50_stocks()` ⭐
**功能:** 获取上证 50 成分股

```python
rs = bs.query_sz50_stocks(date="2025-03-14")
```

### `query_zz500_stocks()` ⭐
**功能:** 获取中证 500 成分股

```python
rs = bs.query_zz500_stocks(date="2025-03-14")
```

---

## 📜 股票基本信息接口

### `query_stock_basic()` ⭐
**功能:** 获取股票基本信息

```python
rs = bs.query_stock_basic()
```

**返回字段:**
- `code`, `code_name`
- `ipoDate`, `outDate`
- `type` (1=股票，2=指数), `status` (1=上市，0=退市)

### `query_stock_industry()` ⭐
**功能:** 获取股票行业分类

```python
rs = bs.query_stock_industry()
```

**返回字段:**
- `code`, `updateDate`, `code_name`
- `industry`, `industry_classification`

### `query_all_stock()` ⭐
**功能:** 获取所有股票列表

```python
rs = bs.query_all_stock(date="2025-03-14")
```

---

## 📅 交易日历接口

### `query_trade_dates()` ⭐
**功能:** 获取交易日历

```python
rs = bs.query_trade_dates(start_date="2025-01-01", end_date="2025-12-31")
```

**返回字段:**
- `calendar_date`, `is_trading_day`

---

## 📉 复权因子接口

### `query_adjust_factor()` ⭐
**功能:** 获取复权因子

```python
rs = bs.query_adjust_factor(code="sh.601398", start_date="2025-01-01", end_date="2025-12-31")
```

---

## 💹 宏观经济接口

### `query_deposit_rate_data()`
**功能:** 获取存款利率

```python
rs = bs.query_deposit_rate_data()
```

### `query_loan_rate_data()`
**功能:** 获取贷款利率

```python
rs = bs.query_loan_rate_data()
```

### `query_required_reserve_ratio_data()`
**功能:** 获取存款准备金率

```python
rs = bs.query_required_reserve_ratio_data()
```

### `query_money_supply_data_year()`
**功能:** 获取货币供应量（年）

```python
rs = bs.query_money_supply_data_year(year=2025)
```

### `query_money_supply_data_month()`
**功能:** 获取货币供应量（月）

```python
rs = bs.query_money_supply_data_month(month="2025-03")
```

---

## 📊 估值分析接口

### `query_evaluation()` (模块)
**功能:** 估值分析相关

```python
from baostock import evaluation
# 具体接口待查
```

---

## ❌ 不存在的接口（常见误区）

以下接口**不存在**，不要使用：

| 错误接口 | 正确替代 |
|----------|----------|
| `query_money_flow_data()` | ❌ 无替代，需其他数据源 |
| `query_analyst_rating_data()` | ❌ 无替代，需其他数据源 |
| `query_shareholder_data()` | ❌ 无替代，需其他数据源 |
| `query_concept_data()` | ❌ 无替代，需其他数据源 |

---

## ✅ 推荐的数据采集策略

### 1. 日线行情 + 估值
```python
bs.query_history_k_data_plus(
    code="sh.601398",
    fields="date,code,open,high,low,close,preclose,volume,amount,adjustflag,turn,pctChg,peTTM,pbMRQ,psTTM,isST",
    start_date="2025-01-01",
    end_date="2025-12-31",
    frequency="d",
    adjustflag="3"
)
```

### 2. 财务数据（季度）
```python
# 利润表
bs.query_profit_data(code="sh.601398", year=2025, quarter=1)

# 资产负债表
bs.query_balance_data(code="sh.601398", year=2025, quarter=1)

# 现金流量表
bs.query_cash_flow_data(code="sh.601398", year=2025, quarter=1)
```

### 3. 成长 + 运营 + 杜邦
```python
bs.query_growth_data(code="sh.601398", year=2025, quarter=1)
bs.query_operation_data(code="sh.601398", year=2025, quarter=1)
bs.query_dupont_data(code="sh.601398", year=2025, quarter=1)
```

### 4. 业绩预告
```python
bs.query_forecast_report(code="sh.601398", year=2025)
```

---

## 📝 代码开发检查清单

在编写 baostock 数据采集代码前，请确认：

- [ ] 接口名称在本文档中存在
- [ ] 接口参数正确（code 格式、日期格式等）
- [ ] 返回字段名称正确
- [ ] 错误处理完善（`rs.error_code != '0'`）
- [ ] 数据清洗逻辑（空值、类型转换）

---

## 🔗 官方文档

- 官网：http://www.baostock.com
- GitHub: https://github.com/baostock/baostock

---

_最后更新：2026-03-14_

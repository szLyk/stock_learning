# 数据采集脚本使用说明

## 概述

数据采集脚本已重构为**独立任务模式**，每个数据类型都有独立的采集方法，便于单独执行和调试。

## 东方财富数据采集 (`src/utils/eastmoney_tool.py`)

### 支持的采集类型

| 类型 | 说明 | 数据表 |
|------|------|--------|
| `moneyflow` | 资金流向 | `stock_capital_flow` |
| `north` | 北向资金 | `stock_capital_flow` |
| `shareholder` | 股东人数 | `stock_shareholder_info` |
| `concept` | 概念板块 | `stock_concept` |
| `analyst` | 分析师评级 | `stock_analyst_expectation` |

### 使用方式

#### 1. 运行完整采集（所有类型）

```bash
cd /home/fan/.openclaw/workspace/stock_learning
python3 src/utils/eastmoney_tool.py
```

#### 2. 单独采集指定类型

```bash
# 采集资金流向
python3 src/utils/eastmoney_tool.py moneyflow

# 采集北向资金
python3 src/utils/eastmoney_tool.py north

# 采集股东人数
python3 src/utils/eastmoney_tool.py shareholder

# 采集概念板块
python3 src/utils/eastmoney_tool.py concept

# 采集分析师评级
python3 src/utils/eastmoney_tool.py analyst
```

### 独立采集方法

- `fetch_moneyflow_batch(max_retries=5)` - 资金流向批量采集
- `fetch_north_batch(max_retries=5)` - 北向资金批量采集
- `fetch_shareholder_batch(max_retries=5)` - 股东人数批量采集
- `fetch_concept_batch(max_retries=5)` - 概念板块批量采集
- `fetch_analyst_batch(max_retries=5)` - 分析师评级批量采集

---

## Baostock 财务数据采集 (`src/utils/baostock_financial.py`)

### 支持的采集类型

| 类型 | 说明 | 数据表 |
|------|------|--------|
| `profit` | 利润表 | `stock_profit_data` |
| `balance` | 资产负债表 | `stock_balance_data` |
| `cashflow` | 现金流量表 | `stock_cash_flow_data` |
| `growth` | 成长能力 | `stock_growth_data` |
| `operation` | 运营能力 | `stock_operation_data` |
| `dupont` | 杜邦分析 | `stock_dupont_data` |
| `forecast` | 业绩预告 | `stock_forecast_report` |
| `dividend` | 分红送配 | `stock_dividend_data` |

### 使用方式

#### 1. 运行完整采集（所有类型）

```bash
cd /home/fan/.openclaw/workspace/stock_learning
python3 src/utils/baostock_financial.py
```

#### 2. 单独采集指定类型

```bash
# 采集利润表
python3 src/utils/baostock_financial.py profit

# 采集资产负债表
python3 src/utils/baostock_financial.py balance

# 采集现金流量表
python3 src/utils/baostock_financial.py cashflow

# 采集成长能力
python3 src/utils/baostock_financial.py growth

# 采集运营能力
python3 src/utils/baostock_financial.py operation

# 采集杜邦分析
python3 src/utils/baostock_financial.py dupont

# 采集业绩预告
python3 src/utils/baostock_financial.py forecast

# 采集分红送配
python3 src/utils/baostock_financial.py dividend
```

### 独立采集方法

- `fetch_profit_batch(years=None, max_retries=5)` - 利润表批量采集
- `fetch_balance_batch(years=None, max_retries=5)` - 资产负债表批量采集
- `fetch_cashflow_batch(years=None, max_retries=5)` - 现金流量表批量采集
- `fetch_growth_batch(years=None, max_retries=5)` - 成长能力批量采集
- `fetch_operation_batch(years=None, max_retries=5)` - 运营能力批量采集
- `fetch_dupont_batch(years=None, max_retries=5)` - 杜邦分析批量采集
- `fetch_forecast_batch(years=None, max_retries=5)` - 业绩预告批量采集
- `fetch_dividend_batch(years=None, max_retries=5)` - 分红送配批量采集

---

## 特性说明

### ✅ 已移除 LIMIT 限制

所有采集脚本已移除 `LIMIT 500` 限制，会采集**全部**符合条件的股票（A 股约 5000 只）。

### 🔄 断点重试机制

每个采集方法都支持断点重试：
- 自动检测未更新/未采集的股票
- 支持多轮重试（默认 5 轮）
- 每轮失败后等待 5 秒重试
- 使用 Redis 记录处理状态，避免重复采集

### 📊 采集记录表

- 东方财富：`update_eastmoney_record`
- 财务数据：`stock_performance_update_record`

采集记录会自动更新，下次采集时只会获取未更新或超过更新周期的股票。

### ⏱️ 速率控制

- 每 10 次请求休眠 0.3 秒
- 不同类型采集之间休眠 2 秒
- 避免请求过快被 API 封禁

---

## 示例场景

### 场景 1：只更新北向资金数据

```bash
python3 src/utils/eastmoney_tool.py north
```

### 场景 2：只更新最新年度财务数据

```bash
# 修改脚本中的 years 参数或手动指定
python3 src/utils/baostock_financial.py profit
```

### 场景 3：完整数据采集流程

```bash
# 先采集财务数据
python3 src/utils/baostock_financial.py

# 再采集东方财富数据
python3 src/utils/eastmoney_tool.py
```

### 场景 4：在 Python 代码中调用

```python
from src.utils.eastmoney_tool import EastMoneyFetcher

fetcher = EastMoneyFetcher()

# 单独采集北向资金
fetcher.fetch_north_batch(max_retries=3)

# 或运行完整采集
fetcher.run_full_collection()

fetcher.close()
```

---

## 日志输出示例

```
=== 开始采集北向资金 (north) ===
第 1 轮：共 5234 只股票待处理
已处理 50/5234，成功 48
已处理 100/5234，成功 97
...
本轮完成：成功 5200/5234
✅ 北向资金全部采集完成
```

---

## 故障排查

### 问题：采集速度慢

- 检查网络连接
- 调整 `time.sleep()` 参数（不推荐，可能触发 API 限制）

### 问题：部分股票采集失败

- 查看日志中的错误信息
- 可能是股票停牌、数据源问题
- 重试机制会自动处理临时失败

### 问题：重复采集同一只股票

- 检查 Redis 连接
- 检查采集记录表是否正确更新

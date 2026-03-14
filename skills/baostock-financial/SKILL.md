# Baostock 财务数据采集 Skill

**技能名称:** baostock-financial  
**创建时间:** 2026-03-14  
**版本:** v1.0

---

## 📋 技能描述

本技能提供基于 Baostock API 的完整财务数据采集能力，支持利润表、资产负债表、现金流量表、成长能力、运营能力、杜邦分析、业绩预告、分红送配等 8 类财务数据。集成 Redis 断点重试机制，确保数据采集的完整性和可靠性。

---

## 🎯 适用场景

- A 股上市公司财务数据采集
- 多因子模型基本面因子计算
- 财务分析和估值建模
- 业绩预告追踪
- 分红送配研究

---

## 📦 依赖安装

```bash
pip3 install baostock pandas pymysql
```

---

## 📊 数据库表结构

### 1. 财务数据记录表

```sql
CREATE TABLE stock_performance_update_record (
    id INT AUTO_INCREMENT PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    stock_name VARCHAR(50),
    market_type VARCHAR(10),
    
    -- 财务数据更新时间
    update_profit_date DATE,       -- 利润表
    update_balance_date DATE,      -- 资产负债表
    update_cashflow_date DATE,     -- 现金流量表
    update_growth_date DATE,       -- 成长能力
    update_operation_date DATE,    -- 运营能力
    update_dupont_date DATE,       -- 杜邦分析
    
    -- 业绩预告和分红
    update_forecast_date DATE,     -- 业绩预告
    update_dividend_date DATE,     -- 分红送配
    
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_stock (stock_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 2. 目标数据表

| 表名 | 说明 | 更新频率 |
|------|------|----------|
| `stock_profit_data` | 利润表 | 季度 |
| `stock_balance_data` | 资产负债表 | 季度 |
| `stock_cash_flow_data` | 现金流量表 | 季度 |
| `stock_growth_data` | 成长能力 | 季度 |
| `stock_operation_data` | 运营能力 | 季度 |
| `stock_dupont_data` | 杜邦分析 | 季度 |
| `stock_forecast_report` | 业绩预告 | 季度 |
| `stock_dividend_data` | 分红送配 | 年度 |

---

## 🚀 使用方法

### 方式 1：完整采集

```bash
cd /home/fan/.openclaw/workspace/stock_learning
export PYTHONPATH=/home/fan/.openclaw/workspace/stock_learning:$PYTHONPATH

# 运行完整采集（所有财务数据）
python3 src/utils/baostock_financial.py
```

### 方式 2：指定数据类型

```bash
# 只采集利润表
python3 src/utils/baostock_financial.py profit

# 只采集资产负债表
python3 src/utils/baostock_financial.py balance

# 只采集现金流量表
python3 src/utils/baostock_financial.py cashflow

# 只采集成长能力
python3 src/utils/baostock_financial.py growth

# 只采集运营能力
python3 src/utils/baostock_financial.py operation

# 只采集杜邦分析
python3 src/utils/baostock_financial.py dupont

# 只采集业绩预告
python3 src/utils/baostock_financial.py forecast

# 只采集分红送配
python3 src/utils/baostock_financial.py dividend
```

### 方式 3：Python 代码调用

```python
from src.utils.baostock_financial import BaostockFinancialFetcher

fetcher = BaostockFinancialFetcher()

# 1. 单只股票测试
df = fetcher.fetch_profit_data('sh.601398', year=2025)
print(f"获取到 {len(df)} 条利润表数据")

# 2. 批量采集（带 Redis 断点重试）
fetcher.batch_fetch_with_retry('profit', years=[2025, 2024], max_retries=3)

# 3. 完整采集
fetcher.run_full_collection()

fetcher.close()
```

---

## 🔄 Redis 断点重试机制

### 工作原理

1. **任务队列**: 使用 Redis 存储待采集股票列表
   - `baostock:profit` - 利润表待采集
   - `baostock:balance` - 资产负债表待采集
   - `baostock:cashflow` - 现金流量表待采集
   - `baostock:growth` - 成长能力待采集
   - `baostock:operation` - 运营能力待采集
   - `baostock:dupont` - 杜邦分析待采集
   - `baostock:forecast` - 业绩预告待采集
   - `baostock:dividend` - 分红送配待采集

2. **断点续传**: 采集失败后，股票会保留在 Redis 队列中

3. **自动重试**: 程序会自动重试未完成的股票，最多重试 5 次

4. **智能休眠**: 每轮重试之间休眠 5 秒，避免请求过快

### Redis 任务管理

```bash
# 查看待采集股票
redis-cli SMEMBERS baostock:profit

# 添加待采集股票
redis-cli SADD baostock:profit sh.601398 sz.000001

# 清空待采集队列
redis-cli DEL baostock:profit

# 标记为已处理
redis-cli SREM baostock:profit sh.601398
```

---

## 📝 数据采集流程

```
开始
  ↓
登录 Baostock
  ↓
从 Redis/数据库获取待采集股票
  ↓
依次采集 8 类财务数据
  ├─ 利润表 (query_profit_data)
  ├─ 资产负债表 (query_balance_data)
  ├─ 现金流量表 (query_cash_flow_data)
  ├─ 成长能力 (query_growth_data)
  ├─ 运营能力 (query_operation_data)
  ├─ 杜邦分析 (query_dupont_data)
  ├─ 业绩预告 (query_forecast_report)
  └─ 分红送配 (query_dividend_data)
  ↓
保存到数据库
  ↓
更新记录表
  ↓
从 Redis 移除已完成股票
  ↓
检查是否还有剩余
  ├─ 有剩余 → 休眠后重试
  └─ 无剩余 → 完成
  ↓
登出 Baostock
```

---

## 📊 数据字段说明

### 利润表 (stock_profit_data)

| 字段 | 说明 | 单位 |
|------|------|------|
| stock_code | 股票代码 | - |
| publish_date | 发布日期 | - |
| statistic_date | 统计日期 | - |
| roe_avg | 加权 ROE | % |
| np_margin | 净利率 | % |
| gp_margin | 毛利率 | % |
| net_profit | 净利润 | 元 |
| eps_ttm | 每股收益 (TTM) | 元 |
| mb_revenue | 营业总收入 | 元 |
| total_share | 总股本 | 万股 |
| liqa_share | 流通股本 | 万股 |
| season | 季度 (1-4) | - |

### 成长能力 (stock_growth_data)

| 字段 | 说明 |
|------|------|
| incomeYOY | 营业收入同比增长率 |
| netProfitYOY | 净利润同比增长率 |
| netProfitGR | 净利润增长率 |
| operateProfitGR | 营业利润增长率 |

### 运营能力 (stock_operation_data)

| 字段 | 说明 |
|------|------|
| turnDays | 营业周期 |
| assetTurn | 总资产周转率 |
| currentTurn | 流动资产周转率 |
| invTurn | 存货周转率 |
| arTurn | 应收账款周转率 |

---

## ⚠️ 注意事项

### 1. 数据更新频率

| 数据类型 | 更新频率 | 建议采集频率 |
|----------|----------|--------------|
| 利润表 | 季度 | 财报季后 |
| 资产负债表 | 季度 | 财报季后 |
| 现金流量表 | 季度 | 财报季后 |
| 成长能力 | 季度 | 财报季后 |
| 运营能力 | 季度 | 财报季后 |
| 杜邦分析 | 季度 | 财报季后 |
| 业绩预告 | 季度 | 预告披露期 |
| 分红送配 | 年度 | 年报后 |

### 2. 财报披露时间

- **一季报**: 4 月 1 日 - 4 月 30 日
- **中报**: 7 月 1 日 - 8 月 31 日
- **三季报**: 10 月 1 日 - 10 月 31 日
- **年报**: 1 月 1 日 - 4 月 30 日

### 3. 请求频率控制

- 每次采集后休眠 0.2-0.3 秒
- 不同类型之间休眠 2 秒
- 重试轮次之间休眠 5 秒

### 4. 数据验证

采集完成后，建议验证数据完整性：

```sql
-- 检查利润表数据量
SELECT COUNT(*) FROM stock_profit_data 
WHERE YEAR(publish_date) = YEAR(CURDATE());

-- 检查未更新的股票
SELECT stock_code, stock_name, update_profit_date 
FROM stock_performance_update_record 
WHERE update_profit_date < DATE_SUB(CURDATE(), INTERVAL 365 DAY);
```

---

## 🔍 常见问题

### Q1: 部分股票采集不到数据？

**A:** 可能原因：
- 新股上市，财务数据不足
- 停牌股票，未披露财报
- Baostock 数据源临时故障

**解决:** 等待数据更新或手动重试

### Q2: 如何清空重采？

**A:** 
```sql
-- 清空财务数据表
TRUNCATE TABLE stock_profit_data;
TRUNCATE TABLE stock_balance_data;
...

-- 清空记录表
TRUNCATE TABLE stock_performance_update_record;

-- 清空 Redis 队列
redis-cli DEL baostock:profit baostock:balance ...
```

### Q3: 采集速度太慢？

**A:** 
- 减少采集年份（只采集最近 2 年）
- 缩短休眠时间（但可能被封 IP）
- 分批次采集（每天采集一类数据）

---

## 📚 相关文档

- [Baostock API 参考](docs/BAOSTOCK_API_REFERENCE.md)
- [东方财富 API 参考](docs/EASTMONEY_API_REFERENCE.md)
- [多因子模型指南](docs/MULTI_FACTOR_GUIDE.md)

---

## 📝 更新日志

- **2026-03-14** v1.0
  - 初始版本
  - 支持 8 类财务数据
  - 集成 Redis 断点重试
  - 重新设计记录表结构
  - 添加完整文档

---

_技能维护者：小罗 📊_

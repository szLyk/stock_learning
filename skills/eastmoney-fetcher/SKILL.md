# 东方财富数据采集 Skill

**技能名称:** eastmoney-fetcher  
**创建时间:** 2026-03-14  
**版本:** v1.0

---

## 📋 技能描述

本技能提供基于东方财富 API 的免费数据采集能力，支持资金流向、北向资金、股东人数、概念板块、分析师评级等数据。集成 Redis 断点重试机制，确保数据采集的完整性和可靠性。

---

## 🎯 适用场景

- A 股量化策略数据准备
- 资金流向分析
- 北向资金追踪
- 股东筹码分析
- 概念板块选股
- 分析师预期研究

---

## 📦 依赖安装

```bash
pip3 install requests pandas
```

---

## 🔧 配置文件

### 1. 数据库配置（config/mysql_config.py）

```ini
[mysql]
host = 192.168.1.109
port = 3306
user = root
password = 123456
database = stock
charset = utf8mb4
```

### 2. Redis 配置（config/redis_config.py）

```ini
[redis]
host = localhost
port = 6379
db = 0
password =
```

---

## 📊 数据库表结构

### 1. 更新记录表

```sql
CREATE TABLE update_eastmoney_record (
    id INT AUTO_INCREMENT PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    stock_name VARCHAR(50),
    market_type VARCHAR(10),
    update_moneyflow DATE,      -- 资金流向最后更新日期
    update_north DATE,          -- 北向资金最后更新日期
    update_shareholder DATE,    -- 股东人数最后更新日期
    update_concept DATE,        -- 概念板块最后更新日期
    update_analyst DATE,        -- 分析师评级最后更新日期
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_stock (stock_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 2. 目标数据表

| 表名 | 说明 | 更新频率 |
|------|------|----------|
| `stock_capital_flow` | 资金流向表 | 每日 |
| `stock_shareholder_info` | 股东人数表 | 季度 |
| `stock_concept` | 概念板块表 | 每周 |
| `stock_analyst_expectation` | 分析师预期表 | 每日 |

---

## 🚀 使用方法

### 方式 1：完整采集

```bash
cd /home/fan/.openclaw/workspace/stock_learning
export PYTHONPATH=/home/fan/.openclaw/workspace/stock_learning:$PYTHONPATH

# 运行完整采集（所有数据类型）
python3 src/utils/eastmoney_tool.py
```

### 方式 2：指定数据类型

```bash
# 只采集资金流向
python3 src/utils/eastmoney_tool.py moneyflow

# 只采集北向资金
python3 src/utils/eastmoney_tool.py north

# 只采集概念板块
python3 src/utils/eastmoney_tool.py concept

# 只采集股东人数
python3 src/utils/eastmoney_tool.py shareholder

# 只采集分析师评级
python3 src/utils/eastmoney_tool.py analyst
```

### 方式 3：Python 代码调用

```python
from src.utils.eastmoney_tool import EastMoneyFetcher

fetcher = EastMoneyFetcher()

# 1. 单只股票测试
df = fetcher.fetch_moneyflow('601398', start_date='2026-01-01', end_date='2026-03-14')
print(f"获取到 {len(df)} 条资金流向数据")

# 2. 批量采集（带 Redis 断点重试）
fetcher.batch_fetch_with_retry('moneyflow', max_retries=3)

# 3. 完整采集
fetcher.run_full_collection()

fetcher.close()
```

---

## 🔄 Redis 断点重试机制

### 工作原理

1. **任务队列**: 使用 Redis 存储待采集股票列表
   - `eastmoney:moneyflow` - 资金流向待采集
   - `eastmoney:north` - 北向资金待采集
   - `eastmoney:shareholder` - 股东人数待采集
   - `eastmoney:concept` - 概念板块待采集
   - `eastmoney:analyst` - 分析师评级待采集

2. **断点续传**: 采集失败后，股票会保留在 Redis 队列中

3. **自动重试**: 程序会自动重试未完成的股票，最多重试 5 次

4. **智能休眠**: 每轮重试之间休眠 5 秒，避免请求过快

### Redis 任务管理

```bash
# 查看待采集股票
redis-cli SMEMBERS eastmoney:moneyflow

# 添加待采集股票
redis-cli SADD eastmoney:moneyflow 1.601398 0.000001

# 清空待采集队列
redis-cli DEL eastmoney:moneyflow

# 标记为已处理
redis-cli SREM eastmoney:moneyflow 1.601398
```

---

## 📝 数据采集流程

```
开始
  ↓
从 Redis/数据库获取待采集股票
  ↓
依次采集各类型数据
  ├─ 资金流向（日频）
  ├─ 北向资金（日频）
  ├─ 概念板块（实时）
  ├─ 股东人数（季度）
  └─ 分析师评级（实时）
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
```

---

## ⚠️ 注意事项

### 1. 请求频率控制

- 每 10 次请求休眠 0.3 秒
- 不同类型之间休眠 2 秒
- 重试轮次之间休眠 5 秒

### 2. 数据更新频率

| 数据类型 | 更新频率 | 建议采集频率 |
|----------|----------|--------------|
| 资金流向 | T+1 | 每日 15:30 后 |
| 北向资金 | T+1 | 每日 15:30 后 |
| 概念板块 | 不定期 | 每周 1 次 |
| 股东人数 | 季度 | 财报季后 |
| 分析师评级 | 实时 | 每日 |

### 3. 错误处理

```python
try:
    df = fetcher.fetch_moneyflow('601398')
    if df.empty:
        logger.warning("无数据")
except Exception as e:
    logger.error(f"采集失败：{e}")
    # 股票会保留在 Redis 队列中，下次重试
```

### 4. 数据验证

采集完成后，建议验证数据完整性：

```sql
-- 检查资金流向数据量
SELECT COUNT(*) FROM stock_capital_flow 
WHERE stock_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY);

-- 检查未更新的股票
SELECT stock_code, stock_name, update_moneyflow 
FROM update_eastmoney_record 
WHERE update_moneyflow < DATE_SUB(CURDATE(), INTERVAL 7 DAY);
```

---

## 🔍 常见问题

### Q1: 部分股票采集不到数据？

**A:** 可能原因：
- 新股上市，数据不足
- 停牌股票，无交易数据
- 数据源临时故障

**解决:** 等待数据更新或手动重试

### Q2: Redis 连接失败？

**A:** 程序会自动降级到数据库模式，从 `update_eastmoney_record` 表判断待采集股票

### Q3: 采集速度太慢？

**A:** 可以调整以下参数：
- 减少 `max_retries` 次数
- 缩短休眠时间（但可能被封 IP）
- 增加并发（需注意 API 限制）

### Q4: 如何清空重采？

**A:** 
```sql
-- 清空记录表
TRUNCATE TABLE update_eastmoney_record;

-- 清空 Redis 队列
redis-cli DEL eastmoney:moneyflow eastmoney:north eastmoney:concept ...
```

---

## 📚 相关文档

- [东方财富 API 参考](docs/EASTMONEY_API_REFERENCE.md)
- [Baostock API 参考](docs/BAOSTOCK_API_REFERENCE.md)
- [多因子模型指南](docs/MULTI_FACTOR_GUIDE.md)

---

## 📝 更新日志

- **2026-03-14** v1.0
  - 初始版本
  - 支持 5 种数据类型
  - 集成 Redis 断点重试
  - 添加完整文档

---

_技能维护者：小罗 📊_

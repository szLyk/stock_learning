# AKShare 批量处理补充说明

## 📋 更新内容

参考 Baostock 的实现模式，为 `akshare_fetcher.py` 补充了完整的批量处理方法。

---

## 🆕 新增功能

### 1. Redis 断点续传机制

```python
# 获取待采集股票（支持断点续传）
def get_pending_stocks(self, data_type='moneyflow', date=None):
    """
    从 Redis 或数据库获取待采集股票
    - 优先从 Redis 获取剩余股票（断点续传）
    - Redis 为空时从数据库初始化
    """

# 从数据库获取待采集股票
def _get_pending_stocks_from_db(self, data_type):
    """
    获取 30 天内未更新的股票
    或从 stock_basic 获取所有股票
    """

# 标记股票为已处理
def mark_as_processed(self, stock_code, data_type):
    """
    从 Redis unprocessed 集合中移除（表示已处理）
    """
```

### 2. 采集记录表更新

```python
# 更新采集记录
def update_record(self, stock_code, data_type, update_date):
    """
    更新 update_eastmoney_record 表
    记录各类型数据的最后更新日期
    """
```

### 3. 批量采集方法（带重试）

```python
# 资金流向批量采集
def fetch_moneyflow_batch(self, max_retries=3):
    """
    - 自动获取待采集股票
    - 支持断点续传
    - 失败自动重试（最多 3 次）
    - 每 10 只股票暂停 1 秒
    - 每 50 只股票输出进度
    """

# 股东人数批量采集
def fetch_shareholder_batch(self, max_retries=3):
    """同上"""

# 概念板块批量采集
def fetch_concept_batch(self, max_retries=3):
    """同上"""

# 分析师评级批量采集
def fetch_analyst_batch(self, max_retries=3):
    """同上"""
```

---

## 🔄 与 Baostock 对比

| 功能 | Baostock | AKShare（新） |
|------|----------|---------------|
| Redis 断点续传 | ✅ | ✅ |
| 自动获取待采集股票 | ✅ | ✅ |
| 采集记录表更新 | ✅ | ✅ |
| 自动重试机制 | ✅ | ✅ |
| 批量处理 | ✅ | ✅ |
| 频率控制 | ✅ | ✅ |
| 错误日志 | ✅ | ✅ |

---

## 📝 使用方法

### 方法 1：初始化脚本（推荐）

```bash
cd /home/fan/.openclaw/workspace/stock_learning
python3 scripts/init_akshare_data.py
```

### 方法 2：XXL-JOB 定时任务

任务已配置，每天 21:00 自动执行：
- 资金流向数据采集（AKShare）
- 股东人数数据采集（AKShare）
- 概念板块数据采集（AKShare）
- 分析师评级数据采集（AKShare）

### 方法 3：Python 代码调用

```python
from src.utils.akshare_fetcher import AkShareFetcher

fetcher = AkShareFetcher()

# 批量采集资金流向
fetcher.fetch_moneyflow_batch(max_retries=3)

# 批量采集股东人数
fetcher.fetch_shareholder_batch(max_retries=3)

# 批量采集概念板块
fetcher.fetch_concept_batch(max_retries=3)

# 批量采集分析师评级
fetcher.fetch_analyst_batch(max_retries=3)

fetcher.mysql_manager.close()
```

---

## 🎯 Redis Key 格式

```
akshare:{data_type}:stock_data:{date}:unprocessed

示例：
akshare:moneyflow:stock_data:2026-03-17:unprocessed
akshare:shareholder:stock_data:2026-03-17:unprocessed
akshare:concept:stock_data:2026-03-17:unprocessed
akshare:analyst:stock_data:2026-03-17:unprocessed
```

---

## ⚙️ 配置说明

### 频率控制
- 每 10 只股票暂停 1 秒
- 每 50 只股票输出进度日志
- 失败重试间隔 5 秒

### 重试机制
- 默认最大重试 3 次
- 连续失败会记录错误日志
- 达到最大重试次数后停止

### 断点续传
- 中断后再次运行会自动从 Redis 获取剩余股票
- 无需从头开始采集
- Redis key 按日期区分，支持跨天继续

---

## 📊 数据库表

采集记录表：`update_eastmoney_record`

| 字段 | 说明 |
|------|------|
| stock_code | 股票代码 |
| update_moneyflow | 资金流向最后更新日期 |
| update_shareholder | 股东人数最后更新日期 |
| update_concept | 概念板块最后更新日期 |
| update_analyst | 分析师评级最后更新日期 |

---

## ✅ 验证清单

- [x] Redis 集成
- [x] 断点续传逻辑
- [x] 批量采集方法
- [x] 采集记录表更新
- [x] 自动重试机制
- [x] 频率控制
- [x] 错误日志
- [x] XXL-JOB 集成
- [x] 初始化脚本

---

## 🚀 下一步

1. **运行初始化采集**：
   ```bash
   python3 scripts/init_akshare_data.py
   ```

2. **重启 XXL-JOB 执行器**：
   ```bash
   cd xxljob && ./restart.sh
   ```

3. **监控采集进度**：
   ```bash
   tail -f logs/stock_project/akshare_fetcher_error.log
   ```

---

**更新时间**：2026-03-17  
**参考实现**：`src/utils/baostock_extension.py`

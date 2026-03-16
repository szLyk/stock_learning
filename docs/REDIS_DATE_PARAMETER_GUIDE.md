# Redis 断点续传使用指南

**更新日期**: 2026-03-16  
**功能**: 支持跨天继续执行数据采集任务

---

## 🎯 功能说明

`run_full_collection` 方法现在支持传入 `date` 参数，用于指定 Redis key 的日期。

**使用场景**:
- 当天数据采集任务没跑完，第二天可以传入昨天的日期继续跑
- 需要重新执行某一天的采集任务
- 多天任务并行执行（不同日期）

---

## 📝 方法签名

### run_full_collection

```python
def run_full_collection(self, year=None, quarter=None, date=None):
    """
    运行完整的数据采集流程（财务数据 + 业绩预告，支持 Redis 断点续传和历史数据初始化）
    
    :param year: 年份，None 表示根据记录表自动判断
    :param quarter: 季度 (1-4)，None 表示全部季度
    :param date: 日期字符串（YYYY-MM-DD），None 表示使用当前日期
                 用于跨天继续执行（如第二天传入昨天的日期继续跑）
    """
```

### get_pending_stocks

```python
def get_pending_stocks(self, data_type='extension', date=None):
    """
    从 Redis 或数据库获取待采集股票（支持断点续传）
    
    :param data_type: 数据类型，默认 'extension'
    :param date: 日期字符串（YYYY-MM-DD），None 表示使用当前日期
    """
```

### mark_as_processed

```python
def mark_as_processed(self, stock_code, data_type='extension', date=None):
    """
    标记股票为已处理（从 Redis unprocessed 集合中移除）
    
    :param stock_code: 股票代码（带市场前缀，如 sh.600000）
    :param data_type: 数据类型，默认 'extension'
    :param date: 日期字符串（YYYY-MM-DD），None 表示使用当前日期
    """
```

---

## 💡 使用示例

### 场景 1: 正常运行（使用当前日期）

```python
from src.utils.baostock_extension import BaostockExtension

baostockExtension = BaostockExtension()
baostockExtension.run_full_collection()  # 不传 date，默认使用当前日期
baostockExtension.close()
```

**Redis Key**: `baostock:extension:stock_data:2026-03-16:unprocessed`

---

### 场景 2: 跨天继续执行（传入昨天的日期）

```python
from src.utils.baostock_extension import BaostockExtension
import datetime

baostockExtension = BaostockExtension()

# 假设昨天（2026-03-15）的任务没跑完，今天继续跑
yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')

baostockExtension.run_full_collection(date=yesterday)
baostockExtension.close()
```

**Redis Key**: `baostock:extension:stock_data:2026-03-15:unprocessed`

---

### 场景 3: 指定年份 + 指定日期

```python
from src.utils.baostock_extension import BaostockExtension

baostockExtension = BaostockExtension()

# 采集 2025 年数据，使用昨天的 Redis key
baostockExtension.run_full_collection(year=2025, date='2026-03-15')
baostockExtension.close()
```

---

### 场景 4: 手动添加股票到指定日期的 Redis key

```python
from src.utils.baostock_extension import BaostockExtension

baostockExtension = BaostockExtension()

# 添加股票到指定日期的 Redis key
target_date = '2026-03-15'
baostockExtension.redis_manager.add_unprocessed_stocks(
    ['sh.600000', 'sh.600001'], 
    target_date,
    'baostock:extension'
)

# 从指定日期执行
baostockExtension.run_full_collection(date=target_date)
baostockExtension.close()
```

---

### 场景 5: 查看指定日期的待处理股票

```python
from src.utils.baostock_extension import BaostockExtension

baostockExtension = BaostockExtension()

# 获取指定日期的待处理股票
pending = baostockExtension.get_pending_stocks('extension', date='2026-03-15')

print(f"待处理股票数量：{len(pending)}")
print(f"待处理股票列表：{pending[:10]}")  # 显示前 10 只

baostockExtension.close()
```

---

## 📊 Redis Key 说明

### Key 格式

```
baostock:{data_type}:stock_data:{date}:unprocessed
```

**示例**:
- `baostock:extension:stock_data:2026-03-16:unprocessed` - 今天的任务
- `baostock:extension:stock_data:2026-03-15:unprocessed` - 昨天的任务
- `baostock:extension:stock_data:2026-03-14:unprocessed` - 前天的任务

### 查看 Redis 中的任务

```bash
# 连接 Redis
redis-cli

# 查看今天的待处理股票数量
SCARD baostock:extension:stock_data:2026-03-16:unprocessed

# 查看昨天的待处理股票数量
SCARD baostock:extension:stock_data:2026-03-15:unprocessed

# 查看待处理股票列表（前 10 个）
SMEMBERS baostock:extension:stock_data:2026-03-15:unprocessed | head -10

# 删除指定日期的任务（如果需要）
DEL baostock:extension:stock_data:2026-03-15:unprocessed
```

---

## 🔄 完整工作流程示例

### Day 1: 开始采集（5510 只股票）

```python
# 2026-03-16 10:00
from src.utils.baostock_extension import BaostockExtension

ext = BaostockExtension()
ext.run_full_collection(year=2025)  # 采集 2025 年数据
# 处理到一半，比如处理了 3000 只，还剩 2510 只
# 程序暂停/停止
```

**Redis 状态**:
```
baostock:extension:stock_data:2026-03-16:unprocessed
剩余：2510 只股票
```

---

### Day 2: 继续执行（处理剩余的 2510 只）

```python
# 2026-03-17 09:00
from src.utils.baostock_extension import BaostockExtension

ext = BaostockExtension()

# 传入昨天的日期，继续处理剩余的股票
ext.run_full_collection(date='2026-03-16')
# 处理完剩余的 2510 只
ext.close()
```

**关键点**:
- ✅ 传入 `date='2026-03-16'`，使用昨天的 Redis key
- ✅ 自动获取昨天剩余的 2510 只股票
- ✅ 处理完成后 Redis key 被清空

---

## ⚠️ 注意事项

### 1. 日期格式

必须使用 `YYYY-MM-DD` 格式：
```python
✅ '2026-03-16'
❌ '2026/03/16'
❌ '03-16-2026'
```

### 2. 日期选择

- **不传 `date`**: 使用当前日期（`self.now_date`）
- **传入 `date`**: 使用指定日期，用于跨天继续执行

### 3. Redis 清理

如果需要重新执行某一天的任务，先清理 Redis：
```python
ext.redis_manager.client.delete('baostock:extension:stock_data:2026-03-16:unprocessed')
```

### 4. 记录表更新

`stock_performance_update_record` 表中的日期字段会正常更新，不受 `date` 参数影响。

---

## 📋 日志示例

### 使用当前日期

```
2026-03-16 10:00:00 - INFO - === 开始扩展数据采集（支持断点续传）日期：2026-03-16 ===
2026-03-16 10:00:01 - INFO - ✅ Redis 初始化完成：5510 只股票（首次执行）
2026-03-16 10:00:01 - DEBUG - Redis key: baostock:extension:stock_data:2026-03-16:unprocessed
```

### 使用指定日期

```
2026-03-17 09:00:00 - INFO - === 开始扩展数据采集（支持断点续传）日期：2026-03-16 ===
2026-03-17 09:00:01 - INFO - 📌 从 Redis 获取 2510 只待处理股票（断点续传）
2026-03-17 09:00:01 - DEBUG - Redis key: baostock:extension:stock_data:2026-03-16:unprocessed
2026-03-17 12:00:00 - DEBUG - ✅ sh.600000 已从 Redis unprocessed 移除（日期：2026-03-16）
```

---

## 🔧 相关代码文件

- `src/utils/baostock_extension.py` - 主要修改文件
  - `run_full_collection()` - 添加 `date` 参数
  - `get_pending_stocks()` - 添加 `date` 参数
  - `mark_as_processed()` - 添加 `date` 参数

---

## ✅ 测试验证

### 测试 1: 不传 date（默认当前日期）

```python
ext = BaostockExtension()
ext.run_full_collection()
# 预期：使用当前日期，Redis key 为 baostock:extension:stock_data:2026-03-16:unprocessed
```

### 测试 2: 传入昨天的日期

```python
from datetime import datetime, timedelta
yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

ext = BaostockExtension()
ext.run_full_collection(date=yesterday)
# 预期：使用昨天的日期，Redis key 为 baostock:extension:stock_data:2026-03-15:unprocessed
```

### 测试 3: 验证 Redis 数据

```bash
# 查看 Redis 中的 key
redis-cli
> KEYS baostock:extension:stock_data:*:unprocessed

# 预期输出：
# baostock:extension:stock_data:2026-03-16:unprocessed
# baostock:extension:stock_data:2026-03-15:unprocessed
```

---

**版本**: 1.0  
**最后更新**: 2026-03-16 18:15  
**维护者**: stock_learning 团队

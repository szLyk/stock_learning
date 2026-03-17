# AKShare 批量采集方法更新报告

**更新时间**：2026-03-17  
**参考实现**：BaostockFinancialFetcher 批量采集方法

---

## 📊 更新内容

### 修改前

```python
def fetch_moneyflow_batch(self, max_retries=3):
    """批量获取资金流向（支持断点续传）"""
    # 固定从 Redis/数据库获取股票列表
    stock_codes = self.get_pending_stocks('moneyflow')
    # ...
```

### 修改后

```python
def fetch_moneyflow_batch(self, stock_codes=None, max_retries=3):
    """
    批量获取资金流向（支持断点续传）
    
    :param stock_codes: 股票代码列表，None 表示自动从 Redis/数据库获取
    :param max_retries: 最大重试次数，默认 3 次
    """
    # 如果没有传入股票列表，自动获取
    if stock_codes is None:
        stock_codes = self.get_pending_stocks('moneyflow')
    # ...
```

---

## ✅ 更新的方法（4 个）

| 方法名 | 新签名 | 功能 |
|--------|--------|------|
| **fetch_moneyflow_batch** | `(self, stock_codes=None, max_retries=3)` | 批量采集资金流向 |
| **fetch_shareholder_batch** | `(self, stock_codes=None, max_retries=3)` | 批量采集股东人数 |
| **fetch_concept_batch** | `(self, stock_codes=None, max_retries=3)` | 批量采集概念板块 |
| **fetch_analyst_batch** | `(self, stock_codes=None, max_retries=3)` | 批量采集分析师评级 |

---

## 🎯 使用方式

### 方式 1：自动获取股票列表（默认）

**适用场景：** 初始化采集、定时任务

```python
from src.utils.akshare_fetcher import AkShareFetcher

fetcher = AkShareFetcher()

# 不传参数，自动从 Redis/数据库获取待采集股票
fetcher.fetch_moneyflow_batch()
fetcher.fetch_shareholder_batch()
fetcher.fetch_concept_batch()
fetcher.fetch_analyst_batch()

fetcher.mysql_manager.close()
```

**行为：**
- 首次运行：从数据库获取所有待采集股票，初始化到 Redis
- 中断后续传：从 Redis 获取剩余股票继续采集
- 完成后：Redis 为空，直接返回

---

### 方式 2：传入自定义股票列表

**适用场景：** 特定股票采集、测试、分批采集

```python
from src.utils.akshare_fetcher import AkShareFetcher

fetcher = AkShareFetcher()

# 传入自定义股票列表
custom_stocks = ['000001', '600000', '300750']

fetcher.fetch_moneyflow_batch(stock_codes=custom_stocks)
fetcher.fetch_analyst_batch(stock_codes=custom_stocks)

fetcher.mysql_manager.close()
```

**行为：**
- 使用传入的股票列表进行采集
- 仍然支持 Redis 断点续传
- 采集完成后从 Redis 移除已处理股票

---

### 方式 3：从其他数据源获取股票列表

**适用场景：** 量化选股、特定条件筛选

```python
from src.utils.akshare_fetcher import AkShareFetcher

fetcher = AkShareFetcher()

# 从数据库查询符合条件的股票
sql = """
SELECT stock_code FROM stock_basic 
WHERE market_type = 'sz' AND stock_status = 1
"""
result = fetcher.mysql_manager.query_all(sql)
sz_stocks = [r['stock_code'] for r in result]

# 只采集深市股票
fetcher.fetch_concept_batch(stock_codes=sz_stocks)

fetcher.mysql_manager.close()
```

---

### 方式 4：分批采集

**适用场景：** 大数据量、分布式采集

```python
from src.utils.akshare_fetcher import AkShareFetcher

fetcher = AkShareFetcher()

# 获取所有待采集股票
all_stocks = fetcher.get_pending_stocks('analyst')

# 分批处理，每批 1000 只
batch_size = 1000
for i in range(0, len(all_stocks), batch_size):
    batch = all_stocks[i:i + batch_size]
    print(f"采集第 {i//batch_size + 1} 批，共 {len(batch)} 只股票")
    fetcher.fetch_analyst_batch(stock_codes=batch)

fetcher.mysql_manager.close()
```

---

## 🔄 与 Baostock 对比

### Baostock 实现

```python
class BaostockFinancialFetcher:
    def fetch_profit_batch(self, max_retries=5):
        """批量采集利润表数据"""
        self._fetch_single_type_batch('profit', ...)
    
    def _fetch_single_type_batch(self, data_type, ...):
        # 内部调用 get_pending_stocks 获取股票列表
        result = self.get_pending_stocks(data_type)
        # ...
```

### AKShare 实现（更新后）

```python
class AkShareFetcher:
    def fetch_moneyflow_batch(self, stock_codes=None, max_retries=3):
        # 支持传入股票列表，也支持自动获取
        if stock_codes is None:
            stock_codes = self.get_pending_stocks('moneyflow')
        # ...
```

### 对比结果

| 特性 | Baostock | AKShare（新） |
|------|----------|---------------|
| **自动获取股票** | ✅ | ✅ |
| **传入自定义列表** | ❌ | ✅ |
| **断点续传** | ✅ | ✅ |
| **自动重试** | ✅ | ✅ |
| **分批采集** | ❌ | ✅ |

**AKShare 更灵活！** 🎉

---

## 📝 完整示例

### 示例 1：定时任务（自动获取）

```python
#!/usr/bin/env python3
# XXL-JOB 执行器调用

from src.utils.akshare_fetcher import AkShareFetcher

def run_akshare_collection(data_type):
    fetcher = AkShareFetcher()
    
    if data_type == 'moneyflow':
        fetcher.fetch_moneyflow_batch()  # 自动获取股票
    elif data_type == 'analyst':
        fetcher.fetch_analyst_batch()    # 自动获取股票
    
    fetcher.mysql_manager.close()
```

---

### 示例 2：测试特定股票

```python
#!/usr/bin/env python3
# 测试脚本

from src.utils.akshare_fetcher import AkShareFetcher

fetcher = AkShareFetcher()

# 只测试几只股票
test_stocks = ['000001', '600000', '300750']

print("测试资金流向采集...")
fetcher.fetch_moneyflow_batch(stock_codes=test_stocks)

print("测试分析师评级采集...")
fetcher.fetch_analyst_batch(stock_codes=test_stocks)

fetcher.mysql_manager.close()
```

---

### 示例 3：量化选股后采集

```python
#!/usr/bin/env python3
# 量化选股策略

from src.utils.akshare_fetcher import AkShareFetcher

fetcher = AkShareFetcher()

# 1. 量化选股（示例：低 PE 股票）
sql = """
SELECT stock_code FROM stock_valuation 
WHERE pe_ratio < 20 AND pe_ratio > 0
LIMIT 100
"""
result = fetcher.mysql_manager.query_all(sql)
selected_stocks = [r['stock_code'] for r in result]

print(f"选股结果：{len(selected_stocks)} 只股票")

# 2. 采集选中股票的分析师评级
fetcher.fetch_analyst_batch(stock_codes=selected_stocks)

fetcher.mysql_manager.close()
```

---

## ✅ 功能验证

### 验证脚本

```bash
cd /home/fan/.openclaw/workspace/stock_learning
python3 << 'EOF'
from src.utils.akshare_fetcher import AkShareFetcher

fetcher = AkShareFetcher()

# 测试 1：自动获取
print("测试 1: 自动获取股票列表")
stocks = fetcher.get_pending_stocks('analyst')
print(f"  待采集股票：{len(stocks)} 只")

# 测试 2：传入自定义列表
print("\n测试 2: 传入自定义股票列表")
test_stocks = ['000001', '600000']
fetcher.fetch_analyst_batch(stock_codes=test_stocks)

fetcher.mysql_manager.close()
EOF
```

---

## 🚀 下一步

### 1. 更新 XXL-JOB 执行器

当前 XXL-JOB 执行器已经使用自动获取模式，无需修改：

```python
def run_akshare_collection_task(data_type):
    fetcher = AkShareFetcher()
    
    if data_type == 'moneyflow':
        fetcher.fetch_moneyflow_batch()  # ✅ 自动获取
    # ...
```

### 2. 更新初始化脚本

当前脚本也已使用自动获取模式，无需修改：

```python
def main():
    fetcher = AkShareFetcher()
    fetcher.fetch_moneyflow_batch()  # ✅ 自动获取
    # ...
```

### 3. 新增灵活用法

现在可以支持更多灵活用法：
- ✅ 特定股票池采集
- ✅ 量化选股后采集
- ✅ 分批采集
- ✅ 分布式采集

---

## 📊 总结

### 更新内容
- ✅ 4 个批量采集方法都添加了 `stock_codes` 参数
- ✅ 默认值为 `None`，保持向后兼容
- ✅ 支持传入自定义股票列表
- ✅ 自动获取逻辑不变

### 优势
- ✅ **更灵活**：支持多种使用场景
- ✅ **向后兼容**：现有代码无需修改
- ✅ **参考 Baostock**：实现模式一致
- ✅ **断点续传**：功能完整保留

### 使用建议
- **定时任务**：使用默认模式（自动获取）
- **测试/调试**：传入特定股票列表
- **量化策略**：先选股，再传入股票列表采集
- **大数据量**：分批采集，避免超时

---

**更新完成！** 🎉

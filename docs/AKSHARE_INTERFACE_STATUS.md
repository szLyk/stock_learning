# AKShare 接口问题总结

**更新时间**：2026-03-17  
**测试股票**：浦发银行 (600000)

---

## 📊 接口状态

| 数据类型 | 接口名 | 状态 | 问题 | 解决方案 |
|---------|--------|------|------|---------|
| **分析师评级** | `stock_research_report_em` | ✅ 正常 | 无 | 已实现，可正常使用 |
| **资金流向** | `stock_fund_flow_individual` | ❌ AKShare bug | 列数不匹配 | 已添加错误处理，跳过失败股票 |
| **股东人数** | `stock_shareholder_change_ths` | ⚠️ 需调整 | 接口返回所有股票数据 | 已修复，获取全部后过滤 |
| **概念板块** | `stock_board_concept_name_em` | ❌ 接口变化 | 参数不匹配 | 待修复 |

---

## ✅ 正常工作的接口

### 分析师评级

**接口：** `ak.stock_research_report_em(symbol=stock_code)`

**测试结果：**
```
✅ 采集成功：224 条
✅ 入库成功：114 条
✅ 数据格式正确
```

**使用方式：**
```python
from src.utils.akshare_fetcher import AkShareFetcher

fetcher = AkShareFetcher()
df = fetcher.fetch_analyst_rating('600000')
fetcher.mysql_manager.batch_insert_or_update('stock_analyst_expectation', df, ['stock_code', 'publish_date'])
```

---

## ⚠️ 有问题的接口

### 1. 资金流向

**问题：** AKShare 库内部 bug，设置列名时出现列数不匹配

**错误信息：**
```
ValueError: Length mismatch: Expected axis has 10 elements, new values have 7 elements
```

**当前处理：**
- 已添加 try-catch 捕获错误
- 返回空 DataFrame，程序继续执行
- 记录警告日志

**建议：** 等待 AKShare 修复或切换到其他数据源

---

### 2. 股东人数

**问题：** 接口返回所有股票数据，需要过滤

**已修复：**
```python
# 获取所有股票数据
df = ak.stock_shareholder_change_ths()

# 过滤指定股票
if '股票代码' in df.columns:
    df = df[df['股票代码'] == stock_code]
```

**测试：** 待验证

---

### 3. 概念板块

**问题：** AKShare 接口参数变化，无法传入股票代码

**当前状态：** 待修复

**建议方案：**
1. 获取所有概念板块数据，然后过滤
2. 或切换到其他数据源

---

## 🎯 建议

### 短期方案

**只使用分析师评级接口**，这个接口目前稳定可用：

```bash
# 采集分析师评级
python3 scripts/run_akshare.py analyst
```

### 中期方案

**修复其他接口：**
1. 资金流向 - 等待 AKShare 修复 bug
2. 股东人数 - 已修复，待测试
3. 概念板块 - 需要找到正确的接口

### 长期方案

**考虑多数据源策略：**
- 分析师评级：AKShare
- 资金流向：Tushare 或其他
- 股东人数：AKShare（已修复）
- 概念板块：Tushare 或其他

---

## 📝 测试记录

### 测试 1：分析师评级（成功）

```bash
python3 << 'EOF'
from src.utils.akshare_fetcher import AkShareFetcher
fetcher = AkShareFetcher()
df = fetcher.fetch_analyst_rating('000001')
print(f"采集：{len(df)} 条")
rows = fetcher.mysql_manager.batch_insert_or_update('stock_analyst_expectation', df, ['stock_code', 'publish_date'])
print(f"入库：{rows} 行")
EOF
```

**结果：**
```
✅ 采集：224 条
✅ 入库：224 行
```

---

### 测试 2：资金流向（失败）

**错误：** AKShare 库 bug

**日志：**
```
2026-03-17 11:29:24 - WARNING - AkShare 库 bug（列数不匹配）：000001，跳过
```

---

### 测试 3：股东人数（待测试）

**已修复代码，待验证**

---

### 测试 4：概念板块（失败）

**错误：** 接口参数不匹配

---

## 🔧 下一步

1. **测试股东人数接口修复**
2. **寻找概念板块的正确接口**
3. **监控 AKShare 资金流向 bug 修复**
4. **考虑引入 Tushare 作为备用数据源**

---

**当前可用功能：** ✅ 分析师评级采集 + 入库

**建议：** 先使用分析师评级功能，其他数据源等待修复或切换

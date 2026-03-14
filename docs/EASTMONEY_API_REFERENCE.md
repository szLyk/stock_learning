# 东方财富 API 参考文档

**创建时间:** 2026-03-14  
**特点:** 完全免费，无需 Token，数据丰富

---

## 📡 API 优势

| 优势 | 说明 |
|------|------|
| ✅ **完全免费** | 无需注册，无需 Token |
| ✅ **数据丰富** | 资金流、股东、概念、研报全有 |
| ✅ **实时数据** | 支持实时行情和资金流向 |
| ✅ **历史数据** | 支持多年历史数据 |
| ✅ **无需授权** | 直接 HTTP 请求即可 |

---

## 🔧 安装依赖

```bash
pip3 install requests pandas
```

---

## 📊 接口列表

### 1. 资金流向接口 ⭐

**功能:** 获取个股每日资金流向（主力、大单、中单、小单）

**API URL:**
```
http://push2.eastmoney.com/api/qt/stock/fflow/daykline/get
```

**参数:**
| 参数 | 说明 | 示例 |
|------|------|------|
| `secid` | 证券 ID | `1.601398` (沪市), `0.000001` (深市) |
| `lmt` | 返回条数 | `1000` |
| `klt` | K 线类型 | `1`=日，`5`=5 日，`10`=10 日 |
| `fields1` | 返回字段 1 | `f1,f2,f3,f7` |
| `fields2` | 返回字段 2 | `f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65` |
| `ut` | 授权 token | `b2884a393a59ad64002292a3e90d46a5` |

**返回字段:**
- `f51` - 交易日期
- `f52` - 主力净流入（元）
- `f53` - 小单净流入
- `f54` - 中单净流入
- `f55` - 大单净流入
- `f56` - 主力净流入率
- `f57` - 小单净流入率
- `f58` - 中单净流入率
- `f59` - 大单净流入率
- `f60` - 收盘价
- `f61` - 涨跌幅
- `f62` - 换手率
- `f63` - 总成交额

**Python 示例:**
```python
import requests

secid = "1.601398"  # 工商银行
url = "http://push2.eastmoney.com/api/qt/stock/fflow/daykline/get"
params = {
    'lmt': '1000',
    'klt': '1',
    'fields1': 'f1,f2,f3,f7',
    'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65',
    'ut': 'b2884a393a59ad64002292a3e90d46a5',
    'secid': secid
}

resp = requests.get(url, params=params)
data = resp.json()

# 解析数据
klines = data['data']['klines']
for line in klines:
    fields = line.split(',')
    print(f"日期：{fields[0]}, 主力净流入：{fields[1]}元")
```

---

### 2. 北向资金接口 ⭐

**功能:** 获取北向资金（沪股通/深股通）持仓和净流入

**API URL:**
```
http://push2.eastmoney.com/api/qt/stock/fflow/kline/get
```

**参数:** 同上

**返回字段:**
- `f51` - 交易日期
- `f52` - 北向持仓（股）
- `f53` - 北向净流入（股）

**Python 示例:**
```python
params = {
    'lmt': '1000',
    'klt': '1',
    'fields1': 'f1,f2,f3,f7',
    'fields2': 'f51,f52,f53',
    'ut': 'b2884a393a59ad64002292a3e90d46a5',
    'secid': '1.601398'
}

resp = requests.get(url, params=params)
data = resp.json()

for line in data['data']['klines']:
    date, hold, net_in = line.split(',')
    print(f"日期：{date}, 持仓：{hold}, 净流入：{net_in}")
```

---

### 3. 股东人数接口 ⭐

**功能:** 获取股东总人数、户均持股等（季度数据）

**API URL:**
```
http://datacenter-web.eastmoney.com/api/data/v1/get
```

**参数:**
| 参数 | 说明 | 示例 |
|------|------|------|
| `reportName` | 报表名称 | `RPT_F10_EH_EQUITY` |
| `columns` | 返回字段 | `SECURITY_CODE,HOLDER_TOTAL_NUM,...` |
| `filter` | 过滤条件 | `(SECURITY_CODE="601398")` |
| `sortColumns` | 排序字段 | `END_DATE` |
| `sortTypes` | 排序方式 | `-1`=降序 |

**返回字段:**
- `SECURITY_CODE` - 股票代码
- `HOLDER_TOTAL_NUM` - 股东总人数
- `HOLDER_TOTAL_NUMCHANGE` - 股东人数变化
- `AVG_HOLD` - 户均持股数
- `AVG_HOLD_CHANGE` - 户均持股变化

**Python 示例:**
```python
url = "http://datacenter-web.eastmoney.com/api/data/v1/get"
params = {
    'reportName': 'RPT_F10_EH_EQUITY',
    'columns': 'SECURITY_CODE,SECURITY_NAME_ABBR,END_DATE,HOLDER_TOTAL_NUM,HOLDER_TOTAL_NUMCHANGE,AVG_HOLD',
    'filter': '(SECURITY_CODE="601398")',
    'pageNumber': '1',
    'pageSize': '20',
    'sortTypes': '-1',
    'sortColumns': 'END_DATE'
}

resp = requests.get(url, params=params)
data = resp.json()

for item in data['result']['data']:
    print(f"日期：{item['END_DATE']}, 股东人数：{item['HOLDER_TOTAL_NUM']}")
```

---

### 4. 概念板块接口

**功能:** 获取股票所属概念板块

**API URL:**
```
http://push2.eastmoney.com/api/qt/stock/get
```

**参数:**
| 参数 | 说明 | 示例 |
|------|------|------|
| `secid` | 证券 ID | `1.601398` |
| `fields` | 返回字段 | `f12,f13,f14,f152` |

**返回字段:**
- `f12` - 股票代码
- `f13` - 市场代码
- `f14` - 股票名称
- `f152` - 概念板块（逗号分隔）

**Python 示例:**
```python
params = {
    'fields': 'f12,f13,f14,f152',
    'secid': '1.601398'
}

resp = requests.get(url, params=params)
data = resp.json()

concepts = data['data']['f152'].split(',')
print(f"概念板块：{concepts}")
```

---

### 5. 分析师评级接口

**功能:** 获取券商研报、分析师评级、目标价

**API URL:**
```
http://datacenter-web.eastmoney.com/api/data/v1/get
```

**参数:**
| 参数 | 说明 | 示例 |
|------|------|------|
| `reportName` | 报表名称 | `RPT_RES_REPORT_INDEX` |
| `filter` | 过滤条件 | `(SECURITY_CODE="601398")` |

**返回字段:**
- `SECURITY_CODE` - 股票代码
- `PUBLISH_DATE` - 发布日期
- `ORGANISM_NAME` - 机构名称
- `ANALYST_NAME` - 分析师姓名
- `RATING_TYPE` - 评级（买入/增持/中性/减持/卖出）
- `TARGET_PRICE` - 目标价

---

## 🔢 证券 ID 规则

| 市场 | 前缀 | 示例 |
|------|------|------|
| 沪市 A 股 | `1.` | `1.601398` (工商银行) |
| 深市 A 股 | `0.` | `0.000001` (平安银行) |
| 沪市 B 股 | `2.` | `2.900901` |
| 深市 B 股 | `3.` | `3.200001` |
| 创业板 | `0.` | `0.300750` (宁德时代) |
| 科创板 | `1.` | `1.688001` |

---

## 📝 使用工具类

```python
from src.utils.eastmoney_tool import EastMoneyFetcher

fetcher = EastMoneyFetcher()

# 1. 资金流向
df = fetcher.fetch_moneyflow('601398', start_date='2026-01-01', end_date='2026-03-14')

# 2. 北向资金
df = fetcher.fetch_north_moneyflow('601398', limit=100)

# 3. 股东人数
df = fetcher.fetch_shareholder_count('601398', year=2025)

# 4. 概念板块
df = fetcher.fetch_concept('601398')

# 5. 分析师评级
df = fetcher.fetch_analyst_rating('601398', limit=50)

# 批量采集
stock_codes = ['601398', '600036', '000001']
df = fetcher.batch_fetch_moneyflow(stock_codes, start_date='2026-01-01')

# 保存到数据库
fetcher.save_to_db(df, 'stock_capital_flow', ['stock_code', 'stock_date'])

fetcher.close()
```

---

## ⚠️ 注意事项

### 1. 请求频率限制
- 建议每请求 10 次休眠 0.3-1 秒
- 避免短时间内大量请求

### 2. 数据格式
- 日期格式：`YYYY-MM-DD`
- 金额单位：元
- 持股比例：%

### 3. 错误处理
```python
try:
    df = fetcher.fetch_moneyflow('601398')
    if df.empty:
        print("无数据")
except Exception as e:
    print(f"请求失败：{e}")
```

### 4. 数据更新频率
| 数据类型 | 更新频率 |
|----------|----------|
| 资金流向 | 实时（交易日 15:00 后） |
| 北向资金 | 实时（交易日 15:00 后） |
| 股东人数 | 季度（财报披露） |
| 概念板块 | 不定期 |
| 分析师评级 | 实时 |

---

## 🔗 相关文档

- [Baostock API 参考](BAOSTOCK_API_REFERENCE.md)
- [多因子模型指南](MULTI_FACTOR_GUIDE.md)

---

_最后更新：2026-03-14_

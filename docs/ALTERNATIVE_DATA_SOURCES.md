# 4 个受影响数据表的替代方案

**调研时间**: 2026-03-17  
**目标**: 寻找资金流向、股东人数、概念板块、分析师评级的替代数据源

---

## 📊 数据表 1: stock_capital_flow（资金流向）⭐⭐⭐

### 数据内容
```
stock_code, stock_date, 
main_net_in（主力净流入）, sm_net_in（小单）, mm_net_in（中单）, bm_net_in（大单）,
main_net_in_rate（主力净流入率）, close_price, change_rate, turnover_rate
```

### 替代方案

#### 方案 1: 爬取东方财富网页版 ⭐⭐⭐⭐

**目标 URL**:
```
http://data.eastmoney.com/zjlx/000001.html
```

**爬取方法**:
```python
from bs4 import BeautifulSoup
import requests

def fetch_moneyflow_web(stock_code):
    url = f"http://data.eastmoney.com/zjlx/{stock_code}.html"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'http://data.eastmoney.com/zjlx/',
    }
    
    resp = requests.get(url, headers=headers)
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    # 查找资金流向表格
    # 需要根据实际页面结构解析
    table = soup.find('table', {'class': 'table'})
    
    # 解析数据
    data = []
    for row in table.find_all('tr')[1:]:  # 跳过表头
        cols = row.find_all('td')
        if len(cols) >= 10:
            data.append({
                'stock_date': cols[0].text.strip(),
                'main_net_in': cols[1].text.strip(),
                'sm_net_in': cols[2].text.strip(),
                'mm_net_in': cols[3].text.strip(),
                'bm_net_in': cols[4].text.strip(),
                'main_net_in_rate': cols[5].text.strip(),
                'close_price': cols[6].text.strip(),
                'change_rate': cols[7].text.strip(),
                'turnover_rate': cols[8].text.strip(),
            })
    
    return pd.DataFrame(data)
```

**优势**:
- ✅ 数据完整（历史数据都有）
- ✅ 免费
- ✅ 更新及时（每日收盘后更新）

**劣势**:
- ⚠️ 需要解析 HTML
- ⚠️ 可能有反爬（需要控制频率）
- ⚠️ 页面结构可能变化

**可行性**: 🟢 **高** - 推荐实施

---

#### 方案 2: 同花顺资金流向 ⭐⭐⭐

**目标 URL**:
```
http://stockpage.10jqka.com.cn/000001/funds/
```

**爬取方法**: 类似东方财富，解析网页表格

**优势**:
- ✅ 数据完整
- ✅ 反爬相对宽松

**劣势**:
- ⚠️ 页面结构复杂
- ⚠️ 需要 JavaScript 渲染

**可行性**: 🟡 **中** - 作为备选

---

#### 方案 3: 百度股市通 ⭐⭐⭐

**目标 URL**:
```
https://gushitong.baidu.com/stock/ab-000001
```

**优势**:
- ✅ 数据完整
- ✅ 页面简洁

**劣势**:
- ⚠️ 需要处理 JavaScript
- ⚠️ 可能需要 Selenium

**可行性**: 🟡 **中** - 作为备选

---

#### 方案 4: Tushare（需要积分）⭐⭐

**接口**:
```python
import tushare as ts
pro = ts.pro_api('your_token')
df = pro.moneyflow(ts_code='000001.SZ', trade_date='20260316')
```

**优势**:
- ✅ 接口稳定
- ✅ 数据规范

**劣势**:
- ❌ 需要 120 积分（注册送 100 积分）
- ❌ 需要签到或捐赠

**费用**: 捐赠 120 元永久 VIP

**可行性**: 🟢 **高**（如果愿意付费）

---

### 推荐方案

**短期**: 爬取东方财富网页版（方案 1）
**长期**: Tushare VIP（120 元/年）

---

## 📊 数据表 2: stock_shareholder_info（股东人数）⭐⭐

### 数据内容
```
stock_code, report_date,
shareholder_count（股东总人数）, shareholder_change（变化率）,
avg_hold_per_household（户均持股）, avg_hold_change,
freehold_shares（流通股份）, freehold_ratio（流通比例）
```

### 替代方案

#### 方案 1: 爬取东方财富网页版 ⭐⭐⭐⭐

**目标 URL**:
```
http://data.eastmoney.com/gdgc/000001.html
```

**爬取方法**:
```python
def fetch_shareholder_web(stock_code):
    url = f"http://data.eastmoney.com/gdgc/{stock_code}.html"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    resp = requests.get(url, headers=headers)
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    # 查找股东人数表格
    table = soup.find('table', {'class': 'table'})
    
    data = []
    for row in table.find_all('tr')[1:]:
        cols = row.find_all('td')
        if len(cols) >= 8:
            data.append({
                'report_date': cols[0].text.strip(),
                'shareholder_count': cols[1].text.strip(),
                'shareholder_change': cols[2].text.strip(),
                'avg_hold_per_household': cols[3].text.strip(),
                'avg_hold_change': cols[4].text.strip(),
                'freehold_shares': cols[5].text.strip(),
                'freehold_ratio': cols[6].text.strip(),
            })
    
    return pd.DataFrame(data)
```

**优势**:
- ✅ 数据完整（季报数据）
- ✅ 免费
- ✅ 更新及时（季报发布后）

**劣势**:
- ⚠️ 季度更新（频率低）
- ⚠️ 需要解析 HTML

**可行性**: 🟢 **高** - 推荐实施

---

#### 方案 2: 巨潮资讯（官方）⭐⭐⭐⭐⭐

**目标 URL**:
```
http://www.cninfo.com.cn/
```

**说明**: 巨潮资讯是证监会指定信息披露网站，所有上市公司财报都在这里

**爬取方法**:
- 访问个股页面
- 下载定期报告（PDF）
- 解析 PDF 获取股东人数

**优势**:
- ✅ 官方数据源
- ✅ 最准确
- ✅ 免费

**劣势**:
- ❌ 需要解析 PDF
- ❌ 工作量大

**可行性**: 🟡 **中** - 适合批量处理

---

#### 方案 3: Tushare ⭐⭐⭐

**接口**:
```python
df = pro.top10_holders(ts_code='000001.SZ', period='20260331')
```

**优势**:
- ✅ 数据规范
- ✅ 免费（基础版即可）

**劣势**:
- ⚠️ 需要注册

**可行性**: 🟢 **高**

---

### 推荐方案

**短期**: 爬取东方财富网页版（方案 1）
**长期**: Tushare 基础版（免费注册）

---

## 📊 数据表 3: stock_concept（概念板块）⭐⭐

### 数据内容
```
stock_code, stock_name, concept_name, concept_type, is_hot
```

### 替代方案

#### 方案 1: 爬取东方财富网页版 ⭐⭐⭐⭐

**目标 URL**:
```
http://quote.eastmoney.com/sz000001.html#secCode
```

**爬取方法**:
```python
def fetch_concept_web(stock_code):
    url = f"http://quote.eastmoney.com/sz{stock_code}.html"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    resp = requests.get(url, headers=headers)
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    # 查找概念板块
    # 通常在页面某个 div 中
    concept_div = soup.find('div', {'class': 'concept-list'})
    
    data = []
    for concept in concept_div.find_all('a'):
        data.append({
            'stock_code': stock_code,
            'concept_name': concept.text.strip(),
            'concept_type': '主题',
            'is_hot': 0,
        })
    
    return pd.DataFrame(data)
```

**优势**:
- ✅ 数据完整
- ✅ 免费

**劣势**:
- ⚠️ 页面结构复杂
- ⚠️ 需要 JavaScript 渲染

**可行性**: 🟡 **中**

---

#### 方案 2: 同花顺概念 ⭐⭐⭐⭐

**目标 URL**:
```
http://stockpage.10jqka.com.cn/000001/
```

**优势**:
- ✅ 概念分类清晰
- ✅ 数据完整

**劣势**:
- ⚠️ 需要解析 HTML

**可行性**: 🟢 **高** - 推荐

---

#### 方案 3: 手动维护（低频更新）⭐⭐⭐

**说明**: 概念板块变化不频繁，可以手动维护或使用静态数据

**方法**:
- 每周更新一次
- 使用 Excel 维护
- 批量导入数据库

**优势**:
- ✅ 简单可靠
- ✅ 无需爬虫

**劣势**:
- ❌ 工作量大
- ❌ 时效性差

**可行性**: 🟡 **中** - 适合少量股票

---

### 推荐方案

**短期**: 同花顺网页爬虫（方案 2）
**中期**: 手动维护（低频更新）

---

## 📊 数据表 4: stock_analyst_expectation（分析师评级）⭐

### 数据内容
```
stock_code, publish_date,
institution_name（机构名称）, analyst_name（分析师）,
rating_type（评级类型）, rating_score（评级打分）, target_price（目标价）
```

### 替代方案

#### 方案 1: 爬取东方财富网页版 ⭐⭐⭐

**目标 URL**:
```
http://quote.eastmoney.com/sz000001.html#research
```

**爬取方法**: 类似其他表，解析网页表格

**优势**:
- ✅ 数据完整
- ✅ 免费

**劣势**:
- ⚠️ 需要解析 HTML
- ⚠️ 数据量大

**可行性**: 🟡 **中**

---

#### 方案 2: 慧博投研资讯 ⭐⭐⭐

**目标 URL**:
```
http://www.hibor.com.cn/
```

**说明**: 专业的研报平台

**优势**:
- ✅ 研报完整
- ✅ 数据专业

**劣势**:
- ❌ 部分数据需要付费
- ❌ 需要注册

**可行性**: 🟡 **中**

---

#### 方案 3: 暂时搁置 ⭐⭐⭐⭐⭐

**理由**:
- 分析师评级是**参考数据**，不影响核心功能
- 量化选股主要看技术指标和财务数据
- 可以后续补充

**可行性**: 🟢 **最高** - 推荐

---

### 推荐方案

**暂时搁置**，等有时间再实施

---

## 📋 总结对比

| 数据表 | 优先级 | 推荐方案 | 开发成本 | 维护成本 | 可行性 |
|--------|--------|---------|---------|---------|--------|
| **stock_capital_flow** | 🟠 中 | 东方财富网页爬虫 | 1 天 | 低 | 🟢 高 |
| **stock_shareholder_info** | 🟢 低 | 东方财富网页爬虫 | 0.5 天 | 很低 | 🟢 高 |
| **stock_concept** | 🟢 低 | 同花顺网页爬虫 | 1 天 | 中 | 🟡 中 |
| **stock_analyst_expectation** | ⚪ 很低 | **暂时搁置** | - | - | 🟢 高 |

---

## 🎯 实施建议

### 阶段 1: 立即执行（1-2 天）

**优先实现**:
1. ✅ 资金流向爬虫（东方财富网页版）
2. ✅ 股东人数爬虫（东方财富网页版）

**预期成果**:
- 恢复 2 个核心辅助表
- 系统数据完整度达到 90%

---

### 阶段 2: 后续实施（3-5 天）

**实现**:
1. 概念板块爬虫（同花顺网页版）
2. 数据验证和测试

**预期成果**:
- 恢复 3 个辅助表
- 系统数据完整度达到 95%

---

### 阶段 3: 可选（有时间再做）

**实现**:
1. 分析师评级爬虫
2. 或直接使用 Tushare

**预期成果**:
- 数据完整度 100%

---

## 💡 最终建议

**推荐方案**:

1. **立即实施**:
   - ✅ 资金流向爬虫（东方财富）
   - ✅ 股东人数爬虫（东方财富）

2. **暂时搁置**:
   - ⏸️ 概念板块（不影响核心功能）
   - ⏸️ 分析师评级（参考数据）

3. **长期方案**:
   - 考虑 Tushare VIP（120 元/年）
   - 一次性解决所有数据源

**理由**:
- ✅ 核心功能（量化选股、技术分析）不受影响
- ✅ 2 天内可以恢复 90% 数据
- ✅ 成本低，风险小

---

**需要我立即开始开发爬虫代码吗？** 🚀

**最后更新**: 2026-03-17 00:45

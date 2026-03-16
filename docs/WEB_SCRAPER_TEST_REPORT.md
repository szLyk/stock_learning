# 网页爬虫测试报告

**测试时间**: 2026-03-17 00:47  
**测试目标**: 东方财富网页爬虫获取资金流向、股东人数、概念板块数据

---

## 📊 测试结果

### 测试 1: 资金流向爬虫

**目标 URL**: `https://data.eastmoney.com/zjlx/000001.html`

**测试过程**:
```bash
# 1. 测试 URL 可访问性
curl -I "https://data.eastmoney.com/zjlx/000001.html"
# 结果：✅ HTTP 200 OK，页面可访问

# 2. 获取页面内容
curl -sL "https://data.eastmoney.com/zjlx/000001.html"
# 结果：✅ 返回 HTML 页面

# 3. 查找数据
grep -o "main_net_in" page.html
# 结果：❌ 未找到数据字段

# 4. 查找 JSON 数据
grep -oE "var.*=.*\{.*\}" page.html
# 结果：⚠️ 只找到基础股票信息，无资金流向数据
```

**结论**: ❌ **失败**
- 页面可以访问
- 但数据是通过 JavaScript 动态加载的
- HTML 源码中不包含资金流向数据
- 需要执行 JavaScript 才能获取数据

---

### 测试 2: 股东人数爬虫

**目标 URL**: `https://data.eastmoney.com/gdgc/000001.html`

**测试结果**: ❌ **404 Not Found**
```
ERROR - 请求失败，已达最大重试次数：404 Client Error: Not Found
```

**结论**: ❌ **URL 已失效**
- 东方财富可能已更改 URL 结构
- 该页面可能已下线

---

### 测试 3: 概念板块爬虫

**目标 URL**: `http://stockpage.10jqka.com.cn/000001/`

**测试结果**: ⚠️ **未找到概念数据**
```
WARNING - 未找到概念板块：000001
```

**结论**: ⚠️ **需要更精确的解析**
- 页面可以访问
- 但概念数据在复杂的 HTML 结构中
- 需要更精确的 CSS 选择器

---

## 🔍 问题分析

### 问题 1: 动态加载数据

**现象**: 页面可以访问，但 HTML 源码中没有数据

**原因**: 
- 东方财富使用 JavaScript 动态加载数据
- 数据是通过 AJAX 请求获取的
- 简单的 HTTP 请求无法获取动态数据

**解决方案**:
1. 使用 Selenium 或 Playwright（可以执行 JavaScript）
2. 找到实际的 API 接口
3. 使用逆向工程找到数据源

---

### 问题 2: API 接口失效

**现象**: 之前使用的 API 返回空数据

```bash
curl "https://push2.eastmoney.com/api/qt/stock/fflow/daykline/get?secid=0.000001"
# 返回：空
```

**原因**:
- API 参数可能已变更（ut token 失效）
- 接口可能已下线
- 可能需要新的认证机制

**解决方案**:
1. 在浏览器开发者工具中抓取新的 API 请求
2. 找到新的有效参数
3. 更新代码中的 API 参数

---

### 问题 3: URL 结构变更

**现象**: 股东人数 URL 返回 404

**原因**:
- 东方财富可能重组了网站结构
- URL 路径可能已变更

**解决方案**:
1. 手动访问网站找到新的 URL
2. 更新爬虫代码中的 URL

---

## 💡 可行的替代方案

### 方案 1: 使用 Selenium（推荐）⭐⭐⭐⭐

**原理**: Selenium 可以控制浏览器，执行 JavaScript

**示例代码**:
```python
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def fetch_moneyflow_selenium(stock_code):
    # 配置无头浏览器
    options = Options()
    options.add_argument('--headless')
    driver = webdriver.Chrome(options=options)
    
    url = f"https://data.eastmoney.com/zjlx/{stock_code}.html"
    driver.get(url)
    
    # 等待 JavaScript 加载数据
    time.sleep(5)
    
    # 获取渲染后的 HTML
    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')
    
    # 解析数据
    # ...
    
    driver.quit()
```

**优势**:
- ✅ 可以获取动态加载的数据
- ✅ 模拟真实浏览器行为
- ✅ 不易被反爬

**劣势**:
- ⚠️ 需要安装 Chrome 和 Selenium
- ⚠️ 资源消耗大
- ⚠️ 速度较慢

**可行性**: 🟢 **高** - 推荐实施

---

### 方案 2: 抓取新的 API 接口 ⭐⭐⭐⭐

**步骤**:
1. 打开浏览器开发者工具（F12）
2. 访问东方财富个股页面
3. 切换到 Network 标签
4. 刷新页面
5. 找到 XHR/Fetch 请求
6. 复制 API URL 和参数
7. 更新代码

**示例**（需要实际抓取）:
```python
# 新的 API 可能长这样
url = "https://newapi.eastmoney.com/xxx/xxx"
params = {
    'code': '000001',
    'token': 'new_token_value',  # 需要抓取新的 token
    # ...
}
```

**优势**:
- ✅ 直接获取 JSON 数据
- ✅ 速度快
- ✅ 资源消耗小

**劣势**:
- ⚠️ 需要手动抓取
- ⚠️ token 可能定期更新

**可行性**: 🟢 **高** - 推荐实施

---

### 方案 3: 使用第三方库 ⭐⭐⭐

**推荐库**: 
- `akshare` - A 股数据接口（免费）
- `tushare` - 财经数据接口（基础版免费）

**示例**:
```python
import akshare as ak

# 资金流向
df = ak.stock_individual_fund_flow(stock="000001")

# 股东人数
df = ak.stock_hold_num(stock="000001")

# 概念板块
df = ak.stock_board_concept_name_em()
```

**优势**:
- ✅ 已经封装好
- ✅ 维护活跃
- ✅ 文档完善

**劣势**:
- ⚠️ 依赖第三方库
- ⚠️ 可能也有失效风险

**可行性**: 🟢 **高** - 推荐实施

---

## 🎯 下一步行动

### 立即执行（推荐）

1. **安装 Selenium**
   ```bash
   apt-get install -y chromium-driver
   pip3 install selenium
   ```

2. **测试 Selenium 爬虫**
   - 编写 Selenium 测试脚本
   - 验证能否获取动态数据
   - 测试成功率

3. **抓取新 API**
   - 在浏览器中打开东方财富页面
   - 使用开发者工具抓取 API
   - 更新代码中的 URL 和参数

### 短期方案（1-2 天）

1. 实现 Selenium 爬虫
2. 测试资金流向、股东人数、概念板块
3. 批量采集测试

### 长期方案

1. 考虑使用 AkShare 等成熟库
2. 建立多数据源备份
3. 定期维护更新

---

## 📋 测试总结

| 数据源 | 测试方法 | 结果 | 原因 | 解决方案 |
|--------|---------|------|------|---------|
| **资金流向** | HTTP 请求 | ❌ | 动态加载 | Selenium / 新 API |
| **股东人数** | HTTP 请求 | ❌ | URL 失效 | 找新 URL |
| **概念板块** | HTTP 请求 | ⚠️ | 解析困难 | Selenium / 优化解析 |
| **API 接口** | 直接调用 | ❌ | 参数失效 | 抓取新参数 |

---

## ✅ 结论

**当前状态**: ❌ **简单 HTTP 爬虫不可行**

**原因**:
1. 数据是动态加载的（JavaScript）
2. API 接口参数已失效
3. URL 结构可能已变更

**推荐方案**:
1. **立即**: 使用 Selenium 获取动态数据
2. **同时**: 在浏览器中抓取新的 API 参数
3. **备选**: 使用 AkShare 等第三方库

**预计时间**:
- Selenium 方案：1-2 天
- 新 API 抓取：0.5 天
- AkShare 集成：0.5 天

---

**需要我立即实施 Selenium 方案吗？** 🚀

**最后更新**: 2026-03-17 00:50

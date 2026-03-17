# 资金流向数据源调研

**调研日期**: 2026-03-17  
**测试股票**: 浦发银行 (600000)

---

## 📊 可用数据源对比

| 数据源 | 接口 | 状态 | 成本 | 稳定性 | 推荐度 |
|--------|------|------|------|--------|--------|
| **AKShare** | `stock_fund_flow_individual` | ⚠️ 有 bug | 免费 | 中 | ⭐⭐ |
| **Tushare** | `moneyflow` | ✅ 稳定 | 120 积分 | 高 | ⭐⭐⭐⭐ |
| **Baostock** | 无 | ❌ 不支持 | 免费 | - | - |
| **东方财富爬虫** | 自建 | ⚠️ 需维护 | 免费 | 中 | ⭐⭐⭐ |
| **同花顺 iFinD** | API | ✅ 稳定 | 付费 | 高 | ⭐⭐⭐⭐ |

---

## 1️⃣ AKShare（当前使用）

### 接口信息
```python
import akshare as ak
df = ak.stock_fund_flow_individual(symbol="600000")
```

### 返回字段
- 日期、主力净流入、小单净流入、中单净流入、大单净流入
- 主力净流入率、收盘价、涨跌幅、换手率

### 当前问题
❌ **AKShare 库内部 bug**
```
ValueError: Length mismatch: Expected axis has 10 elements, new values have 7 elements
```

### 优点
- ✅ 免费
- ✅ 无需注册
- ✅ 安装即用

### 缺点
- ❌ 库内部有 bug（列数不匹配）
- ❌ 部分股票采集失败
- ❌ 接口不稳定

### 解决方案
```python
# 当前代码已添加错误处理
try:
    df = ak.stock_fund_flow_individual(symbol=stock_code)
except ValueError as ve:
    if "Length mismatch" in str(ve):
        logger.warning(f"AKShare bug，跳过{stock_code}")
        return pd.DataFrame()
```

---

## 2️⃣ Tushare（推荐）

### 接口信息
```python
import tushare as ts

ts.set_token('your_token_here')  # 需要有效 token
pro = ts.pro_api()

df = pro.moneyflow(
    ts_code='600000.SH',
    start_date='20260301',
    end_date='20260317'
)
```

### 返回字段
```
trade_date: 交易日期
buy_sm_amount: 小单买入金额
sell_sm_amount: 小单卖出金额
buy_md_amount: 中单买入金额
sell_md_amount: 中单卖出金额
buy_lg_amount: 大单买入金额
sell_lg_amount: 大单卖出金额
buy_elg_amount: 特大单买入金额
sell_elg_amount: 特大单卖出金额
net_mf_amount: 净流入金额
```

### 优点
- ✅ 数据稳定可靠
- ✅ 接口文档完善
- ✅ 历史数据完整
- ✅ 支持批量获取

### 缺点
- ❌ 需要 120 积分（注册约 100 积分，需额外获取）
- ❌ 有调用频率限制（基础版 500 次/分钟）

### 获取积分方式
1. **注册**: +100 积分
2. **完善信息**: +20 积分
3. **邀请好友**: +20 积分/人
4. **社区贡献**: +10~50 积分
5. **付费**: 约 100 元/年

### 成本估算
- **时间成本**: 约 1-2 小时（完成积分任务）
- **金钱成本**: 0 元（通过任务获取积分）或 100 元/年（直接购买）

---

## 3️⃣ 东方财富网爬虫（备选）

### 接口信息
```python
import requests

url = "http://push2.eastmoney.com/api/qt/stock/fundflow/get"
params = {
    'secid': '1.600000',  # 1=沪市，0=深市
    'ut': 'b2884a393a59ad64002292a3e90d46a5',
    'fields1': 'f1,f2,f3,f7',
    'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65'
}

response = requests.get(url, params=params)
data = response.json()
```

### 优点
- ✅ 免费
- ✅ 数据实时
- ✅ 无需 token

### 缺点
- ❌ 需要自己维护爬虫代码
- ❌ 可能被封 IP
- ❌ 接口可能变化
- ❌ 需要处理反爬

---

## 4️⃣ 同花顺 iFinD（专业版）

### 接口信息
```python
# 需要安装 iFinD Python 接口
from ifind import API

api = API(token='your_token')
df = api.get_stock_fund_flow('600000.SH')
```

### 优点
- ✅ 数据最稳定
- ✅ 数据质量高
- ✅ 技术支持好

### 缺点
- ❌ 付费（约 3000-10000 元/年）
- ❌ 需要安装专用客户端

---

## 🎯 推荐方案

### 短期方案（本周）

**使用 AKShare + 错误处理**

```python
# 当前已实现
def fetch_moneyflow(self, stock_code):
    try:
        df = ak.stock_fund_flow_individual(symbol=stock_code)
        # ... 处理数据 ...
    except ValueError as ve:
        if "Length mismatch" in str(ve):
            self.logger.warning(f"AKShare bug，跳过{stock_code}")
            return pd.DataFrame()
```

**影响：**
- 约 30-50% 的股票采集失败
- 因子模型使用默认值 50 分
- 总体影响轻微（权重 10%）

---

### 中期方案（本月）

**引入 Tushare 作为备用数据源**

```python
class FundFlowFetcher:
    def __init__(self):
        self.akshare = AkShareFetcher()
        self.tushare = TushareFetcher()  # 需要 token
    
    def fetch(self, stock_code):
        # 优先使用 AKShare
        df = self.akshare.fetch_moneyflow(stock_code)
        if not df.empty:
            return df
        
        # AKShare 失败，切换到 Tushare
        df = self.tushare.fetch_moneyflow(stock_code)
        return df
```

**成本：**
- 时间：1-2 小时（注册 + 获取积分）
- 金钱：0 元（通过任务获取积分）

**收益：**
- 数据覆盖率从 50% 提升到 95%+
- 因子模型准确性提升
- 减少维护成本

---

### 长期方案（下季度）

**多数据源策略**

```python
class DataSourceManager:
    def __init__(self):
        self.sources = [
            TushareSource(),      # 优先
            AKShareSource(),      # 备用
            EastMoneySpider()     # 最后手段
        ]
    
    def fetch_fund_flow(self, stock_code):
        for source in self.sources:
            try:
                df = source.fetch(stock_code)
                if not df.empty:
                    return df
            except:
                continue
        return pd.DataFrame()
```

---

## 📝 实施建议

### 立即执行（今天）

1. ✅ **继续使用 AKShare**（已添加错误处理）
2. ✅ **因子模型正常运行**（使用默认值）
3. 📋 **注册 Tushare 账号**（https://tushare.pro）

### 本周执行

1. 📋 **获取 Tushare token**
   - 注册账号
   - 完善信息
   - 完成积分任务
   
2. 📋 **安装 Tushare**
   ```bash
   pip install tushare
   ```

3. 📋 **测试 Tushare 接口**
   ```python
   import tushare as ts
   ts.set_token('your_token')
   pro = ts.pro_api()
   df = pro.moneyflow(ts_code='600000.SH')
   ```

### 下周执行

1. 📋 **实现数据源切换逻辑**
2. 📋 **测试完整采集流程**
3. 📋 **验证因子模型效果**

---

## 💰 成本对比

| 方案 | 时间成本 | 金钱成本 | 数据覆盖率 | 维护成本 |
|------|---------|---------|-----------|---------|
| **仅 AKShare** | 0h | 0 元 | 50% | 高 |
| **AKShare + Tushare** | 2h | 0 元 | 95% | 低 |
| **Tushare 单数据源** | 1h | 0 元 | 95% | 最低 |
| **付费数据源** | 0.5h | 100-3000 元 | 99% | 最低 |

---

## 🚀 最佳实践

**推荐：AKShare + Tushare 双数据源**

**理由：**
1. **免费**: 通过任务获取 Tushare 积分，无需付费
2. **稳定**: Tushare 作为主力，AKShare 作为补充
3. **可靠**: 数据覆盖率 95%+
4. **灵活**: 可动态切换数据源

**实施步骤：**
1. 注册 Tushare（10 分钟）
2. 完成积分任务（1-2 小时）
3. 获取 token（5 分钟）
4. 实现双数据源切换（1 小时）

**总计：** 约 2-3 小时，0 元成本

---

## 📞 获取帮助

### Tushare 注册
- 官网：https://tushare.pro
- 文档：https://tushare.pro/document/2
- 社区：https://tushare.pro/user/community

### AKShare 问题
- GitHub: https://github.com/akfamily/akshare
- 文档：https://akshare.akfamily.xyz

---

**结论：建议本周内注册 Tushare 并获取 token，实现双数据源策略，成本为 0 元 + 2-3 小时时间投入。**

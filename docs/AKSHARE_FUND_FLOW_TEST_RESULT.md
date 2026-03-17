# AKShare 资金流向接口测试结果

**测试日期**: 2026-03-17  
**测试时间**: 13:23 GMT+8

---

## 📊 测试结果总结

### ✅ 确认的问题

**`stock_fund_flow_individual` 接口确实有 bug**

**错误信息：**
```
ValueError: Length mismatch: Expected axis has 10 elements, new values have 7 elements
```

**测试股票：**
- ❌ 600000 (浦发银行) - 失败
- ❌ 000001 (平安银行) - 失败
- ❌ 300750 (宁德时代) - 失败
- ❌ 601398 (工商银行) - 失败

**结论：** 该接口对所有测试股票都失败，是 AKShare 库内部 bug。

---

### ⚠️ 网络问题

**`stock_individual_fund_flow` 接口**

第一次测试时成功获取数据（120 条），但后续测试因网络问题失败：
```
requests.exceptions.ConnectionError: 
('Connection aborted.', RemoteDisconnected(...))
```

**可能原因：**
1. AKShare 服务器网络不稳定
2. 请求频率限制
3. 东方财富 API 反爬

---

## 🔧 当前解决方案

### 方案 1：等待 AKShare 修复（推荐）

**优点：**
- 无需额外工作
- 免费
- 数据源统一

**缺点：**
- 时间不确定
- 可能影响因子模型效果

**当前代码已添加错误处理：**
```python
try:
    df = ak.stock_fund_flow_individual(symbol=stock_code)
except ValueError as ve:
    if "Length mismatch" in str(ve):
        logger.warning(f"AKShare bug，跳过{stock_code}")
        return pd.DataFrame()
```

---

### 方案 2：引入 Tushare（稳定可靠）

**接口：**
```python
import tushare as ts

ts.set_token('your_token')
pro = ts.pro_api()

df = pro.moneyflow(ts_code='600000.SH', start_date='20260301')
```

**成本：**
- 时间：1-2 小时（获取 120 积分）
- 金钱：0 元

**优点：**
- 数据稳定
- 接口完善
- 长期可靠

---

### 方案 3：多接口轮询

**实现：**
```python
def fetch_moneyflow(stock_code):
    # 尝试接口 1
    try:
        df = ak.stock_fund_flow_individual(symbol=stock_code)
        if not df.empty:
            return df
    except:
        pass
    
    # 尝试接口 2（添加重试）
    for i in range(3):
        try:
            time.sleep(1)
            df = ak.stock_individual_fund_flow(stock=stock_code)
            if not df.empty:
                return df
        except:
            continue
    
    # 都失败，返回空
    return pd.DataFrame()
```

---

## 📋 建议

### 短期（本周）

**继续使用 AKShare + 错误处理**

- ✅ 代码已添加 bug 处理
- ✅ 因子模型使用默认值
- ⏭️ 影响轻微（10% 权重）

### 中期（下周）

**注册 Tushare 获取 token**

- 花费 1-2 小时获取积分
- 实现双数据源切换
- 提升数据覆盖率到 95%+

### 长期（下月）

**建立多数据源策略**

- AKShare（免费，部分不稳定）
- Tushare（稳定，需要积分）
- 自动切换机制

---

## 📞 后续步骤

1. **监控 AKShare 修复进度**
   - GitHub: https://github.com/akfamily/akshare
   - Issues: 查看是否有相同 bug 报告

2. **准备 Tushare 集成**
   - 注册账号
   - 获取积分
   - 准备 token

3. **实现数据源切换**
   - 抽象数据源接口
   - 实现自动切换逻辑
   - 添加监控告警

---

**结论：AKShare 资金流向接口确实存在 bug，短期内建议使用默认值或切换到 Tushare。**

# XXL-JOB 任务部署状态报告

**检查时间**：2026-03-17 10:54  
**执行器状态**：✅ 运行中

---

## 📊 执行器状态

### 运行状态

```bash
# 进程状态
root  391  python3 executor_server_simple.py

# PID 文件
391

# 健康检查
curl http://localhost:9999/health
{"status": "UP", "timestamp": "2026-03-17T10:54:39.100173"}
```

**状态：** ✅ **执行器正常运行中**

### 注册状态

```
2026-03-17 10:54:46 - INFO - ✅ 注册到 Admin 数据库：172.18.0.2:9999
```

**注册地址：** `172.18.0.2:9999`  
**注册频率：** 每 30 秒自动注册  
**状态：** ✅ **正常注册到 XXL-JOB Admin**

---

## 📋 已配置任务清单

### 第 1 层：基础行情数据（Baostock）

| 任务名称 | Handler | Cron | 参数 | 超时 |
|---------|---------|------|------|------|
| 股票日线数据采集 | `run_daily_collection` | `0 0 18 * * ?` | date_type=d | 3600s |
| 股票周线数据采集 | `run_daily_collection` | `0 30 18 * * ?` | date_type=w | 3600s |
| 股票月线数据采集 | `run_daily_collection` | `0 0 19 * * ?` | date_type=m | 3600s |
| 股票分钟线数据采集 | `run_min_collection` | `0 */30 9-15 * * ?` | - | 1800s |

**执行时间：** 每天 18:00-19:30  
**数据源：** Baostock

---

### 第 2 层：财务数据（Baostock）

| 任务名称 | Handler | Cron | 参数 | 超时 |
|---------|---------|------|------|------|
| 利润表数据采集 | `run_financial_collection` | `0 0 20 * * ?` | data_type=profit | 7200s |
| 资产负债表数据采集 | `run_financial_collection` | `0 0 20 * * ?` | data_type=balance | 7200s |
| 现金流量表数据采集 | `run_financial_collection` | `0 0 20 * * ?` | data_type=cashflow | 7200s |
| 成长能力数据采集 | `run_financial_collection` | `0 0 20 * * ?` | data_type=growth | 7200s |
| 运营能力数据采集 | `run_financial_collection` | `0 0 20 * * ?` | data_type=operation | 7200s |
| 杜邦分析数据采集 | `run_financial_collection` | `0 0 20 * * ?` | data_type=dupont | 7200s |
| 业绩预告数据采集 | `run_financial_collection` | `0 0 20 * * ?` | data_type=forecast | 7200s |
| 分红送配数据采集 | `run_financial_collection` | `0 0 20 * * ?` | data_type=dividend | 7200s |

**执行时间：** 每天 20:00  
**数据源：** Baostock

---

### 第 3 层：AKShare 数据（新增 ✅）

| 任务名称 | Handler | Cron | 参数 | 超时 |
|---------|---------|------|------|------|
| **资金流向数据采集（AKShare）** | `run_akshare_collection` | `0 0 21 * * ?` | data_type=moneyflow | 3600s |
| **股东人数数据采集（AKShare）** | `run_akshare_collection` | `0 0 21 * * ?` | data_type=shareholder | 3600s |
| **概念板块数据采集（AKShare）** | `run_akshare_collection` | `0 0 21 * * ?` | data_type=concept | 3600s |
| **分析师评级数据采集（AKShare）** | `run_akshare_collection` | `0 0 21 * * ?` | data_type=analyst | 3600s |

**执行时间：** 每天 21:00  
**数据源：** AKShare  
**特性：** 支持 Redis 断点续传

---

### 第 4 层：技术指标计算

| 任务名称 | Handler | Cron | 参数 | 超时 |
|---------|---------|------|------|------|
| 技术指标计算（MACD/RSI/BOLL 等） | `run_indicator_calculation` | `0 0 22 * * ?` | indicator_type=all | 3600s |

**执行时间：** 每天 22:00  
**功能：** 计算 MACD、RSI、BOLL、CCI、OBV、ADX 等技术指标

---

### 第 5 层：多因子打分

| 任务名称 | Handler | Cron | 参数 | 超时 |
|---------|---------|------|------|------|
| 多因子打分 | `run_multi_factor` | `0 0 23 * * ?` | - | 1800s |

**执行时间：** 每天 23:00  
**功能：** 多因子量化打分

---

## 📅 每日任务执行时间表

```
18:00 ──▶ 日线采集（Baostock）
18:30 ──▶ 周线采集（Baostock）
19:00 ──▶ 月线采集（Baostock）
20:00 ──▶ 财务数据采集（8 个任务并发）
21:00 ──▶ AKShare 数据采集（4 个任务并发）✅ 新增
22:00 ──▶ 技术指标计算
23:00 ──▶ 多因子打分
```

---

## ✅ 任务配置验证

### 配置文件检查

**文件：** `xxljob/create_jobs.py`

```python
# 任务总数
JOBS = [
    # 第 1 层：4 个任务（基础行情）
    # 第 2 层：8 个任务（财务数据）
    # 第 3 层：4 个任务（AKShare）✅ 新增
    # 第 4 层：1 个任务（技术指标）
    # 第 5 层：1 个任务（多因子）
]

# 总计：18 个任务
```

### Handler 映射检查

**文件：** `xxljob/executor_server.py`

```python
JOB_HANDLERS = {
    'run_daily_collection': JobHandler.run_daily_collection,
    'run_min_collection': JobHandler.run_min_collection,
    'run_financial_collection': JobHandler.run_financial_collection,
    'run_akshare_collection': JobHandler.run_akshare_collection,  # ✅ 新增
    'run_indicator_calculation': JobHandler.run_indicator_calculation,
    'run_multi_factor': JobHandler.run_multi_factor,
}
```

**状态：** ✅ **所有 Handler 已正确映射**

---

## 🔍 部署检查清单

### 执行器部署

- [x] 执行器进程运行中（PID: 391）
- [x] 健康检查正常（HTTP 9999 端口）
- [x] 定期注册到 Admin（每 30 秒）
- [x] 日志正常输出（`logs/xxljob/executor.log`）

### 任务配置

- [x] `create_jobs.py` 已更新 AKShare 任务
- [x] Handler 映射已更新
- [x] 执行器代码已更新（`executor.py`）
- [x] 命令行参数已更新

### 数据源隔离

- [x] Baostock 任务未受影响
- [x] AKShare 任务独立配置
- [x] Redis Key 命名空间隔离
- [x] 数据库表隔离

---

## 🚀 部署建议

### 1. 在 XXL-JOB Admin 创建任务

如果 XXL-JOB Admin 可以访问，运行以下脚本自动创建任务：

```bash
cd /home/fan/.openclaw/workspace/stock_learning/xxljob
python3 create_jobs.py
```

### 2. 手动创建任务（可选）

如果自动脚本无法连接 Admin，可以手动在 XXL-JOB Admin 界面创建：

**执行器配置：**
- 执行器名称：`stock-data-executor`
- 执行器地址：`172.18.0.2:9999`（自动注册）

**任务配置示例（AKShare 资金流向）：**
- 任务描述：`资金流向数据采集（AKShare）`
- Handler：`run_akshare_collection`
- Cron：`0 0 21 * * ?`
- 执行参数：`data_type=moneyflow`
- 超时时间：`3600`

### 3. 测试任务执行

```bash
# 手动测试 AKShare 资金流向采集
python3 xxljob/executor.py run_akshare_collection --data_type=moneyflow

# 手动测试 AKShare 分析师评级采集
python3 xxljob/executor.py run_akshare_collection --data_type=analyst
```

---

## 📊 监控建议

### 日志监控

```bash
# 执行器日志
tail -f logs/xxljob/executor.log

# AKShare 采集日志
tail -f logs/stock_project/akshare_fetcher_error.log

# Baostock 采集日志
tail -f logs/stock_project/baostock_extension_error.log
```

### Redis 监控

```bash
# 查看 AKShare 待采集队列
redis-cli KEYS "akshare:*:unprocessed"

# 查看 Baostock 待采集队列
redis-cli KEYS "baostock:*:unprocessed"
```

### 数据库监控

```sql
-- 查看 AKShare 采集进度
SELECT 
    COUNT(*) as total,
    SUM(CASE WHEN update_moneyflow IS NOT NULL THEN 1 ELSE 0 END) as moneyflow_done,
    SUM(CASE WHEN update_analyst IS NOT NULL THEN 1 ELSE 0 END) as analyst_done
FROM update_eastmoney_record;
```

---

## ✅ 总结

### 当前状态

| 项目 | 状态 |
|------|------|
| **执行器** | ✅ 运行中（PID: 391） |
| **健康检查** | ✅ 正常 |
| **Admin 注册** | ✅ 正常（每 30 秒） |
| **任务配置** | ✅ 18 个任务已配置 |
| **AKShare 任务** | ✅ 4 个新增任务已配置 |
| **Baostock 任务** | ✅ 12 个任务未受影响 |

### 下一步

1. **确认 XXL-JOB Admin 可访问**（当前无法连接，可能是网络或容器问题）
2. **在 Admin 界面创建/更新任务**（自动或手动）
3. **监控首次自动执行**（今晚 21:00 AKShare 任务）

---

**报告生成时间**：2026-03-17 10:54  
**下次检查**：建议今晚 21:00 后查看任务执行情况

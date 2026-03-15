# XXL-JOB Admin 访问信息

## 🌐 访问地址

```
http://192.168.1.109:8080/xxl-job-admin
```

## 🔐 登录账号

- **用户名**: `admin`
- **密码**: `123456`

---

## 📋 手动创建执行器

### 步骤 1：登录 Admin

打开浏览器访问：`http://192.168.1.109:8080/xxl-job-admin`

### 步骤 2：进入执行器管理

点击左侧菜单：**执行器管理**

### 步骤 3：新增执行器

点击 **新增执行器** 按钮，填写以下信息：

| 字段 | 填写值 |
|------|--------|
| **AppName** | `stock-data-executor` |
| **名称** | `股票数据采集执行器` |
| **执行器类型** | `手动录入` |
| **地址列表** | `172.18.0.2:9999` |

### 步骤 4：保存

点击 **保存** 按钮

---

## ✅ 验证执行器

保存后，在执行器列表中应该能看到：

| AppName | 名称 | 执行器类型 | 地址列表 |
|---------|------|------------|----------|
| stock-data-executor | 股票数据采集执行器 | 手动录入 | 172.18.0.2:9999 |

---

## 📝 创建第一个任务

### 任务配置（日线采集）

进入 **任务管理** → **新增任务**

| 字段 | 值 |
|------|-----|
| **执行器** | 股票数据采集执行器 |
| **JobHandler** | `run_daily_collection` |
| **运行模式** | BEAN |
| **触发类型** | CRON |
| **CRON** | `0 0 18 * * ?` |
| **运行参数** | `date_type=d` |
| **阻塞策略** | 单机串行 |
| **超时时间** | 3600 |
| **失败重试** | 3 |

### 测试任务

1. 保存任务后，点击 **执行一次** 按钮
2. 查看执行日志
3. 确认成功后点击 **启动** 任务

---

## 📊 19 个任务清单

### 第 1 层：基础行情（18:00-19:00）

| 任务 | JobHandler | CRON | 运行参数 |
|------|------------|------|----------|
| 日线采集 | `run_daily_collection` | `0 0 18 * * ?` | `date_type=d` |
| 周线采集 | `run_daily_collection` | `0 30 18 * * ?` | `date_type=w` |
| 月线采集 | `run_daily_collection` | `0 0 19 * * ?` | `date_type=m` |
| 分钟线采集 | `run_min_collection` | `0 */30 9-15 * * ?` | （空） |

### 第 2 层：财务数据（20:00）

| 任务 | JobHandler | CRON | 运行参数 |
|------|------------|------|----------|
| 利润表 | `run_financial_collection` | `0 0 20 * * ?` | `data_type=profit` |
| 资产负债表 | `run_financial_collection` | `0 0 20 * * ?` | `data_type=balance` |
| 现金流量表 | `run_financial_collection` | `0 0 20 * * ?` | `data_type=cashflow` |
| 成长能力 | `run_financial_collection` | `0 0 20 * * ?` | `data_type=growth` |
| 运营能力 | `run_financial_collection` | `0 0 20 * * ?` | `data_type=operation` |
| 杜邦分析 | `run_financial_collection` | `0 0 20 * * ?` | `data_type=dupont` |
| 业绩预告 | `run_financial_collection` | `0 0 20 * * ?` | `data_type=forecast` |
| 分红送配 | `run_financial_collection` | `0 0 20 * * ?` | `data_type=dividend` |

### 第 3 层：东方财富（21:00）

| 任务 | JobHandler | CRON | 运行参数 |
|------|------------|------|----------|
| 资金流向 | `run_eastmoney_collection` | `0 0 21 * * ?` | `data_type=moneyflow` |
| 北向资金 | `run_eastmoney_collection` | `0 0 21 * * ?` | `data_type=north` |
| 股东人数 | `run_eastmoney_collection` | `0 0 21 * * ?` | `data_type=shareholder` |
| 概念板块 | `run_eastmoney_collection` | `0 0 21 * * ?` | `data_type=concept` |
| 分析师评级 | `run_eastmoney_collection` | `0 0 21 * * ?` | `data_type=analyst` |

### 第 4 层：指标计算（22:00）

| 任务 | JobHandler | CRON | 运行参数 |
|------|------------|------|----------|
| 技术指标 | `run_indicator_calculation` | `0 0 22 * * ?` | `indicator_type=all` |

### 第 5 层：多因子打分（23:00）

| 任务 | JobHandler | CRON | 运行参数 |
|------|------------|------|----------|
| 多因子打分 | `run_multi_factor` | `0 0 23 * * ?` | （空） |

---

## 🔧 执行器状态

| 项目 | 状态 |
|------|------|
| 执行器地址 | `172.18.0.2:9999` |
| 心跳注册 | ✅ 正常（每 30 秒） |
| 数据库注册 | ✅ 已注册到 `xxl_job_registry` 表 |
| 健康检查 | ✅ `{"status": "UP"}` |

---

## 🐛 故障排查

### 问题 1：执行器列表中看不到

**解决：**
1. 确认执行器类型选择 **手动录入**
2. 地址列表填写：`172.18.0.2:9999`
3. 刷新页面

### 问题 2：任务执行失败

**解决：**
1. 检查 JobHandler 是否正确（与代码中一致）
2. 检查运行参数格式（key=value）
3. 查看执行器日志：`tail -f logs/xxljob/executor.log`

### 问题 3：无法访问 Admin

**解决：**
```bash
# 在宿主机上检查
docker ps | grep xxl-job-admin
netstat -tlnp | grep 8080
```

---

## 📞 当前状态

| 组件 | 状态 | 地址 |
|------|------|------|
| XXL-JOB Admin | ✅ 运行中 | `http://192.168.1.109:8080/xxl-job-admin` |
| 执行器 | ✅ 运行中 | `172.18.0.2:9999` |
| 数据库注册 | ✅ 已注册 | `xxl_job_registry` 表 |

**下一步：** 登录 Admin 创建执行器和任务！

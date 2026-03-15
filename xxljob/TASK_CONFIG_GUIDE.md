# XXL-JOB 任务配置指南

## 📋 执行器已就绪

✅ **执行器状态**
- AppName: `stock-data-executor`
- 地址：`172.18.0.2:9999`
- 状态：心跳正常（每 30 秒自动注册）

---

## 🔧 配置步骤

### 步骤 1：登录 Admin

```
http://<宿主机 IP>:8080/xxl-job-admin
账号：admin
密码：123456
```

### 步骤 2：确认执行器

进入 **执行器管理**，应该能看到：

| AppName | 名称 | 执行器类型 | 地址列表 |
|---------|------|------------|----------|
| stock-data-executor | 股票数据采集执行器 | 自动注册 | 172.18.0.2:9999 |

**如果没有，手动创建：**
- 点击 **新增执行器**
- AppName: `stock-data-executor`
- 名称：`股票数据采集执行器`
- 执行器类型：`自动注册`
- 保存

---

## 📝 任务配置清单（19 个任务）

### 第 1 层：基础行情（18:00-19:00）

#### 1. 日线采集
| 配置项 | 值 |
|--------|-----|
| 执行器 | stock-data-executor |
| JobHandler | `run_daily_collection` |
| 运行模式 | BEAN |
| 触发类型 | CRON |
| CRON | `0 0 18 * * ?` |
| 运行参数 | `date_type=d` |
| 阻塞策略 | 单机串行 |
| 超时时间 | 3600 |
| 失败重试 | 3 |

#### 2. 周线采集
| 配置项 | 值 |
|--------|-----|
| JobHandler | `run_daily_collection` |
| CRON | `0 30 18 * * ?` |
| 运行参数 | `date_type=w` |

#### 3. 月线采集
| 配置项 | 值 |
|--------|-----|
| JobHandler | `run_daily_collection` |
| CRON | `0 0 19 * * ?` |
| 运行参数 | `date_type=m` |

#### 4. 分钟线采集
| 配置项 | 值 |
|--------|-----|
| JobHandler | `run_min_collection` |
| CRON | `0 */30 9-15 * * ?` |
| 运行参数 | （空） |

---

### 第 2 层：财务数据（20:00）

#### 5-12. 财务数据任务（8 个）

**通用配置：**
- 运行模式：BEAN
- 触发类型：CRON
- CRON：`0 0 20 * * ?`
- 阻塞策略：单机串行
- 超时时间：7200
- 失败重试：3

**各任务配置：**

| 序号 | 任务描述 | JobHandler | 运行参数 |
|------|----------|------------|----------|
| 5 | 利润表 | `run_financial_collection` | `data_type=profit` |
| 6 | 资产负债表 | `run_financial_collection` | `data_type=balance` |
| 7 | 现金流量表 | `run_financial_collection` | `data_type=cashflow` |
| 8 | 成长能力 | `run_financial_collection` | `data_type=growth` |
| 9 | 运营能力 | `run_financial_collection` | `data_type=operation` |
| 10 | 杜邦分析 | `run_financial_collection` | `data_type=dupont` |
| 11 | 业绩预告 | `run_financial_collection` | `data_type=forecast` |
| 12 | 分红送配 | `run_financial_collection` | `data_type=dividend` |

---

### 第 3 层：东方财富（21:00）

#### 13-17. 东方财富任务（5 个）

**通用配置：**
- 运行模式：BEAN
- 触发类型：CRON
- CRON：`0 0 21 * * ?`
- 阻塞策略：单机串行
- 超时时间：3600
- 失败重试：3

| 序号 | 任务描述 | JobHandler | 运行参数 |
|------|----------|------------|----------|
| 13 | 资金流向 | `run_eastmoney_collection` | `data_type=moneyflow` |
| 14 | 北向资金 | `run_eastmoney_collection` | `data_type=north` |
| 15 | 股东人数 | `run_eastmoney_collection` | `data_type=shareholder` |
| 16 | 概念板块 | `run_eastmoney_collection` | `data_type=concept` |
| 17 | 分析师评级 | `run_eastmoney_collection` | `data_type=analyst` |

---

### 第 4 层：指标计算（22:00）

#### 18. 技术指标计算

| 配置项 | 值 |
|--------|-----|
| 执行器 | stock-data-executor |
| JobHandler | `run_indicator_calculation` |
| 运行模式 | BEAN |
| 触发类型 | CRON |
| CRON | `0 0 22 * * ?` |
| 运行参数 | `indicator_type=all` |
| 阻塞策略 | 单机串行 |
| 超时时间 | 3600 |
| 失败重试 | 3 |

---

### 第 5 层：多因子打分（23:00）

#### 19. 多因子打分

| 配置项 | 值 |
|--------|-----|
| 执行器 | stock-data-executor |
| JobHandler | `run_multi_factor` |
| 运行模式 | BEAN |
| 触发类型 | CRON |
| CRON | `0 0 23 * * ?` |
| 运行参数 | （空） |
| 阻塞策略 | 单机串行 |
| 超时时间 | 1800 |
| 失败重试 | 3 |

---

## 🎯 快速配置技巧

### 1. 复制任务（快速创建相似任务）

1. 创建好第一个任务后（如日线采集）
2. 点击 **复制** 按钮
3. 修改任务描述、CRON、运行参数
4. 保存

### 2. 批量创建财务数据任务

1. 先创建好一个财务任务（如利润表）
2. 复制 7 次
3. 分别修改：
   - 任务描述
   - 运行参数（data_type=xxx）

### 3. 测试任务

1. 创建任务后，先不要启动
2. 点击 **执行一次** 按钮
3. 查看执行日志
4. 确认成功后再 **启动** 任务

---

## ✅ 验证配置

### 1. 检查执行器在线状态

进入 **执行器管理**，查看地址列表是否有：
```
172.18.0.2:9999
```

### 2. 测试单个任务

1. 进入 **任务管理**
2. 找到刚创建的任务
3. 点击 **执行一次**
4. 查看执行日志

### 3. 查看执行日志

1. 进入 **运行日志**
2. 选择对应任务
3. 查看执行状态和输出

---

## 🐛 常见问题

### 问题 1：执行器未注册

**现象：** 执行器列表为空或地址为空

**解决：**
1. 检查执行器是否启动：`ps aux | grep executor_server_simple`
2. 查看执行器日志：`tail -f logs/xxljob/executor.log`
3. 确认心跳正常：日志中应有"心跳注册"输出

### 问题 2：任务执行失败

**现象：** 执行日志显示失败

**解决：**
1. 检查 JobHandler 是否正确（与代码中一致）
2. 检查运行参数格式（key=value）
3. 查看执行器日志中的详细错误

### 问题 3：任务超时

**现象：** 任务执行时间超过设置值

**解决：**
1. 增加超时时间（如 3600 → 7200）
2. 优化数据采集逻辑
3. 分批处理数据

---

## 📊 任务调度时间表

```
18:00 ─┬─ 日线采集
       ├─ 周线采集（18:30）
       └─ 月线采集（19:00）

20:00 ─┬─ 利润表
       ├─ 资产负债表
       ├─ 现金流量表
       ├─ 成长能力
       ├─ 运营能力
       ├─ 杜邦分析
       ├─ 业绩预告
       └─ 分红送配

21:00 ─┬─ 资金流向
       ├─ 北向资金
       ├─ 股东人数
       ├─ 概念板块
       └─ 分析师评级

22:00 ─┴─ 技术指标计算

23:00 ─┴─ 多因子打分
```

---

## 🔗 相关文档

- `README.md` - 完整部署文档
- `QUICKSTART_XXLJOB.md` - 快速入门
- `AUTOSTART.md` - 开机自启配置

---

## 📞 当前状态

| 组件 | 状态 |
|------|------|
| XXL-JOB Admin | ✅ 运行中 |
| 执行器 | ✅ 已注册（172.18.0.2:9999） |
| 任务配置 | ⏳ 待配置（19 个任务） |

**下一步：** 登录 Admin 网页端，按照上面的配置清单创建任务。

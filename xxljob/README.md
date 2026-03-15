# XXL-JOB 股票数据采集调度系统

## 系统架构

### 任务分层与依赖关系

```
┌─────────────────────────────────────────────────────────────┐
│                    第 1 层：基础行情数据                      │
│  (并行执行，无依赖)                                          │
│  ├── job_stock_daily (日线)                                 │
│  ├── job_stock_weekly (周线)                                │
│  ├── job_stock_monthly (月线)                               │
│  └── job_stock_min (分钟线)                                 │
└─────────────────────────────────────────────────────────────┘
                          ↓ (完成后触发)
┌─────────────────────────────────────────────────────────────┐
│                    第 2 层：财务数据                          │
│  (并行执行，依赖第 1 层)                                       │
│  ├── job_financial_profit (利润表)                          │
│  ├── job_financial_balance (资产负债表)                     │
│  ├── job_financial_cashflow (现金流量表)                    │
│  ├── job_financial_growth (成长能力)                        │
│  ├── job_financial_operation (运营能力)                     │
│  ├── job_financial_dupont (杜邦分析)                        │
│  ├── job_financial_forecast (业绩预告)                      │
│  └── job_financial_dividend (分红送配)                      │
└─────────────────────────────────────────────────────────────┘
                          ↓ (完成后触发)
┌─────────────────────────────────────────────────────────────┐
│                    第 3 层：扩展数据                          │
│  (并行执行，依赖第 2 层)                                       │
│  ├── job_eastmoney_moneyflow (资金流向)                     │
│  ├── job_eastmoney_north (北向资金)                         │
│  ├── job_eastmoney_shareholder (股东人数)                   │
│  ├── job_eastmoney_concept (概念板块)                       │
│  └── job_eastmoney_analyst (分析师评级)                     │
└─────────────────────────────────────────────────────────────┘
                          ↓ (完成后触发)
┌─────────────────────────────────────────────────────────────┐
│                    第 4 层：指标计算                          │
│  (并行执行，依赖第 3 层)                                       │
│  ├── job_indicator_macd (MACD 指标)                          │
│  ├── job_indicator_rsi (RSI 指标)                           │
│  ├── job_indicator_boll (布林线)                            │
│  ├── job_indicator_cci (CCI 指标)                           │
│  ├── job_indicator_obv (OBV 指标)                           │
│  └── job_indicator_adx (ADX 指标)                           │
└─────────────────────────────────────────────────────────────┘
                          ↓ (完成后触发)
┌─────────────────────────────────────────────────────────────┐
│                    第 5 层：多因子与策略                      │
│  (串行执行，依赖第 4 层)                                       │
│  └── job_multi_factor (多因子打分)                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 任务配置清单

### 执行器配置

| 配置项 | 值 |
|--------|-----|
| AppName | `stock-data-executor` |
| 执行器名称 | 股票数据采集执行器 |
| 执行器类型 | 自动注册 |
| 注册方式 | 自动注册 |

---

### 任务 1：基础行情数据

#### job_stock_daily
| 配置项 | 值 |
|--------|-----|
| 执行器 | stock-data-executor |
| JobHandler | `run_daily_collection` |
| 运行模式 | BEAN |
| 触发类型 | CRON |
| CRON | `0 0 18 * * ?` (每天 18:00) |
| 运行参数 | `date_type=d` |

#### job_stock_weekly
| 配置项 | 值 |
|--------|-----|
| 执行器 | stock-data-executor |
| JobHandler | `run_daily_collection` |
| 运行模式 | BEAN |
| 触发类型 | CRON |
| CRON | `0 30 18 * * ?` (每天 18:30) |
| 运行参数 | `date_type=w` |

#### job_stock_monthly
| 配置项 | 值 |
|--------|-----|
| 执行器 | stock-data-executor |
| JobHandler | `run_daily_collection` |
| 运行模式 | BEAN |
| 触发类型 | CRON |
| CRON | `0 0 19 * * ?` (每天 19:00) |
| 运行参数 | `date_type=m` |

#### job_stock_min
| 配置项 | 值 |
|--------|-----|
| 执行器 | stock-data-executor |
| JobHandler | `run_min_collection` |
| 运行模式 | BEAN |
| 触发类型 | CRON |
| CRON | `0 */30 9-15 * * ?` (交易日 9:00-15:00 每 30 分钟) |
| 运行参数 | `date_type=min` |

---

### 任务 2：财务数据

#### job_financial_profit
| 配置项 | 值 |
|--------|-----|
| 执行器 | stock-data-executor |
| JobHandler | `run_financial_collection` |
| 运行模式 | BEAN |
| 触发类型 | CRON |
| CRON | `0 0 20 * * ?` (每天 20:00) |
| 运行参数 | `data_type=profit` |
| 子任务 | 无 |

#### job_financial_balance
| 配置项 | 值 |
|--------|-----|
| 执行器 | stock-data-executor |
| JobHandler | `run_financial_collection` |
| 运行模式 | BEAN |
| 触发类型 | CRON |
| CRON | `0 0 20 * * ?` (每天 20:00) |
| 运行参数 | `data_type=balance` |

#### job_financial_cashflow
| 配置项 | 值 |
|--------|-----|
| 执行器 | stock-data-executor |
| JobHandler | `run_financial_collection` |
| 运行模式 | BEAN |
| 触发类型 | CRON |
| CRON | `0 0 20 * * ?` (每天 20:00) |
| 运行参数 | `data_type=cashflow` |

#### job_financial_growth
| 配置项 | 值 |
|--------|-----|
| 执行器 | stock-data-executor |
| JobHandler | `run_financial_collection` |
| 运行模式 | BEAN |
| 触发类型 | CRON |
| CRON | `0 0 20 * * ?` (每天 20:00) |
| 运行参数 | `data_type=growth` |

#### job_financial_operation
| 配置项 | 值 |
|--------|-----|
| 执行器 | stock-data-executor |
| JobHandler | `run_financial_collection` |
| 运行模式 | BEAN |
| 触发类型 | CRON |
| CRON | `0 0 20 * * ?` (每天 20:00) |
| 运行参数 | `data_type=operation` |

#### job_financial_dupont
| 配置项 | 值 |
|--------|-----|
| 执行器 | stock-data-executor |
| JobHandler | `run_financial_collection` |
| 运行模式 | BEAN |
| 触发类型 | CRON |
| CRON | `0 0 20 * * ?` (每天 20:00) |
| 运行参数 | `data_type=dupont` |

#### job_financial_forecast
| 配置项 | 值 |
|--------|-----|
| 执行器 | stock-data-executor |
| JobHandler | `run_financial_collection` |
| 运行模式 | BEAN |
| 触发类型 | CRON |
| CRON | `0 0 20 * * ?` (每天 20:00) |
| 运行参数 | `data_type=forecast` |

#### job_financial_dividend
| 配置项 | 值 |
|--------|-----|
| 执行器 | stock-data-executor |
| JobHandler | `run_financial_collection` |
| 运行模式 | BEAN |
| 触发类型 | CRON |
| CRON | `0 0 20 * * ?` (每天 20:00) |
| 运行参数 | `data_type=dividend` |

---

### 任务 3：东方财富扩展数据

#### job_eastmoney_moneyflow
| 配置项 | 值 |
|--------|-----|
| 执行器 | stock-data-executor |
| JobHandler | `run_eastmoney_collection` |
| 运行模式 | BEAN |
| 触发类型 | CRON |
| CRON | `0 0 21 * * ?` (每天 21:00) |
| 运行参数 | `data_type=moneyflow` |

#### job_eastmoney_north
| 配置项 | 值 |
|--------|-----|
| 执行器 | stock-data-executor |
| JobHandler | `run_eastmoney_collection` |
| 运行模式 | BEAN |
| 触发类型 | CRON |
| CRON | `0 0 21 * * ?` (每天 21:00) |
| 运行参数 | `data_type=north` |

#### job_eastmoney_shareholder
| 配置项 | 值 |
|--------|-----|
| 执行器 | stock-data-executor |
| JobHandler | `run_eastmoney_collection` |
| 运行模式 | BEAN |
| 触发类型 | CRON |
| CRON | `0 0 21 * * ?` (每天 21:00) |
| 运行参数 | `data_type=shareholder` |

#### job_eastmoney_concept
| 配置项 | 值 |
|--------|-----|
| 执行器 | stock-data-executor |
| JobHandler | `run_eastmoney_collection` |
| 运行模式 | BEAN |
| 触发类型 | CRON |
| CRON | `0 0 21 * * ?` (每天 21:00) |
| 运行参数 | `data_type=concept` |

#### job_eastmoney_analyst
| 配置项 | 值 |
|--------|-----|
| 执行器 | stock-data-executor |
| JobHandler | `run_eastmoney_collection` |
| 运行模式 | BEAN |
| 触发类型 | CRON |
| CRON | `0 0 21 * * ?` (每天 21:00) |
| 运行参数 | `data_type=analyst` |

---

### 任务 4：技术指标计算

#### job_indicator_all
| 配置项 | 值 |
|--------|-----|
| 执行器 | stock-data-executor |
| JobHandler | `run_indicator_calculation` |
| 运行模式 | BEAN |
| 触发类型 | CRON |
| CRON | `0 0 22 * * ?` (每天 22:00) |
| 运行参数 | `--all` |

---

### 任务 5：多因子打分

#### job_multi_factor
| 配置项 | 值 |
|--------|-----|
| 执行器 | stock-data-executor |
| JobHandler | `run_multi_factor` |
| 运行模式 | BEAN |
| 触发类型 | CRON |
| CRON | `0 0 23 * * ?` (每天 23:00) |
| 运行参数 | 无 |

---

## 执行器代码

执行器代码位于：`stock_learning/xxljob/executor.py`

### 运行方式

```bash
# 开发环境
cd /home/fan/.openclaw/workspace/stock_learning
python3 xxljob/executor.py

# 生产环境（使用 systemd）
sudo systemctl start stock-xxljob-executor
sudo systemctl enable stock-xxljob-executor
```

---

## 部署步骤

### 1. XXL-JOB 调度中心部署

```bash
# 下载 XXL-JOB
wget https://github.com/xuxueli/xxl-job/releases/download/2.4.0/xxl-job-2.4.0.zip
unzip xxl-job-2.4.0.zip

# 配置调度中心
cd xxl-job-2.4.0/xxl-job-admin
vim conf/application.properties
# 修改数据库连接、端口等

# 启动调度中心
./bin/start.sh
```

访问：http://localhost:8080/xxl-job-admin

### 2. 执行器部署

```bash
# 安装依赖
pip3 install xxl-job-python

# 配置执行器
cd /home/fan/.openclaw/workspace/stock_learning/xxljob
vim config.py

# 启动执行器
python3 executor.py
```

### 3. 配置任务

登录 XXL-JOB 管理后台，按照上面的任务配置清单逐个创建任务。

---

## 监控与告警

### 1. 任务监控

- XXL-JOB 管理后台查看任务执行状态
- 日志路径：`/home/fan/.openclaw/workspace/stock_learning/logs/xxljob/`

### 2. 告警配置

在 XXL-JOB 管理后台配置告警：
- 任务失败告警
- 任务超时告警
- 邮件/钉钉/企业微信通知

---

## 故障处理

### 常见问题

1. **任务执行失败**
   - 检查执行器日志
   - 检查数据库连接
   - 检查数据源 API 可用性

2. **任务超时**
   - 调整超时时间
   - 优化 SQL 查询
   - 增加批处理大小

3. **数据重复**
   - 检查唯一索引
   - 检查断点重试逻辑

---

## 维护手册

### 日常维护

1. 每天检查任务执行日志
2. 每周检查数据完整性
3. 每月清理过期日志

### 数据校验

```bash
# 检查数据完整性
python3 xxljob/validate_data.py

# 修复缺失数据
python3 xxljob/repair_missing_data.py
```

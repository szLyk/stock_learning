# stock_individual_info 采集说明

## 接口信息

**数据源**: AKShare - stock_individual_info_em (东方财富)  
**接口地址**: https://quote.eastmoney.com/concept/sh603777.html?from=classic  
**更新频率**: 建议每日或每周更新  
**字段列表**:

| 字段名 | 中文名 | 类型 | 说明 |
|--------|--------|------|------|
| 最新 | 最新价格 | DECIMAL(10,2) | 当前股价 |
| 股票代码 | 股票代码 | VARCHAR(10) | 6位代码 |
| 股票简称 | 股票简称 | VARCHAR(50) | 中文名称 |
| 总股本 | 总股本 | DECIMAL(20,2) | 单位：股 |
| 流通股 | 流通股本 | DECIMAL(20,2) | 单位：股 |
| 总市值 | 总市值 | DECIMAL(20,2) | 单位：元 |
| 流通市值 | 流通市值 | DECIMAL(20,2) | 单位：元 |
| 行业 | 所属行业 | VARCHAR(50) | 行业分类 |
| 上市时间 | 上市日期 | DATE | 格式：YYYYMMDD |

## 使用方法

### 1. 测试模式（推荐先测试）

```bash
# 测试少量股票，验证接口和断点续传
python scripts/fetch_stock_individual_info.py --test --test-count 5
```

### 2. 查看状态

```bash
python scripts/fetch_stock_individual_info.py --status
```

### 3. 正式采集

```bash
# 全量采集
python scripts/fetch_stock_individual_info.py --all

# 自定义参数
python scripts/fetch_stock_individual_info.py --all --batch 30 --delay 1.0 --retries 5
```

### 4. 断点续传

如果采集中断，直接再次运行即可继续：

```bash
python scripts/fetch_stock_individual_info.py --all
```

系统会自动从 Redis 获取上次未处理完的股票列表。

### 5. 清除重新采集

```bash
python scripts/fetch_stock_individual_info.py --reset
python scripts/fetch_stock_individual_info.py --all
```

## 断点续传原理

```
┌─────────────┐
│   开始采集   │
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│ Redis 有待处理列表？ │
└──────┬──────┬────────┘
       │      │
     是│      │否
       │      │
       │      ▼
       │  ┌─────────────┐
       │  │ 从数据库获取 │
       │  │ 全部股票     │
       │  └──────┬──────┘
       │         │
       │         ▼
       │  ┌─────────────────┐
       │  │ 初始化 Redis    │
       │  │ 待处理列表      │
       │  └──────┬──────────┘
       │         │
       ▼         ▼
┌─────────────────────┐
│ 处理每只股票        │
│ - 获取数据          │
│ - 保存数据库        │
│ - 标记 Redis 已处理 │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 采集完成/中断        │
└─────────────────────┘
```

## Redis Key 格式

```
individual_info:stock_data:2026-04-02:unprocessed  # 待处理股票集合
```

## 常见问题

### Q: 接口连接失败怎么办？

A: AKShare 接口可能被限流，建议：
1. 增加 `--delay` 参数到 1-2 秒
2. 分批次采集，避开高峰期
3. 使用代理或等待一段时间后重试

### Q: 如何验证断点续传？

A: 运行测试脚本：
```bash
python scripts/test_resume.py --redis
```

### Q: 数据存储在哪里？

A: 
- MySQL: `stock_individual_info` 表
- Redis: 断点续传临时数据（自动清理）

## 定时任务配置

### Crontab 示例

```bash
# 每周日早上 6 点更新
0 6 * * 0 cd /home/fan/.openclaw/workspace/stock_learning && python scripts/fetch_stock_individual_info.py --all >> logs/individual_info.log 2>&1
```

### XXL-JOB 配置

参考 `stock-xxljob-scheduler` 技能
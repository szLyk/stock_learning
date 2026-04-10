# 指数分钟线数据采集方案

## 设计日期：2026-04-10

## 背景

东方财富提供指数分钟线数据接口，免费可用。需要爬取 2010年至今的历史分钟线数据。

---

## 数据源：东方财富

### 接口地址

```
http://push2his.eastmoney.com/api/qt/stock/kline/get
```

### 关键参数

| 参数 | 说明 |
|------|------|
| `secid` | 指数代码（格式：市场.代码，如 1.000001） |
| `klt` | K线类型（5=5分钟，15=15分钟，30=30分钟，60=60分钟） |
| `lmt` | 返回条数（单次最多约1000条） |
| `fqt` | 复权类型（1=不复权） |

### 反爬策略

- **请求间隔**：10-30秒随机
- **单次上限**：约1000条
- **分段策略**：按时间分段请求，避免触发限制

---

## 表结构设计（方案一：单表多频率）

```sql
CREATE TABLE `index_stock_history_min_price` (
  `id` int NOT NULL AUTO_INCREMENT,
  `stock_code` varchar(20) NOT NULL COMMENT '指数代码（如000001）',
  `stock_date` date NOT NULL COMMENT '交易日期',
  `stock_time` varchar(20) NOT NULL COMMENT '时间点（如09:30、10:00）',
  `min_type` int NOT NULL COMMENT '分钟线类型：5=5分钟,15=15分钟,30=30分钟,60=60分钟',
  `open_price` decimal(10,4) DEFAULT NULL COMMENT '开盘价',
  `high_price` decimal(10,4) DEFAULT NULL COMMENT '最高价',
  `low_price` decimal(10,4) DEFAULT NULL COMMENT '最低价',
  `close_price` decimal(10,4) DEFAULT NULL COMMENT '收盘价',
  `trading_volume` decimal(20,4) DEFAULT NULL COMMENT '成交量',
  `trading_amount` decimal(20,4) DEFAULT NULL COMMENT '成交额',
  `amplitude` decimal(10,4) DEFAULT NULL COMMENT '振幅（%）',
  `change_pct` decimal(10,4) DEFAULT NULL COMMENT '涨跌幅（%）',
  `change_amt` decimal(10,4) DEFAULT NULL COMMENT '涨跌额',
  `market_type` varchar(5) NOT NULL COMMENT '市场类型：sh|sz',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_index_min_price` (`stock_code`, `market_type`, `stock_date`, `stock_time`, `min_type`) USING BTREE,
  KEY `idx_stock_date` (`stock_date`) USING BTREE,
  KEY `idx_stock_code_date` (`stock_code`, `stock_date`) USING BTREE,
  KEY `idx_min_type` (`min_type`) USING BTREE,
  KEY `idx_stock_min_type` (`stock_code`, `min_type`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='指数分钟线数据表';
```

---

## 待爬取指数清单

| 指数代码 | 指数名称 | 市场类型 | secid |
|----------|----------|----------|-------|
| 000001 | 上证指数 | sh | 1.000001 |
| 000300 | 沪深300 | sh | 1.000300 |
| 000016 | 上证50 | sh | 1.000016 |
| 000905 | 中证500 | sh | 1.000905 |
| 399001 | 深证成指 | sz | 0.399001 |
| 399006 | 创业板指 | sz | 0.399006 |
| 399005 | 中小板指 | sz | 0.399005 |

---

## 爬取时间范围

- **起始日期**：2010-01-01
- **结束日期**：当前日期
- **频率**：5分钟、15分钟、30分钟、60分钟

---

## 数据量预估

| 频率 | 单指数条数 | 7指数总条数 |
|------|-----------|-----------|
| 5分钟 | 约192,000 | 约134万 |
| 15分钟 | 约64,000 | 约45万 |
| 30分钟 | 约32,000 | 约22万 |
| 60分钟 | 约16,000 | 约11万 |
| **总计** | | **约212万条** |

---

## 爬取耗时预估

| 频率 | 分段数 | 单指数耗时 | 7指数总耗时 |
|------|--------|-----------|-----------|
| 5分钟 | 192段 | 约64分钟 | 约7.5小时 |
| 15分钟 | 64段 | 约20分钟 | 约2.3小时 |
| 30分钟 | 32段 | 约10分钟 | 约1.2小时 |
| 60分钟 | 16段 | 约5分钟 | 约0.6小时 |
| **总计** | | | **约11.6小时** |

---

## 注意事项

### ⚠️ 频率控制（关键）

- **间隔时间**：10-30秒随机
- **实现方式**：每次请求后等待随机秒数
- **代码要求**：
  ```python
  import random
  import time
  
  # 每次请求后等待
  wait_seconds = random.randint(10, 30)
  time.sleep(wait_seconds)
  ```

### ⚠️ 测试时特别注意

- 测试阶段也要遵守频率限制
- 不要连续快速请求
- 测试完成后等待足够时间再开始正式爬取

---

## 实现任务清单

1. 创建数据库表 `index_stock_history_min_price`
2. 编写爬虫脚本：
   - 分段请求逻辑
   - 10-30秒随机间隔
   - 异常重试机制
   - 进度记录（断点续传）
3. 数据入库逻辑
4. 测试脚本（遵守频率限制）
5. 正式爬取历史数据
6. 定时任务：每日增量更新

---

## 状态

- 方案设计完成 ✅
- 待 Claude Code 实现
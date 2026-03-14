# 多因子模型使用指南

**创建时间:** 2026-03-14  
**版本:** v1.0

---

## 📊 多因子模型框架

### 因子体系

| 因子类别 | 权重 | 具体因子 | 数据来源 |
|----------|------|----------|----------|
| **价值因子** | 25% | PE 分位数、PB 分位数 | `stock_history_date_price` |
| **质量因子** | 25% | ROE、毛利率 | `stock_profit_data` |
| **成长因子** | 20% | 营收增速、净利润增速 | `stock_profit_data` |
| **动量因子** | 15% | 60 日动量、5 日反转 | `stock_history_date_price` |
| **资金流向** | 10% | 主力净流入、北向资金 | `stock_capital_flow` (新增) |
| **分析师预期** | 5% | 评级打分、EPS 超预期 | `stock_analyst_expectation` (新增) |

### 打分逻辑

```
综合得分 = 价值得分×0.25 + 质量得分×0.25 + 成长得分×0.20 + 动量得分×0.15 + 资金得分×0.10 + 预期得分×0.05
```

每个因子得分通过**百分位排名**标准化到 0-100 分。

---

## 🗄️ 数据库表结构

### 新增表

| 表名 | 说明 | 更新频率 |
|------|------|----------|
| `stock_capital_flow` | 资金流向表 | 每日 |
| `stock_analyst_expectation` | 分析师预期表 | 每日 |
| `stock_shareholder_info` | 股东筹码表 | 季度 |
| `stock_concept` | 概念板块表 | 每周 |
| `stock_factor_score` | 多因子打分表 | 每日 |
| `stock_factor_ic` | 因子 IC 值表 | 每日 |
| `stock_selection_result` | 选股结果表 | 每日 |

### 核心字段说明

**stock_factor_score:**
- `value_score` - 价值因子得分
- `quality_score` - 质量因子得分
- `growth_score` - 成长因子得分
- `momentum_score` - 动量因子得分
- `capital_score` - 资金流向得分
- `expectation_score` - 分析师预期得分
- `total_score` - 综合得分
- `total_rank` - 全市场排名

---

## 🚀 快速开始

### 1. 初始化数据库表

```bash
mysql -h 192.168.1.109 -P 3306 -u root -p123456 stock < sql/multi_factor_tables.sql
```

### 2. 采集扩展数据（资金流向、分析师预期）

```bash
cd /home/fan/.openclaw/workspace/stock_learning
python src/utils/baostock_extension.py
```

### 3. 运行因子分析

```bash
python src/utils/multi_factor_tool.py
```

### 4. 执行选股策略

```bash
# 每日运行（采集 + 分析 + 选股）
python src/strategy/multi_factor_strategy.py --mode daily

# 只选股，不采集数据
python src/strategy/multi_factor_strategy.py --mode daily --no-collect

# 回测
python src/strategy/multi_factor_strategy.py --mode backtest \
  --start-date 2025-01-01 \
  --end-date 2026-03-14 \
  --top-n 50 \
  --hold-days 5
```

---

## 📈 常用查询

### 查看最新选股结果

```sql
SELECT * FROM stock.v_stock_factor_ranking 
ORDER BY total_score DESC 
LIMIT 50;
```

### 查看历史选股表现

```sql
SELECT 
    strategy_name,
    select_date,
    COUNT(*) as stock_count,
    AVG(return_rate) as avg_return,
    SUM(CASE WHEN return_rate > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as win_rate
FROM stock.stock_selection_result
WHERE status = 'sold'
GROUP BY strategy_name, select_date
ORDER BY select_date DESC;
```

### 查看因子 IC 值

```sql
SELECT 
    factor_name,
    AVG(ic_value) as avg_ic,
    AVG(ic_ir) as avg_ir,
    COUNT(*) as calc_days
FROM stock.stock_factor_ic
GROUP BY factor_name
ORDER BY avg_ic DESC;
```

---

## ⚙️ 配置说明

### 因子权重调整

编辑 `src/utils/multi_factor_tool.py`:

```python
self.factor_weights = {
    'value': 0.25,        # 价值因子
    'quality': 0.25,      # 质量因子
    'growth': 0.20,       # 成长因子
    'momentum': 0.15,     # 动量因子
    'capital': 0.10,      # 资金流向因子
    'expectation': 0.05   # 分析师预期因子
}
```

### 选股参数

```bash
# 选前 50 只股票，最低分数 60 分
python src/strategy/multi_factor_strategy.py --top-n 50

# 持有 5 天后调仓
python src/strategy/multi_factor_strategy.py --hold-days 5
```

---

## 📊 策略优化建议

### 1. 动态因子加权

根据市场状态调整因子权重：
- **牛市**: 增加成长、动量权重
- **熊市**: 增加价值、质量权重
- **震荡市**: 均衡配置

### 2. 行业中性化

避免选股集中在某个行业：
```sql
-- 行业内排名
SELECT stock_code, total_score,
       RANK() OVER (PARTITION BY industry ORDER BY total_score DESC) as industry_rank
FROM stock_factor_score;
```

### 3. 风险控制

- 单只股票最大仓位：10%
- 单一行业最大仓位：30%
- 止损：-8%
- 止盈：+15%

### 4. 因子 IC 监控

定期计算因子 IC 值，剔除失效因子：
- IC > 0.05: 有效因子
- IC < 0.02: 考虑剔除
- IC 连续 3 个月为负：立即剔除

---

## 🔧 代码结构

```
stock_learning/
├── sql/
│   └── multi_factor_tables.sql      # 数据库表结构
├── src/
│   ├── utils/
│   │   ├── baosock_tool.py          # 基础数据采集
│   │   ├── baostock_extension.py    # 扩展数据采集（新增）
│   │   ├── indicator_calculation_tool.py  # 技术指标计算
│   │   ├── multi_factor_tool.py     # 多因子分析（新增）
│   │   └── mysql_tool.py            # 数据库工具
│   └── strategy/
│       └── multi_factor_strategy.py # 多因子策略（新增）
└── docs/
    └── MULTI_FACTOR_GUIDE.md        # 使用指南
```

---

## ⚠️ 注意事项

1. **数据质量**: 确保 baostock 数据采集完整，特别是 PE/PB 数据
2. **回测陷阱**: 避免未来函数，确保因子计算只用当时可得数据
3. **交易成本**: 回测中加入印花税、佣金、滑点
4. **过拟合风险**: 不要过度优化参数，保持逻辑简洁
5. **定期调优**: 每季度检查因子 IC 值，调整权重

---

## 📝 待办事项

- [ ] 补充北向资金数据采集（需其他数据源）
- [ ] 添加股东人数数据采集
- [ ] 实现行业中性化
- [ ] 添加因子 IC 自动计算
- [ ] 完善回测报告（夏普比率、最大回撤等）
- [ ] 添加可视化（收益曲线、因子暴露等）

---

_最后更新：2026-03-14_

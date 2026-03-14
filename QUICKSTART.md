# 快速开始 - 财务数据采集

**更新时间:** 2026-03-14 23:51

---

## ✅ 最新修复

- ✅ 修复利润表字段大小写问题 (`MBRevenue` → `mb_revenue`)
- ✅ 增强字段检测逻辑
- ✅ 测试通过

---

## 🚀 快速开始

### 1. 运行完整采集

```bash
cd /home/fan/.openclaw/workspace/stock_learning
export PYTHONPATH=/home/fan/.openclaw/workspace/stock_learning:$PYTHONPATH

# 采集所有财务数据（预计 30-40 分钟）
python3 src/utils/baostock_financial.py
```

### 2. 分类型采集（推荐）

```bash
# 第一天：采集利润表
python3 src/utils/baostock_financial.py profit

# 第二天：采集资产负债表
python3 src/utils/baostock_financial.py balance

# 第三天：采集现金流量表
python3 src/utils/baostock_financial.py cashflow

# ...以此类推
```

### 3. 单只股票测试

```bash
python3 -c "
from src.utils.baostock_financial import BaostockFinancialFetcher
fetcher = BaostockFinancialFetcher()
df = fetcher.fetch_profit_data('sh.601398', year=2025)
print(f'获取到 {len(df)} 条记录')
print(df.head())
fetcher.close()
"
```

---

## 📊 数据采集顺序建议

**推荐顺序:**
1. **profit** - 利润表（最核心）
2. **balance** - 资产负债表
3. **cashflow** - 现金流量表
4. **growth** - 成长能力
5. **operation** - 运营能力
6. **dupont** - 杜邦分析
7. **forecast** - 业绩预告
8. **dividend** - 分红送配

---

## ⏱️ 预计时间

| 数据类型 | 500 只股票 | 全部 A 股 (5000+) |
|----------|------------|-------------------|
| 单类数据 | ~5-10 分钟 | ~50-60 分钟 |
| 全部 8 类 | ~40-80 分钟 | ~8-10 小时 |

---

## 📝 监控采集进度

### 查看日志

```bash
tail -f logs/stock_project/baostock_financial_error.log
```

### 查看数据库

```sql
-- 查看已采集数据量
SELECT COUNT(*) FROM stock_profit_data;

-- 查看采集进度
SELECT 
    COUNT(DISTINCT stock_code) as stock_count,
    YEAR(statistic_date) as year,
    season
FROM stock_profit_data
GROUP BY year, season
ORDER BY year DESC, season DESC;
```

### 查看 Redis 队列

```bash
# 查看待采集股票数量
redis-cli SCARD baostock:profit

# 查看待采集股票列表
redis-cli SMEMBERS baostock:profit | head -20
```

---

## 🔧 常见问题

### Q: 采集中断了怎么办？

**A:** 直接重新运行即可，Redis 会记住进度：
```bash
python3 src/utils/baostock_financial.py profit
```

### Q: 如何清空重采？

**A:** 
```sql
-- 清空数据
TRUNCATE TABLE stock_profit_data;
TRUNCATE TABLE stock_performance_update_record;

-- 清空 Redis
redis-cli DEL baostock:profit baostock:balance ...

# 重新采集
python3 src/utils/baostock_financial.py
```

### Q: 如何只采集某一年？

**A:** 修改代码中的 `years` 参数：
```python
# 只采集 2025 年
fetcher.batch_fetch_with_retry('profit', years=[2025], max_retries=3)
```

---

## 📚 相关文档

- [财务 Skill 文档](skills/baostock-financial/SKILL.md)
- [测试报告](docs/FINANCIAL_DATA_TEST_REPORT.md)
- [Baostock API 参考](docs/BAOSTOCK_API_REFERENCE.md)

---

_最后更新：2026-03-14 23:51_

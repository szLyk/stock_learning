# 修复中文乱码 SQL 脚本

**更新时间:** 2026-03-15 00:10

---

## 📋 修复的表

| 表名 | 说明 |
|------|------|
| `update_eastmoney_record` | 东方财富数据采集记录 |
| `stock_performance_update_record` | 财务数据采集记录 |
| `stock_capital_flow` | 资金流向表 |
| `stock_analyst_expectation` | 分析师预期表 |
| `stock_shareholder_info` | 股东筹码表 |
| `stock_concept` | 概念板块表 |
| `stock_factor_score` | 多因子打分表 |

---

## 🚀 执行方法

### 方式 1: 修复所有表（推荐）

```bash
mysql -h 192.168.1.109 -P 3306 -u root stock \
  --default-character-set=utf8mb4 \
  < sql/fix_all_tables_charset.sql
```

### 方式 2: 单独修复东方财富记录表

```bash
mysql -h 192.168.1.109 -P 3306 -u root stock \
  --default-character-set=utf8mb4 \
  < sql/fix_eastmoney_record.sql
```

### 方式 3: 交互式执行

```bash
mysql -h 192.168.1.109 -P 3306 -u root stock --default-character-set=utf8mb4

mysql> SOURCE /home/fan/.openclaw/workspace/stock_learning/sql/fix_all_tables_charset.sql;
```

---

## ✅ 验证修复结果

```bash
mysql -h 192.168.1.109 -P 3306 -u root stock --default-character-set=utf8mb4 -e "
SHOW CREATE TABLE update_eastmoney_record\G
" | grep -E "(COMMENT|DEFAULT CHARSET)"
```

**期望输出:**
```
COMMENT='股票代码'
COMMENT='资金流向最后更新日期'
DEFAULT CHARSET=utf8mb4
```

---

## ⚠️ 注意事项

1. **必须指定字符集**: `--default-character-set=utf8mb4`
2. **会删除旧表**: 脚本包含 `DROP TABLE IF EXISTS`
3. **数据备份**: 执行前建议备份重要数据
4. **执行时间**: 约 1-2 分钟

---

## 📚 相关文档

- [MySQL 字符集指南](../docs/MYSQL_CHARSET_GUIDE.md)
- [财务数据表结构](financial_tables.sql)

---

_最后更新：2026-03-15_

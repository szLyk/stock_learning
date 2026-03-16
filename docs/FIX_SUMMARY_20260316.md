# 财务数据采集问题修复总结

## 📅 修复日期
2026-03-16

## 🐛 问题描述

运行 Baostock 扩展数据采集时出现以下错误：

```
2026-03-16 01:31:52 - ERROR - 600000: 批量入库失败：(1366, "Incorrect decimal value: '' for column 'gp_margin' at row 1")
2026-03-16 01:31:52 - ERROR - 600000: 批量入库失败：(1054, "Unknown column 'current_ratio' in 'field list'")
2026-03-16 01:31:52 - ERROR - 600000: 批量入库失败：(1054, "Unknown column 'yoy_equity' in 'field list'")
2026-03-16 01:31:52 - ERROR - 600000: 批量入库失败：(1054, "Unknown column 'nr_turn_ratio' in 'field list'")
2026-03-16 01:31:52 - ERROR - 600000: 批量入库失败：(1054, "Unknown column 'dupont_roe' in 'field list'")
2026-03-16 01:31:52 - ERROR - 获取业绩预告异常 sh.600000: query_forecast_report() got an unexpected keyword argument 'year'
```

## 🔍 根本原因

### 1. 数据库表结构缺失字段
`update_financial_tables.sql` 脚本未执行，导致 4 个表缺少关键字段：
- **stock_balance_data**: 缺少 `current_ratio`, `quick_ratio`, `cash_ratio` 等 6 个字段
- **stock_growth_data**: 缺少 `yoy_equity`, `yoy_asset`, `yoy_ni` 等 5 个字段
- **stock_operation_data**: 缺少 `nr_turn_ratio`, `nr_turn_days`, `inv_turn_ratio` 等 6 个字段
- **stock_dupont_data**: 缺少 `dupont_roe`, `dupont_asset_sto_equity` 等 8 个字段

### 2. 数据清洗缺失
Baostock 返回的数据中包含空字符串 `''`，直接入库导致 MySQL DECIMAL 类型报错。

### 3. API 参数错误
`query_forecast_report()` 接口不支持 `year` 参数，但代码中错误地传递了该参数。

## ✅ 修复方案

### 修复 1：更新数据库表结构
**文件**: `sql/update_financial_tables.sql`

执行方式：
```bash
mysql -h 192.168.1.109 -P 3306 -u root -p stock < sql/update_financial_tables.sql
```

### 修复 2：添加数据清洗功能
**文件**: 
- `src/utils/baostock_extension.py`
- `src/utils/baostock_financial.py`

新增 `_clean_dataframe()` 方法：
```python
def _clean_dataframe(self, df):
    """清洗 DataFrame，将空字符串、'None' 等无效值转换为 None"""
    for col in df.columns:
        df[col] = df[col].apply(lambda x: None if (isinstance(x, str) and (x == '' or x == 'None' or x.lower() == 'nan')) or (isinstance(x, float) and pd.isna(x)) else x)
    return df
```

在入库前调用：
```python
# 数据清洗：将空字符串转换为 None
df = self._clean_dataframe(df)
rows = self.mysql_manager.batch_insert_or_update(target_table, df, ['stock_code', 'statistic_date'])
```

### 修复 3：修复业绩预告接口调用
**文件**: 
- `src/utils/baostock_extension.py` (第 316 行)
- `src/utils/baostock_financial.py` (第 292 行)

修改前：
```python
rs = bs.query_forecast_report(code=stock_code, year=year)
```

修改后：
```python
# 注意：query_forecast_report 不支持 year 参数，返回所有历史数据
rs = bs.query_forecast_report(code=stock_code)
```

## 📝 新增文件

1. **docs/FIX_DATA_COLLECTION_ISSUES.md** - 详细修复指南
2. **sql/verify_financial_tables.sql** - 表结构验证脚本
3. **tests/test_data_cleaning.py** - 数据清洗测试脚本
4. **scripts/fix_data_collection.sh** - 一键修复脚本

## 🚀 执行步骤

### 方法一：一键修复（推荐）
```bash
cd /home/fan/.openclaw/workspace/stock_learning
./scripts/fix_data_collection.sh
```

### 方法二：手动执行

#### 步骤 1：更新数据库表结构
```bash
mysql -h 192.168.1.109 -P 3306 -u root -p stock < sql/update_financial_tables.sql
```

#### 步骤 2：验证表结构
```bash
mysql -h 192.168.1.109 -P 3306 -u root -p stock < sql/verify_financial_tables.sql
```

#### 步骤 3：运行测试
```bash
cd /home/fan/.openclaw/workspace/stock_learning
python tests/test_data_cleaning.py --clean
python tests/test_data_cleaning.py --stock sh.600000
```

#### 步骤 4：清理 Redis（可选）
```bash
redis-cli
> DEL baostock:extension:stock_data:2026-03-16:unprocessed
> EXIT
```

#### 步骤 5：重新运行采集
```bash
cd /home/fan/.openclaw/workspace/stock_learning
python src/utils/baostock_extension.py
```

## ✅ 验证清单

- [ ] 数据库表结构已更新（执行 verify_financial_tables.sql）
- [ ] 数据清洗测试通过（执行 test_data_cleaning.py --clean）
- [ ] 单只股票采集测试通过（执行 test_data_cleaning.py --stock sh.600000）
- [ ] 完整数据采集无错误（查看日志）

## 📊 预期结果

修复后，数据采集应该：
1. ✅ 不再出现 "Unknown column" 错误
2. ✅ 不再出现 "Incorrect decimal value" 错误
3. ✅ 业绩预告采集正常
4. ✅ 数据正常入库

## 📚 相关文档

- [修复指南](docs/FIX_DATA_COLLECTION_ISSUES.md)
- [Baostock API 参考](docs/BAOSTOCK_API_REFERENCE.md)
- [数据采集 README](README_DATA_COLLECTION.md)

## ⚠️ 注意事项

1. **数据库备份**：执行表结构更新前建议备份数据库
2. **Redis 清理**：如果需要重新采集所有股票，清理 Redis 缓存
3. **日志监控**：运行采集时实时监控日志：`tail -f logs/baostock_extension.log`

## 🔄 后续优化建议

1. **数据验证层**：在入库前增加更严格的数据验证
2. **错误重试机制**：对临时性错误增加自动重试
3. **监控告警**：对采集失败率设置告警阈值
4. **单元测试**：为关键函数添加单元测试

---

**修复状态**: ✅ 已完成代码修复，待执行数据库更新和测试验证

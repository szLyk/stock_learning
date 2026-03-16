# 财务数据采集问题修复指南

## 问题诊断（2026-03-16 日志）

```
ERROR - 600000: 批量入库失败：(1366, "Incorrect decimal value: '' for column 'gp_margin' at row 1")
ERROR - 600000: 批量入库失败：(1054, "Unknown column 'current_ratio' in 'field list'")
ERROR - 600000: 批量入库失败：(1054, "Unknown column 'yoy_equity' in 'field list'")
ERROR - 600000: 批量入库失败：(1054, "Unknown column 'nr_turn_ratio' in 'field list'")
ERROR - 600000: 批量入库失败：(1054, "Unknown column 'dupont_roe' in 'field list'")
ERROR - 获取业绩预告异常 sh.600000: query_forecast_report() got an unexpected keyword argument 'year'
```

## 根本原因

### 1. 数据库表结构缺失字段
**问题**：`update_financial_tables.sql` 脚本未执行，导致以下字段缺失：
- `stock_balance_data`: `current_ratio`, `quick_ratio`, `cash_ratio`, `yoy_liability`, `liability_to_asset`, `asset_to_equity`
- `stock_growth_data`: `yoy_equity`, `yoy_asset`, `yoy_ni`, `yoy_eps_basic`, `yoy_pni`
- `stock_operation_data`: `nr_turn_ratio`, `nr_turn_days`, `inv_turn_ratio`, `inv_turn_days`, `ca_turn_ratio`, `asset_turn_ratio`
- `stock_dupont_data`: `dupont_roe`, `dupont_asset_sto_equity`, `dupont_asset_turn`, `dupont_pnitoni`, `dupont_nitogr`, `dupont_tax_burden`, `dupont_int_burden`, `dupont_ebit_to_gr`

**解决方案**：执行 SQL 更新脚本
```bash
mysql -h 192.168.1.109 -P 3306 -u root -p stock < /home/fan/.openclaw/workspace/stock_learning/sql/update_financial_tables.sql
```

### 2. 数据清洗问题 - 空字符串导致入库失败
**问题**：Baostock 返回的数据中，某些字段可能是空字符串 `''` 而不是 `None`，导致 MySQL DECIMAL 类型入库失败。

**解决方案**：修改 `baostock_extension.py` 和 `baostock_financial.py`，在入库前进行数据清洗：

```python
# 在入库前添加数据清洗步骤
def _clean_dataframe(self, df):
    """清洗 DataFrame，将空字符串转换为 None"""
    for col in df.columns:
        # 将空字符串转换为 None
        df[col] = df[col].apply(lambda x: None if x == '' or x == 'None' or pd.isna(x) else x)
    return df
```

### 3. 业绩预告 API 参数错误
**问题**：`query_forecast_report()` 接口不支持 `year` 参数。

**解决方案**：修改 `fetch_forecast_report` 方法，移除 `year` 参数：

```python
def fetch_forecast_report(self, stock_code):
    """获取业绩预告报告（baostock 支持）"""
    try:
        # 注意：query_forecast_report 不支持 year 参数
        rs = bs.query_forecast_report(code=stock_code)
        
        if rs.error_code != '0':
            return pd.DataFrame()
        
        data_list = []
        while rs.next():
            data_list.append(rs.get_row_data())
        
        if not data_list:
            return pd.DataFrame()
        
        df = pd.DataFrame(data_list, columns=rs.fields)
        df['stock_code'] = df['code'].apply(lambda x: x[-6:] if x else x)
        return df
        
    except Exception as e:
        self.logger.error(f"获取业绩预告异常 {stock_code}: {e}")
        return pd.DataFrame()
```

## 执行步骤

### 步骤 1：更新数据库表结构
```bash
mysql -h 192.168.1.109 -P 3306 -u root -p stock < /home/fan/.openclaw/workspace/stock_learning/sql/update_financial_tables.sql
```

### 步骤 2：验证表结构
```sql
USE stock;

-- 检查资产负债表字段
DESC stock_balance_data;

-- 检查成长能力表字段
DESC stock_growth_data;

-- 检查运营能力表字段
DESC stock_operation_data;

-- 检查杜邦分析表字段
DESC stock_dupont_data;
```

### 步骤 3：修改代码（数据清洗）
修改 `src/utils/baostock_extension.py` 和 `src/utils/baostock_financial.py`，在入库前添加数据清洗。

### 步骤 4：修改业绩预告接口调用
修改 `fetch_forecast_report` 方法，移除 `year` 参数。

### 步骤 5：清理 Redis 并重新采集
```bash
# 清理 Redis 中的待处理股票
redis-cli
> DEL baostock:extension:stock_data:2026-03-16:unprocessed
> EXIT

# 重新运行采集
cd /home/fan/.openclaw/workspace/stock_learning
python src/utils/baostock_extension.py
```

## 预防措施

1. **数据验证**：在入库前始终检查数据类型和格式
2. **表结构版本管理**：使用迁移脚本管理表结构变更
3. **错误日志**：详细记录错误信息，便于快速定位问题
4. **断点续传**：利用 Redis 机制，避免重复采集

## 相关文件

- SQL 脚本：`sql/update_financial_tables.sql`
- 数据采集：`src/utils/baostock_extension.py`
- 财务采集：`src/utils/baostock_financial.py`
- 测试脚本：`tests/test_single_stock.py`

# Baostock 财务接口测试报告

**测试日期**: 2026-03-16  
**测试股票**: sh.600000 (浦发银行)  
**测试年份**: 2025  
**测试方法**: fetch_financial_data

## ✅ 测试结果 - 数据获取

所有 6 个财务接口都能成功获取数据：

| 接口 | 返回数据 | 字段数量 | 字段列表 |
|------|---------|---------|---------|
| **profit** (利润表) | ✅ 1 条 | 12 个 | code, pubDate, statDate, roeAvg, npMargin, gpMargin, netProfit, epsTTM, MBRevenue, totalShare, liqaShare, stock_code |
| **balance** (资产负债表) | ✅ 1 条 | 10 个 | code, pubDate, statDate, currentRatio, quickRatio, cashRatio, YOYLiability, liabilityToAsset, assetToEquity, stock_code |
| **cash_flow** (现金流量表) | ✅ 1 条 | 11 个 | code, pubDate, statDate, CAToAsset, NCAToAsset, tangibleAssetToAsset, ebitToInterest, CFOToOR, CFOToNP, CFOToGr, stock_code |
| **growth** (成长能力) | ✅ 1 条 | 9 个 | code, pubDate, statDate, YOYEquity, YOYAsset, YOYNI, YOYEPSBasic, YOYPNI, stock_code |
| **operation** (运营能力) | ✅ 1 条 | 9 个 | code, pubDate, statDate, NRTurnRatio, NRTurnDays, INVTurnRatio, INVTurnDays, CATurnRatio, AssetTurnRatio, stock_code |
| **dupont** (杜邦分析) | ✅ 1 条 | 12 个 | code, pubDate, statDate, dupontROE, dupontAssetStoEquity, dupontAssetTurn, dupontPnitoni, dupontNitogr, dupontTaxBurden, dupontIntburden, dupontEbittogr, stock_code |

## ✅ 数据清洗测试

所有数据都能成功清洗（空字符串→None）：

| 表名 | NULL 值数量 | 状态 |
|------|-----------|------|
| profit | 2 | ✅ |
| balance | 3 | ✅ |
| cash_flow | 4 | ✅ |
| growth | 0 | ✅ |
| operation | 5 | ✅ |
| dupont | 2 | ✅ |

## ❌ 入库测试 - 数据库表结构问题

### 问题汇总

| 表名 | 状态 | 问题 |
|------|------|------|
| stock_profit_data | ❌ | 缺少 12 个字段 |
| stock_balance_data | ❌ | 缺少 10 个字段 |
| stock_cash_flow_data | ❌ | 表不存在 |
| stock_growth_data | ❌ | 缺少 9 个字段 |
| stock_operation_data | ❌ | 缺少 9 个字段 |
| stock_dupont_data | ❌ | 缺少 12 个字段 |

### 缺失字段详情

#### 1. stock_profit_data 缺失字段
```
publish_date, statistic_date, roe_avg, np_margin, gp_margin, 
net_profit, eps_ttm, mb_revenue, total_share, liqa_share, 
stock_code, season
```

#### 2. stock_balance_data 缺失字段
```
publish_date, statistic_date, current_ratio, quick_ratio, cash_ratio, 
yoy_liability, liability_to_asset, asset_to_equity, stock_code, season
```

#### 3. stock_cash_flow_data
```
❌ 表不存在！需要创建表。
```

#### 4. stock_growth_data 缺失字段
```
publish_date, statistic_date, yoy_equity, yoy_asset, yoy_ni, 
yoy_eps_basic, yoy_pni, stock_code, season
```

#### 5. stock_operation_data 缺失字段
```
publish_date, statistic_date, nr_turn_ratio, nr_turn_days, 
inv_turn_ratio, inv_turn_days, ca_turn_ratio, asset_turn_ratio, 
stock_code, season
```

#### 6. stock_dupont_data 缺失字段
```
publish_date, statistic_date, dupont_roe, dupont_asset_sto_equity, 
dupont_asset_turn, dupont_pnitoni, dupont_nitogr, dupont_tax_burden, 
dupont_int_burden, dupont_ebit_to_gr, stock_code, season
```

## 📋 修复步骤

### 步骤 1：执行数据库表结构同步

```bash
mysql -h 192.168.1.109 -P 3306 -u root -p stock < /home/fan/.openclaw/workspace/stock_learning/sql/sync_baostock_tables.sql
```

### 步骤 2：验证表结构

```bash
mysql -h 192.168.1.109 -P 3306 -u root -p stock -e "
SELECT table_name, COUNT(*) as column_count 
FROM information_schema.columns 
WHERE table_schema = 'stock' 
  AND table_name IN (
    'stock_profit_data',
    'stock_balance_data',
    'stock_cash_flow_data',
    'stock_growth_data',
    'stock_operation_data',
    'stock_dupont_data'
  )
GROUP BY table_name;
"
```

### 步骤 3：重新运行测试

```bash
cd /home/fan/.openclaw/workspace/stock_learning
python3 tests/test_financial_collection.py --stock sh.600000 --year 2025
```

### 步骤 4：测试多只股票（可选）

```bash
python3 tests/test_financial_collection.py --stock sh.601398 --year 2025
python3 tests/test_financial_collection.py --stock sz.000001 --year 2025
```

### 步骤 5：测试完整采集流程

```bash
python3 src/utils/baostock_extension.py
```

## 📊 列名映射确认

测试确认了以下列名映射是正确的：

### 基础字段
- `pubDate` → `publish_date`
- `statDate` → `statistic_date`
- `code` → `stock_code`

### 利润表
- `roeAvg` → `roe_avg`
- `npMargin` → `np_margin`
- `gpMargin` → `gp_margin`
- `netProfit` → `net_profit`
- `epsTTM` → `eps_ttm`
- `MBRevenue` → `mb_revenue`

### 资产负债表
- `currentRatio` → `current_ratio`
- `quickRatio` → `quick_ratio`
- `cashRatio` → `cash_ratio`
- `YOYLiability` → `yoy_liability`
- `liabilityToAsset` → `liability_to_asset`
- `assetToEquity` → `asset_to_equity`

### 成长能力
- `YOYEquity` → `yoy_equity`
- `YOYAsset` → `yoy_asset`
- `YOYNI` → `yoy_ni`
- `YOYEPSBasic` → `yoy_eps_basic`
- `YOYPNI` → `yoy_pni`

### 运营能力
- `NRTurnRatio` → `nr_turn_ratio`
- `NRTurnDays` → `nr_turn_days`
- `INVTurnRatio` → `inv_turn_ratio`
- `INVTurnDays` → `inv_turn_days`
- `CATurnRatio` → `ca_turn_ratio`
- `AssetTurnRatio` → `asset_turn_ratio`

### 杜邦分析
- `dupontROE` → `dupont_roe`
- `dupontAssetStoEquity` → `dupont_asset_sto_equity`
- `dupontAssetTurn` → `dupont_asset_turn`
- `dupontPnitoni` → `dupont_pnitoni`
- `dupontNitogr` → `dupont_nitogr`
- `dupontTaxBurden` → `dupont_tax_burden`
- `dupontIntburden` → `dupont_int_burden`
- `dupontEbittogr` → `dupont_ebit_to_gr`

### 现金流量
- `CFOToOR` → `cfo_to_or`
- `CFOToNP` → `cfo_to_np`
- `CFOToGr` → `cfo_to_gr`
- `CAToAsset` → `ca_to_asset`
- `NCAToAsset` → `nca_to_asset`
- `tangibleAssetToAsset` → `tangible_asset_to_asset`
- `ebitToInterest` → `ebit_to_interest`

## ✅ 代码状态

以下代码修改已完成并推送到 GitHub：

1. ✅ `src/utils/baostock_extension.py` - 完善列名映射，添加数据清洗
2. ✅ `src/utils/baostock_financial.py` - 添加数据清洗
3. ✅ `sql/sync_baostock_tables.sql` - 表结构同步脚本
4. ✅ `tests/test_financial_collection.py` - 完整测试脚本

## 🎯 下一步

**必须执行**: 数据库表结构同步脚本

```bash
mysql -h 192.168.1.109 -P 3306 -u root -p stock < sql/sync_baostock_tables.sql
```

执行后重新运行测试，预期所有测试通过。

---

**测试结论**: 
- ✅ 所有 Baostock 接口正常工作
- ✅ 数据清洗功能正常
- ✅ 列名映射正确
- ❌ 数据库表结构需要同步
- ❌ stock_cash_flow_data 表需要创建

**修复优先级**: 高 - 执行 SQL 脚本后即可正常采集数据

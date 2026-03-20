# ATR 指标集成指南

**创建时间**: 2026-03-20  
**版本**: v1.0  
**依赖**: TA-Lib

---

## 📦 1. 安装 TA-Lib

### Ubuntu/Debian

```bash
# 1. 安装 TA-Lib C 库
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib/
./configure --prefix=/usr
make
sudo make install

# 2. 安装 Python 绑定
pip3 install TA-Lib

# 3. 验证安装
python3 -c "import talib; print('TA-Lib 版本:', talib.__version__)"
```

### CentOS/RHEL

```bash
# 1. 安装依赖
sudo yum install -y gcc gcc-c++ make

# 2. 安装 TA-Lib C 库
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib/
./configure --prefix=/usr
make
sudo make install

# 3. 安装 Python 绑定
pip3 install TA-Lib
```

### macOS

```bash
# 使用 Homebrew
brew install ta-lib
pip3 install TA-Lib
```

### Windows

```bash
# 下载预编译 wheel
# 访问：https://github.com/cgohlke/talib-build/releases

# 安装（根据 Python 版本选择）
pip3 install TA_Lib‑0.4.25‑cp39‑cp39‑win_amd64.whl

# 或使用 conda
conda install -c conda-forge ta-lib
```

---

## 🗄️ 2. 创建数据库表

```bash
# 执行 SQL 创建 ATR 表
cd /home/fan/.openclaw/workspace/stock_learning
mysql -u root -p stock < config/atr_tables.sql
```

**创建的表**:
- `stock_date_atr` - 日线 ATR
- `stock_week_atr` - 周线 ATR
- `stock_month_atr` - 月线 ATR
- `update_stock_record` - 添加 ATR 更新记录字段

---

## 🚀 3. 运行 ATR 计算

### 方法 1: 命令行运行

```bash
cd /home/fan/.openclaw/workspace/stock_learning

# 计算日线 ATR
python3 -c "
from src.utils.atr_calculation_tool import calculate_atr_for_all_stocks
calculate_atr_for_all_stocks(date_type='d')
"

# 计算周线 ATR
python3 -c "
from src.utils.atr_calculation_tool import calculate_atr_for_all_stocks
calculate_atr_for_all_stocks(date_type='w')
"

# 计算月线 ATR
python3 -c "
from src.utils.atr_calculation_tool import calculate_atr_for_all_stocks
calculate_atr_for_all_stocks(date_type='m')
"
```

### 方法 2: 直接运行脚本

```bash
cd /home/fan/.openclaw/workspace/stock_learning
python3 src/utils/atr_calculation_tool.py
```

### 方法 3: 使用 Redis 队列（生产环境）

```bash
cd /home/fan/.openclaw/workspace/stock_learning
python3 -c "
from src.utils.atr_calculation_tool import ATRCalculator
calculator = ATRCalculator()
calculator.run_batch_atr_multithread(max_workers=6, date_type='d')
"
```

---

## 📊 4. 查询 ATR 数据

### 查询单只股票 ATR

```sql
-- 日线 ATR
SELECT 
    stock_code,
    stock_date,
    tr,
    atr,
    natr
FROM stock_date_atr
WHERE stock_code = '000001'
ORDER BY stock_date DESC
LIMIT 30;
```

### 查询高波动股票

```sql
-- ATR 最高的股票（波动最大）
SELECT 
    s.stock_code,
    s.stock_name,
    a.atr,
    a.natr,
    p.close_price
FROM stock_date_atr a
JOIN stock_basic s ON a.stock_code = s.stock_code
JOIN stock_history_date_price p ON a.stock_code = p.stock_code AND a.stock_date = p.stock_date
WHERE a.stock_date = CURDATE()
ORDER BY a.natr DESC
LIMIT 20;
```

### 查询 ATR 突破的股票

```sql
-- ATR 放大 1.5 倍以上的股票
SELECT 
    a.stock_code,
    a.stock_date,
    a.atr,
    a.natr,
    (a.atr / LAG(a.atr, 5) OVER (PARTITION BY a.stock_code ORDER BY a.stock_date)) as atr_ratio
FROM stock_date_atr a
WHERE a.stock_date >= DATE_SUB(CURDATE(), INTERVAL 10 DAY)
HAVING atr_ratio > 1.5
ORDER BY atr_ratio DESC
LIMIT 20;
```

---

## 💡 5. ATR 应用示例

### 动态止损

```python
def calculate_stop_loss(entry_price, atr, multiplier=2):
    """计算动态止损价"""
    return entry_price - multiplier * atr

# 示例
entry_price = 100
atr = 3.5
stop_loss = calculate_stop_loss(entry_price, atr)  # 93 元
```

### 仓位管理

```python
def calculate_position_size(capital, risk_percent, atr):
    """根据 ATR 计算仓位"""
    risk_amount = capital * risk_percent
    position_size = risk_amount / atr
    return int(position_size)

# 示例
capital = 1000000  # 100 万
risk_percent = 0.01  # 1% 风险
atr = 3.5
position = calculate_position_size(capital, risk_percent, atr)  # 2857 股
```

### 波动率筛选

```python
# 查询 NATR > 5% 的高波动股票
SELECT * FROM stock_date_atr
WHERE natr > 5
ORDER BY natr DESC;
```

---

## 📝 6. 代码结构

```
stock_learning/
├── config/
│   ├── Indicator_config.py       # ✅ 已添加 get_atr_type()
│   └── atr_tables.sql            # ✅ ATR 表结构 SQL
├── src/utils/
│   └── atr_calculation_tool.py   # ✅ ATR 计算工具
└── docs/
    └── ATR_INTEGRATION_GUIDE.md  # ✅ 本文档
```

---

## 🔧 7. 配置文件说明

### Indicator_config.py

```python
def get_atr_type(self, date_type='d'):
    """获取 ATR 指标配置"""
    if date_type == 'w':
        return {
            'update_column': 'update_stock_week_atr',
            'data_table': 'stock_history_week_price',
            'update_table': 'stock_week_atr',
            'frequency': 56  # 周线
        }
    if date_type == 'm':
        return {
            'update_column': 'update_stock_month_atr',
            'data_table': 'stock_history_month_price',
            'update_table': 'stock_month_atr',
            'frequency': 28  # 月线
        }
    
    # 日线
    return {
        'update_column': 'update_stock_date_atr',
        'data_table': 'stock_history_date_price',
        'update_table': 'stock_date_atr',
        'frequency': 14  # 日线
    }
```

---

## ⚠️ 8. 注意事项

### 数据质量

- ✅ 确保 `high_price >= low_price`
- ✅ 确保无 NULL 值
- ✅ 确保数据连续性

### 性能优化

- 使用增量更新（只计算新数据）
- 批量处理（多线程，默认 6 线程）
- 添加索引（`stock_code`, `stock_date`）

### 死锁处理

- 已内置 `_execute_with_deadlock_retry` 方法
- 遇到死锁自动重试（指数退避）
- 最大重试 3 次

---

## 📊 9. 指标说明

### TR (True Range)

真实波动幅度，取以下三者最大值：
1. 当日最高价 - 当日最低价
2. |当日最高价 - 前一日收盘价 |
3. |当日最低价 - 前一日收盘价 |

### ATR (Average True Range)

TR 的 N 日移动平均（默认 14 日）

### NATR (Normalized ATR)

归一化 ATR = ATR / 收盘价 × 100%

便于跨股票比较波动率

---

## 🔗 10. 相关链接

- [TA-Lib 官方文档](https://ta-lib.github.io/ta-lib-python/)
- [ATR 指标详解](/home/fan/.openclaw/workspace/ATR_INDICATOR_GUIDE.md)
- [集成方案](/home/fan/.openclaw/workspace/ATR_INTEGRATION_PLAN.md)

---

_最后更新：2026-03-20 | 版本：v1.0_

# 数据库操作指南

**日期**: 2026-03-17

---

## ⚠️ MySQL 未启动

当前系统 MySQL 服务未运行，需要手动执行以下操作。

---

## 📋 操作步骤

### 步骤 1：启动 MySQL

**方法 1：使用 systemctl（推荐）**
```bash
sudo systemctl start mysqld
# 或
sudo systemctl start mysql
```

**方法 2：使用 service**
```bash
sudo service mysqld start
# 或
sudo service mysql start
```

**方法 3：手动启动**
```bash
sudo mysqld_safe &
```

**验证启动：**
```bash
mysql -u root -pFan123456 -e "SELECT 1"
```

---

### 步骤 2：删除 Tushare 相关表

**方法 1：使用脚本（推荐）**
```bash
cd /home/fan/.openclaw/workspace/stock_learning
mysql -u root -pFan123456 stock < sql/cleanup_tushare_tables.sql
```

**方法 2：手动执行**
```bash
mysql -u root -pFan123456 stock << 'EOF'
DROP TABLE IF EXISTS stock_moneyflow;
DROP TABLE IF EXISTS update_tushare_record;
EOF
```

**验证删除：**
```bash
mysql -u root -pFan123456 stock -e "SHOW TABLES LIKE '%moneyflow%'; SHOW TABLES LIKE '%tushare%';"
```

如果返回空结果，说明删除成功。

---

### 步骤 3：创建量价因子表

**方法 1：使用脚本（推荐）**
```bash
cd /home/fan/.openclaw/workspace/stock_learning
mysql -u root -pFan123456 stock < sql/create_volume_price_factor_tables.sql
```

**方法 2：手动执行**
```bash
mysql -u root -pFan123456 stock << 'EOF'
-- 创建量价因子表
CREATE TABLE IF NOT EXISTS `stock_factor_volume_price` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `stock_code` VARCHAR(10) NOT NULL,
  `calc_date` DATE NOT NULL,
  `volume_price_score` DECIMAL(10,4) DEFAULT 50.0,
  `volume_ratio` DECIMAL(10,4) DEFAULT 1.0,
  `price_change` DECIMAL(10,4) DEFAULT 0.0,
  `turnover_rate` DECIMAL(10,4) DEFAULT 0.0,
  `obv_change` DECIMAL(10,4) DEFAULT 0.0,
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY `uk_code_date` (`stock_code`, `calc_date`),
  KEY `idx_calc_date` (`calc_date`),
  KEY `idx_vp_score` (`volume_price_score`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 创建记录表
CREATE TABLE IF NOT EXISTS `update_volume_price_record` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `stock_code` VARCHAR(10) NOT NULL,
  `last_calc_date` DATE DEFAULT NULL,
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY `uk_stock_code` (`stock_code`),
  KEY `idx_last_calc_date` (`last_calc_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 初始化记录表
INSERT INTO update_volume_price_record (stock_code)
SELECT stock_code FROM stock_basic WHERE stock_status = 1
ON DUPLICATE KEY UPDATE stock_code = VALUES(stock_code);
EOF
```

**验证创建：**
```bash
mysql -u root -pFan123456 stock -e "SHOW TABLES LIKE '%volume%';"
```

---

### 步骤 4：测试量价因子计算

**测试单只股票：**
```bash
cd /home/fan/.openclaw/workspace/stock_learning
python3 src/utils/volume_price_factor.py
```

**批量计算：**
```bash
python3 scripts/calculate_volume_price_factor.py
```

**查看结果：**
```bash
mysql -u root -pFan123456 stock -e "
SELECT stock_code, volume_price_score, volume_ratio, price_change
FROM stock_factor_volume_price
WHERE calc_date = CURDATE()
ORDER BY volume_price_score DESC
LIMIT 20;
"
```

---

## 📊 完整操作命令（一键执行）

```bash
# 1. 启动 MySQL
sudo systemctl start mysqld

# 2. 删除旧表
cd /home/fan/.openclaw/workspace/stock_learning
mysql -u root -pFan123456 stock < sql/cleanup_tushare_tables.sql

# 3. 创建新表
mysql -u root -pFan123456 stock < sql/create_volume_price_factor_tables.sql

# 4. 测试计算
python3 src/utils/volume_price_factor.py

# 5. 批量计算（可选，需要时间）
python3 scripts/calculate_volume_price_factor.py
```

---

## ❓ 常见问题

### Q1: MySQL 无法启动
**A:** 检查 MySQL 是否安装
```bash
which mysql
which mysqld
rpm -qa | grep mysql
```

### Q2: 权限不足
**A:** 使用 sudo 或联系管理员
```bash
sudo mysql -u root -pFan123456 stock < sql/cleanup_tushare_tables.sql
```

### Q3: 表不存在
**A:** 正常，说明还未创建或已删除
```bash
# 忽略错误，继续执行创建脚本
mysql -u root -pFan123456 stock < sql/create_volume_price_factor_tables.sql
```

---

## 📝 操作记录

**请在此记录你的操作：**

```bash
# 日期：
# 操作人：
# 执行结果：
```

---

**完成上述步骤后，量价因子就可以正常使用了！**

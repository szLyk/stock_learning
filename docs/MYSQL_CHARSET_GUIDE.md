# MySQL 中文乱码避免指南

**创建时间:** 2026-03-14  
**问题:** 建表语句 COMMENT 显示乱码  
**解决:** 正确设置字符集

---

## ❌ 乱码示例

```
`stock_code` varchar(10) NOT NULL COMMENT 'è‚¡ç¥¨ä»£ç '
```

**原因:** 导入 SQL 时没有指定字符集

---

## ✅ 正确做法

### 方法 1: 命令行指定字符集（推荐）

```bash
mysql -h 192.168.1.109 -P 3306 -u root -p123456 stock \
  --default-character-set=utf8mb4 \
  < sql/financial_tables.sql
```

### 方法 2: SQL 文件开头添加

```sql
-- 在 SQL 文件第一行添加
SET NAMES utf8mb4;

USE stock;

CREATE TABLE ...
```

### 方法 3: MySQL 客户端交互模式

```bash
mysql -h 192.168.1.109 -P 3306 -u root -p123456
```

```sql
-- 登录后先设置字符集
SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

-- 然后执行建表语句
USE stock;
CREATE TABLE ...
```

### 方法 4: 在命令中直接指定

```bash
mysql -h 192.168.1.109 -P 3306 -u root -p123456 stock \
  --default-character-set=utf8mb4 \
  -e "CREATE TABLE ... COMMENT '股票代码'"
```

---

## 🔍 验证字符集

### 1. 查看数据库字符集

```sql
SHOW CREATE DATABASE stock;
```

**期望结果:**
```
CREATE DATABASE `stock` 
/*!40100 DEFAULT CHARACTER SET utf8mb4 */
```

### 2. 查看表字符集

```sql
SHOW CREATE TABLE stock_performance_update_record\G
```

**期望结果:**
```
DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
COMMENT='财务数据采集记录表'  ← 中文正常显示
```

### 3. 查看字段注释

```sql
SELECT 
    COLUMN_NAME,
    COLUMN_COMMENT
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = 'stock'
  AND TABLE_NAME = 'stock_performance_update_record';
```

**期望结果:**
```
COLUMN_NAME       COLUMN_COMMENT
stock_code        股票代码
stock_name        股票名称
update_profit_date 利润表最后更新日期
```

---

## 📝 字符集层级

MySQL 字符集设置有多个层级（优先级从高到低）：

1. **SQL 语句级**: `SET NAMES utf8mb4`
2. **连接级**: `--default-character-set=utf8mb4`
3. **数据库级**: `CREATE DATABASE ... DEFAULT CHARSET=utf8mb4`
4. **表级**: `CREATE TABLE ... DEFAULT CHARSET=utf8mb4`
5. **字段级**: `COLUMN ... CHARACTER SET utf8mb4`
6. **服务器级**: `my.cnf` 配置

**推荐:** 统一使用 `utf8mb4`，支持 emoji 和所有 Unicode 字符

---

## 🛠️ 修复已有乱码表

### 步骤 1: 备份数据

```bash
mysqldump -h 192.168.1.109 -u root -p123456 stock \
  stock_performance_update_record > backup.sql
```

### 步骤 2: 删除乱码表

```sql
DROP TABLE stock_performance_update_record;
```

### 步骤 3: 重新创建（指定字符集）

```bash
mysql -h 192.168.1.109 -u root -p123456 stock \
  --default-character-set=utf8mb4 \
  < sql/financial_tables.sql
```

### 步骤 4: 验证

```sql
SHOW CREATE TABLE stock_performance_update_record\G
```

---

## ⚠️ 常见错误

### 错误 1: 忘记指定字符集

```bash
# ❌ 错误
mysql -h ... -u ... -p ... < xxx.sql

# ✅ 正确
mysql -h ... -u ... -p ... --default-character-set=utf8mb4 < xxx.sql
```

### 错误 2: 使用过时的 latin1

```sql
-- ❌ 错误
CREATE TABLE ... DEFAULT CHARSET=latin1

-- ✅ 正确
CREATE TABLE ... DEFAULT CHARSET=utf8mb4
```

### 错误 3: 只设置数据库不设置表

```sql
-- ❌ 不完整
CREATE DATABASE stock DEFAULT CHARSET=utf8mb4;
USE stock;
CREATE TABLE t1 (...);  -- 会继承数据库字符集，但建议显式指定

-- ✅ 推荐
CREATE TABLE t1 (...) DEFAULT CHARSET=utf8mb4;
```

---

## 📋 最佳实践清单

- [ ] SQL 文件开头添加 `SET NAMES utf8mb4;`
- [ ] 建表语句显式指定 `DEFAULT CHARSET=utf8mb4`
- [ ] 命令行导入使用 `--default-character-set=utf8mb4`
- [ ] 所有 COMMENT 使用中文前验证字符集
- [ ] 定期检查数据库字符集配置
- [ ] 备份时保持字符集一致

---

## 🔗 相关文档

- [财务数据表结构](sql/financial_tables.sql)
- [财务 Skill 文档](skills/baostock-financial/SKILL.md)

---

_最后更新：2026-03-14_

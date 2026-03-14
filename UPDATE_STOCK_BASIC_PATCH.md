# update_stock_basic 方法修改补丁

**文件:** `src/utils/baosock_tool.py`  
**行号:** 约 258-295 行  
**修改时间:** 2026-03-15

---

## 📝 修改内容

### 原代码（需要替换的部分）

```python
# 更新股票基础信息
def update_stock_basic(self):
    # 获取行业分类数据
    rs = bs.query_stock_basic()
    data_list = []
    while (rs.error_code == '0') & rs.next():
        # 获取一条记录，将记录合并在一起
        data_list.append(rs.get_row_data())
    result = pd.DataFrame(data_list, columns=rs.fields)
    df = result.rename(columns={
        'code': 'stock_code',
        'code_name': 'stock_name',
        'ipoDate': 'ipo_date',
        'outDate': 'out_date',
        'type': 'stock_type',
        'status': 'stock_status'
    }).replace(r'^\s*$', None, regex=True)
    df['update_date'] = get_last_some_time(0)
    df['market_type'] = df['stock_code'].apply(lambda x: x[:2])
    df['stock_code'] = df['stock_code'].apply(lambda x: x[-6:])
    # # 使用 to_sql 方法将 DataFrame 写入数据库
    table_name = 'stock_basic'
    # 创建 SQLAlchemy 引擎
    self.mysql_manager.batch_insert_or_update(table_name, df, ['stock_code'])
    # 过滤掉 df 中状态 stock_type 不为 1 的数据 建立一个新的数据集
    stock_record = df[df['stock_type'] == '1']
    self.mysql_manager.batch_insert_or_update('update_stock_record',
                                              stock_record[['stock_code', 'stock_name', 'market_type']],
                                              ['stock_code'])
    stock_record = df[df['stock_type'].isin(['2', '5'])]
    self.mysql_manager.batch_insert_or_update('update_index_stock_record',
                                              stock_record[
                                                  ['stock_code', 'stock_name', 'market_type', 'stock_type']],
                                              ['stock_code'])
    return df
```

### 新代码（替换后的代码）

```python
# 更新股票基础信息
def update_stock_basic(self):
    """
    更新股票基础信息，并同步到新的记录表
    - update_stock_record (旧表)
    - stock_performance_update_record (财务数据记录表)
    - update_eastmoney_record (东方财富数据记录表)
    """
    # 获取行业分类数据
    rs = bs.query_stock_basic()
    data_list = []
    while (rs.error_code == '0') & rs.next():
        # 获取一条记录，将记录合并在一起
        data_list.append(rs.get_row_data())
    result = pd.DataFrame(data_list, columns=rs.fields)
    df = result.rename(columns={
        'code': 'stock_code',
        'code_name': 'stock_name',
        'ipoDate': 'ipo_date',
        'outDate': 'out_date',
        'type': 'stock_type',
        'status': 'stock_status'
    }).replace(r'^\s*$', None, regex=True)
    df['update_date'] = get_last_some_time(0)
    df['market_type'] = df['stock_code'].apply(lambda x: x[:2])
    df['stock_code'] = df['stock_code'].apply(lambda x: x[-6:])
    # # 使用 to_sql 方法将 DataFrame 写入数据库
    table_name = 'stock_basic'
    # 创建 SQLAlchemy 引擎
    self.mysql_manager.batch_insert_or_update(table_name, df, ['stock_code'])
    
    # 过滤掉 df 中状态 stock_type 不为 1 的数据 建立一个新的数据集
    stock_record = df[df['stock_type'] == '1']
    
    # 移除 stock_name 为空的记录
    stock_record = stock_record.dropna(subset=['stock_name'])
    stock_record = stock_record[stock_record['stock_name'].str.strip() != '']
    
    self.logger.info(f"有效股票记录：{len(stock_record)} 只（已移除无名称股票）")
    
    if len(stock_record) > 0:
        self.mysql_manager.batch_insert_or_update('update_stock_record',
                                                  stock_record[['stock_code', 'stock_name', 'market_type']],
                                                  ['stock_code'])
        
        # 同步到新记录表 stock_performance_update_record
        for _, row in stock_record.iterrows():
            self.mysql_manager.execute("""
                INSERT INTO stock_performance_update_record (stock_code, stock_name, market_type)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                    stock_name = VALUES(stock_name),
                    market_type = VALUES(market_type)
            """, (row['stock_code'], row['stock_name'], row['market_type']))
        
        # 同步到新记录表 update_eastmoney_record
        for _, row in stock_record.iterrows():
            self.mysql_manager.execute("""
                INSERT INTO update_eastmoney_record (stock_code, stock_name, market_type)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                    stock_name = VALUES(stock_name),
                    market_type = VALUES(market_type)
            """, (row['stock_code'], row['stock_name'], row['market_type']))
    
    stock_record = df[df['stock_type'].isin(['2', '5'])]
    stock_record = stock_record.dropna(subset=['stock_name'])
    stock_record = stock_record[stock_record['stock_name'].str.strip() != '']
    
    if len(stock_record) > 0:
        self.mysql_manager.batch_insert_or_update('update_index_stock_record',
                                                  stock_record[
                                                      ['stock_code', 'stock_name', 'market_type', 'stock_type']],
                                                  ['stock_code'])
    
    self.logger.info(f"股票基础信息更新完成，共 {len(df)} 只股票")
    return df
```

---

## 🔧 修改说明

### 1. 添加文档字符串
```python
"""
更新股票基础信息，并同步到新的记录表
- update_stock_record (旧表)
- stock_performance_update_record (财务数据记录表)
- update_eastmoney_record (东方财富数据记录表)
"""
```

### 2. 添加 stock_name 空值检查
```python
# 移除 stock_name 为空的记录
stock_record = stock_record.dropna(subset=['stock_name'])
stock_record = stock_record[stock_record['stock_name'].str.strip() != '']

self.logger.info(f"有效股票记录：{len(stock_record)} 只（已移除无名称股票）")
```

### 3. 同步到新记录表
```python
# 同步到 stock_performance_update_record
for _, row in stock_record.iterrows():
    self.mysql_manager.execute("""
        INSERT INTO stock_performance_update_record (stock_code, stock_name, market_type)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE 
            stock_name = VALUES(stock_name),
            market_type = VALUES(market_type)
    """, (row['stock_code'], row['stock_name'], row['market_type']))

# 同步到 update_eastmoney_record
for _, row in stock_record.iterrows():
    self.mysql_manager.execute("""
        INSERT INTO update_eastmoney_record (stock_code, stock_name, market_type)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE 
            stock_name = VALUES(stock_name),
            market_type = VALUES(market_type)
    """, (row['stock_code'], row['stock_name'], row['market_type']))
```

### 4. 指数记录也添加空值检查
```python
stock_record = df[df['stock_type'].isin(['2', '5'])]
stock_record = stock_record.dropna(subset=['stock_name'])
stock_record = stock_record[stock_record['stock_name'].str.strip() != '']
```

---

## ✅ 验证方法

运行修复脚本后验证：
```bash
python3 fix_update_stock_basic.py
```

**期望输出:**
```
stock_performance_update_record 表有效记录：7463
update_eastmoney_record 表有效记录：7463
```

---

**请手动修改 `src/utils/baosock_tool.py` 中的 `update_stock_basic` 方法！** 📊

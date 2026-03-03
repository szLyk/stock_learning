import numpy as np
import pandas as pd
from pymysql import IntegrityError
import os
from config.mysql_config import get_mysql_config_instance
import pymysql
from pymysql.cursors import DictCursor
from typing import Optional, Dict, List, Tuple, Any, Union
from contextlib import contextmanager

from logs.logger import LogManager

# 👇 新增导入
from dbutils.pooled_db import PooledDB


class MySQLUtil:
    """MySQL工具类（使用连接池，线程安全）"""

    # 类变量：全局唯一的连接池（单例）
    _pool: Optional[PooledDB] = None

    def __init__(self):
        # 初始化连接池（只执行一次）
        if MySQLUtil._pool is None:
            config = get_mysql_config_instance().get_config()
            MySQLUtil._pool = PooledDB(
                creator=pymysql,  # 使用 pymysql 作为底层驱动
                host=config["host"],
                port=config["port"],
                user=config["user"],
                password=config["password"],
                database=config["database"],
                charset=config["charset"],
                connect_timeout=config["connect_timeout"],
                read_timeout=config["read_timeout"],
                write_timeout=config["write_timeout"],
                cursorclass=DictCursor,

                # 连接池配置
                mincached=2,  # 启动时创建的空闲连接数
                maxcached=10,  # 最大空闲连接数（超过则关闭）
                maxshared=10,  # 最大共享连接数（pymysql 不支持共享，可忽略）
                maxconnections=20,  # 最大总连接数（重要！防打满）
                blocking=True,  # 连接数达上限时，是否阻塞等待
                ping=1,  # 每次从池取连接时 ping 一下（检查有效性）
            )
        self.conn = None
        self.cursor = None
        self.logger = LogManager.get_logger("mysql_util")

    def connect(self) -> None:
        """从连接池获取一个连接（非新建！）"""
        try:
            self.conn = MySQLUtil._pool.connection()  # 从池中借一个连接
            self.cursor = self.conn.cursor()
            # print("从连接池获取数据库连接")  # 可选日志
        except Exception as e:
            raise RuntimeError(f"从连接池获取数据库连接失败：{str(e)}")

    def close(self) -> None:
        """归还连接到池（不是真正关闭）"""
        if self.cursor:
            try:
                self.cursor.close()
            except Exception as e:
                self.logger.warning(f"关闭游标失败：{e}")
        if self.conn:
            try:
                self.conn.close()  # 归还到连接池
                # print("数据库连接已归还到池")  # 可选日志
            except Exception as e:
                self.logger.warning(f"归还连接失败：{e}")

    def __enter__(self) -> "MySQLUtil":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if exc_type:
            if hasattr(self.conn, 'rollback'):
                self.conn.rollback()
            self.logger.error(f"执行异常：{exc_val}")
        else:
            if hasattr(self.conn, 'commit'):
                self.conn.commit()
        self.close()
        return False

    # ========== 以下方法保持不变（仅微调异常处理） ==========

    def query_one(self, sql: str, params: Tuple = ()) -> Optional[Dict[str, Any]]:
        if not self.conn or not self.cursor:
            raise RuntimeError("数据库未连接，请先调用connect()或使用with语句")
        try:
            self.cursor.execute(sql, params)
            return self.cursor.fetchone()
        except Exception as e:
            raise RuntimeError(f"查询单条数据失败：{str(e)}")

    def query_all(self, sql: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        if not self.conn or not self.cursor:
            raise RuntimeError("数据库未连接，请先调用connect()或使用with语句")
        try:
            self.cursor.execute(sql, params)
            return self.cursor.fetchall()
        except Exception as e:
            raise RuntimeError(f"查询多条数据失败：{str(e)}")

    def execute(self, sql: str, params: Tuple = ()) -> int:
        if not self.conn or not self.cursor:
            raise RuntimeError("数据库未连接，请先调用connect()或使用with语句")
        try:
            affected_rows = self.cursor.execute(sql, params)
            self.conn.commit()
            return affected_rows
        except Exception as e:
            self.conn.rollback()
            raise RuntimeError(f"执行SQL失败：{str(e)}")

    def batch_execute(self, sql: str, params_list: List[Tuple]) -> int:
        if not self.conn or not self.cursor:
            raise RuntimeError("数据库未连接，请先调用connect()或使用with语句")
        if not params_list:
            return 0
        try:
            affected_rows = self.cursor.executemany(sql, params_list)
            self.conn.commit()
            return affected_rows
        except Exception as e:
            self.conn.rollback()
            raise RuntimeError(f"批量执行SQL失败：{str(e)}")

    @contextmanager
    def transaction(self):
        if not self.conn or not self.cursor:
            raise RuntimeError("数据库未连接，请先调用connect()或使用with语句")
        try:
            yield
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            raise RuntimeError(f"事务执行失败：{str(e)}")

    def _validate_field_name(self, field_name: str) -> bool:
        return field_name.isidentifier() and not field_name.startswith(('_', 'mysql'))

    def batch_insert_or_update(self, table_name, df, unique_keys):
        df = df.replace(np.nan, None)
        if df.empty:
            print("DataFrame为空，无需入库")
            return 0

        data_list = df.where(pd.notnull(df), None).to_dict('records')
        if not data_list:
            print("数据列表为空，无需入库")
            return 0

        columns = [col for col in df.columns if col in data_list[0]]
        if not columns:
            print("无有效字段，无需入库")
            return 0

        placeholders = ', '.join(['%s'] * len(columns))
        col_str = ', '.join(columns)
        update_str = ', '.join([f"{col} = VALUES({col})" for col in columns if col not in unique_keys])

        sql = f"""
            INSERT INTO {table_name} ({col_str}) 
            VALUES ({placeholders}) 
            ON DUPLICATE KEY UPDATE {update_str}
        """
        try:
            values = [tuple([item[col] for col in columns]) for item in data_list]
            batch_size = 5000
            total_rows = 0
            for i in range(0, len(values), batch_size):
                batch = values[i:i + batch_size]
                self.cursor.executemany(sql, batch)
                total_rows += len(batch)
            self.conn.commit()
            print(f"成功批量插入/更新 {total_rows} 条数据到 {table_name}")
            return total_rows
        except IntegrityError as e:
            self.conn.rollback()
            self.logger.error(f"数据冲突错误：{e}")
            return 0
        except Exception as e:
            self.conn.rollback()
            stock_code = df['stock_code'].iloc[0] if not df.empty and 'stock_code' in df.columns else 'UNKNOWN'
            self.logger.error(f"{stock_code}: 批量入库失败：{e}")
            return 0

    def export_stock_db_schema(self, output_file: str = "../../config/mysql_table.sql"):
        if not self.conn or not self.cursor:
            raise RuntimeError("数据库未连接，请先调用 connect() 或使用 with 上下文管理器")

        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        config = get_mysql_config_instance().get_config()

        try:
            cursor = self.conn.cursor(DictCursor)
            cursor.execute("""
                SELECT TABLE_NAME 
                FROM information_schema.TABLES 
                WHERE TABLE_SCHEMA = %s 
                ORDER BY TABLE_NAME
            """, (config["database"],))

            tables = [row['TABLE_NAME'] for row in cursor.fetchall()]
            if not tables:
                print(f"警告：数据库 {config['database']} 中未找到任何表！")
                return

            with open(output_file, 'w', encoding='utf8') as f:
                f.write(f"-- 自动生成 stock 库表结构\n")
                f.write(f"-- 时间: {pymysql.__version__} | Database: {config['database']}\n\n")
                f.write(f"USE `{config['database']}`;\n\n")

                for table_name in tables:
                    if not table_name.replace('_', '').replace('-', '').isalnum():
                        print(f"跳过非法表名: {table_name}")
                        continue

                    cursor.execute(f"SHOW CREATE TABLE `{config['database']}`.`{table_name}`")
                    result = cursor.fetchone()
                    create_sql = result.get('Create Table') if result else None

                    if create_sql:
                        f.write(f"-- --------------------------------------------------------\n")
                        f.write(f"-- Table structure for table `{table_name}`\n")
                        f.write(f"-- --------------------------------------------------------\n")
                        f.write(f"DROP TABLE IF EXISTS `{table_name}`;\n")
                        f.write(create_sql + ";\n\n")
                    else:
                        print(f"跳过无法读取的表: {table_name}")

            print(f"✅ 成功导出 {len(tables)} 张表结构到: {os.path.abspath(output_file)}")

        except Exception as e:
            print(f"❌ 导出失败: {e}")
            raise


# ===== 测试用法（完全兼容旧代码）=====
if __name__ == "__main__":
    # 方式1：手动管理
    db = MySQLUtil()
    db.connect()
    try:
        db.export_stock_db_schema()
    finally:
        db.close()
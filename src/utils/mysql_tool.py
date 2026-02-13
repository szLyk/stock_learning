import pandas as pd
from pymysql import IntegrityError

from config.mysql_config import get_mysql_config_instance
import pymysql
from pymysql.cursors import DictCursor
from typing import Optional, Dict, List, Tuple, Any, Union
from contextlib import contextmanager


class MySQLUtil:
    """MySQL工具类，封装常用数据库操作，包含完善的异常处理"""

    def __init__(self):
        # 获取配置实例
        self.config = get_mysql_config_instance().get_config()
        self.conn: Optional[pymysql.connections.Connection] = None  # 数据库连接对象
        self.cursor = None  # 游标对象

    def connect(self) -> None:
        """建立数据库连接，处理连接失败异常"""
        try:
            self.conn = pymysql.connect(
                host=self.config["host"],
                port=self.config["port"],
                user=self.config["user"],
                password=self.config["password"],
                database=self.config["database"],
                charset=self.config["charset"],
                connect_timeout=self.config["connect_timeout"],
                read_timeout=self.config["read_timeout"],
                write_timeout=self.config["write_timeout"],
                cursorclass=DictCursor  # 游标返回字典格式（方便使用）
            )
            self.cursor = self.conn.cursor()
            print("数据库连接成功！")  # 新增：提示连接成功
        except pymysql.MySQLError as e:
            raise RuntimeError(f"数据库连接失败：{str(e)}")

    def close(self) -> None:
        """关闭数据库连接（游标+连接），确保资源释放"""
        if self.cursor:
            try:
                self.cursor.close()
            except Exception as e:
                print(f"关闭游标失败：{str(e)}")
        if self.conn:
            try:
                self.conn.close()
                print("数据库连接已关闭！")  # 新增：提示关闭成功
            except Exception as e:
                print(f"关闭连接失败：{str(e)}")

    def __enter__(self) -> "MySQLUtil":
        """上下文管理器入口，自动连接数据库"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """上下文管理器出口，自动关闭连接，处理异常"""
        if exc_type:
            # 有异常时回滚事务
            if self.conn:
                self.conn.rollback()
            print(f"执行异常：{exc_val}")
        else:
            # 无异常时提交事务
            if self.conn:
                self.conn.commit()
        self.close()
        # 返回True表示已处理异常，不会向外抛出；返回False则抛出
        return False

    def query_one(self, sql: str, params: Tuple = ()) -> Optional[Dict[str, Any]]:
        """
        查询单条数据
        :param sql: 查询SQL语句
        :param params: SQL参数（防止SQL注入）
        :return: 单条数据字典，无数据返回None
        """
        if not self.conn or not self.cursor:
            raise RuntimeError("数据库未连接，请先调用connect()或使用with语句")
        try:
            self.cursor.execute(sql, params)
            return self.cursor.fetchone()
        except pymysql.MySQLError as e:
            raise RuntimeError(f"查询单条数据失败：{str(e)}")

    def query_all(self, sql: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        """
        查询多条数据
        :param sql: 查询SQL语句
        :param params: SQL参数
        :return: 数据列表（元素为字典），无数据返回空列表
        """
        if not self.conn or not self.cursor:
            raise RuntimeError("数据库未连接，请先调用connect()或使用with语句")
        try:
            self.cursor.execute(sql, params)
            return self.cursor.fetchall()
        except pymysql.MySQLError as e:
            raise RuntimeError(f"查询多条数据失败：{str(e)}")

    def execute(self, sql: str, params: Tuple = ()) -> int:
        """
        执行单条增/删/改操作
        :param sql: 执行的SQL语句
        :param params: SQL参数
        :return: 受影响的行数
        """
        if not self.conn or not self.cursor:
            raise RuntimeError("数据库未连接，请先调用connect()或使用with语句")
        try:
            affected_rows = self.cursor.execute(sql, params)
            self.conn.commit()  # 手动提交（非上下文管理器模式下）
            return affected_rows
        except pymysql.MySQLError as e:
            self.conn.rollback()  # 异常时回滚
            raise RuntimeError(f"执行SQL失败：{str(e)}")

    def batch_execute(self, sql: str, params_list: List[Tuple]) -> int:
        """
        批量执行增/删/改操作（效率更高）
        :param sql: 执行的SQL语句
        :param params_list: 参数列表（每个元素为一个参数元组）
        :return: 受影响的总行数
        """
        if not self.conn or not self.cursor:
            raise RuntimeError("数据库未连接，请先调用connect()或使用with语句")
        if not params_list:
            return 0
        try:
            affected_rows = self.cursor.executemany(sql, params_list)
            self.conn.commit()
            return affected_rows
        except pymysql.MySQLError as e:
            self.conn.rollback()
            raise RuntimeError(f"批量执行SQL失败：{str(e)}")

    @contextmanager
    def transaction(self):
        """事务管理器，支持手动提交和回滚"""
        if not self.conn or not self.cursor:
            raise RuntimeError("数据库未连接，请先调用connect()或使用with语句")
        try:
            yield
            self.conn.commit()
        except pymysql.MySQLError as e:
            self.conn.rollback()
            raise RuntimeError(f"事务执行失败：{str(e)}")

        # ------------------- 新增：通用插入/更新（UPSERT）方法 -------------------

    def _validate_field_name(self, field_name: str) -> bool:
        """校验字段名合法性（防SQL注入）：仅允许字母、数字、下划线"""
        return field_name.isidentifier() and not field_name.startswith(('_', 'mysql'))

    def batch_insert_or_update(self, table_name, df, unique_keys):
        """
        批量插入/更新DataFrame数据到MySQL
        :param table_name: 表名
        :param df: 要插入的DataFrame
        :param unique_keys: 唯一键列表（如['stock_code']），用于冲突时更新
        :return: 影响行数
        """
        # ========== 修复核心：正确判断DataFrame是否为空 ==========
        if df.empty:  # 替换原有的 if not data_list:
            print("DataFrame为空，无需入库")
            return 0

        # 将DataFrame转为字典列表（适配批量插入）
        data_list = df.where(pd.notnull(df), None).to_dict('records')
        if not data_list:
            print("数据列表为空，无需入库")
            return 0

        # 提取字段名（排除空值列）
        columns = [col for col in df.columns if col in data_list[0]]
        if not columns:
            print("无有效字段，无需入库")
            return 0

        # 构建插入SQL（ON DUPLICATE KEY UPDATE）
        placeholders = ', '.join(['%s'] * len(columns))
        col_str = ', '.join(columns)
        update_str = ', '.join([f"{col} = VALUES({col})" for col in columns if col not in unique_keys])

        sql = f"""
            INSERT INTO {table_name} ({col_str}) 
            VALUES ({placeholders}) 
            ON DUPLICATE KEY UPDATE {update_str}
        """
        # 批量执行
        try:
            # 提取数据值（保持字段顺序）
            values = [tuple([item[col] for col in columns]) for item in data_list]
            # 批量插入（每次插入1000条，避免SQL过长）
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
            print(f"数据冲突错误：{e}")
            return 0
        except Exception as e:
            self.conn.rollback()
            print(f"批量入库失败：{e}")
            return 0
        finally:
            # 不要关闭连接，留给外部管理
            pass


if __name__ == "__main__":
    # 修正测试代码：正确调用connect方法
    try:
        # 方式1：手动调用（测试连接）
        mysql_util = MySQLUtil()  # 创建实例
        mysql_util.connect()  # 调用连接方法（无需传self）
        # 测试查询（示例）
        result = mysql_util.query_all("SELECT * from stock_industry limit 500")
        print("测试查询结果：", result)
    except Exception as e:
        print(f"测试失败：{str(e)}")
    finally:
        mysql_util.close()  # 确保关闭连接

    # 方式2：推荐使用上下文管理器（自动连接/关闭）
    # try:
    #     with MySQLUtil() as mysql:
    #         result = mysql.query_one("SELECT 1 as test")
    #         print("上下文管理器测试结果：", result)
    # except Exception as e:
    #     print(f"上下文管理器测试失败：{str(e)}")

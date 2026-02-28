from config.base_config import BaseConfig, singleton
from typing import Dict, Any
import os  # 处理路径


@singleton  # 单例模式，避免重复加载
class MySQLConfig(BaseConfig[Dict[str, Any]]):
    """MySQL配置类（继承通用基类，仅实现自身配置项）"""

    def __init__(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # 拼接同目录下的config.ini路径（不再跳转根目录）
        config_path = os.path.join(current_dir, "config.ini")
        # 调用父类初始化（传入正确的配置文件绝对路径）
        super().__init__(config_path=config_path, section="mysql")

    def get_config(self) -> Dict[str, Any]:
        """获取MySQL完整配置（封装自身的配置项）"""
        return {
            "host": self.get_str("host"),
            "port": self.get_int("port", fallback=3306),
            "user": self.get_str("user"),
            "password": self.get_str("password"),
            "database": self.get_str("database"),
            "charset": self.get_str("charset", fallback="utf8mb4"),
            "connect_timeout": self.get_int("connect_timeout", fallback=10),
            "read_timeout": self.get_int("read_timeout", fallback=30),
            "write_timeout": self.get_int("write_timeout", fallback=30)
        }


# 简化单例获取方法（装饰器已保证单例）
def get_mysql_config_instance() -> MySQLConfig:
    """获取MySQLConfig单例对象"""
    return MySQLConfig()

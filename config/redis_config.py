from config.base_config import BaseConfig, singleton
from typing import Dict, Any
import os


@singleton  # 单例模式
class RedisConfig(BaseConfig[Dict[str, Any]]):
    """Redis配置类（复用通用基类，仅定义Redis专属配置项）"""

    def __init__(self, config_path: str = "config.ini"):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # 拼接同目录下的config.ini路径（不再跳转根目录）
        config_path = os.path.join(current_dir, "config.ini")
        # 调用父类初始化（传入正确的配置文件绝对路径）
        super().__init__(config_path=config_path, section="redis")

    def get_config(self) -> Dict[str, Any]:
        """获取Redis完整配置"""
        return {
            "host": self.get_str("host", fallback="127.0.0.1"),
            "port": self.get_int("port", fallback=6379),
            "username": self.get_str("username", fallback=""),
            "password": self.get_str("password", fallback=""),
            "db": self.get_int("db", fallback=0),
            "max_connections": self.get_int("max_connections", fallback=20),
            "socket_timeout": self.get_int("timeout", fallback=5),
            "decode_responses": self.get_bool("decode_responses", fallback=True)
        }


# 获取Redis配置实例的快捷方法
def get_redis_config() -> Dict[str, Any]:
    return RedisConfig().get_config()


if __name__ == "__main__":
    # 测试代码
    print(get_redis_config())

import configparser
import os
from typing import Dict, Any, Optional, TypeVar, Generic
from abc import ABC, abstractmethod

# 定义泛型类型，用于约束子类返回的配置结构
ConfigType = TypeVar('ConfigType')


class BaseConfig(ABC, Generic[ConfigType]):
    """通用配置读取基类，抽象配置加载核心逻辑，支持任意配置文件/节点的读取"""

    def __init__(self, config_path: str = "config.ini", section: str = ""):
        self.config_path = config_path  # 配置文件路径
        self.section = section  # 要读取的配置节点（如mysql/redis）
        self.config = configparser.ConfigParser()
        self._load_config()  # 初始化时自动加载配置

    def _load_config(self) -> None:
        """通用配置文件加载逻辑，处理文件不存在/解析失败异常"""
        # 检查文件是否存在
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"配置文件 {self.config_path} 不存在！")

        # 读取配置文件，处理编码和解析异常
        try:
            self.config.read(self.config_path, encoding="utf-8")
        except configparser.Error as e:
            raise RuntimeError(f"配置文件解析失败：{str(e)}")
        except Exception as e:
            raise RuntimeError(f"读取配置文件异常：{str(e)}")

    def _check_section(self) -> None:
        """检查指定的配置节点是否存在"""
        if not self.section or self.section not in self.config.sections():
            raise KeyError(f"配置文件中缺少 [{self.section}] 节点！")

    # ------------------- 通用配置项获取方法（核心复用逻辑） -------------------
    def get_str(self, key: str, fallback: Optional[str] = None) -> str:
        """获取字符串类型配置项"""
        self._check_section()
        return self.config.get(self.section, key, fallback=fallback)

    def get_int(self, key: str, fallback: Optional[int] = None) -> int:
        """获取整数类型配置项"""
        self._check_section()
        return self.config.getint(self.section, key, fallback=fallback)

    def get_bool(self, key: str, fallback: Optional[bool] = None) -> bool:
        """获取布尔类型配置项（支持yes/no、true/false、1/0）"""
        self._check_section()
        return self.config.getboolean(self.section, key, fallback=fallback)

    def get_float(self, key: str, fallback: Optional[float] = None) -> float:
        """获取浮点类型配置项"""
        self._check_section()
        return self.config.getfloat(self.section, key, fallback=fallback)

    # ------------------- 抽象方法（子类必须实现） -------------------
    @abstractmethod
    def get_config(self) -> ConfigType:
        """获取组件完整配置（子类实现，返回对应结构的配置）"""
        pass


# ------------------- 通用单例装饰器（复用单例逻辑） -------------------
def singleton(cls):
    """通用单例装饰器，适用于所有配置类"""
    _instances = {}

    def wrapper(*args, **kwargs):
        if cls not in _instances:
            _instances[cls] = cls(*args, **kwargs)
        return _instances[cls]

    return wrapper
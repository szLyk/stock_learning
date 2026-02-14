import logging
import logging.handlers
import os
from typing import Optional
from config.log_config import LOG_CONFIG, get_log_dir


class LogManager:
    """日志管理器（支持关闭普通日志文件）"""
    _loggers = {}

    @classmethod
    def get_logger(cls, name: str = "stock_learning") -> logging.Logger:
        if name in cls._loggers:
            return cls._loggers[name]

        # 基础配置
        logger = logging.getLogger(name)
        log_level = getattr(logging, LOG_CONFIG["log_level"].upper(), logging.INFO)
        logger.setLevel(log_level)
        logger.propagate = False

        # 1. 控制台Handler（始终保留）
        console_formatter = logging.Formatter(
            fmt=LOG_CONFIG["console_format"],
            datefmt=LOG_CONFIG["date_format"]
        )
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        # 2. 处理文件Handler（根据开关控制）
        try:
            log_dir = get_log_dir()
            if not os.path.exists(log_dir):
                logger.error(f"日志目录不存在：{log_dir}")
                cls._loggers[name] = logger
                return logger

            # ========== 核心：只在开启时添加普通日志FileHandler ==========
            if LOG_CONFIG["enable_normal_log_file"]:
                normal_log_file = os.path.join(log_dir, f"{name}.log")
                file_handler = logging.handlers.RotatingFileHandler(
                    filename=normal_log_file,
                    maxBytes=LOG_CONFIG["max_bytes"],
                    backupCount=LOG_CONFIG["backup_count"],
                    encoding=LOG_CONFIG["encoding"],
                    mode="a"
                )
                file_handler.setLevel(logging.DEBUG)
                file_handler.setFormatter(logging.Formatter(
                    fmt=LOG_CONFIG["file_format"],
                    datefmt=LOG_CONFIG["date_format"]
                ))
                logger.addHandler(file_handler)
                logger.debug(f"普通日志文件已开启：{normal_log_file}")
            else:
                logger.debug("普通日志文件已关闭")  # 提示普通日志已关闭

            # ========== 保留错误日志FileHandler ==========
            if LOG_CONFIG["enable_error_log_file"]:
                error_log_file = os.path.join(log_dir, f"{name}_error.log")
                error_handler = logging.handlers.RotatingFileHandler(
                    filename=error_log_file,
                    maxBytes=LOG_CONFIG["max_bytes"],
                    backupCount=LOG_CONFIG["backup_count"],
                    encoding=LOG_CONFIG["encoding"],
                    mode="a"
                )
                error_handler.setLevel(logging.ERROR)
                error_handler.setFormatter(logging.Formatter(
                    fmt=LOG_CONFIG["file_format"],
                    datefmt=LOG_CONFIG["date_format"]
                ))
                logger.addHandler(error_handler)
                logger.debug(f"错误日志文件已开启：{error_log_file}")

        except Exception as e:
            logger.error(f"创建文件Handler失败：{str(e)}", exc_info=True)

        # 缓存日志器
        cls._loggers[name] = logger
        return logger


def get_default_logger() -> logging.Logger:
    return LogManager.get_logger("stock_learning")
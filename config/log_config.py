import os

# ========== 核心：获取项目根目录 ==========
CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))  # E:\PycharmProjects\stock_learing\config
PROJECT_ROOT = os.path.dirname(CONFIG_DIR)  # E:\PycharmProjects\stock_learing

# ========== 固定日志目录 ==========
LOG_DIR = os.path.join(PROJECT_ROOT, "logs", "stock_project")

# 日志完整配置（新增普通日志开关）
LOG_CONFIG = {
    "log_dir": LOG_DIR,
    "log_level": "DEBUG",
    "max_bytes": 50 * 1024 * 1024,
    "backup_count": 10,
    "encoding": "utf-8",
    "console_format": "%(asctime)s - %(levelname)s - %(message)s",
    "file_format": "%(asctime)s - %(name)s - %(module)s:%(lineno)d - %(levelname)s - %(message)s",
    "date_format": "%Y-%m-%d %H:%M:%S",
    "enable_normal_log_file": False,  # 关闭普通日志文件（设为True则开启）
    "enable_error_log_file": True  # 保留错误日志文件
}


# 确保日志目录存在
def get_log_dir() -> str:
    try:
        os.makedirs(LOG_CONFIG["log_dir"], exist_ok=True)
        if os.path.exists(LOG_CONFIG["log_dir"]):
            print(f"【调试】日志目录创建成功：{LOG_CONFIG['log_dir']}")
        else:
            print(f"【调试】日志目录创建失败：{LOG_CONFIG['log_dir']}")
    except Exception as e:
        print(f"【调试】创建日志目录报错：{str(e)}")
    return LOG_CONFIG["log_dir"]

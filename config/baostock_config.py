import os
from typing import Dict, Any

from config.base_config import BaseConfig, singleton


def get_stock_daly_fields() -> Dict[str, Any]:
    return {
        'date': 'stock_date',
        'code': 'stock_code',
        'open': 'open_price',
        'high': 'high_price',
        'low': 'low_price',
        'close': 'close_price',
        'volume': 'trading_volume',
        'amount': 'trading_amount',
        'adjustflag': 'adjust_flag',
        'turn': 'turn',
        'pctChg': 'ups_and_downs',
        'peTTM': 'rolling_p',
        'pbMRQ': 'pb_ratio',
        'psTTM': 'rolling_pts_ratio',
        'pcfNcfTTM': 'rolling_current_ratio',
        'isST': 'if_st'
    }


def get_stock_week_fields() -> Dict[str, Any]:
    return {
        'date': 'stock_date',
        'code': 'stock_code',
        'open': 'open_price',
        'high': 'high_price',
        'low': 'low_price',
        'close': 'close_price',
        'volume': 'trading_volume',
        'amount': 'trading_amount',
        'adjustflag': 'adjust_flag',
        'turn': 'turn',
        'pctChg': 'ups_and_downs'
    }


def get_stock_month_fields() -> Dict[str, Any]:
    return {
        'date': 'stock_date',
        'code': 'stock_code',
        'open': 'open_price',
        'high': 'high_price',
        'low': 'low_price',
        'close': 'close_price',
        'volume': 'trading_volume',
        'amount': 'trading_amount',
        'adjustflag': 'adjust_flag',
        'turn': 'turn',
        'pctChg': 'ups_and_downs'
    }


# updateDate	code	code_name	industry	industryClassification
def get_stock_industry_fields() -> Dict[str, Any]:
    return {
        'code': 'stock_code',
        'updateDate': 'update_date',
        'code_name': 'stock_name',
        'industry': 'industry',
        'industryClassification': 'industry_classification'
    }


@singleton  # 单例模式，避免重复加载
class BAOSTOCK_CONFIG(BaseConfig[Dict[str, Any]]):
    """Baostock配置类（继承通用基类，完善频率配置）"""

    def __init__(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(current_dir, "config.ini")
        super().__init__(config_path=config_path, section="baostock")

    def get_config(self) -> Dict[str, Any]:
        """获取Baostock完整配置（包含所有频率和字段）"""
        return {
            # K线字段配置
            "date_stock_fields": self.get_str(
                "date_stock_fields",
                fallback="date,code,open,high,low,close,preclose,volume,amount,adjustflag,turn,tradestatus,pctChg,peTTM,pbMRQ,psTTM,pcfNcfTTM,isST"
            ),
            "week_stock_fields": self.get_str(
                "week_stock_fields",
                fallback="date,code,open,high,low,close,volume,amount,adjustflag,turn,pctChg"
            ),
            "month_stock_fields": self.get_str(
                "month_stock_fields",
                fallback="date,code,open,high,low,close,volume,amount,adjustflag,turn,pctChg"
            ),
            # 频率配置（日/周/月）
            "day_frequency": self.get_str("day_frequency", fallback="d"),
            "week_frequency": self.get_str("week_frequency", fallback="w"),
            "month_frequency": self.get_str("month_frequency", fallback="m"),
            # 复权类型（0-不复权，1-前复权，2-后复权，3-定点复权）
            "adjustflag": self.get_str("adjustflag", fallback="3")
        }


# 简化单例获取方法
def get_baostock_config_instance() -> BAOSTOCK_CONFIG:
    """获取Baostock配置单例对象"""
    return BAOSTOCK_CONFIG()


# 快捷获取配置字典的方法（推荐）
def get_baostock_config() -> Dict[str, Any]:
    """直接获取Baostock配置字典，简化调用"""
    return get_baostock_config_instance().get_config()

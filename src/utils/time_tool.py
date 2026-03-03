from __future__ import annotations

from datetime import datetime, timedelta

import holidays
import pandas as pd


def get_last_some_time(day):
    # 获取当前时间
    current_time = datetime.now()
    # 减去一天
    previous_day = current_time - timedelta(days=day)
    return previous_day.strftime('%Y-%m-%d')


def is_trading_day(date):
    # 创建中国节假日实例
    cn_holidays = holidays.country_holidays('CN', years=[date.year])  # 指定年份以提高效率
    """ 判断给定日期是否为交易日（非周末且非节假日） """
    if date.weekday() < 5 and date not in cn_holidays:
        return True
    return False


def find_last_trading_day_of_week(given_date):
    date = pd.to_datetime(given_date)
    # 创建中国节假日实例
    cn_holidays = holidays.country_holidays('CN', years=[date.year])  # 指定年份以提高效率
    """
    找到给定日期所在周的周五，并返回该周最后一个交易日
    """
    # 计算给定日期所在周的周五
    friday_of_week = date - pd.Timedelta(days=date.weekday() - 4)  # 4表示周五
    if friday_of_week < date:
        friday_of_week += pd.Timedelta(days=7)  # 如果周五在给定日期之前，则加一周
    # 向前查找最近的交易日
    current_day = friday_of_week
    while current_day.weekday() > 4 or current_day in cn_holidays:  # 如果是周末或节假日
        current_day -= pd.Timedelta(days=1)
    return current_day.date()


def find_last_trading_day_of_month(given_date):
    date = pd.to_datetime(given_date)
    """ 找到给定日期所在月份的最后一天，并返回该月最后一个交易日 """
    last_day_of_month = (date + pd.offsets.MonthEnd(0)).date()

    while not is_trading_day(last_day_of_month):
        last_day_of_month -= pd.Timedelta(days=1)

    return last_day_of_month


def find_first_trading_day_of_week(given_date):
    """
    给定一个日期，返回该日期所在周的第一个交易日。

    参数:
        given_date (str or datetime): 输入的日期。

    返回:
        date: 该周的第一个交易日。
    """
    # 将输入日期转换为datetime对象
    date = pd.to_datetime(given_date)

    # 创建中国节假日实例
    cn_holidays = holidays.CountryHoliday('CN', years=[date.year])  # 指定年份以提高效率

    # 计算给定日期所在周的周一
    monday_of_week = date - pd.offsets.Day(date.weekday())  # weekday()返回0表示周一

    # 向前查找最近的交易日
    current_day = monday_of_week
    while current_day.weekday() > 4 or current_day in cn_holidays:  # 如果是周末或节假日
        current_day += pd.Timedelta(days=1)  # 如果是周末或假日，则跳过这一天

    return current_day.date()


# 是否是周末 传入字符串日期
def is_weekend(date):
    return datetime.strptime(date, '%Y-%m-%d').weekday() > 4


# 当前时间是否是月初第一天 并且是周末 传入字符串日期
def is_last_day_of_month(date):
    return datetime.strptime(date, '%Y-%m-%d').day == 1 and is_weekend(date)


if __name__ == '__main__':
    print(find_last_trading_day_of_week('1990-12-21'))

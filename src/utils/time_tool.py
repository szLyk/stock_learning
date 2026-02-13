from datetime import datetime, timedelta


def get_last_some_time(day):
    # 获取当前时间
    current_time = datetime.now()
    # 减去一天
    previous_day = current_time - timedelta(days=day)
    return previous_day.strftime('%Y-%m-%d')

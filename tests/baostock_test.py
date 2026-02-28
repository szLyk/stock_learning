from src.utils.baosock_tool import BaostockFetcher
from src.utils.Indicator_calculation_tool import IndicatorCalculator

if __name__ == '__main__':
    # fetcher = BaostockFetcher()
    # fetcher.init_stock_date_week_month()
    # fetcher.close()
    indicator_calculator = IndicatorCalculator()
    indicator_calculator.run_batch_obv_all_time_period()
    indicator_calculator.close()

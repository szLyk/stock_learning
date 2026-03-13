from src.utils.baosock_tool import BaostockFetcher
from src.utils.indicator_calculation_tool import IndicatorCalculator

if __name__ == '__main__':
    baostock_fetcher = BaostockFetcher()
    baostock_fetcher.process_stock(stock_code='sh.603083',date_type='min')
    baostock_fetcher.close()

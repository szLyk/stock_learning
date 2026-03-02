from src.utils.baosock_tool import BaostockFetcher
from src.utils.Indicator_calculation_tool import IndicatorCalculator

if __name__ == '__main__':
    fetcher = BaostockFetcher()
    fetcher.batch_process_stock_data('kd', update_record_table='update_index_stock_record')
    fetcher.batch_process_stock_data('kw', update_record_table='update_index_stock_record')
    fetcher.batch_process_stock_data('km', update_record_table='update_index_stock_record')
    fetcher.close()
    # indicator_calculator = IndicatorCalculator()
    # indicator_calculator.run_batch_obv_all_time_period()
    # indicator_calculator.close()

from src.utils.baosock_tool import BaostockFetcher
from src.utils.indicator_calculation_tool import IndicatorCalculator

if __name__ == '__main__':
    fetcher = BaostockFetcher()
    # fetcher.batch_process_stock_data('kd', update_record_table='update_index_stock_record')
    # fetcher.batch_process_stock_data('kw', update_record_table='update_index_stock_record')
    # fetcher.batch_process_stock_data('km', update_record_table='update_index_stock_record')
    fetcher.batch_process_stock_data_all_time_period()
    # df = fetcher.fetch_daily_data(fetcher.get_daily_type('d'), '600000.sh', '2026-03-05', '2026-03-05')
    # print(df)
    fetcher.close()
    # indicator_calculator = IndicatorCalculator()
    # indicator_calculator.run_batch_adx_all_time_period()
    # indicator_calculator.close()

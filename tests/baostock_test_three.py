from src.utils.baosock_tool import BaostockFetcher
from src.utils.indicator_calculation_tool import IndicatorCalculator

if __name__ == '__main__':
    indicator_calculator = IndicatorCalculator()
    indicator_calculator.run_batch_ma_all_time_period()
    indicator_calculator.run_batch_macd_all_time_period()
    indicator_calculator.run_batch_boll_all_time_period()
    indicator_calculator.run_batch_obv_all_time_period()
    indicator_calculator.run_batch_rsi_all_time_period()
    indicator_calculator.run_batch_cci_all_time_period()
    indicator_calculator.run_batch_adx_all_time_period()
    indicator_calculator.close()

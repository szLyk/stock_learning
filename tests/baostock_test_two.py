#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
利润表数据采集测试工具
独立运行，不依赖 XXL-JOB
"""
from src.utils.atr_calculation_tool import run_batch_ma_all_time_period
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
    run_batch_ma_all_time_period()
    indicator_calculator.close()

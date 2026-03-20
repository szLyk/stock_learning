from config.base_config import singleton


@singleton  # 单例模式，避免重复加载
class INDICATOR_CONFIG:

    def get_ma_type(self, date_type='d'):
        if date_type == 'w':
            return {
                'update_column': 'update_stock_week_ma',
                'data_table': 'stock_history_week_price',
                'update_table': 'week_stock_moving_average_table',
                'frequency': 10,
                'update_record_table': 'update_stock_record',
                'tradestatus': ' '
            }
        if date_type == 'm':
            return {
                'update_column': 'update_stock_month_ma',
                'data_table': 'stock_history_month_price',
                'update_table': 'month_stock_moving_average_table',
                'frequency': 30,
                'update_record_table': 'update_stock_record',
                'tradestatus': ' '
            }

        return {
            'update_column': 'update_stock_date_ma',
            'data_table': 'stock_history_date_price',
            'update_table': 'date_stock_moving_average_table',
            'frequency': 2,
            'update_record_table': 'update_stock_record',
            'tradestatus': ' AND tradestatus = 1 '
        }

    def get_macd_type(self, date_type='d'):
        if date_type == 'w':
            return {
                'update_column': 'update_stock_week_macd',
                'data_table': 'stock_history_week_price',
                'update_table': 'week_stock_macd',
                'update_record_table': 'update_stock_record',
                'frequency': 10
            }
        if date_type == 'm':
            return {
                'update_column': 'update_stock_month_macd',
                'data_table': 'stock_history_month_price',
                'update_table': 'month_stock_macd',
                'update_record_table': 'update_stock_record',
                'frequency': 30
            }

        return {
            'update_column': 'update_stock_date_macd',
            'data_table': 'stock_history_date_price',
            'update_table': 'date_stock_macd',
            'update_record_table': 'update_stock_record',
            'frequency': 2
        }

    def get_boll_type(self, date_type='d'):
        if date_type == 'w':
            return {
                'update_column': 'update_stock_week_boll',
                'data_table': 'stock_history_week_price',
                'ma_table': 'week_stock_moving_average_table',
                'update_table': 'stock_week_boll',
                'tradestatus': ' ',
                'update_record_table': 'update_stock_record',
                'frequency': 20
            }
        if date_type == 'm':
            return {
                'update_column': 'update_stock_month_boll',
                'data_table': 'stock_history_month_price',
                'ma_table': 'month_stock_moving_average_table',
                'update_table': 'stock_month_boll',
                'tradestatus': ' ',
                'update_record_table': 'update_stock_record',
                'frequency': 40
            }

        return {
            'update_column': 'update_stock_date_boll',
            'data_table': 'stock_history_date_price',
            'ma_table': 'date_stock_moving_average_table',
            'update_table': 'stock_date_boll',
            'tradestatus': ' AND tradestatus = 1 ',
            'update_record_table': 'update_stock_record',
            'frequency': 12
        }

    def get_obv_type(self, date_type='d'):
        if date_type == 'w':
            return {
                'update_column': 'update_stock_week_obv',
                'data_table': 'stock_history_week_price',
                'update_table': 'stock_week_obv',
                'update_record_table': 'update_stock_record',
                'tradestatus': ' '
            }
        if date_type == 'm':
            return {
                'update_column': 'update_stock_month_obv',
                'data_table': 'stock_history_month_price',
                'update_table': 'stock_month_obv',
                'update_record_table': 'update_stock_record',
                'tradestatus': ' '
            }

        return {
            'update_column': 'update_stock_date_obv',
            'data_table': 'stock_history_date_price',
            'update_table': 'stock_date_obv',
            'update_record_table': 'update_stock_record',
            'tradestatus': ' AND tradestatus = 1 '
        }

    def get_rsi_type(self, date_type='d'):
        if date_type == 'w':
            return {
                'update_column': 'update_stock_week_rsi',
                'data_table': 'stock_history_week_price',
                'update_table': 'stock_week_rsi',
                'tradestatus': ' ',
                'update_record_table': 'update_stock_record',
                'frequency': 56
            }
        if date_type == 'm':
            return {
                'update_column': 'update_stock_month_rsi',
                'data_table': 'stock_history_month_price',
                'update_table': 'stock_month_rsi',
                'tradestatus': ' ',
                'update_record_table': 'update_stock_record',
                'frequency': 26
            }

        return {
            'update_column': 'update_stock_date_rsi',
            'data_table': 'stock_history_date_price',
            'update_table': 'stock_date_rsi',
            'tradestatus': ' AND tradestatus = 1 ',
            'update_record_table': 'update_stock_record',
            'frequency': 13
        }

    def get_cci_type(self, date_type='d'):
        if date_type == 'w':
            return {
                'update_column': 'update_stock_week_cci',
                'data_table': 'stock_history_week_price',
                'update_table': 'stock_week_cci',
                'tradestatus': ' ',
                'frequency': 56,
                'update_record_table': 'update_stock_record'
            }
        if date_type == 'm':
            return {
                'update_column': 'update_stock_month_cci',
                'data_table': 'stock_history_month_price',
                'update_table': 'stock_month_cci',
                'tradestatus': ' ',
                'frequency': 28,
                'update_record_table': 'update_stock_record'
            }

        return {
            'update_column': 'update_stock_date_cci',
            'data_table': 'stock_history_date_price',
            'update_table': 'stock_date_cci',
            'tradestatus': ' AND tradestatus = 1 ',
            'frequency': 14,
            'update_record_table': 'update_stock_record'
        }

    def get_adx_type(self, date_type='d'):
        if date_type == 'w':
            return {
                'update_column': 'update_stock_week_adx',
                'data_table': 'stock_history_week_price',
                'update_table': 'stock_week_adx',
                'update_record_table': 'update_stock_record',
                'tradestatus': ' ',
            }
        if date_type == 'm':
            return {
                'update_column': 'update_stock_month_adx',
                'data_table': 'stock_history_month_price',
                'update_table': 'stock_month_adx',
                'update_record_table': 'update_stock_record',
                'tradestatus': ' ',
            }

        return {
            'update_column': 'update_stock_date_adx',
            'data_table': 'stock_history_date_price',
            'update_table': 'stock_date_adx',
            'update_record_table': 'update_stock_record',
            'tradestatus': ' AND tradestatus = 1 ',
        }
    
    def get_atr_type(self, date_type='d'):
        """获取 ATR 指标配置"""
        if date_type == 'w':
            return {
                'update_column': 'update_stock_week_atr',
                'data_table': 'stock_history_week_price',
                'update_table': 'stock_week_atr',
                'tradestatus': ' ',
                'update_record_table': 'update_stock_record',
                'frequency': 56  # 周线需要更多历史数据
            }
        if date_type == 'm':
            return {
                'update_column': 'update_stock_month_atr',
                'data_table': 'stock_history_month_price',
                'update_table': 'stock_month_atr',
                'tradestatus': ' ',
                'update_record_table': 'update_stock_record',
                'frequency': 28  # 月线需要更多历史数据
            }
        
        # 日线
        return {
            'update_column': 'update_stock_date_atr',
            'data_table': 'stock_history_date_price',
            'update_table': 'stock_date_atr',
            'tradestatus': ' AND tradestatus = 1 ',
            'update_record_table': 'update_stock_record',
            'frequency': 14  # 日线需要 14 天以上数据
        }

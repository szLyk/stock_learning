use stock;
-- DROP TABLE IF EXISTS stock.update_stock_record;
CREATE TABLE update_stock_record (
  `id` int NOT NULL AUTO_INCREMENT,
  `stock_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '股票名称',
  `stock_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '股票代码',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `update_stock_date` date DEFAULT '1990-01-01' COMMENT '日线更新记录',
  `update_stock_date_macd` date DEFAULT '1990-01-01' COMMENT '日线MACD更新记录',
  `update_stock_week` date DEFAULT '1990-01-01' COMMENT '周线更新记录',
  `update_stock_week_macd` date DEFAULT '1990-01-01' COMMENT '周线MACD更新记录',
  `update_stock_month` date DEFAULT '1990-01-01' COMMENT '月线更新记录',
  `update_stock_month_macd` date DEFAULT '1990-01-01' COMMENT '月线MACD更新记录',
  `update_stock_date_ma` date DEFAULT '1990-01-01' COMMENT '日均线更新记录',
  `update_stock_week_ma` date DEFAULT '1990-01-01' COMMENT '周均线更新记录',
  `update_stock_month_ma` date DEFAULT '1990-01-01' COMMENT '月均线更新记录',
  `update_stock_date_rsi` date DEFAULT '1990-01-01' COMMENT 'RSI值日线更新记录',
  `update_stock_date_cci` date DEFAULT '1990-01-01' COMMENT 'CCI值日线更新记录',
  `update_stock_date_boll` date DEFAULT '1990-01-01' COMMENT 'BOLL值日线更新记录',
  `update_stock_week_rsi` date DEFAULT '1990-01-01' COMMENT 'RSI值周线更新记录',
  `update_stock_month_rsi` date DEFAULT '1990-01-01' COMMENT 'RSI值月线更新记录',
  `update_stock_week_cci` date DEFAULT '1990-01-01' COMMENT 'CCI值周线更新记录',
  `update_stock_month_cci` date DEFAULT '1990-01-01' COMMENT 'CCI值月线更新记录',
  `update_stock_week_boll` date DEFAULT '1990-01-01' COMMENT 'BOLL值周线更新记录',
  `update_stock_month_boll` date DEFAULT '1990-01-01' COMMENT 'BOLL值月线更新记录',
  `update_stock_date_obv` date DEFAULT '1990-01-01' COMMENT 'OBV值日线更新记录',
  `update_stock_week_obv` date DEFAULT '1990-01-01' COMMENT 'OBV值周线更新记录',
  `update_stock_month_obv` date DEFAULT '1990-01-01' COMMENT 'OBV值月线更新记录',
  `market_type` varchar(10) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `u_index_stock_code` (`stock_code`) USING BTREE,
  KEY `index_stock_name` (`stock_name`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=175987 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='股票更新记录表';

-- DROP TABLE IF EXISTS stock.date_stock_macd;
CREATE TABLE `date_stock_macd` (
  `stock_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '股票代码',
  `stock_date` date NOT NULL COMMENT '股票交易日',
  `close_price` decimal(20,4) DEFAULT NULL COMMENT '收盘价',
  `ema_12` decimal(20,4) DEFAULT NULL COMMENT 'macd中ema12指标',
  `ema_26` decimal(20,4) DEFAULT NULL COMMENT 'macd中ema26指标',
  `diff` decimal(20,4) DEFAULT NULL,
  `dea` decimal(20,4) DEFAULT NULL,
  `macd` decimal(10,4) DEFAULT NULL COMMENT 'macd',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`stock_code`,`stock_date`) USING BTREE,
  KEY `index_stock_date` (`stock_date`) USING BTREE,
  KEY `un_index_stock_code_and_date` (`stock_code`,`stock_date`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='股票日线MACD表（前复权）';

-- DROP TABLE IF EXISTS stock.date_stock_moving_average_table;
CREATE TABLE `date_stock_moving_average_table` (
  `stock_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `stock_date` date NOT NULL,
  `close_price` decimal(20,4) DEFAULT NULL COMMENT '收盘价',
  `stock_ma3` decimal(20,4) DEFAULT NULL COMMENT '3日均线',
  `stock_ma5` decimal(20,4) DEFAULT NULL COMMENT '5日均线',
  `stock_ma6` decimal(20,4) DEFAULT NULL COMMENT '6日均线',
  `stock_ma7` decimal(20,4) DEFAULT NULL COMMENT '7日均线',
  `stock_ma9` decimal(20,4) DEFAULT NULL COMMENT '9日均线',
  `stock_ma10` decimal(20,4) DEFAULT NULL COMMENT '10日均线',
  `stock_ma12` decimal(20,4) DEFAULT NULL COMMENT '12日均线',
  `stock_ma20` decimal(20,4) DEFAULT NULL COMMENT '20日均线',
  `stock_ma24` decimal(20,4) DEFAULT NULL COMMENT '24日均线',
  `stock_ma26` decimal(20,4) DEFAULT NULL COMMENT '26日均线',
  `stock_ma30` decimal(20,4) DEFAULT NULL COMMENT '30日均线',
  `stock_ma60` decimal(20,4) DEFAULT NULL COMMENT '60日均线',
  `stock_ma70` decimal(20,4) DEFAULT NULL COMMENT '70日均线',
  `stock_ma125` decimal(20,4) DEFAULT NULL COMMENT '125日均线',
  `stock_ma250` decimal(20,4) DEFAULT NULL COMMENT '250日均线',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`stock_code`,`stock_date`),
  KEY `index_stock_date` (`stock_date`) USING BTREE,
  KEY `un_index_stock_code_and_date` (`stock_code`,`stock_date`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='股票日线均线表（前复权）';

-- DROP TABLE IF EXISTS stock.month_stock_macd;
CREATE TABLE `month_stock_macd` (
  `stock_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '股票代码',
  `stock_date` date NOT NULL COMMENT '股票交易日',
  `close_price` decimal(20,4) DEFAULT NULL COMMENT '收盘价',
  `ema_12` decimal(20,4) DEFAULT NULL COMMENT 'macd中ema12指标',
  `ema_26` decimal(20,4) DEFAULT NULL COMMENT 'macd中ema26指标',
  `diff` decimal(20,4) DEFAULT NULL,
  `dea` decimal(20,4) DEFAULT NULL,
  `macd` decimal(10,4) DEFAULT NULL COMMENT 'macd',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`stock_code`,`stock_date`),
  KEY `index_stock_date` (`stock_date`) USING BTREE,
  KEY `un_index_stock_code_and_date` (`stock_code`,`stock_date`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='股票周线MACD表（前复权）';

-- DROP TABLE IF EXISTS stock.month_stock_moving_average_table;
CREATE TABLE `month_stock_moving_average_table` (
  `stock_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `stock_date` date NOT NULL,
  `close_price` decimal(20,4) DEFAULT NULL COMMENT '收盘价',
  `stock_ma3` decimal(20,4) DEFAULT NULL COMMENT '3日均线',
  `stock_ma5` decimal(20,4) DEFAULT NULL COMMENT '5日均线',
  `stock_ma6` decimal(20,4) DEFAULT NULL COMMENT '6日均线',
  `stock_ma7` decimal(20,4) DEFAULT NULL COMMENT '7日均线',
  `stock_ma9` decimal(20,4) DEFAULT NULL COMMENT '9日均线',
  `stock_ma10` decimal(20,4) DEFAULT NULL COMMENT '10日均线',
  `stock_ma12` decimal(20,4) DEFAULT NULL COMMENT '12日均线',
  `stock_ma20` decimal(20,4) DEFAULT NULL COMMENT '20日均线',
  `stock_ma24` decimal(20,4) DEFAULT NULL COMMENT '24日均线',
  `stock_ma26` decimal(20,4) DEFAULT NULL COMMENT '26日均线',
  `stock_ma30` decimal(20,4) DEFAULT NULL COMMENT '30日均线',
  `stock_ma60` decimal(20,4) DEFAULT NULL COMMENT '60日均线',
  `stock_ma70` decimal(20,4) DEFAULT NULL COMMENT '70日均线',
  `stock_ma125` decimal(20,4) DEFAULT NULL COMMENT '125日均线',
  `stock_ma250` decimal(20,4) DEFAULT NULL COMMENT '250日均线',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`stock_code`,`stock_date`) USING BTREE,
  KEY `index_stock_date` (`stock_date`) USING BTREE,
  KEY `un_index_stock_code_and_date` (`stock_code`,`stock_date`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='股票月线均线表（前复权）';

-- DROP TABLE IF EXISTS stock.stock_basic;
CREATE TABLE `stock_basic` (
  `id` int NOT NULL AUTO_INCREMENT,
  `update_date` date DEFAULT NULL COMMENT '更新日期',
  `stock_code` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '证券代码',
  `stock_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '证券名称',
  `ipo_date` date DEFAULT NULL COMMENT '上市日期',
  `out_date` date DEFAULT NULL COMMENT '退市日期',
  `stock_type` tinyint DEFAULT NULL COMMENT '证券类型，其中1：股票，2：指数，3：其它，4：可转债，5：ETF',
  `stock_status` tinyint DEFAULT NULL COMMENT '上市状态，其中1：上市，0：退市',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `market_type` varchar(10) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `index_stock_code` (`stock_code`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=125802 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='证券基本资料表';

-- DROP TABLE IF EXISTS stock.stock_date_boll;
CREATE TABLE `stock_date_boll` (
  `stock_code` varchar(20) NOT NULL COMMENT '证券代码',
  `stock_date` date NOT NULL COMMENT '交易所行情日期',
  `boll_twenty` decimal(10,4) DEFAULT NULL COMMENT '布林线中轨',
  `upper_rail` decimal(10,4) DEFAULT NULL COMMENT '布林线上轨',
  `lower_rail` decimal(10,4) DEFAULT NULL COMMENT '布林线下轨',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`stock_code`,`stock_date`) USING BTREE,
  KEY `index_stock_date` (`stock_date`) USING BTREE,
  KEY `index_stock_date_price` (`stock_code`,`stock_date`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='计算股票每日的布林线';

-- DROP TABLE IF EXISTS stock.stock_date_cci;
CREATE TABLE `stock_date_cci` (
  `stock_code` varchar(20) NOT NULL COMMENT '证券代码',
  `stock_date` date NOT NULL COMMENT '交易所行情日期',
  `tp` decimal(10,4) DEFAULT NULL COMMENT '（最高价+最低价+收盘价）÷3',
  `mad` decimal(10,4) DEFAULT NULL COMMENT '平均绝对偏差',
  `cci` decimal(10,4) DEFAULT NULL COMMENT '顺势指标',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`stock_code`,`stock_date`) USING BTREE,
  KEY `index_stock_date` (`stock_date`) USING BTREE,
  KEY `index_stock_date_price` (`stock_code`,`stock_date`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='计算股票每日的顺势指标';

-- DROP TABLE IF EXISTS stock.stock_date_obv;
CREATE TABLE `stock_date_obv` (
  `stock_code` varchar(20) NOT NULL COMMENT '证券代码',
  `stock_date` date NOT NULL COMMENT '交易所行情日期',
  `trading_volume` decimal(20,4) DEFAULT NULL COMMENT '成交量（累计 单位：股）',
  `obv` decimal(20,4) DEFAULT NULL COMMENT '平衡交易量',
  `30ma_obv` decimal(20,4) DEFAULT NULL COMMENT '30日平衡交易量',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`stock_code`,`stock_date`) USING BTREE,
  KEY `index_stock_date` (`stock_date`) USING BTREE,
  KEY `index_stock_date_price` (`stock_code`,`stock_date`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='计算股票每日的平衡交易量';

-- DROP TABLE IF EXISTS stock.stock_date_rsi;
CREATE TABLE `stock_date_rsi` (
  `stock_code` varchar(20) NOT NULL COMMENT '证券代码',
  `stock_date` date NOT NULL COMMENT '交易所行情日期',
  `close_price` decimal(10,4) DEFAULT NULL COMMENT '收盘价',
  `rsi_6` decimal(10,4) DEFAULT NULL COMMENT '6周期',
  `rsi_12` decimal(10,4) DEFAULT NULL COMMENT '12周期',
  `rsi_24` decimal(10,4) DEFAULT NULL COMMENT '24周期',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`stock_code`,`stock_date`) USING BTREE,
  KEY `index_stock_date` (`stock_date`) USING BTREE,
  KEY `index_stock_date_price` (`stock_code`,`stock_date`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='计算股票每日的相对强弱指标';

-- DROP TABLE IF EXISTS stock.stock_date_week_month;
CREATE TABLE `stock_date_week_month` (
  `id` int NOT NULL AUTO_INCREMENT,
  `stock_date` date NOT NULL,
  `stock_week_date` date NOT NULL COMMENT 'A股周线交易日',
  `stock_month_date` date NOT NULL COMMENT 'A股月线交易日',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `index_date` (`stock_date`) USING BTREE,
  KEY `index_week` (`stock_week_date`) USING BTREE,
  KEY `index_month` (`stock_month_date`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=51528 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='交易日周月份对照表';

-- DROP TABLE IF EXISTS stock.stock_history_date_price;
CREATE TABLE `stock_history_date_price` (
  `id` int NOT NULL AUTO_INCREMENT,
  `stock_code` varchar(20) NOT NULL COMMENT '证券代码',
  `stock_date` date NOT NULL COMMENT '交易所行情日期',
  `open_price` decimal(10,4) DEFAULT NULL COMMENT '开盘价',
  `high_price` decimal(10,4) DEFAULT NULL COMMENT '最高价',
  `pre_close` decimal(10,4) DEFAULT NULL COMMENT '前收盘价',
  `low_price` decimal(10,4) DEFAULT NULL COMMENT '最低价',
  `close_price` decimal(10,4) DEFAULT NULL COMMENT '收盘价',
  `trading_volume` decimal(20,4) DEFAULT NULL COMMENT '成交量（累计 单位：股）',
  `trading_amount` decimal(20,4) DEFAULT NULL COMMENT '成交额（单位：人民币元）',
  `adjust_flag` tinyint DEFAULT NULL COMMENT '复权状态(1：后复权， 2：前复权，3：不复权）',
  `turn` decimal(20,4) DEFAULT NULL COMMENT '换手率',
  `tradestatus` tinyint DEFAULT NULL COMMENT '交易状态(1：正常交易 0：停牌）',
  `ups_and_downs` decimal(10,4) DEFAULT NULL COMMENT '涨跌幅（百分比）',
  `if_st` tinyint DEFAULT NULL COMMENT '是否ST股，1是，0否',
  `pb_ratio` decimal(20,4) DEFAULT NULL COMMENT '市净率((指定交易日的股票收盘价/指定交易日的每股净资产)=总市值/(最近披露的归属母公司股东的权益-其他权益工具))',
  `rolling_p` decimal(20,4) DEFAULT NULL COMMENT '(指定交易日的股票收盘价/指定交易日的每股盈余TTM)=(指定交易日的股票收盘价*截至当日公司总股本)/归属母公司股东净利润TTM',
  `rolling_pts_ratio` decimal(20,4) DEFAULT NULL COMMENT '(指定交易日的股票收盘价/指定交易日的每股销售额)=(指定交易日的股票收盘价*截至当日公司总股本)/营业总收入TTM',
  `rolling_current_ratio` decimal(20,4) DEFAULT NULL COMMENT '(指定交易日的股票收盘价/指定交易日的每股现金流TTM)=(指定交易日的股票收盘价*截至当日公司总股本)/现金以及现金等价物净增加额TTM',
  `market_type` varchar(5) NOT NULL COMMENT '证券市场 sz|sh',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `index_stock_date_price` (`stock_code`,`stock_date`) USING BTREE,
  KEY `index_tradestatus` (`tradestatus`) USING BTREE,
  KEY `index_stock_date` (`stock_date`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=35840536 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='股票日线价格表（前复权）';

-- DROP TABLE IF EXISTS stock.stock_history_month_price;
CREATE TABLE `stock_history_month_price` (
  `id` int NOT NULL AUTO_INCREMENT,
  `stock_code` varchar(20) NOT NULL COMMENT '证券代码',
  `stock_date` date NOT NULL COMMENT '交易所行情日期',
  `open_price` decimal(10,4) DEFAULT NULL COMMENT '开盘价',
  `high_price` decimal(10,4) DEFAULT NULL COMMENT '最高价',
  `low_price` decimal(10,4) DEFAULT NULL COMMENT '最低价',
  `close_price` decimal(10,4) DEFAULT NULL COMMENT '收盘价',
  `trading_volume` decimal(20,4) DEFAULT NULL COMMENT '成交量（累计 单位：股）',
  `trading_amount` decimal(20,4) DEFAULT NULL COMMENT '成交额（单位：人民币元）',
  `adjust_flag` tinyint DEFAULT NULL COMMENT '复权状态(1：后复权， 2：前复权，3：不复权）',
  `turn` decimal(20,4) DEFAULT NULL COMMENT '换手率',
  `ups_and_downs` decimal(10,4) DEFAULT NULL COMMENT '涨跌幅（百分比）',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `market_type` varchar(10) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `index_stock_date_price` (`stock_code`,`stock_date`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=1708958 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='股票月线价格表（前复权）';

-- DROP TABLE IF EXISTS stock.stock_month_boll;
CREATE TABLE `stock_month_boll` (
  `id` int NOT NULL AUTO_INCREMENT,
  `stock_code` varchar(20) NOT NULL COMMENT '证券代码',
  `stock_date` date NOT NULL COMMENT '交易所行情日期',
  `boll_twenty` decimal(10,4) DEFAULT NULL COMMENT '布林线中轨',
  `upper_rail` decimal(10,4) DEFAULT NULL COMMENT '布林线上轨',
  `lower_rail` decimal(10,4) DEFAULT NULL COMMENT '布林线下轨',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `index_stock_date_price` (`stock_code`,`stock_date`) USING BTREE,
  KEY `index_stock_date` (`stock_date`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='计算股票每月的布林线';

-- DROP TABLE IF EXISTS stock.stock_month_cci;
CREATE TABLE `stock_month_cci` (
  `stock_code` varchar(20) NOT NULL COMMENT '证券代码',
  `stock_date` date NOT NULL COMMENT '交易所行情日期',
  `tp` decimal(10,4) DEFAULT NULL COMMENT '（最高价+最低价+收盘价）÷3',
  `mad` decimal(10,4) DEFAULT NULL COMMENT '平均绝对偏差',
  `cci` decimal(10,4) DEFAULT NULL COMMENT '顺势指标',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`stock_code`,`stock_date`) USING BTREE,
  KEY `index_stock_date` (`stock_date`) USING BTREE,
  KEY `index_stock_date_price` (`stock_code`,`stock_date`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='计算股票每月的顺势指标';

-- DROP TABLE IF EXISTS stock.stock_month_obv;
CREATE TABLE `stock_month_obv` (
  `stock_code` varchar(20) NOT NULL COMMENT '证券代码',
  `stock_date` date NOT NULL COMMENT '交易所行情日期',
  `trading_volume` decimal(20,4) DEFAULT NULL COMMENT '成交量（累计 单位：股）',
  `obv` decimal(20,4) DEFAULT NULL COMMENT '平衡交易量',
  `30ma_obv` decimal(20,4) DEFAULT NULL COMMENT '30日平衡交易量',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`stock_code`,`stock_date`) USING BTREE,
  KEY `index_stock_date` (`stock_date`) USING BTREE,
  KEY `index_stock_date_price` (`stock_code`,`stock_date`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='计算股票每月的平衡交易量';

-- DROP TABLE IF EXISTS stock.stock_month_rsi;
CREATE TABLE `stock_month_rsi` (
  `stock_code` varchar(20) NOT NULL COMMENT '证券代码',
  `stock_date` date NOT NULL COMMENT '交易所行情日期',
  `close_price` decimal(10,4) DEFAULT NULL COMMENT '收盘价',
  `rsi_6` decimal(10,4) DEFAULT NULL COMMENT '6周期',
  `rsi_12` decimal(10,4) DEFAULT NULL COMMENT '12周期',
  `rsi_24` decimal(10,4) DEFAULT NULL COMMENT '24周期',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`stock_code`,`stock_date`) USING BTREE,
  KEY `index_stock_date` (`stock_date`) USING BTREE,
  KEY `index_stock_date_price` (`stock_code`,`stock_date`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='计算股票每月的相对强弱指标';

-- DROP TABLE IF EXISTS stock.stock_week_boll;
CREATE TABLE `stock_week_boll` (
  `id` int NOT NULL AUTO_INCREMENT,
  `stock_code` varchar(20) NOT NULL COMMENT '证券代码',
  `stock_date` date NOT NULL COMMENT '交易所行情日期',
  `boll_twenty` decimal(10,4) DEFAULT NULL COMMENT '布林线中轨',
  `upper_rail` decimal(10,4) DEFAULT NULL COMMENT '布林线上轨',
  `lower_rail` decimal(10,4) DEFAULT NULL COMMENT '布林线下轨',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `index_stock_date_price` (`stock_code`,`stock_date`) USING BTREE,
  KEY `index_stock_date` (`stock_date`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='计算股票每周的布林线';

-- DROP TABLE IF EXISTS stock.stock_week_cci;
CREATE TABLE `stock_week_cci` (
  `stock_code` varchar(20) NOT NULL COMMENT '证券代码',
  `stock_date` date NOT NULL COMMENT '交易所行情日期',
  `tp` decimal(10,4) DEFAULT NULL COMMENT '（最高价+最低价+收盘价）÷3',
  `mad` decimal(10,4) DEFAULT NULL COMMENT '平均绝对偏差',
  `cci` decimal(10,4) DEFAULT NULL COMMENT '顺势指标',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`stock_code`,`stock_date`) USING BTREE,
  KEY `index_stock_date` (`stock_date`) USING BTREE,
  KEY `index_stock_date_price` (`stock_code`,`stock_date`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='计算股票每周的顺势指标';

-- DROP TABLE IF EXISTS stock.stock_week_obv;
CREATE TABLE `stock_week_obv` (
  `stock_code` varchar(20) NOT NULL COMMENT '证券代码',
  `stock_date` date NOT NULL COMMENT '交易所行情日期',
  `trading_volume` decimal(20,4) DEFAULT NULL COMMENT '成交量（累计 单位：股）',
  `obv` decimal(20,4) DEFAULT NULL COMMENT '平衡交易量',
  `30ma_obv` decimal(20,4) DEFAULT NULL COMMENT '30日平衡交易量',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`stock_code`,`stock_date`) USING BTREE,
  KEY `index_stock_date` (`stock_date`) USING BTREE,
  KEY `index_stock_date_price` (`stock_code`,`stock_date`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='计算股票每周的平衡交易量';

-- DROP TABLE IF EXISTS stock.stock_week_rsi;
CREATE TABLE `stock_week_rsi` (
  `stock_code` varchar(20) NOT NULL COMMENT '证券代码',
  `stock_date` date NOT NULL COMMENT '交易所行情日期',
  `close_price` decimal(10,4) DEFAULT NULL COMMENT '收盘价',
  `rsi_6` decimal(10,4) DEFAULT NULL COMMENT '6周期',
  `rsi_12` decimal(10,4) DEFAULT NULL COMMENT '12周期',
  `rsi_24` decimal(10,4) DEFAULT NULL COMMENT '24周期',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`stock_code`,`stock_date`) USING BTREE,
  KEY `index_stock_date` (`stock_date`) USING BTREE,
  KEY `index_stock_date_price` (`stock_code`,`stock_date`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='计算股票每周的相对强弱指标';

-- DROP TABLE IF EXISTS stock.week_stock_macd;
CREATE TABLE `week_stock_macd` (
  `stock_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '股票代码',
  `stock_date` date NOT NULL COMMENT '股票交易日',
  `close_price` decimal(20,4) DEFAULT NULL COMMENT '收盘价',
  `ema_12` decimal(20,4) DEFAULT NULL COMMENT 'macd中ema12指标',
  `ema_26` decimal(20,4) DEFAULT NULL COMMENT 'macd中ema26指标',
  `diff` decimal(20,4) DEFAULT NULL,
  `dea` decimal(20,4) DEFAULT NULL,
  `macd` decimal(10,4) DEFAULT NULL COMMENT 'macd',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`stock_code`,`stock_date`),
  KEY `index_stock_date` (`stock_date`) USING BTREE,
  KEY `un_index_stock_code_and_date` (`stock_code`,`stock_date`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='股票周线MACD表（前复权）';

-- DROP TABLE IF EXISTS stock.week_stock_moving_average_table;
CREATE TABLE `week_stock_moving_average_table` (
  `stock_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `stock_date` date NOT NULL,
  `close_price` decimal(20,4) DEFAULT NULL COMMENT '收盘价',
  `stock_ma3` decimal(20,4) DEFAULT NULL COMMENT '3日均线',
  `stock_ma5` decimal(20,4) DEFAULT NULL COMMENT '5日均线',
  `stock_ma6` decimal(20,4) DEFAULT NULL COMMENT '6日均线',
  `stock_ma7` decimal(20,4) DEFAULT NULL COMMENT '7日均线',
  `stock_ma9` decimal(20,4) DEFAULT NULL COMMENT '9日均线',
  `stock_ma10` decimal(20,4) DEFAULT NULL COMMENT '10日均线',
  `stock_ma12` decimal(20,4) DEFAULT NULL COMMENT '12日均线',
  `stock_ma20` decimal(20,4) DEFAULT NULL COMMENT '20日均线',
  `stock_ma24` decimal(20,4) DEFAULT NULL COMMENT '24日均线',
  `stock_ma26` decimal(20,4) DEFAULT NULL COMMENT '26日均线',
  `stock_ma30` decimal(20,4) DEFAULT NULL COMMENT '30日均线',
  `stock_ma60` decimal(20,4) DEFAULT NULL COMMENT '60日均线',
  `stock_ma70` decimal(20,4) DEFAULT NULL COMMENT '70日均线',
  `stock_ma125` decimal(20,4) DEFAULT NULL COMMENT '125日均线',
  `stock_ma250` decimal(20,4) DEFAULT NULL COMMENT '250日均线',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`stock_code`,`stock_date`) USING BTREE,
  KEY `index_stock_date` (`stock_date`) USING BTREE,
  KEY `un_index_stock_code_and_date` (`stock_code`,`stock_date`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='股票周线均线表（前复权）';

-- drop table IF EXISTS index_stock_history_date_price;
CREATE TABLE IF NOT EXISTS `index_stock_history_date_price` (
  `id` int NOT NULL AUTO_INCREMENT,
  `stock_code` varchar(20) NOT NULL COMMENT '证券代码',
  `stock_date` date NOT NULL COMMENT '交易所行情日期',
  `open_price` decimal(10,4) DEFAULT NULL COMMENT '开盘价',
  `high_price` decimal(10,4) DEFAULT NULL COMMENT '最高价',
  `pre_close` decimal(10,4) DEFAULT NULL COMMENT '前收盘价',
  `low_price` decimal(10,4) DEFAULT NULL COMMENT '最低价',
  `close_price` decimal(10,4) DEFAULT NULL COMMENT '收盘价',
  `trading_volume` decimal(20,4) DEFAULT NULL COMMENT '成交量（累计 单位：股）',
  `trading_amount` decimal(20,4) DEFAULT NULL COMMENT '成交额（单位：人民币元）',
  `ups_and_downs` decimal(10,4) DEFAULT NULL COMMENT '涨跌幅（百分比）',
  `market_type` varchar(5) NOT NULL COMMENT '证券市场 sz|sh',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `index_stock_date_price` (`stock_code`,`stock_date`) USING BTREE,
  KEY `index_market_type` (`stock_code`,`market_type`) USING BTREE,
  KEY `index_stock_date` (`stock_date`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='指数数据表';

-- drop table IF EXISTS index_stock_history_week_price;
CREATE TABLE IF NOT EXISTS `index_stock_history_week_price` (
  `id` int NOT NULL AUTO_INCREMENT,
  `stock_code` varchar(20) NOT NULL COMMENT '证券代码',
  `stock_date` date NOT NULL COMMENT '交易所行情日期',
  `open_price` decimal(10,4) DEFAULT NULL COMMENT '开盘价',
  `high_price` decimal(10,4) DEFAULT NULL COMMENT '最高价',
  `low_price` decimal(10,4) DEFAULT NULL COMMENT '最低价',
  `close_price` decimal(10,4) DEFAULT NULL COMMENT '收盘价',
  `trading_volume` decimal(20,4) DEFAULT NULL COMMENT '成交量（累计 单位：股）',
  `trading_amount` decimal(20,4) DEFAULT NULL COMMENT '成交额（单位：人民币元）',
  `ups_and_downs` decimal(10,4) DEFAULT NULL COMMENT '涨跌幅（百分比）',
  `market_type` varchar(5) NOT NULL COMMENT '证券市场 sz|sh',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `index_stock_date_price` (`stock_code`,`stock_date`) USING BTREE,
  KEY `index_market_type` (`stock_code`,`market_type`) USING BTREE,
  KEY `index_stock_date` (`stock_date`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='指数数据表';

-- drop table IF EXISTS index_stock_history_month_price;
CREATE TABLE IF NOT EXISTS `index_stock_history_month_price` (
  `id` int NOT NULL AUTO_INCREMENT,
  `stock_code` varchar(20) NOT NULL COMMENT '证券代码',
  `stock_date` date NOT NULL COMMENT '交易所行情日期',
  `open_price` decimal(10,4) DEFAULT NULL COMMENT '开盘价',
  `high_price` decimal(10,4) DEFAULT NULL COMMENT '最高价',
  `low_price` decimal(10,4) DEFAULT NULL COMMENT '最低价',
  `close_price` decimal(10,4) DEFAULT NULL COMMENT '收盘价',
  `trading_volume` decimal(20,4) DEFAULT NULL COMMENT '成交量（累计 单位：股）',
  `trading_amount` decimal(20,4) DEFAULT NULL COMMENT '成交额（单位：人民币元）',
  `ups_and_downs` decimal(10,4) DEFAULT NULL COMMENT '涨跌幅（百分比）',
  `market_type` varchar(5) NOT NULL COMMENT '证券市场 sz|sh',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `index_stock_date_price` (`stock_code`,`stock_date`) USING BTREE,
  KEY `index_market_type` (`stock_code`,`market_type`) USING BTREE,
  KEY `index_stock_date` (`stock_date`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='指数数据表';


-- drop table IF EXISTS update_index_stock_record;
CREATE TABLE IF NOT EXISTS `update_index_stock_record` (
  `id` int NOT NULL AUTO_INCREMENT,
  `stock_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '股票名称',
  `stock_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '股票代码',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `update_index_stock_date` date DEFAULT '1990-01-01' COMMENT '日线更新记录',
  `update_index_stock_week` date DEFAULT '1990-01-01' COMMENT '周线更新记录',
  `update_index_stock_month` date DEFAULT '1990-01-01' COMMENT '月线更新记录',
	`stock_type` tinyint DEFAULT NULL COMMENT '证券类型，其中1：股票，2：指数，3：其它，4：可转债，5：ETF',
  `market_type` varchar(10) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `u_index_stock_code` (`stock_code`) USING BTREE,
  KEY `index_stock_name` (`stock_name`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='指数更新记录表';
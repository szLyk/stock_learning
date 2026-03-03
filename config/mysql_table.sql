-- 自动生成 stock 库表结构
-- 时间: 1.4.6 | Database: stock

USE `stock`;

-- --------------------------------------------------------
-- Table structure for table `date_stock_macd`
-- --------------------------------------------------------
DROP TABLE IF EXISTS `date_stock_macd`;
CREATE TABLE `date_stock_macd` (
  `stock_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '股票代码',
  `stock_date` date NOT NULL COMMENT '股票交易日',
  `close_price` decimal(20,4) DEFAULT NULL COMMENT '收盘价',
  `diff` decimal(20,4) DEFAULT NULL,
  `dea` decimal(20,4) DEFAULT NULL,
  `macd` decimal(10,4) DEFAULT NULL COMMENT 'macd',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`stock_code`,`stock_date`) USING BTREE,
  KEY `index_stock_date` (`stock_date`) USING BTREE,
  KEY `un_index_stock_code_and_date` (`stock_code`,`stock_date`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='股票日线MACD表（后复权）';

-- --------------------------------------------------------
-- Table structure for table `date_stock_moving_average_table`
-- --------------------------------------------------------
DROP TABLE IF EXISTS `date_stock_moving_average_table`;
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='股票日线均线表（后复权）';

-- --------------------------------------------------------
-- Table structure for table `index_stock_history_date_price`
-- --------------------------------------------------------
DROP TABLE IF EXISTS `index_stock_history_date_price`;
CREATE TABLE `index_stock_history_date_price` (
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
) ENGINE=InnoDB AUTO_INCREMENT=2279502 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='指数数据表';

-- --------------------------------------------------------
-- Table structure for table `index_stock_history_month_price`
-- --------------------------------------------------------
DROP TABLE IF EXISTS `index_stock_history_month_price`;
CREATE TABLE `index_stock_history_month_price` (
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
) ENGINE=InnoDB AUTO_INCREMENT=107988 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='指数数据表';

-- --------------------------------------------------------
-- Table structure for table `index_stock_history_week_price`
-- --------------------------------------------------------
DROP TABLE IF EXISTS `index_stock_history_week_price`;
CREATE TABLE `index_stock_history_week_price` (
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
) ENGINE=InnoDB AUTO_INCREMENT=842283 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='指数数据表';

-- --------------------------------------------------------
-- Table structure for table `month_stock_macd`
-- --------------------------------------------------------
DROP TABLE IF EXISTS `month_stock_macd`;
CREATE TABLE `month_stock_macd` (
  `stock_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '股票代码',
  `stock_date` date NOT NULL COMMENT '股票交易日',
  `close_price` decimal(20,4) DEFAULT NULL COMMENT '收盘价',
  `diff` decimal(20,4) DEFAULT NULL,
  `dea` decimal(20,4) DEFAULT NULL,
  `macd` decimal(10,4) DEFAULT NULL COMMENT 'macd',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`stock_code`,`stock_date`),
  KEY `index_stock_date` (`stock_date`) USING BTREE,
  KEY `un_index_stock_code_and_date` (`stock_code`,`stock_date`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='股票周线MACD表（后复权）';

-- --------------------------------------------------------
-- Table structure for table `month_stock_moving_average_table`
-- --------------------------------------------------------
DROP TABLE IF EXISTS `month_stock_moving_average_table`;
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='股票月线均线表（后复权）';

-- --------------------------------------------------------
-- Table structure for table `stock_basic`
-- --------------------------------------------------------
DROP TABLE IF EXISTS `stock_basic`;
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
  UNIQUE KEY `index_stock_code` (`stock_code`,`market_type`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=329336 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='证券基本资料表';

-- --------------------------------------------------------
-- Table structure for table `stock_date_adx`
-- --------------------------------------------------------
DROP TABLE IF EXISTS `stock_date_adx`;
CREATE TABLE `stock_date_adx` (
  `stock_code` varchar(20) NOT NULL COMMENT '证券代码',
  `stock_date` date NOT NULL COMMENT '交易所行情日期',
  `adx` decimal(10,4) DEFAULT NULL COMMENT '平均趋向指数（ADX），衡量趋势强度，无方向性',
  `plus_di` decimal(10,4) DEFAULT NULL COMMENT '正向指标（+DI），反映上涨趋势强度',
  `minus_di` decimal(10,4) DEFAULT NULL COMMENT '负向指标（-DI），反映下跌趋势强度',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`stock_code`,`stock_date`) USING BTREE,
  KEY `index_stock_date` (`stock_date`) USING BTREE,
  KEY `index_stock_date_price` (`stock_code`,`stock_date`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='股票日线ADX指标计算结果表（含ADX、+DI、-DI）';

-- --------------------------------------------------------
-- Table structure for table `stock_date_boll`
-- --------------------------------------------------------
DROP TABLE IF EXISTS `stock_date_boll`;
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

-- --------------------------------------------------------
-- Table structure for table `stock_date_cci`
-- --------------------------------------------------------
DROP TABLE IF EXISTS `stock_date_cci`;
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

-- --------------------------------------------------------
-- Table structure for table `stock_date_obv`
-- --------------------------------------------------------
DROP TABLE IF EXISTS `stock_date_obv`;
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

-- --------------------------------------------------------
-- Table structure for table `stock_date_rsi`
-- --------------------------------------------------------
DROP TABLE IF EXISTS `stock_date_rsi`;
CREATE TABLE `stock_date_rsi` (
  `stock_code` varchar(20) NOT NULL COMMENT '证券代码',
  `stock_date` date NOT NULL COMMENT '交易所行情日期',
  `rsi_6` decimal(10,4) DEFAULT NULL COMMENT '6周期',
  `rsi_12` decimal(10,4) DEFAULT NULL COMMENT '12周期',
  `rsi_24` decimal(10,4) DEFAULT NULL COMMENT '24周期',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`stock_code`,`stock_date`) USING BTREE,
  KEY `index_stock_date` (`stock_date`) USING BTREE,
  KEY `index_stock_date_price` (`stock_code`,`stock_date`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='计算股票每日的相对强弱指标';

-- --------------------------------------------------------
-- Table structure for table `stock_date_week_month`
-- --------------------------------------------------------
DROP TABLE IF EXISTS `stock_date_week_month`;
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
) ENGINE=InnoDB AUTO_INCREMENT=99481 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='交易日周月份对照表';

-- --------------------------------------------------------
-- Table structure for table `stock_history_date_price`
-- --------------------------------------------------------
DROP TABLE IF EXISTS `stock_history_date_price`;
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
  KEY `index_stock_date` (`stock_date`) USING BTREE,
  KEY `index_stock_market` (`stock_code`,`market_type`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=35984577 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='股票日线价格表（后复权）';

-- --------------------------------------------------------
-- Table structure for table `stock_history_min_price`
-- --------------------------------------------------------
DROP TABLE IF EXISTS `stock_history_min_price`;
CREATE TABLE `stock_history_min_price` (
  `stock_code` varchar(20) NOT NULL COMMENT '证券代码',
  `stock_date` date NOT NULL COMMENT '交易所行情日期',
  `stock_time` varchar(50) NOT NULL,
  `open_price` decimal(10,4) DEFAULT NULL COMMENT '开盘价',
  `high_price` decimal(10,4) DEFAULT NULL COMMENT '最高价',
  `low_price` decimal(10,4) DEFAULT NULL COMMENT '最低价',
  `close_price` decimal(10,4) DEFAULT NULL COMMENT '收盘价',
  `trading_volume` decimal(20,4) DEFAULT NULL COMMENT '成交量（累计 单位：股）',
  `trading_amount` decimal(20,4) DEFAULT NULL COMMENT '成交额（单位：人民币元）',
  `market_type` varchar(5) NOT NULL COMMENT '证券市场 sz|sh',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `min_type` int NOT NULL DEFAULT '15' COMMENT '15|30|90|120 分钟线',
  `adjust_flag` tinyint DEFAULT NULL,
  PRIMARY KEY (`stock_code`,`market_type`,`stock_date`,`stock_time`) USING BTREE,
  KEY `index_market_type` (`stock_code`,`market_type`) USING BTREE,
  KEY `index_stock_date` (`stock_date`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='指数股票数据分钟表';

-- --------------------------------------------------------
-- Table structure for table `stock_history_month_price`
-- --------------------------------------------------------
DROP TABLE IF EXISTS `stock_history_month_price`;
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
  UNIQUE KEY `index_stock_date_price` (`stock_code`,`stock_date`) USING BTREE,
  KEY `index_stock_market` (`stock_code`,`market_type`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=1724619 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='股票月线价格表（后复权）';

-- --------------------------------------------------------
-- Table structure for table `stock_history_week_price`
-- --------------------------------------------------------
DROP TABLE IF EXISTS `stock_history_week_price`;
CREATE TABLE `stock_history_week_price` (
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
  UNIQUE KEY `index_stock_date_price` (`stock_code`,`stock_date`) USING BTREE,
  KEY `index_stock_market` (`stock_code`,`market_type`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=7207867 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='股票周线价格表（后复权）';

-- --------------------------------------------------------
-- Table structure for table `stock_industry`
-- --------------------------------------------------------
DROP TABLE IF EXISTS `stock_industry`;
CREATE TABLE `stock_industry` (
  `id` int NOT NULL AUTO_INCREMENT,
  `update_date` date DEFAULT NULL COMMENT '更新日期',
  `stock_code` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '证券代码',
  `stock_name` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '证券名称',
  `industry` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '所属行业',
  `industry_classification` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '所属行业类别',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `market_type` varchar(10) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `index_stock_code` (`stock_code`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=54552 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='股票行业表';

-- --------------------------------------------------------
-- Table structure for table `stock_month_adx`
-- --------------------------------------------------------
DROP TABLE IF EXISTS `stock_month_adx`;
CREATE TABLE `stock_month_adx` (
  `stock_code` varchar(20) NOT NULL COMMENT '证券代码',
  `stock_date` date NOT NULL COMMENT '月K线截止日期（通常为每月最后一个交易日）',
  `adx` decimal(10,4) DEFAULT NULL COMMENT '平均趋向指数（ADX），衡量月级别趋势强度，无方向性',
  `plus_di` decimal(10,4) DEFAULT NULL COMMENT '正向指标（+DI），反映月线上涨趋势强度',
  `minus_di` decimal(10,4) DEFAULT NULL COMMENT '负向指标（-DI），反映月线下跌趋势强度',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`stock_code`,`stock_date`) USING BTREE,
  KEY `index_stock_date` (`stock_date`) USING BTREE,
  KEY `index_stock_code_date` (`stock_code`,`stock_date`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='股票月线ADX指标计算结果表（含ADX、+DI、-DI）';

-- --------------------------------------------------------
-- Table structure for table `stock_month_boll`
-- --------------------------------------------------------
DROP TABLE IF EXISTS `stock_month_boll`;
CREATE TABLE `stock_month_boll` (
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='计算股票每月的布林线';

-- --------------------------------------------------------
-- Table structure for table `stock_month_cci`
-- --------------------------------------------------------
DROP TABLE IF EXISTS `stock_month_cci`;
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

-- --------------------------------------------------------
-- Table structure for table `stock_month_obv`
-- --------------------------------------------------------
DROP TABLE IF EXISTS `stock_month_obv`;
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

-- --------------------------------------------------------
-- Table structure for table `stock_month_rsi`
-- --------------------------------------------------------
DROP TABLE IF EXISTS `stock_month_rsi`;
CREATE TABLE `stock_month_rsi` (
  `stock_code` varchar(20) NOT NULL COMMENT '证券代码',
  `stock_date` date NOT NULL COMMENT '交易所行情日期',
  `rsi_6` decimal(10,4) DEFAULT NULL COMMENT '6周期',
  `rsi_12` decimal(10,4) DEFAULT NULL COMMENT '12周期',
  `rsi_24` decimal(10,4) DEFAULT NULL COMMENT '24周期',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`stock_code`,`stock_date`) USING BTREE,
  KEY `index_stock_date` (`stock_date`) USING BTREE,
  KEY `index_stock_date_price` (`stock_code`,`stock_date`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='计算股票每月的相对强弱指标';

-- --------------------------------------------------------
-- Table structure for table `stock_performance_update_record`
-- --------------------------------------------------------
DROP TABLE IF EXISTS `stock_performance_update_record`;
CREATE TABLE `stock_performance_update_record` (
  `id` int NOT NULL AUTO_INCREMENT,
  `stock_code` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '证券代码',
  `performance_year` int DEFAULT '2007' COMMENT '业绩报年年份',
  `performance_season` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '证券季报季度记录',
  `performance_update_date` varchar(10) DEFAULT NULL COMMENT '证券业绩更新时间',
  `performance_type` varchar(10) DEFAULT NULL COMMENT '1 季频盈利能力,2 季频盈利能力,3 季频成长能力,4 季频偿债能力,5 季频现金流量',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `index_stock_code` (`stock_code`,`performance_year`,`performance_type`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=65704 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='证券业绩更新记录表';

-- --------------------------------------------------------
-- Table structure for table `stock_profit_data`
-- --------------------------------------------------------
DROP TABLE IF EXISTS `stock_profit_data`;
CREATE TABLE `stock_profit_data` (
  `id` int NOT NULL AUTO_INCREMENT,
  `stock_code` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '证券代码',
  `publish_date` date DEFAULT NULL COMMENT '公司发布财报的日期',
  `statistic_date` date DEFAULT NULL COMMENT '财报统计的季度的最后一天, 比如2017-03-31, 2017-06-30',
  `roe_avg` decimal(20,4) DEFAULT NULL COMMENT '净资产收益率(平均)(%)',
  `np_margin` decimal(20,4) DEFAULT NULL COMMENT '销售净利率(%)',
  `gp_margin` decimal(20,4) DEFAULT NULL COMMENT '销售毛利率(%)',
  `net_profit` decimal(20,4) DEFAULT NULL COMMENT '净利润(元)',
  `eps_ttm` decimal(20,4) DEFAULT NULL COMMENT '每股收益',
  `mb_revenue` decimal(20,4) DEFAULT NULL COMMENT '主营营业收入(元)',
  `total_share` decimal(20,4) DEFAULT NULL COMMENT '总股本	',
  `liqa_share` decimal(20,4) DEFAULT NULL COMMENT '流通股本',
  `season` int DEFAULT NULL COMMENT '季度',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `index_stock_code` (`stock_code`,`statistic_date`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=251483 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='证券季频盈利能力表';

-- --------------------------------------------------------
-- Table structure for table `stock_week_adx`
-- --------------------------------------------------------
DROP TABLE IF EXISTS `stock_week_adx`;
CREATE TABLE `stock_week_adx` (
  `stock_code` varchar(20) NOT NULL COMMENT '证券代码',
  `stock_date` date NOT NULL COMMENT '周K线截止日期（通常为周五）',
  `adx` decimal(10,4) DEFAULT NULL COMMENT '平均趋向指数（ADX），衡量周级别趋势强度，无方向性',
  `plus_di` decimal(10,4) DEFAULT NULL COMMENT '正向指标（+DI），反映周线上涨趋势强度',
  `minus_di` decimal(10,4) DEFAULT NULL COMMENT '负向指标（-DI），反映周线下跌趋势强度',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`stock_code`,`stock_date`) USING BTREE,
  KEY `index_stock_date` (`stock_date`) USING BTREE,
  KEY `index_stock_code_date` (`stock_code`,`stock_date`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='股票周线ADX指标计算结果表（含ADX、+DI、-DI）';

-- --------------------------------------------------------
-- Table structure for table `stock_week_boll`
-- --------------------------------------------------------
DROP TABLE IF EXISTS `stock_week_boll`;
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
) ENGINE=InnoDB AUTO_INCREMENT=3391571 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='计算股票每周的布林线';

-- --------------------------------------------------------
-- Table structure for table `stock_week_cci`
-- --------------------------------------------------------
DROP TABLE IF EXISTS `stock_week_cci`;
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

-- --------------------------------------------------------
-- Table structure for table `stock_week_obv`
-- --------------------------------------------------------
DROP TABLE IF EXISTS `stock_week_obv`;
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

-- --------------------------------------------------------
-- Table structure for table `stock_week_rsi`
-- --------------------------------------------------------
DROP TABLE IF EXISTS `stock_week_rsi`;
CREATE TABLE `stock_week_rsi` (
  `stock_code` varchar(20) NOT NULL COMMENT '证券代码',
  `stock_date` date NOT NULL COMMENT '交易所行情日期',
  `rsi_6` decimal(10,4) DEFAULT NULL COMMENT '6周期',
  `rsi_12` decimal(10,4) DEFAULT NULL COMMENT '12周期',
  `rsi_24` decimal(10,4) DEFAULT NULL COMMENT '24周期',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`stock_code`,`stock_date`) USING BTREE,
  KEY `index_stock_date` (`stock_date`) USING BTREE,
  KEY `index_stock_date_price` (`stock_code`,`stock_date`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='计算股票每周的相对强弱指标';

-- --------------------------------------------------------
-- Table structure for table `update_index_stock_record`
-- --------------------------------------------------------
DROP TABLE IF EXISTS `update_index_stock_record`;
CREATE TABLE `update_index_stock_record` (
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
) ENGINE=InnoDB AUTO_INCREMENT=1156631 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='指数更新记录表';

-- --------------------------------------------------------
-- Table structure for table `update_stock_record`
-- --------------------------------------------------------
DROP TABLE IF EXISTS `update_stock_record`;
CREATE TABLE `update_stock_record` (
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
  `update_stock_min` date DEFAULT NULL COMMENT '分钟线更新记录',
  `update_stock_date_adx` date DEFAULT '1990-01-01' COMMENT 'ADX值日线更新记录',
  `update_stock_week_adx` date DEFAULT '1990-01-01' COMMENT 'ADX值周线更新记录',
  `update_stock_month_adx` date DEFAULT '1990-01-01' COMMENT 'ADX值月线更新记录',
  PRIMARY KEY (`id`),
  UNIQUE KEY `u_index_stock_code` (`stock_code`) USING BTREE,
  KEY `index_stock_name` (`stock_name`) USING BTREE,
  KEY `index_stock_market` (`stock_code`,`market_type`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=584960 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='股票更新记录表';

-- --------------------------------------------------------
-- Table structure for table `week_stock_macd`
-- --------------------------------------------------------
DROP TABLE IF EXISTS `week_stock_macd`;
CREATE TABLE `week_stock_macd` (
  `stock_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '股票代码',
  `stock_date` date NOT NULL COMMENT '股票交易日',
  `close_price` decimal(20,4) DEFAULT NULL COMMENT '收盘价',
  `diff` decimal(20,4) DEFAULT NULL,
  `dea` decimal(20,4) DEFAULT NULL,
  `macd` decimal(10,4) DEFAULT NULL COMMENT 'macd',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`stock_code`,`stock_date`),
  KEY `index_stock_date` (`stock_date`) USING BTREE,
  KEY `un_index_stock_code_and_date` (`stock_code`,`stock_date`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='股票周线MACD表（后复权）';

-- --------------------------------------------------------
-- Table structure for table `week_stock_moving_average_table`
-- --------------------------------------------------------
DROP TABLE IF EXISTS `week_stock_moving_average_table`;
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='股票周线均线表（后复权）';


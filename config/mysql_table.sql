use stock;
-- DROP TABLE IF EXISTS stock.stock_history_date_price;
CREATE TABLE if NOT EXISTS stock.stock_history_date_price (
  `id` int NOT NULL AUTO_INCREMENT,
  `stock_code` varchar(20) NOT NULL COMMENT '证券代码',
  `stock_date` date NOT NULL COMMENT '交易所行情日期',
  `open_price` decimal(10,4) DEFAULT NULL COMMENT '开盘价',
  `high_price` decimal(10,4) DEFAULT NULL COMMENT '收盘价',
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
) ENGINE=InnoDB AUTO_INCREMENT=17405189 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='股票日线价格表（后复权）';
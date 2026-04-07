# -*- coding: utf-8 -*-
"""
新闻采集架构说明文档

本架构基于 E:\PycharmProjects\python_advanced\month1\week2_data_processing\day13_project 参考代码设计

核心设计：
1. 数据源层：RSS 源配置表 + API 接口（可扩展）
2. 采集层：NewsFetcher + 装饰器（重试/限速/计时）
3. 处理层：情绪分析器 + 新闻-股票关联
4. 存储层：MySQL 表结构（见 sql/create_news_tables.sql）

表结构：
├── stock_news           # 新闻主表（标题、描述、来源、时间、去重哈希）
├── stock_news_relation  # 新闻-股票关联表（一条新闻可能涉及多只股票）
├── stock_news_sentiment # 情绪分析结果表（分数、类型、关键词）
├── rss_source_config    # RSS 源配置表（动态管理采集源）
└── sentiment_dictionary  # 情绪词典表（动态扩展关键词）

核心模式应用：
1. 装饰器：@timer 计时、@retry 重试、@rate_limit 限速
2. 上下文管理器：fetch_stats_context 采集统计
3. 生成器：流式处理新闻数据
4. NumPy：情绪分数向量化计算

使用方法：
    # 采集所有 RSS 源
    python scripts/run_news_fetch.py

    # 采集特定股票
    python scripts/run_news_fetch.py --stocks 000001,600519

    # 查看情绪统计
    python scripts/run_news_fetch.py --stats AAPL --days 7

    # 仅分析未处理新闻
    python scripts/run_news_fetch.py --analyze-only

扩展方向：
1. 添加中文新闻源（财联社、东方财富）
2. 集成 LLM 情绪分析（替换词典方法）
3. 添加新闻聚类（相似新闻合并）
4. 添加实时推送（WebSocket）
"""

print(__doc__)
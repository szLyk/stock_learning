"""
我的缠论系统 - MyChanLun
基于czsc核心思想，适配自有数据结构的定制缠论分析系统

参考项目：czsc (https://github.com/waditu/czsc)
原作者：zengbin93
许可：Apache License 2.0

本项目基于czsc设计思想重新实现，适配自有数据结构。
核心算法（包含处理、分型识别、笔识别）参考czsc实现。

核心模块：
1. objects.py    - 数据对象定义（RawBar, FX, BI, ZS等）
2. analyze.py    - 分型、笔、中枢识别算法
3. signals.py    - 买卖点信号识别
4. adapter.py    - 数据适配层（连接数据库）
5. strategy.py   - 交易策略框架
"""

from chanlun.objects import RawBar, NewBar, FX, BI, ZS
from chanlun.analyze import ChanAnalyzer
from chanlun.adapter import StockDataAdapter

__version__ = "1.0.0"
__author__ = "虾哥"
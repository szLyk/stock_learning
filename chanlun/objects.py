"""
缠论核心对象定义
适配自有数据结构，参考czsc设计

核心对象层级：
RawBar（原始K线） → NewBar（去包含K线） → FX（分型） → BI（笔） → ZS（中枢）
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional


class Direction(Enum):
    """方向枚举"""
    Up = "向上"
    Down = "向下"


class Mark(Enum):
    """分型标记"""
    G = "顶分型"  # Top
    D = "底分型"  # Bottom


class Operate(Enum):
    """操作枚举"""
    Buy = "买入"
    Sell = "卖出"
    Hold = "持有"
    Long = "做多"
    Short = "做空"


@dataclass
class RawBar:
    """
    原始K线元素
    
    数据来源：stock_history_date_price表
    字段映射：
    - symbol: stock_code
    - dt: stock_date  
    - open/high/low/close: open_price/high_price/low_price/close_price
    - vol/amount: trading_volume/trading_amount
    """
    symbol: str           # 股票代码
    dt: datetime          # 日期
    open: float           # 开盘价
    close: float          # 收盘价
    high: float           # 最高价
    low: float            # 最低价
    vol: float            # 成交量
    amount: float         # 成交额
    
    # 扩展字段（数据库其他字段）
    pre_close: float = 0  # 前收盘价
    change_pct: float = 0 # 涨跌幅
    turn: float = 0       # 换手率
    
    # 用户缓存（用于存储技术指标等）
    cache: Dict = field(default_factory=dict)
    
    @property
    def upper(self) -> float:
        """上影线长度"""
        return self.high - max(self.open, self.close)
    
    @property
    def lower(self) -> float:
        """下影线长度"""
        return min(self.open, self.close) - self.low
    
    @property
    def solid(self) -> float:
        """实体长度"""
        return abs(self.open - self.close)
    
    @property
    def is_up(self) -> bool:
        """是否上涨K线"""
        return self.close > self.open
    
    @property
    def is_down(self) -> bool:
        """是否下跌K线"""
        return self.close < self.open


@dataclass
class NewBar:
    """
    去除包含关系后的K线元素
    
    包含关系处理规则（缠论定义）：
    1. 向上趋势中：取高高、取高低（合并高点取最高，低点取较高的）
    2. 向下趋势中：取低高、取低低（合并高点取较低的，低点取最低）
    """
    symbol: str
    dt: datetime
    open: float
    close: float
    high: float
    low: float
    vol: float
    amount: float
    
    # 构成这根K线的原始K线列表
    elements: List[RawBar] = field(default_factory=list)
    cache: Dict = field(default_factory=dict)
    
    @property
    def raw_bars(self) -> List[RawBar]:
        """返回构成这根K线的原始K线"""
        return self.elements


@dataclass
class FX:
    """
    分型对象（顶分型/底分型）
    
    分型定义（缠论原始定义）：
    顶分型：三根K线，中间一根的高点和低点均高于左右两根
    底分型：三根K线，中间一根的高点和低点均低于左右两根
    
    分型强度属性：
    - power_str: 强/中/弱（基于第三根K线收盘位置）
    - has_zs: 是否构成分型内小中枢
    """
    symbol: str
    dt: datetime          # 分型时间（中间K线时间）
    mark: Mark            # 分型标记（G/D）
    high: float           # 分型高点
    low: float            # 分型低点
    fx: float             # 分型值（顶分型=high，底分型=low）
    
    # 构成分型的三根无包含K线
    elements: List[NewBar] = field(default_factory=list)
    cache: Dict = field(default_factory=dict)
    
    @property
    def new_bars(self) -> List[NewBar]:
        """构成分型的无包含K线"""
        return self.elements
    
    @property
    def raw_bars(self) -> List[RawBar]:
        """构成分型的原始K线"""
        res = []
        for e in self.elements:
            res.extend(e.raw_bars)
        return res
    
    @property
    def power_str(self) -> str:
        """分型强度字符串：强/中/弱"""
        assert len(self.elements) == 3
        k1, k2, k3 = self.elements
        
        if self.mark == Mark.D:  # 底分型
            if k3.close > k1.high:
                return "强"  # 第三根收盘高于第一根高点
            elif k3.close > k2.high:
                return "中"  # 第三根收盘高于中间K线高点
            else:
                return "弱"
        else:  # 顶分型
            if k3.close < k1.low:
                return "强"
            elif k3.close < k2.low:
                return "中"
            else:
                return "弱"
    
    @property
    def has_zs(self) -> bool:
        """构成分型的三根K线是否有重叠中枢"""
        assert len(self.elements) == 3
        zd = max([x.low for x in self.elements])  # 中枢下沿
        zg = min([x.high for x in self.elements])  # 中枢上沿
        return zg >= zd  # 有重叠
    
    @property
    def power_volume(self) -> float:
        """分型成交量力度"""
        return sum([x.vol for x in self.elements])


@dataclass
class BI:
    """
    笔对象
    
    笔的定义（缠论严格定义）：
    1. 一笔由顶分型和底分型连接而成
    2. 顶底分型之间不能有包含关系
    3. 笔内至少有5根无包含K线（可配置）
    4. 笔必须独立完成，不能被后续走势破坏
    
    笔的属性：
    - direction: 向上/向下
    - power_price: 价差力度
    - power_volume: 成交量力度
    - slope: 斜率（线性回归）
    - SNR: 信噪比（走势顺畅度）
    """
    symbol: str
    fx_a: FX              # 笔开始的分型
    fx_b: FX              # 笔结束的分型
    fxs: List[FX]         # 笔内所有分型
    direction: Direction  # 笔方向
    bars: List[NewBar] = field(default_factory=list)  # 笔内无包含K线
    cache: Dict = field(default_factory=dict)
    
    def __post_init__(self):
        self.sdt = self.fx_a.dt  # 笔开始时间
        self.edt = self.fx_b.dt  # 笔结束时间
    
    @property
    def high(self) -> float:
        """笔的最高价"""
        return max(self.fx_a.high, self.fx_b.high)
    
    @property
    def low(self) -> float:
        """笔的最低价"""
        return min(self.fx_a.low, self.fx_b.low)
    
    @property
    def power_price(self) -> float:
        """笔的价差力度"""
        return round(abs(self.fx_b.fx - self.fx_a.fx), 2)
    
    @property
    def power_volume(self) -> float:
        """笔的成交量力度"""
        return sum([x.vol for x in self.bars[1:-1]])
    
    @property
    def change(self) -> float:
        """笔的涨跌幅"""
        return round((self.fx_b.fx - self.fx_a.fx) / self.fx_a.fx, 4)
    
    @property
    def length(self) -> int:
        """笔的K线数量"""
        return len(self.bars)
    
    @property
    def raw_bars(self) -> List[RawBar]:
        """笔的原始K线（不包含首尾分型首根）"""
        res = []
        for bar in self.bars[1:-1]:
            res.extend(bar.raw_bars)
        return res


@dataclass  
class ZS:
    """
    中枢对象
    
    中枢定义（缠论定义）：
    至少三笔连续重叠构成中枢
    
    中枢级别：
    - 一笔中枢：次级别走势构成
    - 三笔中枢：本级别走势构成
    - 五笔中枢：更大级别走势构成
    
    中枢属性：
    - zg/zd: 中枢上沿/下沿
    - gg/dd: 中枢最高点/最低点
    - zz: 中枢中轴
    - is_valid: 中枢是否有效
    """
    bis: List[BI]         # 构成中枢的笔列表
    cache: Dict = field(default_factory=dict)
    
    def __post_init__(self):
        self.symbol = self.bis[0].symbol
    
    @property
    def sdt(self) -> datetime:
        """中枢开始时间"""
        return self.bis[0].sdt
    
    @property
    def edt(self) -> datetime:
        """中枢结束时间"""
        return self.bis[-1].edt
    
    @property
    def zg(self) -> float:
        """中枢上沿（前三笔高点最小值）"""
        return min([x.high for x in self.bis[:3]])
    
    @property
    def zd(self) -> float:
        """中枢下沿（前三笔低点最大值）"""
        return max([x.low for x in self.bis[:3]])
    
    @property
    def gg(self) -> float:
        """中枢最高点"""
        return max([x.high for x in self.bis])
    
    @property
    def dd(self) -> float:
        """中枢最低点"""
        return min([x.low for x in self.bis])
    
    @property
    def zz(self) -> float:
        """中枢中轴"""
        return round(self.zd + (self.zg - self.zd) / 2, 2)
    
    @property
    def width(self) -> float:
        """中枢宽度"""
        return round(self.zg - self.zd, 2)
    
    @property
    def is_valid(self) -> bool:
        """中枢是否有效"""
        # 上沿必须高于下沿
        if self.zg < self.zd:
            return False
        
        # 检查每笔是否与中枢有交集
        for bi in self.bis:
            if (self.zg >= bi.high >= self.zd) or \
               (self.zg >= bi.low >= self.zd) or \
               (bi.high >= self.zg > self.zd >= bi.low):
                continue
            else:
                return False
        return True
    
    def __repr__(self) -> str:
        return f"ZS({self.sdt}~{self.edt}, zg={self.zg}, zd={self.zd}, 笔数={len(self.bis)})"
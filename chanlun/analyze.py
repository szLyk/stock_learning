"""
缠论分析核心算法
包含：K线包含处理、分型识别、笔识别、中枢识别

参考czsc实现，适配自有数据结构

核心算法流程：
RawBar → remove_include() → NewBar → check_fx() → FX → check_bi() → BI → check_zs() → ZS
"""

from typing import List, Tuple, Optional
from chanlun.objects import RawBar, NewBar, FX, BI, ZS, Direction, Mark


def remove_include(k1: NewBar, k2: NewBar, k3: RawBar) -> Tuple[bool, NewBar]:
    """
    去除包含关系
    
    缠论定义：
    如果k2和k3存在包含关系（k2高低点完全在k3内或相反），
    则合并为一根新K线
    
    合并规则：
    - 向上趋势（k1.high < k2.high）：取高高、取高低
    - 向下趋势（k1.high > k2.high）：取低高、取低低
    
    Args:
        k1: 前一根无包含K线
        k2: 当前无包含K线
        k3: 新的原始K线
        
    Returns:
        (has_include, new_bar): 是否有包含关系，合并后的新K线
    """
    # 判断趋势方向
    if k1.high < k2.high:
        direction = Direction.Up
    elif k1.high > k2.high:
        direction = Direction.Down
    else:
        # 高点相等，无包含关系
        new_bar = NewBar(
            symbol=k3.symbol,
            dt=k3.dt,
            open=k3.open,
            close=k3.close,
            high=k3.high,
            low=k3.low,
            vol=k3.vol,
            amount=k3.amount,
            elements=[k3],
        )
        return False, new_bar
    
    # 判断k2和k3是否存在包含关系
    is_include = (k2.high <= k3.high and k2.low >= k3.low) or \
                 (k2.high >= k3.high and k2.low <= k3.low)
    
    if is_include:
        # 存在包含关系，合并处理
        if direction == Direction.Up:
            # 向上趋势：取高高、取高低
            high = max(k2.high, k3.high)
            low = max(k2.low, k3.low)
            dt = k2.dt if k2.high > k3.high else k3.dt
        else:
            # 向下趋势：取低高、取低低
            high = min(k2.high, k3.high)
            low = min(k2.low, k3.low)
            dt = k2.dt if k2.low < k3.low else k3.dt
        
        # 确定开盘收盘价
        open_ = high if k3.open > k3.close else low
        close_ = low if k3.open > k3.close else high
        
        # 合并成交量和成交额
        vol = k2.vol + k3.vol
        amount = k2.amount + k3.amount
        
        # 合并原始K线元素
        elements = [x for x in k2.elements if x.dt != k3.dt] + [k3]
        
        new_bar = NewBar(
            symbol=k3.symbol,
            dt=dt,
            open=open_,
            close=close_,
            high=high,
            low=low,
            vol=vol,
            amount=amount,
            elements=elements,
        )
        return True, new_bar
    else:
        # 无包含关系，直接创建新K线
        new_bar = NewBar(
            symbol=k3.symbol,
            dt=k3.dt,
            open=k3.open,
            close=k3.close,
            high=k3.high,
            low=k3.low,
            vol=k3.vol,
            amount=k3.amount,
            elements=[k3],
        )
        return False, new_bar


def check_fx(k1: NewBar, k2: NewBar, k3: NewBar) -> Optional[FX]:
    """
    检查三根K线是否构成分型
    
    顶分型条件：
    k1.high < k2.high > k3.high 且 k1.low < k2.low > k3.low
    
    底分型条件：
    k1.low > k2.low < k3.low 且 k1.high > k2.high < k3.high
    
    Args:
        k1, k2, k3: 连续三根无包含K线
        
    Returns:
        FX对象或None
    """
    # 顶分型：中间K线高低点都高于左右
    if k1.high < k2.high > k3.high and k1.low < k2.low > k3.low:
        fx = FX(
            symbol=k2.symbol,
            dt=k2.dt,
            mark=Mark.G,
            high=k2.high,
            low=k2.low,
            fx=k2.high,
            elements=[k1, k2, k3],
        )
        return fx
    
    # 底分型：中间K线高低点都低于左右
    if k1.low > k2.low < k3.low and k1.high > k2.high < k3.high:
        fx = FX(
            symbol=k2.symbol,
            dt=k2.dt,
            mark=Mark.D,
            high=k2.high,
            low=k2.low,
            fx=k2.low,
            elements=[k1, k2, k3],
        )
        return fx
    
    return None


def check_fxs(bars: List[NewBar]) -> List[FX]:
    """
    在无包含K线序列中查找所有分型
    
    Args:
        bars: 无包含K线列表
        
    Returns:
        分型列表（顶底交替）
    """
    fxs = []
    for i in range(1, len(bars) - 1):
        fx = check_fx(bars[i-1], bars[i], bars[i+1])
        if fx:
            # 确保分型顶底交替
            if fxs and fx.mark == fxs[-1].mark:
                # 同类型分型，取更强的
                if fx.mark == Mark.G:
                    # 都是顶分型，取高点更高的
                    if fx.high > fxs[-1].high:
                        fxs[-1] = fx
                else:
                    # 都是底分型，取低点更低的
                    if fx.low < fxs[-1].low:
                        fxs[-1] = fx
            else:
                fxs.append(fx)
    return fxs


def check_bi(bars: List[NewBar], min_bi_len: int = 5) -> Tuple[Optional[BI], List[NewBar]]:
    """
    在无包含K线序列中查找一笔
    
    成笔条件：
    1. 顶底分型之间无包含关系
    2. 笔长度 >= min_bi_len
    3. 方向一致（向上笔底分型开始，顶分型结束）
    
    Args:
        bars: 无包含K线列表
        min_bi_len: 最小笔长度（默认5根K线）
        
    Returns:
        (笔对象, 剩余K线列表)
    """
    fxs = check_fxs(bars)
    if len(fxs) < 2:
        return None, bars
    
    fx_a = fxs[0]
    
    # 向上笔：底分型开始，找顶分型结束
    if fx_a.mark == Mark.D:
        direction = Direction.Up
        candidates = [x for x in fxs if x.mark == Mark.G and x.dt > fx_a.dt and x.fx > fx_a.fx]
        fx_b = max(candidates, key=lambda x: x.high, default=None)
    
    # 向下笔：顶分型开始，找底分型结束
    elif fx_a.mark == Mark.G:
        direction = Direction.Down
        candidates = [x for x in fxs if x.mark == Mark.D and x.dt > fx_a.dt and x.fx < fx_a.fx]
        fx_b = min(candidates, key=lambda x: x.low, default=None)
    else:
        return None, bars
    
    if fx_b is None:
        return None, bars
    
    # 提取笔内K线
    bars_a = [x for x in bars if fx_a.elements[0].dt <= x.dt <= fx_b.elements[2].dt]
    bars_b = [x for x in bars if x.dt >= fx_b.elements[0].dt]
    
    # 检查顶底分型是否包含
    ab_include = (fx_a.high > fx_b.high and fx_a.low < fx_b.low) or \
                 (fx_a.high < fx_b.high and fx_a.low > fx_b.low)
    
    # 成笔判断
    if not ab_include and len(bars_a) >= min_bi_len:
        fxs_in_bi = [x for x in fxs if fx_a.elements[0].dt <= x.dt <= fx_b.elements[2].dt]
        bi = BI(
            symbol=fx_a.symbol,
            fx_a=fx_a,
            fx_b=fx_b,
            fxs=fxs_in_bi,
            direction=direction,
            bars=bars_a,
        )
        return bi, bars_b
    
    return None, bars


def check_zs(bis: List[BI], min_zs_bis: int = 3) -> List[ZS]:
    """
    在笔序列中查找中枢
    
    中枢定义：
    至少三笔连续重叠构成中枢
    
    Args:
        bis: 笔列表
        min_zs_bis: 最小构成笔数（默认3）
        
    Returns:
        中枢列表
    """
    if len(bis) < min_zs_bis:
        return []
    
    zs_list = []
    i = 0
    
    while i < len(bis) - min_zs_bis + 1:
        # 取连续min_zs_bis笔尝试构建中枢
        candidate_bis = bis[i:i + min_zs_bis]
        
        # 计算中枢区间
        zg = min([x.high for x in candidate_bis])
        zd = max([x.low for x in candidate_bis])
        
        # 检查是否有重叠
        if zg >= zd:
            # 找到潜在中枢，尝试扩展
            zs_bis = candidate_bis.copy()
            
            # 继续向后检查是否可以扩展中枢
            j = i + min_zs_bis
            while j < len(bis):
                next_bi = bis[j]
                # 检查下一笔是否与中枢有交集
                if (zg >= next_bi.high >= zd) or \
                   (zg >= next_bi.low >= zd) or \
                   (next_bi.high >= zg > zd >= next_bi.low):
                    zs_bis.append(next_bi)
                    # 更新中枢边界
                    zg = min(zg, next_bi.high)
                    zd = max(zd, next_bi.low)
                    j += 1
                else:
                    break
            
            # 创建中枢对象
            zs = ZS(bis=zs_bis)
            if zs.is_valid:
                zs_list.append(zs)
                i = j  # 跳过已构成中枢的笔
            else:
                i += 1
        else:
            i += 1
    
    return zs_list


class ChanAnalyzer:
    """
    缠论分析器
    
    核心功能：
    1. 将原始K线转换为缠论结构
    2. 实时更新分型、笔、中枢
    3. 提供买卖点信号
    
    使用方式：
    analyzer = ChanAnalyzer()
    analyzer.update(raw_bars)  # 更新K线
    analyzer.bi_list           # 获取笔列表
    analyzer.zs_list           # 获取中枢列表
    """
    
    def __init__(self, min_bi_len: int = 5, max_bi_num: int = 50):
        """
        Args:
            min_bi_len: 最小笔长度
            max_bi_num: 最大保留笔数
        """
        self.min_bi_len = min_bi_len
        self.max_bi_num = max_bi_num
        
        self.symbol = ""
        self.bars_raw: List[RawBar] = []      # 原始K线
        self.bars_ubi: List[NewBar] = []      # 未完成笔的无包含K线
        self.bi_list: List[BI] = []           # 已完成笔列表
        self.zs_list: List[ZS] = []           # 中枢列表
        
    def update(self, bars: List[RawBar]):
        """
        更新K线数据，执行缠论分析
        
        Args:
            bars: 原始K线列表
        """
        if not bars:
            return
        
        self.symbol = bars[0].symbol
        self.bars_raw = bars
        
        # Step 1: 去除包含关系
        self.bars_ubi = self._remove_all_includes(bars)
        
        # Step 2: 识别分型
        fxs = check_fxs(self.bars_ubi)
        
        # Step 3: 识别笔
        self._build_bi_list(self.bars_ubi)
        
        # Step 4: 识别中枢
        self.zs_list = check_zs(self.bi_list)
        
        # 限制笔数量
        self.bi_list = self.bi_list[-self.max_bi_num:]
    
    def _remove_all_includes(self, bars: List[RawBar]) -> List[NewBar]:
        """去除所有包含关系"""
        new_bars = []
        
        for bar in bars:
            if len(new_bars) < 2:
                # 前两根直接加入
                new_bars.append(NewBar(
                    symbol=bar.symbol,
                    dt=bar.dt,
                    open=bar.open,
                    close=bar.close,
                    high=bar.high,
                    low=bar.low,
                    vol=bar.vol,
                    amount=bar.amount,
                    elements=[bar],
                ))
            else:
                k1, k2 = new_bars[-2:]
                has_include, k3 = remove_include(k1, k2, bar)
                if has_include:
                    new_bars[-1] = k3
                else:
                    new_bars.append(k3)
        
        return new_bars
    
    def _build_bi_list(self, bars: List[NewBar]):
        """构建笔列表"""
        remaining = bars.copy()
        self.bi_list = []
        
        while len(remaining) >= self.min_bi_len + 2:
            bi, remaining = check_bi(remaining, self.min_bi_len)
            if bi:
                self.bi_list.append(bi)
            else:
                break
        
        self.bars_ubi = remaining
    
    @property
    def fx_list(self) -> List[FX]:
        """所有分型列表"""
        fxs = []
        for bi in self.bi_list:
            fxs.extend(bi.fxs)
        
        # 添加未完成笔中的分型
        ubi_fxs = check_fxs(self.bars_ubi)
        for fx in ubi_fxs:
            if not fxs or fx.dt > fxs[-1].dt:
                fxs.append(fx)
        
        return fxs
    
    @property
    def last_bi(self) -> Optional[BI]:
        """最后一笔"""
        return self.bi_list[-1] if self.bi_list else None
    
    @property
    def last_zs(self) -> Optional[ZS]:
        """最后一个中枢"""
        return self.zs_list[-1] if self.zs_list else None
    
    @property
    def ubi_fxs(self) -> List[FX]:
        """未完成笔中的分型"""
        return check_fxs(self.bars_ubi)
    
    def get_summary(self) -> dict:
        """获取分析摘要"""
        return {
            'symbol': self.symbol,
            'bars_count': len(self.bars_raw),
            'bi_count': len(self.bi_list),
            'zs_count': len(self.zs_list),
            'fx_count': len(self.fx_list),
            'last_bi': str(self.last_bi),
            'last_zs': str(self.last_zs),
        }
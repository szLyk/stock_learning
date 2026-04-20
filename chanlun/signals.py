"""
缠论买卖点信号系统

三类买卖点定义（缠论理论）：
- 一买：下跌趋势结束点（中枢离开段底分型确认）
- 二买：一买后回拉不破中枢的底分型
- 三买：离开中枢后回拉不进中枢的底分型
- 一卖、二卖、三卖：对应卖点定义

信号系统设计：
1. 基于笔、中枢结构识别买卖点
2. 信号强度评分（0-100）
3. 支持自定义信号组合
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
from chanlun.objects import BI, ZS, FX, Direction, Mark
from chanlun.analyze import ChanAnalyzer


@dataclass
class ChanSignal:
    """
    缠论信号对象
    
    Attributes:
        signal_type: 信号类型（一买、二买、三买、一卖、二卖、三卖）
        score: 信号强度（0-100）
        position: 信号位置（价格）
        dt: 信号时间
        reason: 信号原因描述
        is_valid: 信号是否有效
    """
    signal_type: str          # 信号类型
    score: int                # 信号强度
    position: float           # 信号价格位置
    dt: str                   # 信号时间
    reason: str               # 信号原因
    is_valid: bool = True     # 信号有效性
    
    def __repr__(self):
        return f"ChanSignal({self.signal_type}, score={self.score}, pos={self.position})"


def check_buy_signals(analyzer: ChanAnalyzer) -> List[ChanSignal]:
    """
    检查买入信号
    
    买入信号条件：
    - 一买：下跌趋势结束（离开段底分型确认）
    - 二买：一买后回拉不破中枢下沿
    - 三买：离开中枢后回拉不进中枢
    
    Args:
        analyzer: 缠论分析器
        
    Returns:
        买入信号列表
    """
    signals = []
    
    if not analyzer.bi_list or len(analyzer.bi_list) < 5:
        return signals
    
    last_bi = analyzer.bi_list[-1]
    last_zs = analyzer.last_zs
    
    # 一买信号：最后一笔向下，且出现底分型
    if last_bi.direction == Direction.Down:
        ubi_fxs = analyzer.ubi_fxs
        
        # 未完成笔中出现底分型
        for fx in ubi_fxs:
            if fx.mark == Mark.D:
                # 计算信号强度
                score = calculate_buy_score(analyzer, 'buy1', fx)
                
                signal = ChanSignal(
                    signal_type='一买',
                    score=score,
                    position=fx.fx,
                    dt=str(fx.dt),
                    reason='下跌趋势末端，底分型确认',
                )
                signals.append(signal)
    
    # 二买信号：有中枢，回拉不破中枢
    if last_zs and last_bi.direction == Direction.Up:
        # 检查是否回拉中枢
        if last_bi.low >= last_zs.zd:
            score = calculate_buy_score(analyzer, 'buy2', last_bi)
            
            signal = ChanSignal(
                signal_type='二买',
                score=score,
                position=last_bi.low,
                dt=str(last_bi.sdt),
                reason='一买后回拉不破中枢',
            )
            signals.append(signal)
    
    # 三买信号：离开中枢后回拉不进
    if last_zs and len(analyzer.bi_list) >= 3:
        prev_bi = analyzer.bi_list[-2]
        
        # 前一笔向上离开中枢，当前笔回拉不进
        if prev_bi.direction == Direction.Up and \
           prev_bi.high > last_zs.zg and \
           last_bi.direction == Direction.Down and \
           last_bi.low > last_zs.zg:
            
            score = calculate_buy_score(analyzer, 'buy3', last_bi)
            
            signal = ChanSignal(
                signal_type='三买',
                score=score,
                position=last_bi.low,
                dt=str(last_bi.sdt),
                reason='离开中枢后回拉不进中枢',
            )
            signals.append(signal)
    
    return signals


def check_sell_signals(analyzer: ChanAnalyzer) -> List[ChanSignal]:
    """
    检查卖出信号
    
    Args:
        analyzer: 缠论分析器
        
    Returns:
        卖出信号列表
    """
    signals = []
    
    if not analyzer.bi_list or len(analyzer.bi_list) < 5:
        return signals
    
    last_bi = analyzer.bi_list[-1]
    last_zs = analyzer.last_zs
    
    # 一卖信号：向上趋势结束，顶分型确认
    if last_bi.direction == Direction.Up:
        ubi_fxs = analyzer.ubi_fxs
        
        for fx in ubi_fxs:
            if fx.mark == Mark.G:
                score = calculate_sell_score(analyzer, 'sell1', fx)
                
                signal = ChanSignal(
                    signal_type='一卖',
                    score=score,
                    position=fx.fx,
                    dt=str(fx.dt),
                    reason='上涨趋势末端，顶分型确认',
                )
                signals.append(signal)
    
    # 二卖信号：一卖后回拉不破中枢上沿
    if last_zs and last_bi.direction == Direction.Down:
        if last_bi.high <= last_zs.zg:
            score = calculate_sell_score(analyzer, 'sell2', last_bi)
            
            signal = ChanSignal(
                signal_type='二卖',
                score=score,
                position=last_bi.high,
                dt=str(last_bi.sdt),
                reason='一卖后回拉不破中枢',
            )
            signals.append(signal)
    
    # 三卖信号：离开中枢后回拉不进
    if last_zs and len(analyzer.bi_list) >= 3:
        prev_bi = analyzer.bi_list[-2]
        
        if prev_bi.direction == Direction.Down and \
           prev_bi.low < last_zs.zd and \
           last_bi.direction == Direction.Up and \
           last_bi.high < last_zs.zd:
            
            score = calculate_sell_score(analyzer, 'sell3', last_bi)
            
            signal = ChanSignal(
                signal_type='三卖',
                score=score,
                position=last_bi.high,
                dt=str(last_bi.sdt),
                reason='离开中枢后回拉不进中枢',
            )
            signals.append(signal)
    
    return signals


def calculate_buy_score(analyzer: ChanAnalyzer, signal_type: str, ref_obj) -> int:
    """
    计算买入信号强度
    
    评分维度：
    1. 分型强度（强/中/弱）：30-10分
    2. 笔长度：10-30分
    3. 中枢质量：10-20分
    4. 成交量配合：0-20分
    
    Args:
        analyzer: 分析器
        signal_type: 信号类型
        ref_obj: 参考对象（FX或BI）
        
    Returns:
        信号强度分数（0-100）
    """
    score = 0
    
    # 分型强度
    if isinstance(ref_obj, FX):
        if ref_obj.power_str == '强':
            score += 30
        elif ref_obj.power_str == '中':
            score += 20
        else:
            score += 10
    
    # 笔长度评分
    if isinstance(ref_obj, BI):
        if ref_obj.length >= 10:
            score += 30
        elif ref_obj.length >= 7:
            score += 20
        else:
            score += 10
    
    # 中枢质量
    last_zs = analyzer.last_zs
    if last_zs:
        # 中枢宽度适中
        if last_zs.width > 0.01 * last_zs.zz:
            score += 15
        else:
            score += 5
        
        # 中枢笔数多表示震荡充分
        if len(last_zs.bis) >= 5:
            score += 5
    
    # 成交量配合
    if isinstance(ref_obj, FX) and ref_obj.power_volume > 0:
        # 与前一个分型对比
        fx_list = analyzer.fx_list
        if len(fx_list) >= 2:
            prev_fx = fx_list[-2]
            if ref_obj.power_volume > prev_fx.power_volume:
                score += 20
            elif ref_obj.power_volume > prev_fx.power_volume * 0.8:
                score += 10
    
    return min(score, 100)


def calculate_sell_score(analyzer: ChanAnalyzer, signal_type: str, ref_obj) -> int:
    """计算卖出信号强度"""
    return calculate_buy_score(analyzer, signal_type, ref_obj)


def get_all_signals(analyzer: ChanAnalyzer) -> Dict[str, List[ChanSignal]]:
    """
    获取所有信号
    
    Args:
        analyzer: 缠论分析器
        
    Returns:
        {'buy': buy_signals, 'sell': sell_signals}
    """
    return {
        'buy': check_buy_signals(analyzer),
        'sell': check_sell_signals(analyzer),
    }


def get_best_signal(analyzer: ChanAnalyzer) -> Optional[ChanSignal]:
    """
    获取最强信号
    
    Args:
        analyzer: 缠论分析器
        
    Returns:
        评分最高的信号
    """
    all_signals = get_all_signals(analyzer)
    
    buy_signals = all_signals['buy']
    sell_signals = all_signals['sell']
    
    all_list = buy_signals + sell_signals
    
    if not all_list:
        return None
    
    return max(all_list, key=lambda s: s.score)


class SignalScanner:
    """
    信号扫描器
    
    扫描多只股票，寻找交易机会
    """
    
    def __init__(self, adapter):
        """初始化扫描器"""
        self.adapter = adapter
        self.results = {}
    
    def scan_one(self, stock_code: str) -> Optional[ChanSignal]:
        """
        扫描单只股票
        
        Returns:
            最佳信号
        """
        from chanlun.adapter import StockDataAdapter
        
        bars = self.adapter.fetch_bars(stock_code)
        if not bars:
            return None
        
        analyzer = ChanAnalyzer()
        analyzer.update(bars)
        
        best_signal = get_best_signal(analyzer)
        
        if best_signal and best_signal.score >= 60:
            self.results[stock_code] = {
                'signal': best_signal,
                'summary': analyzer.get_summary(),
            }
            return best_signal
        
        return None
    
    def scan_batch(self, stock_codes: List[str]) -> Dict[str, ChanSignal]:
        """
        批量扫描
        
        Returns:
            有信号的股票字典
        """
        for code in stock_codes:
            self.scan_one(code)
        
        return self.results
    
    def get_report(self) -> str:
        """生成扫描报告"""
        if not self.results:
            return "无有效信号"
        
        lines = ["=== 缠论信号扫描报告 ==="]
        
        buy_signals = []
        sell_signals = []
        
        for code, data in self.results.items():
            signal = data['signal']
            if signal.signal_type in ['一买', '二买', '三买']:
                buy_signals.append((code, signal))
            else:
                sell_signals.append((code, signal))
        
        if buy_signals:
            lines.append("\n买入机会:")
            for code, sig in sorted(buy_signals, key=lambda x: -x[1].score):
                lines.append(f"  {code}: {sig.signal_type} (强度={sig.score}, 价格={sig.position})")
        
        if sell_signals:
            lines.append("\n卖出信号:")
            for code, sig in sorted(sell_signals, key=lambda x: -x[1].score):
                lines.append(f"  {code}: {sig.signal_type} (强度={sig.score}, 价格={sig.position})")
        
        return "\n".join(lines)
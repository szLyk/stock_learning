"""
缠论系统使用示例

演示如何使用MyChanLun分析股票
"""

# 示例1：分析单只股票
def example_analyze_single():
    """分析单只股票"""
    from chanlun.adapter import StockDataAdapter
    from chanlun.analyze import ChanAnalyzer
    
    # 1. 创建数据适配器
    adapter = StockDataAdapter(
        host='192.168.1.128',
        user='root',
        password='123456',
        database='stock',
    )
    
    # 2. 获取数据
    bars = adapter.fetch_bars('000001', start_date='2024-01-01')
    
    print(f"获取到 {len(bars)} 条K线数据")
    
    # 3. 执行缠论分析
    analyzer = ChanAnalyzer(min_bi_len=5)
    analyzer.update(bars)
    
    # 4. 查看分析结果
    summary = analyzer.get_summary()
    print("\n分析摘要:")
    for key, value in summary.items():
        print(f"  {key}: {value}")
    
    # 5. 查看笔列表
    print("\n笔列表（最近5笔）:")
    for bi in analyzer.bi_list[-5:]:
        print(f"  {bi.direction.value}: {bi.sdt} -> {bi.edt}, 价差={bi.power_price}")
    
    # 6. 查看中枢
    print("\n中枢列表:")
    for zs in analyzer.zs_list:
        print(f"  {zs}")
    
    return analyzer


# 示例2：信号扫描
def example_scan_signals():
    """扫描买卖点信号"""
    from chanlun.adapter import StockDataAdapter
    from chanlun.signals import SignalScanner, get_all_signals
    
    # 1. 分析单只股票
    adapter = StockDataAdapter(host='192.168.1.128')
    
    # 2. 扫描信号
    scanner = SignalScanner(adapter)
    
    # 3. 扫描指定股票
    test_stocks = ['000001', '000002', '600519', '600036']
    
    for code in test_stocks:
        signal = scanner.scan_one(code)
        if signal:
            print(f"{code}: {signal.signal_type}, 强度={signal.score}, 价格={signal.position}")
    
    # 4. 生成报告
    print(scanner.get_report())


# 示例3：批量分析
def example_batch_analyze():
    """批量分析多只股票"""
    from chanlun.adapter import MultiStockAnalyzer, StockDataAdapter
    
    adapter = StockDataAdapter(host='192.168.1.128')
    
    multi_analyzer = MultiStockAnalyzer(adapter)
    
    # 分析指定股票
    results = multi_analyzer.analyze_all(['000001', '000002', '600519'])
    
    for result in results:
        print(f"{result.get('symbol', '未知')}: 笔数={result.get('bi_count', 0)}, 中枢数={result.get('zs_count', 0)}")


# 示例4：自定义分析
def example_custom_analysis():
    """自定义分析参数"""
    from chanlun.adapter import StockDataAdapter
    from chanlun.analyze import ChanAnalyzer
    from chanlun.signals import get_best_signal
    
    adapter = StockDataAdapter(host='192.168.1.128')
    
    # 获取最近1年数据
    bars = adapter.fetch_bars('600519', start_date='2025-01-01')
    
    # 使用不同参数分析
    analyzer = ChanAnalyzer(min_bi_len=7)  # 7根K线成笔（更严格）
    analyzer.update(bars)
    
    # 获取最佳信号
    best_signal = get_best_signal(analyzer)
    
    if best_signal:
        print(f"最佳信号: {best_signal}")
        print(f"  类型: {best_signal.signal_type}")
        print(f"  强度: {best_signal.score}")
        print(f"  位置: {best_signal.position}")
        print(f"  原因: {best_signal.reason}")


if __name__ == '__main__':
    print("=== 缠论系统使用示例 ===")
    print("\n可用函数：")
    print("  example_analyze_single() - 分析单只股票")
    print("  example_scan_signals()   - 扫描买卖信号")
    print("  example_batch_analyze()  - 批量分析")
    print("  example_custom_analysis()- 自定义分析")
    
    # 运行示例
    try:
        print("\n运行示例1：分析单只股票")
        analyzer = example_analyze_single()
    except Exception as e:
        print(f"示例运行失败: {e}")
        print("请确保数据库连接正常")
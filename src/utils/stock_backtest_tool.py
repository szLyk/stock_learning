# src/utils/backtest_tool.py
import os

import pandas as pd
from logs.logger import LogManager
from src.utils.stock_strategy_tool import analyze_stock_top_by_code, comprehensive_buy_strategy, calculate_indicators
from src.utils.stock_strategy_tool import get_stock_data
from src.utils.plot_tool import plot_backtest_result

logger = LogManager.get_logger("backtest_tool")


def run_dynamic_position_backtest(df: pd.DataFrame) -> pd.DataFrame:
    """
    动态仓位回测策略（输出完整回测所需字段）
    """
    df = df.copy()
    df['stock_date'] = pd.to_datetime(df['stock_date'])
    df = df.sort_values('stock_date').reset_index(drop=True)

    # 初始化
    positions = []
    current_pos = 0.0

    for i, row in df.iterrows():
        buy_score = row.get('Buy_Score', 0)
        top_score = row.get('top_score', 0)

        # 1. 买入目标仓位
        if buy_score >= 70:
            target_buy_pos = 1.0
        elif buy_score >= 50:
            target_buy_pos = 1.0
        elif buy_score >= 30:
            target_buy_pos = 0.8
        else:
            target_buy_pos = 0.0

        # 2. 风控上限
        if top_score >= 85:
            risk_control_pos = 0.0  # 极端高估才清仓
        elif top_score >= 65:
            risk_control_pos = 1.0  # 高估时保留底仓
        elif top_score >= 45:
            risk_control_pos = 1.0  # 中等风险正常仓位
        else:
            risk_control_pos = 1.0  # 安全区满仓

        new_pos = min(target_buy_pos, risk_control_pos)
        positions.append(new_pos)
        current_pos = new_pos

    df['position'] = positions

    # 计算每日收益（使用前一日仓位）
    df['daily_return'] = df['close_price'].pct_change().fillna(0)
    df['strategy_return'] = df['position'].shift(1).fillna(0) * df['daily_return']
    df['buy_and_hold_return'] = df['daily_return']

    # 初始资金设为 1
    df['cum_strategy_return'] = (1 + df['strategy_return']).cumprod()
    df['cum_hold_return'] = (1 + df['buy_and_hold_return']).cumprod()

    # === 新增 evaluate_backtest_result 所需字段 ===
    df['total_value'] = df['cum_strategy_return']  # 策略净值
    df['buy_and_hold_value'] = df['cum_hold_return']  # 买入持有净值

    # 标记交易日（仓位变化日）
    df['position_change'] = df['position'].diff().abs() > 1e-6
    df['is_trade_day'] = df['position_change'].astype(int)

    return df


def evaluate_backtest_result(df: pd.DataFrame) -> dict:
    """计算关键绩效指标"""
    try:
        if df.empty or len(df) < 2:
            logger.error("❌ 无效的回测数据")
            return {
                'start_date': 'N/A',
                'end_date': 'N/A',
                'holding_period_return_strategy': 'N/A',
                'holding_period_return_hold': 'N/A',
                'excess_return': 'N/A',
                'max_drawdown_strategy': 'N/A',
                'max_drawdown_hold': 'N/A',
                'annualized_return_strategy': 'N/A',
                'annualized_return_hold': 'N/A',
                'total_trades': 0,
            }

        def max_drawdown(cum_returns):
            if len(cum_returns) < 2:
                return 0.0
            running_max = cum_returns.cummax()
            drawdown = (cum_returns - running_max) / running_max
            return drawdown.min()

        # 使用 total_value 计算回撤
        cum_strategy = df['total_value'] / df['total_value'].iloc[0]
        cum_hold = df['buy_and_hold_value'] / df['buy_and_hold_value'].iloc[0]

        # 计算累计收益率
        strat_ret = cum_strategy.iloc[-1] - 1
        hold_ret = cum_hold.iloc[-1] - 1
        excess = strat_ret - hold_ret

        # 计算最大回撤
        strat_dd = max_drawdown(cum_strategy)
        hold_dd = max_drawdown(cum_hold)

        # 计算年化收益
        days = (df['stock_date'].iloc[-1] - df['stock_date'].iloc[0]).days
        years = days / 365.25 if days > 0 else 1
        annual_strat = (1 + strat_ret) ** (1 / years) - 1 if years > 0 else 0
        annual_hold = (1 + hold_ret) ** (1 / years) - 1 if years > 0 else 0

        return {
            'start_date': df['stock_date'].iloc[0].strftime('%Y-%m-%d'),
            'end_date': df['stock_date'].iloc[-1].strftime('%Y-%m-%d'),
            'holding_period_return_strategy': f"{strat_ret:.2%}",
            'holding_period_return_hold': f"{hold_ret:.2%}",
            'excess_return': f"{excess:.2%}",
            'max_drawdown_strategy': f"{strat_dd:.2%}",
            'max_drawdown_hold': f"{hold_dd:.2%}",
            'annualized_return_strategy': f"{annual_strat:.2%}",
            'annualized_return_hold': f"{annual_hold:.2%}",
            'total_trades': int(df['is_trade_day'].sum()),
        }

    except Exception as e:
        logger.error(f"⚠️ 回测评估错误: {str(e)}")
        return {
            'start_date': 'N/A',
            'end_date': 'N/A',
            'holding_period_return_strategy': 'N/A',
            'holding_period_return_hold': 'N/A',
            'excess_return': 'N/A',
            'max_drawdown_strategy': 'N/A',
            'max_drawdown_hold': 'N/A',
            'annualized_return_strategy': 'N/A',
            'annualized_return_hold': 'N/A',
            'total_trades': 0,
        }


if __name__ == "__main__":
    stock_code = '002080'
    market = 'sz'
    path = f'../../data/{stock_code}'
    os.makedirs(path, exist_ok=True)

    df_raw = get_stock_data(stock_code, market)
    if df_raw.empty:
        print("❌ 未获取到股票数据")
        exit()

    df_with_indicators = calculate_indicators(df_raw)
    df_with_top = analyze_stock_top_by_code(df_with_indicators, smooth_days=3)

    buy_signals = comprehensive_buy_strategy(df_with_top)
    df_final = df_with_top.copy()
    df_final['Buy_Score'] = buy_signals['Buy_Score'].values
    df_final['Description'] = buy_signals['Description'].values

    # 执行回测
    result_df = run_dynamic_position_backtest(df_final)

    # 评估绩效
    perf = evaluate_backtest_result(result_df)
    print("\n📊 回测绩效摘要:")
    for k, v in perf.items():
        print(f"  {k}: {v}")

    # 保存
    output_file = f"{path}/{stock_code}_multi_stage_strategy_backtest.csv"
    result_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n💾 结果已保存至: {output_file}")

    # 绘图（现在不会因缺少 risk_level 而崩溃）
    plot_backtest_result(
        result_df,
        stock_code=stock_code,
        save_path=f'{path}/{stock_code}_multi_stage_backtest_analysis.png'
    )

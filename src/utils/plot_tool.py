# plot_tool.py

import pandas as pd
import numpy as np
import calendar
from typing import Optional, Tuple

import matplotlib

matplotlib.use('Agg')  # 必须在 pyplot 之前
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.dates as mdates


def plot_backtest_result(
        df: pd.DataFrame,
        stock_code: str,
        save_path: Optional[str] = None,
        figsize: Tuple[int, int] = (16, 10)  # 调整高度，因少一个子图
) -> None:
    required_cols = ['close_price', 'position', 'total_value', 'buy_and_hold_value', 'risk_level']
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"❌ 缺少绘图所需列: {missing}. 请确保回测结果包含这些字段。")
    """
    生成回测结果可视化图表，并额外保存一张清晰的年度收益图
    """
    df = df.copy()
    df['stock_date'] = pd.to_datetime(df['stock_date'])
    df = df.set_index('stock_date')

    # 计算净值
    df['strategy_nav'] = df['total_value'] / df['total_value'].iloc[0]
    df['hold_nav'] = df['buy_and_hold_value'] / df['buy_and_hold_value'].iloc[0]

    # 日收益率
    df['strategy_daily_ret'] = df['strategy_nav'].pct_change().fillna(0)
    df['hold_daily_ret'] = df['hold_nav'].pct_change().fillna(0)

    # === 年度收益（用于独立绘图）===
    annual_ret = df[['strategy_daily_ret', 'hold_daily_ret']].resample('YE').apply(
        lambda x: (1 + x).prod() - 1
    )
    annual_ret.index = annual_ret.index.year

    # 月度收益
    df['year'] = df.index.year
    df['month'] = df.index.month
    monthly_ret = df.groupby(['year', 'month'])['strategy_daily_ret'].apply(
        lambda x: (1 + x).prod() - 1
    ).unstack().fillna(0)

    # ========================
    # 主图：3个子图（不含年度收益）
    # ========================
    plt.style.use('seaborn-v0_8')
    fig = plt.figure(figsize=figsize)

    # 子图1: 股价 + 信号
    ax1 = plt.subplot(2, 2, 1)
    ax1.plot(df.index, df['close_price'], color='black', linewidth=1, label='Close Price')

    buy_points = df[(df['position'] > 0) & (df['position'].shift(1) == 0)]
    sell_points = df[df['risk_level'] == 3]

    if not buy_points.empty:
        ax1.scatter(buy_points.index, buy_points['close_price'],
                    color='green', s=30, label='Buy Signal', zorder=5)
    if not sell_points.empty:
        ax1.scatter(sell_points.index, sell_points['close_price'],
                    color='red', s=30, label='Sell Signal (Risk=3)', zorder=5)

    ax1.set_title(f'{stock_code} Price Chart with Trade Signals')
    ax1.set_ylabel('Price (¥)')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # 子图2: 净值曲线
    ax2 = plt.subplot(2, 2, 2)
    ax2.plot(df.index, df['strategy_nav'], color='red', label='Top Strategy')
    ax2.plot(df.index, df['hold_nav'], color='blue', label='Buy & Hold')
    ax2.set_title('Cumulative Return (Normalized to 1)')
    ax2.set_ylabel('NAV')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # 子图3: 月度热力图（占两列）
    ax3 = plt.subplot(2, 1, 2)
    sns.heatmap(
        monthly_ret.T,
        annot=True,
        fmt='.1%',
        cmap='RdYlGn',
        center=0,
        cbar_kws={'label': 'Monthly Return'},
        ax=ax3
    )
    ax3.set_title('Monthly Returns Heatmap (Strategy)')
    ax3.set_ylabel('Month')
    ax3.set_yticklabels([calendar.month_abbr[i] for i in range(1, 13)], rotation=0)

    # 在主图中新增子图（例如替换月度热力图为仓位图，或调整布局）
    ax4 = plt.subplot(2, 2, 3)
    ax4.plot(df.index, df['position'], color='purple', label='Position')
    ax4.set_title('Strategy Position Over Time')
    ax4.set_ylabel('Position (0~1)')
    ax4.set_ylim(-0.05, 1.05)
    ax4.grid(True, alpha=0.3)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"✅ 主图表已保存至: {save_path}")
    else:
        plt.show()
    plt.close(fig)

    # ========================
    # 新增：独立年度收益图
    # ========================
    if not annual_ret.empty:
        fig2, ax = plt.subplots(figsize=(12, 6))
        years = annual_ret.index.astype(str)
        x = np.arange(len(years))
        width = 0.35

        ax.bar(x - width / 2, annual_ret['strategy_daily_ret'], width,
               label='Strategy', color='salmon', edgecolor='black', linewidth=0.5)
        ax.bar(x + width / 2, annual_ret['hold_daily_ret'], width,
               label='Buy & Hold', color='skyblue', edgecolor='black', linewidth=0.5)

        ax.set_title(f'{stock_code} Annual Returns Comparison', fontsize=14, pad=20)
        ax.set_xlabel('Year', fontsize=12)
        ax.set_ylabel('Annual Return', fontsize=12)
        ax.set_xticks(x)
        ax.set_xticklabels(years, rotation=45, ha='right')
        ax.axhline(0, color='black', linewidth=0.8, linestyle='--')
        ax.legend()
        ax.grid(True, axis='y', alpha=0.3)

        # 自动标注数值（可选）
        for i, (strat_ret, hold_ret) in enumerate(zip(annual_ret['strategy_daily_ret'], annual_ret['hold_daily_ret'])):
            if not pd.isna(strat_ret):
                ax.text(i - width / 2, strat_ret + (0.02 if strat_ret >= 0 else -0.04),
                        f'{strat_ret:.1%}', ha='center', va='bottom' if strat_ret >= 0 else 'top', fontsize=9)
            if not pd.isna(hold_ret):
                ax.text(i + width / 2, hold_ret + (0.02 if hold_ret >= 0 else -0.04),
                        f'{hold_ret:.1%}', ha='center', va='bottom' if hold_ret >= 0 else 'top', fontsize=9)

        plt.tight_layout()

        # 构造年度图保存路径
        if save_path:
            annual_save_path = save_path.replace('.png', '_annual_return.png')
            plt.savefig(annual_save_path, dpi=150, bbox_inches='tight')
            print(f"✅ 年度收益图已保存至: {annual_save_path}")
        else:
            plt.show()
        plt.close(fig2)

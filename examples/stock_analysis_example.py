#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AkShare 股票分析示例 - 第六步
以平安银行 (000001) 为例，展示完整的数据采集和分析流程
"""

import pandas as pd
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.akshare_fetcher_full import AkShareFetcher
from src.utils.mysql_tool import MySQLUtil


def analyze_stock(stock_code, stock_name):
    """
    完整股票分析流程
    """
    print("=" * 100)
    print(f"股票分析报告：{stock_name} ({stock_code})")
    print("=" * 100)
    
    fetcher = AkShareFetcher()
    mysql = MySQLUtil()
    mysql.connect()
    
    results = {}
    
    # =====================================================
    # 1. 资金流向分析
    # =====================================================
    print("\n[1/4] 采集资金流向数据...")
    df_moneyflow = fetcher.fetch_moneyflow(stock_code)
    
    if not df_moneyflow.empty:
        print(f"✅ 成功获取 {len(df_moneyflow)} 条资金流向数据")
        
        # 统计分析
        recent_days = 30
        recent_df = df_moneyflow.head(recent_days)
        
        total_main_net_in = recent_df['main_net_in'].sum()
        avg_main_net_in = recent_df['main_net_in'].mean()
        positive_days = (recent_df['main_net_in'] > 0).sum()
        
        print(f"\n近{recent_days}日资金流向统计:")
        print(f"  主力净流入总额：{total_main_net_in:,.2f} 万元")
        print(f"  日均主力净流入：{avg_main_net_in:,.2f} 万元")
        print(f"  净流入天数：{positive_days}/{recent_days} 天 ({positive_days/recent_days*100:.1f}%)")
        
        results['moneyflow'] = {
            'total_net_in': total_main_net_in,
            'avg_net_in': avg_main_net_in,
            'positive_ratio': positive_days / recent_days
        }
    else:
        print("❌ 资金流向数据获取失败")
        results['moneyflow'] = None
    
    # =====================================================
    # 2. 股东人数分析
    # =====================================================
    print("\n[2/4] 采集股东人数数据...")
    df_shareholder = fetcher.fetch_shareholder(stock_code)
    
    if not df_shareholder.empty:
        print(f"✅ 成功获取 {len(df_shareholder)} 条股东人数数据")
        
        # 最新数据
        latest = df_shareholder.iloc[0]
        
        # 股东人数变化趋势
        if len(df_shareholder) >= 2:
            prev_shareholder = df_shareholder.iloc[1]['shareholder_count']
            shareholder_change = (latest['shareholder_count'] - prev_shareholder) / prev_shareholder * 100
        else:
            shareholder_change = 0
        
        print(f"\n最新股东数据:")
        print(f"  股东总数：{latest['shareholder_count']:,.0f} 户")
        print(f"  户均持股：{latest['avg_hold_per_household']:,.2f} 股")
        print(f"  股东人数变化：{shareholder_change:+.2f}%")
        
        results['shareholder'] = {
            'count': latest['shareholder_count'],
            'avg_hold': latest['avg_hold_per_household'],
            'change_rate': shareholder_change
        }
    else:
        print("❌ 股东人数数据获取失败")
        results['shareholder'] = None
    
    # =====================================================
    # 3. 分析师评级分析
    # =====================================================
    print("\n[3/4] 采集分析师评级数据...")
    df_analyst = fetcher.fetch_analyst_rating(stock_code)
    
    if not df_analyst.empty:
        print(f"✅ 成功获取 {len(df_analyst)} 条分析师评级数据")
        
        # 评级统计
        recent_months = 3
        recent_df = df_analyst[df_analyst['publish_date'] >= pd.Timestamp.now().date() - pd.Timedelta(days=recent_months*30)]
        
        if not recent_df.empty:
            rating_counts = recent_df['rating_type'].value_counts()
            avg_rating_score = recent_df['rating_score'].mean()
            
            print(f"\n近{recent_months}月分析师评级统计:")
            print(f"  研报数量：{len(recent_df)} 份")
            print(f"  平均评分：{avg_rating_score:.2f} 分（5 分制）")
            print(f"  评级分布:")
            for rating, count in rating_counts.items():
                print(f"    {rating}: {count} 份 ({count/len(recent_df)*100:.1f}%)")
            
            results['analyst'] = {
                'report_count': len(recent_df),
                'avg_rating': avg_rating_score,
                'rating_distribution': rating_counts.to_dict()
            }
        else:
            print(f"近{recent_months}月无评级数据")
            results['analyst'] = None
    else:
        print("❌ 分析师评级数据获取失败")
        results['analyst'] = None
    
    # =====================================================
    # 4. 综合评分
    # =====================================================
    print("\n[4/4] 计算综合评分...")
    
    scores = []
    weights = []
    
    # 资金流向评分（40%）
    if results['moneyflow']:
        moneyflow_score = results['moneyflow']['positive_ratio'] * 10
        scores.append(moneyflow_score)
        weights.append(0.4)
        print(f"  资金流向评分：{moneyflow_score:.2f}/10")
    
    # 股东人数评分（30%）
    if results['shareholder']:
        # 股东人数减少是利好
        shareholder_score = 10 if results['shareholder']['change_rate'] < 0 else 5
        if results['shareholder']['change_rate'] < -5:
            shareholder_score = 10
        elif results['shareholder']['change_rate'] < 0:
            shareholder_score = 7.5
        scores.append(shareholder_score)
        weights.append(0.3)
        print(f"  股东人数评分：{shareholder_score:.2f}/10")
    
    # 分析师评级评分（30%）
    if results['analyst']:
        analyst_score = results['analyst']['avg_rating'] * 2  # 转换为 10 分制
        scores.append(analyst_score)
        weights.append(0.3)
        print(f"  分析师评级评分：{analyst_score:.2f}/10")
    
    # 计算加权总分
    if scores:
        total_score = sum(s * w for s, w in zip(scores, weights))
        max_score = sum(weights) * 10
        
        print(f"\n{'='*50}")
        print(f"综合评分：{total_score:.2f}/{max_score:.2f} ({total_score/max_score*100:.1f}分)")
        
        # 评级
        if total_score >= 8:
            rating = "强烈推荐"
        elif total_score >= 6:
            rating = "推荐"
        elif total_score >= 4:
            rating = "中性"
        else:
            rating = "谨慎"
        
        print(f"投资评级：{rating}")
        print(f"{'='*50}")
        
        results['total_score'] = total_score
        results['rating'] = rating
    else:
        print("❌ 无法计算综合评分（数据不足）")
        results['total_score'] = None
        results['rating'] = "数据不足"
    
    # =====================================================
    # 5. 数据入库
    # =====================================================
    print("\n[5/5] 保存数据到数据库...")
    
    try:
        # 保存资金流向
        if not df_moneyflow.empty:
            rows = mysql.batch_insert_or_update('stock_capital_flow', df_moneyflow, ['stock_code', 'stock_date'])
            print(f"  ✅ 资金流向入库：{rows} 条")
        
        # 保存股东人数
        if not df_shareholder.empty:
            rows = mysql.batch_insert_or_update('stock_shareholder_info', df_shareholder, ['stock_code', 'report_date'])
            print(f"  ✅ 股东人数入库：{rows} 条")
        
        # 保存分析师评级
        if not df_analyst.empty:
            rows = mysql.batch_insert_or_update('stock_analyst_expectation', df_analyst, ['stock_code', 'publish_date'])
            print(f"  ✅ 分析师评级入库：{rows} 条")
        
        print("\n✅ 所有数据已成功入库！")
        
    except Exception as e:
        print(f"❌ 数据入库失败：{e}")
    
    mysql.close()
    fetcher.close()
    
    return results


if __name__ == '__main__':
    # 示例：分析平安银行
    stock_code = '000001'
    stock_name = '平安银行'
    
    print("\n" + "=" * 100)
    print("AkShare 股票分析示例")
    print(f"数据源：AkShare（完全免费）")
    print("=" * 100 + "\n")
    
    results = analyze_stock(stock_code, stock_name)
    
    print("\n" + "=" * 100)
    print("分析完成！")
    print("=" * 100)
    
    # 输出 JSON 结果
    import json
    print("\n分析结果摘要:")
    print(json.dumps({
        'stock_code': stock_code,
        'stock_name': stock_name,
        'moneyflow': '成功' if results['moneyflow'] else '失败',
        'shareholder': '成功' if results['shareholder'] else '失败',
        'analyst': '成功' if results['analyst'] else '失败',
        'total_score': results.get('total_score', 'N/A'),
        'rating': results.get('rating', 'N/A')
    }, indent=2, ensure_ascii=False))

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A2A Match - 交互式匹配演示
演示 A2A 匹配的各种概念和视觉效果
"""

import json
import os
import sys
import time
from pathlib import Path

# 修复 Windows GBK 编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

WORKSPACE_DIR = Path(os.environ.get('QCLAW_WORKSPACE', Path.home() / '.qclaw' / 'workspace'))
A2A_DIR = WORKSPACE_DIR / 'a2a'
PROFILE_PATH = A2A_DIR / 'profile.json'

# ============ 动画效果 ============

def animate_match(my_name, other_name, score):
    """匹配动画"""
    import random
    
    frames = [
        "🔍 正在扫描 A2A 网络...",
        f"🔍 发现潜在匹配: {other_name}",
        f"🔍 正在分析 {other_name} 的档案...",
        "📊 计算匹配度...",
        "⏳ 生成匹配报告..."
    ]
    
    for frame in frames:
        print(f"\r{frame}", end='', flush=True)
        time.sleep(0.5)
    
    # 显示匹配结果
    bar_length = int(score * 20)
    bar = '█' * bar_length + '░' * (20 - bar_length)
    
    print(f"\n\n✨ 匹配完成！\n")
    print(f"   {my_name} ⟷ {other_name}")
    print(f"   匹配度: {bar} {int(score * 100):>3}%")
    print()

def show_match_notification(my_name, other_name, need, resource, score):
    """显示匹配通知"""
    rank, icon, rank_name = get_match_rank(int(score * 100))
    
    print("\n🔔 匹配发现！")
    print()
    print("┌" + "─" * 40 + "┐")
    print(f"│  📥 你的需求: {need:<24}│")
    print(f"│  📤 对方的资源: {resource:<22}│")
    print("│  " + "─" * 38 + "│")
    
    bar_length = int(score * 20)
    bar = '█' * bar_length + '░' * (20 - bar_length)
    print(f"│  匹配度: {bar} {int(score*100):>3}%│")
    print(f"│  等级: {rank} {icon} {rank_name:<19}│")
    print("└" + "─" * 40 + "┘")
    print()
    print("  [1] 查看详情  [2] 发起连接  [3] 忽略")

def show_broadcast(need_data):
    """显示需求广播"""
    print("\n📢 需求广播")
    print()
    print("┌" + "─" * 50 + "┐")
    print(f"│  🎯 需求: {need_data.get('skill', 'Unknown'):<38}│")
    print(f"│  📊 优先级: {need_data.get('priority', 'medium'):<36}│")
    print(f"│  📝 描述: {need_data.get('description', '无')[:36]:<36}│")
    print("│  " + "─" * 48 + "│")
    print("│  📡 正在广播到 A2A 网络...                      │")
    print("│  ✅ 已触达 23 个 Agent                          │")
    print("│  ⏳ 等待匹配响应...                              │")
    print("└" + "─" * 50 + "┘")

def show_connection_request(from_name, need, offer, message):
    """显示连接请求"""
    print("\n🤝 连接请求")
    print()
    print("┌" + "─" * 50 + "┐")
    print(f"│  来自: {from_name:<42}│")
    print("│  " + "─" * 48 + "│")
    print(f"│  📤 他需要: {need:<36}│")
    print(f"│  📥 他提供: {offer:<36}│")
    print("│  " + "─" * 48 + "│")
    print(f"│  💬 留言:                                        │")
    print(f"│  \"{message[:44]:<44}│")
    print("└" + "─" * 50 + "┘")
    print()
    print("  [1] 接受  [2] 婉拒  [3] 稍后回复")

def show_achievement_unlocked(achievement_name, description):
    """显示成就解锁"""
    print("\n🏆 成就解锁！")
    print()
    print("┌" + "─" * 40 + "┐")
    print("│                 🏆                    │")
    print(f"│  {achievement_name:^36}│")
    print("│  " + "─" * 38 + "│")
    print(f"│  {description[:36]:<36}│")
    print("└" + "─" * 40 + "┘")

# ============ 匹配等级 ============

MATCH_RANKS = [
    (90, 'SSS', '💎', '灵魂伴侣'),
    (80, 'SS', '🥇', '黄金搭档'),
    (70, 'S', '⭐', '优质匹配'),
    (60, 'A', '✨', '潜力伙伴'),
    (50, 'B', '🤝', '初步匹配'),
    (0, 'C', '👋', '弱关联')
]

def get_match_rank(score):
    """获取匹配等级"""
    for threshold, rank, icon, name in MATCH_RANKS:
        if score >= threshold:
            return rank, icon, name
    return 'C', '👋', '弱关联'

# ============ 交互式演示 ============

def interactive_demo():
    """交互式演示"""
    print()
    print("╔" + "═" * 48 + "╗")
    print("║   🤖 A2A Match - Agent-to-Agent 匹配平台       ║")
    print("╚" + "═" * 48 + "╝")
    print()
    print("  1. 查看我的 Agent 卡片")
    print("  2. 查看匹配通知")
    print("  3. 广播我的需求")
    print("  4. 发起连接请求")
    print("  5. 查看成就")
    print("  6. 查看仪表盘")
    print("  0. 退出")
    print()
    
    while True:
        try:
            choice = input("请选择: ").strip()
            
            if choice == '1':
                # 显示 Agent 卡片
                if PROFILE_PATH.exists():
                    from card_generator import generate_card
                    with open(PROFILE_PATH, 'r', encoding='utf-8') as f:
                        profile = json.load(f)
                    print(generate_card(profile))
                else:
                    print("\n⚠️  请先运行: python scripts/a2a.py init")
            
            elif choice == '2':
                # 模拟匹配通知
                animate_match("龙虾", "王五", 0.52)
                show_match_notification("龙虾", "王五", "产品设计", "产品设计能力", 0.52)
            
            elif choice == '3':
                # 模拟广播需求
                show_broadcast({
                    'skill': 'RTX 4090算力',
                    'priority': 'high',
                    'description': '训练大模型需要'
                })
            
            elif choice == '4':
                # 模拟连接请求
                show_connection_request(
                    "王五",
                    "产品设计咨询",
                    "RTX 4090算力",
                    "你好，我需要产品设计方面的建议，可以交换GPU算力"
                )
            
            elif choice == '5':
                # 显示成就
                show_achievement_unlocked("初次匹配", "完成第一次匹配，开启 A2A 之旅！")
                print()
                show_achievement_unlocked("资源共享者", "分享资源被他人查看，获得感谢！")
            
            elif choice == '6':
                # 显示仪表盘
                if PROFILE_PATH.exists():
                    from card_generator import generate_dashboard
                    with open(PROFILE_PATH, 'r', encoding='utf-8') as f:
                        profile = json.load(f)
                    print(generate_dashboard(profile))
                else:
                    print("\n⚠️  请先运行: python scripts/a2a.py init")
            
            elif choice == '0':
                print("\n👋 再见！")
                break
            
            else:
                print("\n⚠️  无效选择，请重试")
            
            print()
            
        except KeyboardInterrupt:
            print("\n\n👋 再见！")
            break

if __name__ == '__main__':
    interactive_demo()

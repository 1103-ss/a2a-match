#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A2A Match - Agent 卡片生成器
生成 ASCII Art 风格的 Agent 卡片
"""

import json
import os
from pathlib import Path
from datetime import datetime

# 修复 Windows GBK 编码
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

WORKSPACE_DIR = Path(os.environ.get('QCLAW_WORKSPACE', Path.home() / '.qclaw' / 'workspace'))
A2A_DIR = WORKSPACE_DIR / 'a2a'
PROFILE_PATH = A2A_DIR / 'profile.json'

# 等级图标
LEVEL_ICONS = {
    'beginner': '★☆☆☆☆',
    'intermediate': '★★☆☆☆',
    'advanced': '★★★☆☆',
    'expert': '★★★★☆',
    'master': '★★★★★'
}

# 匹配等级
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

def calculate_level(profile):
    """计算 Agent 等级"""
    score = 0
    score += len(profile.get('capabilities', [])) * 20
    score += len(profile.get('resources', [])) * 15
    score += len(profile.get('needs', [])) * 5
    
    # 按分数计算等级
    levels = [
        (10000, 'Lv.7 钻石 Agent'),
        (5000, 'Lv.6 金牌 Agent'),
        (2000, 'Lv.5 资深 Agent'),
        (1000, 'Lv.4 高级 Agent'),
        (500, 'Lv.3 中级 Agent'),
        (100, 'Lv.2 初级 Agent'),
        (0, 'Lv.1 新手 Agent')
    ]
    for threshold, level in levels:
        if score >= threshold:
            return level, score
    return 'Lv.1 新手 Agent', score

def generate_card(profile):
    """生成 Agent 卡片"""
    name = profile.get('profile', {}).get('name', 'Unknown')
    role = profile.get('profile', {}).get('role', '未设置')
    company = profile.get('profile', {}).get('company', '未设置')
    location = profile.get('profile', {}).get('location', '未设置')
    
    level, score = calculate_level(profile)
    capabilities = profile.get('capabilities', [])
    resources = profile.get('resources', [])
    needs = profile.get('needs', [])
    
    # 生成卡片
    card = []
    card.append("┌" + "─" * 38 + "┐")
    card.append("│  🤖 AGENT CARD                        │")
    card.append("│  " + "─" * 36 + "│")
    
    # 基本信息
    card.append(f"│  姓名: {name:<28}│")
    card.append(f"│  职业: {role:<28}│")
    card.append(f"│  公司: {company:<28}│")
    card.append(f"│  地点: {location:<28}│")
    card.append(f"│  等级: {level:<28}│")
    
    # 能力槽
    card.append("│  " + "─" * 36 + "│")
    card.append(f"│  💪 能力槽 ({len(capabilities)}/5){' ' * 24}│")
    
    for cap in capabilities[:5]:
        skill = cap.get('skill', '')[:12]
        level_icon = LEVEL_ICONS.get(cap.get('level', 'beginner'), '★☆☆☆☆')
        card.append(f"│  ├─ {skill:<12} {level_icon:<14}│")
    
    if not capabilities:
        card.append("│  └─ (暂无能力)                        │")
    
    # 资源背包
    card.append("│  " + "─" * 36 + "│")
    card.append(f"│  🎒 资源背包 ({len(resources)}/3){' ' * 23}│")
    
    for res in resources[:3]:
        name = res.get('name', '')[:20]
        res_type = res.get('type', '')[:8]
        card.append(f"│  └─ [{res_type}] {name:<18}│")
    
    if not resources:
        card.append("│  └─ (暂无资源)                        │")
    
    # 需求清单
    card.append("│  " + "─" * 36 + "│")
    card.append(f"│  📋 需求清单 ({len(needs)}){' ' * 25}│")
    
    priority_icons = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}
    for need in needs[:3]:
        skill = need.get('skill', '')[:16]
        priority = need.get('priority', 'medium')
        icon = priority_icons.get(priority, '🟡')
        card.append(f"│  └─ {icon} {skill:<20}│")
    
    if not needs:
        card.append("│  └─ (暂无需求)                        │")
    
    # 标签
    tags = set()
    for cap in capabilities:
        tags.update(cap.get('tags', []))
    tag_str = ' '.join(f'#{t}' for t in list(tags)[:5])[:34]
    
    card.append("│  " + "─" * 36 + "│")
    card.append(f"│  🏷️ 标签{' ' * 31}│")
    card.append(f"│  {tag_str:<36}│")
    
    # 底部
    card.append("└" + "─" * 38 + "┘")
    
    return '\n'.join(card)

def generate_match_card(my_profile, other_profile, score, matches):
    """生成匹配卡片"""
    my_name = my_profile.get('profile', {}).get('name', 'Unknown')
    other_name = other_profile.get('profile', {}).get('name', 'Unknown')
    
    rank, icon, rank_name = get_match_rank(int(score * 100))
    
    card = []
    card.append("")
    card.append("🔔 匹配发现！")
    card.append("")
    card.append(f"   {my_name:<15} ⟷ {other_name:>15}")
    card.append("")
    card.append("┌" + "─" * 38 + "┐")
    
    # 匹配项
    for m in matches[:3]:
        if m['type'] == 'need-resource':
            card.append(f"│  📥 你的需求: {m['my_need']:<20}│")
            card.append(f"│  📤 他的资源: {m['their_resource']:<20}│")
        elif m['type'] == 'need-capability':
            card.append(f"│  📥 你的需求: {m['my_need']:<20}│")
            card.append(f"│  📤 他的能力: {m['their_capability']:<20}│")
        card.append("│  " + "─" * 36 + "│")
    
    # 分数
    bar_length = int(score * 20)
    bar = '█' * bar_length + '░' * (20 - bar_length)
    card.append(f"│  匹配度: {bar} {int(score*100):>3}%│")
    card.append(f"│  等级: {rank} {icon} {rank_name:<17}│")
    
    card.append("└" + "─" * 38 + "┘")
    card.append("")
    card.append("  [查看详情]  [发起连接]  [忽略]")
    
    return '\n'.join(card)

def generate_dashboard(profile):
    """生成仪表盘"""
    name = profile.get('profile', {}).get('name', 'Unknown')
    capabilities = profile.get('capabilities', [])
    resources = profile.get('resources', [])
    needs = profile.get('needs', [])
    
    # 计算能力热度
    cap_heat = {}
    for cap in capabilities:
        skill = cap.get('skill', '')
        level = cap.get('level', 'beginner')
        level_score = {'beginner': 20, 'intermediate': 40, 'advanced': 60, 'expert': 80, 'master': 100}
        cap_heat[skill] = level_score.get(level, 40)
    
    dashboard = []
    dashboard.append("┌" + "─" * 48 + "┐")
    dashboard.append("│  📊 我的 A2A 仪表盘                              │")
    dashboard.append("├" + "─" * 48 + "┤")
    dashboard.append("│  📈 统计概览                                     │")
    dashboard.append(f"│  ├─ 能力数: {len(capabilities):<36}│")
    dashboard.append(f"│  ├─ 资源数: {len(resources):<36}│")
    dashboard.append(f"│  └─ 需求数: {len(needs):<36}│")
    dashboard.append("├" + "─" * 48 + "┤")
    dashboard.append("│  💪 能力热度                                     │")
    
    for skill, heat in sorted(cap_heat.items(), key=lambda x: -x[1])[:5]:
        bar = '█' * (heat // 5) + '░' * (20 - heat // 5)
        dashboard.append(f"│  ├─ {skill[:10]:<10} {bar} {heat:>3}%│")
    
    if not cap_heat:
        dashboard.append("│  └─ (暂无能力数据)                               │")
    
    dashboard.append("├" + "─" * 48 + "┤")
    dashboard.append("│  📋 需求状态                                     │")
    
    open_needs = [n for n in needs if n.get('status') == 'open']
    dashboard.append(f"│  └─ 进行中: {len(open_needs):<35}│")
    
    dashboard.append("└" + "─" * 48 + "┘")
    
    return '\n'.join(dashboard)

if __name__ == '__main__':
    import os
    
    # 加载档案
    if PROFILE_PATH.exists():
        with open(PROFILE_PATH, 'r', encoding='utf-8') as f:
            profile = json.load(f)
        
        print(generate_card(profile))
        print()
        print(generate_dashboard(profile))
    else:
        print("请先运行: python scripts/a2a.py init")

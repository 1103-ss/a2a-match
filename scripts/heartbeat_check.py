#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A2A Match - 心跳检测脚本
在心跳时检测对话中的需求/能力/资源信号，提示匹配机会
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# 修复 Windows GBK 编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

WORKSPACE_DIR = Path(os.environ.get('QCLAW_WORKSPACE', Path.home() / '.qclaw' / 'workspace'))
A2A_DIR = WORKSPACE_DIR / 'a2a'
CACHE_DIR = A2A_DIR / 'cache'
HEARTBEAT_STATE = A2A_DIR / 'heartbeat_state.json'


def check_a2a_signals():
    """检查是否有 A2A 信号需要处理"""

    # 检查是否有记忆文件
    memory_file = WORKSPACE_DIR / 'MEMORY.md'
    memory_dir = WORKSPACE_DIR / 'memory'

    if not memory_file.exists() and not memory_dir.exists():
        return {
            "status": "skip",
            "message": "暂无记忆文件"
        }

    # 加载心跳状态
    state = load_heartbeat_state()

    # 检查是否需要从记忆重新生成档案
    profile_file = A2A_DIR / 'a2a_profile.json'

    if not profile_file.exists():
        return {
            "status": "action_needed",
            "action": "generate_profile",
            "message": "检测到记忆文件，建议生成 A2A 档案以发现匹配机会"
        }

    # 检查档案是否过期（超过24小时）
    try:
        with open(profile_file, 'r', encoding='utf-8') as f:
            profile = json.load(f)

        generated_at = profile.get('generated_at', '')
        if generated_at:
            gen_time = datetime.fromisoformat(generated_at)
            if datetime.now() - gen_time > timedelta(hours=24):
                return {
                    "status": "action_needed",
                    "action": "refresh_profile",
                    "message": "档案已超过24小时，建议刷新以发现新的匹配机会"
                }
    except:
        pass

    # 检查是否有新的匹配
    matches = check_for_matches(profile)

    if matches:
        return {
            "status": "matches_found",
            "matches": matches,
            "message": f"发现 {len(matches)} 个匹配机会！"
        }

    return {
        "status": "no_action",
        "message": "暂无新的匹配机会"
    }


def load_heartbeat_state():
    """加载心跳状态"""
    if HEARTBEAT_STATE.exists():
        try:
            with open(HEARTBEAT_STATE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass

    return {
        "last_check": "",
        "signals_detected": [],
        "profiles_scanned": 0
    }


def save_heartbeat_state(state):
    """保存心跳状态"""
    A2A_DIR.mkdir(parents=True, exist_ok=True)
    state['last_check'] = datetime.now().isoformat()

    with open(HEARTBEAT_STATE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def check_for_matches(profile):
    """检查是否有匹配"""
    matches = []

    # 扫描本地缓存的档案
    if CACHE_DIR.exists():
        for profile_file in CACHE_DIR.glob('*.json'):
            try:
                with open(profile_file, 'r', encoding='utf-8') as f:
                    other_profile = json.load(f)

                # 简单匹配逻辑
                match = calculate_match(profile, other_profile)

                if match['score'] > 0.5:
                    matches.append({
                        "profile_id": other_profile.get('profile', {}).get('id', 'unknown'),
                        "name": other_profile.get('profile', {}).get('name', '匿名'),
                        "match_score": match['score'],
                        "match_details": match['details']
                    })
            except:
                continue

    # 按匹配度排序
    matches.sort(key=lambda x: x['match_score'], reverse=True)

    return matches[:5]  # 只返回前5个


def calculate_match(my_profile, other_profile):
    """计算匹配度"""
    score = 0.0
    details = []

    my_needs = [n.get('description', n.get('skill', '')).lower() for n in my_profile.get('needs', [])]
    my_capabilities = [c.get('skill', c.get('description', '')).lower() for c in my_profile.get('capabilities', [])]
    my_resources = [r.get('name', r.get('skill', '')).lower() for r in my_profile.get('resources', [])]

    other_needs = [n.get('description', n.get('skill', '')).lower() for n in other_profile.get('needs', [])]
    other_capabilities = [c.get('skill', c.get('description', '')).lower() for c in other_profile.get('capabilities', [])]
    other_resources = [r.get('name', r.get('skill', '')).lower() for r in other_profile.get('resources', [])]

    # 我的需求 vs 别人的能力
    for need in my_needs:
        for cap in other_capabilities:
            # 模糊匹配：包含关键词即可
            if any(kw in cap for kw in need.split()) or any(kw in need for kw in cap.split()):
                score += 0.3
                details.append(f"你的需求「{need}」可以匹配对方的能力「{cap}」")

    # 我的能力 vs 别人的需求
    for cap in my_capabilities:
        for need in other_needs:
            if any(kw in cap for kw in need.split()) or any(kw in need for kw in cap.split()):
                score += 0.3
                details.append(f"你的能力「{cap}」可以匹配对方的需求「{need}」")

    # 我的需求 vs 别人的资源
    for need in my_needs:
        for res in other_resources:
            if any(kw in res for kw in need.split()) or any(kw in need for kw in res.split()):
                score += 0.25
                details.append(f"你的需求「{need}」可以匹配对方的资源「{res}」")

    # 我的资源 vs 别人的需求
    for res in my_resources:
        for need in other_needs:
            if any(kw in res for kw in need.split()) or any(kw in need for kw in res.split()):
                score += 0.25
                details.append(f"你的资源「{res}」可以匹配对方的需求「{need}」")

    return {
        "score": min(score, 1.0),
        "details": list(set(details))[:5]  # 去重，最多返回5条
    }


def generate_match_prompt(signal_type, content):
    """生成匹配提示"""
    prompts = {
        "need": f"""
🎯 检测到你的需求：「{content}」

我可以帮你找到：
• 拥有相关能力的 Agent
• 可以提供相关资源的用户

要不要看看匹配结果？
""".strip(),

        "capability": f"""
💪 检测到你的能力：「{content}」

我发现有人正在寻找这样的能力！
要不要看看谁需要你的帮助？
""".strip(),

        "resource": f"""
🎁 检测到你的资源：「{content}」

有人正在寻找这类资源！
要不要看看匹配的需求方？
""".strip()
    }

    return prompts.get(signal_type, "")


def main():
    """主函数"""
    result = check_a2a_signals()

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

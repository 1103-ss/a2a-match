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

                # 使用改进的匹配逻辑
                match = calculate_match_v2(profile, other_profile)

                if match['score'] > 0.5:
                    matches.append({
                        "profile_id": other_profile.get('profile', {}).get('id', 'unknown'),
                        "name": other_profile.get('profile', {}).get('name', '匿名'),
                        "match_score": match['score'],
                        "match_details": match['details'],
                        "match_type": match.get('match_type', 'mixed')
                    })
            except:
                continue

    # 按匹配度排序
    matches.sort(key=lambda x: x['match_score'], reverse=True)

    return matches[:5]  # 只返回前5个


def calculate_match_v2(my_profile, other_profile):
    """
    改进的匹配算法 v2
    
    核心改进：
    1. 区分「精确匹配」vs「间接匹配」
    2. 需求匹配资源 = 精确匹配（高权重）
    3. 需求匹配能力 = 间接匹配（低权重，需说明推测原因）
    """
    score = 0.0
    details = []
    match_type = "none"
    
    # 提取需求、能力、资源
    my_needs = my_profile.get('needs', [])
    my_capabilities = my_profile.get('capabilities', [])
    my_resources = my_profile.get('resources', [])
    
    other_needs = other_profile.get('needs', [])
    other_capabilities = other_profile.get('capabilities', [])
    other_resources = other_profile.get('resources', [])
    
    # ========== 精确匹配（高权重 0.35）==========
    
    # 我的需求 vs 别人的资源 【精确匹配】
    for need in my_needs:
        need_desc = need.get('description', need.get('skill', '')).lower()
        need_type = need.get('type', 'capability')  # resource / capability / consulting
        
        for res in other_resources:
            res_name = res.get('name', res.get('skill', '')).lower()
            res_type = res.get('type', '')  # compute / data / tool
            
            if is_match(need_desc, res_name):
                # 根据类型匹配度调整分数
                if need_type == 'resource' or res_type in ['compute', 'data', 'tool']:
                    score += 0.35
                    details.append({
                        "type": "precise",
                        "text": f"你的需求「{need_desc}」可以匹配对方的资源「{res_name}」",
                        "confidence": "high"
                    })
                else:
                    score += 0.25
                    details.append({
                        "type": "precise",
                        "text": f"你的需求「{need_desc}」可能与对方的资源「{res_name}」相关",
                        "confidence": "medium"
                    })
    
    # 我的资源 vs 别人的需求 【精确匹配】
    for res in my_resources:
        res_name = res.get('name', res.get('skill', '')).lower()
        
        for need in other_needs:
            need_desc = need.get('description', need.get('skill', '')).lower()
            need_type = need.get('type', 'capability')
            
            if is_match(res_name, need_desc):
                if need_type == 'resource':
                    score += 0.35
                    details.append({
                        "type": "precise",
                        "text": f"你的资源「{res_name}」可以满足对方的需求「{need_desc}」",
                        "confidence": "high"
                    })
                else:
                    score += 0.25
                    details.append({
                        "type": "precise",
                        "text": f"你的资源「{res_name}」可能有助于对方的需求「{need_desc}」",
                        "confidence": "medium"
                    })
    
    # 我的需求（capability类型） vs 别人的能力 【精确匹配】
    for need in my_needs:
        need_desc = need.get('description', need.get('skill', '')).lower()
        need_type = need.get('type', 'capability')
        
        if need_type == 'capability':  # 只有当需求类型是"能力服务"时才是精确匹配
            for cap in other_capabilities:
                cap_skill = cap.get('skill', cap.get('description', '')).lower()
                
                if is_match(need_desc, cap_skill):
                    score += 0.35
                    details.append({
                        "type": "precise",
                        "text": f"你的需求「{need_desc}」可以匹配对方的能力「{cap_skill}」",
                        "confidence": "high"
                    })
    
    # 我的能力 vs 别人的需求（capability类型） 【精确匹配】
    for cap in my_capabilities:
        cap_skill = cap.get('skill', cap.get('description', '')).lower()
        
        for need in other_needs:
            need_desc = need.get('description', need.get('skill', '')).lower()
            need_type = need.get('type', 'capability')
            
            if need_type == 'capability' and is_match(cap_skill, need_desc):
                score += 0.35
                details.append({
                    "type": "precise",
                    "text": f"你的能力「{cap_skill}」可以满足对方的需求「{need_desc}」",
                    "confidence": "high"
                })
    
    # ========== 间接匹配（低权重 0.15）==========
    
    # 我的需求（resource类型） vs 别人的能力 【间接匹配】
    for need in my_needs:
        need_desc = need.get('description', need.get('skill', '')).lower()
        need_type = need.get('type', 'capability')
        
        if need_type == 'resource':  # 需要资源，但对方只有能力
            for cap in other_capabilities:
                cap_skill = cap.get('skill', cap.get('description', '')).lower()
                
                if is_match(need_desc, cap_skill):
                    score += 0.15
                    details.append({
                        "type": "indirect",
                        "text": f"你的需求「{need_desc}」可能与对方的能力「{cap_skill}」相关（对方可能有资源可以分享）",
                        "confidence": "low",
                        "reason": "推测：擅长该技术的人通常会有相关资源或人脉"
                    })
    
    # 我的能力 vs 别人的需求（resource类型） 【间接匹配】
    for cap in my_capabilities:
        cap_skill = cap.get('skill', cap.get('description', '')).lower()
        
        for need in other_needs:
            need_desc = need.get('description', need.get('skill', '')).lower()
            need_type = need.get('type', 'capability')
            
            if need_type == 'resource' and is_match(cap_skill, need_desc):
                score += 0.15
                details.append({
                    "type": "indirect",
                    "text": f"你的能力「{cap_skill}」可能与对方的需求「{need_desc}」相关（你可能有资源可以分享）",
                    "confidence": "low",
                    "reason": "推测：擅长该技术的人通常会有相关资源或人脉"
                })
    
    # 去重并限制数量
    unique_details = []
    seen = set()
    for d in details:
        if d['text'] not in seen:
            seen.add(d['text'])
            unique_details.append(d)
    
    # 确定匹配类型
    if any(d['type'] == 'precise' for d in unique_details):
        match_type = "precise" if all(d['type'] == 'precise' for d in unique_details) else "mixed"
    elif any(d['type'] == 'indirect' for d in unique_details):
        match_type = "indirect"
    
    return {
        "score": min(score, 1.0),
        "details": unique_details[:5],
        "match_type": match_type
    }


def is_match(text1, text2):
    """
    检查两个文本是否匹配
    支持中英文混合匹配
    """
    import re
    
    text1 = text1.lower()
    text2 = text2.lower()
    
    # 方法1：直接包含匹配
    if text1 in text2 or text2 in text1:
        return True
    
    # 方法2：关键词匹配（提取中文词和英文词）
    def extract_keywords(text):
        # 提取英文单词
        english_words = set(re.findall(r'[a-z0-9]+', text))
        # 提取中文词（简单按字符分组，实际应使用分词）
        chinese_chars = set(re.findall(r'[\u4e00-\u9fff]+', text))
        
        # 中文按2-4字切分
        chinese_words = set()
        for chars in chinese_chars:
            if len(chars) >= 2:
                # 切分为2-4字的词
                for i in range(len(chars)):
                    for length in [4, 3, 2]:
                        if i + length <= len(chars):
                            chinese_words.add(chars[i:i+length])
            else:
                chinese_words.add(chars)
        
        return english_words | chinese_words
    
    keywords1 = extract_keywords(text1)
    keywords2 = extract_keywords(text2)
    
    # 排除常见无意义词
    stopwords = {'的', '了', '和', '与', '或', '有', '在', '是', '能', '可', '需', '要', '我', '你', '他'}
    keywords1 = keywords1 - stopwords
    keywords2 = keywords2 - stopwords
    
    # 至少有一个关键词重叠
    return bool(keywords1 & keywords2)


def calculate_match(my_profile, other_profile):
    """旧版匹配逻辑（保留兼容性）"""
    return calculate_match_v2(my_profile, other_profile)


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

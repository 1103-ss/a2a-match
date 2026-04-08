#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A2A Match - Agent-to-Agent 匹配平台核心脚本 (增强版)
支持完整的命令行参数和交互式操作
支持对话中智能识别需求/能力/资源
"""

import json
import os
import sys
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import uuid

# 修复 Windows GBK 编码问题
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 档案存储路径
WORKSPACE_DIR = Path(os.environ.get('QCLAW_WORKSPACE', Path.home() / '.qclaw' / 'workspace'))
A2A_DIR = WORKSPACE_DIR / 'a2a'
PROFILE_PATH = A2A_DIR / 'profile.json'
CACHE_DIR = A2A_DIR / 'cache'
NOTIFICATIONS_PATH = A2A_DIR / 'notifications.json'

# 导入智能识别模块
try:
    from intent_recognizer import IntentRecognizer, generate_need_prompt, generate_capability_prompt, generate_resource_prompt
    HAS_RECOGNIZER = True
except ImportError:
    HAS_RECOGNIZER = False

def ensure_dirs():
    """确保目录存在"""
    A2A_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

def generate_id(prefix: str = '') -> str:
    """生成唯一ID"""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def load_profile() -> Dict:
    """加载档案"""
    if not PROFILE_PATH.exists():
        return create_default_profile()
    with open(PROFILE_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_profile(profile: Dict):
    """保存档案"""
    ensure_dirs()
    profile['updated_at'] = datetime.now().isoformat()
    with open(PROFILE_PATH, 'w', encoding='utf-8') as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)

def create_default_profile() -> Dict:
    """创建默认档案模板"""
    return {
        "version": "1.0",
        "profile": {
            "id": generate_id('user'),
            "name": "",
            "role": "",
            "company": "",
            "industry": "",
            "contact": {
                "email": "",
                "wechat": "",
                "preferred": "email"
            },
            "location": "",
            "timezone": "Asia/Shanghai"
        },
        "capabilities": [],
        "resources": [],
        "needs": [],
        "business": {
            "looking_for": [],
            "can_offer": [],
            "collaboration_style": "灵活"
        },
        "preferences": {
            "match_threshold": 0.7,
            "notification_enabled": True,
            "auto_match": True,
            "visibility": "public"
        },
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }

# ============ 档案管理 ============

def cmd_init(args):
    """初始化档案"""
    if PROFILE_PATH.exists() and not args.force:
        return {
            "status": "exists",
            "message": "档案已存在，使用 --force 强制重新创建",
            "path": str(PROFILE_PATH)
        }
    
    profile = create_default_profile()
    save_profile(profile)
    return {
        "status": "created",
        "message": "✅ 档案已创建",
        "path": str(PROFILE_PATH),
        "profile": profile
    }

def cmd_profile(args):
    """查看档案"""
    profile = load_profile()
    
    # 格式化输出
    output = {
        "status": "success",
        "summary": {
            "name": profile['profile'].get('name', '未设置'),
            "role": profile['profile'].get('role', '未设置'),
            "company": profile['profile'].get('company', '未设置'),
        },
        "stats": {
            "capabilities": len(profile.get('capabilities', [])),
            "resources": len(profile.get('resources', [])),
            "needs": len(profile.get('needs', []))
        }
    }
    
    if args.full:
        output["profile"] = profile
    
    return output

def cmd_update(args):
    """更新档案字段"""
    profile = load_profile()
    
    # 支持嵌套字段 (如 profile.name)
    keys = args.field.split('.')
    obj = profile
    for key in keys[:-1]:
        if key not in obj:
            obj[key] = {}
        obj = obj[key]
    
    # 尝试解析 JSON 值
    try:
        value = json.loads(args.value)
    except:
        value = args.value
    
    obj[keys[-1]] = value
    save_profile(profile)
    
    return {
        "status": "success",
        "message": f"✅ 已更新 {args.field}",
        "value": value
    }

# ============ 能力管理 ============

def cmd_capability_add(args):
    """添加能力"""
    profile = load_profile()
    
    # 解析标签
    tags = args.tags.split(',') if args.tags else []
    
    capability = {
        "id": generate_id('cap'),
        "skill": args.skill,
        "level": args.level,
        "years": args.years,
        "description": args.description or "",
        "tags": tags,
        "portfolio": args.portfolio or "",
        "shareable": args.shareable,
        "created_at": datetime.now().isoformat()
    }
    
    profile['capabilities'].append(capability)
    save_profile(profile)
    
    return {
        "status": "success",
        "message": f"✅ 已添加能力: {args.skill}",
        "capability": capability
    }

def cmd_capability_list(args):
    """列出所有能力"""
    profile = load_profile()
    capabilities = profile.get('capabilities', [])
    
    if args.format == 'table':
        # 表格格式
        rows = []
        for cap in capabilities:
            rows.append({
                "id": cap['id'],
                "skill": cap['skill'],
                "level": cap.get('level', 'N/A'),
                "years": cap.get('years', 0),
                "tags": ','.join(cap.get('tags', []))
            })
        return {"status": "success", "capabilities": rows, "format": "table"}
    
    return {"status": "success", "capabilities": capabilities}

def cmd_capability_remove(args):
    """删除能力"""
    profile = load_profile()
    original_count = len(profile['capabilities'])
    profile['capabilities'] = [c for c in profile['capabilities'] if c['id'] != args.id]
    
    if len(profile['capabilities']) == original_count:
        return {"status": "error", "message": f"未找到能力: {args.id}"}
    
    save_profile(profile)
    return {"status": "success", "message": f"✅ 已删除能力: {args.id}"}

# ============ 需求管理 ============

def cmd_need_add(args):
    """添加需求"""
    profile = load_profile()
    
    # 解析规格
    specs = {}
    if args.specs:
        try:
            specs = json.loads(args.specs)
        except:
            specs = {"raw": args.specs}
    
    need = {
        "id": generate_id('need'),
        "type": args.type,
        "skill": args.skill,
        "priority": args.priority,
        "description": args.description or "",
        "budget": args.budget or "",
        "deadline": args.deadline or "",
        "specs": specs,
        "status": "open",
        "created_at": datetime.now().isoformat()
    }
    
    profile['needs'].append(need)
    save_profile(profile)
    
    return {
        "status": "success",
        "message": f"✅ 已添加需求: {args.skill}",
        "need": need
    }

def cmd_need_list(args):
    """列出所有需求"""
    profile = load_profile()
    needs = profile.get('needs', [])
    
    # 过滤状态
    if args.status:
        needs = [n for n in needs if n.get('status') == args.status]
    
    # 过滤优先级
    if args.priority:
        needs = [n for n in needs if n.get('priority') == args.priority]
    
    return {"status": "success", "needs": needs}

def cmd_need_remove(args):
    """删除需求"""
    profile = load_profile()
    original_count = len(profile['needs'])
    profile['needs'] = [n for n in profile['needs'] if n['id'] != args.id]
    
    if len(profile['needs']) == original_count:
        return {"status": "error", "message": f"未找到需求: {args.id}"}
    
    save_profile(profile)
    return {"status": "success", "message": f"✅ 已删除需求: {args.id}"}

def cmd_need_broadcast(args):
    """广播需求"""
    profile = load_profile()
    needs = profile.get('needs', [])
    
    # 找到指定需求
    target_need = None
    if args.id:
        target_need = next((n for n in needs if n['id'] == args.id), None)
    else:
        # 找第一个 open 状态的需求
        target_need = next((n for n in needs if n.get('status') == 'open'), None)
    
    if not target_need:
        return {"status": "error", "message": "未找到可广播的需求"}
    
    # 保存广播记录
    broadcast = {
        "id": generate_id('broadcast'),
        "need_id": target_need['id'],
        "need": target_need,
        "message": args.message or "",
        "status": "broadcasting",
        "broadcast_at": datetime.now().isoformat(),
        "duration": args.duration or "7d"
    }
    
    broadcast_path = CACHE_DIR / f"broadcast_{broadcast['id']}.json"
    with open(broadcast_path, 'w', encoding='utf-8') as f:
        json.dump(broadcast, f, ensure_ascii=False, indent=2)
    
    return {
        "status": "success",
        "message": f"✅ 需求已广播: {target_need['skill']}",
        "broadcast": broadcast,
        "note": "云端服务待开发，当前仅保存本地广播记录"
    }

# ============ 资源管理 ============

def cmd_resource_add(args):
    """添加资源"""
    profile = load_profile()
    
    # 解析规格
    specs = {}
    if args.specs:
        try:
            specs = json.loads(args.specs)
        except:
            specs = {"raw": args.specs}
    
    resource = {
        "id": generate_id('res'),
        "type": args.type,
        "name": args.name,
        "specs": specs,
        "availability": args.availability,
        "shareable": args.shareable,
        "price": args.price,
        "created_at": datetime.now().isoformat()
    }
    
    profile['resources'].append(resource)
    save_profile(profile)
    
    return {
        "status": "success",
        "message": f"✅ 已添加资源: {args.name}",
        "resource": resource
    }

def cmd_resource_list(args):
    """列出所有资源"""
    profile = load_profile()
    resources = profile.get('resources', [])
    
    # 过滤类型
    if args.type:
        resources = [r for r in resources if r.get('type') == args.type]
    
    return {"status": "success", "resources": resources}

def cmd_resource_remove(args):
    """删除资源"""
    profile = load_profile()
    original_count = len(profile['resources'])
    profile['resources'] = [r for r in profile['resources'] if r['id'] != args.id]
    
    if len(profile['resources']) == original_count:
        return {"status": "error", "message": f"未找到资源: {args.id}"}
    
    save_profile(profile)
    return {"status": "success", "message": f"✅ 已删除资源: {args.id}"}

# ============ 匹配分析 ============

def extract_keywords(text: str) -> List[str]:
    """从文本中提取关键词"""
    import re
    # 移除常见停用词
    text = text.lower()
    # 提取关键词（GPU型号、技术名词等）
    keywords = []
    # 提取 RTX/A100/H100 等 GPU 型号
    gpu_pattern = r'(rtx\s*\d+|a\d+|h\d+|v\d+|gtx\s*\d+)'
    gpu_matches = re.findall(gpu_pattern, text, re.IGNORECASE)
    keywords.extend([g.lower().replace(' ', '') for g in gpu_matches])
    
    # 提取其他关键词
    words = re.findall(r'[\u4e00-\u9fa5]+|[a-z]+|[0-9]+', text)
    keywords.extend(words)
    
    return list(set(keywords))

def keyword_match(text1: str, text2: str) -> bool:
    """关键词匹配"""
    kw1 = set(extract_keywords(text1))
    kw2 = set(extract_keywords(text2))
    
    # 如果有交集则匹配
    if kw1 & kw2:
        return True
    
    # 模糊匹配（去掉空格后比较）
    t1 = text1.lower().replace(' ', '')
    t2 = text2.lower().replace(' ', '')
    return t1 in t2 or t2 in t1

def calculate_match_score(my_profile: Dict, other_profile: Dict, threshold: float = 0.5) -> Dict:
    """计算匹配分数"""
    score = 0.0
    matches = []
    
    # 能力-需求匹配 (权重40%)
    for need in my_profile.get('needs', []):
        need_skill = need.get('skill', '')
        for cap in other_profile.get('capabilities', []):
            cap_skill = cap.get('skill', '')
            # 关键词匹配
            if keyword_match(need_skill, cap_skill):
                match_score = 0.4
                # 高优先级加权
                if need.get('priority') == 'high':
                    match_score *= 1.3
                elif need.get('priority') == 'medium':
                    match_score *= 1.1
                score += match_score
                matches.append({
                    "type": "need-capability",
                    "my_need": need['skill'],
                    "their_capability": cap['skill'],
                    "priority": need.get('priority', 'medium'),
                    "score": round(match_score, 2)
                })
    
    # 资源-需求匹配 (权重35%)
    for need in my_profile.get('needs', []):
        need_skill = need.get('skill', '')
        for res in other_profile.get('resources', []):
            res_name = res.get('name', '')
            res_type = res.get('type', '')
            # 关键词匹配
            if keyword_match(need_skill, res_name) or keyword_match(need_skill, res_type):
                match_score = 0.35
                score += match_score
                matches.append({
                    "type": "need-resource",
                    "my_need": need['skill'],
                    "their_resource": res['name'],
                    "resource_type": res.get('type'),
                    "score": round(match_score, 2)
                })
    
    # 业务匹配 (权重15%)
    my_looking = my_profile.get('business', {}).get('looking_for', [])
    their_offer = other_profile.get('business', {}).get('can_offer', [])
    for looking in my_looking:
        for offer in their_offer:
            if keyword_match(looking, offer):
                score += 0.15
                matches.append({
                    "type": "business",
                    "looking_for": looking,
                    "can_offer": offer,
                    "score": 0.15
                })
    
    # 同城加分 (权重10%)
    my_location = my_profile.get('profile', {}).get('location', '')
    their_location = other_profile.get('profile', {}).get('location', '')
    if my_location and their_location and my_location == their_location:
        score += 0.1
        matches.append({
            "type": "location",
            "location": my_location,
            "score": 0.1
        })
    
    # 归一化分数
    final_score = min(score, 1.0)
    
    return {
        "score": round(final_score, 2),
        "percentage": f"{final_score * 100:.0f}%",
        "threshold_met": final_score >= threshold,
        "matches": matches
    }

def cmd_match(args):
    """匹配档案"""
    my_profile = load_profile()
    
    # 加载对方档案
    other_path = Path(args.profile)
    if not other_path.exists():
        return {"status": "error", "message": f"档案不存在: {args.profile}"}
    
    with open(other_path, 'r', encoding='utf-8') as f:
        other_profile = json.load(f)
    
    threshold = args.threshold or my_profile.get('preferences', {}).get('match_threshold', 0.7)
    
    # 计算匹配
    result = calculate_match_score(my_profile, other_profile, threshold)
    
    # 反向匹配
    reverse_result = calculate_match_score(other_profile, my_profile, threshold)
    
    # 生成建议
    suggestions = []
    if result['matches']:
        for m in result['matches']:
            if m['type'] == 'need-capability':
                suggestions.append(f"💡 对方可以满足你的需求: {m['my_need']}")
            elif m['type'] == 'need-resource':
                suggestions.append(f"💡 对方有资源: {m['their_resource']}")
    if reverse_result['matches']:
        for m in reverse_result['matches']:
            if m['type'] == 'need-capability':
                suggestions.append(f"💡 你可以帮助对方: {m['my_need']}")
    
    return {
        "status": "success",
        "match": {
            "my_profile": my_profile['profile'].get('name', 'Unknown'),
            "other_profile": other_profile.get('profile', {}).get('name', 'Unknown'),
            "score": result['percentage'],
            "threshold_met": result['threshold_met'],
            "details": result['matches']
        },
        "reverse_match": {
            "score": reverse_result['percentage'],
            "details": reverse_result['matches']
        },
        "suggestions": suggestions
    }

def cmd_match_local(args):
    """本地档案匹配（扫描缓存目录）"""
    my_profile = load_profile()
    threshold = args.threshold or my_profile.get('preferences', {}).get('match_threshold', 0.7)
    
    # 扫描缓存目录中的档案
    matches = []
    for cache_file in CACHE_DIR.glob("*.json"):
        if cache_file.name.startswith("profile_"):
            with open(cache_file, 'r', encoding='utf-8') as f:
                other_profile = json.load(f)
            
            result = calculate_match_score(my_profile, other_profile, threshold)
            if result['threshold_met']:
                matches.append({
                    "profile_name": other_profile.get('profile', {}).get('name', 'Unknown'),
                    "profile_path": str(cache_file),
                    "score": result['percentage'],
                    "matches": result['matches']
                })
    
    # 按分数排序
    matches.sort(key=lambda x: float(x['score'].rstrip('%')), reverse=True)
    
    return {
        "status": "success",
        "threshold": threshold,
        "matches_found": len(matches),
        "matches": matches[:args.limit] if args.limit else matches
    }

# ============ 导入导出 ============

def cmd_export(args):
    """导出档案"""
    profile = load_profile()
    
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = A2A_DIR / f"profile_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)
    
    return {
        "status": "success",
        "message": f"✅ 档案已导出",
        "path": str(output_path)
    }

def cmd_import(args):
    """导入档案"""
    import_path = Path(args.profile)
    if not import_path.exists():
        return {"status": "error", "message": f"档案不存在: {args.profile}"}
    
    with open(import_path, 'r', encoding='utf-8') as f:
        imported = json.load(f)
    
    if args.merge:
        profile = load_profile()
        # 合并能力、资源、需求
        if args.merge_capabilities:
            profile['capabilities'].extend(imported.get('capabilities', []))
        if args.merge_resources:
            profile['resources'].extend(imported.get('resources', []))
        if args.merge_needs:
            profile['needs'].extend(imported.get('needs', []))
        save_profile(profile)
        # 同时保存到缓存
        cache_path = CACHE_DIR / f"profile_{imported.get('profile', {}).get('id', generate_id('imported'))}.json"
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(imported, f, ensure_ascii=False, indent=2)
    else:
        save_profile(imported)
    
    return {
        "status": "success",
        "message": f"✅ 档案已导入",
        "merge": args.merge,
        "cached": args.merge
    }

# ============ 同步功能 ============

def cmd_sync(args):
    """同步到云端"""
    profile = load_profile()
    
    # TODO: 实现云端同步
    # 当前仅保存同步记录
    sync_record = {
        "id": generate_id('sync'),
        "profile_id": profile['profile']['id'],
        "sync_at": datetime.now().isoformat(),
        "status": "pending",
        "note": "云端服务待开发"
    }
    
    sync_path = CACHE_DIR / f"sync_{sync_record['id']}.json"
    with open(sync_path, 'w', encoding='utf-8') as f:
        json.dump(sync_record, f, ensure_ascii=False, indent=2)
    
    return {
        "status": "pending",
        "message": "⚠️ 云端服务待开发，当前仅保存本地同步记录",
        "sync_record": sync_record
    }

def cmd_notifications(args):
    """查看匹配通知"""
    if not NOTIFICATIONS_PATH.exists():
        return {
            "status": "success",
            "notifications": [],
            "message": "暂无通知"
        }
    
    with open(NOTIFICATIONS_PATH, 'r', encoding='utf-8') as f:
        notifications = json.load(f)
    
    return {
        "status": "success",
        "notifications": notifications
    }

# ============ 主入口 ============

def create_parser():
    """创建命令行解析器"""
    parser = argparse.ArgumentParser(
        description='A2A Match - Agent-to-Agent 匹配平台',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    # init 命令
    init_parser = subparsers.add_parser('init', help='初始化档案')
    init_parser.add_argument('--force', action='store_true', help='强制重新创建')
    init_parser.set_defaults(func=cmd_init)
    
    # profile 命令
    profile_parser = subparsers.add_parser('profile', help='查看档案')
    profile_parser.add_argument('--full', action='store_true', help='显示完整档案')
    profile_parser.set_defaults(func=cmd_profile)
    
    # update 命令
    update_parser = subparsers.add_parser('update', help='更新档案')
    update_parser.add_argument('field', help='字段名（支持嵌套如 profile.name）')
    update_parser.add_argument('value', help='字段值')
    update_parser.set_defaults(func=cmd_update)
    
    # capability 命令
    cap_parser = subparsers.add_parser('capability', help='能力管理')
    cap_sub = cap_parser.add_subparsers(dest='subcommand')
    
    cap_add = cap_sub.add_parser('add', help='添加能力')
    cap_add.add_argument('skill', help='技能名称')
    cap_add.add_argument('--level', default='intermediate', 
                         choices=['beginner', 'intermediate', 'advanced', 'expert'],
                         help='技能等级')
    cap_add.add_argument('--years', type=int, default=0, help='经验年限')
    cap_add.add_argument('--description', help='技能描述')
    cap_add.add_argument('--tags', help='标签（逗号分隔）')
    cap_add.add_argument('--portfolio', help='作品集链接')
    cap_add.add_argument('--shareable', action='store_true', default=True, help='是否可分享')
    cap_add.set_defaults(func=cmd_capability_add)
    
    cap_list = cap_sub.add_parser('list', help='列出能力')
    cap_list.add_argument('--format', default='json', choices=['json', 'table'])
    cap_list.set_defaults(func=cmd_capability_list)
    
    cap_remove = cap_sub.add_parser('remove', help='删除能力')
    cap_remove.add_argument('id', help='能力ID')
    cap_remove.set_defaults(func=cmd_capability_remove)
    
    # need 命令
    need_parser = subparsers.add_parser('need', help='需求管理')
    need_sub = need_parser.add_subparsers(dest='subcommand')
    
    need_add = need_sub.add_parser('add', help='添加需求')
    need_add.add_argument('skill', help='需求技能')
    need_add.add_argument('--type', default='capability', 
                          choices=['capability', 'resource', 'service', 'collaboration'],
                          help='需求类型')
    need_add.add_argument('--priority', default='medium',
                          choices=['low', 'medium', 'high', 'urgent'],
                          help='优先级')
    need_add.add_argument('--description', help='需求描述')
    need_add.add_argument('--budget', help='预算')
    need_add.add_argument('--deadline', help='截止日期')
    need_add.add_argument('--specs', help='规格（JSON格式）')
    need_add.set_defaults(func=cmd_need_add)
    
    need_list = need_sub.add_parser('list', help='列出需求')
    need_list.add_argument('--status', help='过滤状态')
    need_list.add_argument('--priority', help='过滤优先级')
    need_list.set_defaults(func=cmd_need_list)
    
    need_remove = need_sub.add_parser('remove', help='删除需求')
    need_remove.add_argument('id', help='需求ID')
    need_remove.set_defaults(func=cmd_need_remove)
    
    need_broadcast = need_sub.add_parser('broadcast', help='广播需求')
    need_broadcast.add_argument('--id', help='需求ID')
    need_broadcast.add_argument('--message', help='广播消息')
    need_broadcast.add_argument('--duration', default='7d', help='广播时长')
    need_broadcast.set_defaults(func=cmd_need_broadcast)
    
    # resource 命令
    res_parser = subparsers.add_parser('resource', help='资源管理')
    res_sub = res_parser.add_subparsers(dest='subcommand')
    
    res_add = res_sub.add_parser('add', help='添加资源')
    res_add.add_argument('type', help='资源类型')
    res_add.add_argument('name', help='资源名称')
    res_add.add_argument('--specs', help='规格（JSON格式）')
    res_add.add_argument('--availability', default='available', help='可用性')
    res_add.add_argument('--shareable', action='store_true', default=True, help='是否可分享')
    res_add.add_argument('--price', default='可协商', help='价格/交换条件')
    res_add.set_defaults(func=cmd_resource_add)
    
    res_list = res_sub.add_parser('list', help='列出资源')
    res_list.add_argument('--type', help='过滤类型')
    res_list.set_defaults(func=cmd_resource_list)
    
    res_remove = res_sub.add_parser('remove', help='删除资源')
    res_remove.add_argument('id', help='资源ID')
    res_remove.set_defaults(func=cmd_resource_remove)
    
    # match 命令
    match_parser = subparsers.add_parser('match', help='匹配分析')
    match_parser.add_argument('profile', nargs='?', help='对方档案路径')
    match_parser.add_argument('--threshold', type=float, help='匹配阈值')
    match_parser.add_argument('--local', action='store_true', help='扫描本地缓存')
    match_parser.add_argument('--limit', type=int, default=10, help='返回数量')
    match_parser.set_defaults(func=cmd_match)
    
    # export 命令
    export_parser = subparsers.add_parser('export', help='导出档案')
    export_parser.add_argument('--output', help='输出路径')
    export_parser.set_defaults(func=cmd_export)
    
    # import 命令
    import_parser = subparsers.add_parser('import', help='导入档案')
    import_parser.add_argument('profile', help='档案路径')
    import_parser.add_argument('--merge', action='store_true', default=True, help='合并模式')
    import_parser.add_argument('--merge-capabilities', action='store_true', default=True)
    import_parser.add_argument('--merge-resources', action='store_true', default=True)
    import_parser.add_argument('--merge-needs', action='store_true', default=True)
    import_parser.set_defaults(func=cmd_import)
    
    # sync 命令
    sync_parser = subparsers.add_parser('sync', help='同步到云端')
    sync_parser.set_defaults(func=cmd_sync)
    
    # notifications 命令
    notif_parser = subparsers.add_parser('notifications', help='查看通知')
    notif_parser.set_defaults(func=cmd_notifications)
    
    # card 命令 - 生成 Agent 卡片
    card_parser = subparsers.add_parser('card', help='生成Agent卡片')
    card_parser.add_argument('--dashboard', action='store_true', help='显示仪表盘')
    card_parser.set_defaults(func=cmd_card)
    
    # dashboard 命令
    dash_parser = subparsers.add_parser('dashboard', help='显示仪表盘')
    dash_parser.set_defaults(func=cmd_dashboard)
    
    # recognize 命令 - 智能识别对话中的需求/能力/资源
    rec_parser = subparsers.add_parser('recognize', help='识别对话中的需求/能力/资源')
    rec_parser.add_argument('text', help='对话文本')
    rec_parser.set_defaults(func=cmd_recognize)
    
    # wizard 命令 - 引导创建档案
    wizard_parser = subparsers.add_parser('wizard', help='引导创建档案')
    wizard_parser.set_defaults(func=cmd_wizard)
    
    return parser

def cmd_card(args):
    """生成 Agent 卡片"""
    profile = load_profile()
    
    # 导入卡片生成函数
    from card_generator import generate_card
    
    card = generate_card(profile)
    
    return {
        "status": "success",
        "card": card,
        "format": "ascii"
    }

def cmd_dashboard(args):
    """显示仪表盘"""
    profile = load_profile()
    
    from card_generator import generate_dashboard
    
    dashboard = generate_dashboard(profile)
    
    return {
        "status": "success",
        "dashboard": dashboard,
        "format": "ascii"
    }

def cmd_recognize(args):
    """智能识别对话中的需求/能力/资源"""
    if not HAS_RECOGNIZER:
        return {
            "status": "error",
            "message": "智能识别模块未安装"
        }
    
    recognizer = IntentRecognizer()
    result = recognizer.analyze_conversation(args.text)
    
    # 生成提示
    prompts = []
    if result['needs']:
        prompts.append({
            "type": "need",
            "prompt": generate_need_prompt([
                type('Item', (), n) for n in result['needs']
            ])
        })
    
    if result['capabilities']:
        prompts.append({
            "type": "capability",
            "prompt": generate_capability_prompt([
                type('Item', (), c) for c in result['capabilities']
            ])
        })
    
    if result['resources']:
        prompts.append({
            "type": "resource",
            "prompt": generate_resource_prompt([
                type('Item', (), r) for r in result['resources']
            ])
        })
    
    return {
        "status": "success",
        "recognized": result,
        "prompts": prompts,
        "has_signals": result['has_signals']
    }

def cmd_wizard(args):
    """引导创建档案"""
    # 运行引导脚本
    import subprocess
    
    wizard_path = Path(__file__).parent / 'setup_wizard.py'
    
    if wizard_path.exists():
        return {
            "status": "info",
            "message": "请运行: python scripts/setup_wizard.py"
        }
    else:
        return {
            "status": "error",
            "message": "引导脚本不存在"
        }

def main():
    """命令行入口"""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # 执行对应的命令函数
    if hasattr(args, 'func'):
        result = args.func(args)
    else:
        result = {"status": "error", "message": f"未知命令: {args.command}"}
    
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()

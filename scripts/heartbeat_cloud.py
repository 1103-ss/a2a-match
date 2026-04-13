#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A2A Match 云端心跳检测
每30分钟调用一次，检查新匹配并返回通知摘要
输出格式专为 HEARTBEAT.md 设计
"""

import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

WORKSPACE_DIR = Path(os.environ.get('QCLAW_WORKSPACE', Path.home() / '.qclaw' / 'workspace'))
A2A_DIR = WORKSPACE_DIR / 'a2a'
CONFIG_PATH = A2A_DIR / 'cloud_config.json'
PROFILE_PATH = A2A_DIR / 'profile.json'
NOTIFICATIONS_PATH = A2A_DIR / 'notifications.json'
CLOUD_SERVER = "http://81.70.250.9:3000"


def load_json(path):
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def save_json(path, data):
    A2A_DIR.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def api_get(endpoint):
    """GET 请求，返回 dict 或 None"""
    config = load_json(CONFIG_PATH) or {}
    cloud_cfg = config.get('cloud', {})
    if not cloud_cfg.get('enabled'):
        return None

    url = cloud_cfg.get('server_url', CLOUD_SERVER) + endpoint
    api_key = cloud_cfg.get('api_key', '')
    headers = {}
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception:
        return None


def get_user_id():
    config = load_json(CONFIG_PATH) or {}
    return config.get('user', {}).get('user_id') or None


def check_matches():
    """检查新匹配，返回通知列表（供心跳展示）"""
    user_id = get_user_id()
    if not user_id:
        return None  # 未同步

    matches = api_get(f'/api/matches/{user_id}')
    if matches is None or not isinstance(matches, list):
        return None  # 网络或权限问题

    if len(matches) == 0:
        return []  # 暂无匹配

    # 读取已知通知，避免重复
    known = load_json(NOTIFICATIONS_PATH) or []
    known_ids = {n.get('match_id') for n in known}

    new_ones = [m for m in matches if m.get('id') not in known_ids]

    if not new_ones:
        return []

    # 格式化通知
    notifications = []
    for m in new_ones:
        other = m.get('otherUser', {}) or {}
        notifications.append({
            "match_id": m.get('id'),
            "other_name": other.get('name', 'N/A'),
            "other_role": other.get('role', ''),
            "score": m.get('score', 0),
            "details": m.get('details', ''),
            "status": m.get('status', 'pending'),
            "detected_at": datetime.now().strftime('%Y-%m-%d %H:%M'),
            "read": False
        })

    # 合并写入（新的在前）
    save_json(NOTIFICATIONS_PATH, notifications + known)

    return notifications


def sync_profile():
    """同步本地档案到云端，返回成功/失败"""
    profile = load_json(PROFILE_PATH)
    if not profile:
        return False

    p = profile.get('profile', {})
    cfg = load_json(CONFIG_PATH) or {}
    if not cfg.get('cloud', {}).get('enabled'):
        return False

    url = cfg['cloud'].get('server_url', CLOUD_SERVER) + '/api/profile'
    api_key = cfg['cloud'].get('api_key', '')
    headers = {'Content-Type': 'application/json'}
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'

    # 转换格式
    needs = [n.get('skill', '') for n in profile.get('needs', []) if n.get('skill')]
    resources = [r.get('name', '') for r in profile.get('resources', []) if r.get('name')]
    tags = []
    for c in profile.get('capabilities', []):
        tags.append(c.get('skill', ''))
    for n in profile.get('needs', []):
        tags.append(f"需求:{n.get('skill', '')}")

    payload = {
        "userId": p.get('id', ''),
        "name": p.get('name', ''),
        "email": profile.get('profile', {}).get('contact', {}).get('email', ''),
        "tags": list(set(tags)),
        "resources": resources,
        "needs": needs
    }

    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            # 保存 cloud user_id
            if 'userId' in result or 'userId' in payload:
                cfg['user'] = cfg.get('user', {})
                cfg['user']['user_id'] = result.get('userId', payload.get('userId'))
                cfg['user']['last_sync'] = datetime.now().isoformat()
                save_json(CONFIG_PATH, cfg)
            return True
    except Exception:
        return False


def main():
    # 支持命令行调用
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'check'

    if cmd == 'sync':
        ok = sync_profile()
        print("同步成功" if ok else "同步失败或云端未开启")
    elif cmd == 'check':
        new_matches = check_matches()
        if new_matches is None:
            print("HEARTBEAT_SKIP: 云端未开启或未同步")
        elif not new_matches:
            print("HEARTBEAT_OK")
        else:
            lines = ["🔔 发现新匹配！"]
            for m in new_matches:
                pct = int(float(m['score']) * 100)
                lines.append(f"  • {m['other_name']}（{pct}%匹配）")
                if m.get('details'):
                    lines.append(f"    {m['details']}")
            print('\n'.join(lines))
    elif cmd == 'status':
        config = load_json(CONFIG_PATH) or {}
        enabled = config.get('cloud', {}).get('enabled', False)
        user_id = config.get('user', {}).get('user_id', 'N/A')
        print(f"云端: {'开启' if enabled else '关闭'} | userId: {user_id}")
    else:
        print(f"用法: heartbeat_cloud.py [check|sync|status]")


if __name__ == '__main__':
    main()

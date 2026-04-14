#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A2A Match 云端心跳检测（双通道版）
- 实时通道：读取 realtime_events.json（WebSocket 守护进程写入）→ 毫秒级通知
- 轮询通道：每30分钟 HTTP 检查一次（兜底）

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
EVENTS_PATH = A2A_DIR / 'realtime_events.json'
CLOUD_SERVER = "http://81.70.250.9:3000"


def load_json(path):
    if path.exists():
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: pass
    return None


def save_json(path, data):
    A2A_DIR.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_config():
    return load_json(CONFIG_PATH) or {}


def is_cloud_enabled():
    cfg = load_config()
    return cfg.get('cloud', {}).get('enabled', False)


def get_user_id():
    cfg = load_config()
    uid = cfg.get('user', {}).get('user_id')
    return uid if uid else None


# ===================== 实时通道（WebSocket 守护进程写入）=====================

def fetch_realtime_events():
    """
    读取 realtime_events.json，取出所有事件后清空。
    这是心跳的"实时通道"——来自 WebSocket 守护进程写入。
    """
    events = load_json(EVENTS_PATH) or []
    if events:
        save_json(EVENTS_PATH, [])  # 取走后清空，避免重复通知
    return events


def format_realtime_events(events):
    """将实时事件格式化为心跳通知文本"""
    if not events:
        return None

    lines = []
    has_new = False

    for ev in events:
        etype = ev.get('type', '')
        data = ev.get('data', {})
        ts = ev.get('ts', '')[:16]  # 取时分秒

        if etype == 'new_message':
            has_new = True
            content = data.get('content', '')
            from_uid = data.get('fromUserId', '?')
            lines.append(f'💬 新消息 [{ts}]: {content[:60]}')
            lines.append(f'   来自: {from_uid}')

        elif etype == 'new_matches':
            has_new = True
            matches = data.get('matches', [])
            for m in matches:
                name = (m.get('otherUser') or {}).get('name', '?')
                score = int(float(m.get('score', 0)) * 100)
                lines.append(f'🔔 新匹配 [{ts}]: {name}（{score}%匹配）')

        elif etype == 'match_accepted':
            has_new = True
            mid = data.get('matchId', '')
            lines.append(f'✅ 匹配被接受了！[{ts}] matchId={mid}')

    if not has_new:
        return None

    return '\n'.join(lines)


# ===================== 轮询通道（HTTP，兜底）=====================

def api_get(endpoint):
    """GET 请求"""
    cfg = load_config()
    url = cfg.get('cloud', {}).get('server_url', CLOUD_SERVER) + endpoint
    api_key = cfg.get('cloud', {}).get('api_key', '')
    headers = {}
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception:
        return None


def check_http_matches():
    """HTTP 轮询检查新匹配（兜底通道）"""
    user_id = get_user_id()
    if not user_id:
        return None  # 未同步

    matches = api_get(f'/api/matches/{user_id}')
    if matches is None or not isinstance(matches, list):
        return None

    if not matches:
        return []

    known = load_json(NOTIFICATIONS_PATH) or []
    known_ids = {n.get('match_id') for n in known}
    new_ones = [m for m in matches if m.get('id') not in known_ids]

    if not new_ones:
        return []

    notifications = []
    for m in new_ones:
        other = m.get('otherUser') or {}
        notifications.append({
            "match_id": m.get('id'),
            "other_name": other.get('name', 'N/A'),
            "score": m.get('score', 0),
            "details": m.get('details', ''),
            "status": m.get('status', 'pending'),
            "detected_at": datetime.now().strftime('%H:%M'),
            "read": False,
            "source": "http_polling"
        })

    save_json(NOTIFICATIONS_PATH, notifications + known)
    return notifications


def sync_profile():
    """同步本地档案到云端"""
    profile = load_json(PROFILE_PATH)
    if not profile:
        return False

    p = profile.get('profile', {})
    cfg = load_config()
    if not cfg.get('cloud', {}).get('enabled'):
        return False

    url = cfg['cloud'].get('server_url', CLOUD_SERVER) + '/api/profile'
    api_key = cfg['cloud'].get('api_key', '')
    headers = {'Content-Type': 'application/json'}
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'

    needs = [n.get('skill', '') for n in profile.get('needs', []) if n.get('skill')]
    resources = [r.get('name', '') for r in profile.get('resources', []) if r.get('name')]
    tags = [c.get('skill', '') for c in profile.get('capabilities', []) if c.get('skill')]
    for n in profile.get('needs', []):
        tags.append(f"需求:{n.get('skill', '')}")

    payload = {
        "userId": p.get('id', ''),
        "name": p.get('name', ''),
        "email": profile.get('profile', {}).get('contact', {}).get('email', ''),
        "tags": list(set([t for t in tags if t])),
        "resources": resources,
        "needs": needs
    }

    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            if 'userId' in result or 'userId' in payload:
                cfg['user'] = cfg.get('user', {})
                cfg['user']['user_id'] = result.get('userId', payload.get('userId'))
                cfg['user']['last_sync'] = datetime.now().isoformat()
                save_json(CONFIG_PATH, cfg)
            return True
    except Exception:
        return False


# ===================== 主入口 =====================

def check():
    """
    心跳检查入口（双通道合并）：
    1. 实时通道：realtime_events.json → 立即返回（毫秒级）
    2. 轮询通道：无实时事件时走 HTTP 兜底
    """
    if not is_cloud_enabled():
        return "HEARTBEAT_SKIP: 云端未开启"

    # 通道1：实时事件（WebSocket）
    rt_events = fetch_realtime_events()
    rt_text = format_realtime_events(rt_events)
    if rt_text:
        # 有实时事件，立即返回，不等 HTTP
        return rt_text

    # 通道2：HTTP 轮询（兜底）
    new_matches = check_http_matches()
    if new_matches is None:
        return "HEARTBEAT_SKIP: 未同步或网络异常"
    if not new_matches:
        return "HEARTBEAT_OK"

    lines = ["🔔 发现新匹配（HTTP兜底通道）"]
    for m in new_matches:
        pct = int(float(m['score']) * 100)
        lines.append(f"  • {m['other_name']}（{pct}%匹配）")
        if m.get('details'):
            lines.append(f"    {m['details']}")
    return '\n'.join(lines)


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'check'

    if cmd == 'check':
        result = check()
        print(result)
    elif cmd == 'sync':
        ok = sync_profile()
        print("同步成功" if ok else "同步失败或云端未开启")
    elif cmd == 'status':
        cfg = load_config()
        enabled = cfg.get('cloud', {}).get('enabled', False)
        user_id = cfg.get('user', {}).get('user_id', 'N/A')
        daemon_running = EVENTS_PATH.exists()
        print(f"云端: {'开启' if enabled else '关闭'} | userId: {user_id[:16]}... | WS守护进程: {'已启动' if daemon_running else '未启动'}")
    elif cmd == 'events':
        evs = load_json(EVENTS_PATH) or []
        print(f"积压事件: {len(evs)} 条")
        for e in evs:
            print(f"  [{e.get('type')}] {e.get('data', {})}")
    else:
        print(f"用法: heartbeat_cloud.py [check|sync|status|events]")


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A2A Match 云端心跳检测（三通道版）
- 实时通道：realtime_events.json（WebSocket 守护进程写入）
- 消息通道：HTTP 轮询未读消息（新加！）
- 匹配通道：HTTP 轮询新匹配

输出格式专为 HEARTBEAT.md 设计
"""

import json, os, sys, urllib.request
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
LOG_PATH = A2A_DIR / 'ws_daemon.log'
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
    return (load_json(CONFIG_PATH) or {}).get('cloud', {}).get('enabled', False)


def get_user_id():
    return (load_json(CONFIG_PATH) or {}).get('user', {}).get('user_id')


def api_get(endpoint):
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


# ===================== 实时通道 =====================

def fetch_realtime_events():
    events = load_json(EVENTS_PATH) or []
    if events:
        save_json(EVENTS_PATH, [])
    return events


def format_realtime_events(events):
    if not events:
        return None
    lines = []
    has_new = False
    for ev in events:
        etype = ev.get('type', '')
        data = ev.get('data', {})
        ts = ev.get('ts', '')[:16]
        if etype == 'new_message':
            has_new = True
            content = data.get('content', '')
            from_name = data.get('fromName', data.get('fromUserId', '?'))
            lines.append(f'💬 新消息 [{ts}] 来自【{from_name}】：{content[:80]}')
        elif etype == 'new_matches':
            has_new = True
            for m in data.get('matches', []):
                name = (m.get('otherUser') or {}).get('name', '?')
                score = int(float(m.get('score', 0)) * 100)
                lines.append(f'🔔 新匹配：{name}（{score}%匹配）')
        elif etype == 'match_accepted':
            has_new = True
            mid = data.get('matchId', '')
            lines.append(f'✅ 匹配被接受了！matchId={mid[:16]}...')
    if has_new:
        return '\n'.join(lines)
    return None


# ===================== 消息通道（HTTP 轮询）=====================

def check_http_messages():
    """
    HTTP 轮询未读消息。
    返回新消息列表（每个消息包含 matchId, fromUserId, fromName, content, msgId）
    """
    user_id = get_user_id()
    if not user_id:
        return []

    msgs = api_get(f'/api/messages/{user_id}?unread=true')
    if msgs is None:
        return []
    if isinstance(msgs, dict):
        msgs = msgs.get('messages', msgs.get('data', []))
    if not isinstance(msgs, list):
        return []

    # 加载已知消息ID，避免重复推送
    known = load_json(NOTIFICATIONS_PATH) or []
    known_msg_ids = {n.get('msg_id') for n in known if n.get('type') == 'message'}
    new_msgs = [m for m in msgs if m.get('messageId', m.get('id', '')) not in known_msg_ids]

    # 标记已读（告诉服务器这些消息已读）
    for m in new_msgs:
        msg_id = m.get('messageId', m.get('id', ''))
        if msg_id:
            try:
                api_get(f'/api/message/{msg_id}/read?userId={user_id}')
            except Exception:
                pass

    if not new_msgs:
        return []

    # 追加到 notifications.json
    new_notifs = []
    for m in new_msgs:
        msg_id = m.get('messageId', m.get('id', ''))
        new_notifs.append({
            'type': 'message',
            'msg_id': msg_id,
            'match_id': m.get('matchId', ''),
            'from_uid': m.get('fromUserId', ''),
            'from_name': m.get('fromNickname', m.get('fromName', '对方')),
            'content': m.get('content', ''),
            'detected_at': datetime.now().strftime('%H:%M'),
            'read': False
        })

    # 保留最近 50 条
    combined = new_notifs + known
    save_json(NOTIFICATIONS_PATH, combined[:50])
    return new_notifs


# ===================== 匹配通道（HTTP 轮询）=====================

def check_http_matches():
    user_id = get_user_id()
    if not user_id:
        return []

    matches = api_get(f'/api/matches/{user_id}')
    if matches is None or not isinstance(matches, list):
        return []

    known = [n for n in (load_json(NOTIFICATIONS_PATH) or []) if n.get('type') == 'match']
    known_ids = {n.get('match_id') for n in known}
    new_ones = [m for m in matches if m.get('id') not in known_ids]

    if not new_ones:
        return []

    new_notifs = []
    for m in new_ones:
        other = m.get('otherUser') or {}
        pct = int(float(m.get('score', 0)) * 100)
        new_notifs.append({
            'type': 'match',
            'match_id': m.get('id'),
            'other_name': other.get('name', 'N/A'),
            'score': pct,
            'status': m.get('status', 'pending'),
            'detected_at': datetime.now().strftime('%H:%M'),
            'read': False
        })

    combined = new_notifs + known
    save_json(NOTIFICATIONS_PATH, combined[:50])
    return new_notifs


# ===================== 主入口 =====================

def check():
    """
    心跳三通道检查：
    1. 实时事件（WS）→ 立即返回
    2. 未读消息（HTTP）→ 返回最新一条消息
    3. 新匹配（HTTP）→ 返回新匹配列表
    """
    if not is_cloud_enabled():
        return "HEARTBEAT_SKIP: 云端未开启"

    # 通道1：实时事件
    rt_text = format_realtime_events(fetch_realtime_events())
    if rt_text:
        return rt_text

    # 通道2：消息检查
    new_msgs = check_http_messages()
    if new_msgs:
        # 只展示最新一条消息，避免刷屏
        latest = new_msgs[0]
        lines = [f"💬 收到一条来自【{latest['from_name']}】的消息："]
        lines.append("")
        lines.append(f"  「{latest['content'][:100]}」")
        lines.append("")
        lines.append("  📝 直接打字回复，我帮你发送")
        lines.append(f"  💡 或者说「查看全部消息」看更多")
        return '\n'.join(lines)

    # 通道3：匹配检查
    new_matches = check_http_matches()
    if not new_matches:
        return "HEARTBEAT_OK"

    lines = [f"🔔 发现 {len(new_matches)} 个新匹配！"]
    for m in new_matches:
        lines.append(f"  • {m['other_name']}（{m['score']}%匹配）")
    return '\n'.join(lines)


def sync_profile():
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


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'check'
    if cmd == 'check':
        print(check())
    elif cmd == 'sync':
        print("同步成功" if sync_profile() else "同步失败或云端未开启")
    elif cmd == 'status':
        cfg = load_config()
        enabled = cfg.get('cloud', {}).get('enabled', False)
        user_id = cfg.get('user', {}).get('user_id', 'N/A')
        uid_short = user_id[:16] + '...' if user_id and len(user_id) > 16 else (user_id or 'N/A')
        import time as _time
        daemon_running = False
        if LOG_PATH.exists():
            try:
                import os as _os
                daemon_running = (_time.time() - _os.path.getmtime(LOG_PATH)) < 120
            except: pass
        print(f"云端: {'开启' if enabled else '关闭'} | userId: {uid_short} | WS守护进程: {'已启动' if daemon_running else '未启动'}")
    elif cmd == 'events':
        evs = load_json(EVENTS_PATH) or []
        print(f"积压事件: {len(evs)} 条")
        for e in evs:
            print(f"  [{e.get('type')}] {e.get('data', {})}")
    elif cmd == 'messages':
        uid = get_user_id()
        if not uid:
            print("未找到 userId")
            return
        msgs = api_get(f'/api/messages/{uid}?unread=true') or []
        if isinstance(msgs, dict):
            msgs = msgs.get('messages', msgs.get('data', []))
        print(f"未读消息: {len(msgs)} 条")
        for m in msgs:
            print(f"  [{m.get('fromNickname','?')}] {m.get('content','')[:60]}")
    elif cmd == 'clear':
        save_json(NOTIFICATIONS_PATH, [])
        print("已清空通知记录")
    else:
        print(f"用法: heartbeat_cloud.py [check|sync|status|events|messages|clear]")


if __name__ == '__main__':
    main()

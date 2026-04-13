#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A2A Match 云端心跳检测
定时检查新匹配并通知用户
"""

import json
import os
import sys
import urllib.request
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

def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"cloud": {"enabled": True, "server_url": CLOUD_SERVER}}

def save_notifications(notifications):
    A2A_DIR.mkdir(parents=True, exist_ok=True)
    with open(NOTIFICATIONS_PATH, 'w', encoding='utf-8') as f:
        json.dump(notifications, f, ensure_ascii=False, indent=2)

def cloud_api(endpoint, data=None, method='GET'):
    config = load_config()
    url = config['cloud']['server_url'] + endpoint
    try:
        if method == 'GET':
            req = urllib.request.Request(url)
        else:
            json_data = json.dumps(data or {}).encode('utf-8')
            req = urllib.request.Request(url, data=json_data, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except:
        return None

def check_new_matches():
    """检查新匹配并通知"""
    config = load_config()
    user_id = config.get('user', {}).get('user_id')
    
    if not user_id:
        return {"status": "no_user", "message": "未同步到云端"}
    
    # 获取匹配
    matches = cloud_api(f'/api/matches/{user_id}')
    if not matches:
        return {"status": "no_matches", "message": "暂无新匹配"}
    
    # 加载已知通知
    known = []
    if NOTIFICATIONS_PATH.exists():
        with open(NOTIFICATIONS_PATH, 'r', encoding='utf-8') as f:
            known = json.load(f)
    
    known_ids = {n.get('match_id') for n in known}
    
    # 新匹配
    new_matches = [m for m in matches if m.get('id') not in known_ids]
    
    if not new_matches:
        return {"status": "no_new", "matches_count": len(matches)}
    
    # 添加新通知
    notifications = []
    for m in new_matches:
        notifications.append({
            "match_id": m.get('id'),
            "matched_user": m.get('matchedUser', {}).get('nickname', 'N/A'),
            "match_type": m.get('type'),
            "score": m.get('score'),
            "at": datetime.now().isoformat(),
            "read": False
        })
    
    save_notifications(notifications + known)
    
    return {
        "status": "new_matches",
        "count": len(new_matches),
        "matches": notifications
    }

def sync_profile():
    """同步档案到云端"""
    if not PROFILE_PATH.exists():
        return {"status": "no_profile"}
    
    with open(PROFILE_PATH, 'r', encoding='utf-8') as f:
        profile = json.load(f)
    
    # 转换格式
    signals = []
    for need in profile.get('needs', []):
        signals.append({"type": "need", "value": need.get('skill', ''), "tags": [need.get('priority', 'medium')]})
    for cap in profile.get('capabilities', []):
        signals.append({"type": "skill", "value": cap.get('skill', ''), "tags": cap.get('tags', [])})
    for res in profile.get('resources', []):
        signals.append({"type": "resource", "value": res.get('name', ''), "tags": [res.get('type', '')]})
    
    cloud_data = {
        "userId": profile['profile'].get('id', ''),
        "nickname": profile['profile'].get('name', ''),
        "signals": signals
    }
    
    result = cloud_api('/api/profile', cloud_data, 'POST')
    
    if result and 'profile' in result:
        config = load_config()
        config['user']['user_id'] = result['profile'].get('userId', '')
        config['user']['last_sync'] = datetime.now().isoformat()
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return {"status": "synced", "matches_found": result.get('matchesFound', 0)}
    
    return {"status": "sync_failed"}

def main():
    if len(sys.argv) < 2:
        print("用法: python heartbeat_cloud.py [sync|check|status]")
        return
    
    cmd = sys.argv[1]
    
    if cmd == 'sync':
        result = sync_profile()
    elif cmd == 'check':
        result = check_new_matches()
    elif cmd == 'status':
        config = load_config()
        result = {
            "server": config['cloud']['server_url'],
            "user_id": config.get('user', {}).get('user_id', 'N/A'),
            "last_sync": config.get('user', {}).get('last_sync', 'N/A'),
            "auto_sync": config['cloud'].get('auto_sync', False)
        }
    else:
        result = {"error": f"未知命令: {cmd}"}
    
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A2A Match 云端同步模块 v2
适配服务器最新格式
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

CLOUD_SERVER = "http://81.70.250.9:3000"

def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"cloud": {"enabled": True, "server_url": CLOUD_SERVER}}

def save_config(config):
    A2A_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def load_profile():
    if PROFILE_PATH.exists():
        with open(PROFILE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def api_call(endpoint, data=None, method='GET'):
    url = CLOUD_SERVER + endpoint
    try:
        if method == 'GET':
            req = urllib.request.Request(url)
        else:
            json_data = json.dumps(data or {}).encode('utf-8')
            req = urllib.request.Request(url, data=json_data, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.read().decode()[:200]}"}
    except Exception as e:
        return {"error": str(e)}

def convert_to_server_format(profile):
    """转换本地档案到服务器期望的格式"""
    needs = []
    resources = []
    tags = []
    
    # 需求 -> needs 数组
    for need in profile.get('needs', []):
        skill = need.get('skill', '')
        if skill:
            needs.append(skill)
            # 添加标签
            priority = need.get('priority', '')
            if priority:
                tags.append(f"need:{priority}")
    
    # 资源 -> resources 数组
    for res in profile.get('resources', []):
        name = res.get('name', '')
        if name:
            resources.append(name)
            res_type = res.get('type', '')
            if res_type:
                tags.append(f"resource:{res_type}")
    
    # 能力 -> 添加到标签
    for cap in profile.get('capabilities', []):
        skill = cap.get('skill', '')
        if skill:
            tags.append(f"skill:{skill}")
        level = cap.get('level', '')
        if level:
            tags.append(f"level:{level}")
    
    # 去重
    tags = list(set(tags))
    
    return {
        "userId": profile['profile'].get('id', ''),
        "name": profile['profile'].get('name', ''),
        "email": profile.get('profile', {}).get('contact', {}).get('email', ''),
        "tags": tags,
        "resources": resources,
        "needs": needs
    }

def sync_to_cloud():
    """同步档案到云端"""
    profile = load_profile()
    if not profile:
        return {"status": "error", "message": "本地档案不存在"}
    
    cloud_data = convert_to_server_format(profile)
    
    result = api_call('/api/profile', cloud_data, 'POST')
    
    if 'error' in result:
        return {"status": "error", "message": result['error']}
    
    # 保存userId到配置
    config = load_config()
    config['user']['user_id'] = cloud_data['userId']
    config['user']['last_sync'] = datetime.now().isoformat()
    save_config(config)
    
    return {
        "status": "success",
        "message": "档案已同步到云端",
        "user_id": cloud_data['userId'][:16] + "...",
        "needs": len(cloud_data['needs']),
        "resources": len(cloud_data['resources']),
        "tags": len(cloud_data['tags'])
    }

def get_status():
    """获取同步状态"""
    config = load_config()
    
    # 测试连接
    profiles = api_call('/api/profiles')
    connected = not isinstance(profiles, dict) and 'error' not in profiles
    
    return {
        "server": CLOUD_SERVER,
        "connected": connected,
        "total_users": len(profiles) if connected else 0,
        "user_id": config.get('user', {}).get('user_id', 'N/A'),
        "last_sync": config.get('user', {}).get('last_sync', 'N/A')
    }

def get_matches():
    """获取匹配列表"""
    config = load_config()
    user_id = config.get('user', {}).get('user_id')
    
    if not user_id:
        return {"status": "error", "message": "尚未同步到云端"}
    
    matches = api_call(f'/api/matches/{user_id}')
    
    if 'error' in matches:
        return {"status": "error", "message": matches['error']}
    
    return {
        "status": "success",
        "matches": matches,
        "count": len(matches)
    }

def main():
    if len(sys.argv) < 2:
        print("A2A Match 云端同步工具")
        print()
        print("用法:")
        print("  status   - 查看云端状态")
        print("  sync     - 同步档案到云端")
        print("  matches  - 查看匹配结果")
        print("  list     - 查看所有用户")
        print("  stats    - 查看系统统计")
        return
    
    cmd = sys.argv[1]
    
    if cmd == 'status':
        result = get_status()
    elif cmd == 'sync':
        result = sync_to_cloud()
    elif cmd == 'matches':
        result = get_matches()
    elif cmd == 'list':
        result = api_call('/api/profiles')
    elif cmd == 'stats':
        result = api_call('/api/stats')
    else:
        result = {"error": f"未知命令: {cmd}"}
    
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()

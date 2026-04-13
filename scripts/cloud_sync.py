#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A2A Match 云端同步模块 v3
v1.8.6: 云端功能默认关闭（需主动启用），支持 API Key 鉴权
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
    """加载云端配置"""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    # 默认配置：云端关闭
    return {
        "cloud": {"enabled": False, "server_url": CLOUD_SERVER, "api_key": ""},
        "user": {"user_id": "", "nickname": "", "last_sync": ""},
        "match": {"auto_match": True, "notify_on_new": True, "threshold": 0.6}
    }

def save_config(config):
    """保存云端配置"""
    A2A_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def is_cloud_enabled():
    """检查云端功能是否启用"""
    config = load_config()
    return config.get('cloud', {}).get('enabled', False)

def load_profile():
    """加载本地档案"""
    if PROFILE_PATH.exists():
        with open(PROFILE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def api_call(endpoint, data=None, method='GET'):
    """调用云端 API"""
    config = load_config()
    server = config['cloud']['server_url']
    api_key = config['cloud'].get('api_key', '')
    url = f"{server}{endpoint}"

    headers = {'Content-Type': 'application/json'}
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'

    try:
        if method == 'GET':
            req = urllib.request.Request(url, headers=headers)
        else:
            json_data = json.dumps(data or {}).encode('utf-8')
            req = urllib.request.Request(url, data=json_data, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:300]
        return {"error": f"HTTP {e.code}: {body}"}
    except Exception as e:
        return {"error": str(e)}

def convert_to_server_format(profile):
    """转换本地档案到服务器期望的格式"""
    needs = []
    resources = []
    tags = []

    for need in profile.get('needs', []):
        skill = need.get('skill', '')
        if skill:
            needs.append(skill)
            priority = need.get('priority', '')
            if priority:
                tags.append(f"need:{priority}")

    for res in profile.get('resources', []):
        name = res.get('name', '')
        if name:
            resources.append(name)
            res_type = res.get('type', '')
            if res_type:
                tags.append(f"resource:{res_type}")

    for cap in profile.get('capabilities', []):
        skill = cap.get('skill', '')
        if skill:
            tags.append(f"skill:{skill}")
        level = cap.get('level', '')
        if level:
            tags.append(f"level:{level}")

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
    if not is_cloud_enabled():
        return {
            "status": "disabled",
            "message": "云端功能未启用。\n\n启用方法：\n1. 编辑 ~/.qclaw/workspace/a2a/cloud_config.json\n2. 将 cloud.enabled 改为 true\n3. 重新运行此命令\n\n⚠️ 启用前请阅读 SKILL.md 中的「隐私与数据说明」。",
            "cloud_config": str(CONFIG_PATH)
        }

    profile = load_profile()
    if not profile:
        return {"status": "error", "message": "本地档案不存在，请先运行 'python scripts/a2a.py init'"}

    cloud_data = convert_to_server_format(profile)
    result = api_call('/api/profile', cloud_data, 'POST')

    if 'error' in result:
        return {"status": "error", "message": result['error']}

    # 保存 userId 到配置
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
    """获取云端状态"""
    config = load_config()
    enabled = config.get('cloud', {}).get('enabled', False)

    if not enabled:
        profiles = []
        connected = False
    else:
        profiles = api_call('/api/profiles')
        connected = not isinstance(profiles, dict) and 'error' not in profiles

    return {
        "cloud_enabled": enabled,
        "server": CLOUD_SERVER,
        "connected": connected,
        "total_users": len(profiles) if isinstance(profiles, list) else 0,
        "user_id": config.get('user', {}).get('user_id', '未同步'),
        "last_sync": config.get('user', {}).get('last_sync', 'N/A'),
        "api_key_configured": bool(config.get('cloud', {}).get('api_key', '')),
        "auto_sync": config.get('cloud', {}).get('auto_sync', False),
        "sync_interval_minutes": config.get('cloud', {}).get('sync_interval_minutes', 30)
    }

def get_matches():
    """获取匹配列表"""
    if not is_cloud_enabled():
        return {"status": "disabled", "message": "云端功能未启用"}

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

def enable_cloud():
    """启用云端功能"""
    config = load_config()
    config['cloud']['enabled'] = True
    save_config(config)
    return {
        "status": "success",
        "message": "云端功能已启用",
        "note": "请阅读 ~/.qclaw/workspace/a2a/cloud_config.json 了解同步的数据范围"
    }

def disable_cloud():
    """禁用云端功能"""
    config = load_config()
    config['cloud']['enabled'] = False
    save_config(config)
    return {
        "status": "success",
        "message": "云端功能已禁用，所有云端同步已停止"
    }

def main():
    if len(sys.argv) < 2:
        print("A2A Match 云端同步工具 v1.8.6")
        print()
        print("用法:")
        print("  status   - 查看云端状态（含开关状态）")
        print("  sync     - 同步档案到云端（需先开启）")
        print("  matches  - 查看匹配结果")
        print("  list     - 查看所有用户")
        print("  stats    - 查看系统统计")
        print("  enable   - 启用云端功能")
        print("  disable  - 禁用云端功能")
        print()
        print("⚠️ 云端功能默认关闭，需先运行 'enable' 开启")
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
    elif cmd == 'enable':
        result = enable_cloud()
    elif cmd == 'disable':
        result = disable_cloud()
    else:
        result = {"error": f"未知命令: {cmd}"}

    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()

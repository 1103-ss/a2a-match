#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A2A Match 云端命令模块 v3
v1.8.6: 云端功能默认关闭（需主动启用），支持 API Key 鉴权
"""

import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

WORKSPACE_DIR = Path(os.environ.get('QCLAW_WORKSPACE', Path.home() / '.qclaw' / 'workspace'))
A2A_DIR = WORKSPACE_DIR / 'a2a'
CONFIG_PATH = A2A_DIR / 'cloud_config.json'
PROFILE_PATH = A2A_DIR / 'profile.json'

CLOUD_SERVER = "http://81.70.250.9:3000"

def load_config() -> Dict:
    """加载云端配置"""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "cloud": {"enabled": False, "server_url": CLOUD_SERVER, "api_key": ""},
        "user": {"user_id": "", "nickname": "", "last_sync": ""},
        "match": {"auto_match": True, "notify_on_new": True, "threshold": 0.6}
    }

def save_config(config: Dict):
    """保存云端配置"""
    A2A_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def is_cloud_enabled() -> bool:
    """检查云端功能是否启用"""
    return load_config().get('cloud', {}).get('enabled', False)

def load_profile() -> Optional[Dict]:
    """加载本地档案"""
    if PROFILE_PATH.exists():
        with open(PROFILE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def cloud_api_call(endpoint: str, data: Optional[Dict] = None, method: str = 'GET') -> Dict:
    """调用云端 API（自动携带 API Key）"""
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
        return {"error": f"HTTP {e.code}: {e.read().decode()[:300]}"}
    except Exception as e:
        return {"error": str(e)}

def convert_to_signals(profile: Dict) -> List[Dict]:
    """转换本地档案到云端信号格式"""
    signals = []

    for need in profile.get('needs', []):
        signals.append({
            "type": "need",
            "value": need.get('skill', ''),
            "tags": [need.get('priority', 'medium'), need.get('type', 'capability')],
            "description": need.get('description', ''),
            "budget": need.get('budget', ''),
            "deadline": need.get('deadline', '')
        })

    for cap in profile.get('capabilities', []):
        signals.append({
            "type": "skill",
            "value": cap.get('skill', ''),
            "tags": cap.get('tags', []) + [cap.get('level', '')],
            "description": cap.get('description', '')
        })

    for res in profile.get('resources', []):
        signals.append({
            "type": "resource",
            "value": res.get('name', ''),
            "tags": [res.get('type', ''), res.get('availability', '')],
            "specs": res.get('specs', {}),
            "price": res.get('price', '')
        })

    return signals

def cmd_cloud_status():
    """查看云端状态"""
    config = load_config()
    profile = load_profile()
    enabled = config.get('cloud', {}).get('enabled', False)

    if not enabled:
        return {
            "status": "ok",
            "cloud_enabled": False,
            "server": CLOUD_SERVER,
            "message": "云端功能已禁用（默认设置）",
            "how_to_enable": "编辑 ~/.qclaw/workspace/a2a/cloud_config.json，将 cloud.enabled 改为 true",
            "local_profile_exists": profile is not None
        }

    result = cloud_api_call('/api/profiles')
    if 'error' in result:
        return {
            "status": "error",
            "message": f"无法连接云端: {result['error']}",
            "server": config['cloud']['server_url']
        }

    profiles = result if isinstance(result, list) else []

    return {
        "status": "success",
        "cloud_enabled": True,
        "server": config['cloud']['server_url'],
        "connected": True,
        "total_users": len(profiles),
        "auto_sync": config['cloud'].get('auto_sync', False),
        "sync_interval": f"{config['cloud'].get('sync_interval_minutes', 30)} 分钟",
        "api_key_configured": bool(config['cloud'].get('api_key', '')),
        "local_profile_exists": profile is not None,
        "cloud_user_id": config.get('user', {}).get('user_id', '未同步')
    }

def cmd_cloud_connect():
    """连接到云端并同步档案"""
    if not is_cloud_enabled():
        return {
            "status": "disabled",
            "message": "云端功能未启用",
            "how_to_enable": "编辑 ~/.qclaw/workspace/a2a/cloud_config.json，将 cloud.enabled 改为 true",
            "config_path": str(CONFIG_PATH)
        }

    config = load_config()
    profile = load_profile()

    if not profile:
        return {
            "status": "error",
            "message": "本地档案不存在，请先运行 'python scripts/a2a.py init'"
        }

    cloud_data = {
        "userId": profile['profile'].get('id', ''),
        "nickname": profile['profile'].get('name', ''),
        "signals": convert_to_signals(profile),
        "contact": profile.get('profile', {}).get('contact', {})
    }

    result = cloud_api_call('/api/profile', cloud_data, 'POST')

    if 'error' in result:
        return {
            "status": "error",
            "message": f"同步失败: {result['error']}"
        }

    if 'profile' in result:
        config['user']['user_id'] = result['profile'].get('userId', '')
        config['user']['nickname'] = result['profile'].get('nickname', '')
        config['user']['last_sync'] = datetime.now().isoformat()
        save_config(config)

    matches_count = result.get('matchesFound', 0)

    return {
        "status": "success",
        "message": "档案已同步到云端",
        "cloud_user_id": (result.get('profile', {}).get('userId', '')[:20] + "...") if result.get('profile', {}).get('userId') else 'N/A',
        "matches_found": matches_count,
        "server_total_users": len(profiles) if isinstance(profiles := cloud_api_call('/api/profiles'), list) else 0
    }

def cmd_cloud_matches():
    """查看云端匹配结果"""
    if not is_cloud_enabled():
        return {"status": "disabled", "message": "云端功能未启用"}

    config = load_config()
    user_id = config.get('user', {}).get('user_id')

    if not user_id:
        return {
            "status": "error",
            "message": "尚未同步到云端，请先运行 'cloud-connect'"
        }

    result = cloud_api_call(f'/api/matches/{user_id}')

    if 'error' in result:
        return {"status": "error", "message": f"获取匹配失败: {result['error']}"}

    return {
        "status": "success",
        "matches": result.get('matches', []),
        "total": len(result.get('matches', []))
    }

def cmd_cloud_enable():
    """启用云端功能"""
    config = load_config()
    config['cloud']['enabled'] = True
    save_config(config)
    return {
        "status": "success",
        "message": "云端功能已启用",
        "note": "数据同步前请确认 cloud_config.json 中的 server_url 和 api_key（如有）"
    }

def cmd_cloud_disable():
    """禁用云端功能"""
    config = load_config()
    config['cloud']['enabled'] = False
    save_config(config)
    return {
        "status": "success",
        "message": "云端功能已禁用，所有云端同步已停止"
    }

def cmd_cloud_list():
    """列出云端所有用户"""
    if not is_cloud_enabled():
        return {"status": "disabled", "message": "云端功能未启用"}
    result = cloud_api_call('/api/profiles')
    if isinstance(result, list):
        return {"status": "success", "profiles": result, "total": len(result)}
    return {"status": "error", "message": result.get('error', '获取失败')}

def main():
    """命令行入口"""
    if len(sys.argv) < 2:
        print("A2A Match 云端命令 v1.8.6")
        print()
        print("用法:")
        print("  cloud-status       - 查看云端状态（含开关状态）")
        print("  cloud-connect      - 同步档案到云端（需先开启）")
        print("  cloud-list         - 查看云端所有用户")
        print("  cloud-matches      - 查看匹配结果")
        print("  cloud-enable       - 启用云端功能")
        print("  cloud-disable      - 禁用云端功能")
        print()
        print("⚠️  云端功能默认关闭！启用前请阅读 SKILL.md 中的隐私说明。")
        return

    cmd = sys.argv[1]

    if cmd == 'cloud-status':
        result = cmd_cloud_status()
    elif cmd == 'cloud-connect':
        result = cmd_cloud_connect()
    elif cmd == 'cloud-list':
        result = cmd_cloud_list()
    elif cmd == 'cloud-matches':
        result = cmd_cloud_matches()
    elif cmd == 'cloud-enable':
        result = cmd_cloud_enable()
    elif cmd == 'cloud-disable':
        result = cmd_cloud_disable()
    else:
        result = {"status": "error", "message": f"未知命令: {cmd}"}

    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()

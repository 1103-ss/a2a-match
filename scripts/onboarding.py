#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A2A Match - 新手引导与云端自动配置
两个功能：
  1. 探测并配置云端服务器（自动）
  2. 引导新用户完成第一步（对话式）
"""
import json, os, sys, urllib.request, urllib.error
from pathlib import Path
from datetime import datetime

# Windows UTF-8
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

WORKSPACE = Path(os.environ.get('QCLAW_WORKSPACE', Path.home() / '.qclaw' / 'workspace'))
A2A = WORKSPACE / 'a2a'
CONFIG = A2A / 'cloud_config.json'
PROFILE = A2A / 'profile.json'

# 默认服务器列表（按优先级）
DEFAULT_SERVERS = [
    'http://81.70.250.9:3000',
]

# ─── 工具函数 ────────────────────────────────────────────
def jread(p):
    return json.load(open(p, encoding='utf-8')) if p.exists() else {}

def jwrite(p, d):
    A2A.mkdir(parents=True, exist_ok=True)
    json.dump(d, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

def probe_server(url):
    """探测服务器是否在线，返回 (可用, info)"""
    try:
        req = urllib.request.Request(url + '/api/info', timeout=5)
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read())
            return True, data
    except:
        return False, None

def test_api(url, api_key=''):
    """测试服务器 API 是否可用"""
    try:
        h = {'Content-Type': 'application/json'}
        if api_key:
            h['Authorization'] = 'Bearer ' + api_key
        req = urllib.request.Request(url + '/api/info', headers=h)
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status == 200
    except urllib.error.HTTPError:
        return True  # 401/403 说明服务器在线，只是 key 不对
    except:
        return False

# ─── 云端配置（自动）──────────────────────────────────────
def setup_cloud():
    """
    自动探测可用服务器，询问用户确认后写入配置。
    返回 (success, message, server_url)
    """
    existing = jread(CONFIG)
    if existing.get('cloud', {}).get('enabled'):
        return True, '云端已开启，跳过配置', existing['cloud'].get('server_url', '')

    # 探测默认服务器
    working_server = None
    for url in DEFAULT_SERVERS:
        ok, info = probe_server(url)
        if ok:
            working_server = url
            break

    if not working_server:
        return False, '未找到可用的云端服务器，请联系管理员', ''

    # 写入配置（默认关闭，等待用户确认）
    new_cfg = {
        'cloud': {
            'enabled': False,  # 默认关闭
            'server_url': working_server,
            'api_key': ''
        },
        'user': {'user_id': None, 'last_sync': None}
    }
    jwrite(CONFIG, new_cfg)
    return True, f'已找到云端服务器 {working_server}，可随时开启', working_server

def enable_cloud(ask_permission=True):
    """
    启用云端同步：
      1. 确保配置已写入
      2. 读取 profile
      3. 上传档案到云端
      4. 开启 enabled=true
    返回 (success, message)
    """
    cfg = jread(CONFIG)
    if not cfg:
        ok, msg, _ = setup_cloud()
        if not ok:
            return False, msg
        cfg = jread(CONFIG)

    cloud = cfg.get('cloud', {})
    server_url = cloud.get('server_url')
    if not server_url:
        return False, '云端服务器未配置'

    prof = jread(PROFILE).get('profile', {})
    if not prof.get('name'):
        return False, '请先设置昵称：告诉我你叫什么名字'

    # 上传档案
    payload = {
        'userId': prof.get('id', ''),
        'name': prof.get('name', '匿名'),
        'email': prof.get('contact', {}).get('email', ''),
        'tags': [c.get('skill', '') for c in jread(PROFILE).get('capabilities', [])],
        'resources': [r.get('name', '') for r in jread(PROFILE).get('resources', [])],
        'needs': [n.get('skill', '') for n in jread(PROFILE).get('needs', [])]
    }

    h = {'Content-Type': 'application/json'}
    api_key = cloud.get('api_key', '')
    if api_key:
        h['Authorization'] = 'Bearer ' + api_key

    try:
        req = urllib.request.Request(
            server_url + '/api/profile',
            data=json.dumps(payload).encode('utf-8'),
            headers=h
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            result = json.loads(r.read())
            cloud_user_id = result.get('userId', prof.get('id'))

            # 更新配置
            cfg['cloud']['enabled'] = True
            cfg['user'] = {
                'user_id': cloud_user_id,
                'last_sync': datetime.now().isoformat()
            }
            jwrite(CONFIG, cfg)

            return True, f'云端已开启！你的 ID：{cloud_user_id}，档案已同步到云端'
    except urllib.error.HTTPError as e:
        return False, f'上传失败 HTTP {e.code}'
    except Exception as e:
        return False, f'上传失败：{e}'

def disable_cloud():
    """关闭云端同步"""
    cfg = jread(CONFIG)
    if not cfg:
        return True, '云端未配置'
    cfg['cloud']['enabled'] = False
    jwrite(CONFIG, cfg)
    return True, '云端已关闭，本地数据不再上传'

def get_status():
    """获取当前状态"""
    cfg = jread(CONFIG)
    prof = jread(PROFILE).get('profile', {})

    status = {
        'cloud_configured': bool(cfg),
        'cloud_enabled': cfg.get('cloud', {}).get('enabled', False),
        'server_url': cfg.get('cloud', {}).get('server_url', ''),
        'cloud_user_id': cfg.get('user', {}).get('user_id', None),
        'profile_name': prof.get('name', ''),
        'capabilities_count': len(jread(PROFILE).get('capabilities', [])),
        'needs_count': len(jread(PROFILE).get('needs', [])),
    }
    return status

# ─── 状态展示 ────────────────────────────────────────────
def print_status(status):
    print()
    print('=' * 50)
    print('📊 A2A Match 状态')
    print('=' * 50)

    # 档案状态
    name = status['profile_name'] or '❓ 未设置'
    caps = status['capabilities_count']
    needs = status['needs_count']
    print(f'  👤 昵称：{name}')
    print(f'  🛠️  能力：{caps} 个')
    print(f'  📦 需求：{needs} 个')
    print()

    # 云端状态
    if status['cloud_enabled']:
        print(f'  ☁️  云端：✅ 已开启')
        print(f'  🔗 服务器：{status["server_url"]}')
        print(f'  🆔 云端ID：{status["cloud_user_id"] or "未同步"}')
    else:
        print('  ☁️  云端：⏸️  未开启（默认模式：纯本地）')
    print()
    print('=' * 50)

# ─── 命令行入口 ────────────────────────────────────────────
if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'status'

    if cmd == 'setup':
        ok, msg, url = setup_cloud()
        print(msg)
        if ok and url:
            print(f'\n要开启云端吗？说「开启云端同步」即可。')

    elif cmd == 'enable':
        ok, msg = enable_cloud()
        print(msg)

    elif cmd == 'disable':
        ok, msg = disable_cloud()
        print(msg)

    elif cmd == 'status':
        status = get_status()
        print_status(status)

    else:
        print(f'用法: onboarding.py <setup|enable|disable|status>')

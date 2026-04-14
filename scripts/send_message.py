#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A2A Match 发送消息
用法: python send_message.py <match_id> <对方user_id> <消息内容>
"""

import json, os, sys, urllib.request
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

WORKSPACE_DIR = Path(os.environ.get('QCLAW_WORKSPACE', Path.home() / '.qclaw' / 'workspace'))
A2A_DIR = WORKSPACE_DIR / 'a2a'
CONFIG_PATH = A2A_DIR / 'cloud_config.json'
CLOUD_SERVER = "http://81.70.250.9:3000"


def load_json(path):
    if path.exists():
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: pass
    return None


def api_post(endpoint, payload):
    cfg = load_json(CONFIG_PATH) or {}
    url = (cfg.get('cloud', {}).get('server_url', CLOUD_SERVER)) + endpoint
    api_key = cfg.get('cloud', {}).get('api_key', '')
    headers = {'Content-Type': 'application/json'}
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'
    body = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=body, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode('utf-8'))


def get_user_id():
    cfg = load_json(CONFIG_PATH) or {}
    return cfg.get('user', {}).get('user_id')


def main():
    if len(sys.argv) < 4:
        print("用法: python send_message.py <match_id> <对方user_id> <消息内容>")
        sys.exit(1)

    match_id = sys.argv[1]
    to_user_id = sys.argv[2]
    content = sys.argv[3]
    from_user_id = get_user_id()

    if not from_user_id:
        print("错误: 未找到本地 userId，请先执行云端同步")
        sys.exit(1)

    result = api_post('/api/message', {
        "matchId": match_id,
        "fromUserId": from_user_id,
        "toUserId": to_user_id,
        "content": content
    })

    if result.get('success'):
        msg_id = result.get('messageId', '')
        print(f"OK:{msg_id}")
    else:
        print(f"ERROR:{result.get('error', '发送失败')}")
        sys.exit(1)


if __name__ == '__main__':
    main()

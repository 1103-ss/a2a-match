#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import subprocess, sys, os, shutil

# 创建干净的临时目录
tmp = 'C:/tmp/a2a-publish'
shutil.rmtree(tmp, ignore_errors=True)
os.makedirs(tmp, exist_ok=True)

# 复制必要文件
src = 'C:/Users/Administrator/.qclaw/workspace/a2a-match'
for f in ['SKILL.md', 'skill.json', 'README.md', 'CHANGELOG.md', 'server.js', 'ws_relay.js']:
    shutil.copy(os.path.join(src, f), tmp)
os.makedirs(os.path.join(tmp, 'scripts'), exist_ok=True)
for f in os.listdir(os.path.join(src, 'scripts')):
    shutil.copy(os.path.join(src, 'scripts', f), os.path.join(tmp, 'scripts'))

print('Published from:', tmp)
result = subprocess.run(
    ['npx', 'clawhub', 'publish', tmp,
     '--version', '2.8.0',
     '--changelog', 'v2.8.0: WebSocket realtime relay'],
    capture_output=True, text=True,
    timeout=120
)
print('EXIT:', result.returncode)
print('STDOUT:', result.stdout[:3000])
print('STDERR:', result.stderr[:1000])

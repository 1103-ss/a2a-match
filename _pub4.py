#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import subprocess, sys, os, shutil, time

# 复制到干净目录
tmp = 'C:/tmp/a2a-publish'
shutil.rmtree(tmp, ignore_errors=True)
os.makedirs(tmp, exist_ok=True)
src = 'C:/Users/Administrator/.qclaw/workspace/a2a-match'
for f in ['SKILL.md', 'skill.json', 'README.md', 'CHANGELOG.md', 'server.js', 'ws_relay.js']:
    shutil.copy(os.path.join(src, f), tmp)
os.makedirs(os.path.join(tmp, 'scripts'), exist_ok=True)
for f in os.listdir(os.path.join(src, 'scripts')):
    shutil.copy(os.path.join(src, 'scripts', f), os.path.join(tmp, 'scripts'))

print('Prepared:', tmp)
sys.stdout.flush()

cmd = ('cmd /c "cd /d %s && npx clawhub publish . --version 2.8.0 --changelog \"v2.8.0: WebSocket realtime relay\" 2>&1"' % tmp)
print('Running:', cmd)
sys.stdout.flush()
result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
print('EXIT:', result.returncode)
print('STDOUT:', result.stdout[:3000])
print('STDERR:', result.stderr[:500])

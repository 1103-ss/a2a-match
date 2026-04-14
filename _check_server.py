#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""查看云端服务器当前状态"""
import paramiko, sys

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    client.connect('81.70.250.9', username='ubuntu', password='Aa6842271', timeout=10)
except Exception as e:
    print('连接失败: ' + str(e))
    sys.exit(1)

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    return out, err

# 1. 目录结构
out, err = run('ls -la /var/www/a2a-match/')
print('=== 目录结构 ===')
print(out)

# 2. package.json
out, err = run('cat /var/www/a2a-match/package.json')
print('=== package.json ===')
print(out)

# 3. server_enhanced.js 行数
out, err = run('wc -l /var/www/a2a-match/server_enhanced.js')
print('=== server_enhanced.js 行数 ===')
print(out)

# 4. PM2 状态
out, err = run('pm2 list')
print('=== PM2 状态 ===')
print(out)

# 5. 消息相关关键词
out, err = run('grep -n "message\\|chat\\|relay\\|broadcast\\|sendMsg\\|deliver" /var/www/a2a-match/server_enhanced.js | head -30')
print('=== 消息相关关键词 ===')
print(out)
if err: print('STDERR:', err)

# 6. socket.io 版本
out, err = run('cd /var/www/a2a-match && npm list socket.io-client 2>/dev/null || npm list socket.io 2>/dev/null || echo "not found"')
print('=== socket.io ===')
print(out)

# 7. MongoDB
out, err = run("cd /var/www/a2a-match && node -e \"try{const p=require('./package.json');console.log('deps:',JSON.stringify(p.dependencies||{}));}catch(e){console.log(e)}\"")
print('=== package deps ===')
print(out)

client.close()
print('=== 完成 ===')

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试 WebSocket 连接 + ws_relay"""
import subprocess, json, time

# 用 node 内置 WebSocket 测试
test_code = '''
const { io } = require('/home/ubuntu/a2a-match/node_modules/socket.io-client');
const ws = require('/home/ubuntu/a2a-match/node_modules/ws');

async function test() {
    // 先测试 HTTP
    const http = require('http');
    return new Promise((resolve) => {
        http.get('http://localhost:3000/health', (res) => {
            let data = '';
            res.on('data', c => data += c);
            res.on('end', () => {
                console.log('HTTP_OK:' + data);
                resolve();
            });
        }).on('error', e => { console.log('HTTP_ERR:' + e.message); resolve(); });
    });
}
test();
'''

result = subprocess.run(['node', '-e', test_code], capture_output=True, text=True, timeout=10, cwd='/var/www/a2a-match')
print('HTTP Health:', result.stdout.strip())
if result.stderr: print('STDERR:', result.stderr.strip()[:200])

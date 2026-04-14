#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""下载服务器上的 server.js"""
import paramiko, sys

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    client.connect('81.70.250.9', username='ubuntu', password='Aa6842271', timeout=10)
except Exception as e:
    print('connect fail: ' + str(e))
    sys.exit(1)

sftp = client.open_sftp()
local_path = 'C:/Users/Administrator/.qclaw/workspace/a2a-match/server_fetched.js'
sftp.get('/var/www/a2a-match/server.js', local_path)
sftp.close()
client.close()
print('ok: ' + local_path)

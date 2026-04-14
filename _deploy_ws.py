#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deploy ws_relay.js + server.js to cloud server"""
import paramiko, os, time, sys

HOST = '81.70.250.9'
USER = 'ubuntu'
PASS = 'Aa6842271'
REMOTE_DIR = '/var/www/a2a-match'
TMP_DIR = '/home/ubuntu/tmp_deploy'
LOCAL_DIR = 'C:/Users/Administrator/.qclaw/workspace/a2a-match'
FILES = ['server.js', 'ws_relay.js']

def log(msg):
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode('ascii', 'replace').decode('ascii'))

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    client.connect(HOST, username=USER, password=PASS, timeout=10)
except Exception as e:
    log('SSH fail: ' + str(e))
    sys.exit(1)

sftp = client.open_sftp()

# Create tmp dir
try:
    sftp.mkdir(TMP_DIR)
except:
    pass

# Upload files
for fname in FILES:
    local = LOCAL_DIR + '/' + fname
    remote_tmp = TMP_DIR + '/' + fname
    if not os.path.exists(local):
        log('NOT FOUND: ' + local)
        continue
    log('Upload ' + fname + ' (' + str(os.path.getsize(local)) + ' bytes)...')
    sftp.put(local, remote_tmp)
    log('  done -> ' + remote_tmp)

sftp.close()

# Move to target with sudo
for fname in FILES:
    bak = REMOTE_DIR + '/' + fname + '.bak2'
    dest = REMOTE_DIR + '/' + fname
    tmp = TMP_DIR + '/' + fname
    # Check if file exists on server first
    stdin_chk, stdout_chk, _ = client.exec_command('ls ' + dest + ' 2>/dev/null && echo EXISTS || echo NEW')
    exists = 'EXISTS' in stdout_chk.read().decode('utf-8', errors='replace')
    if exists:
        cmd = 'sudo mv "%s" "%s" && sudo mv "%s" "%s" && echo DEPLOY_OK' % (dest, bak, tmp, dest)
    else:
        cmd = 'sudo mv "%s" "%s" && echo DEPLOY_OK' % (tmp, dest)
    log('Move ' + fname + '...')
    stdin, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    if 'DEPLOY_OK' in out:
        log('  DEPLOYED')
    else:
        log('  ERR: ' + out + ' | ' + err)

# Restart PM2
log('PM2 restart...')
cmd = 'cd /var/www/a2a-match && pm2 stop server.js 2>/dev/null; pm2 start server.js && pm2 save && echo PM2_OK'
stdin, stdout, stderr = client.exec_command(cmd)
out = stdout.read().decode('utf-8', errors='replace').strip()
log(out)
err = stderr.read().decode('utf-8', errors='replace').strip()
if err: log('STDERR: ' + err[:200])

time.sleep(5)

# Health check
log('Health check...')
stdin, stdout, stderr = client.exec_command('curl -s http://localhost:3000/health')
hc = stdout.read().decode('utf-8', errors='replace').strip()
log('Result: ' + hc)

# PM2 status
stdin, stdout, stderr = client.exec_command('pm2 list 2>&1 | head -10')
st = stdout.read().decode('utf-8', errors='replace').strip()
log('PM2: ' + st)

# Error log
stdin, stdout, stderr = client.exec_command('tail -15 /var/www/a2a-match/logs/error.log 2>/dev/null')
lg = stdout.read().decode('utf-8', errors='replace').strip()
if lg: log('Error log: ' + lg)

client.close()
log('DONE')

#!/usr/bin/env python3
"""Deploy server_enhanced.js v1.8.6 to cloud server"""
import paramiko, time, urllib.request, json

HOST = '81.70.250.9'
USER = 'ubuntu'
PASS = 'Aa6842271'
LOCAL_FILE = r'C:\Users\Administrator\.qclaw\workspace\a2a-match\scripts\server_enhanced.js'
REMOTE_PATH = '/var/www/a2a-match/server.js'

print("[1] Connecting to server...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(hostname=HOST, username=USER, password=PASS, timeout=15)
print("    Connected!")

sftp = ssh.open_sftp()

# Backup old file
ts = int(time.time())
try:
    sftp.rename(REMOTE_PATH, f'{REMOTE_PATH}.backup.{ts}')
    print(f"    Backup: {REMOTE_PATH}.backup.{ts}")
except Exception as e:
    print(f"    Backup skip: {e}")

# Upload new file
sftp.put(LOCAL_FILE, REMOTE_PATH)
print(f"    Uploaded: server_enhanced.js -> server.js")
sftp.close()

# Restart PM2
print("[2] Restarting PM2...")
stdin, stdout, stderr = ssh.exec_command(
    'pm2 restart a2a-match && sleep 5 && pm2 list'
)
out = stdout.read().decode('utf-8', errors='replace')
err = stderr.read().decode('utf-8', errors='replace')
print(out)
if err and 'error' in err.lower():
    print("PM2 Errors:", err[:300])

# Health check
print("[3] Verifying server...")
time.sleep(3)
try:
    resp = urllib.request.urlopen('http://81.70.250.9:3000/health', timeout=8)
    print("    Health:", resp.read().decode('utf-8', errors='replace'))
except Exception as e:
    print("    Health check failed:", e)

# API info check
try:
    resp2 = urllib.request.urlopen('http://81.70.250.9:3000/api/info', timeout=8)
    info = json.loads(resp2.read().decode('utf-8', errors='replace'))
    print("    API version:", info.get('service'))
    print("    Auth mode:", info.get('authMode'))
    print("    Auth required:", info.get('authRequired'))
except Exception as e:
    print("    API info:", e)

ssh.close()
print("[4] Done!")

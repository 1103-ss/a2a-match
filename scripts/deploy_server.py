import paramiko, sys, time, json, urllib.request

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

CLOUD_HOST = '81.70.250.9'
CLOUD_USER = 'ubuntu'
CLOUD_PASS = 'Aa6842271'
LOCAL_SERVER = r'C:\Users\Administrator\.qclaw\workspace\a2a-match\scripts\server_enhanced.js'
REMOTE_SERVER = '/var/www/a2a-match/server.js'

def deploy():
    print(f'Connecting to {CLOUD_HOST}...')
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(CLOUD_HOST, username=CLOUD_USER, password=CLOUD_PASS, timeout=15)
    
    # Upload
    print(f'Uploading server_enhanced.js...')
    sftp = ssh.open_sftp()
    sftp.put(LOCAL_SERVER, REMOTE_SERVER)
    sftp.close()
    print('Upload done.')
    
    # Restart PM2
    print('Restarting PM2...')
    stdin, stdout, stderr = ssh.exec_command('pm2 restart a2a-match')
    print(stdout.read().decode('utf-8').strip())
    time.sleep(3)
    
    # Verify
    stdin, stdout, stderr = ssh.exec_command('head -1 /var/www/a2a-match/server.js')
    print(f'Server header: {stdout.read().decode("utf-8").strip()}')
    
    stdin, stdout, stderr = ssh.exec_command('pm2 list --no-color | grep a2a')
    print(f'PM2: {stdout.read().decode("utf-8").strip()}')
    
    ssh.close()
    
    # External health check
    time.sleep(1)
    req = urllib.request.Request(f'http://{CLOUD_HOST}:3000/api/info')
    with urllib.request.urlopen(req, timeout=10) as resp:
        info = json.loads(resp.read().decode('utf-8'))
        print(f'API: {info.get("service", "N/A")}')
    
    print('=== CLOUD DEPLOY SUCCESS ===')

if __name__ == '__main__':
    deploy()

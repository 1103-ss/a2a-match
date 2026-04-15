# -*- coding: utf-8 -*-
import paramiko
HOST, PORT, USER, PASSWORD = '81.70.250.9', 22, 'ubuntu', 'Aa6842271'
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, port=PORT, username=USER, password=PASSWORD, timeout=10)
# Upload the new onboarding script
sftp = client.open_sftp()
sftp.put(r'C:\Users\Administrator\.qclaw\workspace\a2a-match\scripts\onboarding.py', '/var/www/a2a-match/scripts/onboarding.py')
sftp.close()
print('Uploaded onboarding.py')
# Restart
stdin, stdout, stderr = client.exec_command('cd /var/www/a2a-match && pm2 restart a2a-match && sleep 3 && pm2 list')
out = stdout.read().decode('utf-8', errors='replace')
print(out.encode('ascii', 'replace').decode('ascii'))
client.close()

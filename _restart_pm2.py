# -*- coding: utf-8 -*-
import paramiko
HOST, PORT, USER, PASSWORD = '81.70.250.9', 22, 'ubuntu', 'Aa6842271'
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, port=PORT, username=USER, password=PASSWORD, timeout=10)
cmd = 'cd /var/www/a2a-match && pm2 restart a2a-match && sleep 3 && pm2 list'
stdin, stdout, stderr = client.exec_command(cmd)
out = stdout.read().decode('utf-8', errors='replace')
err = stderr.read().decode('utf-8', errors='replace')
# Print without unicode chars
print(out.encode('ascii', 'replace').decode('ascii'))
if err:
    print('STDERR:', err.encode('ascii', 'replace').decode('ascii'))
client.close()

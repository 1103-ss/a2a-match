#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import paramiko

def p(s):
    try: print(s)
    except: print(s.encode('ascii','replace').decode('ascii'))

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('81.70.250.9', username='ubuntu', password='Aa6842271', timeout=10)

# Write test script to server
test_script = r'''
const io = require("socket.io-client");
const s = io("http://localhost:3000", { transports: ["websocket"], timeout: 8000 });
s.on("connect", function() {
    console.log("CONNECTED:" + s.id);
    s.emit("join", { userId: "test_user_001", matchId: null });
});
s.on("joined", function(d) {
    console.log("JOINED:" + JSON.stringify(d));
    s.disconnect();
    process.exit(0);
});
s.on("connect_error", function(e) {
    console.log("ERR:" + e.message);
    process.exit(1);
});
setTimeout(function() {
    console.log("TIMEOUT");
    process.exit(1);
}, 8000);
'''

# Write to file
with open('/tmp/ws_test.js', 'w') as f:
    f.write(test_script)

sftp = client.open_sftp()
sftp.put('/tmp/ws_test.js', '/home/ubuntu/ws_test.js')
sftp.close()

# Run test
stdin, stdout, stderr = client.exec_command('cd /var/www/a2a-match && node /home/ubuntu/ws_test.js 2>&1')
out = stdout.read().decode('utf-8', errors='replace').strip()
err = stderr.read().decode('utf-8', errors='replace').strip()
p('WS result: ' + out[:400])
if err and 'CONNECTED' not in out:
    p('WS stderr: ' + err[:400])

client.close()
p('DONE')

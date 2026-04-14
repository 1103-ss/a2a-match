#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import paramiko

def p(s):
    try: print(s)
    except: print(s.encode('ascii','replace').decode('ascii'))

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('81.70.250.9', username='ubuntu', password='Aa6842271', timeout=10)

tests = [
    ('HTTP Health', 'curl -s http://localhost:3000/health'),
    ('ws_relay module', 'cd /var/www/a2a-match && node -e "try{require(\'./ws_relay\');p(\'OK\');}catch(e){p(\'ERR:\'+e.message);}"'),
]

for name, cmd in tests:
    stdin, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    p(name + ': ' + out[:200])
    if err and 'OK' not in out: p('  ERR: ' + err[:200])

# WS test
ws_code = 'io=require("socket.io-client");s=io("http://localhost:3000",{transports:["websocket"],timeout:5000});s.on("connect",function(){p("CONNECTED:"+s.id);s.emit("join",{userId:"test001"});s.on("joined",function(d){p("JOINED:"+JSON.stringify(d));s.disconnect();process.exit(0);});});s.on("connect_error",function(e){p("ERR:"+e.message);process.exit(1);});setTimeout(function(){p("TIMEOUT");process.exit(1);},6000);'
stdin, stdout, stderr = client.exec_command('cd /var/www/a2a-match && node -e "' + ws_code + '" 2>&1')
out = stdout.read().decode('utf-8', errors='replace').strip()
err = stderr.read().decode('utf-8', errors='replace').strip()
p('WS: ' + out[:300])
if err and 'CONNECTED' not in out: p('WS ERR: ' + err[:300])

client.close()
p('DONE')

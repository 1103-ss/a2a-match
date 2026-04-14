import json, urllib.request, sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

BASE = 'http://81.70.250.9:3000'
UID = 'user_0a66ca36'
MATCH_ID = '69ddebd2bc8bd8eda844ba89'

def api(path):
    req = urllib.request.Request(BASE + path)
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.loads(r.read().decode('utf-8'))

# 1. Chat messages between me and guodage
print('=== 我与 guodage 的聊天记录 ===')
msg_data = api(f'/api/match/{MATCH_ID}/messages?userId={UID}')
if isinstance(msg_data, dict):
    msgs = msg_data.get('messages', msg_data.get('data', []))
elif isinstance(msg_data, list):
    msgs = msg_data
else:
    msgs = []

for m in msgs:
    sender = 'me' if m.get('fromUserId') == UID else 'guodage'
    content = m.get('content', '')
    ts = m.get('createdAt', m.get('timestamp', ''))
    status = m.get('status', m.get('read', ''))
    print(f'  [{ts[:19] if ts else "??"}] {sender}: {content}')
    if status:
        print(f'    status={status}')

# 2. My unread messages
print('\n=== 我的未读消息 ===')
unread = api(f'/api/messages/{UID}?unread=true')
if isinstance(unread, dict):
    msgs2 = unread.get('messages', unread.get('data', []))
elif isinstance(unread, list):
    msgs2 = unread
else:
    msgs2 = []
print(f'  unread count: {len(msgs2)}')
for m in msgs2:
    print(f'  from={m.get("fromNickname","")} content={m.get("content","")[:60]}')

# 3. Match status
print('\n=== 匹配状态 ===')
match = api(f'/api/match/{MATCH_ID}?userId={UID}')
if isinstance(match, dict):
    print(f'  status={match.get("status")} acceptedAt={match.get("acceptedAt","")}')
    other = match.get('otherUser', {})
    print(f'  other: name={other.get("name","")} online={other.get("online","")}')

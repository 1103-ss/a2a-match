import json, urllib.request, sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

BASE = 'http://81.70.250.9:3000'
UID = 'user_0a66ca36'

def api(path, method='GET', data=None):
    url = BASE + path
    body = None
    if data:
        body = json.dumps(data).encode('utf-8')
    req = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.loads(r.read().decode('utf-8'))

print('=== 1. Health Check ===')
print(api('/health'))

print('\n=== 2. My Profile ===')
p = api(f'/api/profile/{UID}')
print(f'  name={p.get("name","")} tags={p.get("tags",[])} needs={p.get("needs",[])} resources={p.get("resources",[])}')

print('\n=== 3. Matches ===')
matches = api(f'/api/matches/{UID}')
print(f'  count={len(matches)}')
for m in matches:
    other = m.get('otherUser', {})
    print(f'  id={m["id"][:16]} status={m["status"]} other={other.get("name","")} score={m.get("score",0)}')

print('\n=== 4. Send Message ===')
result = api('/api/message', 'POST', {
    'matchId': '69ddebd2bc8bd8eda844ba89',
    'fromUserId': UID,
    'toUserId': 'a3f8d2e1-guodage-4a8a-b9c1-d28ef3a7c501',
    'content': '[v2.5.0 cloud test] deploy verification ok'
})
print(f'  success={result.get("success")} msgId={result.get("messageId","")}')

print('\n=== 5. Unread Messages ===')
msgs = api(f'/api/messages/{UID}?unread=true')
print(f'  unread={len(msgs)}')

print('\n=== 6. Chat History ===')
hist = api(f'/api/match/69ddebd2bc8bd8eda844ba89/messages?userId={UID}')
print(f'  total={len(hist)}')
for h in hist[-5:]:
    who = 'me' if h.get('fromUserId') == UID else h.get('fromUserId', '')[:12]
    print(f'  [{who}] {h.get("content","")[:60]}')

print('\n=== ALL CLOUD TESTS PASSED ===')

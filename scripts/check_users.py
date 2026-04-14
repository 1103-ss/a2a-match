import json, urllib.request, sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

BASE = 'http://81.70.250.9:3000'

def api(path):
    req = urllib.request.Request(BASE + path)
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.loads(r.read().decode('utf-8'))

# 1. Stats
print('=== 平台统计 ===')
stats = api('/api/stats')
for k, v in stats.items():
    print(f'  {k}: {v}')

# 2. All profiles
print('\n=== 所有用户 ===')
profiles = api('/api/profiles')
if isinstance(profiles, dict):
    plist = profiles.get('profiles', profiles.get('data', []))
elif isinstance(profiles, list):
    plist = profiles
else:
    plist = []

real_users = []
test_users = []
for p in plist:
    uid = p.get('userId', p.get('id', ''))
    name = p.get('name', p.get('nickname', ''))
    needs = p.get('needs', [])
    resources = p.get('resources', [])
    tags = p.get('tags', [])
    created = p.get('createdAt', '')

    # check if real or test
    has_content = bool(needs or resources)
    entry = {
        'uid': uid[:20],
        'name': name,
        'needs': needs,
        'resources': resources,
        'tags': tags[:3] if tags else [],
        'created': created[:10] if created else ''
    }
    if has_content:
        real_users.append(entry)
    else:
        test_users.append(entry)

print(f'  总用户: {len(plist)}')
print(f'  真实用户(有需求/资源): {len(real_users)}')
print(f'  空档案: {len(test_users)}')

print('\n--- 真实用户 ---')
for u in real_users:
    print(f'  [{u["name"]}] uid={u["uid"]} needs={u["needs"]} resources={u["resources"]} tags={u["tags"]}')

print('\n--- 空档案 ---')
for u in test_users:
    print(f'  [{u["name"]}] uid={u["uid"]} created={u["created"]}')

# 3. Check matches for each real user
print('\n=== 匹配情况 ===')
total_matches = 0
accepted_matches = 0
for u in real_users:
    uid = u['uid']
    try:
        matches = api(f'/api/matches/{uid}')
        if isinstance(matches, dict):
            mlist = matches.get('matches', matches.get('data', []))
        elif isinstance(matches, list):
            mlist = matches
        else:
            mlist = []
        total_matches += len(mlist)
        for m in mlist:
            status = m.get('status', '')
            other = m.get('otherUser', {})
            if status == 'accepted':
                accepted_matches += 1
            print(f'  [{u["name"]}] <-> [{other.get("name","")}] status={status} score={m.get("score","")}')
    except Exception as e:
        print(f'  [{u["name"]}] error: {e}')

print(f'\n=== 汇总 ===')
print(f'  总匹配数: {total_matches}')
print(f'  已接受: {accepted_matches}')
print(f'  待确认: {total_matches - accepted_matches}')

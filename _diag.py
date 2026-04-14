import json, os

data = json.load(open('a2a-match/skill.json', encoding='utf-8'))
print('=== skill.json key fields ===')
print('name:', data.get('name'))
print('version:', data.get('version'))
print('entry:', data.get('entry'))
print('description (first 150):', data.get('description', '')[:150])
print()

print('=== scripts/ dir contents ===')
total = 0
for root, dirs, files in os.walk('a2a-match/scripts'):
    for f in files:
        p = os.path.join(root, f)
        sz = os.path.getsize(p)
        total += sz
        print(f'  {os.path.relpath(p, "a2a-match")}: {sz} bytes ({sz//1024}KB)')
print(f'Total scripts/: {total} bytes ({total//1024}KB)')
print()

# Check skillhub install location
homes = [
    os.path.expanduser('~/.openclaw/skills/a2a-match'),
    os.path.expanduser('~/.claw/skills/a2a-match'),
]
for h in homes:
    if os.path.exists(h):
        print(f'Found skill at: {h}')
        for f in os.listdir(h):
            fp = os.path.join(h, f)
            if os.path.isdir(fp):
                print(f'  [DIR] {f}/')
            else:
                print(f'  {f}: {os.path.getsize(fp)} bytes')
    else:
        print(f'Not found: {h}')

# Current SKILL.md size
sm_sz = os.path.getsize('a2a-match/SKILL.md')
print(f'\nSKILL.md: {sm_sz} bytes, ~{sm_sz//4} tokens, ~{sm_sz//120} lines')

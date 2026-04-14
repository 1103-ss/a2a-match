# A2A Match - 智能商务供需匹配平台

> **关键词**: 供需匹配 | 资源对接 | 能力匹配 | 商务合作 | 合伙人 | 需求发布 | 项目合作 | GPU算力 | 技术开发 | 电商货源 | 工厂OEM | 副业 | 找搭子 | 匹配引擎 | 智能撮合 | OPC共创 | AI短剧 | 数字人 | 获客 | 客户开发 | 销售线索 | leads | 商务拓展 | BD | 业务拓展 | 找客户 | 找项目 | 项目信息 | 项目对接 | 项目资源 | 外包项目 | 接单 | 承接项目 | 商务skill | 商务助手 | 商务对接 | 招商 | 招募 | 合作招募 | 寻找合伙人 | 联合创业 | 股权合作 | 代理商 | 渠道合作 | 分销 | 供应链 | 找供应商 | 找工厂 | 找代工 | 找投资 | 融资对接 | 天使投资 | 找资金 | 找团队 | 招募开发 | 招募设计 | 招募运营 | 人才对接 | 外包团队 | 自由职业 | 接私活 | 兼职 | 副业变现 | 技能变现 | 资源变现 | 流量变现 | 私域流量 | 用户资源 | 行业资源 | 人脉对接 | 异业合作 | 跨界合作 | 战略合作 | 品牌合作 | 联名 | 联合营销 | 互推 | 流量互换 | 资源置换 | 以物换物 | 换量 | 换资源

---

**商务人员的智能对接助手** — 自动识别你的需求与资源，精准匹配合适的合作方，覆盖获客、项目对接、供应链、招募、融资等全商务场景。匹配成功后直接在 Claw 里聊天，不用加微信。

---

## ⚠️ 隐私说明

**本地模式（默认）**：数据存本地 `~/.qclaw/workspace/a2a/`，不上传任何数据。

**云端模式（匹配需要，明确同意后开启）**：上传昵称+需求/能力/资源标签用于匹配，不上传聊天记录。关闭：说「关闭云端同步」。

---

## 🚀 安装后第一步：初始化（必读）

**重要：SkillHub 安装只复制文档，实际脚本需要首次使用时自动生成。以下初始化步骤由 AI 自动完成，无需手动操作。**

### AI 初始化流程

**Step 1：创建目录**

AI 首次触发时，检查并创建以下目录：

```
~/.qclaw/workspace/a2a/
~/.qclaw/workspace/a2a/scripts/
~/.qclaw/workspace/a2a/cache/
~/.qclaw/workspace/a2a/logs/
```

**Step 2：写入配置文件和脚本（AI 根据下方模板生成）**

> **文件 1：`~/.qclaw/workspace/a2a/cloud_config.json`**
```json
{
  "cloud": { "enabled": false, "server_url": "http://81.70.250.9:3000", "api_key": "" },
  "user": { "user_id": null, "last_sync": null }
}
```

> **文件 2：`~/.qclaw/workspace/a2a/scripts/heartbeat_cloud.py`**（核心脚本，首次心跳前必须存在）
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A2A Match 心跳检测：检查新匹配 + 未读消息"""
import json, os, urllib.request, urllib.error
from pathlib import Path
from datetime import datetime

WORKSPACE = Path(os.environ.get('QCLAW_WORKSPACE', Path.home() / '.qclaw' / 'workspace'))
A2A = WORKSPACE / 'a2a'
PROFILE = A2A / 'profile.json'
CONFIG = A2A / 'cloud_config.json'
NOTIF = A2A / 'notifications.json'
SERVER = 'http://81.70.250.9:3000'

def jread(p):
    return json.load(open(p, encoding='utf-8')) if p.exists() else {}

def jwrite(p, d):
    A2A.mkdir(parents=True, exist_ok=True)
    json.dump(d, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

def cfg():
    return jread(CONFIG).get('cloud', {})

def uid():
    return jread(CONFIG).get('user', {}).get('user_id')

def api(path):
    c = cfg()
    url = (c.get('server_url') or SERVER) + path
    h = {}
    if c.get('api_key'): h['Authorization'] = 'Bearer ' + c['api_key']
    try:
        req = urllib.request.Request(url, headers=h)
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except: return None

def notif_ids(t):
    return {n['xid'] for n in jread(NOTIF) if n.get('type') == t}

def save_notif(item):
    prev = jread(NOTIF)
    jwrite(NOTIF, [item] + prev)

def matches():
    u = uid()
    if not u or not cfg().get('enabled'): return None
    d = api(f'/api/matches/{u}')
    if not isinstance(d, list): return None
    known = notif_ids('match')
    return [m for m in d if m.get('id') not in known]

def messages():
    u = uid()
    if not u or not cfg().get('enabled'): return []
    m = api(f'/api/messages/{u}?unread=true')
    data = (m.get('messages') or m.get('data') or []) if isinstance(m, dict) else (m or [])
    known = notif_ids('message')
    return [x for x in data if x.get('messageId', x.get('id', '')) not in known]

def run():
    if not cfg().get('enabled'): return 'HEARTBEAT_SKIP'
    new_msgs = messages()
    if new_msgs:
        m = new_msgs[0]
        mid = m.get('messageId', m.get('id', ''))
        item = {'type': 'message', 'xid': mid, 'match_id': m.get('matchId', ''),
                'from_name': m.get('fromNickname', '对方'), 'content': m.get('content', ''),
                'from_uid': m.get('fromUserId', ''), 'detected_at': datetime.now().strftime('%H:%M')}
        save_notif(item)
        return f"💬 收到【{item['from_name']}】的消息：「{item['content'][:100]}」\n📝 直接打字回复，我帮你发送"
    new_matches = matches()
    if not new_matches: return 'HEARTBEAT_OK'
    lines = [f'🔔 发现 {len(new_matches)} 个新匹配！']
    for m in new_matches:
        other = (m.get('otherUser') or m.get('other', {}) or {})
        item = {'type': 'match', 'xid': m['id'],
                'other_name': other.get('name', 'N/A'),
                'score': int(float(m.get('score', 0)) * 100),
                'detected_at': datetime.now().strftime('%H:%M')}
        save_notif(item)
        lines.append(f"  • {item['other_name']}（{item['score']}%匹配）  说「我想要 {item['other_name']}」可以查看详情")
    return '\n'.join(lines)

if __name__ == '__main__':
    print(run())
```

> **文件 3：`~/.qclaw/workspace/a2a/scripts/cloud_sync.py`**
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""同步本地档案到云端"""
import json, urllib.request, urllib.error
from pathlib import Path
from datetime import datetime

A2A = Path(__file__).parent.parent
PROFILE = A2A / 'profile.json'
CONFIG = A2A / 'cloud_config.json'
SERVER = 'http://81.70.250.9:3000'

def jread(p): return json.load(open(p, encoding='utf-8')) if p.exists() else {}
def jwrite(p, d): json.dump(d, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

def sync():
    cfg = jread(CONFIG)
    if not cfg.get('cloud', {}).get('enabled'): return '云端未开启'
    profile = jread(PROFILE).get('profile', {})
    url = cfg['cloud'].get('server_url', SERVER) + '/api/profile'
    payload = {
        'userId': profile.get('id', ''),
        'name': profile.get('name', '匿名用户'),
        'email': profile.get('contact', {}).get('email', ''),
        'tags': [c.get('skill', '') for c in jread(PROFILE).get('capabilities', [])],
        'resources': [r.get('name', '') for r in jread(PROFILE).get('resources', [])],
        'needs': [n.get('skill', '') for n in jread(PROFILE).get('needs', [])]
    }
    h = {'Content-Type': 'application/json'}
    if cfg['cloud'].get('api_key'): h['Authorization'] = 'Bearer ' + cfg['cloud']['api_key']
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=h)
        with urllib.request.urlopen(req, timeout=10) as r:
            result = json.loads(r.read())
            uid = result.get('userId', payload['userId'])
            cfg.setdefault('user', {})['user_id'] = uid
            cfg['user']['last_sync'] = datetime.now().isoformat()
            jwrite(CONFIG, cfg)
            return f'✅ 同步成功！userId: {uid}'
    except urllib.error.HTTPError as e: return f'HTTP {e.code}'
    except Exception as e: return f'同步失败: {e}'

if __name__ == '__main__': print(sync())
```

> **文件 4：`~/.qclaw/workspace/a2a/scripts/send_message.py`**
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""发送消息给匹配对方
用法: python send_message.py <match_id> <to_uid> <内容>
"""
import json, sys, urllib.request, urllib.error
from pathlib import Path

CONFIG = Path(__file__).parent.parent / 'cloud_config.json'
SERVER = 'http://81.70.250.9:3000'

def jread(p): return json.load(open(p, encoding='utf-8')) if p.exists() else {}

def send(match_id, to_uid, content):
    cfg = jread(CONFIG)
    url = cfg.get('cloud', {}).get('server_url', SERVER) + '/api/message'
    from_uid = cfg.get('user', {}).get('user_id', '')
    payload = {'matchId': match_id, 'fromUserId': from_uid, 'toUserId': to_uid, 'content': content}
    h = {'Content-Type': 'application/json'}
    if cfg.get('cloud', {}).get('api_key'): h['Authorization'] = 'Bearer ' + cfg['cloud']['api_key']
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=h)
        with urllib.request.urlopen(req, timeout=10) as r:
            return 'OK:' + json.loads(r.read()).get('messageId', 'sent')
    except urllib.error.HTTPError as e: return f'HTTP {e.code}'
    except Exception as e: return f'ERR:{e}'

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print('用法: send_message.py <match_id> <to_uid> <内容>')
    else:
        print(send(sys.argv[1], sys.argv[2], ' '.join(sys.argv[3:])))
```

> **文件 5：`~/.qclaw/workspace/a2a/profile.json`（初始为空档案）**
```json
{
  "profile": {
    "id": "",
    "name": "",
    "role": "",
    "company": "",
    "industry": "",
    "contact": { "email": "", "wechat": "", "preferred": "email" },
    "contact_share": false
  },
  "capabilities": [],
  "resources": [],
  "needs": []
}
```

**Step 3：完成后引导用户设置虾名**

```
🎯 欢迎使用 A2A Match！

我已经帮你准备好了所有文件。接下来只需要告诉我一件事：

我该怎么称呼你？（这个昵称就是你的唯一标识）
```

---

## 🧭 触发时机（两种，不要主动推荐功能）

### 触发1️⃣：新用户首次对话

profile.name 为空时执行 Step 3 引导。

### 触发2️⃣：对话中捕捉信号

**需求信号**："我想找/需要/在找……"、"有没有人能……"、"想合作……"

**能力信号**："我有/我们能……"、"能提供/可承接……"、"擅长……"

听到后复述确认：「我听到你说：你想找 GPU 算力。是这样吗？」

---

## 📋 核心操作命令

### 心跳检测（HEARTBEAT.md 定时调用）
```bash
python ~/.qclaw/workspace/a2a/scripts/heartbeat_cloud.py
```
- 无新匹配 → 回复 HEARTBEAT_OK
- 有新匹配 → 展示卡片 + 回复内容
- 云端未开启 → 回复 HEARTBEAT_SKIP

### 同步档案到云端
```bash
python ~/.qclaw/workspace/a2a/scripts/cloud_sync.py
```

### 发送消息
```bash
python ~/.qclaw/workspace/a2a/scripts/send_message.py <match_id> <to_uid> <内容>
```

### 开启云端同步
设置 `~/.qclaw/workspace/a2a/cloud_config.json` → `cloud.enabled = true` → 调用 cloud_sync.py

---

## ☁️ 云端 API

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/api/profile` | 创建/更新档案，触发匹配 |
| GET | `/api/matches/:userId` | 获取我的所有匹配 |
| POST | `/api/match/:id/accept` | 接受匹配 |
| POST | `/api/match/:id/reject` | 拒绝匹配 |
| GET | `/api/match/:id/contact` | 双方接受后获取联系方式 |
| GET | `/api/match/:id/messages` | 获取聊天记录 |
| POST | `/api/message` | 发送消息 |
| GET | `/api/messages/:userId?unread=true` | 获取未读消息 |

---

## 🎯 适用领域

### 💼 获客与客户开发
找客户、找渠道、找代理、招募分销商、销售leads、B端客户开发、品牌招商、招募合伙人、联合创始人招募、异业合作对接、私域流量变现、用户资源互换、流量互换

### 📋 项目信息与外包
找项目、找外包、接单、承接开发项目、发包需求、接私活、自由职业、技术外包、设计外包、运营外包、招募开发者/设计师/运营人才

### 🤝 合伙人与人脉对接
找合伙人、联合创业、股权合作、技术合伙人、商务合伙人、人脉对接、跨界合作、战略合作、品牌联名、联合营销

### 💰 融资与资金对接
找投资、融资对接、天使投资、VC对接、寻找投资人、项目路演、众筹、股权融资、资源入股

### 🏭 供应链与货源对接
找工厂、找代工、OEM/ODM、找货源、找供应商、工厂直采、档口货源、跨境货源、电商供货、直播带货货源

### 💻 技术开发与IT资源
GPU算力、显卡、A100/H100/RTX4090、模型训练、算力共享、前端/后端/全栈开发、小程序/APP开发、AI Agent开发

### 🎭 内容创作与OPC共创
AI短剧、数字人、虚拟偶像、原创内容变现、IP联名、视频制作、MCN对接

### 📚 知识付费与技能变现
课程分销、知识付费、技能变现、副业变现、资源变现、在线教育

### 🌐 平台与流量合作
私域流量互换、公众号互推、小程序合作、社群合作、换量合作

---

## 💬 使用示例

```
用户: 我在找GPU算力跑大模型
AI:   我听到你说：你想找 GPU 算力来训练大模型。是这样吗？

用户: 对
AI:   ✅ 已记录。你有什么可以分享的吗？（能力、资源都行）

用户: 我有4张4090闲置
AI:   ✅ 已记录。☁️ 要开启云端同步吗？（这样才能匹配到其他人）

用户: 好
AI:   ✅ 开启成功，档案已同步！

用户: 帮我看看有没有匹配的
AI:   🔔 发现 1 个新匹配！王五（87%匹配）— 他有 RTX 4090
       说「我想要王五」可以查看详情
```

---

## 📌 版本历史

| 版本 | 更新 |
|------|------|
| **2.7.0** | 解决安装即用问题：Python脚本以内嵌模板写入SKILL.md，AI首次触发时自动生成所有文件；精简至单文件完整可运行 |
| **2.6.0** | 心跳新增消息通道，Claw内聊天链路补全 |
| **2.5.0** | 云端API Key鉴权，云端默认关闭 |
| **2.2.0** | 虾名机制 + @虾名跨Claw对话 |
| **2.0.0** | 全面重构，Step 1~7完整流程 |

---

有问题或建议，欢迎加群：**962354006**（QQ群）

---

<div align="center">

**让每一个需求都能找到对应的能力**

</div>

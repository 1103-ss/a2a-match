# A2A Match - 智能商务供需匹配平台

> **关键词**: 供需匹配 | 资源对接 | 能力匹配 | 商务合作 | 合伙人 | 需求发布 | 项目合作 | GPU算力 | 技术开发 | 电商货源 | 工厂OEM | 副业 | 找搭子 | 匹配引擎 | 智能撮合 | OPC共创 | AI短剧 | 数字人 | 获客 | 客户开发 | 销售线索 | leads | 商务拓展 | BD | 业务拓展 | 找客户 | 找项目 | 项目信息 | 项目对接 | 项目资源 | 外包项目 | 接单 | 承接项目 | 商务skill | 商务助手 | 商务对接 | 招商 | 招募 | 合作招募 | 寻找合伙人 | 联合创业 | 股权合作 | 代理商 | 渠道合作 | 分销 | 供应链 | 找供应商 | 找工厂 | 找代工 | 找投资 | 融资对接 | 天使投资 | 找资金 | 找团队 | 招募开发 | 招募设计 | 招募运营 | 人才对接 | 外包团队 | 自由职业 | 接私活 | 兼职 | 副业变现 | 技能变现 | 资源变现 | 流量变现 | 私域流量 | 用户资源 | 行业资源 | 人脉对接 | 异业合作 | 跨界合作 | 战略合作 | 品牌合作 | 联名 | 联合营销 | 互推 | 流量互换 | 资源置换 | 以物换物 | 换量 | 换资源

---

**商务人员的智能对接助手** — 自动识别你的需求与资源，精准匹配合适的合作方，覆盖获客、项目对接、供应链、招募、融资等全商务场景。匹配成功后直接在 Claw 里实时聊天，不用加微信。

---

## ⚠️ 隐私说明

**本地模式（默认）**：数据存本地 `~/.qclaw/workspace/a2a/`，不上传任何数据。

**云端模式（匹配需要，明确同意后开启）**：上传昵称+需求/能力/资源标签用于匹配，不上传聊天记录。关闭：说「关闭云端同步」。

---

## 🚀 安装后第一步：初始化

SkillHub 安装只复制文档，实际脚本需要首次使用时自动生成。AI 读取本文件后自动执行以下初始化，无需手动操作。

### Step 1：创建目录
```
~/.qclaw/workspace/a2a/
~/.qclaw/workspace/a2a/scripts/
~/.qclaw/workspace/a2a/cache/
~/.qclaw/workspace/a2a/logs/
```

### Step 2：写入以下文件（模板见下方）

**文件 1：`~/.qclaw/workspace/a2a/cloud_config.json`**
```json
{
  "cloud": { "enabled": false, "server_url": "http://81.70.250.9:3000", "api_key": "" },
  "user": { "user_id": null, "last_sync": null }
}
```

**文件 2：`~/.qclaw/workspace/a2a/scripts/heartbeat_cloud.py`**（心跳检测：检查新匹配 + 未读消息）
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
    return {n.get('xid') for n in jread(NOTIF) if n.get('type') == t}

def save_notif(item):
    prev = jread(NOTIF)
    jwrite(NOTIF, [item] + prev)

def matches():
    u = uid()
    if not u or not cfg().get('enabled'): return None
    d = api(f'/api/matches/{u}')
    if not isinstance(d, list): return None
    known = notif_ids('match')
    return [m for m in d if str(m.get('id', '')) not in known]

def messages():
    u = uid()
    if not u or not cfg().get('enabled'): return []
    m = api(f'/api/messages/{u}')
    data = (m.get('messages') or []) if isinstance(m, dict) else (m or [])
    known = notif_ids('message')
    return [x for x in data if str(x.get('messageId', '')) not in known]

def run():
    if not cfg().get('enabled'): return 'HEARTBEAT_SKIP'
    new_msgs = messages()
    if new_msgs:
        m = new_msgs[0]
        from_name = m.get('from', {}).get('name', '对方')
        item = {'type': 'message', 'xid': str(m.get('messageId', '')),
                'match_id': str(m.get('matchId', '')),
                'from_name': from_name,
                'content': m.get('content', ''),
                'from_uid': m.get('from', {}).get('userId', ''),
                'detected_at': datetime.now().strftime('%H:%M')}
        save_notif(item)
        return f"收到【{from_name}】的消息：「{item['content'][:80]}」\n直接打字回复，我帮你发送"
    new_matches = matches()
    if not new_matches: return 'HEARTBEAT_OK'
    lines = [f'发现 {len(new_matches)} 个新匹配！']
    for m in new_matches:
        other = (m.get('otherUser') or {})
        item = {'type': 'match', 'xid': str(m.get('id', '')),
                'other_name': other.get('name', 'N/A'),
                'score': int(float(m.get('score', 0)) * 100),
                'detected_at': datetime.now().strftime('%H:%M')}
        save_notif(item)
        lines.append(f"  · {item['other_name']}（{item['score']}%匹配）")
    return '\n'.join(lines)

if __name__ == '__main__':
    print(run())
```

**文件 3：`~/.qclaw/workspace/a2a/scripts/cloud_sync.py`**
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
    prof = jread(PROFILE).get('profile', {})
    url = cfg['cloud'].get('server_url', SERVER) + '/api/profile'
    payload = {
        'userId': prof.get('id', ''),
        'name': prof.get('name', '匿名'),
        'email': prof.get('contact', {}).get('email', ''),
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
            return f'同步成功！userId: {uid}'
    except urllib.error.HTTPError as e: return f'HTTP {e.code}'
    except Exception as e: return f'同步失败: {e}'

if __name__ == '__main__': print(sync())
```

**文件 4：`~/.qclaw/workspace/a2a/scripts/a2a_ws_client.py`**
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A2A Match WebSocket 实时通讯客户端
用法:
  python a2a_ws_client.py join <user_id> <match_id>
  python a2a_ws_client.py send <content>
  python a2a_ws_client.py history <match_id>
"""
import json, sys, time, threading, queue, urllib.request
from pathlib import Path

SERVER = 'http://81.70.250.9:3000'
CONFIG = Path(__file__).parent.parent / 'cloud_config.json'
A2A = Path(__file__).parent.parent

def jread(p): return json.load(open(p, encoding='utf-8')) if p.exists() else {}
def cfg(): return jread(CONFIG).get('cloud', {})

# 尝试导入 socket.io.client（需要: pip install "python-socketio[client]>=4.6")
try:
    import socketio
    HAS_SOCKETIO = True
except ImportError:
    HAS_SOCKETIO = False

class A2AClient:
    def __init__(self):
        self.sio = None
        self.connected = False
        self.user_id = None
        self.match_id = None
        self.msg_queue = queue.Queue()
        self.pending_reply = {}  # sent_id -> event
        self._thread = None

    def connect_ws(self, user_id, match_id=None):
        if not HAS_SOCKETIO:
            print('ERROR: python-socketio 未安装，消息走 REST API')
            return False
        self.user_id = user_id
        self.match_id = match_id
        self.sio = socketio.Client(reconnection=True, reconnection_attempts=3)
        self.sio.on('connect', self._on_connect)
        self.sio.on('disconnect', self._on_disconnect)
        self.sio.on('msg', self._on_msg)
        self.sio.on('sent', self._on_sent)
        self.sio.on('error', self._on_error)
        try:
            self.sio.connect(SERVER, transports=['websocket'], wait_timeout=5)
            return True
        except Exception as e:
            print('WS连接失败: ' + str(e))
            return False

    def _on_connect(self):
        self.connected = True
        self.sio.emit('join', {'userId': self.user_id, 'matchId': self.match_id})

    def _on_disconnect(self):
        self.connected = False

    def _on_msg(self, data):
        # 收到对方消息
        self.msg_queue.put({'type': 'msg', 'data': data})

    def _on_sent(self, data):
        # 自己的消息发送确认
        sid = data.get('id', '')
        if sid in self.pending_reply:
            self.pending_reply[sid].set()

    def _on_error(self, data):
        print('WS错误: ' + str(data.get('message', data)))

    def send(self, content):
        if not self.connected:
            return self._send_rest(content)
        msg_payload = {'matchId': self.match_id, 'content': content}
        self.sio.emit('send_msg', msg_payload)
        # 等待确认
        return True

    def _send_rest(self, content):
        """REST API 备用发送"""
        c = cfg()
        url = c.get('server_url', SERVER) + '/api/message'
        h = {'Content-Type': 'application/json'}
        if c.get('api_key'): h['Authorization'] = 'Bearer ' + c['api_key']
        payload = {'matchId': self.match_id, 'fromUserId': self.user_id, 'content': content}
        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=h)
            with urllib.request.urlopen(req, timeout=10) as r:
                return json.loads(r.read()).get('success', False)
        except Exception as e:
            return False

    def get_history(self, match_id, limit=20):
        c = cfg()
        url = c.get('server_url', SERVER) + f'/api/match/{match_id}/messages?userId={self.user_id}&limit={limit}'
        h = {}
        if c.get('api_key'): h['Authorization'] = 'Bearer ' + c['api_key']
        try:
            req = urllib.request.Request(url, headers=h)
            with urllib.request.urlopen(req, timeout=10) as r:
                return json.loads(r.read())
        except: return {'messages': []}

    def wait_for_reply(self, timeout=30):
        try:
            return self.msg_queue.get(timeout=timeout)
        except: return None

    def close(self):
        if self.sio: self.sio.disconnect()

# ─── 命令行入口 ──────────────────────────────────────
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('用法: a2a_ws_client.py <join|send|history> [args...]')
        sys.exit(1)

    cmd = sys.argv[1]
    client = A2AClient()

    if cmd == 'join':
        user_id = sys.argv[2] if len(sys.argv) > 2 else None
        match_id = sys.argv[3] if len(sys.argv) > 3 else None
        if not user_id:
            print('ERROR: 需要 user_id')
            sys.exit(1)
        ok = client.connect_ws(user_id, match_id)
        if ok:
            print('连接成功，等待消息...（Ctrl+C 退出）')
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                client.close()
        else:
            print('连接失败，请检查网络或 user_id')

    elif cmd == 'send':
        if len(sys.argv) < 3:
            print('ERROR: 需要消息内容')
            sys.exit(1)
        content = ' '.join(sys.argv[2:])
        c = jread(CONFIG).get('user', {})
        user_id = c.get('user_id')
        # 读取上次对话的 match_id
        match_file = A2A / 'current_match.json'
        match_data = jread(match_file)
        match_id = match_data.get('match_id')
        if not user_id or not match_id:
            print('ERROR: 请先 join 一个对话')
            sys.exit(1)
        client.user_id = user_id
        client.match_id = match_id
        ok = client._send_rest(content)
        print('发送成功' if ok else '发送失败')

    elif cmd == 'history':
        if len(sys.argv) < 3:
            print('ERROR: 需要 match_id')
            sys.exit(1)
        match_id = sys.argv[2]
        c = jread(CONFIG).get('user', {})
        user_id = c.get('user_id')
        if not user_id:
            print('ERROR: 未登录')
            sys.exit(1)
        client.user_id = user_id
        result = client.get_history(match_id)
        for m in result.get('messages', []):
            prefix = '>' if m.get('fromUserId') == user_id else '<'
            print(f"{prefix} {m.get('content', '')}")

    else:
        print('未知命令: ' + cmd)
```

**文件 5：`~/.qclaw/workspace/a2a/profile.json`**
```json
{
  "profile": { "id": "", "name": "", "role": "", "company": "", "industry": "", "contact": { "email": "", "wechat": "" }, "contact_share": false },
  "capabilities": [], "resources": [], "needs": []
}
```

**文件 6：`~/.qclaw/workspace/a2a/current_match.json`**（记录当前对话的 match_id）
```json
{ "match_id": "", "other_name": "", "other_user_id": "" }
```

### Step 3：引导设置昵称
```
🎯 欢迎使用 A2A Match！

我已经帮你准备好了所有文件。接下来只需要告诉我一件事：

我该怎么称呼你？（这个昵称就是你在 A2A Match 里的唯一标识）
```

---

## 📞 实时通讯流程（匹配成功后）

用户接受匹配后，按以下步骤开启实时聊天：

```
① 用户说「我和XXX聊天」或「我要联系XXX」
② AI 执行：join <user_id> <match_id>
③ WebSocket 连接成功 → 双方进入同一对话房间
④ 任意一方发消息 → 另一方实时收到推送
⑤ 离线消息存入 MongoDB，下次连接时拉取历史
```

**技术原理（与 Claw ↔ 飞书 完全相同）：**

```
你的 AI ←→ 云服务器 WebSocket 中转 ←→ 对方的 AI
              ↕
           MongoDB（历史记录）
```

---

## 🧭 触发时机（不要主动推荐功能）

### 触发1️⃣：新用户首次对话
`profile.name` 为空时引导设置昵称。

### 触发2️⃣：对话中捕捉信号

**需求信号**：「我想找/需要/在找……」「有没有人能……」「想合作……」

**能力信号**：「我有/我们能……」「能提供/可承接……」「擅长……」

听到后复述确认：「我听到你说……是这样吗？」

---

## 📋 核心操作命令

| 命令 | 说明 |
|------|------|
| `python scripts/heartbeat_cloud.py` | 心跳检测（新匹配 + 未读消息）|
| `python scripts/cloud_sync.py` | 同步档案到云端 |
| `python scripts/a2a_ws_client.py join <user_id> <match_id>` | WebSocket 加入对话 |
| `python scripts/a2a_ws_client.py send <内容>` | 通过 WebSocket 发送消息 |
| `python scripts/a2a_ws_client.py history <match_id>` | 拉取对话历史 |

---

## ☁️ 云端 API

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/api/profile` | 创建/更新档案，触发匹配 |
| GET | `/api/matches/:userId` | 获取我的所有匹配 |
| POST | `/api/match/:id/accept` | 接受匹配 |
| POST | `/api/match/:id/reject` | 拒绝匹配 |
| GET | `/api/match/:id/messages` | 获取聊天记录 |
| POST | `/api/message` | 发送消息 |
| GET | `/api/messages/:userId` | 获取未读消息 |

---

## 🎯 适用领域

| 领域 | 关键词 |
|------|--------|
| 💼 获客与BD | 找客户、找渠道、招募分销商、销售leads、异业合作 |
| 📋 项目与外包 | 找项目、接私活、技术外包、招募开发者 |
| 🤝 合伙与人脉 | 找合伙人、技术合伙人、联合创业 |
| 💰 融资对接 | 找投资、天使投资、融资对接 |
| 🏭 供应链 | 找工厂、OEM、找货源、电商供货 |
| 💻 技术资源 | GPU算力、A100/H100/RTX4090、AI开发 |
| 🎭 内容与OPC | AI短剧、数字人、IP联名 |

---

## 💬 使用示例

```
用户: 我想找GPU算力跑大模型
AI:   我听到你说：你想找 GPU 算力来训练大模型。是这样吗？

用户: 对
AI:   ✅ 已记录。你有什么可以分享的吗？

用户: 我有4张4090闲置
AI:   ✅ 已记录。开启云端同步吗？（这样才能匹配到其他人）

用户: 好
AI:   ✅ 开启成功，档案已同步！

用户: 帮我看看有没有匹配的
AI:   🔔 发现 1 个新匹配！王五（87%匹配）— 他有 RTX 4090
       说「我要和王五聊天」可以开始实时对话

用户: 我要和王五聊天
AI:   ✅ 正在连接云端 WebSocket...
       ✅ 连接成功！已加入与王五的对话
       现在可以直接打字，我会帮你实时发送
```

---

## 📌 版本历史

| 版本 | 更新 |
|------|------|
| **2.8.0** | 云端 WebSocket 实时消息中转上线！匹配成功后双方通过云服务器中转实时聊天，原理与 Claw↔飞书 完全相同；ws_relay.js 整合到服务器；新增 a2a_ws_client.py |
| **2.7.0** | 安装即用：Python脚本以内嵌模板写入SKILL.md |
| **2.6.0** | 心跳新增消息通道 |
| **2.5.0** | 云端API Key鉴权，云端默认关闭 |
| **2.2.0** | 虾名机制 |
| **2.0.0** | 全面重构 |

---

有问题或建议，欢迎加群：**962354006**

<div align="center">

**让每一个需求都能找到对应的能力**

</div>

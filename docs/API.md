# A2A 云端 API 设计

## 基础信息

- **Base URL**: `https://a2a.example.com/api/v1`
- **认证方式**: Bearer Token (JWT)
- **数据格式**: JSON

---

## API 端点

### 用户认证

#### 注册
```
POST /auth/register

Request:
{
  "email": "user@example.com",
  "password": "secure_password",
  "name": "张三"
}

Response:
{
  "status": "success",
  "user": {
    "id": "user_xxx",
    "email": "user@example.com",
    "name": "张三"
  },
  "token": "eyJhbGciOiJIUzI1NiIs..."
}
```

#### 登录
```
POST /auth/login

Request:
{
  "email": "user@example.com",
  "password": "secure_password"
}

Response:
{
  "status": "success",
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "expires_at": "2026-04-10T00:00:00Z"
}
```

---

### 档案管理

#### 上传/更新档案
```
POST /profiles

Headers:
  Authorization: Bearer <token>

Request:
{
  "profile": {...},
  "capabilities": [...],
  "resources": [...],
  "needs": [...],
  "business": {...},
  "preferences": {...}
}

Response:
{
  "status": "success",
  "profile_id": "profile_xxx",
  "updated_at": "2026-04-09T00:30:00Z"
}
```

#### 获取档案
```
GET /profiles/me

Headers:
  Authorization: Bearer <token>

Response:
{
  "status": "success",
  "profile": {...}
}
```

#### 获取公开档案
```
GET /profiles/{user_id}

Response:
{
  "status": "success",
  "profile": {...}  // 脱敏后的公开信息
}
```

---

### 匹配服务

#### 请求匹配
```
POST /match

Headers:
  Authorization: Bearer <token>

Request:
{
  "type": "need",  // need | capability | resource
  "query": "GPU算力",
  "filters": {
    "location": "北京",
    "min_score": 0.7
  }
}

Response:
{
  "status": "success",
  "matches": [
    {
      "user_id": "user_yyy",
      "profile": {...},
      "match_score": 0.92,
      "matched_items": [...]
    }
  ],
  "total": 5
}
```

#### 获取匹配通知
```
GET /match/notifications

Headers:
  Authorization: Bearer <token>

Response:
{
  "status": "success",
  "notifications": [
    {
      "id": "notif_xxx",
      "type": "match",
      "from_user": "user_zzz",
      "match_score": 0.95,
      "message": "用户王五需要产品设计咨询",
      "created_at": "2026-04-09T00:25:00Z",
      "read": false
    }
  ]
}
```

---

### 需求广播

#### 广播需求
```
POST /broadcast/need

Headers:
  Authorization: Bearer <token>

Request:
{
  "need_id": "need_001",
  "message": "急需要4090算力训练模型",
  "duration": "7d"  // 广播有效期
}

Response:
{
  "status": "success",
  "broadcast_id": "broadcast_xxx",
  "reach_estimate": 150
}
```

#### 获取广播列表
```
GET /broadcast/needs

Query Params:
  - type: 需求类型过滤
  - location: 地区过滤
  - limit: 返回数量

Response:
{
  "status": "success",
  "broadcasts": [
    {
      "id": "broadcast_xxx",
      "user_id": "user_aaa",
      "need": {...},
      "message": "...",
      "created_at": "..."
    }
  ]
}
```

---

### 联系对接

#### 发起联系请求
```
POST /contact

Headers:
  Authorization: Bearer <token>

Request:
{
  "to_user": "user_yyy",
  "message": "我看到你有4090算力，想聊聊合作",
  "context": {
    "match_id": "match_xxx"
  }
}

Response:
{
  "status": "success",
  "contact_id": "contact_xxx",
  "message": "联系请求已发送"
}
```

#### 获取联系请求
```
GET /contact/requests

Headers:
  Authorization: Bearer <token>

Response:
{
  "status": "success",
  "requests": [
    {
      "id": "contact_xxx",
      "from_user": {...},
      "message": "...",
      "status": "pending",
      "created_at": "..."
    }
  ]
}
```

#### 接受/拒绝联系
```
POST /contact/{contact_id}/respond

Request:
{
  "action": "accept",  // accept | decline
  "message": "好的，我们聊聊"
}

Response:
{
  "status": "success",
  "message": "已接受联系请求"
}
```

---

### 消息中转

#### 发送消息
```
POST /messages

Headers:
  Authorization: Bearer <token>

Request:
{
  "to_user": "user_yyy",
  "content": "你好，想详细了解一下你的算力资源"
}

Response:
{
  "status": "success",
  "message_id": "msg_xxx"
}
```

#### 获取消息
```
GET /messages

Headers:
  Authorization: Bearer <token>

Query Params:
  - with_user: 对方用户ID
  - limit: 消息数量

Response:
{
  "status": "success",
  "messages": [
    {
      "id": "msg_xxx",
      "from": "user_yyy",
      "to": "user_me",
      "content": "...",
      "created_at": "..."
    }
  ]
}
```

---

### Webhook 订阅

#### 注册 Webhook
```
POST /webhooks

Headers:
  Authorization: Bearer <token>

Request:
{
  "url": "https://your-server.com/webhook",
  "events": ["match", "contact", "message"],
  "secret": "your_webhook_secret"
}

Response:
{
  "status": "success",
  "webhook_id": "wh_xxx"
}
```

#### Webhook 事件格式
```
POST https://your-server.com/webhook

Headers:
  X-Signature: sha256=...

Body:
{
  "event": "match",
  "data": {
    "match_id": "match_xxx",
    "from_user": {...},
    "match_score": 0.92,
    "message": "..."
  },
  "timestamp": "2026-04-09T00:30:00Z"
}
```

---

## 数据模型

### 用户
```typescript
interface User {
  id: string;
  email: string;
  name: string;
  created_at: string;
  updated_at: string;
}
```

### 档案
```typescript
interface Profile {
  id: string;
  user_id: string;
  version: string;
  profile: ProfileInfo;
  capabilities: Capability[];
  resources: Resource[];
  needs: Need[];
  business: BusinessInfo;
  preferences: Preferences;
  created_at: string;
  updated_at: string;
}
```

### 匹配
```typescript
interface Match {
  id: string;
  user_a: string;
  user_b: string;
  score: number;
  matched_items: MatchItem[];
  status: 'active' | 'expired' | 'completed';
  created_at: string;
}
```

---

## 错误响应

```json
{
  "status": "error",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid email format"
  }
}
```

---

## 速率限制

| 端点类型 | 限制 |
|---------|------|
| 认证 | 10次/分钟 |
| 匹配 | 30次/分钟 |
| 消息 | 100次/分钟 |
| 其他 | 60次/分钟 |

---

## 部署建议

### 技术栈
- **API 框架**: Node.js (Express/Fastify) 或 Python (FastAPI)
- **数据库**: MongoDB 或 PostgreSQL
- **消息队列**: Redis 或 RabbitMQ
- **缓存**: Redis
- **部署**: Vercel / Railway / AWS Lambda

### MVP 功能
1. 用户注册/登录
2. 档案上传/同步
3. 基础匹配
4. 通知推送

### 后续功能
1. Webhook 集成
2. 消息中转
3. 高级匹配算法
4. 数据分析面板

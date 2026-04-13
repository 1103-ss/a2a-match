// A2A Match 服务器增强版 v2.1.0
// 添加：API Key 鉴权 / 自动匹配算法 / WebSocket 通知 / 匹配内即时消息

const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const mongoose = require('mongoose');
const cors = require('cors');
const { v4: uuidv4 } = require('uuid');
const winston = require('winston');

const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(winston.format.timestamp(), winston.format.json()),
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: 'logs/error.log', level: 'error' }),
    new winston.transports.File({ filename: 'logs/combined.log' })
  ]
});

const app = express();
const server = http.createServer(app);
const io = new Server(server, { cors: { origin: "*", methods: ["GET", "POST"] } });

// ==================== API Key 鉴权 ====================
const API_KEY = process.env.A2A_API_KEY || '';
const AUTH_MODE = API_KEY.length > 0;

// API Key 中间件（仅在配置了 A2A_API_KEY 时启用）
function requireAuth(req, res, next) {
  if (!AUTH_MODE) return next(); // 未配置 Key 时跳过鉴权（开发模式）

  const authHeader = req.headers['authorization'] || req.headers['authorization'];
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({ error: '未提供 API Key，请联系管理员获取。', docs: '/api/info' });
  }

  const token = authHeader.slice(7);
  if (token !== API_KEY) {
    return res.status(403).json({ error: 'API Key 无效' });
  }

  next();
}

// ==================== MongoDB ====================
const MONGODB_URI = process.env.MONGODB_URI || 'mongodb://localhost:27017/a2a_match';

mongoose.connect(MONGODB_URI).then(() => {
  logger.info('MongoDB 连接成功');
}).catch(err => {
  logger.error('MongoDB 连接失败:', err);
});

app.use(cors());
app.use(express.json());

// ==================== 数据模型 ====================
const profileSchema = new mongoose.Schema({
  userId: { type: String, required: true, unique: true },
  name: String,
  email: String,
  tags: [String],
  resources: [String],
  needs: [String],
  createdAt: { type: Date, default: Date.now },
  updatedAt: { type: Date, default: Date.now }
});

const matchSchema = new mongoose.Schema({
  userId1: String,
  userId2: String,
  matchScore: Number,
  matchDetails: String,
  status: { type: String, enum: ['pending', 'accepted', 'rejected'], default: 'pending' },
  acceptedBy: String,
  blockedBy: String,
  createdAt: { type: Date, default: Date.now }
});

const messageSchema = new mongoose.Schema({
  matchId: { type: mongoose.Schema.Types.ObjectId, ref: 'Match', required: true },
  fromUserId: { type: String, required: true },
  toUserId: { type: String, required: true },
  content: { type: String, required: true, maxlength: 2000 },
  read: { type: Boolean, default: false },
  readAt: Date,
  createdAt: { type: Date, default: Date.now, index: true }
});

const Profile = mongoose.model('Profile', profileSchema);
const Match = mongoose.model('Match', matchSchema);
const Message = mongoose.model('Message', messageSchema);

// ==================== 匹配算法 ====================
function calculateMatchScore(profile1, profile2) {
  const needs1 = profile1.needs || [];
  const needs2 = profile2.needs || [];
  const resources1 = profile1.resources || [];
  const resources2 = profile2.resources || [];
  const tags1 = profile1.tags || [];
  const tags2 = profile2.tags || [];

  let score = 0;
  let details = [];

  // 1. 需求-资源匹配 (权重 50%)
  for (const need of needs1) {
    const needLower = need.toLowerCase();
    for (const resource of resources2) {
      const resourceLower = resource.toLowerCase();
      if (resourceLower.includes(needLower) || needLower.includes(resourceLower)) {
        score += 0.5;
        details.push(`"${need}" 匹配到 "${resource}"`);
      }
    }
  }

  // 2. 资源-需求匹配 (权重 50%)
  for (const resource of resources1) {
    const resourceLower = resource.toLowerCase();
    for (const need of needs2) {
      const needLower = need.toLowerCase();
      if (needLower.includes(resourceLower) || resourceLower.includes(needLower)) {
        score += 0.5;
        details.push(`"${resource}" 匹配到 "${need}" 的需求`);
      }
    }
  }

  // 3. 标签匹配 (权重 20%)
  const commonTags = tags1.filter(tag => tags2.includes(tag));
  score += commonTags.length * 0.2;
  if (commonTags.length > 0) {
    details.push(`共同标签: ${commonTags.join(', ')}`);
  }

  // 归一化 (最高1.0)
  score = Math.min(score, 1.0);
  return { score: Math.round(score * 100) / 100, details: details.slice(0, 3) };
}

async function findMatchesForProfile(profile) {
  const allProfiles = await Profile.find({ userId: { $ne: profile.userId } });
  const matches = [];

  for (const other of allProfiles) {
    const { score, details } = calculateMatchScore(profile, other);
    if (score >= 0.3) {
      const existing = await Match.findOne({
        $or: [
          { userId1: profile.userId, userId2: other.userId },
          { userId1: other.userId, userId2: profile.userId }
        ]
      });
      if (!existing) {
        const match = await Match.create({
          userId1: profile.userId,
          userId2: other.userId,
          matchScore: score,
          matchDetails: details.join('; ')
        });
        matches.push(match);
      }
    }
  }
  return matches;
}

// ==================== API 路由（全部需要鉴权）====================
app.get('/health', (req, res) => {
  res.json({
    status: 'UP',
    timestamp: new Date().toISOString(),
    version: '2.1.0',
    auth: AUTH_MODE ? '🔐 加密模式' : '🔓 开放模式（开发测试）'
  });
});

app.get('/api/info', requireAuth, (req, res) => {
  res.json({
    service: 'A2A Match - 智能供需匹配平台 v2.1.0',
    authMode: AUTH_MODE ? '🔐 API Key 鉴权' : '🔓 开放模式（开发测试）',
    description: '零配置智能供需匹配 + 自动匹配算法 + WebSocket 实时通知',
    authRequired: AUTH_MODE,
    endpoints: [
      'GET  /health',
      'GET  /api/info',
      'GET  /api/stats       [需鉴权]',
      'POST /api/profile     [需鉴权] - 创建/更新档案并自动匹配',
      'GET  /api/profile/:userId  [需鉴权]',
      'GET  /api/matches/:userId  [需鉴权]',
      'POST /api/match/:id/accept  [需鉴权]',
      'POST /api/match/:id/reject  [需鉴权]',
      'POST /api/match/:id/block   [需鉴权] - 屏蔽对方',
      'GET  /api/match/:id/contact [需鉴权]',
      'GET  /api/match/:id/messages [需鉴权] - 聊天记录',
      'POST /api/message     [需鉴权] - 发送消息',
      'GET  /api/messages/:userId  [需鉴权] - 获取消息(unread=true仅未读)',
      'POST /api/messages/read [需鉴权] - 标记已读',
      'GET  /api/profiles     [需鉴权]',
      'DELETE /api/profile/:userId [需鉴权]'
    ],
    websocketEvents: ['join', 'new_matches', 'match_accepted', 'new_message'],
    setup: AUTH_MODE ? '已配置 API Key，请使用 Authorization: Bearer <key>' : '未配置 API Key（开发模式），生产环境请设置 A2A_API_KEY 环境变量'
  });
});

app.get('/api/stats', requireAuth, async (req, res) => {
  try {
    const [profileCount, matchCount] = await Promise.all([
      Profile.countDocuments(),
      Match.countDocuments()
    ]);
    res.json({
      profiles: profileCount,
      matches: matchCount,
      activeMatches: await Match.countDocuments({ status: 'pending' }),
      acceptedMatches: await Match.countDocuments({ status: 'accepted' }),
      authMode: AUTH_MODE ? '🔐' : '🔓'
    });
  } catch (err) {
    res.status(500).json({ error: '获取统计失败' });
  }
});

app.post('/api/profile', requireAuth, async (req, res) => {
  try {
    const { userId, name, email, tags = [], resources = [], needs = [] } = req.body;

    if (!userId) {
      return res.status(400).json({ error: 'userId 是必需的' });
    }

    const profile = await Profile.findOneAndUpdate(
      { userId },
      { name, email, tags, resources, needs, updatedAt: new Date() },
      { upsert: true, new: true, setDefaultsOnInsert: true }
    );

    logger.info(`档案更新: ${userId}`);

    const newMatches = await findMatchesForProfile(profile);

    if (newMatches.length > 0) {
      io.emit('new_matches', { userId, matches: newMatches });
      logger.info(`为用户 ${userId} 创建了 ${newMatches.length} 个新匹配`);
    }

    res.json({
      ...profile.toObject(),
      matchesFound: newMatches.length
    });

  } catch (err) {
    logger.error('创建档案失败:', err);
    res.status(500).json({ error: '创建档案失败' });
  }
});

app.get('/api/profile/:userId', requireAuth, async (req, res) => {
  try {
    const profile = await Profile.findOne({ userId: req.params.userId });
    if (!profile) {
      return res.status(404).json({ error: '档案不存在' });
    }
    res.json(profile);
  } catch (err) {
    res.status(500).json({ error: '获取档案失败' });
  }
});

app.get('/api/matches/:userId', requireAuth, async (req, res) => {
  try {
    const matches = await Match.find({
      $or: [{ userId1: req.params.userId }, { userId2: req.params.userId }]
    }).sort({ matchScore: -1 });

    const enrichedMatches = await Promise.all(matches.map(async (m) => {
      const otherUserId = m.userId1 === req.params.userId ? m.userId2 : m.userId1;
      const otherProfile = await Profile.findOne({ userId: otherUserId });
      return {
        id: m._id,
        score: m.matchScore,
        details: m.matchDetails,
        status: m.status,
        otherUser: otherProfile ? { userId: otherProfile.userId, name: otherProfile.name } : { userId: otherUserId }
      };
    }));

    res.json(enrichedMatches);
  } catch (err) {
    res.status(500).json({ error: '获取匹配列表失败' });
  }
});

app.post('/api/match/:id/accept', requireAuth, async (req, res) => {
  try {
    const match = await Match.findById(req.params.id);
    if (!match) {
      return res.status(404).json({ error: '匹配不存在' });
    }

    // 检查是否已有另一方接受了
    const otherAccepted = match.acceptedBy && match.acceptedBy !== req.body.userId;

    // 记录接受方
    if (!match.acceptedBy) {
      match.acceptedBy = req.body.userId;
    }

    // 判断是否双向接受
    if (otherAccepted) {
      match.status = 'accepted';
      // 触发 contact exchange
      io.emit('match_accepted', {
        matchId: req.params.id,
        match: await match.save()
      });
    } else {
      await match.save();
    }

    const updated = await Match.findById(req.params.id);

    // 返回结果，附带是否双向接受
    res.json({
      ...updated.toObject(),
      mutualAccepted: otherAccepted || (match.acceptedBy && match.acceptedBy === req.body.userId && updated.status === 'accepted'),
      waitingForOther: !otherAccepted && updated.status === 'pending'
    });

  } catch (err) {
    res.status(500).json({ error: '接受匹配失败' });
  }
});

app.post('/api/match/:id/reject', requireAuth, async (req, res) => {
  try {
    const match = await Match.findByIdAndUpdate(
      req.params.id, { status: 'rejected' }, { new: true }
    );
    if (!match) {
      return res.status(404).json({ error: '匹配不存在' });
    }
    res.json(match);
  } catch (err) {
    res.status(500).json({ error: '拒绝匹配失败' });
  }
});

// 互换联系方式（双方都接受后可用）
app.get('/api/match/:id/contact', requireAuth, async (req, res) => {
  try {
    const match = await Match.findById(req.params.id);
    if (!match) {
      return res.status(404).json({ error: '匹配不存在' });
    }
    if (match.status !== 'accepted') {
      return res.status(400).json({ error: '双方尚未互相接受，无法获取联系方式' });
    }

    const userId1 = match.userId1;
    const userId2 = match.userId2;

    const [profile1, profile2] = await Promise.all([
      Profile.findOne({ userId: userId1 }),
      Profile.findOne({ userId: userId2 })
    ]);

    // 只有标记了 contact_share 的才返回完整联系方式
    const formatContact = (p, isSelf) => ({
      userId: p.userId,
      name: p.name,
      role: p.role || '',
      industry: p.industry || '',
      contact: isSelf ? p.contact : (p.contact_share ? p.contact : { preferred: 'email' })
    });

    res.json({
      status: 'success',
      mutualAccepted: true,
      contact: {
        user1: profile1 ? formatContact(profile1, req.headers['x-user-id'] === userId1) : null,
        user2: profile2 ? formatContact(profile2, req.headers['x-user-id'] === userId2) : null
      }
    });

  } catch (err) {
    res.status(500).json({ error: '获取联系方式失败' });
  }
});

// 更新档案时附带联系方式设置
app.patch('/api/profile/:userId/contact', requireAuth, async (req, res) => {
  try {
    const { contact, contact_share } = req.body;
    const update = {};
    if (contact) update['contact'] = contact;
    if (typeof contact_share === 'boolean') update['contact_share'] = contact_share;

    const profile = await Profile.findOneAndUpdate(
      { userId: req.params.userId },
      update,
      { new: true }
    );
    if (!profile) {
      return res.status(404).json({ error: '档案不存在' });
    }
    res.json({ status: 'success', profile });
  } catch (err) {
    res.status(500).json({ error: '更新联系方式失败' });
  }
});

// ==================== 即时消息系统 ====================

// 发送消息（仅允许已匹配双方，且未被拉黑）
app.post('/api/message', requireAuth, async (req, res) => {
  try {
    const { matchId, fromUserId, toUserId, content } = req.body;

    if (!matchId || !fromUserId || !toUserId || !content || !content.trim()) {
      return res.status(400).json({ error: 'matchId, fromUserId, toUserId, content 都是必需的' });
    }

    if (content.length > 2000) {
      return res.status(400).json({ error: '消息内容不能超过 2000 字' });
    }

    // 校验匹配存在且双方都在其中
    const match = await Match.findById(matchId);
    if (!match) {
      return res.status(404).json({ error: '匹配不存在' });
    }

    const userIds = [match.userId1, match.userId2];
    if (!userIds.includes(fromUserId) || !userIds.includes(toUserId)) {
      return res.status(403).json({ error: '你不是这个匹配的参与者' });
    }

    // 校验未被拉黑
    if (match.blockedBy === fromUserId) {
      return res.status(403).json({ error: '你已被对方屏蔽' });
    }

    // 校验状态：pending(已双向接受) 或 accepted
    if (match.status === 'rejected') {
      return res.status(403).json({ error: '匹配已拒绝，无法发送消息' });
    }

    // 创建消息
    const message = await Message.create({ matchId, fromUserId, toUserId, content: content.trim() });

    // WebSocket 实时推送
    io.to(toUserId).emit('new_message', {
      messageId: message._id,
      matchId: matchId,
      fromUserId: fromUserId,
      content: content.trim(),
      createdAt: message.createdAt
    });

    logger.info(`消息: ${fromUserId} → ${toUserId} (match: ${matchId})`);

    res.json({ success: true, messageId: message._id });

  } catch (err) {
    logger.error('发送消息失败:', err);
    res.status(500).json({ error: '发送消息失败' });
  }
});

// 获取未读消息
app.get('/api/messages/:userId', requireAuth, async (req, res) => {
  try {
    const userId = req.params.userId;
    const unreadOnly = req.query.unread === 'true';

    const query = { toUserId: userId };
    if (unreadOnly) {
      query.read = false;
    }

    const messages = await Message.find(query)
      .sort({ createdAt: -1 })
      .limit(50)
      .populate('matchId');

    const enriched = await Promise.all(messages.map(async (msg) => {
      const sender = await Profile.findOne({ userId: msg.fromUserId });
      return {
        messageId: msg._id,
        matchId: msg.matchId,
        fromUser: sender ? { userId: sender.userId, name: sender.name } : { userId: msg.fromUserId, name: '未知' },
        content: msg.content,
        read: msg.read,
        createdAt: msg.createdAt
      };
    }));

    const unreadCount = await Message.countDocuments({ toUserId: userId, read: false });

    res.json({ messages: enriched, unreadCount });

  } catch (err) {
    res.status(500).json({ error: '获取消息失败' });
  }
});

// 标记消息已读
app.post('/api/messages/read', requireAuth, async (req, res) => {
  try {
    const { userId, messageIds } = req.body;
    if (!userId || !messageIds || !Array.isArray(messageIds)) {
      return res.status(400).json({ error: 'userId 和 messageIds (数组) 是必需的' });
    }

    await Message.updateMany(
      { _id: { $in: messageIds }, toUserId: userId },
      { read: true, readAt: new Date() }
    );

    res.json({ success: true, markedRead: messageIds.length });
  } catch (err) {
    res.status(500).json({ error: '标记已读失败' });
  }
});

// 拉黑对方（不再接收消息）
app.post('/api/match/:id/block', requireAuth, async (req, res) => {
  try {
    const match = await Match.findByIdAndUpdate(
      req.params.id,
      { blockedBy: req.body.userId },
      { new: true }
    );
    if (!match) return res.status(404).json({ error: '匹配不存在' });
    res.json({ success: true, message: '已屏蔽对方' });
  } catch (err) {
    res.status(500).json({ error: '屏蔽失败' });
  }
});

// 获取某个匹配的聊天记录
app.get('/api/match/:id/messages', requireAuth, async (req, res) => {
  try {
    const userId = req.query.userId;
    if (!userId) return res.status(400).json({ error: 'userId 是必需的' });

    const match = await Match.findById(req.params.id);
    if (!match) return res.status(404).json({ error: '匹配不存在' });

    const userIds = [match.userId1, match.userId2];
    if (!userIds.includes(userId)) {
      return res.status(403).json({ error: '你不是这个匹配的参与者' });
    }

    const messages = await Message.find({ matchId: req.params.id })
      .sort({ createdAt: 1 })
      .limit(100);

    // 标记为已读
    await Message.updateMany(
      { matchId: req.params.id, toUserId: userId, read: false },
      { read: true, readAt: new Date() }
    );

    const otherUserId = match.userId1 === userId ? match.userId2 : match.userId1;
    const otherProfile = await Profile.findOne({ userId: otherUserId });

    res.json({
      matchUser: otherProfile ? { userId: otherProfile.userId, name: otherProfile.name } : { userId: otherUserId },
      messages: messages.map(m => ({
        messageId: m._id,
        fromUserId: m.fromUserId,
        toUserId: m.toUserId,
        content: m.content,
        createdAt: m.createdAt
      })),
      blocked: match.blockedBy === userId
    });
  } catch (err) {
    res.status(500).json({ error: '获取聊天记录失败' });
  }
});

app.get('/api/profiles', requireAuth, async (req, res) => {
  try {
    const profiles = await Profile.find().sort({ createdAt: -1 });
    res.json(profiles);
  } catch (err) {
    res.status(500).json({ error: '获取所有档案失败' });
  }
});

app.delete('/api/profile/:userId', requireAuth, async (req, res) => {
  try {
    await Profile.deleteOne({ userId: req.params.userId });
    await Match.deleteMany({ $or: [{ userId1: req.params.userId }, { userId2: req.params.userId }] });
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: '删除档案失败' });
  }
});

// ==================== WebSocket ====================
io.on('connection', (socket) => {
  logger.info('WebSocket 连接:', socket.id);

  socket.on('join', (userId) => {
    socket.join(userId);
    logger.info(`用户 ${userId} 加入`);
  });

  socket.on('disconnect', () => {
    logger.info('WebSocket 断开:', socket.id);
  });
});

// ==================== 启动 ====================
const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
  logger.info(`========================================`);
  logger.info(`A2A Match 服务器 v2.1.0 启动!`);
  logger.info(`端口: ${PORT}`);
  logger.info(`鉴权模式: ${AUTH_MODE ? '🔐 API Key（生产）' : '🔓 开放（开发测试）'}`);
  logger.info(`========================================`);
});

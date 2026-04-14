/**
 * A2A Match 服务器 v2.6.0
 * 
 * 更新：
 * - WebSocket 实时消息中转（ws_relay 集成）
 * - 统一消息事件：msg（收到）/ sent（发送确认）/ unread（未读数）
 * - match 房间机制：双方 join m:<matchId> 即可双向收发
 * - 历史消息通过 REST API 获取
 */

const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const mongoose = require('mongoose');
const cors = require('cors');
const { v4: uuidv4 } = require('uuid');
const winston = require('winston');
const wsRelay = require('./ws_relay');

const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(winston.format.timestamp(), winston.format.json()),
  transports: [
    new winston.transports.Console({ format: winston.format.simple() }),
    new winston.transports.File({ filename: 'logs/error.log', level: 'error' }),
    new winston.transports.File({ filename: 'logs/combined.log' })
  ]
});

const app = express();
const server = http.createServer(app);
const io = new Server(server, {
  cors: { origin: '*', methods: ['GET', 'POST'] },
  pingTimeout: 60000,
  pingInterval: 25000
});

// ==================== API Key 鉴权 ====================
const API_KEY = process.env.A2A_API_KEY || '';
const AUTH_MODE = API_KEY.length > 0;

function requireAuth(req, res, next) {
  if (!AUTH_MODE) return next();
  const authHeader = req.headers['authorization'] || req.headers['Authorization'];
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({ error: '未提供 API Key', docs: '/api/info' });
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
  logger.info('MongoDB 连接成功: ' + MONGODB_URI);
}).catch(err => {
  logger.error('MongoDB 连接失败:', err.message);
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
  matchId: { type: mongoose.Schema.Types.ObjectId, ref: 'Match' },
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
function calculateMatchScore(p1, p2) {
  const needs1 = p1.needs || [];
  const needs2 = p2.needs || [];
  const res1 = p1.resources || [];
  const res2 = p2.resources || [];
  const tags1 = p1.tags || [];
  const tags2 = p2.tags || [];

  let score = 0;
  const details = [];

  for (const n of needs1) {
    const nl = n.toLowerCase();
    for (const r of res2) {
      const rl = r.toLowerCase();
      if (rl.includes(nl) || nl.includes(rl)) { score += 0.5; details.push(`"${n}"匹配"${r}"`); }
    }
  }
  for (const r of res1) {
    const rl = r.toLowerCase();
    for (const n of needs2) {
      const nl = n.toLowerCase();
      if (nl.includes(rl) || rl.includes(nl)) { score += 0.5; details.push(`"${r}"匹配"${n}"的需求`); }
    }
  }
  const common = tags1.filter(t => tags2.includes(t));
  score += common.length * 0.2;
  if (common.length > 0) details.push('共同标签:' + common.join(','));

  return { score: Math.min(score, 1.0), details: details.slice(0, 3) };
}

async function findMatchesForProfile(profile) {
  const all = await Profile.find({ userId: { $ne: profile.userId } });
  const matches = [];
  for (const other of all) {
    const { score, details } = calculateMatchScore(profile, other);
    if (score >= 0.3) {
      const ex = await Match.findOne({
        $or: [
          { userId1: profile.userId, userId2: other.userId },
          { userId1: other.userId, userId2: profile.userId }
        ]
      });
      if (!ex) {
        matches.push(await Match.create({
          userId1: profile.userId, userId2: other.userId,
          matchScore: score, matchDetails: details.join('; ')
        }));
      }
    }
  }
  return matches;
}

// ==================== API 路由 ====================
app.get('/health', (req, res) => {
  res.json({
    status: 'UP', timestamp: new Date().toISOString(),
    version: '2.6.0', auth: AUTH_MODE ? '🔐' : '🔓',
    ws: 'wss://81.70.250.9:3000'
  });
});

app.get('/api/info', requireAuth, (req, res) => {
  res.json({
    service: 'A2A Match v2.6.0',
    authMode: AUTH_MODE ? '🔐' : '🔓',
    wsEndpoint: 'ws://81.70.250.9:3000',
    wsEvents: {
      clientSend: ['join', 'join_match', 'send_msg', 'get_history', 'mark_read'],
      serverSend: ['msg', 'sent', 'history', 'joined', 'unread', 'error', 'peer_online', 'peer_offline']
    },
    restEndpoints: [
      'POST /api/profile', 'GET  /api/profile/:userId',
      'GET  /api/matches/:userId', 'POST /api/match/:id/accept',
      'POST /api/match/:id/reject', 'GET  /api/match/:id/messages',
      'GET  /api/match/:id/contact', 'POST /api/message',
      'GET  /api/messages/:userId', 'POST /api/messages/read'
    ]
  });
});

app.get('/api/stats', requireAuth, async (req, res) => {
  try {
    res.json({
      profiles: await Profile.countDocuments(),
      matches: await Match.countDocuments(),
      active: await Match.countDocuments({ status: 'pending' }),
      accepted: await Match.countDocuments({ status: 'accepted' }),
      wsOnline: Object.keys(io.sockets?.sockets || {}).length
    });
  } catch (err) { res.status(500).json({ error: err.message }); }
});

app.post('/api/profile', requireAuth, async (req, res) => {
  try {
    const { userId, name, email, tags = [], resources = [], needs = [] } = req.body;
    if (!userId) return res.status(400).json({ error: 'userId 必填' });
    if (!name?.trim()) return res.status(400).json({ error: 'name（昵称）必填' });

    const profile = await Profile.findOneAndUpdate(
      { userId }, { name, email, tags, resources, needs, updatedAt: new Date() },
      { upsert: true, new: true }
    );

    const newMatches = await findMatchesForProfile(profile);
    if (newMatches.length > 0) {
      // 通知所有连接的客户端
      io.emit('new_matches', { userId, count: newMatches.length });
      logger.info(`用户 ${userId} 新增 ${newMatches.length} 个匹配`);
    }

    res.json({ ...profile.toObject(), matchesFound: newMatches.length });
  } catch (err) { res.status(500).json({ error: err.message }); }
});

app.get('/api/profile/:userId', requireAuth, async (req, res) => {
  try {
    const p = await Profile.findOne({ userId: req.params.userId });
    if (!p) return res.status(404).json({ error: '档案不存在' });
    res.json(p);
  } catch (err) { res.status(500).json({ error: err.message }); }
});

app.get('/api/matches/:userId', requireAuth, async (req, res) => {
  try {
    const matches = await Match.find({
      $or: [{ userId1: req.params.userId }, { userId2: req.params.userId }]
    }).sort({ matchScore: -1 });

    const enriched = await Promise.all(matches.map(async (m) => {
      const otherId = m.userId1 === req.params.userId ? m.userId2 : m.userId1;
      const other = await Profile.findOne({ userId: otherId });
      return {
        id: m._id, score: m.matchScore, details: m.matchDetails,
        status: m.status, acceptedBy: m.acceptedBy,
        otherUser: other ? { userId: other.userId, name: other.name } : { userId: otherId }
      };
    }));
    res.json(enriched);
  } catch (err) { res.status(500).json({ error: err.message }); }
});

app.post('/api/match/:id/accept', requireAuth, async (req, res) => {
  try {
    const match = await Match.findById(req.params.id);
    if (!match) return res.status(404).json({ error: '匹配不存在' });

    const otherId = match.userId1 === req.body.userId ? match.userId2 : match.userId1;
    const otherAccepted = match.acceptedBy && match.acceptedBy !== req.body.userId;

    if (!match.acceptedBy) match.acceptedBy = req.body.userId;

    if (otherAccepted) {
      match.status = 'accepted';
      await match.save();
      // 双向接受成功，通知双方
      io.to('u:' + match.userId1).emit('match_accepted', { matchId: req.params.id });
      io.to('u:' + match.userId2).emit('match_accepted', { matchId: req.params.id });
    } else {
      await match.save();
      // 通知另一方有人接受了
      io.to('u:' + otherId).emit('match_accepted_partial', {
        matchId: req.params.id, by: req.body.userId
      });
    }

    res.json({ ...match.toObject(), mutualAccepted: otherAccepted || match.status === 'accepted' });
  } catch (err) { res.status(500).json({ error: err.message }); }
});

app.post('/api/match/:id/reject', requireAuth, async (req, res) => {
  try {
    const match = await Match.findByIdAndUpdate(req.params.id, { status: 'rejected' }, { new: true });
    if (!match) return res.status(404).json({ error: '匹配不存在' });
    res.json(match);
  } catch (err) { res.status(500).json({ error: err.message }); }
});

app.get('/api/match/:id/contact', requireAuth, async (req, res) => {
  try {
    const match = await Match.findById(req.params.id);
    if (!match) return res.status(404).json({ error: '匹配不存在' });
    if (match.status !== 'accepted') return res.status(400).json({ error: '双方尚未互相接受' });
    const [p1, p2] = await Promise.all([
      Profile.findOne({ userId: match.userId1 }),
      Profile.findOne({ userId: match.userId2 })
    ]);
    const self = req.headers['x-user-id'];
    res.json({
      user1: p1 ? { userId: p1.userId, name: p1.name, role: p1.role || '', contact: self === p1.userId ? p1.contact || {} : {} } : null,
      user2: p2 ? { userId: p2.userId, name: p2.name, role: p2.role || '', contact: self === p2.userId ? p2.contact || {} : {} } : null
    });
  } catch (err) { res.status(500).json({ error: err.message }); }
});

app.get('/api/match/:id/messages', requireAuth, async (req, res) => {
  try {
    const { userId } = req.query;
    if (!userId) return res.status(400).json({ error: 'userId 必填' });

    const match = await Match.findById(req.params.id);
    if (!match) return res.status(404).json({ error: '匹配不存在' });
    if (![match.userId1, match.userId2].includes(userId)) return res.status(403).json({ error: '无权访问' });

    const msgs = await Message.find({ matchId: req.params.id }).sort({ createdAt: 1 }).limit(100);
    await Message.updateMany({ matchId: req.params.id, toUserId: userId, read: false }, { read: true });

    const otherId = match.userId1 === userId ? match.userId2 : match.userId1;
    const other = await Profile.findOne({ userId: otherId });

    res.json({
      matchUser: other ? { userId: other.userId, name: other.name } : { userId: otherId },
      messages: msgs.map(m => ({
        id: m._id.toString(), fromUserId: m.fromUserId, toUserId: m.toUserId,
        content: m.content, read: m.read, createdAt: m.createdAt
      }))
    });
  } catch (err) { res.status(500).json({ error: err.message }); }
});

// ─── 发送消息（核心，修复路由）────────────────────────
app.post('/api/message', requireAuth, async (req, res) => {
  try {
    const { matchId, fromUserId, toUserId, content } = req.body;
    if (!matchId || !fromUserId || !content?.trim()) {
      return res.status(400).json({ error: 'matchId, fromUserId, content 必填' });
    }
    if (content.length > 2000) return res.status(400).json({ error: '消息不能超过2000字' });

    const match = await Match.findById(matchId);
    if (!match) return res.status(404).json({ error: '匹配不存在' });
    if (![match.userId1, match.userId2].includes(fromUserId)) return res.status(403).json({ error: '你不是参与者' });
    if (match.status === 'rejected') return res.status(403).json({ error: '匹配已拒绝' });
    if (match.blockedBy === toUserId) return res.status(403).json({ error: '你已被屏蔽' });

    // 确定接收方
    const receiverId = toUserId || ([match.userId1, match.userId2].find(id => id !== fromUserId));

    const msg = await Message.create({ matchId, fromUserId, toUserId: receiverId, content: content.trim() });

    // ── WebSocket 实时推送 ──
    const msgPayload = {
      id: msg._id.toString(), matchId, fromUserId,
      toUserId: receiverId, content: content.trim(),
      createdAt: msg.createdAt.toISOString()
    };

    // 发给发送者（确认）
    io.to('u:' + fromUserId).emit('sent', msgPayload);

    // 发给接收者（新消息）
    io.to('u:' + receiverId).emit('msg', msgPayload);

    logger.info(`[MSG] ${fromUserId} → ${receiverId} (match:${matchId})`);
    res.json({ success: true, messageId: msg._id.toString() });

  } catch (err) { res.status(500).json({ error: err.message }); }
});

app.get('/api/messages/:userId', requireAuth, async (req, res) => {
  try {
    const query = { toUserId: req.params.userId };
    if (req.query.unread === 'true') query.read = false;
    const msgs = await Message.find(query).sort({ createdAt: -1 }).limit(50);
    const unread = await Message.countDocuments({ toUserId: req.params.userId, read: false });
    const enriched = await Promise.all(msgs.map(async (m) => {
      const s = await Profile.findOne({ userId: m.fromUserId });
      return {
        messageId: m._id, matchId: m.matchId,
        from: s ? { userId: s.userId, name: s.name } : { userId: m.fromUserId },
        content: m.content, read: m.read, createdAt: m.createdAt
      };
    }));
    res.json({ messages: enriched, unread });
  } catch (err) { res.status(500).json({ error: err.message }); }
});

app.post('/api/messages/read', requireAuth, async (req, res) => {
  try {
    const { userId, matchId } = req.body;
    if (!userId || !matchId) return res.status(400).json({ error: 'userId 和 matchId 必填' });
    const result = await Message.updateMany(
      { matchId, toUserId: userId, read: false },
      { read: true, readAt: new Date() }
    );
    res.json({ success: true, marked: result.modifiedCount });
  } catch (err) { res.status(500).json({ error: err.message }); }
});

app.post('/api/match/:id/block', requireAuth, async (req, res) => {
  try {
    const match = await Match.findByIdAndUpdate(req.params.id, { blockedBy: req.body.userId }, { new: true });
    if (!match) return res.status(404).json({ error: '匹配不存在' });
    res.json({ success: true });
  } catch (err) { res.status(500).json({ error: err.message }); }
});

app.delete('/api/profile/:userId', requireAuth, async (req, res) => {
  try {
    await Profile.deleteOne({ userId: req.params.userId });
    await Match.deleteMany({ $or: [{ userId1: req.params.userId }, { userId2: req.params.userId }] });
    res.json({ success: true });
  } catch (err) { res.status(500).json({ error: err.message }); }
});

// ==================== WebSocket（ws_relay 集成）============
wsRelay.init(io, logger, 'http://81.70.250.9:3000');

io.on('connection', (socket) => {
  logger.info('[WS] 连接: ' + socket.id);

  // ws_relay 处理所有 WebSocket 事件
  wsRelay.registerHandlers(socket);

  socket.on('disconnect', () => {
    logger.info('[WS] 断开: ' + socket.id);
  });
});

// ==================== 启动 ====================
const PORT = process.env.PORT || 3000;
server.listen(PORT, '0.0.0.0', () => {
  logger.info('========================================');
  logger.info(`A2A Match 服务器 v2.6.0 启动！`);
  logger.info(`端口: ${PORT}`);
  logger.info(`鉴权: ${AUTH_MODE ? '🔐 API Key' : '🔓 开放（开发测试）'}`);
  logger.info(`MongoDB: ${MONGODB_URI}`);
  logger.info(`WebSocket: ws://81.70.250.9:${PORT}`);
  logger.info('========================================');
});

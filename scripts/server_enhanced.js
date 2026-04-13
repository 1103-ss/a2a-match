// A2A Match 服务器增强版 v1.8.6
// 添加：API Key 鉴权 / 自动匹配算法 / WebSocket 通知

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
  createdAt: { type: Date, default: Date.now }
});

const Profile = mongoose.model('Profile', profileSchema);
const Match = mongoose.model('Match', matchSchema);

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
    version: '1.8.6',
    auth: AUTH_MODE ? '🔐 加密模式' : '🔓 开放模式（开发测试）'
  });
});

app.get('/api/info', requireAuth, (req, res) => {
  res.json({
    service: 'A2A Match - 智能供需匹配平台 v1.8.6',
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
      'GET  /api/profiles     [需鉴权]',
      'DELETE /api/profile/:userId [需鉴权]'
    ],
    websocketEvents: ['join', 'new_matches', 'match_accepted'],
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
    const match = await Match.findByIdAndUpdate(
      req.params.id, { status: 'accepted' }, { new: true }
    );
    if (!match) {
      return res.status(404).json({ error: '匹配不存在' });
    }
    io.emit('match_accepted', { matchId: req.params.id, match });
    res.json(match);
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
  logger.info(`A2A Match 服务器 v1.8.6 启动!`);
  logger.info(`端口: ${PORT}`);
  logger.info(`鉴权模式: ${AUTH_MODE ? '🔐 API Key（生产）' : '🔓 开放（开发测试）'}`);
  logger.info(`========================================`);
});

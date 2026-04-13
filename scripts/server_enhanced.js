// A2A Match 服务器增强版
// 添加自动匹配算法

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

const MONGODB_URI = process.env.MONGODB_URI || 'mongodb://localhost:27017/a2a_match';

mongoose.connect(MONGODB_URI).then(() => {
  logger.info('MongoDB 连接成功');
}).catch(err => {
  logger.error('MongoDB 连接失败:', err);
});

app.use(cors());
app.use(express.json());

// 数据模型
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
        details.push(`${profile1.name}的需求"${need}"匹配到${profile2.name}的资源"${resource}"`);
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
        details.push(`${profile1.name}的资源"${resource}"匹配到${profile2.name}的需求"${need}"`);
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
    
    // 匹配阈值 0.3
    if (score >= 0.3) {
      // 检查是否已存在匹配
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

// ==================== API 路由 ====================

app.get('/health', (req, res) => {
  res.json({ status: 'UP', timestamp: new Date().toISOString(), version: '1.8.3-enhanced' });
});

app.get('/api/info', (req, res) => {
  res.json({
    service: 'A2A Match - 智能匹配平台 v1.8.3',
    description: '零配置智能供需匹配 + 自动匹配算法',
    endpoints: [
      'GET  /health',
      'POST /api/profile - 创建档案并自动匹配',
      'GET  /api/profile/:userId',
      'GET  /api/matches/:userId',
      'POST /api/match/:id/accept',
      'POST /api/match/:id/reject',
      'GET  /api/profiles',
      'GET  /api/stats'
    ]
  });
});

app.get('/api/stats', async (req, res) => {
  try {
    const [profileCount, matchCount] = await Promise.all([
      Profile.countDocuments(),
      Match.countDocuments()
    ]);
    res.json({
      profiles: profileCount,
      matches: matchCount,
      activeMatches: await Match.countDocuments({ status: 'pending' }),
      acceptedMatches: await Match.countDocuments({ status: 'accepted' })
    });
  } catch (err) {
    res.status(500).json({ error: '获取统计失败' });
  }
});

app.post('/api/profile', async (req, res) => {
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
    
    // 自动匹配
    const newMatches = await findMatchesForProfile(profile);
    
    // 通过 WebSocket 通知
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

app.get('/api/profile/:userId', async (req, res) => {
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

app.get('/api/matches/:userId', async (req, res) => {
  try {
    const matches = await Match.find({
      $or: [{ userId1: req.params.userId }, { userId2: req.params.userId }]
    }).sort({ matchScore: -1 });
    
    // 填充用户信息
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

app.post('/api/match/:id/accept', async (req, res) => {
  try {
    const match = await Match.findByIdAndUpdate(
      req.params.id, { status: 'accepted' }, { new: true }
    );
    if (!match) {
      return res.status(404).json({ error: '匹配不存在' });
    }
    
    // 通知双方
    io.emit('match_accepted', { matchId: req.params.id, match });
    res.json(match);
  } catch (err) {
    res.status(500).json({ error: '接受匹配失败' });
  }
});

app.post('/api/match/:id/reject', async (req, res) => {
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

app.get('/api/profiles', async (req, res) => {
  try {
    const profiles = await Profile.find().sort({ createdAt: -1 });
    res.json(profiles);
  } catch (err) {
    res.status(500).json({ error: '获取所有档案失败' });
  }
});

app.delete('/api/profile/:userId', async (req, res) => {
  try {
    await Profile.deleteOne({ userId: req.params.userId });
    await Match.deleteMany({ $or: [{ userId1: req.params.userId }, { userId2: req.params.userId }] });
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: '删除档案失败' });
  }
});

// WebSocket
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

const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
  logger.info(`A2A Match 服务器启动! port:${PORT}`);
});

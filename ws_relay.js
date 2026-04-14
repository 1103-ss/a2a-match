/**
 * ws_relay.js - WebSocket 实时消息中转模块
 * 整合到 server.js 的 WebSocket 层
 * 
 * 事件：
 *   emit('join', { userId, matchId? })        → 加入个人/对话房间
 *   emit('send_msg', { matchId, content })     → 发送消息（自动走 REST API）
 *   emit('get_history', { matchId, limit? })   → 获取历史
 *   emit('mark_read', { matchId })             → 标记已读
 * 
 * 监听：
 *   on('msg', data)                            → 收到新消息
 *   on('history', { matchId, messages })        → 历史记录返回
 *   on('unread', { count })                     → 未读数
 *   on('joined', { matchId })                   → 加入成功
 *   on('error', { message })                   → 错误
 */

let io = null;
let logger = null;
let axios = null;
let serverBase = '';

// 在线用户
const onlineUsers = new Map(); // userId → { socketId, matchIds: Set }

function init(socketIO, log, baseUrl) {
    io = socketIO;
    logger = log;
    serverBase = baseUrl || 'http://81.70.250.9:3000';
    try { axios = require('axios'); } catch (e) { /* fallback */ }
}

function isUserOnline(userId) { return onlineUsers.has(userId); }

// ─── 加入对话 ─────────────────────────────────────────
function handleJoin(socket, data) {
    const { userId, matchId } = data;
    if (!userId) {
        socket.emit('error', { message: 'userId 不能为空' });
        return;
    }

    // 加入个人房间
    socket.userId = userId;
    socket.join(`u:${userId}`);
    socket.matchIds = new Set();

    const existing = onlineUsers.get(userId) || { socketId: socket.id, matchIds: new Set() };
    existing.socketId = socket.id;
    onlineUsers.set(userId, existing);

    // 如果有 matchId，一并加入对话房间
    if (matchId) {
        socket.join(`m:${matchId}`);
        socket.matchIds.add(matchId);
        existing.matchIds.add(matchId);
    }

    socket.emit('joined', { userId, matchId: matchId || null, online: true });
    logger?.info(`用户 ${userId} 加入 WebSocket${matchId ? '，对话 ' + matchId : ''}`);
}

// ─── 加入对话房间（已在对话中，要加入另一个 match）─────────────
function handleJoinMatch(socket, data) {
    const { matchId } = data;
    if (!matchId || !socket.userId) {
        socket.emit('error', { message: 'matchId 或未登录' });
        return;
    }
    socket.join(`m:${matchId}`);
    socket.matchIds.add(matchId);
    const info = onlineUsers.get(socket.userId) || {};
    info.matchIds = info.matchIds || new Set();
    info.matchIds.add(matchId);
    onlineUsers.set(socket.userId, info);
    socket.emit('joined', { matchId, via: 'match' });
    logger?.info(`用户 ${socket.userId} 加入对话房间 m:${matchId}`);
}

// ─── 发送消息（通过 HTTP REST API）────────────────────
async function handleSendMsg(socket, data) {
    const { matchId, content } = data;
    if (!matchId || !content?.trim()) {
        socket.emit('error', { message: 'matchId 和 content 不能为空' });
        return;
    }
    if (!socket.userId) {
        socket.emit('error', { message: '请先 join 登录' });
        return;
    }

    const apiKey = process.env.A2A_API_KEY || '';
    try {
        // 先获取 match 记录来确定对方 userId
        const matchResp = await fetch(`${serverBase}/api/matches/${socket.userId}`, {
            headers: { ...(apiKey ? { 'Authorization': `Bearer ${apiKey}` } : {}) }
        });
        let toUserId = null;
        if (matchResp.ok) {
            const matches = await matchResp.json();
            const myMatch = matches.find(m => m.id === matchId || m._id === matchId);
            if (myMatch) {
                toUserId = myMatch.otherUser?.userId;
            }
        }

        const resp = await fetch(`${serverBase}/api/message`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...(apiKey ? { 'Authorization': `Bearer ${apiKey}` } : {})
            },
            body: JSON.stringify({
                matchId, fromUserId: socket.userId,
                toUserId: toUserId || undefined,
                content: content.trim()
            })
        });
        const result = await resp.json();
        if (resp.ok) {
            socket.emit('sent', { id: result.messageId, matchId, content: content.trim() });
        } else {
            socket.emit('error', { message: result.error || '发送失败' });
        }
    } catch (e) {
        socket.emit('error', { message: '网络错误：' + e.message });
    }
}

// ─── 获取历史记录 ─────────────────────────────────────
async function handleGetHistory(socket, data) {
    const { matchId, before, limit = 20 } = data;
    if (!matchId || !socket.userId) {
        socket.emit('error', { message: 'matchId 或未登录' });
        return;
    }
    const apiKey = process.env.A2A_API_KEY || '';
    try {
        const params = new URLSearchParams({ userId: socket.userId });
        if (before) params.set('before', before);
        params.set('limit', String(limit));
        const resp = await fetch(`${serverBase}/api/match/${matchId}/messages?${params}`, {
            headers: { ...(apiKey ? { 'Authorization': `Bearer ${apiKey}` } : {}) }
        });
        const result = await resp.json();
        if (resp.ok) {
            socket.emit('history', {
                matchId,
                messages: (result.messages || []).map(m => ({
                    id: m.messageId || m.id,
                    senderId: m.fromUserId,
                    content: m.content,
                    createdAt: m.createdAt
                })),
                hasMore: (result.messages || []).length === Number(limit)
            });
        } else {
            socket.emit('error', { message: result.error || '获取历史失败' });
        }
    } catch (e) {
        socket.emit('error', { message: '网络错误：' + e.message });
    }
}

// ─── 标记已读 ─────────────────────────────────────────
async function handleMarkRead(socket, data) {
    const { matchId } = data;
    if (!matchId || !socket.userId) return;
    const apiKey = process.env.A2A_API_KEY || '';
    try {
        await fetch(`${serverBase}/api/messages/read`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...(apiKey ? { 'Authorization': `Bearer ${apiKey}` } : {})
            },
            body: JSON.stringify({ matchId, userId: socket.userId })
        });
    } catch (e) { /* fire and forget */ }
}

// ─── 断开连接 ─────────────────────────────────────────
function handleDisconnect(socket) {
    if (socket.userId) {
        const info = onlineUsers.get(socket.userId);
        if (info) {
            // 通知对方下线
            if (info.matchIds) {
                for (const mid of info.matchIds) {
                    socket.to(`m:${mid}`).emit('peer_offline', { userId: socket.userId });
                }
            }
        }
        onlineUsers.delete(socket.userId);
        logger?.info(`用户 ${socket.userId} WebSocket 断开`);
    }
}

// ─── 注册所有事件 ─────────────────────────────────────
function registerHandlers(socket) {
    socket.on('join', (data) => handleJoin(socket, data));
    socket.on('join_match', (data) => handleJoinMatch(socket, data));
    socket.on('send_msg', (data) => handleSendMsg(socket, data));
    socket.on('get_history', (data) => handleGetHistory(socket, data));
    socket.on('mark_read', (data) => handleMarkRead(socket, data));
    socket.on('disconnect', () => handleDisconnect(socket));
}

// ─── 服务器端主动推送（被 server.js 调用）──────────────
function pushToUser(userId, event, data) {
    if (io && userId) {
        io.to(`u:${userId}`).emit(event, data);
    }
}

function pushToMatch(matchId, event, data, excludeUserId = null) {
    if (io && matchId) {
        const room = `m:${matchId}`;
        if (excludeUserId) {
            io.to(room).except(`u:${excludeUserId}`).emit(event, data);
        } else {
            io.to(room).emit(event, data);
        }
    }
}

module.exports = { init, registerHandlers, pushToUser, pushToMatch, isUserOnline };

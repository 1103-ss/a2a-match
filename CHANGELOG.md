# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.2.0] - 2026-04-14

### Added
- 👤 **虾名机制** —— 首次注册必填昵称（虾名），虾名即为 A2A Match 里的唯一身份标识
- 🔄 **产品流程升级为 8 步** —— 新增 Step 0：设置虾名（必填项）
- 💬 **@虾名跨 Claw 对话** —— 匹配成功后，双方通过 @对方虾名 实时通信

### Changed
- 首次引导流程调整：先问虾名，再问需求/能力，最后问云端同步
- 昵称作为 profile.name 必须在 POST /api/profile 中上传（昵称即「虾名」）

## [2.1.0] - 2026-04-14

### Added
- 💬 **匹配内即时消息** —— 匹配成功后双方可通过 `@对方昵称` 在 Claw 对话框内直接聊天
- 📨 **消息 API** —— POST /api/message 发送、GET /api/messages/:userId 接收、POST /api/messages/read 标记已读
- 💾 **消息持久化** —— MongoDB 存储聊天记录，支持查询历史
- 🚫 **屏蔽功能** —— POST /api/match/:id/block 可屏蔽对方
- 🔔 **WebSocket new_message** —— 实时消息推送
- 📋 **聊天记录查询** —— GET /api/match/:id/messages 查看完整聊天

### Changed
- 产品流程从 6 步升级为 7 步（新增 Step 7 即时消息）
- SKILL.md 新增 @提及识别逻辑和消息展示格式

## [2.0.1] - 2026-04-14

### Changed
- 🔒 云端同步改为首次引导时由用户明确同意才开启，不自动开启

## [1.8.6] - 2026-04-13

### Security & Privacy
- 🔐 **API Key 鉴权** —— 所有 `/api/*` 接口支持 Bearer Token 认证（生产模式）
- ☁️ **云端功能默认关闭** —— 用户主动开启才连云端，解决"本地vs云端"不一致问题
- 📋 **完整隐私声明** —— 明确列出上传/不上传的数据范围
- 🔓 **开发/生产双模式** —— 未配置 API Key 时为开放模式（开发测试），配置后自动开启鉴权

### Changed
- 云端 WebSocket 通知需用户手动启用（cloud.enabled=false 默认）
- SKILL.md 增加「隐私与数据说明」专区，解决安全扫描警告

## [1.8.5] - 2026-04-13

### Added
- ☁️ **云端 WebSocket 通知** —— 匹配成功时实时推送通知
- 🔗 **Skill ↔ Cloud ↔ Skill 完整交互流程** —— 本地 Skill 与云端无缝对接
- 🌐 **云端服务器部署** —— `http://81.70.250.9:3000` 已上线
- 📡 **WebSocket 实时事件**：`new_matches` / `match_accepted`
- 🔄 **云端档案同步模块**（cloud_sync.py）
- 🛠️ **云端命令工具**（cloud_commands.py）
- 💓 **云端心跳检测**（heartbeat_cloud.py）
- 🧠 **自动匹配算法** —— 云端自动计算匹配分数（阈值 0.3）

### Changed
- Socket.IO 替代纯 WebSocket，兼容性更好
- 匹配算法归一化处理（最高 1.0）
- 云端配置支持 WebSocket 开关

## [1.8.3] - 2026-04-13

### Added
- 多平台发布（SkillHub v1.8.3、GitHub）
- 推广文章（掘金、知乎）

## [1.8.2] - 2026-04-12

### Added
- SkillHub SEO 优化（13个关键词）
- 详细推广清单文档

## [1.8.1] - 2026-04-11

### Added
- 腾讯云服务器部署准备
- MongoDB + PM2 部署脚本

## [1.8.0] - 2026-04-10

### Added
- 聚焦 5 大核心领域，补充领域术语
- 匹配类型说明文档

## [1.6.1] - 2026-04-09

### Added
- 推广素材：README.md、推广文章、贡献指南
- 推广清单文档 (docs/PROMOTION_CHECKLIST.md)
- 多平台发布准备

## [1.6.0] - 2026-04-09

### Added
- 💓 心跳机制：对话中自动检测需求/能力/资源并提示匹配机会
- heartbeat_check.py 脚本
- 匹配结果展示优化
- 模糊匹配算法（支持关键词匹配）

### Changed
- 匹配逻辑支持不同字段名（description/skill/name）
- 匹配计算改为小写并支持关键词包含

## [1.5.0] - 2026-04-08

### Added
- 从记忆文件读取功能 (memory_parser.py)
- 防幻觉机制：严格只记录明确提到的信息
- 置信度阈值（>80% 才记录）

### Changed
- 废弃模板填写方式
- 改为从 MEMORY.md 自动解析

## [1.4.0] - 2026-04-07

### Added
- 智能识别：从对话中自动提取信号
- 意图识别器 (intent_recognizer.py)

### Deprecated
- 交互式设置向导

## [1.3.0] - 2026-04-06

### Added
- 游戏化概念：XP、等级、成就系统
- Agent 卡片生成器

## [1.0.0] - 2026-04-05

### Added
- 初始版本
- 基础匹配引擎
- 档案管理
- 简单的命令行界面

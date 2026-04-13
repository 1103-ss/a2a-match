# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

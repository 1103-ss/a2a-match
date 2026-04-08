# A2A Match 发布流程

> 更新时需同步发布到三个平台

---

## 📦 版本更新检查清单

- [ ] 更新 `skill.json` 中的 `version` 字段
- [ ] 更新 `CHANGELOG.md` 添加版本记录
- [ ] 测试核心功能是否正常

---

## 🚀 发布步骤

### 1️⃣ ClawHub

```bash
cd C:\Users\Administrator\.qclaw\workspace\skills\a2a-match
clawhub publish .
```

---

### 2️⃣ GitHub

```bash
cd C:\Users\Administrator\.qclaw\workspace\skills\a2a-match
git add .
git commit -m "v1.8.3 - 更新说明"
git push
git tag v1.8.3
git push --tags
```

---

### 3️⃣ SkillHub

#### 打包（排除不允许的文件）

```powershell
# 清理旧文件
Remove-Item "a2a-match-clean" -Recurse -Force -ErrorAction SilentlyContinue

# 复制文件（排除不允许的类型）
robocopy "a2a-match" "a2a-match-clean" /E /XD .git __pycache__ /XF start.bat LICENSE test_match.py .gitignore

# 打包
Compress-Archive -Path "a2a-match-clean\*" -DestinationPath "a2a-match-clean.zip" -Force
```

#### 上传

1. 访问 https://skillhub.tencent.com/publish
2. 上传 `a2a-match-clean.zip`
3. 填写表单：
   - **Slug**: `a2a-match`（保持不变）
   - **显示名称**: `A2A Match - 智能供需匹配平台`
   - **描述**: 零配置的智能匹配系统，从对话中自动识别需求/能力/资源，帮你找到合适的合作伙伴。支持AI、互联网、云算力、电商、工业数字化5大领域的供需匹配。
   - **版本号**: `1.8.3`（更新为新版本）
   - **变更说明**: 填写本次更新内容

---

## ⚠️ SkillHub 文件限制

不允许上传的文件类型：
- ❌ `.bat`、`.exe`、`.sh`、`.cmd` 等可执行脚本
- ❌ `LICENSE` 文件
- ❌ `.gitignore` 等配置文件
- ❌ `__pycache__/` 编译缓存
- ❌ `test_*.py` 测试文件

允许的文件类型：
- ✅ `.md` Markdown 文档
- ✅ `.py` Python 源码
- ✅ `.json` 配置文件
- ✅ `.txt` 文本文件

---

## 📝 版本号规则

遵循语义化版本：`MAJOR.MINOR.PATCH`

- **MAJOR**: 重大更新，不兼容的 API 修改
- **MINOR**: 新增功能，向后兼容
- **PATCH**: Bug 修复，小改进

---

## 🔗 相关链接

- **SkillHub**: https://skillhub.tencent.com/skills/a2a-match
- **GitHub**: https://github.com/qclaw/a2a-match
- **ClawHub**: `clawhub search a2a-match`

---

## 📅 版本历史

| 版本 | 日期 | 更新内容 |
|------|------|---------|
| 1.8.2 | 2026-04-09 | 优化文档结构，添加关键词标签 |
| 1.8.0 | 2026-04-08 | 聚焦5大核心领域，补充领域术语 |
| 1.7.0 | - | 区分精确匹配/间接匹配 |
| 1.6.0 | - | 心跳机制，主动提示匹配 |

---

**最后更新**: 2026-04-09

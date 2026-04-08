# A2A Match 开发指南

## 项目结构

```
a2a-match/
├── SKILL.md                    # Skill 说明文档
├── README.md                   # GitHub README
├── LICENSE                     # MIT 许可证
├── skill.json                  # Skill 元数据
├── scripts/                    # 核心脚本
│   ├── a2a.py                  # 匹配引擎
│   ├── memory_parser.py        # 记忆解析器
│   └── heartbeat_check.py      # 心跳检测
├── a2a/                        # 数据目录
│   ├── config.json             # 配置文件
│   └── cache/                  # 缓存目录
└── docs/                       # 文档
    └── article.md              # 推广文章
```

## 本地开发

### 1. 克隆仓库

```bash
git clone https://github.com/your-org/a2a-match.git
cd a2a-match
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 测试脚本

```bash
# 测试记忆解析
python scripts/memory_parser.py

# 测试匹配
python scripts/a2a.py match --local

# 测试心跳检测
python scripts/heartbeat_check.py
```

## 发布流程

### 1. 更新版本号

在 `skill.json` 中更新版本号：

```json
{
  "version": "1.7.0",
  ...
}
```

### 2. 更新 CHANGELOG

在 `SKILL.md` 的版本历史中添加：

```markdown
| 版本 | 更新 |
|------|------|
| 1.7.0 | 新功能描述 |
```

### 3. 发布到 SkillHub

```bash
clawhub publish . --name "A2A Match" --slug "a2a-match" --version "1.7.0"
```

### 4. 推送到 GitHub

```bash
git add .
git commit -m "Release v1.7.0"
git tag v1.7.0
git push origin main
git push --tags
```

## 代码规范

### Python

- 使用 Python 3.8+
- 遵循 PEP 8 规范
- 函数必须有文档字符串
- 使用类型注解

### 示例

```python
from typing import Dict, List, Optional


def calculate_match(
    my_profile: Dict,
    other_profile: Dict,
    threshold: float = 0.3
) -> Dict[str, float]:
    """
    计算两个档案的匹配度。

    Args:
        my_profile: 我的档案
        other_profile: 对方的档案
        threshold: 匹配阈值

    Returns:
        包含匹配分数和详情的字典
    """
    ...
```

## 贡献指南

### 提交 PR

1. Fork 本仓库
2. 创建特性分支: `git checkout -b feature/amazing-feature`
3. 提交更改: `git commit -m 'Add amazing feature'`
4. 推送分支: `git push origin feature/amazing-feature`
5. 提交 Pull Request

### 代码审查

所有 PR 都需要通过代码审查才能合并。

## 测试

```bash
# 运行所有测试
pytest tests/

# 运行特定测试
pytest tests/test_match.py -v
```

## 许可证

MIT License

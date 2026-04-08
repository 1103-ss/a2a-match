#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A2A Match - 引导流程
新用户启用 Skill 时的引导流程
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime

# 修复 Windows GBK 编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

WORKSPACE_DIR = Path(os.environ.get('QCLAW_WORKSPACE', Path.home() / '.qclaw' / 'workspace'))
A2A_DIR = WORKSPACE_DIR / 'a2a'
PROFILE_PATH = A2A_DIR / 'profile.json'

# 行业列表
INDUSTRIES = [
    "技术开发", "互联网", "电商", "金融", "咨询", "媒体", "教育",
    "医疗", "法律", "设计", "营销", "制造业", "零售", "其他"
]

# 热门能力
POPULAR_CAPABILITIES = {
    "技术开发": ["Python开发", "前端开发", "后端开发", "AI开发", "移动开发"],
    "互联网": ["产品设计", "用户研究", "数据分析", "项目管理", "运营"],
    "电商": ["电商运营", "直播带货", "供应链管理", "流量投放", "客服管理"],
    "金融": ["投资分析", "风险管理", "财务顾问", "合规咨询", "融资对接"],
    "咨询": ["战略咨询", "管理咨询", "人力资源", "流程优化", "数字化转型"],
    "媒体": ["内容创作", "视频制作", "新媒体运营", "品牌营销", "公关传播"],
    "教育": ["课程设计", "在线教学", "教育咨询", "培训师", "教育技术"],
    "设计": ["UI设计", "产品设计", "平面设计", "品牌设计", "动效设计"],
}

# 热门需求
POPULAR_NEEDS = {
    "技术开发": ["GPU算力", "测试资源", "技术外包", "开源合作"],
    "互联网": ["用户增长", "流量渠道", "合作伙伴", "投资对接"],
    "电商": ["货源资源", "流量渠道", "物流合作", "品牌合作"],
    "金融": ["项目资源", "客户线索", "合规支持", "技术合作"],
    "咨询": ["客户线索", "行业资源", "专家网络", "案例合作"],
    "媒体": ["流量变现", "品牌合作", "内容分发", "商业合作"],
    "教育": ["学生资源", "课程分销", "讲师合作", "技术支持"],
    "设计": ["客户资源", "项目外包", "素材资源", "工具授权"],
}


def show_welcome():
    """显示欢迎页面"""
    print()
    print("╔" + "═" * 50 + "╗")
    print("║                                                    ║")
    print("║   🤖 欢迎来到 A2A Match！                          ║")
    print("║                                                    ║")
    print("║   在这里，你可以：                                 ║")
    print("║   • 发布你的能力和资源                             ║")
    print("║   • 表达你的需求                                   ║")
    print("║   • 找到匹配的合作伙伴                             ║")
    print("║                                                    ║")
    print("║   让我们创建你的 Agent 档案                        ║")
    print("║   只需要 1 分钟！                                  ║")
    print("║                                                    ║")
    print("╚" + "═" * 50 + "╝")
    print()


def show_step(step, total, title):
    """显示步骤标题"""
    print()
    print(f"📝 第 {step} 步（共 {total} 步）：{title}")
    print("-" * 50)


def select_from_list(items, prompt, allow_multi=False):
    """从列表中选择"""
    for i, item in enumerate(items, 1):
        print(f"  {i}. {item}")

    print()

    if allow_multi:
        print(f"{prompt}（多选用逗号分隔，如 1,3,5）")
    else:
        print(prompt)

    try:
        choice = input("请选择: ").strip()

        if allow_multi:
            indices = [int(x.strip()) - 1 for x in choice.split(',') if x.strip().isdigit()]
            return [items[i] for i in indices if 0 <= i < len(items)]
        else:
            if choice.isdigit():
                index = int(choice) - 1
                if 0 <= index < len(items):
                    return items[index]
    except:
        pass

    return None if not allow_multi else []


def create_profile_wizard():
    """创建档案向导"""
    show_welcome()

    profile = {
        "version": "1.0",
        "profile": {},
        "capabilities": [],
        "resources": [],
        "needs": [],
        "business": {},
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }

    # 第1步：基本信息
    show_step(1, 4, "你是谁？")

    name = input("姓名: ").strip()
    role = input("职业: ").strip()
    company = input("公司（可选）: ").strip()

    print()
    print("选择你的行业：")
    industry = select_from_list(INDUSTRIES, "选择行业")

    profile["profile"] = {
        "id": f"user_{os.urandom(4).hex()}",
        "name": name or "匿名用户",
        "role": role or "未设置",
        "company": company,
        "industry": industry or "其他"
    }

    # 第2步：选择能力
    show_step(2, 4, "你擅长什么？")

    if industry and industry in POPULAR_CAPABILITIES:
        print(f"\n💡 {industry}热门能力：")
        capabilities = select_from_list(
            POPULAR_CAPABILITIES[industry],
            "选择你擅长的能力",
            allow_multi=True
        )
    else:
        print("\n输入你的能力（用逗号分隔）：")
        caps_input = input("例如: Python开发, 产品设计: ").strip()
        capabilities = [c.strip() for c in caps_input.split(',') if c.strip()]

    for cap in capabilities[:10]:  # 最多10个
        profile["capabilities"].append({
            "id": f"cap_{os.urandom(3).hex()}",
            "skill": cap,
            "level": "intermediate",
            "years": 0,
            "description": "",
            "tags": []
        })

    # 第3步：选择需求
    show_step(3, 4, "你需要什么？")

    if industry and industry in POPULAR_NEEDS:
        print(f"\n💡 {industry}常见需求：")
        needs = select_from_list(
            POPULAR_NEEDS[industry],
            "选择你需要的东西",
            allow_multi=True
        )
    else:
        print("\n输入你的需求（用逗号分隔）：")
        needs_input = input("例如: GPU算力, 流量渠道: ").strip()
        needs = [n.strip() for n in needs_input.split(',') if n.strip()]

    for need in needs[:10]:
        profile["needs"].append({
            "id": f"need_{os.urandom(3).hex()}",
            "type": "capability",
            "skill": need,
            "priority": "medium",
            "description": "",
            "status": "open"
        })

    # 第4步：是否有资源分享
    show_step(4, 4, "你有资源可以分享吗？")

    print("\n可选：如果你有闲置资源愿意分享")
    print("例如：GPU算力、流量渠道、货源资源等")

    has_resources = input("有资源分享吗？(y/n): ").strip().lower()

    if has_resources == 'y':
        print("\n输入你的资源（用逗号分隔）：")
        res_input = input("例如: RTX 4090算力, 公众号流量: ").strip()
        resources = [r.strip() for r in res_input.split(',') if r.strip()]

        for res in resources[:5]:
            profile["resources"].append({
                "id": f"res_{os.urandom(3).hex()}",
                "type": "other",
                "name": res,
                "specs": {},
                "availability": "available",
                "price": "可协商"
            })

    # 保存档案
    A2A_DIR.mkdir(parents=True, exist_ok=True)
    with open(PROFILE_PATH, 'w', encoding='utf-8') as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)

    # 显示完成
    print()
    print("╔" + "═" * 50 + "╗")
    print("║                                                    ║")
    print("║   ✨ 档案创建完成！                                ║")
    print("║                                                    ║")
    print("╚" + "═" * 50 + "╝")

    # 生成 Agent 卡片
    print()
    print("你的 Agent 卡片：")
    print()

    from card_generator import generate_card
    print(generate_card(profile))

    # 显示匹配提示
    print()
    print("💡 下一步：")
    print("   • 查看 Agent 卡片: python scripts/a2a.py card")
    print("   • 查看匹配: python scripts/a2a.py match --local")
    print("   • 查看仪表盘: python scripts/a2a.py dashboard")
    print()

    return profile


if __name__ == '__main__':
    # 检查是否已有档案
    if PROFILE_PATH.exists():
        print("\n⚠️  你已有档案！")
        print("   要重新创建，请先删除: " + str(PROFILE_PATH))
        print("   或使用: python scripts/a2a.py profile --full")
        sys.exit(0)

    try:
        create_profile_wizard()
    except KeyboardInterrupt:
        print("\n\n👋 已取消")

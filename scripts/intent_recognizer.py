#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A2A Match - 智能识别引擎
在对话中自动识别用户的需求、能力、资源
"""

import re
import json
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict

# 修复 Windows GBK 编码
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


@dataclass
class RecognizedItem:
    """识别出的项目"""
    type: str  # need, capability, resource
    content: str
    category: str
    confidence: float
    keywords: List[str]
    context: str  # 原始上下文


class IntentRecognizer:
    """意图识别器"""

    # 需求信号模式
    NEED_PATTERNS = {
        # 技术/算力
        "GPU算力": [
            r"需要.*GPU",
            r"训练.*模型",
            r"算力.*不够",
            r"显卡.*不够",
            r"RTX.*\d+",
            r"A\d+.*算力",
            r"H\d+.*算力",
            r"云服务器",
            r"深度学习.*资源",
        ],

        # 设计服务
        "设计服务": [
            r"需要.*设计",
            r"找人.*设计",
            r"UI.*设计",
            r"logo.*设计",
            r"品牌.*设计",
            r"海报.*设计",
            r"界面.*设计",
            r"设计.*外包",
        ],

        # 流量/推广
        "流量渠道": [
            r"需要.*流量",
            r"推广.*渠道",
            r"获客.*渠道",
            r"引流.*渠道",
            r"投放.*渠道",
            r"流量.*变现",
            r"用户.*增长",
            r"曝光.*渠道",
        ],

        # 货源/供应链
        "货源资源": [
            r"找.*货源",
            r"供应商.*资源",
            r"采购.*渠道",
            r"批发.*货源",
            r"工厂.*资源",
            r"供应链.*对接",
        ],

        # 法律服务
        "法律咨询": [
            r"法律.*问题",
            r"需要.*律师",
            r"合同.*问题",
            r"知识产权.*问题",
            r"法务.*咨询",
            r"合规.*咨询",
        ],

        # 融资/投资
        "融资对接": [
            r"需要.*融资",
            r"找.*投资人",
            r"路演.*机会",
            r"融资.*渠道",
            r"VC.*对接",
            r"天使.*投资",
        ],

        # 内容创作
        "内容创作": [
            r"需要.*内容",
            r"内容.*创作",
            r"文案.*写作",
            r"视频.*制作",
            r"脚本.*创作",
            r"文章.*撰写",
        ],

        # 技术开发
        "技术开发": [
            r"需要.*开发",
            r"技术.*外包",
            r"开发.*团队",
            r"程序员.*合作",
            r"项目.*开发",
            r"App.*开发",
            r"网站.*开发",
        ],
    }

    # 能力信号模式
    CAPABILITY_PATTERNS = {
        # 技术能力
        "Python开发": [
            r"我会.*Python",
            r"Python.*开发",
            r"Python.*编程",
            r"精通.*Python",
            r"擅长.*Python",
        ],

        "前端开发": [
            r"前端.*开发",
            r"Vue.*开发",
            r"React.*开发",
            r"Web.*开发",
            r"JavaScript.*开发",
        ],

        "后端开发": [
            r"后端.*开发",
            r"服务端.*开发",
            r"Java.*开发",
            r"Go.*开发",
            r"Node.*开发",
        ],

        "AI/机器学习": [
            r"AI.*开发",
            r"机器学习",
            r"深度学习",
            r"大模型.*开发",
            r"算法.*工程",
        ],

        # 设计能力
        "UI设计": [
            r"UI.*设计",
            r"界面.*设计",
            r"交互.*设计",
            r"Figma.*设计",
        ],

        "产品设计": [
            r"产品.*设计",
            r"产品.*经理",
            r"产品.*规划",
            r"用户.*研究",
        ],

        # 运营能力
        "电商运营": [
            r"电商.*运营",
            r"店铺.*运营",
            r"淘宝.*运营",
            r"抖音.*运营",
        ],

        "内容运营": [
            r"内容.*运营",
            r"新媒体.*运营",
            r"社群.*运营",
            r"用户.*运营",
        ],

        # 咨询能力
        "战略咨询": [
            r"战略.*咨询",
            r"管理.*咨询",
            r"业务.*咨询",
            r"企业.*咨询",
        ],

        "财务顾问": [
            r"财务.*顾问",
            r"税务.*咨询",
            r"财务.*规划",
            r"投资.*顾问",
        ],
    }

    # 资源信号模式
    RESOURCE_PATTERNS = {
        # 算力资源
        "GPU算力": [
            r"有.*GPU",
            r"RTX.*\d+.*闲置",
            r"有.*显卡",
            r"服务器.*闲置",
            r"算力.*可以提供",
            r"有.*A\d+",
            r"有.*H\d+",
        ],

        # 流量资源
        "流量渠道": [
            r"有.*流量",
            r"公众号.*粉丝",
            r"抖音.*粉丝",
            r"小红书.*粉丝",
            r"私域.*流量",
            r"社群.*资源",
        ],

        # 货源资源
        "货源渠道": [
            r"有.*货源",
            r"工厂.*资源",
            r"供应商.*资源",
            r"可以.*供货",
            r"批发.*渠道",
        ],

        # 资金资源
        "资金/投资": [
            r"有.*资金",
            r"可以.*投资",
            r"天使.*投资人",
            r"VC.*资源",
        ],

        # 内容资源
        "内容/渠道": [
            r"有.*账号",
            r"有.*平台",
            r"媒体.*资源",
            r"渠道.*资源",
        ],
    }

    def __init__(self):
        self.compiled_need_patterns = self._compile_patterns(self.NEED_PATTERNS)
        self.compiled_capability_patterns = self._compile_patterns(self.CAPABILITY_PATTERNS)
        self.compiled_resource_patterns = self._compile_patterns(self.RESOURCE_PATTERNS)

    def _compile_patterns(self, patterns: Dict[str, List[str]]) -> Dict[str, List]:
        """编译正则表达式"""
        compiled = {}
        for category, pattern_list in patterns.items():
            compiled[category] = [
                re.compile(p, re.IGNORECASE) for p in pattern_list
            ]
        return compiled

    def recognize_needs(self, text: str) -> List[RecognizedItem]:
        """识别需求"""
        return self._recognize(text, self.compiled_need_patterns, "need")

    def recognize_capabilities(self, text: str) -> List[RecognizedItem]:
        """识别能力"""
        return self._recognize(text, self.compiled_capability_patterns, "capability")

    def recognize_resources(self, text: str) -> List[RecognizedItem]:
        """识别资源"""
        return self._recognize(text, self.compiled_resource_patterns, "resource")

    def _recognize(self, text: str, patterns: Dict[str, List], item_type: str) -> List[RecognizedItem]:
        """通用识别方法"""
        results = []

        for category, compiled_patterns in patterns.items():
            for pattern in compiled_patterns:
                match = pattern.search(text)
                if match:
                    # 计算置信度
                    confidence = self._calculate_confidence(match, text)

                    # 提取关键词
                    keywords = self._extract_keywords(match.group())

                    results.append(RecognizedItem(
                        type=item_type,
                        content=category,
                        category=category,
                        confidence=confidence,
                        keywords=keywords,
                        context=match.group()
                    ))
                    break  # 一个类别只匹配一次

        return results

    def _calculate_confidence(self, match, text: str) -> float:
        """计算置信度"""
        # 基础置信度
        base_confidence = 0.7

        # 匹配长度加成
        match_length = len(match.group())
        length_bonus = min(match_length / 20, 0.2)

        # 上下文加成
        context_keywords = ["需要", "寻找", "求", "帮", "有吗", "可以"]
        context_bonus = 0.1 if any(kw in text for kw in context_keywords) else 0

        return min(base_confidence + length_bonus + context_bonus, 1.0)

    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        # 简单提取
        keywords = []

        # GPU 型号
        gpu_match = re.search(r'(RTX|GTX|A|H)\s*\d+', text, re.IGNORECASE)
        if gpu_match:
            keywords.append(gpu_match.group().upper())

        # 数字
        numbers = re.findall(r'\d+', text)
        keywords.extend(numbers[:2])

        return keywords

    def analyze_conversation(self, text: str) -> Dict:
        """分析对话内容"""
        needs = self.recognize_needs(text)
        capabilities = self.recognize_capabilities(text)
        resources = self.recognize_resources(text)

        return {
            "needs": [asdict(n) for n in needs],
            "capabilities": [asdict(c) for c in capabilities],
            "resources": [asdict(r) for r in resources],
            "has_signals": bool(needs or capabilities or resources),
            "summary": self._generate_summary(needs, capabilities, resources)
        }

    def _generate_summary(self, needs, capabilities, resources) -> str:
        """生成识别摘要"""
        parts = []

        if needs:
            parts.append(f"需要: {', '.join([n.content for n in needs])}")

        if capabilities:
            parts.append(f"擅长: {', '.join([c.content for c in capabilities])}")

        if resources:
            parts.append(f"资源: {', '.join([r.content for r in resources])}")

        return " | ".join(parts) if parts else "未识别到明显信号"


# ============ 交互式提示生成 ============

def generate_need_prompt(items: List[RecognizedItem]) -> str:
    """生成需求确认提示"""
    if not items:
        return ""

    item = items[0]  # 取置信度最高的

    return f"""
🎯 我注意到你可能需要：

• {item.content}

要添加到你的需求列表吗？
这样我可以帮你找到匹配的 Agent！

[添加需求] [稍后] [不是这个]
""".strip()


def generate_capability_prompt(items: List[RecognizedItem]) -> str:
    """生成能力确认提示"""
    if not items:
        return ""

    item = items[0]

    return f"""
💪 发现你的能力：

• {item.content}

要添加到你的能力列表吗？
这样有需要的人可以找到你！

[添加能力] [稍后] [不是这个]
""".strip()


def generate_resource_prompt(items: List[RecognizedItem]) -> str:
    """生成资源确认提示"""
    if not items:
        return ""

    item = items[0]

    return f"""
🎁 发现你有可分享的资源：

• {item.content}

要添加到你的资源列表吗？
这样有需要的人可以找到你！

[添加资源] [稍后] [不是这个]
""".strip()


# ============ 测试 ============

if __name__ == '__main__':
    recognizer = IntentRecognizer()

    # 测试用例
    test_cases = [
        "我最近在训练一个大模型，需要一些GPU算力",
        "我在找人做一个APP，需要技术开发",
        "我有几台服务器闲着，有RTX 4090",
        "我是做产品设计的，有5年经验",
        "我们公司需要找一些流量推广渠道",
        "我这里有女装货源，可以提供",
        "我需要找一个律师咨询一下合同问题",
    ]

    print("=" * 60)
    print("A2A Match - 智能识别测试")
    print("=" * 60)

    for text in test_cases:
        print(f"\n📝 输入: {text}")
        print("-" * 60)

        result = recognizer.analyze_conversation(text)

        if result['has_signals']:
            print(f"📊 识别结果: {result['summary']}")

            # 显示详细
            for need in result['needs']:
                print(f"   📥 需求: {need['content']} (置信度: {need['confidence']:.0%})")

            for cap in result['capabilities']:
                print(f"   💪 能力: {cap['content']} (置信度: {cap['confidence']:.0%})")

            for res in result['resources']:
                print(f"   🎁 资源: {res['content']} (置信度: {res['confidence']:.0%})")
        else:
            print("   未识别到明显信号")

    print("\n" + "=" * 60)

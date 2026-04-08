#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A2A Match - 记忆解析器
从 MEMORY.md 和 memory/ 目录读取用户信息，生成 A2A 档案
"""

import re
import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

# 修复 Windows GBK 编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# 路径配置
WORKSPACE_DIR = Path(os.environ.get('QCLAW_WORKSPACE', Path.home() / '.qclaw' / 'workspace'))
MEMORY_FILE = WORKSPACE_DIR / 'MEMORY.md'
MEMORY_DIR = WORKSPACE_DIR / 'memory'
A2A_DIR = WORKSPACE_DIR / 'a2a'
PROFILE_PATH = A2A_DIR / 'a2a_profile.json'


@dataclass
class ExtractedInfo:
    """提取的信息"""
    type: str  # need, capability, resource, profile
    content: str
    source: str  # 来源文件:行号
    confidence: float
    context: str  # 原始上下文
    date: Optional[str] = None


class MemoryParser:
    """记忆解析器 - 从记忆文件提取结构化信息"""

    # 需求信号模式（只匹配明确的表述）
    # 格式: (pattern, confidence, need_type)
    # need_type: resource(需要资源本身) / capability(需要能力服务) / consulting(需要咨询建议)
    NEED_PATTERNS = [
        # ========== 人工智能领域 ==========
        # Token/API 相关
        (r"需要(.{2,20})(?:API|api|token|Token)", 0.95, "resource"),
        (r"找(.{2,20})(?:API|api|token|Token)", 0.95, "resource"),
        (r"求(.{2,20})(?:API|api|token|Token)", 0.95, "resource"),
        
        # Agent/AI开发
        (r"需要(.{2,20})Agent开发", 0.95, "capability"),
        (r"需要(.{2,20})AI开发", 0.95, "capability"),
        (r"找(.{2,20})Agent开发", 0.90, "capability"),
        
        # 图像生成/AI短剧
        (r"需要(.{2,20})图像生成", 0.95, "capability"),
        (r"需要(.{2,20})AI短剧", 0.95, "capability"),
        (r"找(.{2,20})图像生成", 0.90, "capability"),
        
        # OPC创业找搭子
        (r"(.{2,20})创业找搭子", 0.95, "capability"),
        (r"找(.{2,20})合伙人", 0.90, "capability"),
        (r"寻找(.{2,20})合作伙伴", 0.90, "capability"),
        
        # ========== 互联网领域 ==========
        # 平台/Web/小程序开发
        (r"需要(.{2,20})平台开发", 0.95, "capability"),
        (r"需要(.{2,20})Web开发", 0.95, "capability"),
        (r"需要(.{2,20})小程序开发", 0.95, "capability"),
        (r"需要(.{2,20})网站开发", 0.95, "capability"),
        (r"需要(.{2,20})APP开发", 0.95, "capability"),
        
        # 技术解决方案
        (r"需要(.{2,20})技术解决", 0.90, "capability"),
        (r"需要(.{2,20})技术支持", 0.90, "capability"),
        (r"需要(.{2,20})架构设计", 0.90, "capability"),
        
        # ========== 云算力领域 ==========
        # 大模型训练用卡
        (r"需要(.{2,20})训练用卡", 0.95, "resource"),
        (r"需要(.{2,20})GPU(?:卡|算力)?", 0.95, "resource"),
        (r"需要(.{2,20})(?:RTX|GTX|A\d+|H\d+|4090|3090)", 0.95, "resource"),
        (r"找(.{2,20})显卡", 0.90, "resource"),
        
        # 算力硬件
        (r"需要(.{2,20})算力硬件", 0.95, "resource"),
        (r"需要(.{2,20})服务器", 0.95, "resource"),
        (r"需要(.{2,20})算力", 0.90, "resource"),
        
        # 镜像需求
        (r"需要(.{2,20})镜像", 0.90, "resource"),
        (r"找(.{2,20})镜像", 0.90, "resource"),
        
        # 算力运维
        (r"需要(.{2,20})算力运维", 0.95, "capability"),
        (r"需要(.{2,20})集群部署", 0.95, "capability"),
        
        # ========== 电商领域 ==========
        # 工厂OEM/ODM
        (r"需要(.{2,20})OEM", 0.95, "resource"),
        (r"需要(.{2,20})ODM", 0.95, "resource"),
        (r"找(.{2,20})代工厂", 0.95, "resource"),
        (r"找(.{2,20})工厂代工", 0.95, "resource"),
        
        # 电商供销
        (r"需要(.{2,20})货源", 0.95, "resource"),
        (r"找(.{2,20})货源", 0.95, "resource"),
        (r"需要(.{2,20})供销渠道", 0.90, "resource"),
        (r"需要(.{2,20})分销渠道", 0.90, "resource"),
        
        # 运营服务
        (r"需要(.{2,20})店铺运营", 0.95, "capability"),
        (r"需要(.{2,20})直播带货", 0.95, "capability"),
        (r"需要(.{2,20})电商运营", 0.95, "capability"),
        
        # ========== 工业数字化领域 ==========
        # 操作端开发
        (r"需要(.{2,20})操作端开发", 0.95, "capability"),
        (r"需要(.{2,20})MES开发", 0.95, "capability"),
        (r"需要(.{2,20})ERP开发", 0.95, "capability"),
        
        # 企业部署
        (r"需要(.{2,20})企业部署", 0.95, "capability"),
        (r"需要(.{2,20})系统集成", 0.95, "capability"),
        
        # 企业SaaS
        (r"需要(.{2,20})企业SaaS", 0.95, "resource"),
        (r"需要(.{2,20})SaaS服务", 0.95, "resource"),
        
        # 数字化转型
        (r"需要(.{2,20})数字化转型", 0.90, "consulting"),
        (r"需要(.{2,20})数字化咨询", 0.90, "consulting"),
        
        # ========== 通用需求 ==========
        (r"需要(.{2,20})资源", 0.90, "resource"),
        (r"求(.{2,20})资源", 0.90, "resource"),
        (r"在找(.{2,20})", 0.80, "auto"),
        (r"缺少(.{2,20})", 0.80, "auto"),
        (r"缺(.{2,20})", 0.75, "auto"),
        (r"需要(.{2,20})", 0.70, "auto"),
    ]

    # 能力信号模式
    CAPABILITY_PATTERNS = [
        # ========== 人工智能领域 ==========
        (r"会(.{2,20})Agent开发", 0.95),
        (r"擅长(.{2,20})Agent", 0.95),
        (r"精通(.{2,20})大模型", 0.95),
        (r"会(.{2,20})图像生成", 0.95),
        (r"擅长(.{2,20})SD|Stable Diffusion", 0.95),
        (r"会(.{2,20})AI短剧", 0.95),
        (r"擅长(.{2,20})Prompt", 0.90),
        (r"精通(.{2,20})模型微调", 0.95),
        
        # ========== 互联网领域 ==========
        (r"会(.{2,20})(?:平台|Web|网站|APP|小程序)开发", 0.95),
        (r"擅长(.{2,20})前端", 0.95),
        (r"擅长(.{2,20})后端", 0.95),
        (r"精通(.{2,20})全栈", 0.95),
        (r"擅长(.{2,20})架构设计", 0.90),
        
        # ========== 云算力领域 ==========
        (r"擅长(.{2,20})算力运维", 0.95),
        (r"精通(.{2,20})集群部署", 0.95),
        (r"会(.{2,20})模型训练", 0.95),
        (r"有(\d+)年(.{2,10})运维经验", 0.95),
        
        # ========== 电商领域 ==========
        (r"擅长(.{2,20})店铺运营", 0.95),
        (r"会(.{2,20})直播带货", 0.95),
        (r"有(\d+)年(.{2,10})电商经验", 0.95),
        (r"擅长(.{2,20})供应链", 0.90),
        
        # ========== 工业数字化领域 ==========
        (r"擅长(.{2,20})MES", 0.95),
        (r"精通(.{2,20})ERP", 0.95),
        (r"会(.{2,20})企业部署", 0.95),
        (r"擅长(.{2,20})系统集成", 0.95),
        (r"有(\d+)年(.{2,10})数字化转型经验", 0.95),
        
        # ========== 通用能力 ==========
        (r"我会(.{2,20})", 0.85),
        (r"我擅长(.{2,20})", 0.90),
        (r"精通(.{2,20})", 0.85),
        (r"熟悉(.{2,20})", 0.75),
        (r"有(\d+)年(.{2,10})经验", 0.90),
        (r"做(.{2,10})有(\d+)年", 0.85),
        (r"我是(.{2,10})(?:工程师|设计师|产品|运营|开发)", 0.80),
        (r"负责(.{2,20})", 0.70),
    ]

    # 资源信号模式
    RESOURCE_PATTERNS = [
        # ========== 人工智能领域 ==========
        (r"有(.{2,20})(?:API|api|token|Token)", 0.95),
        (r"有(.{2,20})额度", 0.90),
        (r"有(.{2,20})模型", 0.90),
        
        # ========== 云算力领域 ==========
        (r"有(.{2,20})(?:RTX|GTX|A\d+|H\d+|4090|3090)", 0.95),
        (r"有(.{2,20})显卡", 0.95),
        (r"有(.{2,20})GPU(?:算力)?", 0.95),
        (r"有(.{2,20})算力", 0.90),
        (r"有(.{2,20})服务器", 0.90),
        (r"闲置(.{2,20})(?:GPU|显卡|算力)", 0.95),
        (r"有(.{2,20})镜像", 0.85),
        
        # ========== 电商领域 ==========
        (r"有(.{2,20})货源", 0.95),
        (r"有(.{2,20})工厂", 0.90),
        (r"有(.{2,20})仓库", 0.85),
        (r"有(.{2,20})渠道", 0.85),
        (r"有(\d+).{0,5}(?:粉丝|用户)", 0.85),
        
        # ========== 工业数字化领域 ==========
        (r"有(.{2,20})SaaS", 0.90),
        (r"有(.{2,20})软件", 0.85),
        (r"有(.{2,20})系统", 0.80),
        
        # ========== 通用资源 ==========
        (r"有(.{2,20})可以分享", 0.90),
        (r"有(.{2,20})闲置", 0.90),
        (r"有(.{2,20})资源", 0.85),
        (r"可以提供(.{2,20})", 0.85),
    ]

    # 职业信息模式
    PROFILE_PATTERNS = [
        (r"在(.{2,30})公司", 0.80),
        (r"就职于(.{2,30})", 0.85),
        (r"职业[是为](.{2,20})", 0.90),
        (r"职位[是为](.{2,20})", 0.90),
        (r"做(.{2,20})工作", 0.75),
    ]

    def __init__(self):
        self.memory_content = ""
        self.daily_contents: Dict[str, str] = {}

    def load_memories(self) -> Tuple[bool, str]:
        """加载记忆文件"""
        errors = []

        # 加载主记忆文件
        if MEMORY_FILE.exists():
            try:
                with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
                    self.memory_content = f.read()
            except Exception as e:
                errors.append(f"读取 MEMORY.md 失败: {e}")

        # 加载每日记忆（最近30天）
        if MEMORY_DIR.exists():
            for file in sorted(MEMORY_DIR.glob("*.md"), reverse=True)[:30]:
                try:
                    with open(file, 'r', encoding='utf-8') as f:
                        self.daily_contents[file.stem] = f.read()
                except Exception as e:
                    errors.append(f"读取 {file.name} 失败: {e}")

        loaded = bool(self.memory_content or self.daily_contents)
        error_msg = "; ".join(errors) if errors else ""

        return loaded, error_msg

    def extract_from_text(self, text: str, source: str) -> List[ExtractedInfo]:
        """从文本中提取信息"""
        results = []

        # 提取需求（带类型）
        for pattern_data in self.NEED_PATTERNS:
            # 支持新旧格式
            if len(pattern_data) == 3:
                pattern, confidence, need_type = pattern_data
            else:
                pattern, confidence = pattern_data
                need_type = "capability"  # 默认类型
            
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                # 跳过太短的匹配
                if len(match.group(1 if match.lastindex else 0)) < 2:
                    continue

                content = match.group(1).strip() if match.lastindex else match.group(0)
                
                # 自动推断类型
                if need_type == "auto":
                    need_type = self._infer_need_type(content)

                results.append(ExtractedInfo(
                    type="need",
                    content=self._clean_content(content),
                    source=source,
                    confidence=confidence,
                    context=match.group(0),
                    date=self._extract_date(source)
                ))
                
                # 存储 need_type 到 ExtractedInfo
                results[-1].need_type = need_type

        # 提取能力
        for pattern, confidence in self.CAPABILITY_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                # 处理带年份的模式
                if match.lastindex and match.lastindex >= 2:
                    years = match.group(1) if match.group(1).isdigit() else None
                    skill = match.group(2) if years else match.group(1)
                    content = f"{skill.strip()} ({years}年经验)" if years else skill.strip()
                else:
                    content = match.group(1).strip() if match.lastindex else match.group(0)

                results.append(ExtractedInfo(
                    type="capability",
                    content=self._clean_content(content),
                    source=source,
                    confidence=confidence,
                    context=match.group(0),
                    date=self._extract_date(source)
                ))

        # 提取资源
        for pattern, confidence in self.RESOURCE_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                content = match.group(1).strip() if match.lastindex else match.group(0)
                
                # 推断资源类型
                res_type = self._infer_resource_type(content)

                results.append(ExtractedInfo(
                    type="resource",
                    content=self._clean_content(content),
                    source=source,
                    confidence=confidence,
                    context=match.group(0),
                    date=self._extract_date(source)
                ))
                
                # 存储 res_type 到 ExtractedInfo
                results[-1].res_type = res_type

        # 提取职业信息
        for pattern, confidence in self.PROFILE_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                content = match.group(1).strip() if match.lastindex else match.group(0)

                results.append(ExtractedInfo(
                    type="profile",
                    content=self._clean_content(content),
                    source=source,
                    confidence=confidence,
                    context=match.group(0),
                    date=self._extract_date(source)
                ))

        return results

    def _infer_need_type(self, content: str) -> str:
        """根据内容推断需求类型（5大领域）"""
        # 资源类关键词
        resource_keywords = [
            # 人工智能
            'api', 'token', '额度', '模型', 'key',
            # 云算力
            'gpu', 'rtx', 'gtx', 'a100', 'h100', '4090', '3090', '显卡', '算力', '服务器', '镜像',
            # 电商
            '货源', '工厂', '仓库', 'oem', 'odm', '渠道',
            # 工业数字化
            'saas', '软件', '系统',
            # 通用
            '资源', '设备', '场地', '资金'
        ]
        
        # 能力类关键词
        capability_keywords = [
            # 人工智能
            'agent', 'ai', '图像生成', 'sd', 'stable diffusion', '短剧', '微调', 'prompt',
            # 互联网
            '开发', '前端', '后端', '全栈', '架构', '平台', 'web', 'app', '小程序',
            # 云算力
            '运维', '部署', '集群', '训练',
            # 电商
            '运营', '直播', '带货', '供应链',
            # 工业数字化
            'mes', 'erp', '集成', '数字化',
            # 通用
            '设计', '写', '做', '帮忙', '支持', '帮助'
        ]
        
        # 咨询类关键词
        consulting_keywords = [
            '建议', '咨询', '指导', '方案', '选型', '规划', '转型', '战略'
        ]
        
        # 合作类关键词
        cooperation_keywords = [
            '合伙人', '搭子', '合作伙伴', '团队', '合作'
        ]
        
        content_lower = content.lower()
        
        # 先检查合作类
        for kw in cooperation_keywords:
            if kw in content_lower:
                return "cooperation"
        
        # 再检查资源类
        for kw in resource_keywords:
            if kw.lower() in content_lower:
                return "resource"
        
        # 检查咨询类
        for kw in consulting_keywords:
            if kw in content_lower:
                return "consulting"
        
        # 检查能力类
        for kw in capability_keywords:
            if kw.lower() in content_lower:
                return "capability"
        
        return "capability"  # 默认

    def _infer_resource_type(self, content: str) -> str:
        """根据内容推断资源类型（5大领域）"""
        # 算力资源
        compute_keywords = [
            'gpu', 'rtx', 'gtx', 'a100', 'h100', '4090', '3090', '显卡', 
            '算力', '服务器', '集群', '机器'
        ]
        
        # 数据资源
        data_keywords = [
            '数据', '数据集', '语料', '用户', '流量', '粉丝',
            'api', 'token', '额度', 'key'
        ]
        
        # 工具/软件资源
        tool_keywords = [
            '工具', '软件', '账号', '镜像', '模型', 'saas', '系统'
        ]
        
        # 供应链资源
        supply_keywords = [
            '货源', '工厂', '仓库', '渠道', 'oem', 'odm'
        ]
        
        content_lower = content.lower()
        
        for kw in compute_keywords:
            if kw.lower() in content_lower:
                return "compute"
        
        for kw in data_keywords:
            if kw.lower() in content_lower:
                return "data"
        
        for kw in tool_keywords:
            if kw.lower() in content_lower:
                return "tool"
        
        for kw in supply_keywords:
            if kw.lower() in content_lower:
                return "supply"
        
        return "other"

    def _clean_content(self, text: str) -> str:
        """清理提取的内容"""
        # 移除常见的无意义词
        text = text.strip()

        # 移除标点
        text = re.sub(r'[，。！？、]+$', '', text)

        # 限制长度
        if len(text) > 50:
            text = text[:50]

        return text

    def _extract_date(self, source: str) -> Optional[str]:
        """从源文件名提取日期"""
        # 尝试匹配日期格式
        match = re.search(r'(\d{4}-\d{2}-\d{2})', source)
        if match:
            return match.group(1)
        return None

    def parse_all(self) -> Dict[str, List[ExtractedInfo]]:
        """解析所有记忆"""
        all_extractions: Dict[str, List[ExtractedInfo]] = {
            "needs": [],
            "capabilities": [],
            "resources": [],
            "profile": []
        }

        # 解析主记忆文件
        if self.memory_content:
            extractions = self.extract_from_text(self.memory_content, "MEMORY.md")

            for ext in extractions:
                if ext.type == "need":
                    all_extractions["needs"].append(ext)
                elif ext.type == "capability":
                    all_extractions["capabilities"].append(ext)
                elif ext.type == "resource":
                    all_extractions["resources"].append(ext)
                elif ext.type == "profile":
                    all_extractions["profile"].append(ext)

        # 解析每日记忆
        for date, content in self.daily_contents.items():
            extractions = self.extract_from_text(content, f"memory/{date}.md")

            for ext in extractions:
                if ext.type == "need":
                    all_extractions["needs"].append(ext)
                elif ext.type == "capability":
                    all_extractions["capabilities"].append(ext)
                elif ext.type == "resource":
                    all_extractions["resources"].append(ext)
                elif ext.type == "profile":
                    all_extractions["profile"].append(ext)

        # 去重（相同内容的只保留置信度最高的）
        for key in all_extractions:
            all_extractions[key] = self._deduplicate(all_extractions[key])

        return all_extractions

    def _deduplicate(self, items: List[ExtractedInfo]) -> List[ExtractedInfo]:
        """去重，保留置信度最高的"""
        seen = {}

        for item in items:
            # 清理内容，移除"需要"等前缀词
            clean_content = re.sub(r'^(需要|寻找|求|在找|缺少|缺)', '', item.content)
            key = clean_content.lower().strip()

            if key not in seen or item.confidence > seen[key].confidence:
                # 用清理后的内容
                item.content = clean_content.strip() if clean_content.strip() else item.content
                seen[key] = item

        return list(seen.values())

    def generate_profile(self) -> Dict:
        """生成 A2A 档案"""
        extractions = self.parse_all()

        profile = {
            "version": "1.5.0",
            "source": "memory",
            "generated_at": datetime.now().isoformat(),
            "profile": {
                "name": "",
                "role": "",
                "company": "",
                "industry": ""
            },
            "capabilities": [],
            "needs": [],
            "resources": [],
            "statistics": {
                "memory_files_scanned": 1 + len(self.daily_contents),
                "total_extractions": sum(len(v) for v in extractions.values())
            }
        }

        # 处理职业信息
        if extractions["profile"]:
            best_profile = max(extractions["profile"], key=lambda x: x.confidence)

            # 尝试提取公司
            if "公司" in best_profile.context:
                match = re.search(r'在(.+?)公司', best_profile.context)
                if match:
                    profile["profile"]["company"] = match.group(1)

            # 尝试提取职位
            if "职位" in best_profile.context or "职业" in best_profile.context:
                match = re.search(r'[职业职位][是为](.+)', best_profile.context)
                if match:
                    profile["profile"]["role"] = match.group(1)
            else:
                profile["profile"]["role"] = best_profile.content

        # 处理能力
        for cap in extractions["capabilities"]:
            # 只保留高置信度的
            if cap.confidence >= 0.80:
                profile["capabilities"].append({
                    "id": f"cap_{os.urandom(3).hex()}",
                    "skill": cap.content,
                    "confidence": round(cap.confidence, 2),
                    "source": cap.source,
                    "context": cap.context
                })

        # 处理需求
        for need in extractions["needs"]:
            if need.confidence >= 0.80:
                need_type = getattr(need, 'need_type', 'capability')  # 默认为 capability
                profile["needs"].append({
                    "id": f"need_{os.urandom(3).hex()}",
                    "description": need.content,
                    "type": need_type,  # resource / capability / consulting
                    "confidence": round(need.confidence, 2),
                    "source": need.source,
                    "status": "open"
                })

        # 处理资源
        for res in extractions["resources"]:
            if res.confidence >= 0.80:
                res_type = getattr(res, 'res_type', 'other')  # 默认为 other
                profile["resources"].append({
                    "id": f"res_{os.urandom(3).hex()}",
                    "name": res.content,
                    "type": res_type,  # compute / data / tool / other
                    "confidence": round(res.confidence, 2),
                    "source": res.source,
                    "available": True
                })

        return profile


def main():
    """主函数"""
    print("=" * 60)
    print("A2A Match - 记忆解析器")
    print("=" * 60)

    parser = MemoryParser()

    # 加载记忆
    loaded, error = parser.load_memories()

    if not loaded:
        print("\n❌ 未找到记忆文件")
        print(f"   MEMORY.md: {'存在' if MEMORY_FILE.exists() else '不存在'}")
        print(f"   memory/: {'存在' if MEMORY_DIR.exists() else '不存在'}")

        if error:
            print(f"\n错误: {error}")

        return

    print(f"\n✅ 已加载记忆文件:")
    if parser.memory_content:
        print(f"   - MEMORY.md")
    for date in parser.daily_contents.keys():
        print(f"   - memory/{date}.md")

    # 解析
    print("\n📊 解析结果:")
    extractions = parser.parse_all()

    print(f"   需求: {len(extractions['needs'])} 个")
    for need in extractions['needs'][:5]:
        print(f"      • {need.content} ({need.confidence:.0%})")

    print(f"   能力: {len(extractions['capabilities'])} 个")
    for cap in extractions['capabilities'][:5]:
        print(f"      • {cap.content} ({cap.confidence:.0%})")

    print(f"   资源: {len(extractions['resources'])} 个")
    for res in extractions['resources'][:5]:
        print(f"      • {res.content} ({res.confidence:.0%})")

    print(f"   职业: {len(extractions['profile'])} 条")
    for pro in extractions['profile'][:3]:
        print(f"      • {pro.content} ({pro.confidence:.0%})")

    # 生成档案
    print("\n📝 生成档案...")

    profile = parser.generate_profile()

    # 保存
    A2A_DIR.mkdir(parents=True, exist_ok=True)
    with open(PROFILE_PATH, 'w', encoding='utf-8') as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 档案已保存: {PROFILE_PATH}")

    # 显示统计
    print("\n📈 统计:")
    print(f"   扫描文件: {profile['statistics']['memory_files_scanned']} 个")
    print(f"   提取信息: {profile['statistics']['total_extractions']} 条")
    print(f"   有效能力: {len(profile['capabilities'])} 个")
    print(f"   有效需求: {len(profile['needs'])} 个")
    print(f"   有效资源: {len(profile['resources'])} 个")

    # 显示档案预览
    print("\n" + "=" * 60)
    print("档案预览:")
    print("=" * 60)
    print(json.dumps(profile, ensure_ascii=False, indent=2)[:500] + "...")


if __name__ == '__main__':
    main()

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
        # 资源类需求（需要实际的资源）
        (r"需要(.{2,20})资源", 0.95, "resource"),
        (r"求(.{2,20})资源", 0.95, "resource"),
        (r"缺少(.{2,20})资源", 0.90, "resource"),
        (r"在找(.{2,20})资源", 0.90, "resource"),
        (r"需要(.{2,10})算力", 0.95, "resource"),
        (r"需要(.{2,10})服务器", 0.95, "resource"),
        (r"需要(.{2,10})流量", 0.90, "resource"),
        (r"需要(.{2,10})货源", 0.90, "resource"),
        (r"需要(.{2,10})数据", 0.90, "resource"),
        
        # 能力类需求（需要人帮忙做某事）
        (r"需要(.{2,20})支持", 0.95, "capability"),
        (r"需要(.{2,20})帮助", 0.95, "capability"),
        (r"寻找(.{2,20})(?:合作|团队|伙伴)", 0.90, "capability"),
        (r"求(.{2,20})(?:渠道|人)", 0.85, "capability"),
        (r"需要.*开发.{0,10}团队", 0.90, "capability"),
        (r"需要.*设计.{0,10}支持", 0.90, "capability"),
        (r"需要.*运维.{0,10}支持", 0.90, "capability"),
        (r"需要.*推广.{0,10}渠道", 0.85, "capability"),
        
        # 咨询类需求（需要建议/咨询）
        (r"需要(.{2,20})建议", 0.90, "consulting"),
        (r"需要(.{2,20})咨询", 0.90, "consulting"),
        (r"求(.{2,20})建议", 0.85, "consulting"),
        
        # 通用需求（需根据内容判断）
        (r"在找(.{2,20})", 0.80, "auto"),
        (r"缺少(.{2,20})", 0.80, "auto"),
        (r"缺(.{2,20})", 0.75, "auto"),
        (r"需要(.{2,20})", 0.70, "auto"),
    ]

    # 能力信号模式
    CAPABILITY_PATTERNS = [
        # 非常明确的信号
        (r"我会(.{2,20})", 0.90),
        (r"我擅长(.{2,20})", 0.95),
        (r"精通(.{2,20})", 0.90),
        (r"熟悉(.{2,20})", 0.80),
        (r"有(\d+)年(.{2,10})经验", 0.95),
        (r"做(.{2,10})有(\d+)年", 0.90),

        # 职业相关
        (r"我是(.{2,10})(?:工程师|设计师|产品|运营|开发)", 0.85),
        (r"在(.{2,20})工作", 0.70),  # 较低置信度
        (r"负责(.{2,20})", 0.75),
    ]

    # 资源信号模式
    RESOURCE_PATTERNS = [
        (r"有(.{2,20})可以分享", 0.90),
        (r"有(.{2,20})闲置", 0.90),
        (r"有(.{2,20})资源", 0.85),
        (r"可以提供(.{2,20})", 0.85),
        (r"有(\d+).{0,5}(?:粉丝|用户|流量)", 0.85),
        (r"有(RTX|GTX|A\d+|H\d+)", 0.90),
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
        """根据内容推断需求类型"""
        resource_keywords = ['算力', '服务器', '机器', 'GPU', 'CPU', '流量', '数据', '资源', 
                           '货源', '场地', '设备', '资金', '投资']
        capability_keywords = ['开发', '设计', '运维', '推广', '运营', '写', '做', '帮忙',
                              '支持', '帮助', '合作', '团队']
        consulting_keywords = ['建议', '咨询', '指导', '方案', '选型', '规划']
        
        content_lower = content.lower()
        
        for kw in resource_keywords:
            if kw in content_lower:
                return "resource"
        
        for kw in consulting_keywords:
            if kw in content_lower:
                return "consulting"
        
        for kw in capability_keywords:
            if kw in content_lower:
                return "capability"
        
        return "capability"  # 默认

    def _infer_resource_type(self, content: str) -> str:
        """根据内容推断资源类型"""
        compute_keywords = ['GPU', 'CPU', '算力', '服务器', '机器', 'RTX', 'GTX', 'A100', 'H100', '4090']
        data_keywords = ['数据', '数据集', '语料', '用户', '流量', '粉丝']
        tool_keywords = ['工具', '软件', '账号', 'API', 'key']
        
        content_lower = content.lower()
        
        for kw in compute_keywords:
            if kw.lower() in content_lower:
                return "compute"
        
        for kw in data_keywords:
            if kw in content_lower:
                return "data"
        
        for kw in tool_keywords:
            if kw in content_lower:
                return "tool"
        
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

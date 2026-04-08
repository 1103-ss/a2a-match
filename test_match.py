#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试匹配逻辑
"""
import json
import sys

# 修复 Windows GBK 编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from scripts.heartbeat_check import is_match, calculate_match_v2

# 测试 is_match
print('=' * 60)
print('测试 is_match 函数')
print('=' * 60)

test_cases = [
    ('GPU算力', 'GPU算力运维'),
    ('GPU算力', 'RTX 4090 算力'),
    ('GPU运维', 'GPU算力运维'),
    ('产品经理', '产品设计'),
    ('Python开发', 'Python全栈'),
]

for text1, text2 in test_cases:
    result = is_match(text1, text2)
    print(f'{text1} vs {text2}: {result}')

print()

# 测试匹配场景
print('=' * 60)
print('测试匹配场景')
print('=' * 60)

# 场景1：需要GPU算力 vs 有GPU运维能力（应该是间接匹配）
my_profile1 = {
    'needs': [
        {'description': 'GPU算力', 'type': 'resource'}
    ],
    'capabilities': [],
    'resources': []
}

other_profile1 = {
    'needs': [],
    'capabilities': [
        {'skill': 'GPU算力运维'}
    ],
    'resources': []
}

print('场景1: 需要GPU算力(resource) vs 有GPU运维能力')
result1 = calculate_match_v2(my_profile1, other_profile1)
print(json.dumps(result1, ensure_ascii=False, indent=2))
print()

# 场景2：需要GPU算力 vs 有GPU资源（应该是精确匹配）
other_profile2 = {
    'needs': [],
    'capabilities': [],
    'resources': [
        {'name': 'RTX 4090 算力', 'type': 'compute'}
    ]
}

print('场景2: 需要GPU算力(resource) vs 有GPU资源(compute)')
result2 = calculate_match_v2(my_profile1, other_profile2)
print(json.dumps(result2, ensure_ascii=False, indent=2))
print()

# 场景3：需要GPU运维服务 vs 有GPU运维能力（应该是精确匹配）
my_profile3 = {
    'needs': [
        {'description': 'GPU运维', 'type': 'capability'}
    ],
    'capabilities': [],
    'resources': []
}

print('场景3: 需要GPU运维服务(capability) vs 有GPU运维能力')
result3 = calculate_match_v2(my_profile3, other_profile1)
print(json.dumps(result3, ensure_ascii=False, indent=2))
print()

# 场景4：需要产品经理 vs 有产品设计能力
my_profile4 = {
    'needs': [
        {'description': '产品经理', 'type': 'capability'}
    ],
    'capabilities': [],
    'resources': []
}

other_profile4 = {
    'needs': [],
    'capabilities': [
        {'skill': '产品设计'}
    ],
    'resources': []
}

print('场景4: 需要产品经理(capability) vs 有产品设计能力')
result4 = calculate_match_v2(my_profile4, other_profile4)
print(json.dumps(result4, ensure_ascii=False, indent=2))

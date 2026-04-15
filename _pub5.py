#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""直接调用 ClawHub API 发布 skill"""
import json, urllib.request, urllib.error, os, shutil, hashlib, base64, time

# Read auth token
token_file = os.path.expanduser('~/.config/clawhub/token')
if not os.path.exists(token_file):
    token_file = os.path.expanduser('~/.clawhub/token')
if not os.path.exists(token_file):
    token_file = 'C:/Users/Administrator/.config/clawhub/token'

print('Token file:', token_file, 'exists:', os.path.exists(token_file))
if os.path.exists(token_file):
    token = open(token_file).read().strip()
    print('Token found:', token[:20] + '...')
else:
    token = None
    print('No token found')

# Try API directly
REGISTRY = 'https://registry.clawhub.com'
headers = {'Content-Type': 'application/json'}
if token:
    headers['Authorization'] = 'Bearer ' + token

# Get skill info
req = urllib.request.Request(REGISTRY + '/api/skills/a2a-match', headers=headers)
try:
    with urllib.request.urlopen(req, timeout=10) as r:
        print('Skill info:', json.loads(r.read())[:500])
except Exception as e:
    print('Get info failed:', e)

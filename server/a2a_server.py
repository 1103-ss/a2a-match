"""
A2A 云端服务 MVP - Flask 版本
运行: python a2a_server.py
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import uuid
from datetime import datetime
from pathlib import Path

app = Flask(__name__)
CORS(app)

# 数据存储目录
DATA_DIR = Path(__file__).parent / 'data'
DATA_DIR.mkdir(exist_ok=True)

# 内存数据库 (MVP)
users_db = {}
profiles_db = {}
matches_db = {}
notifications_db = {}

def generate_id(prefix='id'):
    return f"{prefix}_{uuid.uuid4().hex[:12]}"

def save_data():
    """保存数据到文件"""
    data = {
        'users': users_db,
        'profiles': profiles_db,
        'matches': matches_db,
        'notifications': notifications_db
    }
    with open(DATA_DIR / 'a2a_data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_data():
    """从文件加载数据"""
    data_path = DATA_DIR / 'a2a_data.json'
    if data_path.exists():
        with open(data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            globals()['users_db'] = data.get('users', {})
            globals()['profiles_db'] = data.get('profiles', {})
            globals()['matches_db'] = data.get('matches', {})
            globals()['notifications_db'] = data.get('notifications', {})

# 启动时加载数据
load_data()

# ============ 用户认证 ============

@app.route('/api/v1/auth/register', methods=['POST'])
def register():
    """用户注册"""
    data = request.json
    
    if not data.get('email') or not data.get('password'):
        return jsonify({'status': 'error', 'message': '邮箱和密码必填'}), 400
    
    # 检查邮箱是否已注册
    for uid, user in users_db.items():
        if user.get('email') == data['email']:
            return jsonify({'status': 'error', 'message': '邮箱已注册'}), 400
    
    user_id = generate_id('user')
    users_db[user_id] = {
        'id': user_id,
        'email': data['email'],
        'name': data.get('name', ''),
        'password': data['password'],  # MVP 不加密
        'created_at': datetime.now().isoformat()
    }
    
    save_data()
    
    return jsonify({
        'status': 'success',
        'user': {
            'id': user_id,
            'email': data['email'],
            'name': data.get('name', '')
        },
        'token': f'token_{user_id}'  # MVP 简化 token
    })

@app.route('/api/v1/auth/login', methods=['POST'])
def login():
    """用户登录"""
    data = request.json
    
    for uid, user in users_db.items():
        if user.get('email') == data.get('email') and user.get('password') == data.get('password'):
            return jsonify({
                'status': 'success',
                'token': f'token_{uid}',
                'user': {
                    'id': uid,
                    'email': user['email'],
                    'name': user.get('name', '')
                }
            })
    
    return jsonify({'status': 'error', 'message': '邮箱或密码错误'}), 401

# ============ 档案管理 ============

@app.route('/api/v1/profiles', methods=['POST'])
def upload_profile():
    """上传/更新档案"""
    # MVP 简化认证
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token.startswith('token_'):
        return jsonify({'status': 'error', 'message': '未授权'}), 401
    
    user_id = token.replace('token_', '')
    data = request.json
    
    profile_id = generate_id('profile')
    data['id'] = profile_id
    data['user_id'] = user_id
    data['updated_at'] = datetime.now().isoformat()
    
    profiles_db[profile_id] = data
    
    # 触发匹配
    trigger_matching(user_id, data)
    
    save_data()
    
    return jsonify({
        'status': 'success',
        'profile_id': profile_id,
        'updated_at': data['updated_at']
    })

@app.route('/api/v1/profiles/me', methods=['GET'])
def get_my_profile():
    """获取我的档案"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token.startswith('token_'):
        return jsonify({'status': 'error', 'message': '未授权'}), 401
    
    user_id = token.replace('token_', '')
    
    # 查找用户的档案
    for pid, profile in profiles_db.items():
        if profile.get('user_id') == user_id:
            return jsonify({'status': 'success', 'profile': profile})
    
    return jsonify({'status': 'error', 'message': '档案不存在'}), 404

@app.route('/api/v1/profiles/<profile_id>', methods=['GET'])
def get_profile(profile_id):
    """获取公开档案"""
    profile = profiles_db.get(profile_id)
    if not profile:
        return jsonify({'status': 'error', 'message': '档案不存在'}), 404
    
    # 脱敏
    public_profile = {
        'id': profile['id'],
        'profile': profile.get('profile', {}),
        'capabilities': profile.get('capabilities', []),
        'resources': profile.get('resources', []),
        'needs': profile.get('needs', []),
        'business': profile.get('business', {})
    }
    
    return jsonify({'status': 'success', 'profile': public_profile})

# ============ 匹配服务 ============

def extract_keywords(text):
    """提取关键词"""
    import re
    text = text.lower()
    keywords = []
    gpu_pattern = r'(rtx\s*\d+|a\d+|h\d+|v\d+|gtx\s*\d+)'
    gpu_matches = re.findall(gpu_pattern, text, re.IGNORECASE)
    keywords.extend([g.lower().replace(' ', '') for g in gpu_matches])
    words = re.findall(r'[\u4e00-\u9fa5]+|[a-z]+|[0-9]+', text)
    keywords.extend(words)
    return list(set(keywords))

def keyword_match(text1, text2):
    """关键词匹配"""
    kw1 = set(extract_keywords(text1))
    kw2 = set(extract_keywords(text2))
    if kw1 & kw2:
        return True
    t1 = text1.lower().replace(' ', '')
    t2 = text2.lower().replace(' ', '')
    return t1 in t2 or t2 in t1

def calculate_match_score(profile_a, profile_b):
    """计算匹配分数"""
    score = 0.0
    matches = []
    
    # 能力-需求匹配
    for need in profile_a.get('needs', []):
        for cap in profile_b.get('capabilities', []):
            if keyword_match(need.get('skill', ''), cap.get('skill', '')):
                match_score = 0.4
                if need.get('priority') == 'high':
                    match_score *= 1.3
                score += match_score
                matches.append({
                    'type': 'need-capability',
                    'need': need['skill'],
                    'capability': cap['skill'],
                    'score': match_score
                })
    
    # 资源-需求匹配
    for need in profile_a.get('needs', []):
        for res in profile_b.get('resources', []):
            if keyword_match(need.get('skill', ''), res.get('name', '')):
                match_score = 0.35
                score += match_score
                matches.append({
                    'type': 'need-resource',
                    'need': need['skill'],
                    'resource': res['name'],
                    'score': match_score
                })
    
    return {
        'score': min(round(score, 2), 1.0),
        'percentage': f"{min(score, 1.0) * 100:.0f}%",
        'matches': matches
    }

def trigger_matching(user_id, new_profile):
    """触发匹配"""
    for pid, profile in profiles_db.items():
        if profile.get('user_id') == user_id:
            continue
        
        # 双向匹配
        result_a = calculate_match_score(new_profile, profile)
        result_b = calculate_match_score(profile, new_profile)
        
        if result_a['score'] >= 0.5:
            # 创建匹配记录
            match_id = generate_id('match')
            matches_db[match_id] = {
                'id': match_id,
                'user_a': user_id,
                'user_b': profile['user_id'],
                'score': result_a['percentage'],
                'matches': result_a['matches'],
                'created_at': datetime.now().isoformat()
            }
            
            # 发送通知给 user_b
            notif_id = generate_id('notif')
            notifications_db[notif_id] = {
                'id': notif_id,
                'user_id': profile['user_id'],
                'type': 'match',
                'from_user': user_id,
                'match_score': result_a['percentage'],
                'message': f"发现匹配！匹配度 {result_a['percentage']}",
                'matches': result_a['matches'],
                'read': False,
                'created_at': datetime.now().isoformat()
            }
        
        if result_b['score'] >= 0.5:
            # 反向匹配通知
            notif_id = generate_id('notif')
            notifications_db[notif_id] = {
                'id': notif_id,
                'user_id': user_id,
                'type': 'match',
                'from_user': profile['user_id'],
                'match_score': result_b['percentage'],
                'message': f"发现匹配！匹配度 {result_b['percentage']}",
                'matches': result_b['matches'],
                'read': False,
                'created_at': datetime.now().isoformat()
            }

@app.route('/api/v1/match', methods=['POST'])
def request_match():
    """请求匹配"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token.startswith('token_'):
        return jsonify({'status': 'error', 'message': '未授权'}), 401
    
    user_id = token.replace('token_', '')
    data = request.json
    
    # 找到用户的档案
    my_profile = None
    for pid, profile in profiles_db.items():
        if profile.get('user_id') == user_id:
            my_profile = profile
            break
    
    if not my_profile:
        return jsonify({'status': 'error', 'message': '请先上传档案'}), 400
    
    # 匹配所有其他档案
    results = []
    for pid, profile in profiles_db.items():
        if profile.get('user_id') == user_id:
            continue
        
        result = calculate_match_score(my_profile, profile)
        if result['score'] >= data.get('min_score', 0.5):
            results.append({
                'profile_id': pid,
                'user_name': profile.get('profile', {}).get('name', 'Unknown'),
                'match_score': result['percentage'],
                'matches': result['matches']
            })
    
    # 按分数排序
    results.sort(key=lambda x: float(x['match_score'].rstrip('%')), reverse=True)
    
    return jsonify({
        'status': 'success',
        'matches': results[:10],
        'total': len(results)
    })

@app.route('/api/v1/match/notifications', methods=['GET'])
def get_notifications():
    """获取匹配通知"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token.startswith('token_'):
        return jsonify({'status': 'error', 'message': '未授权'}), 401
    
    user_id = token.replace('token_', '')
    
    notifications = [
        n for n in notifications_db.values()
        if n.get('user_id') == user_id
    ]
    
    # 按时间排序
    notifications.sort(key=lambda x: x['created_at'], reverse=True)
    
    return jsonify({
        'status': 'success',
        'notifications': notifications
    })

# ============ 需求广播 ============

@app.route('/api/v1/broadcast/need', methods=['POST'])
def broadcast_need():
    """广播需求"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token.startswith('token_'):
        return jsonify({'status': 'error', 'message': '未授权'}), 401
    
    user_id = token.replace('token_', '')
    data = request.json
    
    # 创建广播记录
    broadcast_id = generate_id('broadcast')
    
    return jsonify({
        'status': 'success',
        'broadcast_id': broadcast_id,
        'message': '需求已广播',
        'reach_estimate': len(profiles_db)
    })

# ============ 联系对接 ============

@app.route('/api/v1/contact', methods=['POST'])
def send_contact():
    """发起联系请求"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token.startswith('token_'):
        return jsonify({'status': 'error', 'message': '未授权'}), 401
    
    user_id = token.replace('token_', '')
    data = request.json
    
    contact_id = generate_id('contact')
    
    # 发送通知给目标用户
    notif_id = generate_id('notif')
    notifications_db[notif_id] = {
        'id': notif_id,
        'user_id': data.get('to_user'),
        'type': 'contact',
        'from_user': user_id,
        'message': data.get('message', '有人想联系你'),
        'read': False,
        'created_at': datetime.now().isoformat()
    }
    
    save_data()
    
    return jsonify({
        'status': 'success',
        'contact_id': contact_id,
        'message': '联系请求已发送'
    })

# ============ 健康检查 ============

@app.route('/api/v1/health', methods=['GET'])
def health():
    """健康检查"""
    return jsonify({
        'status': 'ok',
        'service': 'A2A Match API',
        'version': '1.0.0',
        'users': len(users_db),
        'profiles': len(profiles_db)
    })

if __name__ == '__main__':
    print("=" * 50)
    print("A2A Match API MVP")
    print("=" * 50)
    print("API 文档: http://localhost:5000/api/v1/health")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=True)

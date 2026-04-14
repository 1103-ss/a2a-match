#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A2A Match WebSocket 守护进程 v2.0
实时监听云端服务器事件 → 写入事件文件 → 立即唤醒主会话

架构：
  云端服务器 → WebSocket → 守护进程 → realtime_events.json + /hooks/wake → 主会话
"""

import json, os, sys, time, signal, logging, urllib.request, urllib.error
from pathlib import Path
from datetime import datetime

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import socketio

# ==================== 配置 ====================
WORKSPACE = Path(os.environ.get('QCLAW_WORKSPACE', Path.home() / '.qclaw' / 'workspace'))
A2A_DIR = WORKSPACE / 'a2a'
CONFIG_PATH = A2A_DIR / 'cloud_config.json'
EVENTS_PATH = A2A_DIR / 'realtime_events.json'
LOG_PATH = A2A_DIR / 'ws_daemon.log'
PID_PATH = A2A_DIR / 'ws_daemon.pid'
DEFAULT_CLOUD_SERVER = "http://81.70.250.9:3000"
GATEWAY_PORT = 28789
HOOKS_TOKEN = "a2a-match-wake-2026"

logging.basicConfig(
    filename=str(LOG_PATH), level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('ws_daemon')
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch.setFormatter(logging.Formatter('%(asctime)s %(message)s', datefmt='%H:%M:%S'))
logger.addHandler(ch)

running = True


def cfg():
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def my_uid():
    return cfg().get('user', {}).get('user_id', '')


def cloud_url():
    return cfg().get('cloud', {}).get('server_url', DEFAULT_CLOUD_SERVER)


def gateway_url():
    """从 openclaw.json 读取 gateway port 和 hooks token"""
    try:
        oc = Path(os.environ.get('OPENCLAW_CONFIG_PATH', Path.home() / '.qclaw' / 'openclaw.json'))
        with open(oc, 'r', encoding='utf-8') as f:
            c = json.load(f)
        port = c.get('gateway', {}).get('port', GATEWAY_PORT)
        token = c.get('hooks', {}).get('token', HOOKS_TOKEN)
        return f'http://127.0.0.1:{port}/hooks/wake', token
    except Exception:
        return f'http://127.0.0.1:{GATEWAY_PORT}/hooks/wake', HOOKS_TOKEN


def push_event(etype, data):
    """写入实时事件到文件"""
    A2A_DIR.mkdir(parents=True, exist_ok=True)
    events = []
    if EVENTS_PATH.exists():
        try:
            with open(EVENTS_PATH, 'r', encoding='utf-8') as f:
                events = json.load(f)
        except Exception:
            events = []
    events.append({'type': etype, 'data': data, 'ts': datetime.now().isoformat()})
    if len(events) > 100:
        events = events[-100:]
    with open(EVENTS_PATH, 'w', encoding='utf-8') as f:
        json.dump(events, f, ensure_ascii=False, indent=2)


def wake_main_session(text):
    """立即唤醒主会话"""
    url, token = gateway_url()
    payload = json.dumps({'text': text, 'mode': 'now'}).encode('utf-8')
    req = urllib.request.Request(
        url, data=payload,
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            result = resp.read().decode('utf-8')
            logger.info(f'WAKE OK: {result[:100]}')
            return True
    except Exception as e:
        logger.error(f'WAKE FAILED: {e}')
        return False


def get_nickname(uid):
    if not uid:
        return '???'
    try:
        req = urllib.request.Request(cloud_url() + f'/api/profile/{uid}', timeout=5)
        with urllib.request.urlopen(req, timeout=5) as resp:
            p = json.loads(resp.read().decode('utf-8'))
            return p.get('name', uid[:16])
    except Exception:
        return uid[:16]


# ==================== Socket.IO 客户端 ====================

sio = socketio.Client(reconnection=True, reconnection_attempts=999,
                      reconnection_delay=5, reconnection_delay_max=60, logger=False)


@sio.event
def connect():
    logger.info('CONNECTED')
    uid = my_uid()
    if uid:
        sio.emit('join', uid)
        logger.info(f'Joined room: {uid[:16]}')


@sio.event
def disconnect():
    logger.info('DISCONNECTED')


@sio.on('new_matches')
def on_new_matches(data):
    logger.info(f'new_matches: {json.dumps(data, ensure_ascii=False)[:200]}')
    push_event('new_matches', data)
    wake_main_session('A2A Match: 发现新匹配，请检查')


@sio.on('match_accepted')
def on_match_accepted(data):
    logger.info(f'match_accepted: {json.dumps(data, ensure_ascii=False)[:200]}')
    push_event('match_accepted', data)
    wake_main_session('A2A Match: 对方接受了你的匹配请求')


@sio.on('new_message')
def on_new_message(data):
    from_uid = data.get('fromUserId', '')
    if from_uid and from_uid != my_uid():
        nickname = get_nickname(from_uid)
        content = data.get('content', '')
        data['fromNickname'] = nickname
        logger.info(f'new_message from {nickname}: {content[:80]}')
        push_event('new_message', data)
        wake_main_session(f'A2A Match: 收到 {nickname} 的新消息')


# ==================== 入口 ====================

def run():
    global running
    A2A_DIR.mkdir(parents=True, exist_ok=True)
    with open(PID_PATH, 'w') as f:
        f.write(str(os.getpid()))

    wake_url, _ = gateway_url()
    logger.info(f'=== WS Daemon v2.0 Start ===')
    logger.info(f'  cloud={cloud_url()}  uid={my_uid()[:16]}')
    logger.info(f'  wake={wake_url}')

    def signal_handler(sig, frame):
        global running
        running = False
        sio.disconnect()

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        sio.connect(cloud_url(), transports=['websocket', 'polling'])
        sio.wait()
    except Exception as e:
        logger.error(f'Fatal: {e}')
    finally:
        if PID_PATH.exists():
            PID_PATH.unlink()
        logger.info('Daemon stopped')


def stop():
    if not PID_PATH.exists():
        print('Not running'); return
    try:
        with open(PID_PATH, 'r') as f:
            pid = int(f.read().strip())
        os.kill(pid, signal.SIGTERM)
        print(f'Stopped PID {pid}')
    except ProcessLookupError:
        PID_PATH.unlink(missing_ok=True)
        print('Already gone, cleaned up')
    except Exception as e:
        print(f'Error: {e}')


def status():
    pid = None
    alive = False
    if PID_PATH.exists():
        try:
            with open(PID_PATH, 'r') as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)
            alive = True
        except (ProcessLookupError, ValueError):
            PID_PATH.unlink(missing_ok=True)

    evts = []
    if EVENTS_PATH.exists():
        try:
            with open(EVENTS_PATH, 'r', encoding='utf-8') as f:
                evts = json.load(f)
        except Exception:
            pass

    print(f'{"RUNNING" if alive else "STOPPED"} | PID={pid or "-"} | events={len(evts)} | uid={my_uid()[:16] or "N/A"}')
    if LOG_PATH.exists():
        try:
            with open(LOG_PATH, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            for l in lines[-5:]:
                print(f'  {l.rstrip()}')
        except Exception:
            pass


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'start'
    if cmd == 'start':   run()
    elif cmd == 'stop':  stop()
    elif cmd == 'status': status()
    else: print('Usage: ws_daemon.py [start|stop|status]')

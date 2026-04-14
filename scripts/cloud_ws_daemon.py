# -*- coding: utf-8 -*-
"""cloud_ws_daemon.py v3 - 改用 Windows start /b 启动真正后台进程"""
import json, os, sys, time, subprocess, signal, socketio
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

WORKSPACE_DIR = Path(os.environ.get('QCLAW_WORKSPACE', Path.home() / '.qclaw' / 'workspace'))
A2A_DIR = WORKSPACE_DIR / 'a2a'
CONFIG_PATH = A2A_DIR / 'cloud_config.json'
EVENTS_PATH = A2A_DIR / 'realtime_events.json'
DAEMON_PID_PATH = A2A_DIR / 'ws_daemon.pid'
LOG_PATH = A2A_DIR / 'ws_daemon.log'
CLOUD_SERVER = "http://81.70.250.9:3000"
RECONNECT_DELAY = 5
MAX_EVENTS = 100

def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    A2A_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, 'a', encoding='utf-8') as f:
        f.write(line + '\n')

def load_events():
    try:
        with open(EVENTS_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except: return []

def save_events(evs):
    with open(EVENTS_PATH, 'w', encoding='utf-8') as f:
        json.dump(evs, f, ensure_ascii=False, indent=2)

def push_event(etype, data):
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    evs = load_events()
    evs.append({'type': etype, 'data': data, 'ts': ts})
    if len(evs) > MAX_EVENTS: evs = evs[-MAX_EVENTS:]
    save_events(evs)
    log(f"[{etype}] {str(data)[:80]}")

def load_config():
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except: return {}

def get_user_id():
    return load_config().get('user', {}).get('user_id', '')

def _ws_loop(user_id):
    """实际的 WebSocket 连接循环（运行在独立进程中）"""
    while True:
        try:
            sio = socketio.Client(request_timeout=10)
            sio.on('new_matches', lambda d: push_event('new_matches', d))
            sio.on('match_accepted', lambda d: push_event('match_accepted', d))
            sio.on('new_message', lambda d: push_event('new_message', d))
            sio.connect(CLOUD_SERVER, transports=['websocket'],
                        socketio_path='/socket.io/', wait_timeout=5)
            log(f"WebSocket 已连接: {CLOUD_SERVER}")
            sio.emit('join', user_id)
            sio.wait()
        except Exception as e:
            log(f"连接失败，{RECONNECT_DELAY}秒后重连... ({e})")
            time.sleep(RECONNECT_DELAY)

def start_via_subprocess():
    """通过 start /b 启动真正的后台进程（Windows）"""
    import subprocess
    uid = get_user_id()
    if not uid:
        log("错误：未设置 user_id，请先运行 cloud_sync.py sync")
        return False

    log(f"启动实时监听，用户: {uid[:16]}...")

    # 写 PID（当前进程自己）
    with open(DAEMON_PID_PATH, 'w') as f:
        f.write(str(os.getpid()))

    # 启动独立后台进程
    script_path = __file__
    cmd = [sys.executable, script_path, '_inner_loop', uid]
    DETACHED = 0x00000008   # CREATE_NO_WINDOW = 8
    subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    stdin=subprocess.DEVNULL, creationflags=DETACHED)
    log(f"独立进程已启动")
    return True

def inner_loop(user_id):
    """_inner_loop：实际 WebSocket 运行体"""
    with open(DAEMON_PID_PATH, 'w') as f:
        f.write(str(os.getpid()))
    _ws_loop(user_id)

def start():
    import subprocess
    uid = get_user_id()
    if not uid:
        log("错误：未设置 user_id，请先运行 cloud_sync.py sync")
        return

    # 先杀掉旧进程
    stop()

    log(f"启动实时监听，用户: {uid[:16]}...")
    DETACHED = 0x00000008
    script_path = __file__
    cmd = [sys.executable, script_path, '_inner_loop', uid]
    subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    stdin=subprocess.DEVNULL, creationflags=DETACHED)
    log(f"守护进程已在后台启动 (PID见 ws_daemon.pid)")
    time.sleep(1)

def stop():
    if DAEMON_PID_PATH.exists():
        try:
            pid = int(DAEMON_PID_PATH.read_text().strip())
            os.kill(pid, signal.SIGTERM)
        except: pass
        try: DAEMON_PID_PATH.unlink()
        except: pass
        log("守护进程已停止")

def status():
    running = False
    pid = None
    if DAEMON_PID_PATH.exists():
        try:
            pid = int(DAEMON_PID_PATH.read_text().strip())
            import psutil
            running = psutil.pid_exists(pid)
        except: pass
    events = load_events()
    return {
        "running": running,
        "pid": pid,
        "user_id": get_user_id()[:16] + '...' if get_user_id() else 'N/A',
        "events_pending": len(events),
        "log": str(LOG_PATH)
    }

def fetch_events():
    evs = load_events()
    save_events([])
    return evs

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("A2A Match WebSocket 守护进程 v3.0")
        print("用法: cloud_ws_daemon.py [start|stop|status|fetch|log]")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == 'start':
        start()
    elif cmd == 'stop':
        stop()
    elif cmd == 'status':
        import json as _json
        print(_json.dumps(status(), ensure_ascii=False, indent=2))
    elif cmd == 'fetch':
        import json as _json
        print(_json.dumps(fetch_events(), ensure_ascii=False, indent=2))
    elif cmd == 'log':
        if LOG_PATH.exists():
            print(LOG_PATH.read_text(encoding='utf-8'))
        else:
            print("无日志文件")
    elif cmd == '_inner_loop':
        uid = sys.argv[2] if len(sys.argv) > 2 else get_user_id()
        inner_loop(uid)
    else:
        print(f"未知命令: {cmd}")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A2A Match 云端实时监听守护进程 v1.0
功能：
  - Socket.IO WebSocket 连接，实时接收 new_matches / match_accepted / new_message
  - 消息写入本地队列文件 ~/.qclaw/workspace/a2a/realtime_events.json
  - Skill 读取队列文件，即时向用户展示
  - 自动重连，进程常驻
"""

import json
import os
import sys
import time
import threading
import socketio
from pathlib import Path
from datetime import datetime

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

WORKSPACE_DIR = Path(os.environ.get('QCLAW_WORKSPACE', Path.home() / '.qclaw' / 'workspace'))
A2A_DIR = WORKSPACE_DIR / 'a2a'
CONFIG_PATH = A2A_DIR / 'cloud_config.json'
EVENTS_PATH = A2A_DIR / 'realtime_events.json'
DAEMON_PID_PATH = A2A_DIR / 'ws_daemon.pid'
LOG_PATH = A2A_DIR / 'ws_daemon.log'

CLOUD_SERVER = "http://81.70.250.9:3000"
RECONNECT_DELAY = 5  # 重连间隔（秒）
MAX_EVENTS = 100     # 本地队列最大条数


def log(msg):
    ts = datetime.now().strftime('%H:%M:%S')
    line = f"[{ts}] {msg}"
    print(line)
    A2A_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, 'a', encoding='utf-8') as f:
        f.write(line + '\n')


def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def get_user_id():
    cfg = load_config()
    return cfg.get('user', {}).get('user_id', '')


def load_events():
    if EVENTS_PATH.exists():
        try:
            with open(EVENTS_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: pass
    return []


def save_events(events):
    with open(EVENTS_PATH, 'w', encoding='utf-8') as f:
        json.dump(events[-MAX_EVENTS:], f, ensure_ascii=False, indent=2)


def push_event(event_type, data):
    """写入一条实时事件，Skill 下次心跳时可读取"""
    events = load_events()
    event = {
        "type": event_type,
        "data": data,
        "ts": datetime.now().isoformat()
    }
    events.append(event)
    save_events(events)

    # 日志输出
    if event_type == 'new_message':
        msg = data.get('content', '')[:30]
        print(f'\n🎯 新消息: {msg}...')
        print(f'   来自: {data.get("fromUserId","?")}  时间: {data.get("createdAt","")}\n')
    elif event_type == 'new_matches':
        print(f'\n🔔 新匹配! {len(data.get("matches",[]))} 条\n')
    elif event_type == 'match_accepted':
        print(f'\n✅ 匹配被接受了! matchId={data.get("matchId","")}\n')


class WsDaemon:
    def __init__(self):
        self.running = False
        self.sio = None
        self.user_id = ''
        self.thread = None

    def start(self):
        if self.running:
            log("已在运行中")
            return

        self.running = True
        self.user_id = get_user_id()
        if not self.user_id:
            log("错误：未设置 user_id，请先运行 cloud_sync.py sync")
            self.running = False
            return

        # 写 PID
        with open(DAEMON_PID_PATH, 'w') as f:
            f.write(str(os.getpid()))
        DAEMON_PID_PATH.chmod(0o600)

        log(f"启动实时监听，用户: {self.user_id[:16]}...")
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        while self.running:
            try:
                self.sio = socketio.Client(reconnection=True,
                                           reconnection_attempts=0,  # 无限重连由我们控制
                                           request_timeout=10)
                self.sio.connect(CLOUD_SERVER,
                                 transports=['websocket'],
                                 socketio_path='/socket.io/')

                self.sio.emit('join', self.user_id)
                log(f"WebSocket 已连接: {CLOUD_SERVER}")

                self.sio.on('new_matches', lambda d: push_event('new_matches', d))
                self.sio.on('match_accepted', lambda d: push_event('match_accepted', d))
                self.sio.on('new_message', lambda d: push_event('new_message', d))

                self.sio.wait()

            except socketio.exceptions.ConnectionError as e:
                if not self.running:
                    break
                log(f"连接失败，{RECONNECT_DELAY}秒后重连... ({e})")
                time.sleep(RECONNECT_DELAY)
            except Exception as e:
                if not self.running:
                    break
                log(f"异常: {e}，{RECONNECT_DELAY}秒后重连")
                time.sleep(RECONNECT_DELAY)

        log("WebSocket 守护进程已停止")

    def stop(self):
        log("正在停止...")
        self.running = False
        if self.sio:
            try:
                self.sio.disconnect()
            except: pass
        try:
            DAEMON_PID_PATH.unlink()
        except: pass


# ===================== 全局单例 =====================
_daemon = None
_daemon_lock = threading.Lock()


def get_daemon():
    global _daemon
    with _daemon_lock:
        if _daemon is None:
            _daemon = WsDaemon()
        return _daemon


def start_daemon():
    d = get_daemon()
    d.start()


def stop_daemon():
    d = get_daemon()
    d.stop()


def status():
    """检查守护进程是否在运行"""
    running = False
    pid = None
    if DAEMON_PID_PATH.exists():
        try:
            pid = int(DAEMON_PID_PATH.read_text().strip())
            # 简单检查进程是否存在
            if sys.platform == 'win32':
                import psutil
                running = psutil.pid_exists(pid)
            else:
                import os
                try:
                    os.kill(pid, 0)
                    running = True
                except OSError:
                    running = False
        except: pass

    return {
        "running": running,
        "pid": pid,
        "server": CLOUD_SERVER,
        "user_id": get_user_id()[:16] + '...' if get_user_id() else 'N/A',
        "log": str(LOG_PATH),
        "events_queue": str(EVENTS_PATH),
        "events_count": len(load_events())
    }


def fetch_and_clear_events():
    """Skill 调用此函数获取所有积压事件，然后清空"""
    events = load_events()
    if events:
        log(f"取出 {len(events)} 条事件")
    save_events([])
    return events


def main():
    if len(sys.argv) < 2:
        print("A2A Match WebSocket 守护进程 v1.0")
        print()
        print("用法:")
        print("  start   - 启动守护进程（后台运行）")
        print("  stop    - 停止守护进程")
        print("  status  - 查看运行状态")
        print("  fetch   - 获取并清空事件队列（供 Skill 调用）")
        print("  log     - 查看运行日志")
        print()
        print("提示：启动前请确保已运行 cloud_sync.py sync")
        return

    cmd = sys.argv[1]

    if cmd == 'start':
        start_daemon()
    elif cmd == 'stop':
        stop_daemon()
    elif cmd == 'status':
        result = status()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif cmd == 'fetch':
        events = fetch_and_clear_events()
        print(json.dumps(events, ensure_ascii=False, indent=2))
    elif cmd == 'log':
        if LOG_PATH.exists():
            print(LOG_PATH.read_text(encoding='utf-8'))
        else:
            print("无日志文件")
    else:
        print(f"未知命令: {cmd}")


if __name__ == '__main__':
    main()

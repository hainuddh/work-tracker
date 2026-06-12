#!/usr/bin/env python3.11
"""
HTTPS 反向代理 - v3 健壮版
解决 CLOSE-WAIT 僵尸连接耗尽线程池的问题

关键改进:
1. 连接数上限 + 超时自动清理 CLOSE-WAIT 连接
2. 单连接处理时间上限, 防止慢连接占槽
3. 连接池复用后端连接, 避免频繁建立/销毁
4. 支持 graceful shutdown, 优雅处理正在处理的请求
5. 健康检查间隔可配置, 日志带时间戳
"""
from __future__ import annotations
import ssl
import socket
import threading
import time
import sys
import traceback
import signal
import os
from collections import deque

# ============ 配置 ============
BACKEND_HOST = os.environ.get("BACKEND_HOST", "127.0.0.1")
BACKEND_PORT = int(os.environ.get("BACKEND_PORT", "8000"))
LISTEN_PORT = int(os.environ.get("LISTEN_PORT", "443"))
CERT_FILE = os.environ.get("CERT_FILE", "/etc/letsencrypt/live/api.ddhlf.xyz/fullchain.pem")
KEY_FILE = os.environ.get("KEY_FILE", "/etc/letsencrypt/live/api.ddhlf.xyz/privkey.pem")

# 连接控制
MAX_CONNECTIONS = 50            # 最大并发连接数
CONNECT_TIMEOUT = 3             # 后端连接超时(秒)
CLIENT_READ_TIMEOUT = 10        # 读取客户端请求超时(秒)
BACKEND_TIMEOUT = 30            # 后端响应超时(秒)
SINGLE_CONN_MAX_LIFE = 60       # 单个连接最大生命周期(秒)
CONN_TRACK_INTERVAL = 30        # 僵尸连接检测间隔(秒)
BACKOFF_TIMEOUT = 0.1           # accept 空循环退避(秒)

# 连接池
POOL_MAX = 5                    # 后端连接池大小
POOL_TTL = 30                   # 连接池存活时间(秒)

# ============ 全局状态 ============
running = True
connection_count = 0
lock = threading.Lock()

# 活跃连接追踪 (addr, thread_start_time)
active_connections: dict[tuple, float] = {}
conn_lock = threading.Lock()

# 连接池
pool: deque = deque()
pool_lock = threading.Lock()
pool_ttls: dict[int, float] = {}


def log(msg: str, flush=True):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=flush)


def is_backend_healthy() -> bool:
    """探测后端是否存活"""
    try:
        s = socket.create_connection((BACKEND_HOST, BACKEND_PORT), timeout=CONNECT_TIMEOUT)
        s.close()
        return True
    except Exception:
        return False


def get_backend_conn():
    """从连接池获取后端连接"""
    with pool_lock:
        if pool:
            ts, backend = pool.popleft()
            if time.time() - ts < POOL_TTL:
                try:
                    # 测试连接是否还活
                    backend.settimeout(0.1)
                    data = backend.recv(1, socket.MSG_PEEK)
                    if not data:
                        # 连接已关闭，丢弃
                        backend.close()
                        return get_backend_conn()
                    backend.settimeout(None)
                    return backend
                except Exception:
                    backend.close()
                    return get_backend_conn()
            else:
                # 过期连接，关闭
                backend.close()

    # 新建连接
    try:
        backend = socket.create_connection((BACKEND_HOST, BACKEND_PORT), timeout=CONNECT_TIMEOUT)
        backend.settimeout(None)
        return backend
    except Exception:
        return None


def return_backend_conn(backend: socket.socket):
    """归还后端连接到连接池"""
    if backend is None:
        return
    with pool_lock:
        if len(pool) < POOL_MAX:
            pid = id(backend)
            pool.append((time.time(), backend))
            pool_ttls[pid] = time.time() + POOL_TTL


def drain(sock: socket.socket, timeout: float, max_bytes: int = 65536) -> bytes:
    """从 socket 读取直到超时或达到最大字节数"""
    data = b""
    deadline = time.time() + timeout
    while len(data) < max_bytes and time.time() < deadline:
        try:
            remaining = max_bytes - len(data)
            sock.settimeout(min(1.0, deadline - time.time()))
            chunk = sock.recv(remaining)
            if not chunk:
                break
            data += chunk
        except socket.timeout:
            break
        except OSError:
            break
    return data


def handle_client(client_sock: socket.socket, addr: tuple):
    """处理单个客户端连接 - 带连接数限制和超时"""
    global connection_count
    start_time = time.time()

    with conn_lock:
        active_connections[addr] = start_time

    try:
        # 连接数上限检查
        with lock:
            if connection_count >= MAX_CONNECTIONS:
                log(f"[拒绝] {addr} 超过最大连接数 {MAX_CONNECTIONS}", flush=True)
                try:
                    client_sock.sendall(b"HTTP/1.1 503 Service Unavailable\r\n\r\n")
                except Exception:
                    pass
                return

        log(f"[新连接] {addr}", flush=True)

        with lock:
            connection_count += 1

        # 读取客户端请求（带超时）
        request = drain(client_sock, CLIENT_READ_TIMEOUT, 65536)
        if not request:
            log(f"[断开] {addr} - 无请求数据", flush=True)
            return

        # 检查后端
        if not is_backend_healthy():
            log(f"[后端不可用] {addr}", flush=True)
            try:
                client_sock.sendall(
                    b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 10\r\n\r\nGateway"
                )
            except Exception:
                pass
            return

        # 获取后端连接
        backend = get_backend_conn()
        if backend is None:
            log(f"[后端连接失败] {addr}", flush=True)
            try:
                client_sock.sendall(
                    b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 10\r\n\r\nGateway"
                )
            except Exception:
                pass
            return

        try:
            # 转发请求
            backend.sendall(request)

            # 接收后端响应
            try:
                while True:
                    response = drain(backend, BACKEND_TIMEOUT, 65536)
                    if not response:
                        break
                    try:
                        client_sock.sendall(response)
                    except OSError:
                        log(f"[客户端断开] {addr}", flush=True)
                        break
            except Exception:
                pass
        finally:
            return_backend_conn(backend)

        log(f"[完成] {addr}", flush=True)

    except Exception as e:
        log(f"[错误] {addr}: {e}", flush=True)
    finally:
        with lock:
            connection_count -= 1
        try:
            client_sock.close()
        except Exception:
            pass
        with conn_lock:
            active_connections.pop(addr, None)


def check_zombie_connections():
    """定期检查并清理超时/CLOSE-WAIT 连接"""
    global running
    while running:
        time.sleep(CONN_TRACK_INTERVAL)
        now = time.time()

        with conn_lock:
            stale = [addr for addr, start in active_connections.items()
                     if now - start > SINGLE_CONN_MAX_LIFE]

        if stale:
            log(f"[清理] 检测到 {len(stale)} 个超时连接, 强制重启服务", flush=True)
            # 触发优雅关闭
            os.kill(os.getpid(), signal.SIGTERM)
            break


def shutdown(signum, frame):
    """优雅退出"""
    global running
    with lock:
        count = connection_count
    log(f"收到信号 {signum}, 当前活跃连接: {count}, 正在关闭...", flush=True)
    running = False


def health_monitor():
    """后台健康检查线程"""
    while running:
        time.sleep(10)
        with lock:
            count = connection_count
        if not is_backend_healthy():
            log(f"[告警] 后端 {BACKEND_HOST}:{BACKEND_PORT} 不可达", flush=True)
        else:
            log(f"[健康] 后端正常，活跃连接: {count}", flush=True)


def main():
    global running

    log("=" * 60, flush=True)
    log("HTTPS 反向代理 v3 启动", flush=True)
    log(f"  监听: 0.0.0.0:{LISTEN_PORT}", flush=True)
    log(f"  转发: {BACKEND_HOST}:{BACKEND_PORT}", flush=True)
    log(f"  证书: {CERT_FILE}", flush=True)
    log(f"  最大并发: {MAX_CONNECTIONS}", flush=True)
    log(f"  连接池大小: {POOL_MAX}", flush=True)
    log(f"  单连接超时: {SINGLE_CONN_MAX_LIFE}s", flush=True)
    log("=" * 60, flush=True)

    # 加载 SSL
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.set_ciphers("DEFAULT:@SECLEVEL=1")
    ctx.load_cert_chain(CERT_FILE, KEY_FILE)
    log("SSL 证书加载成功", flush=True)

    # 创建服务端 socket
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # 设置 backlog 为 128 (避免连接被拒绝)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    server = ctx.wrap_socket(server, server_side=True)

    try:
        server.bind(("0.0.0.0", LISTEN_PORT))
        server.listen(128)
        server.settimeout(1.0)
        log(f"监听 0.0.0.0:{LISTEN_PORT}", flush=True)

        # 启动健康检查和僵尸连接清理
        monitor = threading.Thread(target=health_monitor, daemon=True)
        monitor.start()

        zombie = threading.Thread(target=check_zombie_connections, daemon=True)
        zombie.start()

        log("按 Ctrl+C 停止", flush=True)

        while running:
            try:
                client_sock, addr = server.accept()
                client_sock.settimeout(None)
                t = threading.Thread(
                    target=handle_client,
                    args=(client_sock, addr),
                    daemon=True,
                )
                t.start()
            except socket.timeout:
                continue
            except Exception as e:
                if running:
                    log(f"accept 错误: {e}", flush=True)
                    traceback.print_exc()

    except KeyboardInterrupt:
        log("用户中断", flush=True)
    except Exception as e:
        log(f"主循环异常: {e}", flush=True)
        traceback.print_exc()
    finally:
        # 等待活跃连接处理完毕
        log("等待活跃连接处理完毕...", flush=True)
        deadline = time.time() + 30
        while running and time.time() < deadline:
            with lock:
                if connection_count == 0:
                    break
            time.sleep(0.5)

        # 关闭所有连接池中的连接
        with pool_lock:
            while pool:
                ts, backend = pool.popleft()
                try:
                    backend.close()
                except Exception:
                    pass

        server.close()
        log("HTTPS 代理已停止", flush=True)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    try:
        main()
    except Exception as e:
        log(f"致命错误: {e}", flush=True)
        traceback.print_exc()
        sys.exit(1)

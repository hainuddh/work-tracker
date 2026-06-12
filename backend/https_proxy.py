#!/usr/bin/env python3.11
"""
HTTPS 反向代理 - 监听 443, 转发到 127.0.0.1:8000
"""
import ssl
import socket
import threading
import selectors
import os
import signal

BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 8000
LISTEN_PORT = 443

CERT_FILE = "/etc/letsencrypt/live/api.ddhlf.xyz/fullchain.pem"
KEY_FILE = "/etc/letsencrypt/live/api.ddhlf.xyz/privkey.pem"

# Copy to readable location if not already there
import shutil
os.makedirs("/home/admin/ssl", exist_ok=True)
shutil.copy2(CERT_FILE, "/home/admin/ssl/cert.pem")
shutil.copy2(KEY_FILE, "/home/admin/ssl/key.pem")
CERT_FILE = "/home/admin/ssl/cert.pem"
KEY_FILE = "/home/admin/ssl/key.pem"

running = True


def handle_client(client_sock):
    backend = None
    try:
        header = client_sock.recv(8192)
        if not header:
            return

        backend = socket.create_connection((BACKEND_HOST, BACKEND_PORT))
        backend.send(header)

        def forward(src, dst):
            try:
                while True:
                    data = src.recv(4096)
                    if not data:
                        break
                    dst.send(data)
                dst.shutdown(socket.SHUT_WR)
            except:
                pass

        t1 = threading.Thread(target=forward, args=(client_sock, backend), daemon=True)
        t2 = threading.Thread(target=forward, args=(backend, client_sock), daemon=True)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

    except Exception as e:
        pass
    finally:
        try:
            if client_sock:
                client_sock.close()
        except:
            pass
        try:
            if backend:
                backend.close()
        except:
            pass


def shutdown(signum, frame):
    global running
    print("\n shutting down...")
    running = False


def main():
    global running
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    print(f"HTTPS 代理: 443 -> 127.0.0.1:8000")

    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.load_cert_chain(CERT_FILE, KEY_FILE)

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server = ctx.wrap_socket(server, server_side=True)

    try:
        server.bind(("", LISTEN_PORT))
        server.listen(100)
        print(f"监听 0.0.0.0:{LISTEN_PORT}")
        print("按 Ctrl+C 停止")

        while running:
            try:
                client_sock, addr = server.accept()
                t = threading.Thread(target=handle_client, args=(client_sock,), daemon=True)
                t.start()
            except:
                break

    finally:
        server.close()


if __name__ == "__main__":
    main()

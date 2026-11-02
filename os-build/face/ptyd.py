"""pty bridge: raw-TCP loopback daemon giving one 80x24 bash session at a time.

Protocol: TCP 127.0.0.1:18933, no framing (raw bytes both ways).
Each connection forks `bash -i` on a fresh pty; one client at a time.
Busy clients get b'\\r\\n[busy]\\r\\n' then close.
No resize protocol: slave winsize fixed at 80x24 (see LIMIT). Linux-only
(pty.fork, termios.TIOCSWINSZ, fcntl.ioctl). Stdlib only.
Selftest: python3 ptyd.py --selftest
"""
import fcntl
import os
import pty
import select
import signal
import socket
import struct
import sys
import termios
import threading

HOST, PORT = "127.0.0.1", 18933
BUSY = b"\r\n[busy]\r\n"
LOCK = threading.Lock()


def _pump(conn, master):
    while True:
        r, _, _ = select.select([conn, master], [], [], 60.0)
        if conn in r:
            try:
                data = conn.recv(65536)
            except OSError:
                break
            if not data:
                break
            try:
                os.write(master, data)
            except OSError:
                break
        if master in r:
            try:
                data = os.read(master, 65536)
            except OSError:
                break  # EIO: child exited on Linux
            if not data:
                break
            try:
                conn.sendall(data)
            except OSError:
                break


def handle(conn):
    if not LOCK.acquire(blocking=False):
        try:
            conn.sendall(BUSY)
        except OSError:
            pass
        conn.close()
        return
    try:
        pid, master = pty.fork()
        if pid == 0:
            try:
                fcntl.ioctl(1, termios.TIOCSWINSZ,
                            struct.pack("HHHH", 24, 80, 0, 0))
            except OSError:
                pass
            os.execvp("/bin/bash", ["bash", "-i"])
        try:
            _pump(conn, master)
        finally:
            try:
                conn.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            conn.close()
            try:
                os.close(master)
            except OSError:
                pass
            try:
                os.kill(pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
            try:
                os.waitpid(pid, 0)
            except (ChildProcessError, InterruptedError):
                pass
    finally:
        LOCK.release()


def serve(host=HOST, port=PORT):
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((host, port))
    srv.listen(8)
    while True:
        conn, _ = srv.accept()
        threading.Thread(target=handle, args=(conn,), daemon=True).start()


def selftest(host=HOST, port=PORT):
    threading.Thread(target=serve, kwargs={"host": host, "port": port},
                     daemon=True).start()
    import time
    deadline = time.time() + 6.0
    while True:
        try:
            c = socket.create_connection((host, port), timeout=2)
            break
        except OSError:
            if time.time() > deadline:
                print("FAIL: server did not start");
                return 1
            time.sleep(0.1)
    c.settimeout(5)
    c.sendall(b"echo MARKER123\n")
    buf = b""
    try:
        while time.time() < deadline:
            try:
                chunk = c.recv(65536)
            except socket.timeout:
                break
            if not chunk:
                break
            buf += chunk
            if b"MARKER123" in buf:
                print("PASS")
                c.close()
                return 0
    except OSError as e:
        print("FAIL: %r last=%r" % (e, buf[-200:]))
        return 1
    print("FAIL: marker missing last=%r" % buf[-200:])
    return 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    serve()

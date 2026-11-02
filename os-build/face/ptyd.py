"""pty bridge: raw-TCP + WebSocket loopback daemon, one 80x24 bash at a time.

Ports: TCP 127.0.0.1:18933, loopback only, stdlib only, Linux guest.
- Raw TCP (nc, selftest): connect, bytes pump both ways to `bash -i`
  on a fresh pty. One client at a time; busy clients get
  b'\\r\\n[busy]\\r\\n' then close.
- WebSocket (browser Terminal): GET / with `Upgrade: websocket`
  (RFC 6455, handshake via hashlib+base64, stdlib only). After the
  101 response, client frames (masked text/binary) pump to the pty
  and pty output returns as unmasked binary frames. Ping->pong,
  close handshake honoured.
- No resize protocol: slave winsize fixed at 80x24 (see LIMIT).
Selftest: python3 ptyd.py --selftest        (raw TCP path)
WS selftest: python3 ptyd.py --selftest-ws  (handshake + echo path)
"""
import base64
import fcntl
import hashlib
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
WS_MAGIC = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


def _pump_raw(conn, master, pre=b""):
    if pre:
        try:
            os.write(master, pre)
        except OSError:
            pass
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


def _ws_send(conn, payload):
    if isinstance(payload, str):
        payload = payload.encode("utf-8", "replace")
    hdr = bytes([0x82])
    n = len(payload)
    if n < 126:
        hdr += bytes([n])
    elif n < 65536:
        hdr += bytes([126]) + struct.pack("!H", n)
    else:
        hdr += bytes([127]) + struct.pack("!Q", n)
    conn.sendall(hdr + payload)


def _ws_recv_frames(buf):
    """Parse masked client frames in buf. Returns (msgs, pongs, closed, rest)."""
    msgs = []
    pongs = []
    closed = False
    while len(buf) >= 2:
        b1, b2 = buf[0], buf[1]
        fin = (b1 & 0x80) != 0
        op = b1 & 0x0F
        masked = (b2 & 0x80) != 0
        ln = b2 & 0x7F
        idx = 2
        if ln == 126:
            if len(buf) < 4:
                break
            ln = struct.unpack("!H", buf[2:4])[0]
            idx = 4
        elif ln == 127:
            if len(buf) < 10:
                break
            ln = struct.unpack("!Q", buf[2:10])[0]
            idx = 10
        if not masked:
            break  # protocol violation: client must mask; drop rest
        if len(buf) < idx + 4 + ln:
            break
        mask = buf[idx:idx + 4]
        idx += 4
        payload = bytes(buf[idx + i] ^ mask[i % 4] for i in range(ln))
        idx += ln
        buf = buf[idx:]
        if op == 0x8:
            closed = True
            break
        elif op == 0x9:
            pongs.append(payload)
        elif op in (0x1, 0x2, 0x0):
            void = fin  # no fragmentation reassembly: 80x24 shell fits
            msgs.append(payload)
        # ignore other opcodes
    return msgs, pongs, closed, buf


def _pump_ws(conn, master):
    conn.settimeout(60.0)
    buf = b""
    conn.sendall(b"")  # keepalive no-op
    while True:
        r, _, _ = select.select([conn, master], [], [], 60.0)
        if conn in r:
            try:
                data = conn.recv(65536)
            except (OSError, socket.timeout):
                break
            if not data:
                break
            buf += data
            try:
                msgs, pongs, closed, buf = _ws_recv_frames(buf)
            except Exception:
                break
            for pong in pongs:
                try:
                    hdr = bytes([0x8A, len(pong) if len(pong) < 126 else 126])
                    conn.sendall(hdr + pong)
                except OSError:
                    pass
            if closed:
                try:
                    conn.sendall(b"\x88\x00")
                except OSError:
                    pass
                break
            for m in msgs:
                try:
                    os.write(master, m)
                except OSError:
                    break
        if master in r:
            try:
                data = os.read(master, 65536)
            except OSError:
                break
            if not data:
                break
            try:
                _ws_send(conn, data)
            except OSError:
                break


def _spawn_shell():
    pid, master = pty.fork()
    if pid == 0:
        try:
            fcntl.ioctl(1, termios.TIOCSWINSZ,
                         struct.pack("HHHH", 24, 80, 0, 0))
        except OSError:
            pass
        os.execvp("/bin/bash", ["bash", "-i"])
    return pid, master


def _cleanup(conn, master, pid):
    try:
        conn.shutdown(socket.SHUT_RDWR)
    except OSError:
        pass
    try:
        conn.close()
    except OSError:
        pass
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


def handle(conn):
    conn.settimeout(3.0)
    try:
        first = conn.recv(4096)
    except (OSError, socket.timeout):
        first = b""
    is_ws = first.startswith(b"GET ")
    if is_ws and b"Upgrade" not in first and b"upgrade" not in first:
        try:
            conn.sendall(b"HTTP/1.1 400 need-websocket-upgrade\r\n"
                         b"Content-Length: 0\r\nConnection: close\r\n\r\n")
        except OSError:
            pass
        conn.close()
        return
    if not LOCK.acquire(blocking=False):
        try:
            if is_ws:
                conn.sendall(b"HTTP/1.1 503 busy\r\nContent-Length: 0\r\n"
                             b"Connection: close\r\n\r\n")
            else:
                conn.sendall(BUSY)
        except OSError:
            pass
        conn.close()
        return
    try:
        if is_ws:
            try:
                head = first.decode("latin1")
            except Exception:
                head = ""
            key = ""
            for line in head.split("\r\n"):
                if line.lower().startswith("sec-websocket-key:"):
                    key = line.split(":", 1)[1].strip()
                    break
            if not key:
                try:
                    conn.sendall(b"HTTP/1.1 400 missing-key\r\nContent-Length: 0\r\n"
                                 b"Connection: close\r\n\r\n")
                except OSError:
                    pass
                conn.close()
                return
            accept = base64.b64encode(
                hashlib.sha1((key + WS_MAGIC).encode()).digest()).decode()
            try:
                conn.sendall(("HTTP/1.1 101 Switching Protocols\r\n"
                              "Upgrade: websocket\r\nConnection: Upgrade\r\n"
                              "Sec-WebSocket-Accept: " + accept + "\r\n\r\n").encode())
            except OSError:
                conn.close()
                return
            conn.settimeout(60.0)
            pid, master = _spawn_shell()
            try:
                _pump_ws(conn, master)
            finally:
                _cleanup(conn, master, pid)
        else:
            pid, master = _spawn_shell()
            try:
                _pump_raw(conn, master, pre=first)
            finally:
                _cleanup(conn, master, pid)
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
                print("FAIL: server did not start")
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


def selftest_ws(host=HOST, port=PORT):
    import time
    threading.Thread(target=serve, kwargs={"host": host, "port": port},
                     daemon=True).start()
    time.sleep(0.5)
    c = socket.create_connection((host, port), timeout=5)
    key = base64.b64encode(os.urandom(16)).decode()
    c.sendall(("GET / HTTP/1.1\r\nHost: %s:%d\r\nUpgrade: websocket\r\n"
               "Connection: Upgrade\r\nSec-WebSocket-Key: %s\r\n"
               "Sec-WebSocket-Version: 13\r\n\r\n" % (host, port, key)).encode())
    resp = b""
    c.settimeout(5)
    while b"\r\n\r\n" not in resp:
        chunk = c.recv(4096)
        if not chunk:
            print("FAIL: no handshake")
            return 1
        resp += chunk
    if b"101" not in resp.split(b"\r\n", 1)[0]:
        print("FAIL: handshake %r" % resp[:120])
        return 1
    payload = b"echo WSMARKER456\n"
    mask = os.urandom(4)
    masked = bytes(payload[i] ^ mask[i % 4] for i in range(len(payload)))
    c.sendall(bytes([0x82, 0x80 | len(payload)]) + mask + masked)
    buf = b""
    deadline = time.time() + 6.0
    while time.time() < deadline:
        try:
            chunk = c.recv(65536)
        except socket.timeout:
            break
        if not chunk:
            break
        buf += chunk
        if b"WSMARKER456" in buf:
            print("PASS")
            c.close()
            return 0
    print("FAIL: marker missing last=%r" % buf[-200:])
    return 1


if __name__ == "__main__":
    if "--selftest-ws" in sys.argv:
        sys.exit(selftest_ws())
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    serve()

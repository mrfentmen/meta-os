#!/usr/bin/env python3
"""vnc_type.py — type text into a QEMU VNC console, stdlib only.

Why this exists: proving K3's keyboard path needs a real key to travel
PS/2 controller -> IRQ1 -> ring buffer -> shell. QEMU's monitor `sendkey`
looks like it does that and does not: it routes through the display's input
handler, and a VNC display with no connected client has none, so the events
are accepted and dropped. The tell was a monitor transcript with no errors and
a kernel log with no scancode.

A VNC client *does* own the input handler, so this connects the way a viewer
does (RFB 3.8, security type None), completes the handshake, and sends
KeyEvent messages. QEMU translates each keysym into set-2 scancodes for the
emulated i8042 — the same bytes a human's keyboard would produce. Nothing is
injected into the kernel, only into the emulated hardware.

Usage: vnc_type.py [host] [port] "text with \\n for Return"
       vnc_type.py 127.0.0.1 5909 "uptime\n"
"""

import socket
import struct
import sys
import time

RETURN = 0xFF0D
BACKSPACE = 0xFF08


def recv_exact(sock, count):
    buf = b""
    while len(buf) < count:
        chunk = sock.recv(count - len(buf))
        if not chunk:
            raise OSError("VNC server closed the connection during handshake")
        buf += chunk
    return buf


def handshake(sock):
    version = recv_exact(sock, 12)
    if not version.startswith(b"RFB "):
        raise OSError(f"not a VNC server: {version!r}")
    # 3.8 is what QEMU offers; replying with it keeps the exchange simple.
    sock.sendall(b"RFB 003.008\n")
    count = recv_exact(sock, 1)[0]
    if count == 0:
        reason_len = struct.unpack(">I", recv_exact(sock, 4))[0]
        raise OSError(f"server refused: {recv_exact(sock, reason_len)!r}")
    types = recv_exact(sock, count)
    if 1 not in types:
        raise OSError(f"no 'None' security offered (types {list(types)})")
    sock.sendall(bytes([1]))  # choose None
    result = struct.unpack(">I", recv_exact(sock, 4))[0]
    if result != 0:
        raise OSError(f"security handshake failed ({result})")
    sock.sendall(bytes([1]))  # ClientInit: shared desktop
    server_init = recv_exact(sock, 24)  # ServerInit: size, pixel format, name len
    width, height = struct.unpack(">HH", server_init[0:4])
    # QEMU's VNC server only treats a client as an input source once it has
    # asked for pixels. FramebufferUpdateRequest (type 3): incremental is one
    # byte, then x, y, w, h as u16 — 10 bytes total. Packing incremental as a
    # u16 makes it 11 and QEMU closes the connection mid-typing, which is the
    # broken-pipe shape this had on its first run.
    sock.sendall(struct.pack(">BBHHHH", 3, 0, 0, 0, width, height))


def key_event(sock, keysym, down):
    sock.sendall(struct.pack(">BBHI", 4, 1 if down else 0, 0, keysym))


def type_text(sock, text, delay):
    for ch in text:
        keysym = RETURN if ch == "\n" else (BACKSPACE if ch == "\b" else ord(ch))
        key_event(sock, keysym, True)
        time.sleep(delay / 2)
        key_event(sock, keysym, False)
        time.sleep(delay / 2)


def main(argv):
    host = argv[1] if len(argv) > 1 else "127.0.0.1"
    port = int(argv[2]) if len(argv) > 2 else 5909
    text = argv[3] if len(argv) > 3 else "uptime\n"
    delay = float(argv[4]) if len(argv) > 4 else 0.08

    with socket.create_connection((host, port), timeout=10) as sock:
        sock.settimeout(10)
        handshake(sock)
        type_text(sock, text, delay)
        # Let QEMU flush the last release before the socket closes.
        time.sleep(0.2)
    print(f"vnc_type: typed {len(text)} keys into {host}:{port}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

#!/usr/bin/env python3
"""Type into the Meta OS shell over the QEMU HMP monitor.

Two modes, so both a human and os-build/gate.sh can use it:

  standalone (starts its own QEMU):
      drive.py --wait 9 help status
  attach (QEMU already running, gate mode):
      drive.py --monitor /tmp/mon.sock help status

Keys go over `sendkey`, i.e. real PS/2 scancodes into the kernel's own
keyboard path -- not a serial console, because there isn't one.

Each argument is typed then Enter. Characters are mapped to QEMU key
names; anything unlisted is passed through as-is (single letters and
digits work verbatim).
"""
import argparse
import os
import socket
import subprocess
import sys
import time

KEYMAP = {
    " ": "spc",
    "/": "slash",
    ".": "dot",
    "-": "minus",
    "_": "shift-minus",
    "=": "equal",
    ":": "shift-semicolon",
    ",": "comma",
}


def connect(path, timeout=2.0):
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(path)
    s.settimeout(timeout)
    time.sleep(0.3)
    try:
        s.recv(65536)
    except socket.timeout:
        pass
    return s


def send(sock, cmd):
    sock.sendall((cmd + "\n").encode())
    time.sleep(0.08)
    try:
        sock.recv(65536)
    except socket.timeout:
        pass


def type_words(sock, words, settle=0.6):
    for word in words:
        for ch in word:
            send(sock, f"sendkey {KEYMAP.get(ch, ch)}")
        send(sock, "sendkey ret")
        time.sleep(settle)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("words", nargs="*", help="each is typed then Enter")
    ap.add_argument("--monitor", help="attach to an existing HMP unix socket")
    ap.add_argument("--image", default="kernel/target/x86_64-unknown-none/debug/bootimage-metaos-kernel.bin")
    ap.add_argument("--log", default="/tmp/boot-drive.txt")
    ap.add_argument("--socket", default="/tmp/mon-drive.sock")
    ap.add_argument("--wait", type=float, default=9.0, help="seconds to let the guest boot")
    args = ap.parse_args()

    if args.monitor:
        if not args.words:
            ap.error("give at least one word to type")
        type_words(connect(args.monitor), args.words)
        return 0

    # No-boot guard (OS-4): standalone mode starts its own QEMU. Attach mode
    # above does not boot, so it is not guarded. The flag is read from the
    # exported environment only: os.environ, never argv, never a file.
    if os.environ.get("METAOS_ALLOW_QEMU") != "1":
        sys.stderr.write(
            "refused: drive.py boots QEMU. "
            "set METAOS_ALLOW_QEMU=1 to allow it.\n"
        )
        return 2

    subprocess.run(["rm", "-f", args.log, args.socket], check=False)
    qemu = subprocess.Popen(
        [
            "qemu-system-x86_64",
            "-drive", f"format=raw,file={args.image}",
            "-display", "none",
            "-no-reboot",
            "-m", "128M",
            "-serial", f"file:{args.log}",
            "-monitor", f"unix:{args.socket},server,nowait",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(args.wait)
    if args.words:
        type_words(connect(args.socket), args.words)
    time.sleep(1.0)
    qemu.terminate()
    time.sleep(0.5)

    with open(args.log) as fh:
        sys.stdout.write(fh.read())
    return 0


if __name__ == "__main__":
    sys.exit(main())

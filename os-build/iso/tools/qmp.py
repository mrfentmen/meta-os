#!/usr/bin/env python3
"""Minimal QEMU QMP client for the MetaOS install proof.

Why not pexpect/VNC: QMP is a documented JSON protocol over a unix socket,
available in every qemu build, and `screendump` is exactly the artifact the
acceptance test needs. No third-party python packages.

Subcommands
  screendump PATH     write the current framebuffer as PNG
  key ret,tab,...     send one QKeyCode sequence
  type TEXT           type ascii text (letters, digits, space, dot, dash, colon)
  wait MS             sleep
  status              print VM run state
  quit                request shutdown

Example
  python3 qmp.py --socket /tmp/metaos-qmp.sock screendump /tmp/boot.png
"""

import argparse
import json
import os
import socket
import sys
import time


class QMPError(RuntimeError):
    pass


class QMP:
    def __init__(self, path, timeout=20.0):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(timeout)
        self.sock.connect(path)
        self.fh = self.sock.makefile("rwb")
        self._read()                      # greeting
        self.execute("qmp_capabilities")

    def _read(self):
        line = self.fh.readline()
        if not line:
            raise QMPError("QMP closed the connection")
        try:
            return json.loads(line.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise QMPError(f"bad QMP line: {line!r}") from exc

    def execute(self, command, **arguments):
        msg = {"execute": command}
        if arguments:
            msg["arguments"] = arguments
        self.fh.write((json.dumps(msg) + "\n").encode("utf-8"))
        self.fh.flush()
        while True:
            resp = self._read()
            if "event" in resp:
                continue
            if "error" in resp:
                err = resp["error"]
                raise QMPError(f"{command}: {err.get('desc', err)}")
            return resp.get("return")

    def close(self):
        try:
            self.fh.close()
        finally:
            self.sock.close()


SHIFTED = {
    "!": "1", "@": "2", "#": "3", "$": "4", "%": "5", "^": "6",
    "&": "7", "*": "8", "(": "9", ")": "0", "_": "minus", "+": "equal",
    ":": "semicolon", '"': "apostrophe", "?": "slash", "<": "comma", ">": "dot",
}

PLAIN = {
    " ": "spc", ".": "dot", ",": "comma", "-": "minus", "_": "minus",
    "/": "slash", ":": "semicolon", ";": "semicolon", "'": "apostrophe",
    "\n": "ret", "\t": "tab", "=": "equal", "(": "shift-9", ")": "shift-0",
}


def char_keys(ch):
    if ch.isdigit() or (ch.isalpha() and ch.islower()):
        return [ch]
    if ch.isalpha() and ch.isupper():
        return ["shift", ch.lower()]
    if ch in PLAIN:
        seq = PLAIN[ch]
        return seq.split("-")
    if ch in SHIFTED:
        return ["shift", SHIFTED[ch]]
    raise QMPError(f"type: no key mapping for {ch!r}")


def main(argv=None):
    ap = argparse.ArgumentParser(description="QEMU QMP client (MetaOS proof harness)")
    ap.add_argument("--socket", required=True, help="QMP unix socket path")
    ap.add_argument("--timeout", type=float, default=20.0)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_shot = sub.add_parser("screendump")
    p_shot.add_argument("path")

    p_key = sub.add_parser("key")
    p_key.add_argument("keys", help="comma separated QKeyCodes, e.g. ret,tab")

    p_type = sub.add_parser("type")
    p_type.add_argument("text")

    p_wait = sub.add_parser("wait")
    p_wait.add_argument("ms", type=int)

    sub.add_parser("status")
    sub.add_parser("quit")

    args = ap.parse_args(argv)
    qmp = QMP(args.socket, timeout=args.timeout)
    try:
        if args.cmd == "screendump":
            out = os.path.abspath(args.path)
            os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
            qmp.execute("screendump", filename=out)
            deadline = time.time() + 10
            while time.time() < deadline:
                if os.path.exists(out) and os.path.getsize(out) > 0:
                    print(out)
                    return 0
                time.sleep(0.1)
            raise QMPError(f"screendump wrote nothing to {out}")
        if args.cmd == "key":
            keys = [k for k in (s.strip() for s in args.keys.split(",")) if k]
            if not keys:
                raise QMPError("key: empty key list")
            qmp.execute("send-key", keys=[{"type": "qcode", "data": k} for k in keys])
            return 0
        if args.cmd == "type":
            for ch in args.text:
                qmp.execute("send-key", keys=[{"type": "qcode", "data": k} for k in char_keys(ch)])
                time.sleep(0.03)
            return 0
        if args.cmd == "wait":
            time.sleep(args.ms / 1000.0)
            return 0
        if args.cmd == "status":
            print(qmp.execute("query-status").get("status", "unknown"))
            return 0
        if args.cmd == "quit":
            qmp.execute("quit")
            return 0
        raise QMPError(f"unhandled command {args.cmd}")
    finally:
        qmp.close()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (QMPError, OSError) as exc:
        print(f"qmp: {exc}", file=sys.stderr)
        sys.exit(1)

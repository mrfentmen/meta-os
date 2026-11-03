#!/usr/bin/env python3
"""meta-monitor — the Meta OS system monitor. A real GTK program, not a page.

Reads the machine it is running on: /proc for CPU and memory, statvfs for the
disk, /proc/uptime for uptime, and the local agent daemon on 18940 for the
agent count. Every number on screen is measured; when a source is missing the
row says so instead of showing a placeholder.
"""
import json
import os
import sys
import time
import urllib.request

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk  # noqa: E402

AGENTS_URL = "http://127.0.0.1:18940/agents"
REFRESH_SECONDS = 2

CSS = b"""
window { background: #070b16; }
label.key { color: #8291ac; font-family: monospace; font-size: 11px; }
label.val { color: #edf5ff; font-family: monospace; font-size: 20px; }
label.warn { color: #ff4f9a; font-family: monospace; font-size: 12px; }
label.title { color: #1877f2; font-family: monospace; font-size: 13px; font-weight: bold; }
"""


def read(path, default=""):
    try:
        with open(path, "r") as fh:
            return fh.read()
    except OSError:
        return default


def cpu_times():
    fields = read("/proc/stat").splitlines()[0].split()[1:]
    vals = [int(v) for v in fields]
    idle = vals[3] + (vals[4] if len(vals) > 4 else 0)
    return sum(vals), idle


def meminfo():
    out = {}
    for line in read("/proc/meminfo").splitlines():
        bits = line.split()
        if len(bits) >= 2:
            out[bits[0].rstrip(":")] = int(bits[1]) * 1024
    return out


def uptime_human():
    try:
        secs = float(read("/proc/uptime").split()[0])
    except (ValueError, IndexError):
        return "unavailable"
    h, rem = divmod(int(secs), 3600)
    m = rem // 60
    return f"{h}h {m:02d}m"


def disk(root="/"):
    try:
        st = os.statvfs(root)
    except OSError:
        return None
    total = st.f_frsize * st.f_blocks
    free = st.f_frsize * st.f_bavail
    return total, free


def agents():
    try:
        with urllib.request.urlopen(AGENTS_URL, timeout=2) as r:
            data = json.loads(r.read().decode())
    except Exception:
        return None
    if isinstance(data, dict):
        for k in ("agents", "data", "items"):
            if isinstance(data.get(k), list):
                data = data[k]
                break
    return data if isinstance(data, list) else None


class Monitor(Gtk.Window):
    def __init__(self):
        super().__init__(title="Meta Monitor")
        self.set_default_size(360, 420)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.prev = cpu_times()

        prov = Gtk.CssProvider()
        prov.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(
            self.get_screen(), prov, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        box.set_border_width(20)
        self.add(box)

        head = Gtk.Label(label="META OS", xalign=0)
        head.get_style_context().add_class("title")
        box.pack_start(head, False, False, 0)

        self.rows = {}
        for key, label in (
            ("cpu", "CPU"),
            ("mem", "MEMORY"),
            ("disk", "DISK FREE"),
            ("up", "UPTIME"),
            ("agents", "AGENTS"),
            ("host", "HOST"),
        ):
            wrap = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
            k = Gtk.Label(label=label, xalign=0)
            k.get_style_context().add_class("key")
            v = Gtk.Label(label="—", xalign=0)
            v.get_style_context().add_class("val")
            wrap.pack_start(k, False, False, 0)
            wrap.pack_start(v, False, False, 0)
            box.pack_start(wrap, False, False, 0)
            self.rows[key] = v

        self.foot = Gtk.Label(label="", xalign=0)
        self.foot.get_style_context().add_class("warn")
        box.pack_end(self.foot, False, False, 0)

        self.refresh()
        GLib.timeout_add_seconds(REFRESH_SECONDS, self.refresh)

    def set(self, key, text):
        self.rows[key].set_text(text)

    def refresh(self):
        total, idle = cpu_times()
        d_total = total - self.prev[0]
        d_idle = idle - self.prev[1]
        self.prev = (total, idle)
        if d_total > 0:
            pct = 100.0 * (1.0 - d_idle / d_total)
            self.set("cpu", f"{pct:5.1f}%")
        else:
            self.set("cpu", "sampling…")

        mem = meminfo()
        if mem.get("MemTotal"):
            used = mem["MemTotal"] - mem.get("MemAvailable", mem.get("MemFree", 0))
            gb = used / 1024**3
            self.set("mem", f"{gb:.1f} / {mem['MemTotal'] / 1024**3:.1f} GB")
        else:
            self.set("mem", "unavailable")

        d = disk("/")
        if d:
            total_b, free_b = d
            self.set(
                "disk",
                f"{free_b / 1024**3:.1f} GB free of {total_b / 1024**3:.1f}",
            )
        else:
            self.set("disk", "unavailable")

        self.set("up", uptime_human())
        self.set("host", os.uname().nodename)

        a = agents()
        if a is None:
            self.set("agents", "daemon down")
            self.foot.set_text("18940 not answering — agent rows are not live")
        else:
            live = sum(1 for x in a if not x.get("draft"))
            self.set("agents", f"{live} live / {len(a)} known")
            self.foot.set_text("")
        return True


def main():
    win = Monitor()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()
    return 0


if __name__ == "__main__":
    sys.exit(main())

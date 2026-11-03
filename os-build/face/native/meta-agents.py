#!/usr/bin/env python3
"""meta-agents — the Meta OS agent console. A real GTK program.

Two panes, both from the machine:
  left   the agents the local daemon on 18940 reports, live vs draft
  right  an order box that runs /usr/local/bin/meta-ask for real and prints
         exactly what it printed — refusals included

There is no simulated reply anywhere in this file. If the daemon is down the
list says so, and if meta-ask refuses, its refusal is the output.
"""
import json
import subprocess
import sys
import threading
import urllib.request

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk  # noqa: E402

AGENTS_URL = "http://127.0.0.1:18940/agents"
META_ASK = "/usr/local/bin/meta-ask"
CSS = b"""
window { background: #070b16; }
list { background: #0b1220; color: #edf5ff; font-family: monospace; }
row:selected { background: #1877f2; }
textview, textview text { background: #05080f; color: #edf5ff; font-family: monospace; font-size: 12px; }
label { color: #8291ac; }
entry { background: #0b1220; color: #edf5ff; }
"""


def fetch_agents():
    try:
        with urllib.request.urlopen(AGENTS_URL, timeout=2) as r:
            data = json.loads(r.read().decode())
    except Exception as exc:
        return None, str(exc)
    if isinstance(data, dict):
        for key in ("agents", "data", "items"):
            if isinstance(data.get(key), list):
                data = data[key]
                break
    if not isinstance(data, list):
        return None, "unexpected /agents shape"
    return data, None


class Console(Gtk.Window):
    def __init__(self):
        super().__init__(title="Meta Agents")
        self.set_default_size(860, 560)

        prov = Gtk.CssProvider()
        prov.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(
            self.get_screen(), prov, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        header = Gtk.HeaderBar(title="Meta Agents", show_close_button=True)
        self.set_titlebar(header)
        refresh = Gtk.Button(label="Refresh")
        refresh.connect("clicked", lambda *_: self.reload())
        header.pack_start(refresh)

        self.health = Gtk.Label(label="")
        header.pack_end(self.health)

        split = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        split.set_position(280)
        self.add(split)

        self.list = Gtk.ListBox()
        self.list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.list.connect("row-selected", self.on_pick)
        scroll = Gtk.ScrolledWindow()
        scroll.add(self.list)
        split.pack1(scroll, resize=False, shrink=False)

        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        right.set_border_width(10)

        form = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.order = Gtk.Entry()
        self.order.set_placeholder_text("order for the selected agent…")
        self.order.connect("activate", self.on_submit)
        go = Gtk.Button(label="Submit")
        go.connect("clicked", self.on_submit)
        form.pack_start(self.order, True, True, 0)
        form.pack_start(go, False, False, 0)
        right.pack_start(form, False, False, 0)

        self.out = Gtk.TextView()
        self.out.set_editable(False)
        self.out.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        out_scroll = Gtk.ScrolledWindow()
        out_scroll.add(self.out)
        right.pack_start(out_scroll, True, True, 0)

        split.pack2(right, resize=True, shrink=False)

        self.picked = None
        self.reload()

    def log(self, text):
        buf = self.out.get_buffer()
        buf.insert(buf.get_end_iter(), text.rstrip() + "\n")
        mark = buf.create_mark(None, buf.get_end_iter(), False)
        self.out.scroll_mark_onscreen(mark)

    def reload(self):
        for row in self.list.get_children():
            self.list.remove(row)
        agents, err = fetch_agents()
        if agents is None:
            self.health.set_text("daemon down")
            self.log(f"18940: {err}\nno agent list — start metaosd.service")
            return
        self.health.set_text(f"{len(agents)} agents")
        for a in agents:
            name = a.get("name") or a.get("id") or "unnamed"
            draft = bool(a.get("draft"))
            row = Gtk.ListBoxRow()
            label = Gtk.Label(
                label=f"{name}{'  (draft)' if draft else ''}", xalign=0
            )
            label.set_margin_top(5)
            label.set_margin_bottom(5)
            label.set_margin_start(8)
            row.add(label)
            row.agent = name
            row.draft = draft
            self.list.add(row)
        self.list.show_all()

    def on_pick(self, _list, row):
        if row is not None:
            self.picked = row.agent

    def on_submit(self, _widget):
        text = self.order.get_text().strip()
        agent = self.picked
        if not text:
            self.log("refused: empty order")
            return
        if not agent:
            self.log("refused: pick an agent on the left first")
            return
        self.order.set_text("")
        self.log(f"$ meta-ask {text!r} --agent {agent}")
        threading.Thread(
            target=self._run, args=(text, agent), daemon=True
        ).start()

    def _run(self, text, agent):
        if not (META_ASK and __import__("os").path.exists(META_ASK)):
            GLib.idle_add(self.log, f"missing {META_ASK} on this system")
            return
        try:
            proc = subprocess.run(
                [META_ASK, text, "--agent", agent],
                capture_output=True,
                text=True,
                timeout=20,
            )
            out = (proc.stdout or "") + (proc.stderr or "")
            GLib.idle_add(self.log, out.strip() or f"exit {proc.returncode}, no output")
        except subprocess.TimeoutExpired:
            GLib.idle_add(self.log, "meta-ask timed out after 20s")
        except OSError as exc:
            GLib.idle_add(self.log, f"could not run meta-ask: {exc}")


def main():
    win = Console()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""MetaOS Imperium app — native GTK shell, cooked-in, no hosting.

Loads the Imperium web UI from local files (file://) in a WebKitGTK
window and keeps the assess backend on 127.0.0.1:8080 alive as a child
process. Nothing leaves the machine: no remote servers, no open ports.
If node or the backend is missing, the UI still opens (live features
show the backend-unknown state, exactly as designed).
"""
import json
import os
import socket
import subprocess
import sys

APP_DIR = "/usr/share/metaos/imperium"
SERVER_DIR = "/usr/share/metaos/server"
INDEX = os.path.join(APP_DIR, "index.html")
PORT = int(os.environ.get("META_IMPERIUM_PORT", "8080"))


def backend_up():
    s = socket.socket()
    s.settimeout(0.5)
    try:
        s.connect(("127.0.0.1", PORT))
        s.close()
        return True
    except OSError:
        return False


def ensure_backend():
    if backend_up():
        return None
    node = "/usr/bin/node"
    main = os.path.join(SERVER_DIR, "server.mjs")
    if not (os.path.exists(node) and os.path.exists(main)):
        return None
    env = dict(os.environ, PORT=str(PORT))
    try:
        p = subprocess.Popen(
            [node, main], env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(40):
            import time
            time.sleep(0.25)
            if backend_up():
                return p
        return p
    except OSError:
        return None


def main():
    ensure_backend()
    try:
        import gi
        gi.require_version("Gtk", "3.0")
        gi.require_version("WebKit2", "4.1")
        from gi.repository import Gtk, WebKit2
    except (ImportError, ValueError):
        sys.stderr.write("metaos-imperium: GTK/WebKit2 unavailable\n")
        return 1
    win = Gtk.Window(title="Imperium")
    win.set_default_size(1280, 800)
    view = WebKit2.WebView()
    settings = view.get_settings()
    try:
        settings.set_enable_developer_extras(False)
    except Exception:
        pass
    view.load_uri("file://" + INDEX)
    win.add(view)
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()
    return 0


if __name__ == "__main__":
    sys.exit(main())

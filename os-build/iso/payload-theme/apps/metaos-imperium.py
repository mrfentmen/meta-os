#!/usr/bin/env python3
"""MetaOS Imperium app — native GTK shell, cooked in, no hosting.

Loads the Imperium web UI from local files (file://) in a WebKitGTK
window and keeps the assess backend on 127.0.0.1:8080 alive as a child
process. Nothing leaves the machine: no remote servers, no open ports.
If node or the backend is missing, the UI still opens (the backend
status reads unknown, as designed).
"""
import os
import sys

APP_DIR = "/usr/share/metaos/imperium"
SERVER_DIR = "/usr/share/metaos/server"
# The console page links ../styles.css and ../vendor/maplibre, so it has to sit
# one level under the site root to be styled at all. Installed on its own under
# /usr/share/metaos/imperium it drew as bare HTML -- black text on white, blue
# underlined links -- which is exactly the "it's a webpage" look this app is
# meant to kill. Prefer the site-root copy when it is there.
SITE_ROOT = os.environ.get("METAOS_SITE_ROOT", "/opt/face-site")
SITE_INDEX = os.path.join(SITE_ROOT, "imperium", "index.html")
INDEX = SITE_INDEX if os.path.exists(SITE_INDEX) else os.path.join(APP_DIR, "index.html")
PORT = int(os.environ.get("META_IMPERIUM_PORT", "8080"))


def backend_up():
    import socket
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
    import subprocess
    import time
    # The page is served by this backend, not read off disk. Two things only
    # work same-origin: GET /api/cameras (NYCTMC sends no CORS header, so the
    # proxy is the only way the live camera list can load) and the relative
    # ../js and ../vendor paths, which need the site root as the document
    # root. Loaded as file:// the proxy became file:///api/cameras, the live
    # list and the basemap both fell back, and the console looked like a plain
    # web page with pins — which is what shipped and what was wrong.
    env = dict(os.environ, PORT=str(PORT), METAOS_STATIC_ROOT=SITE_ROOT)
    try:
        p = subprocess.Popen(
            [node, main], env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(40):
            time.sleep(0.25)
            if backend_up():
                return p
        return p
    except OSError:
        return None


def doc_url():
    """http:// when the backend answers, file:// only as the fallback."""
    rel = os.path.relpath(INDEX, SITE_ROOT)
    http = "http://127.0.0.1:%d/%s" % (PORT, rel.replace(os.sep, "/"))
    return http if backend_up() else "file://" + INDEX


def main(argv):
    # Two dock tiles, one program: Trio (the three divisions) and Imperium (the
    # console they sit in). The window title is the only thing that has to
    # differ, and it is passed in by the launcher rather than guessed here.
    title = os.environ.get("META_IMPERIUM_TITLE", "Imperium Console")
    args = [a for a in argv[1:] if a != ""]
    for i, a in enumerate(args):
        if a == "--title" and i + 1 < len(args):
            title = args[i + 1]
    ensure_backend()
    try:
        import gi
        gi.require_version("Gtk", "3.0")
        gi.require_version("WebKit2", "4.1")
        from gi.repository import Gtk, Gdk
    except (ImportError, ValueError) as e:
        sys.stderr.write("metaos-imperium: GTK/WebKit unavailable (%s)\n" % e)
        return 1
    if not os.path.exists(INDEX):
        sys.stderr.write("metaos-imperium: missing %s\n" % INDEX)
        return 1
    win = Gtk.Window(title=title)
    win.set_default_size(1280, 800)
    from gi.repository import WebKit2
    view = WebKit2.WebView()
    view.load_uri(doc_url())
    win.add(view)
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

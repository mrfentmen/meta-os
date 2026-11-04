"""Meta OS launcher daemon. POST /launch {"app": name}
runs a real Linux app behind the fullscreen browser. Allow-list only —
no shell, no arguments. Runs on 127.0.0.1:18931, loopback only.

Base-image mapping (verified from casper/filesystem.manifest + APP_MATRIX.md):
- pcmanfm (absent, LXDE) -> thunar (present 4.18.8, Xfce file manager)
- lxterminal (absent, LXDE) -> xfce4-terminal (present 1.1.3)
- mousepad (present 0.6.1) -> kept
- orage (absent, deprecated; no standalone calendar in base) ->
  thunderbird (present as snap, ships calendar) for a native calendar
- galculator (absent) -> mate-calc (present 1.26.0)
- chromium (absent as deb; transitional shim) -> firefox (present as snap)
"""
import json
import shutil
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer

ALLOW = {
    "thunar": ["thunar"],
    "xfce4-terminal": ["xfce4-terminal"],
    "mousepad": ["mousepad"],
    "thunderbird": ["thunderbird"],
    "mate-calc": ["mate-calc"],
    "firefox": ["firefox", "--new-window", "about:blank"],
}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        if self.path == "/apps":
            # Computed, not hard-coded twice: an app is listed only when its
            # binary resolves on this machine's PATH right now. A failed
            # lookup drops the app from the list instead of lying about it.
            live = sorted(a for a, c in ALLOW.items() if shutil.which(c[0]))
            return self._send(200, {"ok": True, "apps": live})
        return self._send(404, {"ok": False, "error": "not found"})

    def do_POST(self):
        if self.path != "/launch":
            return self._send(404, {"ok": False, "error": "not found"})
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        try:
            app = json.loads(self.rfile.read(length) or b"{}").get("app")
        except Exception:
            return self._send(400, {"ok": False, "error": "bad json"})
        if app not in ALLOW:
            return self._send(403, {"ok": False,
                                     "error": "not allowed: " + str(app)})
        try:
            subprocess.Popen(ALLOW[app], stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            return self._send(500, {"ok": False, "error":
                                     "not installed on this image: " +
                                     " ".join(ALLOW[app])})
        return self._send(200, {"ok": True, "app": app})


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", 18931), H).serve_forever()

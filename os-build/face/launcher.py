"""Meta OS launcher daemon. POST /launch {"app": name}
runs a real Linux app behind the fullscreen browser. Allow-list only —
no shell, no arguments. Runs on 127.0.0.1:18931, loopback only.

Xubuntu 24.04.5 base (verified from casper/filesystem.manifest):
- pcmanfm (absent, LXDE) -> thunar (present 4.18.8, Xfce file manager)
- lxterminal (absent, LXDE) -> xfce4-terminal (present 1.1.3)
- mousepad (present 0.6.1) -> kept
- orage (absent, deprecated; no standalone calendar in base) ->
  thunderbird (present as snap, ships calendar) for a native calendar
- galculator (absent) -> mate-calc (present 1.26.0)
- chromium (absent as deb; Ubuntu shim) -> firefox (present as snap)
"""
import json
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
            return self._send(200, {"ok": True, "apps": sorted(ALLOW)})
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
            return self._send(403, {"ok": False, "error": "not allowed"})
        try:
            subprocess.Popen(ALLOW[app], stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            return self._send(500, {"ok": False, "error": "not installed"})
        return self._send(200, {"ok": True, "app": app})


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", 18931), H).serve_forever()

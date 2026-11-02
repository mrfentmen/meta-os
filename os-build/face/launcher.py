"""Meta OS launcher daemon (spike A companion). POST /launch {"app": name}
runs a real Linux app behind the fullscreen browser. Allow-list only —
no shell, no arguments. Runs on 127.0.0.1:18931, loopback only."""
import json
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer

ALLOW = {
    "pcmanfm": ["pcmanfm"],
    "lxterminal": ["lxterminal"],
    "mousepad": ["mousepad"],
    "orage": ["orage"],
    "galculator": ["galculator"],
    "chromium": ["chromium", "--new-window", "about:blank"],
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

"""Board: tiny multi-room message board. Rooms list, post, receive.
GET /rooms, GET /messages?room=X, POST /post {"room","author","text"}.
JSON file persistence across restart. Stdlib only. 127.0.0.1:18935."""
import json
import os
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

PORT = 18935
def _data_file():
    base = os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")
    d = os.path.join(base, "metaos")
    try:
        os.makedirs(d, exist_ok=True)
        return os.path.join(d, "board.json")
    except OSError:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "board.json")

FILE = _data_file()
DEFAULT_ROOMS = ["general", "random", "announce"]
MAX_TEXT = 500
MAX_AUTHOR = 32


def load():
    try:
        with open(FILE) as fh:
            d = json.load(fh)
            if isinstance(d, dict):
                return {str(k): list(v) for k, v in d.items()}
    except (OSError, ValueError):
        pass
    return {r: [] for r in DEFAULT_ROOMS}


def save(store):
    tmp = FILE + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(store, fh)
    os.replace(tmp, FILE)


STORE = load()
for r in DEFAULT_ROOMS:
    STORE.setdefault(r, [])


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
        self.end_headers()

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/rooms":
            return self._send(200, {"ok": True, "rooms": sorted(STORE)})
        if u.path == "/messages":
            room = parse_qs(u.query).get("room", [""])[0]
            if room not in STORE:
                return self._send(404, {"ok": False, "error": "no room"})
            return self._send(200, {"ok": True, "room": room,
                                   "messages": STORE[room][-100:]})
        return self._send(404, {"ok": False, "error": "not found"})

    def do_POST(self):
        if self.path != "/post":
            return self._send(404, {"ok": False, "error": "not found"})
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            n = 0
        try:
            d = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return self._send(400, {"ok": False, "error": "bad json"})
        room = str(d.get("room") or "").strip()[:32]
        author = str(d.get("author") or "anon").strip()[:MAX_AUTHOR] or "anon"
        text = str(d.get("text") or "").strip()
        if not room or not text:
            return self._send(400, {"ok": False, "error": "room+text needed"})
        if room not in STORE:
            STORE[room] = []
        msgs = STORE[room]
        mid = (msgs[-1]["id"] + 1) if msgs else 1
        msg = {"id": mid, "author": author, "text": text[:MAX_TEXT],
               "ts": int(time.time())}
        msgs.append(msg)
        del msgs[:-200]
        try:
            save(STORE)
        except OSError:
            return self._send(500, {"ok": False, "error": "persist failed"})
        return self._send(200, {"ok": True, "room": room, "message": msg})


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", PORT), H).serve_forever()

"""Meta OS notes daemon (spike A companion). Notes + calendar + settings.

Notes persist as files (not browser localStorage):
  $XDG_DATA_HOME/metaos/notes/<id>.json  (canonical store)
  ~/Notes/<id>.md                         (readable mirror, browsable in Files)

Calendar events persist as:
  $XDG_DATA_HOME/metaos/calendar.json     (canonical store)
  ~/Notes/calendar.ics                     (valid VCALENDAR mirror)

Settings persist as:
  ~/.config/metaos/settings.json

Stdlib only. Runs on 127.0.0.1:18937, loopback only.

GET  /notes          -> {"ok", "notes": [{id,text,updated}], "dir": NOTEDIR}
POST /notes {"id"?, "text"} -> upsert, returns {"ok", "note": {...}}
POST /notes/delete {"id"}   -> delete note + mirror
GET  /events         -> {"ok", "events": {date: [texts]}, "ics": ICSPATH}
POST /events {"date", "text"} -> append event, rewrites calendar.ics
POST /events/delete {"date", "index"} -> remove event, rewrites calendar.ics
GET  /export         -> {"ok", "ics": <vcalendar text>, "path": ICSPATH}
POST /import {"ics": <vcalendar text>} -> parse VEVENTs, returns {"ok", "added": N}
GET  /settings       -> {"ok", "settings": {...}, "path": SETTINGSFILE}
POST /settings {k: v, ...}  -> merge into settings.json
Selftest: python3 notesd.py --selftest
"""
import json
import os
import re
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

PORT = 18937


def home_dir():
    return os.path.expanduser("~")


def data_dir():
    base = (os.environ.get("XDG_DATA_HOME")
            or os.path.join(home_dir(), ".local", "share"))
    d = os.path.join(base, "metaos")
    os.makedirs(d, exist_ok=True)
    return d


def notes_dir():
    d = os.path.join(data_dir(), "notes")
    os.makedirs(d, exist_ok=True)
    return d


def mirror_dir():
    d = os.path.join(home_dir(), "Notes")
    os.makedirs(d, exist_ok=True)
    return d


def calendar_file():
    return os.path.join(data_dir(), "calendar.json")


def ics_path():
    return os.path.join(mirror_dir(), "calendar.ics")


def settings_file():
    base = (os.environ.get("XDG_CONFIG_HOME")
            or os.path.join(home_dir(), ".config"))
    d = os.path.join(base, "metaos")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "settings.json")


SAFE_ID = re.compile(r"[^A-Za-z0-9_-]")


def clean_id(v):
    if not isinstance(v, str) or not v or len(v) > 64:
        raise ValueError("bad id")
    if SAFE_ID.search(v):
        raise ValueError("bad id")
    if v in (".", ".."):
        raise ValueError("bad id")
    return v


def new_id():
    return "%d-%04d" % (int(time.time() * 1000), os.getpid() % 10000)


# ---------------- notes ----------------

def note_path(nid):
    return os.path.join(notes_dir(), clean_id(nid) + ".json")


def mirror_path(nid):
    return os.path.join(mirror_dir(), clean_id(nid) + ".md")


def read_note(nid):
    with open(note_path(nid), encoding="utf-8") as fh:
        d = json.load(fh)
    if not isinstance(d, dict) or not isinstance(d.get("text"), str):
        raise ValueError("bad note file")
    return {"id": clean_id(nid), "text": d["text"],
            "updated": int(d.get("updated") or 0)}


def list_notes():
    out = []
    try:
        names = os.listdir(notes_dir())
    except OSError:
        return out
    for name in names:
        if not name.endswith(".json"):
            continue
        nid = name[:-5]
        try:
            out.append(read_note(nid))
        except (OSError, ValueError):
            continue
    out.sort(key=lambda n: n["updated"], reverse=True)
    return out


def write_mirror(nid, text):
    first = (text.split("\n")[0] if text else "").strip()[:80]
    title = first or "Untitled note"
    body = "# %s\n\n%s\n" % (title, text)
    tmp = mirror_path(nid) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        fh.write(body)
    os.replace(tmp, mirror_path(nid))


def save_note(nid, text):
    if not isinstance(text, str):
        raise ValueError("text must be text")
    if len(text.encode("utf-8")) > 512 * 1024:
        raise ValueError("note too large")
    nid = clean_id(nid)
    note = {"id": nid, "text": text, "updated": int(time.time())}
    tmp = note_path(nid) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(note, fh)
    os.replace(tmp, note_path(nid))
    write_mirror(nid, text)
    return note


def delete_note(nid):
    nid = clean_id(nid)
    gone = False
    for p in (note_path(nid), mirror_path(nid)):
        try:
            os.unlink(p)
            gone = True
        except OSError:
            pass
    if not gone:
        raise ValueError("no such note")
    # remove orphaned .tmp files if any
    for p in (note_path(nid) + ".tmp", mirror_path(nid) + ".tmp"):
        try:
            os.unlink(p)
        except OSError:
            pass


# ---------------- calendar ----------------

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def clean_date(v):
    if not isinstance(v, str) or not DATE_RE.match(v):
        raise ValueError("date must be YYYY-MM-DD")
    y, m, d = int(v[0:4]), int(v[5:7]), int(v[8:10])
    if not (1 <= m <= 12 and 1 <= d <= 31):
        raise ValueError("bad date")
    return v


def load_events():
    try:
        with open(calendar_file(), encoding="utf-8") as fh:
            d = json.load(fh)
    except (OSError, ValueError):
        return {}
    if not isinstance(d, dict):
        return {}
    out = {}
    for k, v in d.items():
        try:
            dk = clean_date(str(k))
        except ValueError:
            continue
        if isinstance(v, list):
            out[dk] = [str(x) for x in v if isinstance(x, str)][:200]
    return out


def store_events(events):
    tmp = calendar_file() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(events, fh, sort_keys=True)
    os.replace(tmp, calendar_file())
    write_ics(events)


def esc_ics(s):
    return (s.replace("\\", "\\\\").replace(";", "\\;")
             .replace(",", "\\,").replace("\n", "\\n"))


def unesc_ics(s):
    return (s.replace("\\n", "\n").replace("\\N", "\n")
             .replace("\\;", ";").replace("\\,", ",")
             .replace("\\\\", "\\"))


def ics_date_next(date):
    import datetime
    y, m, d = int(date[0:4]), int(date[5:7]), int(date[8:10])
    nxt = datetime.date(y, m, d) + datetime.timedelta(days=1)
    return nxt.strftime("%Y%m%d")


def build_ics(events):
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0",
             "PRODID:-//MetaOS//Calendar//EN"]
    for date in sorted(events):
        compact = date.replace("-", "")
        for i, text in enumerate(events[date]):
            uid = "%s-%d@metaos" % (compact, i)
            lines.append("BEGIN:VEVENT")
            lines.append("UID:" + uid)
            lines.append("DTSTAMP:" + stamp)
            lines.append("DTSTART;VALUE=DATE:" + compact)
            lines.append("DTEND;VALUE=DATE:" + ics_date_next(date))
            lines.append("SUMMARY:" + esc_ics(text))
            lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def write_ics(events):
    path = ics_path()
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        fh.write(build_ics(events))
    os.replace(tmp, path)
    return path


def parse_ics(text):
    """Return {date: [texts]} parsed from a VCALENDAR string."""
    if not isinstance(text, str):
        raise ValueError("ics must be text")
    if "BEGIN:VCALENDAR" not in text or "END:VCALENDAR" not in text:
        raise ValueError("not a VCALENDAR")
    # unfold continuation lines (start with space/tab)
    raw = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    lines = []
    for ln in raw:
        if ln[:1] in (" ", "\t") and lines:
            lines[-1] += ln[1:]
        else:
            lines.append(ln)
    events = {}
    in_ev = False
    cur = {}
    for ln in lines:
        if ln == "BEGIN:VEVENT":
            in_ev = True
            cur = {}
        elif ln == "END:VEVENT":
            if in_ev and "DTSTART" in cur and "SUMMARY" in cur:
                try:
                    dk = cur["DTSTART"]
                    if len(dk) == 8 and dk.isdigit():
                        dk = "%s-%s-%s" % (dk[0:4], dk[4:6], dk[6:8])
                    dk = clean_date(dk)
                    events.setdefault(dk, []).append(cur["SUMMARY"])
                except ValueError:
                    pass
            in_ev = False
            cur = {}
        elif in_ev and ":" in ln:
            name, _, val = ln.partition(":")
            name = name.split(";")[0]
            if name == "DTSTART":
                cur["DTSTART"] = val.strip()
            elif name == "SUMMARY":
                cur["SUMMARY"] = unesc_ics(val.strip())
    return events


# ---------------- settings ----------------

def load_settings():
    try:
        with open(settings_file(), encoding="utf-8") as fh:
            d = json.load(fh)
            if isinstance(d, dict):
                return {str(k): v for k, v in d.items()}
    except (OSError, ValueError):
        pass
    return {}


def store_settings(patch):
    if not isinstance(patch, dict):
        raise ValueError("settings must be an object")
    cur = load_settings()
    for k, v in patch.items():
        if not isinstance(k, str) or len(k) > 64:
            raise ValueError("bad setting key")
        if not isinstance(v, (str, int, float, bool)) and v is not None:
            raise ValueError("bad setting value for %s" % k)
        cur[k] = v
    tmp = settings_file() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(cur, fh, indent=2, sort_keys=True)
    os.replace(tmp, settings_file())
    return cur


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

    def _body(self):
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            n = 0
        if n > 1024 * 1024:
            return None
        try:
            return json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return None

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/notes":
            try:
                notes = list_notes()
            except OSError as e:
                return self._send(500, {"ok": False, "error": str(e)})
            return self._send(200, {"ok": True, "notes": notes,
                                   "dir": notes_dir()})
        if u.path == "/events":
            try:
                events = load_events()
            except OSError as e:
                return self._send(500, {"ok": False, "error": str(e)})
            return self._send(200, {"ok": True, "events": events,
                                   "ics": ics_path()})
        if u.path == "/export":
            try:
                events = load_events()
                text = build_ics(events)
            except OSError as e:
                return self._send(500, {"ok": False, "error": str(e)})
            return self._send(200, {"ok": True, "ics": text,
                                   "path": ics_path()})
        if u.path == "/settings":
            try:
                cur = load_settings()
            except OSError as e:
                return self._send(500, {"ok": False, "error": str(e)})
            return self._send(200, {"ok": True, "settings": cur,
                                   "path": settings_file()})
        return self._send(404, {"ok": False, "error": "not found"})

    def do_POST(self):
        if self.path not in ("/notes", "/notes/delete", "/events",
                             "/events/delete", "/import", "/settings"):
            return self._send(404, {"ok": False, "error": "not found"})
        d = self._body()
        if d is None:
            return self._send(400, {"ok": False, "error": "bad json"})
        try:
            if self.path == "/notes":
                nid = d.get("id") or new_id()
                note = save_note(nid, d.get("text"))
                return self._send(200, {"ok": True, "note": note})
            if self.path == "/notes/delete":
                delete_note(d.get("id"))
                return self._send(200, {"ok": True})
            if self.path == "/events":
                date = clean_date(d.get("date"))
                text = d.get("text")
                if not isinstance(text, str) or not text.strip():
                    raise ValueError("text needed")
                events = load_events()
                events.setdefault(date, []).append(text.strip()[:500])
                store_events(events)
                return self._send(200, {"ok": True, "date": date})
            if self.path == "/events/delete":
                date = clean_date(d.get("date"))
                idx = d.get("index")
                if not isinstance(idx, int):
                    raise ValueError("index needed")
                events = load_events()
                arr = events.get(date) or []
                if not (0 <= idx < len(arr)):
                    raise ValueError("no such event")
                arr.pop(idx)
                if arr:
                    events[date] = arr
                else:
                    events.pop(date, None)
                store_events(events)
                return self._send(200, {"ok": True})
            if self.path == "/import":
                parsed = parse_ics(d.get("ics"))
                events = load_events()
                added = 0
                for date, texts in parsed.items():
                    for t in texts:
                        events.setdefault(date, []).append(t[:500])
                        added += 1
                store_events(events)
                return self._send(200, {"ok": True, "added": added})
            cur = store_settings(d)
            return self._send(200, {"ok": True, "settings": cur})
        except ValueError as e:
            return self._send(400, {"ok": False, "error": str(e)})
        except OSError as e:
            return self._send(500, {"ok": False, "error": str(e)})


def selftest():
    import socket
    import tempfile
    import threading
    import urllib.request
    tmp = tempfile.mkdtemp(prefix="face-notesd-test-")
    os.environ["XDG_DATA_HOME"] = os.path.join(tmp, "data")
    os.environ["XDG_CONFIG_HOME"] = os.path.join(tmp, "config")
    os.environ["HOME"] = os.path.join(tmp, "home")
    os.makedirs(os.environ["HOME"], exist_ok=True)
    port = 18937
    try:
        s = socket.create_connection(("127.0.0.1", port), timeout=1)
        s.close()
        print("selftest: port 18937 busy, abort")
        raise SystemExit(1)
    except OSError:
        pass
    srv = HTTPServer(("127.0.0.1", port), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    def call(method, route, data=None):
        url = "http://127.0.0.1:%d%s" % (port, route)
        body = json.dumps(data or {}).encode() if data is not None else None
        req = urllib.request.Request(url, data=body, method=method,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read().decode())

    def check(cond, label):
        print(("ok" if cond else "FAIL") + " selftest: " + label)
        if not cond:
            raise SystemExit(1)

    s, d = call("POST", "/notes", {"text": "hello\nworld"})
    check(s == 200 and d["ok"] and d["note"]["id"], "create note")
    nid = d["note"]["id"]
    s, d = call("GET", "/notes")
    check(s == 200 and any(n["id"] == nid for n in d["notes"]), "list has note")
    md = os.path.join(tmp, "home", "Notes", nid + ".md")
    check(os.path.isfile(md) and "hello" in open(md).read(), "md mirror")
    srv.shutdown()
    srv.server_close()
    # restart: new server, same HOME -> note must survive
    srv = HTTPServer(("127.0.0.1", port), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    s, d = call("GET", "/notes")
    check(s == 200 and any(n["id"] == nid for n in d["notes"]),
          "note survives restart")
    s, d = call("POST", "/events", {"date": "2026-11-10", "text": "demo; day, one"})
    check(s == 200 and d["ok"], "add event")
    s, d = call("GET", "/export")
    ics = d["ics"]
    check(s == 200 and "BEGIN:VCALENDAR" in ics and "BEGIN:VEVENT" in ics
          and "DTSTART" in ics and "demo\\; day\\, one" in ics, "ics valid+escaped")
    check(ics.count("BEGIN:VEVENT") == 1, "ics event count matches")
    icsf = os.path.join(tmp, "home", "Notes", "calendar.ics")
    check(os.path.isfile(icsf), "calendar.ics on disk")
    s, d = call("POST", "/import", {"ics": ics})
    check(s == 200 and d["added"] == 1, "import round-trips")
    s, d = call("POST", "/settings", {"metaos-theme": "light"})
    check(s == 200 and d["settings"]["metaos-theme"] == "light", "save settings")
    s, d = call("GET", "/settings")
    check(s == 200 and d["settings"]["metaos-theme"] == "light",
          "settings survive read")
    srv.shutdown()
    print("PASS")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        HTTPServer(("127.0.0.1", PORT), H).serve_forever()

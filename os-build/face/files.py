"""Meta OS files service (spike A companion). List real dirs, read/save
text files, move to the Freedesktop trash. Stdlib only.

Runs on 127.0.0.1:18936, loopback only.

GET  /list?path=DIR  -> {"ok", "path", "parent", "entries":
                          [{name,path,is_dir,size,mtime}]} (no path = face dir)
GET  /read?path=FILE -> {"ok", "path", "content", "size", "mtime"}
POST /save {"path","content"} -> write text file (atomic replace)
POST /mkdir {"path"}          -> create dir (parents ok)
POST /trash {"path"}          -> move to ~/.local/share/Trash
GET  /trash                   -> {"ok", "entries":
                                  [{name,orig,deleted,size,is_dir}]}
POST /restore {"name"} -> move trash entry back to its original path
POST /delete {"name"}  -> delete a trash entry permanently
POST /empty            -> empty the trash ({"ok", "removed": N})
Selftest: python3 files.py --selftest
"""
import json
import os
import shutil
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

PORT = 18936
BASE = os.path.dirname(os.path.abspath(__file__))
MAX_READ = 512 * 1024
MAX_SAVE = 1024 * 1024


def trash_dirs():
    data_home = (os.environ.get("XDG_DATA_HOME")
                 or os.path.join(os.path.expanduser("~"), ".local", "share"))
    top = os.path.join(data_home, "Trash")
    return top, os.path.join(top, "files"), os.path.join(top, "info")


def ensure_trash():
    top, files, info = trash_dirs()
    os.makedirs(files, exist_ok=True)
    os.makedirs(info, exist_ok=True)
    return top, files, info


def unique_path(path):
    if not os.path.lexists(path):
        return path
    n = 1
    while True:
        cand = "%s.%d" % (path, n)
        if not os.path.lexists(cand):
            return cand
        n += 1


def abs_path(p):
    if not isinstance(p, str) or not p:
        raise ValueError("path needed")
    if "\x00" in p:
        raise ValueError("bad path")
    if not os.path.isabs(p):
        raise ValueError("absolute path needed")
    return os.path.abspath(p)


def clean_name(name):
    if not isinstance(name, str) or not name or "/" in name:
        raise ValueError("bad name")
    if name in (".", "..") or "\x00" in name:
        raise ValueError("bad name")
    return name


def list_dir(path):
    out = []
    for name in os.listdir(path):
        fp = os.path.join(path, name)
        try:
            st = os.lstat(fp)
        except OSError:
            continue
        out.append({"name": name, "path": fp,
                    "is_dir": os.path.isdir(fp),
                    "size": st.st_size, "mtime": int(st.st_mtime)})
    out.sort(key=lambda e: (not e["is_dir"], e["name"].lower()))
    return out


def read_text(path):
    if os.path.isdir(path):
        raise ValueError("is a directory")
    size = os.path.getsize(path)
    if size > MAX_READ:
        raise ValueError("file too large (%d bytes)" % size)
    with open(path, "rb") as fh:
        raw = fh.read()
    if b"\x00" in raw:
        raise ValueError("binary file")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        raise ValueError("binary file (not utf-8)")


def save_text(path, content):
    if not isinstance(content, str):
        raise ValueError("content must be text")
    raw = content.encode("utf-8")
    if len(raw) > MAX_SAVE:
        raise ValueError("content too large")
    if os.path.isdir(path):
        raise ValueError("is a directory")
    parent = os.path.dirname(path)
    if not os.path.isdir(parent):
        raise ValueError("parent dir missing: %s" % parent)
    tmp = "%s.tmp.%d" % (path, os.getpid())
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        fh.write(content)
    os.replace(tmp, path)
    return len(raw)


def trash_move(path):
    top, files, info = ensure_trash()
    if not os.path.lexists(path):
        raise ValueError("no such file")
    rp = os.path.abspath(path)
    if rp == top or rp.startswith(top + os.sep):
        raise ValueError("already in trash")
    name = os.path.basename(rp.rstrip(os.sep)) or "root"
    dest = unique_path(os.path.join(files, name))
    shutil.move(rp, dest)
    tname = os.path.basename(dest)
    with open(os.path.join(info, tname + ".trashinfo"),
              "w", encoding="utf-8") as fh:
        fh.write("[Trash Info]\nPath=%s\nDeletionDate=%s\n"
                 % (rp, time.strftime("%Y-%m-%dT%H:%M:%S")))
    return tname


def read_trashinfo(tip):
    orig, deleted = "", ""
    try:
        with open(tip, encoding="utf-8") as fh:
            for line in fh.read().splitlines():
                if line.startswith("Path="):
                    orig = line[5:]
                elif line.startswith("DeletionDate="):
                    deleted = line[13:]
    except OSError:
        pass
    return orig, deleted


def trash_list():
    _, files, info = ensure_trash()
    try:
        names = os.listdir(files)
    except OSError:
        return []
    out = []
    for name in sorted(names, key=str.lower):
        fp = os.path.join(files, name)
        try:
            st = os.lstat(fp)
        except OSError:
            continue
        orig, deleted = read_trashinfo(os.path.join(info, name + ".trashinfo"))
        out.append({"name": name, "orig": orig, "deleted": deleted,
                    "is_dir": os.path.isdir(fp),
                    "size": st.st_size, "mtime": int(st.st_mtime)})
    return out


def trash_restore(name):
    _, files, info = ensure_trash()
    name = clean_name(name)
    src = os.path.join(files, name)
    if not os.path.lexists(src):
        raise ValueError("not in trash")
    orig, _ = read_trashinfo(os.path.join(info, name + ".trashinfo"))
    if not orig:
        raise ValueError("original path unknown")
    parent = os.path.dirname(orig)
    if parent:
        os.makedirs(parent, exist_ok=True)
    dest = unique_path(orig)
    shutil.move(src, dest)
    try:
        os.unlink(os.path.join(info, name + ".trashinfo"))
    except OSError:
        pass
    return dest


def trash_delete(name):
    _, files, info = ensure_trash()
    name = clean_name(name)
    src = os.path.join(files, name)
    if not os.path.lexists(src):
        raise ValueError("not in trash")
    if os.path.isdir(src) and not os.path.islink(src):
        shutil.rmtree(src)
    else:
        os.unlink(src)
    try:
        os.unlink(os.path.join(info, name + ".trashinfo"))
    except OSError:
        pass


def trash_empty():
    _, files, info = ensure_trash()
    n = 0
    for d, only_info in ((files, False), (info, True)):
        try:
            names = os.listdir(d)
        except OSError:
            continue
        for name in names:
            if only_info and not name.endswith(".trashinfo"):
                continue
            fp = os.path.join(d, name)
            try:
                if (not only_info and os.path.isdir(fp)
                        and not os.path.islink(fp)):
                    shutil.rmtree(fp)
                else:
                    os.unlink(fp)
                n += 1
            except OSError:
                pass
    return n


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
        try:
            return json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return None

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path == "/list":
            raw = q.get("path", [""])[0]
            try:
                path = abs_path(raw) if raw else BASE
            except ValueError as e:
                return self._send(400, {"ok": False, "error": str(e)})
            if not os.path.isdir(path):
                return self._send(404, {"ok": False, "error": "no such dir"})
            try:
                entries = list_dir(path)
            except OSError as e:
                return self._send(500, {"ok": False, "error": str(e)})
            return self._send(200, {"ok": True, "path": path,
                                   "parent": os.path.dirname(path),
                                   "entries": entries})
        if u.path == "/read":
            try:
                path = abs_path(q.get("path", [""])[0])
            except ValueError as e:
                return self._send(400, {"ok": False, "error": str(e)})
            if not os.path.lexists(path):
                return self._send(404, {"ok": False, "error": "no such file"})
            try:
                content = read_text(path)
                st = os.stat(path)
            except ValueError as e:
                return self._send(400, {"ok": False, "error": str(e)})
            except OSError as e:
                return self._send(500, {"ok": False, "error": str(e)})
            return self._send(200, {"ok": True, "path": path,
                                   "content": content,
                                   "size": len(content.encode("utf-8")),
                                   "mtime": int(st.st_mtime)})
        if u.path == "/trash":
            try:
                entries = trash_list()
            except OSError as e:
                return self._send(500, {"ok": False, "error": str(e)})
            return self._send(200, {"ok": True, "entries": entries})
        return self._send(404, {"ok": False, "error": "not found"})

    def do_POST(self):
        if self.path not in ("/save", "/mkdir", "/trash", "/restore",
                             "/delete", "/empty"):
            return self._send(404, {"ok": False, "error": "not found"})
        d = self._body()
        if d is None:
            return self._send(400, {"ok": False, "error": "bad json"})
        try:
            if self.path == "/save":
                path = abs_path(d.get("path"))
                nbytes = save_text(path, d.get("content"))
                return self._send(200, {"ok": True, "path": path,
                                       "bytes": nbytes})
            if self.path == "/mkdir":
                path = abs_path(d.get("path"))
                os.makedirs(path, exist_ok=True)
                if not os.path.isdir(path):
                    raise OSError("mkdir failed")
                return self._send(200, {"ok": True, "path": path})
            if self.path == "/trash":
                path = abs_path(d.get("path"))
                name = trash_move(path)
                return self._send(200, {"ok": True, "name": name})
            if self.path == "/restore":
                dest = trash_restore(d.get("name"))
                return self._send(200, {"ok": True, "path": dest})
            if self.path == "/delete":
                trash_delete(clean_name(d.get("name")))
                return self._send(200, {"ok": True})
            n = trash_empty()
            return self._send(200, {"ok": True, "removed": n})
        except ValueError as e:
            return self._send(400, {"ok": False, "error": str(e)})
        except OSError as e:
            return self._send(500, {"ok": False, "error": str(e)})


def selftest(host="127.0.0.1", port=PORT):
    import socket
    import tempfile
    import threading
    import urllib.request
    srv = HTTPServer((host, port), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    def call(method, route, data=None):
        url = "http://%s:%d%s" % (host, port, route)
        body = json.dumps(data or {}).encode() if data is not None else None
        req = urllib.request.Request(url, data=body, method=method,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read().decode())

    def check(cond, label):
        print(("ok" if cond else "FAIL") + " selftest: " + label)
        if not cond:
            raise SystemExit(1)

    tmp = tempfile.mkdtemp(prefix="face-files-test-")
    demo = os.path.join(tmp, "hello.txt")
    with open(demo, "w") as fh:
        fh.write("one\n")
    s, d = call("GET", "/list?path=" + tmp)
    check(s == 200 and d["ok"] and any(e["name"] == "hello.txt"
                                       for e in d["entries"]), "list tmp dir")
    s, d = call("GET", "/read?path=" + demo)
    check(s == 200 and d["content"] == "one\n", "read text file")
    s, d = call("POST", "/save", {"path": demo, "content": "two\n"})
    check(s == 200 and d["ok"], "save text file")
    with open(demo) as fh:
        check(fh.read() == "two\n", "save landed on disk")
    s, d = call("POST", "/trash", {"path": demo})
    check(s == 200 and d["ok"] and not os.path.lexists(demo), "trash moves")
    tname = d["name"]
    s, d = call("GET", "/trash")
    check(s == 200 and any(e["name"] == tname for e in d["entries"]),
          "trash lists entry")
    s, d = call("POST", "/restore", {"name": tname})
    check(s == 200 and open(demo).read() == "two\n", "restore returns file")
    s, d = call("POST", "/trash", {"path": demo})
    check(s == 200 and d["ok"], "trash again")
    s, d = call("POST", "/delete", {"name": d["name"]})
    check(s == 200 and d["ok"] and not os.path.lexists(demo),
          "delete purges trash entry")
    try:
        call("GET", "/read?path=" + demo)
        check(False, "read of trashed file should 404")
    except Exception:
        print("ok selftest: read of missing file 404s")
    shutil.rmtree(tmp, ignore_errors=True)
    try:
        s = socket.create_connection((host, port), timeout=5)
        s.close()
    except OSError:
        pass
    srv.shutdown()
    print("PASS")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        HTTPServer(("127.0.0.1", PORT), H).serve_forever()

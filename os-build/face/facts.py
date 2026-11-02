"""Meta OS facts service (spike A companion). GET /facts returns live
numbers from THIS machine: cpu load, memory, storage, network.
Stdlib only. Runs on 127.0.0.1:18932, loopback only."""
import json
import os
import shutil
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer


def facts():
    try:
        with open("/proc/loadavg") as fh:
            load = fh.read().split()[0]
    except OSError:
        load = "?"
    try:
        mem = {}
        with open("/proc/meminfo") as fh:
            for line in fh:
                k, _, v = line.partition(":")
                mem[k.strip()] = v.strip().split()[0]
        total = int(mem.get("MemTotal", 0)) // 1024
        avail = int(mem.get("MemAvailable", 0)) // 1024
        mem_s = "%dM / %dM" % (total - avail, total)
    except (OSError, ValueError):
        mem_s = "?"
    try:
        u = shutil.disk_usage("/")
        disk_s = "%dG / %dG" % (u.used // 2**30, u.total // 2**30)
    except OSError:
        disk_s = "?"
    try:
        out = subprocess.run(["ip", "-4", "-o", "addr", "show", "scope",
                              "global"], capture_output=True, text=True,
                             timeout=5).stdout
        net_s = out.split()[3] if len(out.split()) > 3 else "?"
    except Exception:
        net_s = "?"
    return {"cpu": "load %s" % load, "mem": mem_s, "disk": disk_s,
            "net": net_s}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path != "/facts":
            self.send_response(404)
            self.end_headers()
            return
        body = json.dumps(facts()).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", 18932), H).serve_forever()

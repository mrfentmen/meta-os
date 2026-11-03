"""Meta OS facts service (spike A companion). GET /facts returns live
numbers from THIS machine: cpu load, memory, storage, network, distro,
kernel, uptime, package count, agent count.
Stdlib only. Runs on 127.0.0.1:18932, loopback only."""
import json
import os
import shutil
import subprocess
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.request import urlopen

BOOT_T = time.time()


def distro():
    try:
        info = {}
        with open("/etc/os-release", encoding="utf-8") as fh:
            for line in fh:
                if "=" in line:
                    k, _, v = line.partition("=")
                    info[k.strip()] = v.strip().strip('"')
        if info.get("PRETTY_NAME"):
            return info["PRETTY_NAME"]
        name = info.get("NAME", "?")
        ver = info.get("VERSION", "")
        return (name + " " + ver).strip()
    except OSError:
        return "?"


def kernel():
    try:
        return os.uname().release
    except (AttributeError, OSError):
        return "?"


def uptime():
    try:
        secs = int(float(open("/proc/uptime").read().split()[0]))
    except (OSError, ValueError, IndexError):
        secs = int(time.time() - BOOT_T)
    d, secs = divmod(secs, 86400)
    h, secs = divmod(secs, 3600)
    m, _ = divmod(secs, 60)
    if d:
        return "%dd %dh %dm" % (d, h, m)
    if h:
        return "%dh %dm" % (h, m)
    return "%dm" % m


def mem_info():
    try:
        mem = {}
        with open("/proc/meminfo") as fh:
            for line in fh:
                k, _, v = line.partition(":")
                mem[k.strip()] = v.strip().split()[0]
        total = int(mem.get("MemTotal", 0)) // 1024
        avail = int(mem.get("MemAvailable", 0)) // 1024
        return "%dM / %dM" % (total - avail, total), total - avail, total
    except (OSError, ValueError, IndexError):
        return "?", None, None


def disk_info():
    try:
        u = shutil.disk_usage("/")
        disk_s = "%dG / %dG" % (u.used // 2**30, u.total // 2**30)
        free_s = "%dG free of %dG" % (u.free // 2**30, u.total // 2**30)
        return disk_s, free_s
    except OSError:
        return "?", "?"


def package_count():
    try:
        n = 0
        with open("/var/lib/dpkg/status", encoding="utf-8",
                  errors="replace") as fh:
            for line in fh:
                if line.startswith("Package: "):
                    n += 1
        return str(n)
    except OSError:
        pass
    try:
        out = subprocess.run(["dpkg-query", "-W", "-f=${binary:Package}\n"],
                             capture_output=True, text=True,
                             timeout=15).stdout
        n = len([l for l in out.splitlines() if l.strip()])
        return str(n) if n else "?"
    except Exception:
        return "?"


def agent_count():
    try:
        with urlopen("http://127.0.0.1:18940/agents", timeout=2) as r:
            d = json.loads(r.read().decode())
        agents = d.get("agents")
        if isinstance(agents, list):
            return str(len(agents))
        return "?"
    except Exception:
        return "?"


def facts():
    try:
        with open("/proc/loadavg") as fh:
            load = fh.read().split()[0]
    except OSError:
        load = "?"
    try:
        out = subprocess.run(["ip", "-4", "-o", "addr", "show", "scope",
                              "global"], capture_output=True, text=True,
                             timeout=5).stdout
        net_s = out.split()[3] if len(out.split()) > 3 else "?"
    except Exception:
        net_s = "?"
    mem_s, _, _ = mem_info()
    disk_s, disk_free = disk_info()
    return {"cpu": "load %s" % load, "mem": mem_s, "disk": disk_s,
            "disk_free": disk_free, "net": net_s,
            "distro": distro(), "kernel": kernel(), "uptime": uptime(),
            "packages": package_count(), "agents": agent_count()}


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

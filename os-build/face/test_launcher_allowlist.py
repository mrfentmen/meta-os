#!/usr/bin/env python3
"""Launcher allowlist proof: fake PATH, real handler, four outcomes.

Builds a temp bin dir with an executable stub for every app the launcher
allows EXCEPT one (mate-calc is left missing), puts it first on PATH, boots
the real os-build/face/launcher.py handler on a loopback ephemeral port, and
checks:
  1. GET /apps lists exactly the stubbed apps (computed, missing one omitted)
  2. POST /launch {unknown app} -> 403 naming the app
  3. POST /launch {app whose binary is missing} -> 500 naming the binary
  4. POST /launch {present app} -> 200 (stub runs, exits 0)

Usage: python3 test_launcher_allowlist.py [--check]
--check: exit non-zero on any failure (for OS-4 verify_tree.sh).
No network beyond 127.0.0.1, no root, no packages. Cleans up after itself.
"""
import importlib.util
import json
import os
import stat
import sys
import tempfile
import threading
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
_LAUNCHER = os.path.join(_HERE, "launcher.py")
MISSING = "mate-calc"  # the one binary the fake PATH deliberately lacks


def _load():
    spec = importlib.util.spec_from_file_location("meta_launcher", _LAUNCHER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _serve(handler):
    from http.server import HTTPServer
    srv = HTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.05},
                     daemon=True).start()
    return srv


def _get(port, path):
    with urllib.request.urlopen("http://127.0.0.1:%d%s" % (port, path)) as r:
        return r.status, json.loads(r.read().decode())


def _post(port, obj):
    req = urllib.request.Request(
        "http://127.0.0.1:%d/launch" % port,
        data=json.dumps(obj).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def main():
    import urllib.error  # noqa: F401  (used in _post)
    failures = []

    def check(name, cond, detail=""):
        print(("PASS " if cond else "FAIL ") + name +
              ((" — " + str(detail)) if detail else ""))
        if not cond:
            failures.append(name)

    mod = _load()
    apps = sorted(mod.ALLOW)
    tmp = tempfile.mkdtemp(prefix="launcher-fakebin-")
    for app in apps:
        if mod.ALLOW[app][0] == MISSING:
            continue
        p = os.path.join(tmp, mod.ALLOW[app][0])
        with open(p, "w") as fh:
            fh.write("#!/bin/sh\nexit 0\n")
        os.chmod(p, os.stat(p).st_mode | stat.S_IXUSR | stat.S_IXGRP |
                 stat.S_IXOTH)
    os.environ["PATH"] = tmp + os.pathsep + "/usr/bin" + os.pathsep + "/bin"
    srv = _serve(mod.H)
    port = srv.server_address[1]

    # 1. /apps is computed: everything stubbed, missing one omitted.
    code, body = _get(port, "/apps")
    expected = sorted(a for a in apps if mod.ALLOW[a][0] != MISSING)
    check("apps-lists-only-resolving-binaries",
          code == 200 and body.get("apps") == expected,
          "got %r want %r" % (body.get("apps"), expected))
    check("apps-omits-missing-binary",
          MISSING not in [a for a in apps
                          if a in (body.get("apps") or [])] and
          not any(mod.ALLOW[a][0] == MISSING for a in (body.get("apps") or [])),
          "mate-calc absent from %r" % (body.get("apps"),))

    # 2. unknown app -> 403 naming the app.
    code, body = _post(port, {"app": "snap-store"})
    check("unknown-app-403-names-app",
          code == 403 and "snap-store" in str(body.get("error")),
          "code=%r body=%r" % (code, body))

    # 3. missing binary -> 500 naming the binary.
    missing_app = [a for a in apps if mod.ALLOW[a][0] == MISSING][0]
    code, body = _post(port, {"app": missing_app})
    check("missing-binary-500-names-binary",
          code == 500 and MISSING in str(body.get("error")) and
          "not installed on this image" in str(body.get("error")),
          "code=%r body=%r" % (code, body))

    # 4. present app -> 200 ok.
    present_app = expected[0]
    code, body = _post(port, {"app": present_app})
    check("present-app-200", code == 200 and body.get("ok") is True,
          "code=%r body=%r" % (code, body))

    srv.shutdown()
    for f in os.listdir(tmp):
        os.unlink(os.path.join(tmp, f))
    os.rmdir(tmp)
    print("launcher-allowlist: %d failure(s)" % len(failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

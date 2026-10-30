"""Cgroup-limits drill (Milo lane, OS-035).

Acceptance: a runaway fixture worker is throttled by its cgroup
while the bus stays responsive; final limits recorded in META_OS.md.

Phases:
  file        the slice file parses and carries exactly the spec
              values (CPUQuota=100%, MemoryMax=1G).
  verify      systemd-analyze verify accepts the slice file
              (offline syntax check only, same as OS-033).
  gate        the host cgroup hierarchy must expose the cpu and
              memory controllers, or live enforcement cannot run.
  enforcement (only when the gate passes): a transient unit in the
              slice runs a 2-thread CPU burner and a memory hog.
              The burner must show throttling (nr_throttled > 0)
              under the slice quota; the hog, capped at a 50M test
              scale by a unit property (the slice's own 1G ceiling
              stays above it), must die before allocating its
              200M target. The 50M test scale is deliberate: the
              drill proves the memory mechanism without needing to
              allocate over 1G on the test box. The slice's 1G
              value itself is proven by the file phase plus this
              mechanism, not by a 1G kill.

What this drill does NOT claim: bus responsiveness on the test
image (there is no live bus here to measure, and no test image
in this repo), and worker attachment (relay-worker@.service is
Pax OS-017, not landed; the drill uses transient units in the
slice instead). On a host where the gate fails, the drill prints
ENVIRONMENT-BLOCKED for the enforcement phase and exits 2: that
is the honest result, not a pass. On this dev VM the gate fails
(cgroup.controllers is empty, subtree_control writes fail, and
transient scopes do not stay tracked), so the drill stops after
the file and verify phases with that verdict.

No network, no Redis, no bus posts. The slice install into
/run/systemd/system is transient (gone on reboot) and removed
in a finally block, along with the drill's temp files.
"""

import os
import re
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
SLICE = os.path.join(ROOT, "os", "services", "relay-workers.slice")
RUN_SLICE = "/run/systemd/system/relay-workers.slice"
TMP = "/tmp"
CPU_OUT = os.path.join(TMP, "os035_cpu.txt")
HOG_PROG = os.path.join(TMP, "os035_hog_progress.txt")
HOG_SCRIPT = os.path.join(TMP, "os035_hog.py")
BURN_SCRIPT = os.path.join(TMP, "os035_burn.py")

EXPECTED = {"CPUQuota": "100%", "MemoryMax": "1G"}
HOG_TARGET_CHUNKS = 20
HOG_CHUNK_MB = 10
HOG_TEST_CAP = "50M"


def parse_slice(path):
    values = {}
    section = None
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("[") and line.endswith("]"):
                section = line[1:-1]
                continue
            if section == "Slice" and "=" in line:
                key, val = line.split("=", 1)
                values[key.strip()] = val.strip()
    return values


def run(cmd, timeout=60):
    return subprocess.run(cmd, capture_output=True, text=True,
                          timeout=timeout)


def wait_for_file(path, timeout=40):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if os.path.exists(path):
            return True
        time.sleep(0.5)
    return False


def wait_for_stable(path, timeout=40):
    """True once path exists and its size is unchanged for 2s."""
    deadline = time.time() + timeout
    last_size = None
    stable_since = None
    while time.time() < deadline:
        if os.path.exists(path):
            size = os.path.getsize(path)
            if size == last_size:
                if stable_since is None:
                    stable_since = time.time()
                elif time.time() - stable_since >= 2:
                    return True
            else:
                last_size = size
                stable_since = None
        time.sleep(0.5)
    return False


def phase_file():
    values = parse_slice(SLICE)
    for key, want in EXPECTED.items():
        got = values.get(key)
        print(f"file: {key}={got} (expected {want})")
        if got != want:
            print(f"file: FAIL: {key} mismatch")
            return False
    print("file: PASS")
    return True


def phase_verify():
    proc = run(["systemd-analyze", "verify", SLICE])
    print(f"verify: exit={proc.returncode}")
    if proc.stdout.strip():
        print(f"verify: stdout: {proc.stdout.strip()}")
    if proc.stderr.strip():
        print(f"verify: stderr: {proc.stderr.strip()}")
    if proc.returncode != 0:
        print("verify: FAIL")
        return False
    print("verify: PASS")
    return True


def phase_gate():
    try:
        with open("/sys/fs/cgroup/cgroup.controllers") as f:
            controllers = set(f.read().split())
    except OSError as exc:
        print(f"gate: cannot read cgroup.controllers: {exc}")
        print("gate: ENVIRONMENT-BLOCKED")
        return False
    print(f"gate: controllers present: {sorted(controllers) or '(none)'}")
    missing = [c for c in ("cpu", "memory") if c not in controllers]
    if missing:
        print(f"gate: missing controllers: {missing}")
        print("gate: ENVIRONMENT-BLOCKED: live enforcement cannot "
              "run on this host")
        return False
    print("gate: PASS")
    return True


def phase_enforcement():
    """Run only when the gate passed. Returns True on full pass."""
    for path in (CPU_OUT, HOG_PROG):
        if os.path.exists(path):
            os.remove(path)
    burn_src = (
        "import threading, time\n"
        "out = '@OUT@'\n"
        "stop = time.time() + 2.0\n"
        "def burn():\n"
        "    while time.time() < stop:\n"
        "        pass\n"
        "ts = [threading.Thread(target=burn) for _ in range(2)]\n"
        "[t.start() for t in ts]\n"
        "[t.join() for t in ts]\n"
        "cg = open('/proc/self/cgroup').read()\n"
        "path = [l.split(':')[2] for l in cg.strip().splitlines()\n"
        "        if l.split(':')[1] == ''][0]\n"
        "stat = dict(l.split() for l in\n"
        "            open('/sys/fs/cgroup' + path + '/cpu.stat')\n"
        "            .read().strip().splitlines()\n"
        "            if len(l.split()) == 2)\n"
        "with open(out, 'w') as fh:\n"
        "    fh.write('cgroup=' + path + '\\n')\n"
        "    fh.write('usage_usec=' + str(stat.get('usage_usec')) + '\\n')\n"
        "    fh.write('nr_throttled=' + str(stat.get('nr_throttled')) + '\\n')\n"
    ).replace("@OUT@", CPU_OUT)
    with open(BURN_SCRIPT, "w") as f:
        f.write(burn_src)
    hog_src = (
        "import os, time\n"
        "prog = '@PROG@'\n"
        "if os.path.exists(prog):\n"
        "    os.remove(prog)\n"
        "bufs = []\n"
        "for i in range(@CHUNKS@):\n"
        "    b = bytearray(@MB@ * 1024 * 1024)\n"
        "    for j in range(0, len(b), 4096):\n"
        "        b[j] = 1\n"
        "    bufs.append(b)\n"
        "    with open(prog, 'a') as fh:\n"
        "        fh.write(str(i) + '\\n')\n"
        "    time.sleep(0.05)\n"
        "print('SURVIVED')\n"
    ).replace("@PROG@", HOG_PROG).replace(
        "@CHUNKS@", str(HOG_TARGET_CHUNKS)).replace(
        "@MB@", str(HOG_CHUNK_MB))
    with open(HOG_SCRIPT, "w") as f:
        f.write(hog_src)
    installed = False
    try:
        shutil.copyfile(SLICE, RUN_SLICE)
        installed = True
        proc = run(["systemctl", "daemon-reload"])
        if proc.returncode != 0:
            print(f"enforcement: daemon-reload failed: {proc.stderr}")
            return False
        proc = run(["systemd-run", "--scope", "--slice=relay-workers.slice",
                    "python3", BURN_SCRIPT])
        if proc.returncode != 0:
            print(f"enforcement: burner launch failed: {proc.stdout} "
                  f"{proc.stderr}")
            return False
        if not wait_for_file(CPU_OUT):
            print("enforcement: burner produced no stats file")
            return False
        stats = {}
        with open(CPU_OUT) as f:
            for line in f:
                if "=" in line:
                    key, val = line.strip().split("=", 1)
                    stats[key] = val
        print(f"enforcement: burner {stats}")
        throttled = stats.get("nr_throttled")
        if throttled is None or int(throttled) <= 0:
            print("enforcement: FAIL: no throttling observed")
            return False
        proc = run(["systemd-run", "--scope", "--slice=relay-workers.slice",
                    "--property", f"MemoryMax={HOG_TEST_CAP}",
                    "python3", HOG_SCRIPT])
        if proc.returncode != 0:
            print(f"enforcement: hog launch failed: {proc.stdout} "
                  f"{proc.stderr}")
            return False
        if not wait_for_stable(HOG_PROG):
            print("enforcement: hog progress never stabilized")
            return False
        with open(HOG_PROG) as f:
            lines = f.read().strip().splitlines()
        print(f"enforcement: hog stopped after {len(lines)} of "
              f"{HOG_TARGET_CHUNKS} chunks at {HOG_TEST_CAP} test cap")
        if len(lines) >= HOG_TARGET_CHUNKS:
            print("enforcement: FAIL: hog survived its cap")
            return False
        print("enforcement: PASS")
        return True
    finally:
        if installed and os.path.exists(RUN_SLICE):
            os.remove(RUN_SLICE)
            run(["systemctl", "daemon-reload"])
        for path in (BURN_SCRIPT, HOG_SCRIPT):
            if os.path.exists(path):
                os.remove(path)


def main():
    ok = phase_file()
    ok = phase_verify() and ok
    if not phase_gate():
        print("RESULT: file+verify PASS, enforcement "
              "ENVIRONMENT-BLOCKED (exit 2)")
        return 2
    ok = phase_enforcement() and ok
    print(f"RESULT: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

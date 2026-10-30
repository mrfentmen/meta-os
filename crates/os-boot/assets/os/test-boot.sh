#!/bin/bash
# Meta OS boot test harness (OS-019, first light).
#
# Boots a built image headless in QEMU, waits for the relay-ready
# marker via the guest agent, reads the image version stamp, and
# screenshots the dashboard. It checks the boot, it does not claim
# it: every check prints its evidence, and any failed check exits
# nonzero with the serial tail attached.
#
# Usage:
#   os/test-boot.sh IMAGE [--timeout SECS] [--screenshot FILE.ppm]
#                   [--memory MB] [--cpus N] [--keep] [--no-snapshot]
#
#   IMAGE       a raw metaos-*.img file (built by os/build-image.sh).
#   --timeout   seconds to wait for the ready marker (default 600).
#   --screenshot  where to write the dashboard screenshot, PPM only
#               (QEMU screendump writes PPM; default is a file in
#               the run dir, removed with it unless --keep is given).
#   --memory / --cpus  guest sizing (defaults 2048 MB, 2 CPUs).
#   --keep      leave the run dir (serial log, qemu log, screenshot)
#               behind and print its path instead of deleting it.
#   --no-snapshot  write through to IMAGE instead of the default
#               snapshot overlay. Default snapshot mode never
#               modifies the image under test.
#
# What it proves, and what it does not:
#   - BOOT_OK: QEMU stayed up past launch (the image at least starts).
#   - READY_OK: /run/metaos/ready appeared, read through the guest
#     agent (qemu-guest-agent, in the image package set under OS-010).
#     The ready file is written by metaos-boot-checklist only once
#     the dashboard service is active (OS-016), so this is the boot
#     gate, not a login prompt.
#   - VERSION: /etc/metaos-version read from the guest, printed
#     verbatim. Matching it against the version on screen is a
#     human check on the screenshot for now (META_OS.md item 12);
#     no OCR step is claimed here.
#   - SCREENSHOT_OK: the screendump file exists and is non-empty.
#   A non-empty PPM is not a rendered dashboard; it is the evidence
#   a human opens to confirm the dashboard is on screen.
#   The full 13-item boot checklist in plan/META_OS.md stays a
#   manual procedure: this harness automates items 1, 2, and the
#   evidence half of 12. Items 3-11 and 13 need a booted image plus
#   hands (kill a unit, cut power, read the brief) and are not
#   claimed by a PASS here.
#
# UNPROVEN, stated plainly: no QEMU run has happened from this
# script. The sandbox has no qemu-system-x86_64 binary, and no
# test image has been booted by it yet, so the launch flags, the
# guest-agent handshake, and the monitor screendump are written
# from the QEMU interface contract, not from a run. The first run
# on a build host may find flag drift; fix the script, not the
# report, when it does.
#
# No bus post, no live Redis, no network: the guest runs isolated
# (no -netdev flag, so no network device at all) and the host side
# only talks to local unix sockets.
set -euo pipefail

IMAGE=""
TIMEOUT=600
SCREENSHOT=""
MEMORY=2048
CPUS=2
KEEP=0
SNAPSHOT=",snapshot=on"

die() { echo "test-boot: ERROR: $*" >&2; exit 2; }
fail() { echo "test-boot: FAIL: $*" >&2; }

usage() {
    sed -n '2,40p' "$0" >&2
    echo "usage: $0 IMAGE [--timeout SECS] [--screenshot FILE.ppm]" >&2
    echo "       [--memory MB] [--cpus N] [--keep] [--no-snapshot]" >&2
    exit 2
}

is_posint() { case "$1" in ''|*[!0-9]*) return 1;; *) [ "$1" -gt 0 ];; esac; }

while [ $# -gt 0 ]; do
    case "$1" in
        --timeout) TIMEOUT="$2"; shift 2;;
        --screenshot) SCREENSHOT="$2"; shift 2;;
        --memory) MEMORY="$2"; shift 2;;
        --cpus) CPUS="$2"; shift 2;;
        --keep) KEEP=1; shift;;
        --no-snapshot) SNAPSHOT=""; shift;;
        -h|--help) usage;;
        --*) die "unknown option: $1";;
        *) [ -z "$IMAGE" ] || die "only one IMAGE allowed"; IMAGE="$1"; shift;;
    esac
done

[ -n "$IMAGE" ] || usage
[ -f "$IMAGE" ] || die "image not found: $IMAGE"
is_posint "$TIMEOUT" || die "timeout must be a positive integer: $TIMEOUT"
is_posint "$MEMORY" || die "memory must be a positive integer: $MEMORY"
is_posint "$CPUS" || die "cpus must be a positive integer: $CPUS"
# Pure argument validation first (builtins only), so a bad call
# fails on its own problem before any tool check runs.
if [ -n "$SCREENSHOT" ]; then
    case "$SCREENSHOT" in
        *.ppm) ;;
        *) die "screenshot path must end in .ppm (QEMU screendump format): $SCREENSHOT";;
    esac
    case "$SCREENSHOT" in
        */*) SHOT_DIR="${SCREENSHOT%/*}";;
        *) SHOT_DIR=".";;
    esac
    [ -d "$SHOT_DIR" ] || die "screenshot directory not found: $SHOT_DIR"
fi
command -v qemu-system-x86_64 >/dev/null 2>&1 \
    || die "qemu-system-x86_64 not found in PATH"
command -v python3 >/dev/null 2>&1 || die "python3 not found in PATH"

RUN_DIR=$(mktemp -d /tmp/metaos-boottest.XXXXXX)
QPID=""
if [ -z "$SCREENSHOT" ]; then
    SCREENSHOT="$RUN_DIR/screenshot.ppm"
fi

cleanup() {
    if [ -n "$QPID" ] && kill -0 "$QPID" 2>/dev/null; then
        kill "$QPID" 2>/dev/null || true
        wait "$QPID" 2>/dev/null || true
    fi
    if [ "$KEEP" -eq 1 ]; then
        echo "test-boot: run dir kept: $RUN_DIR" >&2
    else
        rm -rf "$RUN_DIR"
    fi
}
trap cleanup EXIT

qemu-system-x86_64 \
    -m "$MEMORY" -smp "$CPUS" \
    -drive "file=$IMAGE,format=raw,if=virtio$SNAPSHOT" \
    -display none \
    -monitor "unix:$RUN_DIR/monitor.sock,server,nowait" \
    -chardev "socket,path=$RUN_DIR/qga.sock,server=on,wait=off,id=qga0" \
    -device virtserialport,chardev=qga0,name=org.qemu.guest_agent.0 \
    -serial "file:$RUN_DIR/serial.log" \
    >"$RUN_DIR/qemu.log" 2>&1 &
QPID=$!
sleep 2
if ! kill -0 "$QPID" 2>/dev/null; then
    fail "QEMU exited during launch; qemu log:"
    tail -40 "$RUN_DIR/qemu.log" >&2 || true
    exit 1
fi
echo "test-boot: BOOT_OK image=$IMAGE qemu_pid=$QPID"

# Wait for /run/metaos/ready through the guest agent. The guest
# agent answers only once the guest has booted far enough to run
# it, so connection errors and command errors before the deadline
# mean "not ready yet", not failure. Past the deadline it is a
# failed boot, and the serial tail is the evidence.
if ! python3 - "$RUN_DIR/qga.sock" "$TIMEOUT" <<'QGA_WAIT_PY'
import json, socket, sys, time

sock_path, timeout = sys.argv[1], float(sys.argv[2])
deadline = time.time() + timeout
buf = b""

def connect():
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(5)
    s.connect(sock_path)
    return s

def recv_obj(s):
    global buf
    while b"\n" not in buf:
        chunk = s.recv(4096)
        if not chunk:
            raise ConnectionError("guest agent closed the socket")
        buf += chunk
    line, buf = buf.split(b"\n", 1)
    return json.loads(line.decode("utf-8", "replace"))

def cmd(s, obj):
    s.sendall((json.dumps(obj) + "\n").encode())
    return recv_obj(s)

s = None
while time.time() < deadline:
    try:
        s = connect()
        break
    except OSError:
        time.sleep(2)
if s is None:
    print("QGA_CONNECT_TIMEOUT", file=sys.stderr)
    sys.exit(2)
try:
    cmd(s, {"execute": "guest-sync", "arguments": {"id": 1}})
except Exception as e:
    print("QGA_SYNC_FAILED %s" % e, file=sys.stderr)
    sys.exit(2)

def guest_exec(path, args, capture):
    r = cmd(s, {"execute": "guest-exec", "arguments": {
        "path": path, "arg": args, "capture-output": capture}})
    if "error" in r:
        return None, None
    pid = r["return"]["pid"]
    while True:
        st = cmd(s, {"execute": "guest-exec-status",
                     "arguments": {"pid": pid}})
        if "error" in st:
            return None, None
        ret = st["return"]
        if ret.get("exited"):
            return ret.get("exitcode"), ret.get("out-data")
        if time.time() > deadline:
            return None, None
        time.sleep(2)

while time.time() < deadline:
    code, _ = guest_exec("/usr/bin/test", ["-f", "/run/metaos/ready"], False)
    if code == 0:
        print("READY after %.0fs" % (timeout - (deadline - time.time())))
        sys.exit(0)
    time.sleep(5)
print("READY_TIMEOUT", file=sys.stderr)
sys.exit(2)
QGA_WAIT_PY
then
    fail "ready marker /run/metaos/ready never appeared within ${TIMEOUT}s; serial tail:"
    tail -40 "$RUN_DIR/serial.log" >&2 || true
    exit 1
fi
echo "test-boot: READY_OK marker=/run/metaos/ready"

# Read the version stamp from the guest, same guest-agent channel.
VERSION=$(python3 - "$RUN_DIR/qga.sock" <<'QGA_VERSION_PY'
import base64, json, socket, sys

sock_path = sys.argv[1]
buf = b""
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.settimeout(10)
s.connect(sock_path)

def recv_obj():
    global buf
    while b"\n" not in buf:
        chunk = s.recv(4096)
        if not chunk:
            raise ConnectionError("guest agent closed the socket")
        buf += chunk
    line, buf = buf.split(b"\n", 1)
    return json.loads(line.decode("utf-8", "replace"))

def cmd(obj):
    s.sendall((json.dumps(obj) + "\n").encode())
    return recv_obj(s)

cmd({"execute": "guest-sync", "arguments": {"id": 2}})
r = cmd({"execute": "guest-exec", "arguments": {
    "path": "/bin/cat", "arg": ["/etc/metaos-version"],
    "capture-output": True}})
if "error" in r:
    sys.exit(1)
pid = r["return"]["pid"]
for _ in range(30):
    st = cmd({"execute": "guest-exec-status", "arguments": {"pid": pid}})
    if "error" in st:
        sys.exit(1)
    ret = st["return"]
    if ret.get("exited"):
        if ret.get("exitcode") != 0:
            sys.exit(1)
        data = ret.get("out-data", "")
        sys.stdout.write(base64.b64decode(data).decode("utf-8", "replace"))
        sys.exit(0)
    import time
    time.sleep(1)
sys.exit(1)
QGA_VERSION_PY
) || {
    fail "could not read /etc/metaos-version from the guest"
    exit 1
}
echo "test-boot: VERSION"
echo "$VERSION" | sed 's/^/test-boot:   /'

# Screenshot the dashboard through the monitor socket. The file
# is PPM by construction; a zero-byte file is a failed shot.
python3 - "$RUN_DIR/monitor.sock" "$SCREENSHOT" <<'MON_PY'
import socket, sys, time

sock_path, shot = sys.argv[1], sys.argv[2]
deadline = time.time() + 30
s = None
while time.time() < deadline:
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect(sock_path)
        break
    except OSError:
        time.sleep(1)
if s is None:
    print("MONITOR_CONNECT_TIMEOUT", file=sys.stderr)
    sys.exit(2)
def read_to_prompt():
    buf = b""
    while b"(qemu)" not in buf:
        chunk = s.recv(4096)
        if not chunk:
            break
        buf += chunk

read_to_prompt()
s.sendall(("screendump %s\n" % shot).encode())
read_to_prompt()
sys.exit(0)
MON_PY
if [ ! -s "$SCREENSHOT" ]; then
    fail "screenshot missing or empty: $SCREENSHOT"
    exit 1
fi
SHOT_BYTES=$(wc -c < "$SCREENSHOT" | tr -d ' ')
echo "test-boot: SCREENSHOT_OK $SCREENSHOT $SHOT_BYTES bytes"
echo "test-boot: PASS"
exit 0

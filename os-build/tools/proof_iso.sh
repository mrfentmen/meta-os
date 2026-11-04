#!/bin/bash
# proof_iso.sh — bounded boot proof for the MetaOS arm64 ISO (C4) and for
# disks written by metaos-install.sh (C5).
#
# Boots detached (-display none) on qemu-system-aarch64 -M virt with EDK2,
# polls the framebuffer via the monitor socket until it is NOT a single
# colour (same standard as os-build/tools/proof_boot.sh), saves the
# capture, and ALWAYS kills the VM on exit.
#
#   proof_iso.sh --iso <file.iso>  [--timeout S] [--out DIR]
#   proof_iso.sh --disk <file.qcow2> [--timeout S] [--out DIR]
#
# Output: PASS/FAIL lines + capture path. Exit 1 on any failure.
# This is a BOOT proof, not an install proof: for the ISO it shows the
# live medium boots; the install claim additionally needs the --disk run.
set -eu

ISO=""; DISK=""; TIMEOUT=240; OUTDIR=""; SETTLE=0
HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO="$(CDPATH= cd -- "$HERE/../.." && pwd)"
[ -z "$OUTDIR" ] && OUTDIR="$REPO/os-build/captures"

while [ $# -gt 0 ]; do
    case "$1" in
        --iso) ISO="$2"; shift 2 ;;
        --disk) DISK="$2"; shift 2 ;;
        --timeout) TIMEOUT="$2"; shift 2 ;;
        --out) OUTDIR="$2"; shift 2 ;;
        --settle) SETTLE="$2"; shift 2 ;;
        -h|--help) sed -n '2,14p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) echo "proof_iso: unknown flag $1" >&2; exit 2 ;;
    esac
done
[ "$TIMEOUT" -le 300 ] || { echo "proof_iso: FAIL: timeout $TIMEOUT exceeds 300 s cap" >&2; exit 2; }
if [ -n "$ISO" ] && [ -n "$DISK" ]; then echo "proof_iso: pass exactly one of --iso/--disk" >&2; exit 2; fi
[ -n "$ISO$DISK" ] || { echo "proof_iso: need --iso or --disk" >&2; exit 2; }

QEMU="qemu-system-aarch64"
command -v "$QEMU" >/dev/null 2>&1 || { echo "proof_iso: FAIL: $QEMU not found" >&2; exit 2; }
CODE="/opt/homebrew/share/qemu/edk2-aarch64-code.fd"
VARS_TMPL="/opt/homebrew/share/qemu/edk2-arm-vars.fd"
[ -f "$CODE" ] || { echo "proof_iso: FAIL: EDK2 code missing: $CODE" >&2; exit 2; }
[ -f "$VARS_TMPL" ] || { echo "proof_iso: FAIL: EDK2 vars missing: $VARS_TMPL" >&2; exit 2; }
mkdir -p "$OUTDIR"

if [ -n "$ISO" ]; then
    [ -f "$ISO" ] || { echo "proof_iso: FAIL: ISO not found: $ISO" >&2; exit 2; }
    MODE=iso; SRC="$ISO"; ARCH=arm64
else
    [ -f "$DISK" ] || { echo "proof_iso: FAIL: disk not found: $DISK" >&2; exit 2; }
    MODE=disk; SRC="$DISK"; ARCH=arm64
fi

# EDK2 vars must be writable: work on a temp copy, never the Homebrew file.
VARS="$(mktemp /tmp/proof-vars.XXXXXX.fd)"
cp -f "$VARS_TMPL" "$VARS"
MON="$(mktemp -u /tmp/proof-iso-mon.XXXXXX)"
SER_LOG="$(mktemp /tmp/proof-iso-serial.XXXXXX)"
PPM_TMP="$(mktemp /tmp/proof-iso-fb.XXXXXX)"
QEMU_PID=""

cleanup() {
    if [ -n "$QEMU_PID" ] && kill -0 "$QEMU_PID" 2>/dev/null; then
        python3 - "$MON" <<'PY' 2>/dev/null || true
import socket, sys, time
mon = sys.argv[1]
try:
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(mon); s.settimeout(3)
    time.sleep(0.2)
    try: s.recv(65536)
    except Exception: pass
    s.sendall(b"system_powerdown\n")
    time.sleep(0.5)
    try: s.recv(65536)
    except Exception: pass
    s.close()
except Exception:
    pass
PY
        sleep 2
        kill "$QEMU_PID" 2>/dev/null || true
        sleep 1
        kill -9 "$QEMU_PID" 2>/dev/null || true
    fi
    rm -f "$PPM_TMP" "$VARS"
    rm -f "$MON" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "proof_iso: mode=$MODE src=$SRC timeout=${TIMEOUT}s arch=$ARCH"
echo "proof_iso: edk2=$(basename "$CODE") serial=$SER_LOG"

# shellcheck disable=SC2086
if [ "$MODE" = "iso" ]; then
    DRIVE_ARGS="-cdrom $SRC"
else
    DRIVE_ARGS="-drive file=$SRC,format=qcow2,if=virtio"
fi

# shellcheck disable=SC2086
"$QEMU" \
    -M virt -cpu host -accel hvf -m 2048 -smp 2 \
    -drive "file=$CODE,format=raw,if=pflash,readonly=on" \
    -drive "file=$VARS,format=raw,if=pflash" \
    $DRIVE_ARGS \
    -device virtio-gpu-pci,xres=1024,yres=768 \
    -device qemu-xhci -device usb-kbd -device usb-tablet \
    -serial "file:$SER_LOG" \
    -monitor "unix:$MON,server,nowait" \
    -display none &
QEMU_PID=$!
echo "proof_iso: qemu pid=$QEMU_PID"

for i in $(seq 1 30); do
    if [ -S "$MON" ]; then break; fi
    if ! kill -0 "$QEMU_PID" 2>/dev/null; then
        echo "proof_iso: FAIL: qemu died during start (see $SER_LOG)" >&2
        exit 1
    fi
    sleep 1
done
[ -S "$MON" ] || { echo "proof_iso: FAIL: monitor never appeared at $MON" >&2; exit 1; }

hmp_screendump() {
    python3 - "$MON" "$1" <<'PY'
import socket, sys, time
mon, out = sys.argv[1], sys.argv[2]
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.connect(mon)
s.settimeout(5)
time.sleep(0.3)
try:
    s.recv(65536)
except Exception:
    pass
s.sendall(("screendump %s\n" % out).encode())
time.sleep(0.8)
try:
    s.recv(65536)
except Exception:
    pass
s.close()
PY
}

analyze_ppm() {
    python3 - "$1" <<'PY'
import sys, re
p = sys.argv[1]
try:
    d = open(p, "rb").read()
except Exception:
    print("BAD cannot-read"); sys.exit(0)
m = re.match(rb'P6\n(\d+) (\d+)\n(\d+)\n', d)
if not m:
    print("BAD no-header"); sys.exit(0)
w, h, mx = int(m.group(1)), int(m.group(2)), int(m.group(3))
hdr = len(m.group(0))
pix = d[hdr:]
want = w * h * 3
if len(pix) < want:
    print("BAD short %dx%d" % (w, h)); sys.exit(0)
pix = pix[:want]
step = max(1, len(pix) // (3 * 20000))
uniq = set()
maxv = 0
for i in range(0, len(pix), 3 * step):
    uniq.add(pix[i:i+3])
    v = pix[i]
    if pix[i+1] > v: v = pix[i+1]
    if pix[i+2] > v: v = pix[i+2]
    if v > maxv: maxv = v
print("%d %d %d %d" % (w, h, len(uniq), maxv))
PY
}

echo "proof_iso: polling framebuffer every 5s (single-colour = FAIL)..."
FOUND=0
FW=0; FH=0; FUNIQ=0; FMAX=0
ELAPSED=0
while [ "$ELAPSED" -lt "$TIMEOUT" ]; do
    sleep 5
    ELAPSED=$((ELAPSED + 5))
    if ! kill -0 "$QEMU_PID" 2>/dev/null; then
        echo "proof_iso: FAIL: qemu died after ${ELAPSED}s (see $SER_LOG)" >&2
        exit 1
    fi
    rm -f "$PPM_TMP"
    hmp_screendump "$PPM_TMP" 2>/dev/null || true
    if [ ! -s "$PPM_TMP" ]; then
        echo "proof_iso: ... ${ELAPSED}s: no frame yet"
        continue
    fi
    info="$(analyze_ppm "$PPM_TMP")"
    # shellcheck disable=SC2086
    set -- $info
    if [ "${1:-}" = "BAD" ]; then
        echo "proof_iso: ... ${ELAPSED}s: $info"
        continue
    fi
    FW="$1"; FH="$2"; FUNIQ="$3"; FMAX="$4"
    echo "proof_iso: ... ${ELAPSED}s: ${FW}x${FH} unique~${FUNIQ} max=${FMAX}"
    if [ "$FMAX" -lt 16 ]; then
        continue
    fi
    if [ "$FUNIQ" -le 5 ]; then
        continue
    fi
    FOUND=1
    break
done

if [ "$FOUND" -ne 1 ]; then
    echo "proof_iso: FAIL: framebuffer stayed single-colour/black after ${TIMEOUT}s" >&2
    echo "proof_iso: last=${FW}x${FH} unique~${FUNIQ} max=${FMAX} serial=$SER_LOG" >&2
    exit 1
fi

# --settle S: press Enter (boot the highlighted GRUB entry / start the
# installed system), then keep the VM up to S more seconds so the kernel
# and userspace actually run. Bounded: ELAPSED + SETTLE <= TIMEOUT.
if [ "$SETTLE" -gt 0 ]; then
    REMAIN=$((TIMEOUT - ELAPSED - 10))
    [ "$REMAIN" -gt 0 ] || REMAIN=0
    [ "$SETTLE" -le "$REMAIN" ] || SETTLE="$REMAIN"
    echo "proof_iso: settle: sending Enter, then ${SETTLE}s more (of ${TIMEOUT}s budget)"
    python3 - "$MON" <<'PY' 2>/dev/null || true
import socket, sys, time
mon = sys.argv[1]
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.connect(mon)
s.settimeout(5)
time.sleep(0.3)
try: s.recv(65536)
except Exception: pass
s.sendall(b"sendkey ret\n")
time.sleep(0.5)
try: s.recv(65536)
except Exception: pass
s.close()
PY
    SLEPT=0
    while [ "$SLEPT" -lt "$SETTLE" ]; do
        sleep 5
        SLEPT=$((SLEPT + 5))
        ELAPSED=$((ELAPSED + 5))
        if ! kill -0 "$QEMU_PID" 2>/dev/null; then
            echo "proof_iso: FAIL: qemu died during settle (see $SER_LOG)" >&2
            exit 1
        fi
        echo "proof_iso: ... settle ${SLEPT}/${SETTLE}s"
    done
    rm -f "$PPM_TMP"
    hmp_screendump "$PPM_TMP" 2>/dev/null || true
    if [ -s "$PPM_TMP" ]; then
        info="$(analyze_ppm "$PPM_TMP")"
        # shellcheck disable=SC2086
        set -- $info
        if [ "${1:-}" != "BAD" ]; then
            FW="$1"; FH="$2"; FUNIQ="$3"; FMAX="$4"
            echo "proof_iso: ... settled: ${FW}x${FH} unique~${FUNIQ} max=${FMAX}"
            if [ "$FMAX" -lt 16 ] || [ "$FUNIQ" -le 5 ]; then
                echo "proof_iso: FAIL: settled framebuffer is single-colour/black" >&2
                exit 1
            fi
        fi
    fi
fi

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BASE="iso-${ARCH}-${STAMP}"
cp -f "$PPM_TMP" "$OUTDIR/$BASE.ppm"
SAVED="$OUTDIR/$BASE.ppm"

if python3 -c "from PIL import Image; Image.open('$SAVED').save('${SAVED%.ppm}.png')" 2>/dev/null; then
    echo "proof_iso: PASS: mode=$MODE framebuffer ${FW}x${FH} unique~${FUNIQ} (not single-colour)"
    echo "proof_iso: capture: $SAVED"
    echo "proof_iso: capture: ${SAVED%.ppm}.png"
else
    if command -v sips >/dev/null 2>&1 && sips -s format png "$SAVED" --out "${SAVED%.ppm}.png" >/dev/null 2>&1; then
        echo "proof_iso: PASS: mode=$MODE framebuffer ${FW}x${FH} unique~${FUNIQ} (not single-colour)"
        echo "proof_iso: capture: $SAVED"
        echo "proof_iso: capture: ${SAVED%.ppm}.png"
    else
        echo "proof_iso: PASS: mode=$MODE framebuffer ${FW}x${FH} unique~${FUNIQ} (not single-colour)"
        echo "proof_iso: capture: $SAVED (no PNG converter available)"
    fi
fi
echo "proof_iso: serial tail:"
tail -5 "$SER_LOG" 2>/dev/null || true
echo "proof_iso: serial: $SER_LOG monitor: $MON pid: $QEMU_PID"
exit 0

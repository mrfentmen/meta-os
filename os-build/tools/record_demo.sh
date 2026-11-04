#!/bin/bash
# record_demo.sh — record the guest's own framebuffer to a movie.
#
# Why not screen-record the Mac: that films a QEMU window with host chrome, a
# host cursor and whatever else is on the desktop. This asks QEMU's monitor for
# a screendump of the guest's framebuffer instead, so every pixel in the file was
# drawn by Meta OS at 1920x1080 and nothing else is in shot.
#
# Usage
#   METAOS_ALLOW_QEMU=1 sh os-build/tools/record_demo.sh --record [options]
#   sh os-build/tools/record_demo.sh --selftest        # no QEMU, proves the encode path
#   sh os-build/tools/record_demo.sh --encode DIR      # re-encode a captured DIR
#
# Options for --record
#   --seconds N     how long to capture after the desktop appears (default 180)
#   --fps N         capture attempts per second (default 10; ~8-12 is the real ceiling)
#   --out FILE      output movie (default os-build/captures/demo-<stamp>.mp4)
#   --dir DIR       where frames go (default /tmp/metaos-rec/<stamp>)
#   --wait N        max seconds to wait for a non-blank screen (default 150)
#
# Honesty rules baked in:
#   * frames are captured at whatever rate the monitor answers; each frame's real
#     timestamp is recorded and the encode replays true duration, so motion is
#     real-time rather than sped up or smoothed over;
#   * the reported fps in the final line is the MEASURED rate, never the asked-for
#     one;
#   * the image is opened with snapshot=on, so the recording never writes to it.
set -u

HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(CDPATH= cd -- "$HERE/../.." && pwd)
IMAGE=${IMAGE:-/tmp/metaos.ext4}
KERNEL=${KERNEL:-/tmp/meta-boot/vmlinuz}
INITRD=${INITRD:-/tmp/meta-boot/initrd.img}
STAMP=$(date -u +%Y%m%dT%H%M%SZ)

MODE=record
SECONDS_TO_CAP=180
FPS=10
OUT=
DIR=
WAIT_MAX=150
ENCODE_DIR=

while [ $# -gt 0 ]; do
  case "$1" in
    --record) MODE=record ;;
    --selftest) MODE=selftest ;;
    --encode) MODE=encode; ENCODE_DIR=${2:-}; shift ;;
    --seconds) SECONDS_TO_CAP=${2:-180}; shift ;;
    --fps) FPS=${2:-10}; shift ;;
    --out) OUT=${2:-}; shift ;;
    --dir) DIR=${2:-}; shift ;;
    --wait) WAIT_MAX=${2:-150}; shift ;;
    -h|--help) sed -n '2,30p' "$0"; exit 0 ;;
    *) echo "record_demo: unknown argument: $1" >&2; exit 2 ;;
  esac
  shift
done

# --- encode ---------------------------------------------------------------
# DIR holds f-000001.jpg ... and times.txt ("<filename> <seconds since first>").
# The concat demuxer gets an explicit duration per frame, so a capture hiccup
# shows up as a held frame instead of a jump cut.
encode() {
  _dir=$1
  _out=$2
  _list="$_dir/concat.txt"
  if [ ! -s "$_dir/times.txt" ]; then
    echo "encode: no times.txt in $_dir" >&2
    return 1
  fi
  awk 'NR==1{prev=$2; print "ffconcat version 1.0"; print "file '"'"'" $1 "'"'"'"; next}
       {d=$2-prev; if (d < 0.01) d=0.01; printf "duration %.4f\n", d;
        print "file '"'"'" $1 "'"'"'"; prev=$2}
       END{if (NR>0) printf "duration 0.1000\n"}' \
      "$_dir/times.txt" >"$_list"
  _n=$(wc -l <"$_dir/times.txt" | tr -d ' ')
  if [ "$_n" -lt 2 ]; then
    echo "encode: only $_n frame(s), nothing to watch" >&2
    return 1
  fi
  ffmpeg -y -v error -f concat -safe 0 -i "$_list" \
    -vf "fps=30,format=yuv420p" -c:v libx264 -preset veryfast -crf 18 \
    -movflags +faststart "$_out" || return 1
  if [ ! -s "$_out" ]; then
    echo "encode: ffmpeg wrote nothing" >&2
    return 1
  fi
  return 0
}

probe() {
  ffprobe -v error -select_streams v:0 \
    -show_entries stream=width,height,nb_frames,r_frame_rate:format=duration,size \
    -of default=noprint_wrappers=1 "$1"
}

# --- selftest -------------------------------------------------------------
# Runs the real encoder over synthetic frames, so the only untested part of a
# real take is QEMU itself. Fails loudly if the movie is not what was ordered.
if [ "$MODE" = selftest ]; then
  T=$(mktemp -d /tmp/rec-selftest.XXXXXX) || exit 1
  python3 - "$T" <<'PY' || { echo "selftest: could not draw frames"; rm -rf "$T"; exit 1; }
import sys, os
from PIL import Image, ImageDraw
d = sys.argv[1]
times = []
for i in range(60):
    im = Image.new("RGB", (1920, 1080), (7, 11, 22))
    dr = ImageDraw.Draw(im)
    dr.rectangle([100 + i * 20, 400, 300 + i * 20, 600], fill=(24, 119, 242))
    n = "f-%06d.jpg" % (i + 1)
    im.save(os.path.join(d, n), quality=90)
    times.append("%s %.4f" % (n, i * 0.1))
open(os.path.join(d, "times.txt"), "w").write("\n".join(times) + "\n")
PY
  encode "$T" "$T/out.mp4" || { echo "selftest: FAIL encode"; rm -rf "$T"; exit 1; }
  INFO=$(probe "$T/out.mp4") || { echo "selftest: FAIL probe"; rm -rf "$T"; exit 1; }
  echo "$INFO"
  DUR=$(echo "$INFO" | awk -F= '/^duration=/{print $2}')
  WH=$(echo "$INFO" | awk -F= '/^width=/{w=$2} /^height=/{h=$2} END{print w"x"h}')
  OK=1
  awk -v d="$DUR" 'BEGIN{exit !(d > 5.5 && d < 6.5)}' || { echo "selftest: FAIL duration $DUR (wanted ~6.0)"; OK=0; }
  [ "$WH" = "1920x1080" ] || { echo "selftest: FAIL size $WH"; OK=0; }
  [ -s "$T/out.mp4" ] || { echo "selftest: FAIL empty file"; OK=0; }
  if [ "$OK" = 1 ]; then
    echo "selftest: PASS 60 frames @ 10 fps -> $DUR s, $WH, $(du -h "$T/out.mp4" | cut -f1)"
  fi
  rm -rf "$T"
  [ "$OK" = 1 ] || exit 1
  exit 0
fi

# --- encode only ----------------------------------------------------------
if [ "$MODE" = encode ]; then
  [ -n "$ENCODE_DIR" ] || { echo "record_demo: --encode needs a directory" >&2; exit 2; }
  OUT=${OUT:-$ROOT/os-build/captures/demo-$STAMP.mp4}
  encode "$ENCODE_DIR" "$OUT" || exit 1
  probe "$OUT"
  echo "wrote $OUT"
  exit 0
fi

# --- record ---------------------------------------------------------------
. "$HERE/qemu_guard.sh"
qemu_guard "record_demo.sh"

DIR=${DIR:-/tmp/metaos-rec/$STAMP}
OUT=${OUT:-$ROOT/os-build/captures/demo-$STAMP.mp4}
mkdir -p "$DIR"

for f in "$IMAGE" "$KERNEL" "$INITRD"; do
  [ -e "$f" ] || { echo "record_demo: missing $f" >&2; exit 1; }
done

# One VM at a time. Two boots of the same 16 GiB image is how the fans get loud.
if pgrep -f "qemu-system-aarch64" >/dev/null 2>&1; then
  echo "record_demo: a QEMU is already running; refusing to start a second" >&2
  pgrep -fl "qemu-system-aarch64" >&2
  exit 1
fi

MON=$(mktemp -u /tmp/rec-mon.XXXXXX)
SER="$DIR/serial.log"
echo "record_demo: booting $IMAGE (snapshot=on) -> $DIR"

qemu-system-aarch64 \
  -M virt -cpu host -accel hvf -m 4096 -smp 4 \
  -kernel "$KERNEL" -initrd "$INITRD" \
  -append "root=/dev/vda rw console=ttyAMA0 console=tty0 plymouth.enable=0" \
  -drive "file=$IMAGE,if=virtio,format=raw,snapshot=on" \
  -device virtio-gpu-pci,xres=1920,yres=1080 \
  -device qemu-xhci -device usb-kbd -device usb-tablet \
  -netdev "user,id=n0" -device virtio-net-pci,netdev=n0 \
  -chardev "socket,id=c0,path=/tmp/rec-ser.$$,server=on,wait=off,logfile=$SER" \
  -serial chardev:c0 \
  -monitor "unix:$MON,server,nowait" \
  -display none &
QPID=$!
trap 'kill $QPID 2>/dev/null; wait $QPID 2>/dev/null' EXIT INT TERM

# Capture. The loop never guesses that the screen is ready: it probes with a
# screendump, decides whether the frame is a single colour (kernel text, black,
# greeter mid-paint) and only starts counting seconds once something is drawn.
python3 - "$MON" "$DIR" "$FPS" "$SECONDS_TO_CAP" "$WAIT_MAX" <<'PY'
import os, socket, sys, time

mon, outdir, fps, seconds, waitmax = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
from PIL import Image

def grab(path, timeout=4.0):
    """Ask the monitor for one screendump and wait for a complete PPM."""
    if os.path.exists(path):
        os.remove(path)
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        s.connect(mon)
        s.settimeout(timeout)
        time.sleep(0.05)
        try:
            s.recv(65536)
        except Exception:
            pass
        s.sendall(("screendump %s\n" % path).encode())
        deadline = time.time() + timeout
        last = -1
        while time.time() < deadline:
            if os.path.exists(path):
                sz = os.path.getsize(path)
                if sz > 1024 and sz == last:
                    return True
                last = sz
            time.sleep(0.02)
        return os.path.exists(path) and os.path.getsize(path) > 1024
    except Exception as exc:
        print("record: monitor error: %s" % exc, file=sys.stderr)
        return False
    finally:
        try:
            s.close()
        except Exception:
            pass

def distinct(im):
    """How many colours in the frame. 1 means nothing is drawn yet."""
    return len(im.convert("RGB").getcolors(maxcolors=4096) or [])

probe_ppm = os.path.join(outdir, "probe.ppm")
started = None
t_wait = time.time()
while time.time() - t_wait < waitmax:
    if not grab(probe_ppm):
        time.sleep(0.5)
        continue
    try:
        im = Image.open(probe_ppm)
        im.load()
        n = distinct(im)
    except Exception:
        n = 0
    if n > 8:
        started = time.time()
        print("record: desktop is up after %.0fs (%d colours)" % (started - t_wait, n), flush=True)
        break
    time.sleep(0.5)
if started is None:
    print("record: FAIL no drawn screen within %ds" % waitmax, file=sys.stderr)
    sys.exit(1)

interval = 1.0 / max(1, fps)
times = []
i = 0
t_first = None
while time.time() - started < seconds:
    t_target = started + i * interval
    now = time.time()
    if now < t_target:
        time.sleep(min(t_target - now, 0.05))
        continue
    ppm = os.path.join(outdir, "grab.ppm")
    if not grab(ppm):
        time.sleep(0.05)
        continue
    name = "f-%06d.jpg" % (i + 1)
    try:
        im = Image.open(ppm)
        im.load()
    except Exception:
        continue
    # Full frame, no downscale: the deliverable is 1080p.
    im.convert("RGB").save(os.path.join(outdir, name), quality=88, optimize=False)
    if t_first is None:
        t_first = time.time()
    times.append((name, time.time() - t_first))
    i += 1
    os.remove(ppm)
    if i % 50 == 0:
        print("record: %d frames, %.1fs elapsed" % (i, time.time() - started), flush=True)

with open(os.path.join(outdir, "times.txt"), "w") as f:
    for n, t in times:
        f.write("%s %.4f\n" % (n, t))
if times:
    real = times[-1][1] / max(1, len(times) - 1)
    print("record: captured %d frames, measured %.1f fps over %.1fs"
          % (len(times), 1.0 / real if real else 0, times[-1][1]), flush=True)
PY
RC=$?

# Always power the guest down: a snapshot VM left running holds RAM and a core.
python3 - "$MON" <<'PY' 2>/dev/null || true
import socket, sys, time
try:
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(sys.argv[1]); s.settimeout(3); time.sleep(0.2)
    try:
        s.recv(65536)
    except Exception:
        pass
    s.sendall(b"system_powerdown\n"); time.sleep(0.5); s.close()
except Exception:
    pass
PY
sleep 2
kill $QPID 2>/dev/null
wait $QPID 2>/dev/null
trap - EXIT INT TERM

[ "$RC" = 0 ] || { echo "record_demo: capture failed (rc=$RC); frames kept in $DIR" >&2; exit 1; }

if [ ! -s "$DIR/times.txt" ]; then
  echo "record_demo: no frames captured; see $SER" >&2
  exit 1
fi

encode "$DIR" "$OUT" || { echo "record_demo: encode failed; frames kept in $DIR" >&2; exit 1; }
probe "$OUT"
echo "frames: $DIR"
echo "wrote:  $OUT"

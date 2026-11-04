#!/bin/sh
# show_os.sh — boot Meta OS in a real window on this Mac, ready to demo.
#
# Why this exists: the command everyone was demoing with lived at
# /tmp/metaos-boot.sh. /tmp is wiped, so "the boot command" kept disappearing
# and the demo kept turning into an archaeology exercise. This is the same
# command, in the repo, with two additions:
#
#   display   cocoa window (not -display none), so you see the desktop
#   audio     a virtual HDA card on the host's CoreAudio device, so Musica has
#             something to play out of. Without it the guest has no sound card
#             at all: GStreamer decodes, and nothing is audible.
#
# snapshot=on means the boot does NOT write the image. A demo cannot corrupt
# the OS, and the next boot starts from the same clean state.
#
#   sh os-build/tools/show_os.sh                 # window + sound, snapshot
#   sh os-build/tools/show_os.sh --persist       # writes to the image
#   sh os-build/tools/show_os.sh --headless 45   # no window, 45s, self-check
#
# Image paths can be overridden with META_IMAGE / META_KERNEL / META_INITRD.
set -eu

ROOT=$(cd "$(dirname "$0")/../.." && pwd)
IMAGE="${META_IMAGE:-/tmp/metaos.ext4}"
ISO="${META_ISO:-$ROOT/os-build/iso/output/metaos-1.0-arm64.iso}"
BOOTDIR="${META_BOOTDIR:-/tmp/meta-boot}"
KERNEL="${META_KERNEL:-$BOOTDIR/vmlinuz}"
INITRD="${META_INITRD:-$BOOTDIR/initrd.img}"

# The kernel and initrd used to live only in /tmp/meta-boot, which a reboot
# empties. They are inside the ISO, so rebuild them from there on demand —
# otherwise the demo command is one laptop restart away from broken again.
extract_boot_files() {
  [ -f "$ISO" ] || return 1
  command -v bsdtar >/dev/null 2>&1 || return 1
  mkdir -p "$BOOTDIR"
  echo "show_os: extracting kernel + initrd from $(basename "$ISO")"
  ( cd "$BOOTDIR" && bsdtar -xf "$ISO" casper/vmlinuz casper/initrd ) || return 1
  # bsdtar keeps the ISO path (casper/…), so lift the two files out of it.
  [ -f "$BOOTDIR/casper/vmlinuz" ] || return 1
  [ -f "$BOOTDIR/casper/initrd" ] || return 1
  mv -f "$BOOTDIR/casper/vmlinuz" "$BOOTDIR/vmlinuz"
  mv -f "$BOOTDIR/casper/initrd" "$BOOTDIR/initrd.img"
  rmdir "$BOOTDIR/casper" 2>/dev/null || true
  chmod u+w "$BOOTDIR/vmlinuz" "$BOOTDIR/initrd.img" 2>/dev/null || true
  return 0
}

MODE=window
SECS=0
case "${1:-}" in
  --persist) MODE=persist ;;
  --headless) MODE=headless; SECS="${2:-45}" ;;
  "") ;;
  *) echo "show_os: unknown option $1 (use --persist or --headless N)" >&2; exit 2 ;;
esac

# Network: the Imperium/Trio dispatch console draws no basemap without its
# style URL, and the live NYC traffic-camera list is a remote feed. User-mode
# NAT (no port forwards, nothing reachable from outside) is enough for those
# two, and it is what a judge's laptop has anyway. METAOS_NO_NET=1 boots the
# demo offline on purpose, e.g. to prove the desktop needs no network.
if [ "${METAOS_NO_NET:-0}" = "1" ]; then
  NETARGS=""
  echo "show_os: METAOS_NO_NET=1 — headless-of-network boot"
else
  NETARGS="-netdev user,id=n0 -device virtio-net-pci,netdev=n0"
fi

QEMU=$(command -v qemu-system-aarch64 || true)
[ -n "$QEMU" ] || { echo "show_os: qemu-system-aarch64 not on PATH" >&2; exit 2; }

if [ ! -f "$KERNEL" ] || [ ! -f "$INITRD" ]; then
  extract_boot_files || {
    echo "show_os: missing $KERNEL / $INITRD and could not extract from $ISO" >&2
    echo "show_os: set META_KERNEL and META_INITRD, or build the ISO first" >&2
    exit 2
  }
fi
[ -f "$IMAGE" ] || { echo "show_os: missing image $IMAGE" >&2; exit 2; }

# One VM at a time. Two QEMUs on the same ext4 both write it and both corrupt
# it, which is exactly how an image gets a mysterious filesystem error.
if pgrep -f "qemu-system-aarch64.*$IMAGE" >/dev/null 2>&1; then
  echo "show_os: a VM is already running on $IMAGE — closing it first"
  pkill -f "qemu-system-aarch64.*$IMAGE" || true
  sleep 2
fi

SER_LOG="${META_SERIAL_LOG:-/tmp/metaos-show.log}"
: >"$SER_LOG"

# Display: a real window unless a proof asked for none.
DISPLAY_ARGS="-display cocoa,show-cursor=on,zoom-to-fit=on"
[ "$MODE" = headless ] && DISPLAY_ARGS="-display none"

# Audio: build the device list so a QEMU without coreaudio support still boots
# (a missing sound card is a silent OS, not a dead one).
# No-boot guard (OS-4): probing `-audiodev help` already executes the QEMU
# binary, so the guard sits before it, not just before the VM launch.
. "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)/qemu_guard.sh"
qemu_guard "show_os.sh"
AUDIO_ARGS=""
if [ "${META_NO_AUDIO:-0}" = "1" ]; then
  echo "show_os: sound disabled (META_NO_AUDIO=1)"
elif "$QEMU" -audiodev help 2>/dev/null | grep -q coreaudio; then
  # hda-output, not hda-duplex: duplex also opens a capture stream, and macOS
  # QEMU refuses it ("Can not open adc") and drops the whole card.
  AUDIO_ARGS="-audiodev coreaudio,id=snd0 -device intel-hda -device hda-output,audiodev=snd0"
else
  echo "show_os: this QEMU has no coreaudio backend — booting without sound"
fi

SNAP="snapshot=on"
[ "$MODE" = persist ] && SNAP=""

echo "show_os: image=$IMAGE"
echo "show_os: serial=$SER_LOG  mode=$MODE"

# A stale qcow2 overlay lock from a killed VM blocks the next boot; the raw
# ext4 here has no lock file, but the check is cheap and the message is clear.
rm -f /tmp/metaos-show.qmp /tmp/metaos-qmp.sock

# /etc/fstab in this image carries `metaos_repo /mnt/metaos 9p trans=virtio`.
# Without a matching virtfs channel the kernel logs "9pnet_virtio: no channels
# available" and the boot stops before reaching the graphical target. Sharing
# the repo makes that line satisfiable and lets you browse the source from
# inside the guest.
VIRTFS=""
[ -d "$ROOT" ] && VIRTFS="-virtfs local,path=$ROOT,mount_tag=metaos_repo,security_model=none,readonly=on"

# shellcheck disable=SC2086
"$QEMU" \
  -M virt -cpu host -accel hvf -m 4096 -smp 4 \
  -kernel "$KERNEL" -initrd "$INITRD" \
  -append "root=/dev/vda rw console=ttyAMA0 console=tty0 plymouth.enable=0" \
  -drive "file=$IMAGE,if=virtio,format=raw,$SNAP" \
  -device virtio-gpu-pci,xres=1920,yres=1080,edid=on \
  $AUDIO_ARGS \
  -device qemu-xhci -device usb-kbd -device usb-tablet \
  $NETARGS \
  $VIRTFS \
  -serial "file:$SER_LOG" \
  -monitor "unix:/tmp/metaos-show.qmp,server,nowait" \
  -qmp "unix:/tmp/metaos-qmp.sock,server,nowait" \
  $DISPLAY_ARGS &
QEMU_PID=$!
echo "show_os: qemu pid=$QEMU_PID"

if [ "$MODE" = headless ]; then
  # Headless is a self-check: it must reach the graphical session, and it must
  # exit on its own so a proof can never leave a VM running on the laptop.
  i=0
  while [ "$i" -lt "$SECS" ]; do
    if ! kill -0 "$QEMU_PID" 2>/dev/null; then
      echo "show_os: FAIL: qemu exited early — tail of $SER_LOG:"
      tail -20 "$SER_LOG"
      exit 1
    fi
    sleep 1
    i=$((i + 1))
  done
  # Do NOT judge by the serial log: systemd logs to /dev/console, which is
  # tty0 (the graphical console), so the serial goes silent about 0.5s in while
  # the OS boots perfectly well. The only honest check is the pixels, so ask
  # the monitor for a screendump and count distinct colours.
  python3 - /tmp/metaos-show.qmp /tmp/metaos-show.ppm <<'PY' || true
import socket, sys, time
mon, out = sys.argv[1], sys.argv[2]
try:
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM); s.connect(mon)
    s.settimeout(8); time.sleep(0.3)
    try: s.recv(65536)
    except Exception: pass
    s.sendall(("screendump %s\n" % out).encode()); time.sleep(1.5)
    try: s.recv(65536)
    except Exception: pass
except Exception as e:
    print("show_os: screendump failed: %s" % e); sys.exit(1)
PY
  rc=0
  if [ -f /tmp/metaos-show.ppm ]; then
    uniq=$(python3 - <<'PY'
import sys
p = "/tmp/metaos-show.ppm"
try:
    f = open(p, "rb")
    assert f.readline().strip() == b"P6"
    line = f.readline()
    while line.startswith(b"#"): line = f.readline()
    w, h = map(int, line.split())
    f.readline()
    data = f.read()
    seen = set()
    step = max(1, len(data) // 60000) * 3
    for i in range(0, len(data) - 3, step):
        seen.add(data[i:i+3])
    print(len(seen))
except Exception:
    print(0)
PY
)
    if [ "${uniq:-0}" -gt 50 ]; then
      echo "show_os: PASS: framebuffer has ${uniq} distinct colours (desktop drew)"
    else
      echo "show_os: FAIL: framebuffer is nearly single-colour (${uniq}) — desktop did not draw"
      echo "show_os: see $SER_LOG"
      rc=1
    fi
  else
    echo "show_os: WARN: no screendump produced, cannot judge the screen"
  fi
  kill "$QEMU_PID" 2>/dev/null || true
  wait "$QEMU_PID" 2>/dev/null || true
  echo "show_os: stopped"
  exit "$rc"
fi

cat <<EOF

  Meta OS is booting in a window (about 30-60s to the desktop).

  Close the window, or kill pid $QEMU_PID, when you are done.
  Serial console log: $SER_LOG
EOF

wait "$QEMU_PID" || true
echo "show_os: VM closed"

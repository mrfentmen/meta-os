#!/bin/sh
# sync_image.sh — put the current repo tree onto a Meta OS ext4 image.
#
# Why this exists: the image is built from this working tree, so the guest is
# always as old as the last time somebody provisioned it. Tonight the guest had
# 19 dock tiles while the repo had 27, 22 icons while the repo had 26, no
# /opt/face-site/aegis at all, and a session.sh with no single-dock guard.
#
# macOS cannot loop-mount ext4, so this runs provision.sh inside a privileged
# container with the image mounted. It writes only what provision.sh writes
# (/opt/face, /opt/face-site, /usr/local/bin/meta-*, the user units, the dock
# icons, the panel/dock themes) plus the shell prompt fix.
#
# Usage:
#   sh os-build/tools/sync_image.sh                  # provision /tmp/metaos.ext4
#   sh os-build/tools/sync_image.sh --dry-run        # only report what is there
#   IMAGE=/path/to/other.ext4 sh os-build/tools/sync_image.sh
#
# It refuses to touch an image that QEMU has open. Shut the VM down first: a
# write underneath a running guest is how you get a corrupted filesystem.
set -eu

IMAGE="${IMAGE:-/tmp/metaos.ext4}"
DRY=0
FORCE=0

while [ $# -gt 0 ]; do
  case "$1" in
    --image) IMAGE="$2"; shift 2 ;;
    --dry-run) DRY=1; shift ;;
    --force) FORCE=1; shift ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "sync_image: unknown flag $1" >&2; exit 2 ;;
  esac
done

die() { echo "sync_image: $*" >&2; exit 1; }

REPO="$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)"
[ -f "$IMAGE" ] || die "no image at $IMAGE"
[ -f "$REPO/os-build/face/provision.sh" ] || die "no provision.sh under $REPO/os-build/face"
command -v docker >/dev/null 2>&1 || die "docker not found — macOS has no loop mount, this needs a privileged container"

echo "sync_image: image=$IMAGE ($(( $(wc -c <"$IMAGE") / 1048576 )) MB)"
echo "sync_image: repo=$REPO"
echo "sync_image: mode=$([ "$DRY" = 1 ] && echo dry-run || echo write)"

# --- refuse to write under a running guest -----------------------------------
if pgrep -f "file=$IMAGE" >/dev/null 2>&1; then
  if [ "$DRY" = 1 ]; then
    echo "sync_image: WARNING a QEMU is running with this image; dry-run mounts read-only"
  elif [ "$FORCE" = 1 ]; then
    echo "sync_image: WARNING --force: writing while QEMU has this image open"
  else
    die "QEMU has $IMAGE open (pgrep -f file=$IMAGE). Shut the VM down, or re-run with --dry-run."
  fi
fi

MODE=rw
[ "$DRY" = 1 ] && MODE=ro

# -i is required: the container script arrives on stdin. Without it docker
# leaves stdin closed, `bash -s` reads an empty script, and the run "succeeds"
# having done nothing at all.
docker run --rm -i --privileged \
  -v "$IMAGE:/disk.img" \
  -v "$REPO:/repo:ro" \
  -e MODE="$MODE" \
  -e DRY="$DRY" \
  ubuntu:24.04 bash -s <<'CONTAINER'
set -eu
mkdir -p /mnt/img
if [ "$MODE" = ro ]; then
  mount -o loop,ro,noload /disk.img /mnt/img 2>/dev/null || mount -o loop,ro /disk.img /mnt/img
else
  mount -o loop /disk.img /mnt/img
fi
trap 'umount /mnt/img 2>/dev/null || true' EXIT INT TERM

show() {   # $1 = humans-readable label, rest = command
  label=$1; shift
  printf '%-34s ' "$label"
  "$@" 2>/dev/null || echo "—"
}

count_tiles() { grep -cE '^[[:space:]]*add_app ' /mnt/img/opt/face/meta-desktop.sh 2>/dev/null || echo 0; }
# Count the PNGs, not every entry: the icon dir also holds index.theme and a
# 128x128/ subdir, so a plain ls made a synced image look two icons ahead.
count_icons() { find /mnt/img/usr/share/icons/metaos -maxdepth 1 -name '*.png' 2>/dev/null | wc -l | tr -d ' '; }
has() { [ -e "$1" ] && echo yes || echo no; }

if [ "$DRY" = 0 ]; then
  echo
  echo "--- provision ---"
  sh /repo/os-build/face/provision.sh --root /mnt/img
  echo
  echo "--- shell prompt ---"
  sh /repo/os-build/tools/fix_terminal_prompt.sh /mnt/img
fi

echo
echo "--- what the image now has ---"
show "dock tiles (repo: $(grep -cE '^[[:space:]]*add_app ' /repo/os-build/face/meta-desktop.sh))" count_tiles
show "dock icons (repo: $(find /repo/os-build/iso/payload-theme/icons/metaos -maxdepth 1 -name '*.png' | wc -l | tr -d ' '))" count_icons
show "site aegis/index.html" has /mnt/img/opt/face-site/aegis/index.html
show "site bus.html" has /mnt/img/opt/face-site/bus.html
show "vendor/three.min.js" has /mnt/img/opt/face-site/vendor/three.min.js
show "face notesd.py" has /mnt/img/opt/face/notesd.py
show "bin meta-notes" has /mnt/img/usr/local/bin/meta-notes
show "session plank guard" sh -c "grep -q 'pgrep -x plank' /mnt/img/opt/face/session.sh && echo yes || echo no"
show "prompt says metaos" sh -c "grep -q \"metaos\" /mnt/img/etc/skel/.bashrc && echo yes || echo no"
show "os-release PRETTY_NAME" sh -c "sed -n 's/^PRETTY_NAME=//p' /mnt/img/etc/os-release"
CONTAINER

echo
echo "sync_image: done — nothing was booted. Boot proof is a separate step:"
echo "           sh os-build/tools/proof_boot.sh --timeout 180"

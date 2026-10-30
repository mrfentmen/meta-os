#!/bin/bash
# Meta OS full build, single-session (see STATUS.md for why):
#   mount tmpfs -> debootstrap bookworm -> build-image.sh -> .img in this dir
# Progress log: build.log in this directory (a plain file, readable live).
set -x
cd "$(dirname "$0")"
# NOTE: no `exec >> build.log` here - the caller redirects the whole
# script (`./build-all.sh >> build.log 2>&1`). An in-script exec redirect
# made the sandbox harness reap the session within ~1s (observed twice);
# per-command redirection from the caller runs to completion.
echo "=== build-all start $(date -u +%FT%TZ) ==="
rm -rf work/rootfs
mkdir -p work/rootfs
# tmpfs is LOAD-BEARING (learned 2026-10-26 run 5): the workspace disk
# is an overlay where tar cannot chown to foreign gids (base-files
# ./var/local gid 50 fails EPERM), so debootstrap on disk dies at
# extraction. On tmpfs the same debootstrap completed rc=0 (run 1).
mount -t tmpfs -o size=2200M tmpfs work/rootfs
debootstrap --variant=minbase \
  --include=systemd,systemd-sysv,udev,dbus,linux-image-amd64,initramfs-tools,python3,curl,ca-certificates,iproute2,git \
  bookworm work/rootfs http://deb.debian.org/debian
DBRC=$?
echo "debootstrap rc=$DBRC"
if [ "$DBRC" -ne 0 ]; then
  echo "BUILD_ALL_ABORT: debootstrap failed, not running build-image" 
  exit 1
fi
./build-image.sh
echo "build-image rc=$?"
ls -lh metaos-*.img* 2>/dev/null
echo "=== build-all end $(date -u +%FT%TZ) ==="

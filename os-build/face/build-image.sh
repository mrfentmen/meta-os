#!/bin/sh
# os-build/face/build-image.sh — reproducible carrier image build.
# Why not the debootstrap route: os/build-image.sh needs root + Linux;
# this Mac has neither, and the delivered image never arrived. So the
# recipe below starts from the official Debian 12 cloud image and
# customizes it with cloud-init + a guest-side provision script.
# One command in, one .img out, hash printed.
#
# Usage: sh os-build/face/build-image.sh [workdir]
# Output: $workdir/metaos-face.img + $workdir/metaos-face.img.sha256
set -eu
WORK="${1:-/tmp/face-img}"
# Toolchain pins (OC1B-278/280 — installed in-guest by the provision
# phase below; git and chromium already ride as apt packages):
OPENCODE_VERSION="${OPENCODE_VERSION:-2.2.0}"   # v2 installer --version pin
SSH_PORT="${SSH_PORT:-2223}"                    # provision/checks SSH port
FACE_KEY="$WORK/face-key"                       # build-local key, never git
REPO_FACE="$(cd "$(dirname "$0")" && pwd)"      # os-build/face in this tree
CLOUD_URL="https://cloud.debian.org/images/cloud/bookworm/latest/debian-12-generic-amd64.qcow2"
mkdir -p "$WORK"
cd "$WORK"

if [ ! -f debian-12-generic-amd64.qcow2 ]; then
  echo "build-image: downloading Debian 12 cloud image..."
  curl -sSL -o debian-12-generic-amd64.qcow2 "$CLOUD_URL"
fi

echo "build-image: writing NoCloud seed (hostname metaos, relay user, autologin tty1)..."
if [ ! -f "$FACE_KEY" ]; then
  echo "build-image: generating build-local ssh key..."
  ssh-keygen -t ed25519 -N "" -f "$FACE_KEY" -C "metaos-carrier-build" >/dev/null
fi
mkdir -p seed
PUBKEY="$(cat "$FACE_KEY.pub")"
cat > seed/user-data <<EOF
#cloud-config
hostname: metaos
manage_etc_hosts: true
timezone: America/New_York
locale: en_US.UTF-8
users:
  - name: relay
    sudo: ALL=(ALL) NOPASSWD:ALL
    shell: /bin/bash
    plain_text_passwd: metaos
    lock_passwd: false
    ssh_authorized_keys:
      - $PUBKEY
ssh_pwauth: true
runcmd:
  - [ systemctl, enable, --now, serial-getty@ttyS0.service ]
  - mkdir -p /etc/systemd/system/getty@tty1.service.d
  - printf '[Service]\nExecStart=\nExecStart=-/sbin/agetty --autologin relay --noclear %%I $TERM\n' > /etc/systemd/system/getty@tty1.service.d/autologin.conf
  - [ systemctl, daemon-reload ]
  - [ systemctl, restart, getty@tty1.service ]
EOF
printf 'instance-id: metaos-carrier-oc1b\nlocal-hostname: metaos\n' > seed/meta-data
rm -f seed.iso
hdiutil makehybrid -o seed.iso -iso -iso-volume-name cidata \
  -joliet -joliet-volume-name cidata seed/ >/dev/null
cp -f debian-12-generic-amd64.qcow2 metaos-face.img
qemu-img resize metaos-face.img +10G
sha256sum metaos-face.img 2>/dev/null || shasum -a 256 metaos-face.img | tee metaos-face.img.sha256

echo "build-image: provision boot (toolchain: opencode $OPENCODE_VERSION)..."
# -cpu max: the host is arm64 so the guest is TCG-emulated; QEMU's default
# qemu64 CPU lacks AVX2 and the Bun-compiled opencode binary dies with
# SIGILL (Illegal instruction) without it. x86-64-v3 is required.
qemu-system-x86_64 -cpu max -m 2048 -drive file="$WORK/metaos-face.img,format=qcow2" \
  -cdrom "$WORK/seed.iso" -serial "file:$WORK/provision-boot.txt" \
  -display none -net nic -net "user,hostfwd=tcp::${SSH_PORT}-:22" &
QPID=$!
echo "build-image: waiting for ssh on $SSH_PORT (cloud-init first boot)..."
ok=0
for i in $(seq 1 60); do
  if ssh -i "$FACE_KEY" -p "$SSH_PORT" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
      -o ConnectTimeout=5 relay@127.0.0.1 true 2>/dev/null; then ok=1; break; fi
  sleep 10
done
if [ "$ok" != 1 ]; then echo "build-image: SSH never came up"; kill $QPID; exit 1; fi
echo "build-image: running provision-toolchain.sh (OPENCODE_VERSION=$OPENCODE_VERSION)..."
scp -i "$FACE_KEY" -P "$SSH_PORT" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
  "$REPO_FACE/provision-toolchain.sh" relay@127.0.0.1:/tmp/provision-toolchain.sh
ssh -i "$FACE_KEY" -p "$SSH_PORT" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null relay@127.0.0.1 \
  "OPENCODE_VERSION=$OPENCODE_VERSION bash /tmp/provision-toolchain.sh" 2>&1 | tee "$WORK/provision.log"
echo "build-image: shutting down provision guest..."
ssh -i "$FACE_KEY" -p "$SSH_PORT" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null relay@127.0.0.1 "sudo poweroff" 2>/dev/null || true
wait $QPID 2>/dev/null || true
shasum -a 256 metaos-face.img | tee metaos-face.img.sha256
echo "build-image: done. Boot with:"
echo "  qemu-system-x86_64 -cpu max -m 2048 -drive file=$WORK/metaos-face.img,format=qcow2 -cdrom $WORK/seed.iso -serial file:boot.txt -display none -qmp unix:/tmp/face-qmp,server,nowait -net nic -net user,hostfwd=tcp::${SSH_PORT}-:22"

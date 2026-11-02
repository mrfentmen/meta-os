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
CLOUD_URL="https://cloud.debian.org/images/cloud/bookworm/latest/debian-12-generic-amd64.qcow2"
mkdir -p "$WORK"
cd "$WORK"

if [ ! -f debian-12-generic-amd64.qcow2 ]; then
  echo "build-image: downloading Debian 12 cloud image..."
  curl -sSL -o debian-12-generic-amd64.qcow2 "$CLOUD_URL"
fi

echo "build-image: writing NoCloud seed (hostname metaos, relay user, autologin tty1)..."
mkdir -p seed
cat > seed/user-data <<'EOF'
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
ssh_pwauth: true
runcmd:
  - [ systemctl, enable, --now, serial-getty@ttyS0.service ]
  - mkdir -p /etc/systemd/system/getty@tty1.service.d
  - printf '[Service]\nExecStart=\nExecStart=-/sbin/agetty --autologin relay --noclear %%I $TERM\n' > /etc/systemd/system/getty@tty1.service.d/autologin.conf
  - [ systemctl, daemon-reload ]
  - [ systemctl, restart, getty@tty1.service ]
EOF
printf 'instance-id: metaos-face-01\nlocal-hostname: metaos\n' > seed/meta-data
# NOTE: for SSH access, append your key under users[0].ssh_authorized_keys
# and bump instance-id before first boot of a fresh work copy.
rm -f seed.iso
hdiutil makehybrid -o seed.iso -iso -iso-volume-name cidata \
  -joliet -joliet-volume-name cidata seed/ >/dev/null
cp -f debian-12-generic-amd64.qcow2 metaos-face.img
qemu-img resize metaos-face.img +10G
sha256sum metaos-face.img 2>/dev/null || shasum -a 256 metaos-face.img | tee metaos-face.img.sha256
echo "build-image: done. Boot with:"
echo "  qemu-system-x86_64 -m 2048 -drive file=$WORK/metaos-face.img,format=qcow2 -cdrom $WORK/seed.iso -serial file:boot.txt -display none -qmp unix:/tmp/face-qmp,server,nowait -net nic -net user,hostfwd=tcp::2222-:22"

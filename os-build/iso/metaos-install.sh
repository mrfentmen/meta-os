#!/bin/sh
# metaos-install.sh — install a MetaOS live rootfs to a target disk.
# No Calamares, no network at install time: rsync the live tree, lay down
# a GPT (ESP + ext4 root), install the arm64-efi bootloader, set
# hostname/user, keep /etc/metaos.
#
# Runs as root on Linux (live ISO session, or a container pointed at an
# unpacked ISO tree). The target may be a block device (/dev/vda) or a
# plain image file (attached via losetup -P automatically).
#
#   metaos-install.sh --src <live-root-dir> --disk <dev-or-image>
#                     [--hostname NAME] [--user NAME]
#
# Every stage prints STEP:. Any failure exits non-zero. Demo credentials
# (ubuntu/ubuntu) are printed, never hidden.
set -eu
fail() { echo "INSTALL-FAIL: $*" >&2; exit 1; }
step() { echo "STEP: $*"; }

SRC=""; DISK=""; HOSTNAME="metaos"; USER="ubuntu"; KERNEL=""; INITRD=""
while [ $# -gt 0 ]; do
    case "$1" in
        --src) SRC=${2:-}; shift 2 ;;
        --disk) DISK=${2:-}; shift 2 ;;
        --hostname) HOSTNAME=${2:-}; shift 2 ;;
        --user) USER=${2:-}; shift 2 ;;
        --kernel) KERNEL=${2:-}; shift 2 ;;
        --initrd) INITRD=${2:-}; shift 2 ;;
        -h|--help) sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) fail "unknown argument: $1" ;;
    esac
done
[ -n "$SRC" ] || fail "--src <live-root-dir> required"
[ -n "$DISK" ] || fail "--disk <device-or-image> required"
# The live squashfs carries no kernel (it rides in /casper on the ISO),
# so the kernel+initrd that match the rootfs modules are explicit inputs.
[ -n "$KERNEL" ] || fail "--kernel <vmlinuz matching the rootfs modules> required"
[ -n "$INITRD" ] || fail "--initrd <initrd.img matching the rootfs modules> required"
[ -f "$KERNEL" ] || fail "--kernel not found: $KERNEL"
[ -f "$INITRD" ] || fail "--initrd not found: $INITRD"
[ -d "$SRC/etc" ] && [ -d "$SRC/usr" ] || fail "--src $SRC is not a root filesystem"
[ "$(id -u)" = "0" ] || fail "must run as root"

step "tools check"
for t in sfdisk mkfs.vfat mkfs.ext4 grub-install rsync qemu-nbd blkid chroot useradd chpasswd; do
    command -v "$t" >/dev/null 2>&1 || fail "missing tool: $t"
done
echo "tools-ok"

step "payload check (refuse to install a non-Meta tree)"
for f in usr/share/xsessions/metaos.desktop \
         opt/face/session.sh opt/face/kiosk.sh \
         usr/share/metaos/agent/server/queue/queue_service.py \
         etc/metaos/release; do
    [ -e "$SRC/$f" ] || fail "src is not a MetaOS tree, missing: $f"
done
echo "payload-ok (kernel+initrd supplied separately: $(basename "$KERNEL"), $(basename "$INITRD"))"

LOOP=""
cleanup() {
    umount "$MNT/boot/efi" 2>/dev/null || true
    umount "$MNT" 2>/dev/null || true
    [ -n "${LOOP:-}" ] && [ -n "${OUR_NBD:-}" ] && nbd_detach "$LOOP" || true
    [ -n "${LOOP:-}" ] && [ -z "${KEEPLOOP:-}" ] && [ -z "${OUR_NBD:-}" ] && losetup -d "$LOOP" 2>/dev/null || true
}
MNT=""
OUR_NBD=""

# qemu-nbd -c daemonizes and `qemu-nbd -d` does not reliably reap it, so a
# lingering daemon keeps the image write-locked and poisons the next run.
# Teardown matches the daemon by its device argument (qemu-nbd 8.2 has no
# --pidfile).
nbd_attach() { # $1 = /dev/nbdN, $2 = image file
    qemu-nbd -c "$1" "$2" || return 1
    # A stale partition node from an earlier run must never satisfy
    # part_wait for a fresh table: drop them right after attach.
    rm -f "$1"p* 2>/dev/null || true
    return 0
}

nbd_detach() { # $1 = /dev/nbdN
    qemu-nbd -d "$1" 2>/dev/null || true
    sleep 1
    # `qemu-nbd -c` daemonizes and -d does not reliably reap it; a
    # lingering daemon keeps the image write-locked and poisons the
    # next run. Kill any qemu-nbd still serving THIS device.
    for p in $(pidof qemu-nbd 2>/dev/null || true); do
        if tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null | grep -q " $1 "; then
            kill -9 "$p" 2>/dev/null || true
        fi
    done
}

nbd_free() { # echo a free /dev/nbdN or fail
    for i in 0 1 2 3 4 5 6 7; do
        if [ -b "/dev/nbd$i" ] && [ ! -b "/dev/nbd${i}p1" ]; then
            echo "/dev/nbd$i"; return 0
        fi
    done
    return 1
}

step "attach target $DISK"
if [ -b "$DISK" ]; then
    LOOP="$DISK"; KEEPLOOP=1
elif [ -f "$DISK" ]; then
    case "$DISK" in
        *.qcow2|*.qcow|*.img|*.raw)
            command -v qemu-nbd >/dev/null 2>&1 || fail "image file needs qemu-nbd (only block devices otherwise)"
            LOOP=$(nbd_free) || fail "no free /dev/nbdN for $DISK"
            nbd_attach "$LOOP" "$DISK" || fail "qemu-nbd attach failed on $LOOP"
            OUR_NBD=1
            echo "attached $DISK as $LOOP (installer-managed, detached on exit)"
            ;;
        *) fail "--disk file not understood (need .qcow2/.img/.raw or a block device): $DISK" ;;
    esac
else
    fail "--disk not found: $DISK"
fi

step "partition GPT (ESP 512MiB + root)"
sfdisk --wipe always "$LOOP" <<'PART' || fail "sfdisk failed"
label: gpt
,512M,C12A7328-F81F-11D2-BA4B-00A0C93EC93B,*
,,0FC63DAF-8483-4772-8E79-3D69D8477DE4
PART
if [ -n "${OUR_NBD:-}" ]; then
    # No udev here on purpose: container udevd receives the kernel add
    # events yet leaves "Device node missing, skipping handling"
    # (proven), and the daemon is racy across containers sharing /dev.
    # The kernel's own sysfs is synchronous after the re-read ioctl, so
    # partition major:minor is read from there -- never guessed.
    for PN in 1 2; do
        SYSDEV="/sys/block/$(basename "$LOOP")/$(basename "$LOOP")p$PN/dev"
        for i in $(seq 1 10); do
            [ -f "$SYSDEV" ] && break
            sleep 1
        done
        [ -f "$SYSDEV" ] || fail "kernel has no partition $PN on $LOOP ($SYSDEV missing)"
        MM=$(cat "$SYSDEV")
        MAJOR=${MM%%:*}; MINOR=${MM##*:}
        rm -f "$LOOP"p$PN 2>/dev/null || true
        mknod "$LOOP"p$PN b "$MAJOR" "$MINOR" || fail "mknod $LOOP p$PN failed"
    done
    echo "nodes: $LOOP p1 ($(stat -c '%t:%T' "$LOOP"p1)) p2 ($(stat -c '%t:%T' "$LOOP"p2))"
elif [ -z "${KEEPLOOP:-}" ]; then
    losetup -d "$LOOP"
    LOOP=$(losetup -P -f --show "$DISK") || fail "losetup -P failed on $DISK"
else
    # Block devices (vdX, pre-attached nbd): ask the kernel to rescan.
    partprobe "$LOOP" 2>/dev/null || partx -u "$LOOP" 2>/dev/null || true
fi
part_wait() { # $1 = partition suffix
    for i in $(seq 1 10); do
        if [ -b "$LOOP$1" ]; then return 0; fi
        sleep 1
    done
    echo "DEBUG: devices now:" >&2; ls "$LOOP"* 2>&1 >&2
    fail "partition $LOOP$1 never appeared"
}
part_wait p1; part_wait p2
ESP="$LOOP"p1; ROOT="$LOOP"p2

step "filesystems (vfat ESP, ext4 root)"
mkfs.vfat -F32 -n METAOS_ESP "$ESP" > /dev/null || fail "mkfs.vfat failed"
mkfs.ext4 -q -L metaos-root "$ROOT" || fail "mkfs.ext4 failed"

step "mount target"
MNT=$(mktemp -d)
trap 'umount "$MNT/boot/efi" 2>/dev/null; umount "$MNT" 2>/dev/null; [ -n "${LOOP:-}" ] && [ -n "${OUR_NBD:-}" ] && nbd_detach "$LOOP" 2>/dev/null; [ -n "${LOOP:-}" ] && [ -z "${KEEPLOOP:-}" ] && [ -z "${OUR_NBD:-}" ] && losetup -d "$LOOP" 2>/dev/null; true' EXIT INT TERM
mount "$ROOT" "$MNT" || fail "mount root failed"
mkdir -p "$MNT/boot/efi"
mount "$ESP" "$MNT/boot/efi" || fail "mount ESP failed"

step "rsync live rootfs -> target"
rsync -aHAX --delete \
    --exclude '/dev/*' --exclude '/proc/*' --exclude '/sys/*' \
    --exclude '/tmp/*' --exclude '/run/*' --exclude '/mnt/*' \
    --exclude '/media/*' --exclude '/lost+found' \
    --exclude '/boot/efi' \
    "$SRC/" "$MNT/" || fail "rsync failed"
mkdir -p "$MNT/dev" "$MNT/proc" "$MNT/sys" "$MNT/tmp" "$MNT/run" "$MNT/mnt" "$MNT/media"
chmod 1777 "$MNT/tmp"

step "fstab by UUID"
ROOT_UUID=$(blkid -s UUID -o value "$ROOT") || fail "no UUID for root"
ESP_UUID=$(blkid -s UUID -o value "$ESP") || fail "no UUID for ESP"
cat > "$MNT/etc/fstab" <<FSTAB
UUID=$ROOT_UUID / ext4 errors=remount-ro 0 1
UUID=$ESP_UUID /boot/efi vfat umask=0077 0 1
FSTAB
echo "fstab: root=$ROOT_UUID esp=$ESP_UUID"

step "hostname + user (demo credentials follow)"
printf '%s\n' "$HOSTNAME" > "$MNT/etc/hostname"
sed -i "s/127.0.1.1.*/127.0.1.1\t$HOSTNAME/" "$MNT/etc/hosts" 2>/dev/null || \
    printf '127.0.1.1\t%s\n' "$HOSTNAME" >> "$MNT/etc/hosts"
if ! chroot "$MNT" id "$USER" >/dev/null 2>&1; then
    chroot "$MNT" useradd -m -s /bin/bash -G sudo "$USER" || fail "useradd $USER failed"
fi
printf '%s:%s\n' "$USER" "$USER" | chroot "$MNT" chpasswd || fail "chpasswd failed"
echo "demo login: $USER / $USER (hostname $HOSTNAME)"

step "keep /etc/metaos + install record"
mkdir -p "$MNT/etc/metaos"
cat "$SRC/etc/metaos/release" > "$MNT/etc/metaos/release" 2>/dev/null || true
cat >> "$MNT/etc/metaos/install.log" <<LOG
installed=$(date -u +%Y-%m-%dT%H:%M:%SZ) method=metaos-install.sh host=$(uname -m)
LOG
echo "kept: /etc/metaos/release"

step "kernel+initrd into target /boot (live squashfs carries none)"
KV="vmlinuz-$(basename "$KERNEL" | sed 's/^vmlinuz-//')"
[ "$KV" = "vmlinuz-$(basename "$KERNEL")" ] && KV="vmlinuz"
KI="initrd.img-$(basename "$INITRD" | sed 's/^initrd\(.img\)\?-//')"
[ "$KI" = "initrd.img-$(basename "$INITRD")" ] && KI="initrd.img"
cp -f "$KERNEL" "$MNT/boot/$KV" || fail "copy kernel failed"
cp -f "$INITRD" "$MNT/boot/$KI" || fail "copy initrd failed"
[ -s "$MNT/boot/$KV" ] && [ -s "$MNT/boot/$KI" ] || fail "kernel/initrd copy empty"
echo "boot: $KV + $KI"

step "bootloader (grub arm64-efi, removable path, no NVRAM)"
grub-install --target=arm64-efi --efi-directory="$MNT/boot/efi" \
    --boot-directory="$MNT/boot" --removable --no-nvram || fail "grub-install failed"
[ -f "$MNT/boot/efi/EFI/BOOT/BOOTAA64.EFI" ] || fail "BOOTAA64.EFI missing after grub-install"
mkdir -p "$MNT/boot/grub"
cat > "$MNT/boot/grub/grub.cfg" <<GRUB
set timeout=5
set default=0
# The stock initrd is the ISO's LIVE initrd, whose conf.d defaults
# BOOT=casper (proven by unpacking: `if [ -z "$BOOT" ]; then export
# BOOT=casper`). Without an explicit boot= the installed system
# live-boots, finds no live medium, and stalls at casper's interactive
# netmount prompt. boot=local selects the standard local-root path
# with the same initrd bytes -- the documented initramfs-tools switch.
menuentry "MetaOS 1.0" {
    linux /boot/$KV root=UUID=$ROOT_UUID ro quiet splash boot=local console=ttyAMA0,115200 console=tty0
    initrd /boot/$KI
}
GRUB
# The EFI binary grub-install emits boots with prefix=($esp)/boot/grub
# (proven at the grub> prompt: prefix='(hd0,gpt1)/boot/grub'), so the
# config it loads first MUST live on the ESP. This early config searches
# the real root by UUID and chainloads the menu above; without it the
# machine drops to a grub shell.
mkdir -p "$MNT/boot/efi/boot/grub" "$MNT/boot/efi/EFI/BOOT"
cat > "$MNT/boot/efi/boot/grub/grub.cfg" <<GRUB
search.fs_uuid $ROOT_UUID root
set prefix=(\$root)/boot/grub
configfile (\$root)/boot/grub/grub.cfg
GRUB
cp -f "$MNT/boot/efi/boot/grub/grub.cfg" "$MNT/boot/efi/EFI/BOOT/grub.cfg"
[ -s "$MNT/boot/efi/boot/grub/grub.cfg" ] || fail "early grub.cfg empty"
[ -s "$MNT/boot/grub/grub.cfg" ] || fail "target grub.cfg empty"
echo "bootloader-ok: BOOTAA64.EFI + early chainloader + menu ($KV)"

step "unmount + detach"
umount "$MNT/boot/efi"
umount "$MNT"
trap - EXIT INT TERM
if [ -n "${OUR_NBD:-}" ]; then
    nbd_detach "$LOOP"
elif [ -z "${KEEPLOOP:-}" ]; then
    losetup -d "$LOOP"
fi
echo "INSTALL-DONE: $DISK carries MetaOS (hostname $HOSTNAME, user $USER)"
echo "boot it: qemu-system-aarch64 -M virt -cpu host -accel hvf -bios <EDK2> -drive file=$DISK,format=qcow2,if=virtio"

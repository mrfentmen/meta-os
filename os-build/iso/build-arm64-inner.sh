#!/bin/sh
# build-arm64-inner.sh — MetaOS arm64 ISO build. Runs INSIDE Docker
# (linux/arm64, as root). The Mac cannot run xorriso/mksquashfs/chroot,
# so this script is the whole build; build_iso.sh --rebuild is the
# one-line wrapper that launches it.
#
# Inputs (env):  BASE_ISO  read-only base ISO path in the container
#                WORK      scratch dir on a Linux volume (NOT a mac bind)
#                OUTDIR    export dir (mac bind mount, world-readable out)
#                REPO      repo checkout mounted read-only (/repo)
# Optional:      OUT_NAME  default metaos-1.0-arm64.iso
#
# Pipeline: mount base -> unsquash minimal (default source) -> chroot apt
# (calamares, user-setup, lightdm, xfce4) -> iso/provision.sh
# --no-initramfs -> face/provision.sh --root -> Meta extras (kiosk
# xsessions, lightdm autologin, /etc/metaos/release) -> live-layer
# transplant -> grub finalize + ttyAMA0 -> manifest regen -> repack
# single squashfs -> rewrite install-sources.yaml -> xorriso replay ->
# export. Any missing payload file is a hard FAIL (named step).
#
# Claim label until a green run: WRITTEN, UNRUN.
set -e
fail() { echo "GATE-FAIL: $*" >&2; exit 1; }
gate() { echo "gate: PASS ($*)"; }
step() { echo "STEP: $*"; }

BASE_ISO="${BASE_ISO:?set BASE_ISO}"
WORK="${WORK:?set WORK}"
OUTDIR="${OUTDIR:?set OUTDIR}"
REPO="${REPO:?set REPO}"
OUT_NAME="${OUT_NAME:-metaos-1.0-arm64.iso}"
LANE="$REPO/os-build/iso"
FACE="$REPO/os-build/face"
AGENT="$REPO/agent-layer"

[ "$(id -u)" = "0" ] || fail "must run as root in the container"
[ -f "$BASE_ISO" ] || fail "base ISO not found: $BASE_ISO"
# C6: every payload this build needs must exist before anything is extracted.
for d in "$LANE/provision.sh" "$LANE/finalize-iso-tree.sh" \
         "$LANE/plymouth/metaos" "$LANE/calamares" \
         "$LANE/payload-theme" "$LANE/payload-apps" \
         "$FACE/provision.sh" "$FACE/session.sh" "$FACE/kiosk.sh" \
         "$AGENT/stage.sh"; do
    [ -e "$d" ] || fail "required payload missing: $d (STEP payload-check)"
done
step "payload-check: all required payload dirs/files present"

export DEBIAN_FRONTEND=noninteractive
step "host-tools: install xorriso squashfs-tools rsync"
apt-get update -qq
apt-get install -y -qq xorriso squashfs-tools rsync python3 fdisk dosfstools e2fsprogs parted > /dev/null
echo "tools-ok"

[ "$(uname -m)" = "aarch64" ] || fail "this build is arm64-only (host is $(uname -m))"
echo "host: native $(uname -m), no qemu-user-static needed"

rm -rf "$WORK"; mkdir -p "$WORK/rootfs" "$WORK/iso" "$OUTDIR"
SRCMNT="$WORK/srcmnt"; mkdir -p "$SRCMNT"
step "mount base ISO read-only"
mount -o loop,ro "$BASE_ISO" "$SRCMNT"
trap 'umount "$WORK/rootfs/dev" "$WORK/rootfs/proc" "$WORK/rootfs/sys" 2>/dev/null || true; umount "$SRCMNT" 2>/dev/null || true' EXIT

step "detect base layout"
ls "$SRCMNT/casper/" | head -30
# Layer choice (C5 size gate): the base ISO's DEFAULT live source is the
# minimized variant (install-sources.yaml: ubuntu-desktop-minimal,
# default:true, path minimal.squashfs). Merging minimal alone keeps the
# installed tree under the 8 GB install target; stacking
# minimal.standard (+~1.5 GB of desktop apps) pushes it past what a blank
# 8 GB disk holds. Recorded decision, not an accident.
if [ -f "$SRCMNT/casper/filesystem.squashfs" ]; then
    LAYERS="$SRCMNT/casper/filesystem.squashfs"
elif [ -f "$SRCMNT/casper/install-sources.yaml" ]; then
    LAYERS="$SRCMNT/casper/minimal.squashfs"
    [ -f "$SRCMNT/casper/minimal.squashfs" ] || fail "layered base lacks minimal.squashfs"
else
    fail "unrecognised base layout (no filesystem.squashfs, no install-sources.yaml)"
fi
echo "layers: $LAYERS"

step "extract ISO tree"
xorriso -osirrox on -indev "$BASE_ISO" -extract / "$WORK/iso" 2>&1 | tail -1
COMP="$(unsquashfs -s $LAYERS 2>/dev/null | awk -F': *' '/^Compression/ {print $2; exit}')"
[ -n "$COMP" ] || COMP="$(unsquashfs -s ${LAYERS%% *} 2>/dev/null | awk -F': *' '/^Compression/ {print $2; exit}')"
echo "base squashfs compression: ${COMP:-unknown}"

cat > "$WORK/excludes.txt" <<'EOF'
var/lib/swcatalog/yaml/*
EOF
step "unsquash layers (whiteouts excluded)"
set -- $LAYERS
i=0
for sq in "$@"; do
    i=$((i + 1))
    unsquashfs -exclude-file "$WORK/excludes.txt" -d "$WORK/l$i" -f "$sq" > /dev/null
done
step "overlay layers in order"
mkdir -p "$WORK/rootfs"
i=0
for sq in "$@"; do
    i=$((i + 1))
    rsync -a "$WORK/l$i/" "$WORK/rootfs/"
    rm -rf "$WORK/l$i"
done
rm -rf "$WORK/rootfs/dev/"* "$WORK/rootfs/proc/"* "$WORK/rootfs/sys/"* "$WORK/rootfs/tmp/"* 2>/dev/null || true

step "GATE 1: rootfs sanity"
for d in bin etc usr; do
    [ -d "$WORK/rootfs/$d" ] || fail "rootfs missing /$d after layer overlay"
done
if [ ! -x "$WORK/rootfs/bin/sh" ] && [ ! -x "$WORK/rootfs/usr/bin/sh" ]; then
    fail "rootfs has no /bin/sh after layer overlay"
fi
gate "rootfs has bin/etc/usr + sh ($(find "$WORK/rootfs" | wc -l | tr -d ' ') entries)"

step "chroot setup (native arm64)"
cp /etc/resolv.conf "$WORK/rootfs/etc/resolv.conf"
mount --bind /dev "$WORK/rootfs/dev"; mount -t proc none "$WORK/rootfs/proc"; mount -t sysfs none "$WORK/rootfs/sys"
chroot "$WORK/rootfs" true || fail "chroot smoke test failed"

step "provision packages in chroot"
chroot "$WORK/rootfs" apt-get update -qq
MISSING=""
for p in calamares user-setup casper xfce4 xorg epiphany-browser wmctrl lightdm lightdm-gtk-greeter plymouth; do
    if chroot "$WORK/rootfs" dpkg-query -W -f='${Status}' "$p" 2>/dev/null | grep -q "install ok installed"; then
        echo "have: $p"
    else
        MISSING="$MISSING $p"
    fi
done
if [ -n "$MISSING" ]; then
    echo "installing:$MISSING"
    # Preseed lightdm as the default display manager (non-interactive).
    echo "lightdm shared/default-x-display-manager select lightdm" | chroot "$WORK/rootfs" debconf-set-selections
    chroot "$WORK/rootfs" apt-get install -y -qq $MISSING > /dev/null
fi
step "display manager: lightdm must own display-manager.service"
# systemctl enable does not dislodge gdm3's existing alias symlink in a
# chroot, so set the well-known display-manager.service alias by hand
# (this is what update-alternatives/lightdm postinst converge on).
chroot "$WORK/rootfs" systemctl enable lightdm > /dev/null 2>&1 || fail "systemctl enable lightdm failed"
ln -sf /lib/systemd/system/lightdm.service "$WORK/rootfs/etc/systemd/system/display-manager.service"
DM_LINK=$(chroot "$WORK/rootfs" readlink /etc/systemd/system/display-manager.service 2>/dev/null || true)
echo "display-manager.service -> ${DM_LINK:-(unset)}"
[ "${DM_LINK##*/}" = "lightdm.service" ] || fail "display manager is $DM_LINK, not lightdm"
step "GATE 2: provision packages installed"
for p in calamares user-setup casper lightdm plymouth xorg epiphany-browser wmctrl; do
    st=$(chroot "$WORK/rootfs" dpkg-query -W -f='${Status}' "$p" 2>/dev/null || true)
    ver=$(chroot "$WORK/rootfs" dpkg-query -W -f='${Version}' "$p" 2>/dev/null || true)
    [ "$st" = "install ok installed" ] || fail "package $p not installed (status: ${st:-missing})"
    echo "gate: $p $ver installed"
done
[ -x "$WORK/rootfs/usr/bin/startxfce4" ] || fail "xfce4 installed but no /usr/bin/startxfce4"
[ -x "$WORK/rootfs/usr/bin/epiphany" ] || fail "epiphany-browser installed but no /usr/bin/epiphany"
gate "provision packages installed (calamares+user-setup+casper+lightdm+plymouth+xfce4+xorg+epiphany)"

step "Meta payload (iso provision.sh, no initramfs rebuild)"
sh "$LANE/provision.sh" "$WORK/rootfs" --no-initramfs

step "face payload (/opt/face via lane A provisioner, read-only use)"
sh "$FACE/provision.sh" --root "$WORK/rootfs" || fail "face provision --root failed"

step "Meta extras: kiosk session, autologin, release stamp"
mkdir -p "$WORK/rootfs/usr/share/xsessions"
cat > "$WORK/rootfs/usr/share/xsessions/metaos.desktop" <<'DESKTOP'
[Desktop Entry]
Version=1.0
Name=Meta OS Desktop
Comment=Meta OS kiosk over XFCE
Exec=/opt/face/session.sh
TryExec=/opt/face/session.sh
Type=Application
DesktopNames=XFCE
DESKTOP
chmod 0644 "$WORK/rootfs/usr/share/xsessions/metaos.desktop"
mkdir -p "$WORK/rootfs/etc/lightdm/lightdm.conf.d"
cat > "$WORK/rootfs/etc/lightdm/lightdm.conf.d/50-metaos.conf" <<'LIGHTDM'
[Seat:*]
autologin-user=meta
autologin-user-timeout=0
user-session=metaos
greeter-session=lightdm-gtk-greeter
LIGHTDM
chmod 0644 "$WORK/rootfs/etc/lightdm/lightdm.conf.d/50-metaos.conf"
printf '/usr/sbin/lightdm\n' > "$WORK/rootfs/etc/X11/default-display-manager"
mkdir -p "$WORK/rootfs/etc/metaos"
cat > "$WORK/rootfs/etc/metaos/release" <<REL
METAOS_VERSION=1.0
METAOS_ARCH=arm64
METAOS_BASE=ubuntu-24.04.5-desktop-arm64.iso
METAOS_BASE_SHA256=$(sha256sum "$BASE_ISO" | awk '{print $1}')
METAOS_BUILT=$(date -u +%Y-%m-%dT%H:%M:%SZ)
REL
chmod 0644 "$WORK/rootfs/etc/metaos/release"

step "payload gate (theme, calamares, hook, autostart, kiosk, face, agent)"
for f in usr/share/plymouth/themes/metaos/metaos.plymouth \
         etc/plymouth/plymouthd.conf \
         etc/calamares/settings.conf \
         etc/calamares/branding/metaos/branding.desc \
         usr/local/lib/metaos/meta-branding.sh \
         etc/xdg/autostart/metaos-install.desktop \
         usr/share/metaos/installer.png \
         usr/share/xsessions/metaos.desktop \
         etc/lightdm/lightdm.conf.d/50-metaos.conf \
         opt/face/session.sh opt/face/kiosk.sh opt/face/shell.html \
         usr/share/metaos/agent/server/queue/queue_service.py \
         usr/lib/systemd/user/oc2-queue.service \
         etc/xdg/autostart/meta-agent-login.desktop \
         etc/metaos/release; do
    [ -e "$WORK/rootfs/$f" ] || fail "payload missing in rootfs: $f"
done
gate "Meta payload present in rootfs"

step "live-layer transplant (skel + casper.conf + KERNEL MODULES + firmware)"
LIVE="$SRCMNT/casper/minimal.standard.live.squashfs"
if [ -f "$LIVE" ]; then
    mkdir -p "$WORK/livefix" && unsquashfs -f -d "$WORK/livefix" "$LIVE" etc/skel etc/casper.conf lib/modules usr/lib/modules > /dev/null 2>&1 || true
    [ -d "$WORK/livefix/etc/skel" ] && cp -r "$WORK/livefix/etc/skel/." "$WORK/rootfs/etc/skel/" 2>/dev/null || true
    [ -f "$WORK/livefix/etc/casper.conf" ] && cp "$WORK/livefix/etc/casper.conf" "$WORK/rootfs/etc/casper.conf" 2>/dev/null || true
    echo "transplanted skel + casper.conf"
    # The kernel (modules) ships ONLY in the .live layer on this base
    # (minimal/standard carry none -- proven by unsquashfs -l).
    # Without this the live session runs on initrd modules alone and an
    # installed system cannot modprobe anything (vfat/nls -> ESP mount
    # fails -> emergency mode; proven 2026-11-03).
    # Firmware is deliberately NOT transplanted: 746 MB that the 8 GB
    # install target cannot hold (installed tree would land with ~0
    # bytes free and lightdm then dies writing .Xauthority -- proven).
    # Firmware stays an apt-install on real hardware.
    for moddir in lib/modules usr/lib/modules; do
        if [ -d "$WORK/livefix/$moddir" ]; then
            mkdir -p "$WORK/rootfs/$moddir"
            cp -r "$WORK/livefix/$moddir/." "$WORK/rootfs/$moddir/" 2>/dev/null || true
            echo "transplanted $moddir ($(du -sh "$WORK/rootfs/$moddir" 2>/dev/null | awk '{print $1}'))"
        fi
    done
    rm -rf "$WORK/livefix"
else
    echo "WARN: no .live layer in base; skel/casper.conf/modules transplant skipped"
fi
[ -n "$(ls "$WORK/rootfs/usr/lib/modules/" 2>/dev/null)" ] || fail "no kernel modules transplanted (usr/lib/modules empty)"
gate "kernel modules present in rootfs"

step "grub finalize (layerfs-path + serial console + branding)"
sh "$LANE/finalize-iso-tree.sh" "$WORK/iso"
python3 - "$WORK/iso/boot/grub/grub.cfg" <<'PYEOF'
import sys
p = sys.argv[1]
s = open(p).read()
if 'console=ttyAMA0' not in s:
    s = s.replace(' --- quiet splash', ' console=ttyAMA0,115200 --- quiet splash')
open(p, 'w').write(s)
print('grub: ttyAMA0=%d' % s.count('console=ttyAMA0'))
PYEOF
LAYERFS_N=$(grep -c 'layerfs-path=filesystem.squashfs' "$WORK/iso/boot/grub/grub.cfg" || true)
AMA_N=$(grep -c 'console=ttyAMA0' "$WORK/iso/boot/grub/grub.cfg" || true)
echo "grub: layerfs-path=${LAYERFS_N:-0} ttyAMA0=${AMA_N:-0}"
[ "${LAYERFS_N:-0}" -ge 1 ] || fail "grub.cfg has no layerfs-path=filesystem.squashfs"
[ "${AMA_N:-0}" -ge 1 ] || fail "grub.cfg has no console=ttyAMA0"
gate "grub carries layerfs-path + ttyAMA0 serial console"
grep -q 'MetaOS' "$WORK/iso/boot/grub/grub.cfg" || fail "grub.cfg lost MetaOS branding"
gate "grub carries MetaOS branding"

umount "$WORK/rootfs/dev" "$WORK/rootfs/proc" "$WORK/rootfs/sys" 2>/dev/null || true
rm -f "$WORK/rootfs/etc/resolv.conf"

step "apt cache clean (keeps the installed tree under the 8 GB target)"
chroot "$WORK/rootfs" apt-get clean || true
rm -rf "$WORK/rootfs/var/cache/apt/archives/"*.deb 2>/dev/null || true

step "manifest regen from the new rootfs"
mount --bind /dev "$WORK/rootfs/dev"
chroot "$WORK/rootfs" dpkg-query -W -f='${Package} ${Version}\n' > "$WORK/iso/casper/filesystem.manifest" 2>/dev/null
umount "$WORK/rootfs/dev" 2>/dev/null || true
[ -s "$WORK/iso/casper/filesystem.manifest" ] || fail "filesystem.manifest empty after regen"
grep -q '^calamares ' "$WORK/iso/casper/filesystem.manifest" || fail "regen manifest lacks calamares"
echo "manifest: $(wc -l < "$WORK/iso/casper/filesystem.manifest" | tr -d ' ') packages"

step "repack single squashfs (base compression: ${COMP:-xz})"
case "$COMP" in
    zstd) MKSQ="-comp zstd -Xcompression-level 15" ;;
    gzip) MKSQ="-comp gzip" ;;
    *)    MKSQ="-comp xz" ;;
esac
# shellcheck disable=SC2086
mksquashfs "$WORK/rootfs" "$WORK/iso/casper/filesystem.squashfs" -noappend -b 131072 -no-progress $MKSQ > /dev/null
rm -f "$WORK"/iso/casper/minimal*.squashfs
step "GATE 4: filesystem.squashfs exists and > 1 GB"
[ -f "$WORK/iso/casper/filesystem.squashfs" ] || fail "filesystem.squashfs missing after repack"
SQ_BYTES=$(stat -c %s "$WORK/iso/casper/filesystem.squashfs")
echo "filesystem.squashfs: $SQ_BYTES bytes"
[ "$SQ_BYTES" -gt 1073741824 ] || fail "filesystem.squashfs only $SQ_BYTES bytes (<= 1 GB)"
gate "filesystem.squashfs $(du -h "$WORK/iso/casper/filesystem.squashfs" | awk '{print $1}') > 1 GB"

step "rewrite install-sources.yaml (single source) + sizes"
du -sb "$WORK/rootfs" | awk '{print $1}' > "$WORK/iso/casper/filesystem.size"
SZ=$(cat "$WORK/iso/casper/filesystem.size")
cat > "$WORK/iso/casper/install-sources.yaml" <<YAML
- default: true
  description:
    en: A full featured MetaOS Desktop.
  id: metaos-desktop
  locale_support: langpack
  name:
    en: MetaOS Desktop
  path: filesystem.squashfs
  size: $SZ
  type: fsimage-layered
  variant: desktop
YAML
if [ -f "$WORK/iso/md5sum.txt" ]; then
    ( cd "$WORK/iso" && find . -type f ! -name md5sum.txt -print0 | xargs -0 md5sum > md5sum.txt )
fi

step "rebuild bootable ISO (El Torito replayed from the arm64 base)"
OUT_ISO="$WORK/$OUT_NAME"
xorriso -indev "$BASE_ISO" -outdev "$OUT_ISO" \
    -boot_image any replay \
    -overwrite on \
    -volid "METAOS_1_0" \
    -rm_r / -- -map "$WORK/iso" / \
    -commit 2>&1 | tail -3
[ -f "$OUT_ISO" ] || fail "xorriso produced no output at $OUT_ISO"
( cd "$(dirname "$OUT_ISO")" && sha256sum "$(basename "$OUT_ISO")" > "$(basename "$OUT_ISO").sha256" )
echo "iso: $OUT_ISO ($(du -h "$OUT_ISO" | awk '{print $1}')) sha256 $(awk '{print $1}' "$OUT_ISO.sha256")"

step "GATE 5: El Torito boot entry present (arm64: EFI)"
xorriso -indev "$OUT_ISO" -report_el_torito plain > "$WORK/el-torito.txt" 2>&1 || fail "xorriso could not read El Torito"
cat "$WORK/el-torito.txt"
BOOT_N=$(grep -ci 'boot img' "$WORK/el-torito.txt" || true)
[ -n "$BOOT_N" ] || BOOT_N=0
[ "$BOOT_N" -ge 1 ] || fail "no El Torito boot image in $OUT_ISO"
gate "El Torito boot entry present ($BOOT_N)"

step "export (world-readable for the mac bind mount)"
chmod -R u+rwX,a+rX "$WORK/iso"
cp "$OUT_ISO" "$OUTDIR/" && cp "$OUT_ISO.sha256" "$OUTDIR/"
chmod -R a+rX "$OUTDIR/$OUT_NAME" "$OUTDIR/$OUT_NAME.sha256"
ls -la "$OUTDIR/$OUT_NAME"
echo ALL-DONE

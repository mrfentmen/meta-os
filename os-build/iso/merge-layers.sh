#!/bin/sh
# MetaOS single-squashfs build (reproducible pipeline, OpenCode 1).
# Runs INSIDE Linux (Docker). Inputs: $ISO (base iso), $SRCDIR (mounted
# ISO tree, read-only ok), $WORK (scratch, Linux fs), $OUTDIR (export).
# Optional: $OUT_ISO (final ISO path; default $WORK/metaos-1.0-amd64.iso).
# The lane's os-build/iso dir (provision.sh, finalize-iso-tree.sh,
# plymouth/, calamares/) must be visible in the container next to this
# script -- see os-build/iso/PIPELINE.md "container layout".
# Usage: ISO=/iso/x.iso SRCDIR=/iso-mnt WORK=/root/isowork OUTDIR=/work ./merge-layers.sh
set -e
fail() { echo "GATE-FAIL: $*" >&2; exit 1; }
gate() { echo "gate: PASS ($*)"; }

ISO="${ISO:?base iso path}"; SRCDIR="${SRCDIR:?mounted iso tree}"; WORK="${WORK:?work dir}"; OUTDIR="${OUTDIR:?export dir}"
OUT_ISO="${OUT_ISO:-$WORK/metaos-1.0-amd64.iso}"
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

apt-get update -qq && apt-get install -y -qq xorriso squashfs-tools rsync initramfs-tools-core > /dev/null
echo "tools-ok"
rm -rf "$WORK"; mkdir -p "$WORK/rootfs" "$WORK/iso"
echo "=== extract ISO tree ==="
xorriso -osirrox on -indev "$ISO" -extract / "$WORK/iso" 2>&1 | tail -1
cat > "$WORK/excludes.txt" <<'EOF'
var/lib/swcatalog/yaml/*
EOF
echo "=== unsquash layers (whiteouts excluded) ==="
# The base ships 11 char-device whiteouts (0,0) under var/lib/swcatalog/yaml
# that cannot be created in this container; they are excluded, not fabricated.
# NB: unsquashfs -ef means extract-only; the flag for skipping paths is
# -exclude-file (a live-build gotcha, kept here so nobody "fixes" it back).
unsquashfs -exclude-file "$WORK/excludes.txt" -d "$WORK/minimal" -f "$SRCDIR/casper/minimal.squashfs" > /dev/null
unsquashfs -exclude-file "$WORK/excludes.txt" -d "$WORK/std" -f "$SRCDIR/casper/minimal.standard.squashfs" > /dev/null
echo "=== overlay minimal, then std ==="
# minimal/standard are base + delta (not alternatives): standard alone is a
# thin overlay, so merge = extract separately, rsync in layer order.
mkdir -p "$WORK/rootfs"
rsync -a "$WORK/minimal/" "$WORK/rootfs/"
rsync -a "$WORK/std/" "$WORK/rootfs/"
rm -rf "$WORK/minimal" "$WORK/std" "$WORK/rootfs/dev/"* "$WORK/rootfs/proc/"* "$WORK/rootfs/sys/"* "$WORK/rootfs/tmp/"* 2>/dev/null || true
echo "=== GATE 1: rootfs sanity (bin/etc/usr) ==="
for d in bin etc usr; do
  [ -d "$WORK/rootfs/$d" ] || fail "rootfs missing /$d after layer overlay"
done
if [ ! -x "$WORK/rootfs/bin/sh" ] && [ ! -x "$WORK/rootfs/usr/bin/sh" ]; then
  fail "rootfs has no /bin/sh after layer overlay"
fi
gate "rootfs has bin/etc/usr + sh ($(find "$WORK/rootfs" | wc -l | tr -d ' ') entries)"
echo "=== foreign-arch chroot setup (qemu-user-static on ARM hosts) ==="
# Live build ran on an ARM Mac (Docker Desktop): the rootfs is x86_64, so a
# plain chroot dies with "exec format error". Fix: install qemu-user-static
# on the HOST container and copy the static emulator into the chroot
# (binfmt for x86_64 is pre-registered by Docker Desktop). Removed again
# before repack so it never ships in the squashfs.
HOST_ARCH=$(uname -m)
QEMU_IN_ROOTFS=0
if [ "$HOST_ARCH" != "x86_64" ]; then
  apt-get install -y -qq qemu-user-static > /dev/null
  [ -f /usr/bin/qemu-x86_64-static ] || fail "qemu-user-static installed but no /usr/bin/qemu-x86_64-static"
  cp /usr/bin/qemu-x86_64-static "$WORK/rootfs/usr/bin/"
  QEMU_IN_ROOTFS=1
  echo "foreign-arch host ($HOST_ARCH): qemu-x86_64-static staged in chroot"
else
  echo "native x86_64 host: no emulator needed"
fi
cp /etc/resolv.conf "$WORK/rootfs/etc/resolv.conf"
mount --bind /dev "$WORK/rootfs/dev"; mount -t proc none "$WORK/rootfs/proc"; mount -t sysfs none "$WORK/rootfs/sys"
chroot "$WORK/rootfs" true || fail "chroot smoke test failed (foreign-arch? qemu-user-static missing?)"
echo "=== provision in chroot ==="
chroot "$WORK/rootfs" apt-get update -qq
DEBIAN_FRONTEND=noninteractive chroot "$WORK/rootfs" apt-get install -y -qq calamares plank fonts-inter user-setup casper > /dev/null
# casper: live-boot scripts for the single-squashfs layout (reinstalled so
# they match the merged tree, not the layered base). user-setup: provides
# user-setup-apply, without which casper-bottom/25adduser creates no live
# user and the greeter shows only "Other..." (live-build failure, fixed).
echo "=== GATE 2: provision packages installed (calamares+plank+fonts+user-setup+casper) ==="
for p in calamares plank fonts-inter user-setup casper; do
  st=$(chroot "$WORK/rootfs" dpkg-query -W -f='${Status}' "$p" 2>/dev/null || true)
  ver=$(chroot "$WORK/rootfs" dpkg-query -W -f='${Version}' "$p" 2>/dev/null || true)
  [ "$st" = "install ok installed" ] || fail "package $p not installed (status: ${st:-missing})"
  echo "gate: $p $ver installed"
done
gate "5/5 provision packages installed"
echo "=== Meta payload (provision.sh, no initramfs yet) ==="
# MERGE_NOTES claims the theme files are baked in; that only reproduces if
# provision.sh actually runs here. --no-initramfs because the initrd is
# rebuilt AFTER the .live transplants below (modules + conf must land first).
[ -f "$SCRIPT_DIR/provision.sh" ] || fail "provision.sh not beside merge-layers.sh (mount the lane's os-build/iso dir; see PIPELINE.md)"
[ -d "$SCRIPT_DIR/plymouth/metaos" ] || fail "plymouth/metaos payload missing beside merge-layers.sh"
[ -d "$SCRIPT_DIR/calamares" ] || fail "calamares/ payload missing beside merge-layers.sh"
sh "$SCRIPT_DIR/provision.sh" "$WORK/rootfs" --no-initramfs
echo "=== payload gate (theme, calamares, hook, autostart) ==="
for f in usr/share/plymouth/themes/metaos/metaos.plymouth etc/calamares/settings.conf usr/local/lib/metaos/meta-branding.sh etc/xdg/autostart/metaos-install.desktop; do
  [ -e "$WORK/rootfs/$f" ] || fail "payload missing in rootfs: $f (provision.sh did not land it?)"
done
gate "Meta payload present in rootfs"
echo "=== live-session files from .live layer ==="
# user-setup-apply, the live skel and casper.conf live ONLY in the excluded
# .live layer; without this transplant there is no live user (proven).
mkdir -p "$WORK/livefix" && unsquashfs -f -d "$WORK/livefix" "$SRCDIR/casper/minimal.standard.live.squashfs" etc/skel etc/casper.conf etc/initramfs-tools/conf.d usr/share/initramfs-tools/conf.d usr/share/initramfs-tools/hooks usr/share/initramfs-tools/scripts lib/modules usr/lib/modules > /dev/null 2>&1 || true
mkdir -p "$WORK/rootfs/etc/skel/.config/xfce4"
cp -r "$WORK/livefix/etc/skel/." "$WORK/rootfs/etc/skel/" 2>/dev/null || true
cp "$WORK/livefix/etc/casper.conf" "$WORK/rootfs/etc/casper.conf" 2>/dev/null || true
echo "=== initramfs-conf transplant (casper hooks + conf.d) ==="
# The stock initrd hardcodes LAYERFS_PATH=minimal.standard.live.squashfs via
# initramfs conf.d; the rebuild below must pick up the .live layer's casper
# hooks, not the stale base ones.
if [ -d "$WORK/livefix/etc/initramfs-tools/conf.d" ]; then
  mkdir -p "$WORK/rootfs/etc/initramfs-tools/conf.d"
  cp -r "$WORK/livefix/etc/initramfs-tools/conf.d/." "$WORK/rootfs/etc/initramfs-tools/conf.d/" 2>/dev/null || true
  echo "transplanted etc/initramfs-tools/conf.d"
else
  echo "WARN: no etc/initramfs-tools/conf.d in .live layer; base conf.d kept"
fi
for sub in hooks scripts; do
  if [ -d "$WORK/livefix/usr/share/initramfs-tools/$sub" ]; then
    mkdir -p "$WORK/rootfs/usr/share/initramfs-tools/$sub"
    cp -r "$WORK/livefix/usr/share/initramfs-tools/$sub/." "$WORK/rootfs/usr/share/initramfs-tools/$sub/" 2>/dev/null || true
    echo "transplanted usr/share/initramfs-tools/$sub"
  fi
done
[ -d "$WORK/livefix/usr/share/initramfs-tools/conf.d" ] && {
  mkdir -p "$WORK/rootfs/usr/share/initramfs-tools/conf.d"
  cp -r "$WORK/livefix/usr/share/initramfs-tools/conf.d/." "$WORK/rootfs/usr/share/initramfs-tools/conf.d/" 2>/dev/null || true
  echo "transplanted usr/share/initramfs-tools/conf.d"
} || true
echo "=== kernel-module transplant from .live layer ==="
# The initrd rebuild needs the ISO kernel's modules present; any module dir
# the .live layer carries that the merged rootfs lacks is copied over.
for moddir in lib/modules usr/lib/modules; do
  if [ -d "$WORK/livefix/$moddir" ]; then
    mkdir -p "$WORK/rootfs/$moddir"
    for kver in "$WORK/livefix/$moddir/"*/; do
      [ -d "$kver" ] || continue
      kv=$(basename "$kver")
      if [ ! -d "$WORK/rootfs/$moddir/$kv" ]; then
        cp -r "$kver" "$WORK/rootfs/$moddir/$kv"
        echo "transplanted modules: $moddir/$kv"
      fi
    done
  fi
done
echo "=== align LAYERFS_PATH default with the single squashfs ==="
# grub's layerfs-path= param (finalize step) overrides this at boot, but the
# rebuilt initrd's baked-in default must also point at filesystem.squashfs,
# not the dead layered name.
grep -rl 'minimal.standard.live.squashfs' "$WORK/rootfs/etc/casper.conf" "$WORK/rootfs/etc/initramfs-tools/conf.d/" 2>/dev/null | while IFS= read -r f; do
  sed -i 's/minimal\.standard\.live\.squashfs/filesystem.squashfs/g' "$f" && echo "patched LAYERFS_PATH in $f"
done
echo "=== rebuild initrd in chroot ==="
KVER=""
for moddir in lib/modules usr/lib/modules; do
  if [ -d "$WORK/rootfs/$moddir" ]; then
    cand=$(ls "$WORK/rootfs/$moddir" 2>/dev/null | sort -V | tail -1 || true)
    [ -n "$cand" ] && KVER="$cand"
  fi
done
[ -n "$KVER" ] || fail "no kernel version found under rootfs lib/modules (module transplant failed?)"
echo "target kernel: $KVER"
chroot "$WORK/rootfs" update-initramfs -u -k "$KVER"
[ -f "$WORK/iso/casper/initrd" ] || fail "no casper/initrd in base tree (found: $(ls "$WORK/iso/casper" | tr '\n' ' '))"
cp "$WORK/rootfs/boot/initrd.img-$KVER" "$WORK/iso/casper/initrd"
echo "initrd installed: $WORK/iso/casper/initrd ($(du -h "$WORK/iso/casper/initrd" | awk '{print $1}'))"
echo "=== GATE 3: casper file count in the new initrd (>= 40 or FAIL) ==="
CASPER_N=$(lsinitramfs "$WORK/iso/casper/initrd" 2>/dev/null | grep -c casper || true)
[ -n "$CASPER_N" ] || CASPER_N=0
echo "casper files in initrd: $CASPER_N"
[ "$CASPER_N" -ge 40 ] || fail "new initrd carries only $CASPER_N casper files (< 40): live boot would drop to initramfs"
gate "initrd casper file count $CASPER_N >= 40"
echo "=== grub finalize (layerfs-path + serial console + branding) ==="
if [ -f "$SCRIPT_DIR/finalize-iso-tree.sh" ]; then
  sh "$SCRIPT_DIR/finalize-iso-tree.sh" "$WORK/iso"
else
  echo "WARN: finalize-iso-tree.sh not beside merge-layers.sh; inline fallback (see PIPELINE.md)"
  python3 - "$WORK/iso/boot/grub/grub.cfg" <<'PYEOF'
import sys
p = sys.argv[1]
s = open(p).read()
s = s.replace('/casper/vmlinuz ', '/casper/vmlinuz layerfs-path=filesystem.squashfs ')
s = s.replace('/casper/vmlinuz nomodeset ', '/casper/vmlinuz layerfs-path=filesystem.squashfs nomodeset ')
s = s.replace(' --- quiet splash', ' console=ttyS0 --- quiet splash')
open(p, 'w').write(s)
print('grub: layerfs=%d console=%d' % (s.count('layerfs-path='), s.count('console=ttyS0')))
PYEOF
fi
LAYERFS_N=$(grep -c 'layerfs-path=filesystem.squashfs' "$WORK/iso/boot/grub/grub.cfg" || true)
CONSOLE_N=$(grep -c 'console=ttyS0' "$WORK/iso/boot/grub/grub.cfg" || true)
echo "grub: layerfs-path=${LAYERFS_N:-0} console=${CONSOLE_N:-0}"
[ "${LAYERFS_N:-0}" -ge 1 ] || fail "grub.cfg has no layerfs-path=filesystem.squashfs (boot would hit 'File system layers are missing')"
[ "${CONSOLE_N:-0}" -ge 1 ] || fail "grub.cfg has no console=ttyS0 (no serial log for headless proof)"
gate "grub carries layerfs-path + serial console"
umount "$WORK/rootfs/dev" "$WORK/rootfs/proc" "$WORK/rootfs/sys" 2>/dev/null || true
rm -f "$WORK/rootfs/etc/resolv.conf"
if [ "$QEMU_IN_ROOTFS" = "1" ]; then
  rm -f "$WORK/rootfs/usr/bin/qemu-x86_64-static"
  echo "qemu static binary removed from rootfs (must not ship)"
fi
rm -rf "$WORK/livefix"
echo "=== manifest regen from the new rootfs ==="
mount --bind /dev "$WORK/rootfs/dev"
chroot "$WORK/rootfs" dpkg-query -W -f='${Package} ${Version}\n' > "$WORK/iso/casper/filesystem.manifest" 2>/dev/null
umount "$WORK/rootfs/dev" 2>/dev/null || true
[ -s "$WORK/iso/casper/filesystem.manifest" ] || fail "filesystem.manifest empty after regen"
grep -q '^calamares ' "$WORK/iso/casper/filesystem.manifest" || fail "regen manifest lacks calamares (provisioned rootfs?)"
echo "manifest: $(wc -l < "$WORK/iso/casper/filesystem.manifest" | tr -d ' ') packages"
echo "=== repack single squashfs ==="
mksquashfs "$WORK/rootfs" "$WORK/iso/casper/filesystem.squashfs" -noappend -b 131072 -comp xz -no-progress > /dev/null
rm -f "$WORK/iso/casper/minimal.squashfs" "$WORK/iso/casper/minimal.standard.squashfs" "$WORK/iso/casper/minimal.standard.live.squashfs"
echo "=== GATE 4: filesystem.squashfs exists and > 1 GB ==="
[ -f "$WORK/iso/casper/filesystem.squashfs" ] || fail "filesystem.squashfs missing after repack"
SQ_BYTES=$(stat -c %s "$WORK/iso/casper/filesystem.squashfs")
echo "filesystem.squashfs: $SQ_BYTES bytes"
[ "$SQ_BYTES" -gt 1073741824 ] || fail "filesystem.squashfs only $SQ_BYTES bytes (<= 1 GB): repack is truncated"
gate "filesystem.squashfs $(du -h "$WORK/iso/casper/filesystem.squashfs" | awk '{print $1}') > 1 GB"
echo "=== rewrite install-sources.yaml (single source) ==="
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
  echo "=== refresh md5sum.txt ==="
  ( cd "$WORK/iso" && find . -type f ! -name md5sum.txt -print0 | xargs -0 md5sum > md5sum.txt )
fi
echo "=== rebuild bootable ISO (El Torito replayed from base) ==="
# Same recipe as build_iso.sh: -boot_image any replay clones the base ISO's
# El Torito (BIOS eltorito + appended EFI partition) and hybrid MBR+GPT
# instead of hand-writing per-release isohybrid args.
xorriso -indev "$ISO" -outdev "$OUT_ISO" \
  -boot_image any replay \
  -overwrite on \
  -rm_r / -- -map "$WORK/iso" / \
  -commit 2>&1 | tail -3
[ -f "$OUT_ISO" ] || fail "xorriso produced no ISO at $OUT_ISO"
( cd "$(dirname "$OUT_ISO")" && sha256sum "$(basename "$OUT_ISO")" > "$(basename "$OUT_ISO").sha256" )
echo "iso: $OUT_ISO ($(du -h "$OUT_ISO" | awk '{print $1}')) sha256 $(awk '{print $1}' "$OUT_ISO.sha256")"
echo "=== GATE 5: El Torito has exactly the BIOS + UEFI entries ==="
xorriso -indev "$OUT_ISO" -report_el_torito as plain > "$WORK/el-torito.txt" 2>&1 || fail "xorriso could not read El Torito from $OUT_ISO"
cat "$WORK/el-torito.txt"
BOOT_N=$(grep -ci 'boot image' "$WORK/el-torito.txt" || true)
[ -n "$BOOT_N" ] || BOOT_N=0
[ "$BOOT_N" -eq 2 ] || fail "expected exactly 2 El Torito boot images (BIOS + UEFI), found $BOOT_N; see $WORK/el-torito.txt"
gate "El Torito BIOS + UEFI entries present (2/2)"
echo "=== export (permissions fixed for macOS bind mounts) ==="
# OUTDIR is usually a Docker Desktop bind mount from macOS: root-owned files
# with bare modes can come out unreadable on the Mac side, so the tree and
# ISO are made world-readable before the copy, which the live build had to
# redo by hand after a confusing "permission denied" on export.
chmod -R u+rwX,a+rX "$WORK/iso"
rm -rf "$OUTDIR/isowork" && cp -r "$WORK/iso" "$OUTDIR/isowork"
cp "$OUT_ISO" "$OUTDIR/" && cp "$OUT_ISO.sha256" "$OUTDIR/"
chmod -R a+rX "$OUTDIR/isowork" "$OUTDIR/$(basename "$OUT_ISO")" "$OUTDIR/$(basename "$OUT_ISO").sha256"
ls -la "$OUTDIR/isowork/casper/filesystem.squashfs" "$OUTDIR/$(basename "$OUT_ISO")"
echo ALL-DONE

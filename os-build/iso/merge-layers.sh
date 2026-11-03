#!/bin/sh
# MetaOS single-squashfs build (reproducible pipeline, OpenCode 1).
# Runs INSIDE Linux (Docker). Inputs: $ISO (base iso), $SRCDIR (mounted
# ISO tree, read-only ok), $WORK (scratch, Linux fs), $OUTDIR (export).
# Usage: ISO=/iso/x.iso SRCDIR=/iso-mnt WORK=/root/isowork OUTDIR=/work ./merge-layers.sh
set -e
ISO="${ISO:?base iso path}"; SRCDIR="${SRCDIR:?mounted iso tree}"; WORK="${WORK:?work dir}"; OUTDIR="${OUTDIR:?export dir}"
apt-get update -qq && apt-get install -y -qq xorriso squashfs-tools rsync > /dev/null
echo "tools-ok"
rm -rf "$WORK"; mkdir -p "$WORK/rootfs" "$WORK/iso"
echo "=== extract ISO tree ==="
xorriso -osirrox on -indev "$ISO" -extract / "$WORK/iso" 2>&1 | tail -1
cat > "$WORK/excludes.txt" <<'EOF'
var/lib/swcatalog/yaml/*
EOF
echo "=== unsquash layers (whiteouts excluded) ==="
unsquashfs -exclude-file "$WORK/excludes.txt" -d "$WORK/minimal" -f "$SRCDIR/casper/minimal.squashfs" > /dev/null
unsquashfs -exclude-file "$WORK/excludes.txt" -d "$WORK/std" -f "$SRCDIR/casper/minimal.standard.squashfs" > /dev/null
echo "=== overlay minimal, then std ==="
mkdir -p "$WORK/rootfs"
rsync -a "$WORK/minimal/" "$WORK/rootfs/"
rsync -a "$WORK/std/" "$WORK/rootfs/"
rm -rf "$WORK/minimal" "$WORK/std" "$WORK/rootfs/dev/"* "$WORK/rootfs/proc/"* "$WORK/rootfs/sys/"* "$WORK/rootfs/tmp/"* 2>/dev/null || true
echo "=== provision in chroot (needs qemu-user-static on foreign arch) ==="
cp /etc/resolv.conf "$WORK/rootfs/etc/resolv.conf"
mount --bind /dev "$WORK/rootfs/dev"; mount -t proc none "$WORK/rootfs/proc"; mount -t sysfs none "$WORK/rootfs/sys"
chroot "$WORK/rootfs" apt-get update -qq
chroot "$WORK/rootfs" apt-get install -y -qq calamares plank fonts-inter user-setup > /dev/null
echo "=== live-session files from .live layer ==="
mkdir -p "$WORK/livefix" && unsquashfs -f -d "$WORK/livefix" "$SRCDIR/casper/minimal.standard.live.squashfs" etc/skel etc/casper.conf > /dev/null 2>&1 || true
mkdir -p "$WORK/rootfs/etc/skel/.config/xfce4"
cp -r "$WORK/livefix/etc/skel/." "$WORK/rootfs/etc/skel/" 2>/dev/null || true
cp "$WORK/livefix/etc/casper.conf" "$WORK/rootfs/etc/casper.conf" 2>/dev/null || true
echo "=== grub fixes (layerfs-path + serial console) ==="
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
umount "$WORK/rootfs/dev" "$WORK/rootfs/proc" "$WORK/rootfs/sys" 2>/dev/null || true
rm -f "$WORK/rootfs/etc/resolv.conf"
echo "=== repack single squashfs ==="
mksquashfs "$WORK/rootfs" "$WORK/iso/casper/filesystem.squashfs" -noappend -b 131072 -comp xz -no-progress > /dev/null
rm -f "$WORK/iso/casper/minimal.squashfs" "$WORK/iso/casper/minimal.standard.squashfs" "$WORK/iso/casper/minimal.standard.live.squashfs"
du -sb "$WORK/rootfs" | awk '{print $1}' > "$WORK/iso/casper/filesystem.size"
mount --bind /dev "$WORK/rootfs/dev"
chroot "$WORK/rootfs" dpkg-query -W -f='${Package} ${Version}\n' > "$WORK/iso/casper/filesystem.manifest" 2>/dev/null
umount "$WORK/rootfs/dev" 2>/dev/null || true
echo "=== rewrite install-sources.yaml (single source) ==="
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
echo "=== export ==="
rm -rf "$OUTDIR/isowork" && cp -r "$WORK/iso" "$OUTDIR/isowork"
ls -la "$OUTDIR/isowork/casper/filesystem.squashfs"
echo ALL-DONE

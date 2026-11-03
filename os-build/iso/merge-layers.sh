#!/bin/sh
set -e
apt-get update -qq && apt-get install -y -qq xorriso squashfs-tools rsync > /dev/null 2>&1
echo "tools-ok"
WORK=/root/isowork
rm -rf $WORK; mkdir -p $WORK/minimal $WORK/std $WORK/iso $WORK/minimal $WORK/std
echo "=== extract ISO tree ==="
xorriso -osirrox on -indev /iso/xubuntu-base.iso -extract / $WORK/iso 2>&1 | tail -1
echo "=== unsquash layers separately ==="
unsquashfs -exclude-file /excludes.txt -d $WORK/minimal -f /iso-mnt/casper/minimal.squashfs > /dev/null
unsquashfs -exclude-file /excludes.txt -d $WORK/std -f /iso-mnt/casper/minimal.standard.squashfs > /dev/null
echo "=== overlay minimal, then std (rsync into rootfs) ==="
mkdir -p $WORK/rootfs
rsync -a $WORK/minimal/ $WORK/rootfs/
rsync -a $WORK/std/ $WORK/rootfs/
rm -rf $WORK/minimal $WORK/std
rm -rf $WORK/rootfs/dev/* $WORK/rootfs/proc/* $WORK/rootfs/sys/* $WORK/rootfs/tmp/* 2>/dev/null || true
echo "rootfs top: $(ls $WORK/rootfs | tr '\n' ' ')"
echo "=== provision in chroot ==="
cp /etc/resolv.conf $WORK/rootfs/etc/resolv.conf
mount --bind /dev $WORK/rootfs/dev
mount -t proc none $WORK/rootfs/proc
mount -t sysfs none $WORK/rootfs/sys
chroot $WORK/rootfs apt-get update -qq
chroot $WORK/rootfs apt-get install -y -qq calamares calamares-settings-ubuntu plank fonts-inter > /dev/null 2>&1
umount $WORK/rootfs/dev $WORK/rootfs/proc $WORK/rootfs/sys 2>/dev/null || true
echo "provision done"
echo "=== repack single squashfs ==="
mksquashfs $WORK/rootfs $WORK/iso/casper/filesystem.squashfs -noappend -b 131072 -comp xz -no-progress
rm -f $WORK/iso/casper/minimal.squashfs $WORK/iso/casper/minimal.standard.squashfs $WORK/iso/casper/minimal.standard.live.squashfs
echo "=== export artifacts to bind mount ==="
rm -rf /work/isowork && cp -r $WORK/iso /work/isowork
ls -la /work/isowork/casper/ | grep -E "squashfs|yaml"
echo ALL-DONE

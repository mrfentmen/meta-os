#!/bin/bash
# Meta OS image build (route (a): debootstrap rootfs -> raw UEFI .img).
# Ported into the repo os/ tree by OS-006 (2026-10-27) from the proven
# image lane; the only adaptations from the lane script are the layout
# mapping below and the payload source. Layout in this repo:
#   services/  <- lane src/units (systemd units + relay.target)
#   firstboot/ <- lane src/bin/metaos-firstboot (firstboot program)
#   bin/       <- lane src/bin/metaos-boot-checklist, metaos-update
#   grub-early.cfg, README-FIRSTBOOT.md <- lane src/ files of same name
# The script dir is os/, so work/ and the output image live under os/
# (both gitignored: build outputs never commit).
# Implements META_OS.md OS-005/OS-007 (adapted: Packer is replaced by this
# scripted assembly in the sandbox), OS-011 (stack baked at a pinned
# commit: the script refuses a dirty checkout, records the checkout
# HEAD as PINNED_COMMIT, and stamps it into the image), OS-012 (zero
# credentials), OS-016 (relay.target), OS-022 (rescue entry),
# OS-059 (gateway bake: daemon plus catalog beside /opt/relay,
# unit enabled under relay.target).
#
# Usage: ./build-image.sh            (expects work/rootfs from debootstrap)
# Output: metaos-<date>.img + .sha256 in this directory.
set -euxo pipefail
git config --global --add safe.directory '*' 2>/dev/null || true
cd "$(dirname "$0")"
ROOTFS=work/rootfs
# Payload is this repo itself: the script lives in os/, the repo root is
# its parent. The lane script hardcoded a home-dir checkout path; this
# keeps the bake working from any checkout of this repo.
PAYLOAD_SRC="$(cd "$(dirname "$0")/.." && pwd)"
DATE=$(date +%F)
IMG="metaos-$DATE.img"
# OS-011: the bake records exactly one source commit. A dirty checkout
# refuses outright (same guard as os/build-packer.sh and
# os/build-live.sh), so a produced image always matches a commit, and
# PINNED_COMMIT is the checkout HEAD at build time, not a hash typed
# into this script. The stamp lands in the image in two places below:
# /opt/relay/.metaos-source-commit and the /etc/metaos-version lines.
[ -z "$(git -C "$PAYLOAD_SRC" status --porcelain)" ] || {
  echo "refusing: checkout is dirty - commit or stash first" >&2
  exit 1
}
PINNED_COMMIT="$(git -C "$PAYLOAD_SRC" rev-parse HEAD)"
[ -n "$PINNED_COMMIT" ] || { echo "refusing: no pinned commit resolved" >&2; exit 1; }
ROOT_UUID="3d9a5c41-7b2e-4c1a-9e55-2f6a1b8d0e77"
ESP_MIB=64
TOTAL_MIB=3072

[ -d "$ROOTFS/etc" ] || { echo "rootfs missing - run debootstrap first" >&2; exit 1; }

# ---------- 1. In-chroot system configuration ----------
mountpoint -q "$ROOTFS/proc" || mount -t proc proc "$ROOTFS/proc" || true
mountpoint -q "$ROOTFS/sys"  || mount -t sysfs sys "$ROOTFS/sys" || true
cleanup() { umount "$ROOTFS/proc" "$ROOTFS/sys" 2>/dev/null || true; }
trap cleanup EXIT

echo "metaos" > "$ROOTFS/etc/hostname"
cat > "$ROOTFS/etc/fstab" <<EOF
UUID=$ROOT_UUID  /          ext4  defaults        0 1
LABEL=METAESP    /boot/efi  vfat  defaults        0 2
EOF
echo "metaos-$DATE (debian 12 bookworm, stock kernel)" > "$ROOTFS/etc/metaos-version"
echo "source-commit $PINNED_COMMIT" >> "$ROOTFS/etc/metaos-version"
printf 'LANG=C.UTF-8\n' > "$ROOTFS/etc/default/locale"

# policy-rc.d: never start services inside the chroot
printf '#!/bin/sh\nexit 101\n' > "$ROOTFS/usr/sbin/policy-rc.d"
chmod +x "$ROOTFS/usr/sbin/policy-rc.d"

chroot "$ROOTFS" /bin/bash -e <<'CHROOT'
export DEBIAN_FRONTEND=noninteractive
# relay user (appliance account; password locked, getty autologin below)
id relay >/dev/null 2>&1 || useradd -m -s /bin/bash relay
usermod -p '!' relay || true
# kernel + initramfs were installed by debootstrap --include; make sure the
# initramfs exists for the installed kernel
update-initramfs -u -k all || true
systemctl enable serial-getty@ttyS0.service || true
CHROOT
rm -f "$ROOTFS/usr/sbin/policy-rc.d"

# ---------- 2. Payload -> /opt/relay ----------
mkdir -p "$ROOTFS/opt/relay"
rsync -a --delete \
  --exclude='.git' --exclude='__pycache__' --exclude='tests' \
  --exclude='plan' --exclude='*.pyc' \
  "$PAYLOAD_SRC"/ "$ROOTFS/opt/relay"/
# Belt and braces: never let a payload .git leak into the image tree;
# run 1's log shows a "dubious ownership" fatal from git in this section.
rm -rf "$ROOTFS/opt/relay/.git"
# OS-011: the pinned-commit record lives beside the payload, not in
# the local git checkout below (that checkout is an empty commit made
# only so metaos-update sees a git tree; it carries no source history).
echo "$PINNED_COMMIT" > "$ROOTFS/opt/relay/.metaos-source-commit"
mkdir -p "$ROOTFS/opt/relay/metaos-src"
cp -a services firstboot bin "$ROOTFS/opt/relay/metaos-src/" 2>/dev/null || true

# ---------- 2b. OS-059: gateway bake ----------
# The gateway program lives outside this repo (Dale's
# ~/workspace/mcp-gateway checkout), so it is the one build
# input that is not the repo checkout itself. The bake copies
# ONLY the daemon and its catalog: gateway.py plus
# backends.json. It never copies the working estate around
# them: no .venv, no servers/ runtimes, no debug/ logs, no
# *.db, no *.out, no *.bak. A missing source file refuses
# the build instead of baking a gateway that cannot start.
# The stamp records the bake date, the source dir, and the
# sha256 of both baked files, so a rebuild from changed
# sources stamps differently: that hash record IS the pin,
# because the source is not a git checkout and has no commit
# to pin. The stamp lands beside the baked files, where the
# OS-012 sweep allowlist expects it. This block runs before
# the chown below, so the baked dir ends up relay-owned
# with the rest of /opt/relay.
GATEWAY_SRC="${METAOS_GATEWAY_SRC:-$(cd "$(dirname "$0")/../.." && pwd)/mcp-gateway}"
[ -f "$GATEWAY_SRC/gateway.py" ] || { echo "refusing: no gateway.py in $GATEWAY_SRC" >&2; exit 1; }
[ -f "$GATEWAY_SRC/backends.json" ] || { echo "refusing: no backends.json in $GATEWAY_SRC" >&2; exit 1; }
mkdir -p "$ROOTFS/opt/relay/mcp-gateway"
install -m 644 "$GATEWAY_SRC/gateway.py" "$GATEWAY_SRC/backends.json" "$ROOTFS/opt/relay/mcp-gateway/"
{
  echo "gateway-bake $DATE"
  echo "source $GATEWAY_SRC"
  (cd "$ROOTFS/opt/relay/mcp-gateway" && sha256sum gateway.py backends.json)
} > "$ROOTFS/opt/relay/mcp-gateway/.metaos-gateway-bake"

# ---------- 2c. OS-083: artifact store root ----------
# The store itself is not a daemon: it is a directory that
# mos/artifact_store.py turns into a git repo on first deposit.
# The bake creates the directory empty plus a marker file, and
# nothing else: no artifact is baked, so no work product and no
# credential-adjacent file can ride into the image here. The
# chown runs now (not with the /opt/relay chown below) so the
# relay user owns the store root from first boot. Git init is
# deliberately NOT baked: a baked .git would carry build-machine
# state, and the module inits the repo on first deposit.
mkdir -p "$ROOTFS/var/lib/metaos/artifacts"
{
  echo "artifact-store-root /var/lib/metaos/artifacts"
  echo "git-init on first deposit by mos/artifact_store.py"
} > "$ROOTFS/var/lib/metaos/artifacts/.metaos-artifact-store"
chroot "$ROOTFS" chown relay:relay /var/lib/metaos/artifacts

# ---------- 2d. OS-078: memory store root ----------
# Same empty-plus-marker shape as the artifact store (2c): the
# memory service is a filesystem store, not a daemon, so the
# bake creates the root empty plus a marker and nothing else.
# No memory entry is baked, so no settled decision and no
# credential-adjacent text can ride into the image here. The
# relay-memory.service unit creates the agents/ and shared/
# namespaces at boot (mos/memory.py ensure), so the bake does
# not pre-create them: the marker records the root only. The
# chown runs now so the relay user owns the root from first
# boot and the unit can ensure the namespaces as relay.
mkdir -p "$ROOTFS/var/lib/metaos/memory"
{
  echo "memory-store-root /var/lib/metaos/memory"
  echo "namespaces ensured at boot by relay-memory.service"
} > "$ROOTFS/var/lib/metaos/memory/.metaos-memory-store"
chroot "$ROOTFS" chown relay:relay /var/lib/metaos/memory

# ---------- 2e. OS-065: skills collection root ----------
# Same empty-plus-marker shape as the stores (2c/2d): the skills
# loader mounts collections at process launch, so the bake
# creates the conventional collection root empty plus a marker
# and nothing else. No skill content is baked: a baked skill
# would freeze one agent's craft into every image, and the
# collection is populated later by an install step (the Phase B
# meta-pkg flow, OS-069/070), not by the image build. The chown
# runs now so the relay user owns the root from first boot.
mkdir -p "$ROOTFS/var/lib/metaos/skills"
{
  echo "skills-collection-root /var/lib/metaos/skills"
  echo "populated by a later install step, never baked with skill content"
} > "$ROOTFS/var/lib/metaos/skills/.metaos-skills-root"
chroot "$ROOTFS" chown relay:relay /var/lib/metaos/skills

# metaos-update expects /opt/relay to be a git checkout; init a local one
# whose origin records the source repo (no credentials involved).
# ORDER MATTERS: git init/commit run BEFORE the chown to relay below.
# After chown the tree is owned by uid relay and root-run git refuses it
# ("dubious ownership", run 1 build.log line 757) even for an empty commit.
if [ ! -d "$ROOTFS/opt/relay/.git" ]; then
  git -c safe.directory='*' -C "$ROOTFS/opt/relay" init -q -b main || \
    echo "WARN: payload git init failed (non-fatal)"
  git -c safe.directory='*' -C "$ROOTFS/opt/relay" \
      -c user.email=metaos@localhost -c user.name=metaos \
      commit -q --allow-empty -m "Meta OS payload bake $DATE" || \
    echo "WARN: payload git commit failed (non-fatal)"
fi
chroot "$ROOTFS" chown -R relay:relay /opt/relay

# ---------- 3. OS glue: units, scripts, firstboot ----------
install -m 644 services/*.service services/*.timer services/relay.target \
  "$ROOTFS/etc/systemd/system/"
# OS-038 (Milo): the demo thresholds drop-in is DEMO IMAGE ONLY.
# Production builds (the default) never install it, so production
# thresholds come from intel/thresholds.py defaults alone. A demo
# build (METAOS_DEMO=1) installs the drop-in next to the unit it
# extends, where systemd reads <unit>.d/*.conf automatically; the
# env file it points at (/opt/relay/intel/metaos-demo.env) arrives
# with the repo payload rsync above, not from this block.
if [ "${METAOS_DEMO:-0}" = "1" ]; then
  mkdir -p "$ROOTFS/etc/systemd/system/relay-watchdog.service.d"
  install -m 644 services/relay-watchdog.service.d/demo-thresholds.conf \
    "$ROOTFS/etc/systemd/system/relay-watchdog.service.d/"
fi
install -m 755 firstboot/metaos-firstboot bin/metaos-boot-checklist bin/metaos-update \
  "$ROOTFS/usr/local/bin/"
install -m 644 README-FIRSTBOOT.md "$ROOTFS/usr/local/share/README-FIRSTBOOT.md" 2>/dev/null || \
  install -m 644 README-FIRSTBOOT.md "$ROOTFS/root/README-FIRSTBOOT.md"
mkdir -p "$ROOTFS/etc/systemd/system/relay.target.wants" \
         "$ROOTFS/etc/systemd/system/multi-user.target.wants"
for u in relay-dashboard.service relay-bus.service relay-jobs.service relay-overseer.timer relay-ready.service relay-watchdog.service relay-brief.service relay-watchman.service relay-uplink.service relay-mcp-gateway.service relay-memory.service metaos-firstboot.service; do
  case $u in
    metaos-firstboot.service) ln -sf "/etc/systemd/system/$u" "$ROOTFS/etc/systemd/system/multi-user.target.wants/$u" ;;
    *) ln -sf "/etc/systemd/system/$u" "$ROOTFS/etc/systemd/system/relay.target.wants/$u" ;;
  esac
done
ln -sf /etc/systemd/system/relay-overseer.service \
  "$ROOTFS/etc/systemd/system/relay.target.wants/relay-overseer.service"
# getty autologin for the relay user on tty1 + serial (appliance, OS-009)
for g in getty@tty1 serial-getty@ttyS0; do
  d="$ROOTFS/etc/systemd/system/$g.d"
  mkdir -p "$d"
  svc=getty; [ "$g" = "serial-getty@ttyS0" ] && svc=serial-getty
  cat > "$d/autologin.conf" <<EOF
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin relay --noclear %I \$TERM
EOF
done
mkdir -p "$ROOTFS/etc/metaos" "$ROOTFS/boot/efi"
chmod 700 "$ROOTFS/etc/metaos"

# ---------- 4. GRUB config on the root filesystem ----------
KVER=$(basename "$(ls -d "$ROOTFS"/lib/modules/* | head -1)")
mkdir -p "$ROOTFS/boot/grub"
cat > "$ROOTFS/boot/grub/grub.cfg" <<EOF
set timeout=5
set default=0
menuentry "Meta OS" {
    linux /boot/vmlinuz-$KVER root=UUID=$ROOT_UUID ro console=tty0 console=ttyS0,115200 systemd.unit=relay.target
    initrd /boot/initrd.img-$KVER
}
menuentry "Meta OS (rescue - base system, no crew)" {
    linux /boot/vmlinuz-$KVER root=UUID=$ROOT_UUID ro console=tty0 console=ttyS0,115200 systemd.unit=multi-user.target
    initrd /boot/initrd.img-$KVER
}
EOF
cleanup; trap - EXIT

# ---------- 4b. OS-012: secrets sweep before assembly ----------
# The rootfs is complete at this point and still a directory, so
# the sweep can read it directly. A finding fails the build here,
# before any filesystem image is made from a leaking rootfs.
# Invoked with sh, not by path: connector pushes do not preserve
# the executable bit, and a skipped sweep is worse than a slow one.
if [ -f bin/metaos-secrets-sweep ]; then
  sh bin/metaos-secrets-sweep "$ROOTFS" || exit 1
fi

# ---------- 5. Filesystem images (no loop devices in this sandbox) ----------
ROOT_MIB=$((TOTAL_MIB - ESP_MIB - 1))
rm -f work/root.img
# Explicit size: ROOT_MIB MiB in 4096-byte blocks.
mkfs.ext4 -q -F -b 4096 -U "$ROOT_UUID" -L METAOSROOT -d "$ROOTFS" \
  work/root.img $((ROOT_MIB * 256))
echo "mkfs.ext4 rc=$?"
truncate -s "${ESP_MIB}M" work/esp.img
# -T (total sectors) is required: without it mformat fails with
# "Disk size not known" on a plain image file (run 7 root cause,
# and the unexplained run 1 death at the same step).
mformat -i work/esp.img -F -v METAESP -C -T $((ESP_MIB * 2048)) ::
mmd -i work/esp.img ::/EFI ::/EFI/BOOT

# ---------- 6. Standalone UEFI GRUB ----------
sed "s/__ROOT_UUID__/$ROOT_UUID/" grub-early.cfg > work/grub-early.cfg
grub-mkstandalone -O x86_64-efi -o work/BOOTX64.EFI \
  --modules="part_msdos part_gpt fat ext2 normal configfile linux search search_fs_uuid" \
  -d /usr/lib/grub/x86_64-efi \
  "boot/grub/grub.cfg=$PWD/work/grub-early.cfg"
mcopy -i work/esp.img work/BOOTX64.EFI ::/EFI/BOOT/BOOTX64.EFI

# ---------- 7. Assemble the raw disk image (MBR, written by python) ----------
python3 - "$IMG" "$ESP_MIB" "$TOTAL_MIB" <<'PYEOF'
import struct, sys
img, esp_mib, total_mib = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
SECT = 512
total_sectors = total_mib * 2048
esp_start = 2048
esp_sectors = esp_mib * 2048
root_start = esp_start + esp_sectors
root_sectors = total_sectors - root_start
with open(img, "wb") as f:
    f.truncate(total_sectors * SECT)
    mbr = bytearray(SECT)
    def entry(boot, ptype, start, count):
        e = bytearray(16)
        e[0] = boot; e[4] = ptype
        struct.pack_into("<I", e, 8, start)
        struct.pack_into("<I", e, 12, count)
        # CHS filler (ignored by modern boot paths)
        e[1:4] = b"\xfe\xff\xff"; e[5:8] = b"\xfe\xff\xff"
        return e
    mbr[446:462] = entry(0x80, 0xEF, esp_start, esp_sectors)
    mbr[462:478] = entry(0x00, 0x83, root_start, root_sectors)
    mbr[510:512] = b"\x55\xaa"
    f.seek(0); f.write(mbr)
    with open("work/esp.img", "rb") as e:
        f.seek(esp_start * SECT); f.write(e.read())
    with open("work/root.img", "rb") as r:
        f.seek(root_start * SECT); f.write(r.read())
print(f"image written: {img} esp@{esp_start}+{esp_sectors} root@{root_start}+{root_sectors}")
PYEOF
sha256sum "$IMG" > "$IMG.sha256"
ls -lh "$IMG"
echo "BUILD_OK $IMG"

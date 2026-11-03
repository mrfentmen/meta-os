#!/bin/bash
# Fixture tests for the MetaOS ISO build stages — WITHOUT running the build.
#
# No network, no containers, no mounts, no root. Heavy tools
# (xorriso/unsquashfs/mksquashfs/chroot) are either absent on purpose
# (missing-tool gates) or replaced by PATH-shim fakes. merge-layers.sh itself
# is NEVER executed here (it rm -rf's $WORK, mounts, chroots and apt-gets);
# its stage order, flags and gates are proven statically: every gate message,
# flag and call is pinned to a line number and asserted in pipeline order.
#
#   os-build/iso/test/test_stages.sh
#
# Exit 0 only if every fixture passes.
set -uo pipefail

HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
LANE=$(CDPATH= cd -- "$HERE/.." && pwd)
MERGE="$LANE/merge-layers.sh"
BUILD="$LANE/build_iso.sh"
PROV="$LANE/provision.sh"
FINAL="$LANE/finalize-iso-tree.sh"
GRUBFIX="$LANE/grub-fix.sh"
SPLASH="$LANE/splash/generate-splash.py"
CHECKCFG="$LANE/tools/check_configs.py"
QMP="$LANE/tools/qmp.py"

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
fails=0
passes=0

step() { printf '\n== %s ==\n' "$*"; }
ok()   { passes=$((passes + 1)); printf 'PASS  %s\n' "$*"; }
bad()  { fails=$((fails + 1));  printf 'FAIL  %s\n' "$*"; }

# run <label> <want-rc> <needle> <cmd...> — empty needle skips the output check
run() {
    local label=$1 want=$2 needle=$3
    shift 3
    local out rc
    out=$("$@" 2>&1)
    rc=$?
    if [ "$rc" -ne "$want" ]; then
        bad "$label: wanted exit $want, got $rc"
        printf '%s\n' "$out" | head -8
        return
    fi
    if [ -n "$needle" ] && ! printf '%s\n' "$out" | grep -qF -- "$needle"; then
        bad "$label: exit $rc but output lacks [$needle]"
        printf '%s\n' "$out" | head -8
        return
    fi
    ok "$label (exit $rc)"
}

# firstlineno <file> <fixed-pattern> — prints 0 when absent
firstlineno() {
    local n
    n=$(grep -n -F -m1 -e "$2" "$1" 2>/dev/null | cut -d: -f1)
    if [ -n "${n:-}" ]; then printf '%s' "$n"; else printf '0'; fi
}

prev=0
ordered() { # ordered <label> <file> <fixed-pattern>
    local n
    n=$(firstlineno "$2" "$3")
    if [ "$n" -eq 0 ]; then
        bad "$1: pattern not found: $3"
        return
    fi
    if [ "$n" -gt "$prev" ]; then
        ok "$1 (line $n)"
    else
        bad "$1: line $n not after previous line $prev"
    fi
    prev=$n
}

have_pattern() { # have_pattern <label> <file> <fixed-pattern>
    if grep -qF -e "$3" "$2"; then ok "$1"; else bad "$1: missing [$3]"; fi
}

count_is() { # count_is <label> <file> <fixed-pattern> <want>
    local c
    c=$(grep -cF -e "$3" "$2" 2>/dev/null || true)
    if [ "$c" -eq "$4" ]; then ok "$1 (x$4)"; else bad "$1: found x$c, want x$4"; fi
}

# ---------------------------------------------------------------- arg parsing
step "build_iso.sh argument parsing + preflight (native, no fakes)"
printf 'fake-iso-bytes\n' > "$tmp/fake.iso"
run "verify rejects missing ISO" 1 "base ISO not found" \
    bash "$BUILD" --verify-base "$tmp/nope.iso"
run "unknown flag rejected" 1 "unknown argument" \
    bash "$BUILD" --frobnicate
run "no args prints usage" 2 "--check" \
    bash "$BUILD"
run "--iso refuses non-Linux host" 1 "needs Linux" \
    bash "$BUILD" --iso "$tmp/fake.iso"

# --------------------------------------- faked Linux+root PATH shims for --iso
step "build_iso.sh --iso gates under faked Linux+root (ISO_MOUNT fixtures)"
mkdir -p "$tmp/shim-full"
printf '#!/bin/sh\necho Linux\n' > "$tmp/shim-full/uname"
printf '#!/bin/sh\necho 0\n' > "$tmp/shim-full/id"
for t in xorriso unsquashfs mksquashfs chroot; do
    printf '#!/bin/sh\nexit 0\n' > "$tmp/shim-full/$t"
done
chmod +x "$tmp/shim-full"/*
digest=$(sha256sum "$tmp/fake.iso" | awk '{print $1}')
printf '%s  fake.iso\n' "$digest" > "$tmp/SHA256SUMS"
mkdir -p "$tmp/mnt-layered/casper" "$tmp/mnt-unknown/casper"
: > "$tmp/mnt-layered/casper/minimal.standard.squashfs"
printf -- '- default: true\n  path: minimal.standard.squashfs\n' \
    > "$tmp/mnt-layered/casper/install-sources.yaml"
run "layered base refused without merge" 1 "layered install sources" \
    env ISO_MOUNT="$tmp/mnt-layered" PATH="$tmp/shim-full:$PATH" \
    bash "$BUILD" --iso "$tmp/fake.iso" --sha256sums "$tmp/SHA256SUMS"
run "unknown layout refused" 1 "unrecognised base layout" \
    env ISO_MOUNT="$tmp/mnt-unknown" PATH="$tmp/shim-full:$PATH" \
    bash "$BUILD" --iso "$tmp/fake.iso" --sha256sums "$tmp/SHA256SUMS"
mkdir -p "$tmp/shim-notools"
printf '#!/bin/sh\necho Linux\n' > "$tmp/shim-notools/uname"
printf '#!/bin/sh\necho 0\n' > "$tmp/shim-notools/id"
chmod +x "$tmp/shim-notools"/*
mkdir -p "$tmp/mnt-single/casper"
: > "$tmp/mnt-single/casper/filesystem.squashfs"
run "missing xorriso refused before any work" 1 "missing tool: xorriso" \
    env ISO_MOUNT="$tmp/mnt-single" PATH="$tmp/shim-notools:$PATH" \
    bash "$BUILD" --iso "$tmp/fake.iso" --sha256sums "$tmp/SHA256SUMS"

step "build_iso.sh --iso stage order (static: verify first, replay last)"
prev=0
ordered "verify_base precedes everything" "$BUILD" 'verify_base "$base" "$SUMS_FILE"'
ordered "layout detected after verify" "$BUILD" 'layout=$(base_layout "$base")'
ordered "xorriso extract after layout gate" "$BUILD" 'xorriso -osirrox on -indev "$base" -extract'
ordered "unsquash after extract" "$BUILD" 'unsquashfs -d "$work/squashfs_root" -f "$sq"'
ordered "provision after unsquash" "$BUILD" 'provision.sh" "$work/squashfs_root"'
ordered "mksquashfs after provision" "$BUILD" 'mksquashfs "$work/squashfs_root" "$sq" -noappend -b 131072'
ordered "xorriso rebuild last" "$BUILD" 'xorriso -indev "$base" -outdev "$out"'
ordered "El Torito replayed from base" "$BUILD" '-boot_image any replay \'
have_pattern "rebuild keeps -overwrite on" "$BUILD" '-overwrite on'
have_pattern "mksquashfs forwards detected compression args" "$BUILD" '"${mksq_args[@]}"'

# ------------------------------------------------------------- provision.sh
step "provision.sh argument parsing + preflight"
run "no args prints usage" 2 "usage: provision.sh" \
    bash "$PROV"
run "unknown flag rejected before root checks" 2 "unknown flag" \
    bash "$PROV" "$tmp" --bogus
mkdir -p "$tmp/fakeroot/etc" "$tmp/fakeroot/usr" "$tmp/emptyroot"
run "non-root refused even with valid flags" 1 "needs root" \
    bash "$PROV" "$tmp/fakeroot" --no-packages --no-initramfs
mkdir -p "$tmp/shim-root"
printf '#!/bin/sh\necho 0\n' > "$tmp/shim-root/id"
chmod +x "$tmp/shim-root/id"
run "non-rootfs dir refused as root" 1 "does not look like a root filesystem" \
    env PATH="$tmp/shim-root:$PATH" \
    bash "$PROV" "$tmp/emptyroot" --no-packages --no-initramfs

step "provision.sh payload lands with --no-packages --no-initramfs (fake root)"
mkdir -p "$tmp/shim-ok"
printf '#!/bin/sh\necho 0\n' > "$tmp/shim-ok/id"
printf '#!/bin/sh\necho "POISONED chroot invoked: $*" >&2\nexit 42\n' > "$tmp/shim-ok/chroot"
chmod +x "$tmp/shim-ok"/*
mkdir -p "$tmp/root/etc" "$tmp/root/usr"
out=$(env PATH="$tmp/shim-ok:$PATH" bash "$PROV" "$tmp/root" --no-packages --no-initramfs 2>&1)
rc=$?
if [ "$rc" -ne 0 ]; then
    bad "provision fixture run exited $rc"; printf '%s\n' "$out" | head -8
else
    ok "provision fixture run (exit 0)"
fi
LOG="$tmp/root/var/log/metaos-provision.log"
if [ -f "$LOG" ] && grep -q "provision complete" "$LOG"; then
    ok "provision log records completion"
else
    bad "provision log missing completion line"
fi
if [ -f "$LOG" ] && grep -q "POISONED" "$LOG"; then
    bad "provision invoked chroot despite --no-packages --no-initramfs"
else
    ok "no chroot/network in --no-packages --no-initramfs path"
fi
if [ -f "$LOG" ] && grep -q "packages skipped (--no-packages)" "$LOG" \
    && grep -q "initramfs rebuild skipped (--no-initramfs)" "$LOG"; then
    ok "both --no-* flags honoured"
else
    bad "flag-skip lines missing from provision log"
fi
for f in usr/share/plymouth/themes/metaos/metaos.plymouth \
         etc/plymouth/plymouthd.conf \
         etc/calamares/settings.conf \
         usr/local/lib/metaos/meta-branding.sh \
         etc/xdg/autostart/metaos-install.desktop; do
    if [ -f "$tmp/root/$f" ]; then ok "payload landed: $f"; else bad "payload missing: $f"; fi
done
if [ -x "$tmp/root/usr/local/lib/metaos/meta-branding.sh" ]; then
    ok "branding hook is executable"
else
    bad "branding hook lost its mode"
fi

# ------------------------------------------------------ grub finalize logic
step "finalize-iso-tree.sh + grub-fix.sh (fixture tree, real runs)"
mkdir -p "$tmp/tree/boot/grub" "$tmp/tree/.disk"
cat > "$tmp/tree/boot/grub/grub.cfg" <<'EOF'
menuentry "Try or Install Xubuntu" {
    linux   /casper/vmlinuz  file=$cdrom/preseed/xubuntu.seed --- quiet splash
}
menuentry "Xubuntu (safe graphics)" {
    linux   /casper/vmlinuz nomodeset --- quiet splash
}
EOF
run "finalize rejects missing tree arg" 1 "iso tree root" \
    bash "$FINAL"
out=$(bash "$FINAL" "$tmp/tree" 2>&1); rc=$?
if [ "$rc" -ne 0 ]; then bad "finalize fixture run exited $rc"; else ok "finalize fixture run (exit 0)"; fi
lf1=$(grep -c 'layerfs-path=filesystem.squashfs' "$tmp/tree/boot/grub/grub.cfg" || true)
cs1=$(grep -c 'console=ttyS0' "$tmp/tree/boot/grub/grub.cfg" || true)
[ "${lf1:-0}" -ge 1 ] && ok "layerfs-path present (x$lf1)" || bad "layerfs-path missing after finalize"
[ "${cs1:-0}" -ge 1 ] && ok "serial console present (x$cs1)" || bad "console=ttyS0 missing after finalize"
if grep -q "Try or Install MetaOS" "$tmp/tree/boot/grub/grub.cfg" \
    && grep -q "MetaOS (safe graphics)" "$tmp/tree/boot/grub/grub.cfg" \
    && ! grep -q "Xubuntu" "$tmp/tree/boot/grub/grub.cfg"; then
    ok "Meta branding strings replace Xubuntu"
else
    bad "branding strings wrong after finalize"
fi
if [ "$(cat "$tmp/tree/.disk/info")" = "MetaOS 1.0 LTS" ]; then
    ok ".disk/info rewritten"
else
    bad ".disk/info not rewritten"
fi
bash "$FINAL" "$tmp/tree" >/dev/null 2>&1
lf2=$(grep -c 'layerfs-path=filesystem.squashfs' "$tmp/tree/boot/grub/grub.cfg" || true)
cs2=$(grep -c 'console=ttyS0' "$tmp/tree/boot/grub/grub.cfg" || true)
if [ "$lf1" = "$lf2" ] && [ "$cs1" = "$cs2" ]; then
    ok "finalize is idempotent (exactly-once, no double insert)"
else
    bad "finalize duplicated entries on rerun ($lf1->$lf2, $cs1->$cs2)"
fi
sed -i.bak 's/ layerfs-path=filesystem.squashfs//g; s/ console=ttyS0//g' \
    "$tmp/tree/boot/grub/grub.cfg"
rm -f "$tmp/tree/boot/grub/grub.cfg.bak"
lf0=$(grep -c 'layerfs-path=filesystem.squashfs' "$tmp/tree/boot/grub/grub.cfg" || true)
[ "${lf0:-0}" -eq 0 ] && ok "clobbered grub.cfg loses layerfs (test setup)" \
    || bad "clobber setup failed"
run "grub-fix restores layerfs+console" 0 "grub fixed:" \
    bash "$GRUBFIX" "$tmp/tree/boot/grub/grub.cfg"
lf3=$(grep -c 'layerfs-path=filesystem.squashfs' "$tmp/tree/boot/grub/grub.cfg" || true)
cs3=$(grep -c 'console=ttyS0' "$tmp/tree/boot/grub/grub.cfg" || true)
if [ "$lf3" = "$lf1" ] && [ "$cs3" = "$cs1" ]; then
    ok "grub-fix restores exact counts (no duplication)"
else
    bad "grub-fix counts differ ($lf1/$cs1 vs $lf3/$cs3)"
fi
bash "$GRUBFIX" "$tmp/tree/boot/grub/grub.cfg" >/dev/null 2>&1
lf4=$(grep -c 'layerfs-path=filesystem.squashfs' "$tmp/tree/boot/grub/grub.cfg" || true)
[ "$lf4" = "$lf3" ] && ok "grub-fix is idempotent" || bad "grub-fix duplicated on rerun"
out=$(bash "$GRUBFIX" "$tmp/missing.cfg" 2>&1); rc=$?
if [ "$rc" -ne 0 ]; then ok "grub-fix fails loudly on missing file"; else bad "grub-fix passed on missing file"; fi
out=$(bash "$FINAL" "$tmp/no-such-tree" 2>&1); rc=$?
# finalize-iso-tree.sh has no `set -e`: a missing tree prints the python
# traceback but still exits 0 via the disk-info skip path. That tolerance is
# safe only because merge-layers.sh asserts grub layerfs/console counts right
# after the finalize call (order proven above: call line 176 < assert).
if printf '%s' "$out" | grep -q "disk-info skipped"; then
    ok "finalize tolerates missing tree (skips info; merge grub assert is the loud gate)"
else
    bad "finalize missing-tree behavior changed: rc=$rc out=$out"
fi
mkdir -p "$tmp/tree2/boot/grub"
cp "$tmp/tree/boot/grub/grub.cfg" "$tmp/tree2/boot/grub/grub.cfg"
run "finalize without .disk skips info, still exits 0" 0 "disk-info skipped" \
    bash "$FINAL" "$tmp/tree2"

# --------------------------------- merge-layers.sh static proof (NEVER run it)
step "merge-layers.sh stage order (static: asserted in pipeline order)"
prev=0
ordered "env gates first (unset ISO aborts)" "$MERGE" 'ISO="${ISO:?base iso path}"'
ordered "tool install before any work" "$MERGE" 'apt-get install -y -qq xorriso'
ordered "xorriso extract" "$MERGE" 'xorriso -osirrox on -indev "$ISO" -extract'
ordered "unsquash minimal layer" "$MERGE" 'unsquashfs -exclude-file "$WORK/excludes.txt" -d "$WORK/minimal"'
ordered "rsync overlay after unsquash" "$MERGE" 'rsync -a "$WORK/minimal/"'
ordered "GATE 1 rootfs sanity" "$MERGE" 'GATE 1'
ordered "chroot smoke test" "$MERGE" 'chroot "$WORK/rootfs" true'
ordered "provision package install" "$MERGE" 'calamares plank fonts-inter'
ordered "GATE 2 five packages" "$MERGE" 'GATE 2'
ordered "Meta payload via provision.sh" "$MERGE" 'provision.sh" "$WORK/rootfs" --no-initramfs'
ordered "payload gate" "$MERGE" 'payload gate'
ordered ".live layer transplant" "$MERGE" 'minimal.standard.live.squashfs'
ordered "initramfs rebuild" "$MERGE" 'update-initramfs -u -k'
ordered "GATE 3 casper count" "$MERGE" 'GATE 3'
ordered "grub finalize call" "$MERGE" 'finalize-iso-tree.sh" "$WORK/iso'
ordered "grub assert" "$MERGE" 'grub.cfg has no layerfs'
ordered "manifest regen" "$MERGE" '> "$WORK/iso/casper/filesystem.manifest"'
ordered "mksquashfs repack" "$MERGE" 'mksquashfs "$WORK/rootfs"'
ordered "GATE 4 size gate" "$MERGE" 'GATE 4'
ordered "install-sources rewrite" "$MERGE" '> "$WORK/iso/casper/install-sources.yaml"'
ordered "xorriso rebuild" "$MERGE" 'xorriso -indev "$ISO" -outdev "$OUT_ISO"'
ordered "GATE 5 El Torito" "$MERGE" 'GATE 5'
ordered "GATE 6 UUID sync" "$MERGE" 'GATE 6'
ordered "export ALL-DONE last" "$MERGE" 'ALL-DONE'

step "merge-layers.sh flags (static)"
count_is "both squashfs layers use -exclude-file" "$MERGE" 'unsquashfs -exclude-file' 2
if grep -vE '^[[:space:]]*#' "$MERGE" | grep -qE '(^| )-ef( |$)'; then
    bad "bare -ef flag present (must be -exclude-file, see script NB)"
else
    ok "no bare -ef flag (exclude-file gotcha held)"
fi
if grep -vE '^[[:space:]]*#' "$MERGE" | grep -qE 'unsquashfs -f -d "\$WORK/livefix".*\|\| true'; then
    ok ".live transplant is WARN-tolerant (|| true)"
else
    bad ".live transplant lost its || true tolerance"
fi
mksq=$(grep -F -m1 -e 'mksquashfs "$WORK/rootfs"' "$MERGE")
for flag in '-noappend' '-b 131072' '-comp xz' '-no-progress'; do
    if printf '%s' "$mksq" | grep -qF -- "$flag"; then ok "mksquashfs flag: $flag"
    else bad "mksquashfs flag missing: $flag"; fi
done
block=$(sed -n '/rebuild bootable ISO/,/-commit/p' "$MERGE")
for flag in '-boot_image any replay' '-overwrite on' '-rm_r /' '-map "$WORK/iso" /'; do
    if printf '%s' "$block" | grep -qF -- "$flag"; then ok "xorriso rebuild flag: $flag"
    else bad "xorriso rebuild flag missing: $flag"; fi
done
have_pattern "initramfs rebuilt for newest kver" "$MERGE" 'update-initramfs -u -k'
have_pattern "GATE 3 threshold >= 40 casper files" "$MERGE" '"$CASPER_N" -ge 40'
have_pattern "GATE 4 threshold > 1 GiB" "$MERGE" '"$SQ_BYTES" -gt 1073741824'
have_pattern "GATE 5 wants exactly 2 boot images" "$MERGE" '"$BOOT_N" -eq 2'
have_pattern "UUID baked via unmkinitramfs" "$MERGE" 'unmkinitramfs'
have_pattern "UUID read from initrd uuid.conf" "$MERGE" 'uuid.conf'
have_pattern "UUID sync verified by re-read" "$MERGE" '"$(cat "$WORK/iso/.disk/casper-uuid-generic")" = "$INITRD_UUID"'
count_is "tree UUID written exactly once" "$MERGE" '> "$WORK/iso/.disk/casper-uuid-generic"' 1
count_is "finalize-iso-tree.sh invoked exactly once" "$MERGE" 'finalize-iso-tree.sh" "$WORK/iso' 1
fline=$(firstlineno "$MERGE" 'finalize-iso-tree.sh" "$WORK/iso')
uline=$(firstlineno "$MERGE" '> "$WORK/iso/.disk/casper-uuid-generic"')
if [ "$fline" -ge 1 ] && [ "$uline" -gt "$fline" ]; then
    ok "grub-finalize (line $fline) precedes UUID-sync (line $uline)"
else
    bad "grub-finalize/UUID-sync order wrong ($fline, $uline)"
fi
have_pattern "unset SRCDIR aborts" "$MERGE" 'SRCDIR="${SRCDIR:?mounted iso tree}"'
have_pattern "unset WORK aborts" "$MERGE" 'WORK="${WORK:?work dir}"'
have_pattern "unset OUTDIR aborts" "$MERGE" 'OUTDIR="${OUTDIR:?export dir}"'
have_pattern "host tools pinned (xorriso/squashfs/rsync/initramfs)" "$MERGE" 'apt-get install -y -qq xorriso squashfs-tools rsync initramfs-tools-core'
have_pattern "foreign-arch emulator staged conditionally" "$MERGE" 'qemu-user-static'

step "merge-layers.sh gates fire on bad inputs (static: fail messages)"
for pair in \
    "rootfs sanity|rootfs missing /\$d after layer overlay" \
    "package check|package \$p not installed" \
    "sibling provision.sh|provision.sh not beside merge-layers.sh" \
    "payload presence|payload missing in rootfs" \
    "kernel detection|no kernel version found" \
    "base initrd presence|no casper/initrd in base tree" \
    "grub layerfs|grub.cfg has no layerfs" \
    "grub console|grub.cfg has no console=ttyS0" \
    "manifest non-empty|filesystem.manifest empty" \
    "manifest calamares|lacks calamares" \
    "repack present|filesystem.squashfs missing after repack" \
    "repack size|repack is truncated" \
    "xorriso output|xorriso produced no ISO" \
    "El Torito count|expected exactly 2 El Torito" \
    "unmkinitramfs|unmkinitramfs failed" \
    "baked UUID|no baked UUID in built initrd" \
    "UUID verify|UUID sync verify failed" \
    "qemu static|qemu-user-static installed but no" \
    "chroot smoke|chroot smoke test failed" ; do
    label=${pair%%|*}
    pat=${pair#*|}
    have_pattern "gate: $label" "$MERGE" "$pat"
done

# ------------------------------------------------- python generators/validators
step "python generators/validators (py_compile + splash PNG asserts)"
run "py_compile generate-splash.py" 0 "" python3 -m py_compile "$SPLASH"
run "py_compile check_configs.py" 0 "" python3 -m py_compile "$CHECKCFG"
run "py_compile qmp.py" 0 "" python3 -m py_compile "$QMP"
if [ -e "$LANE/../metaos-theme/wallpapers/gen.py" ]; then
    run "py_compile wallpapers/gen.py" 0 "" python3 -m py_compile "$LANE/../metaos-theme/wallpapers/gen.py"
else
    printf 'NOTE  metaos-theme/wallpapers/gen.py absent on this branch (not tested)\n'
fi
RECOL=$(find "$LANE" -maxdepth 3 -iname '*recolor*' -print -quit 2>/dev/null)
if [ -n "$RECOL" ]; then
    step "recolor script maps Papirus blues on a fixture tree (offline)"
    mkdir -p "$tmp/pap/SIZE/places"
    printf '<svg><path fill="#5294e2"/><path fill="#4877b1"/></svg>' > "$tmp/pap/SIZE/places/folder-blue.svg"
    printf '<svg><path fill="#5294e2"/></svg>' > "$tmp/pap/SIZE/places/user-blue-starred.svg"
    printf '<svg><path fill="#5294e2"/></svg>' > "$tmp/pap/SIZE/places/solus-logo.svg"
    ln -s folder-blue.svg "$tmp/pap/SIZE/places/folder.svg"
    run "recolor fixture run (exit 0)" 0 "recolored" sh "$RECOL" "$tmp/pap" "$tmp/icons-out"
    [ "$(grep -c '#1877F2' "$tmp/icons-out/SIZE/places/folder-blue.svg")" = "1" ] \
        && ok "front tone mapped #5294e2 -> #1877F2" || bad "front tone map missing"
    [ "$(grep -c '#1360C4' "$tmp/icons-out/SIZE/places/folder-blue.svg")" = "1" ] \
        && ok "back tone mapped #4877b1 -> #1360C4" || bad "back tone map missing"
    if grep -q '#5294e2\|#4877b1' "$tmp/icons-out/SIZE/places/folder-blue.svg" "$tmp/icons-out/SIZE/places/user-blue-starred.svg" 2>/dev/null; then
        bad "source tones remain in scope"
    else
        ok "no source tones left in scope"
    fi
    [ -L "$tmp/icons-out/SIZE/places/folder.svg" ] \
        && ok "symlink alias preserved" || bad "symlink alias lost"
    grep -q '#5294e2' "$tmp/icons-out/SIZE/places/solus-logo.svg" \
        && ok "out-of-scope file untouched" || bad "out-of-scope file touched"
else
    printf 'NOTE  no recolor script on this branch (not tested)\n'
fi
mkdir -p "$tmp/splash-out"
run "splash generator emits spec PNGs to tempdir" 0 "splash generator:" \
    python3 - "$SPLASH" "$tmp/splash-out" <<'PYEOF'
import importlib.util
import os
import sys
modpath, outdir = sys.argv[1], sys.argv[2]
spec = importlib.util.spec_from_file_location("gensplash", modpath)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
os.makedirs(outdir, exist_ok=True)
bg = m.load_background()
assert bg.size == (1920, 1080), bg.size
assert bg.mode == "RGB", bg.mode
mark = m.draw_mark()
assert mark.size == (512, 512), mark.size
assert mark.mode == "RGBA", mark.mode
bar = m.draw_progress()
assert bar.size == (560, 28), bar.size
assert bar.mode == "RGBA", bar.mode
bg.save(os.path.join(outdir, "background.png"))
mark.save(os.path.join(outdir, "meta-m.png"))
bar.save(os.path.join(outdir, "progress.png"))
from PIL import Image
for name, size, mode in [("background.png", (1920, 1080), "RGB"),
                         ("meta-m.png", (512, 512), "RGBA"),
                         ("progress.png", (560, 28), "RGBA")]:
    im = Image.open(os.path.join(outdir, name))
    im.load()
    assert im.size == size and im.mode == mode, (name, im.size, im.mode)
print("splash generator: background 1920x1080 RGB, mark 512x512 RGBA, bar 560x28 RGBA")
PYEOF

step "summary"
printf '%d pass, %d fail\n' "$passes" "$fails"
if [ "$fails" -ne 0 ]; then
    printf 'STAGE FIXTURES: FAIL\n'
    exit 1
fi
printf 'STAGE FIXTURES: PASS (merge-layers.sh never executed; no network/mounts/root)\n'

#!/bin/bash
# MetaOS 1.0 -- boot + installer lane build driver.
#
# Three modes, in the order the 12-hour plan uses them:
#
#   --check                     validate configs + report tool readiness.
#                               Runs anywhere, including this Mac.
#   --root <cubic-root>         provision a Cubic chroot, stop there.
#                               Then press Generate in Cubic, by hand.
#   --iso <base.iso> [--out F]  full patch on a Linux host as root:
#                               verify the base hash, extract, unsquash,
#                               provision, re-squash, rebuild the ISO with
#                               its boot images replayed, print the sha256.
#   --tree-only [DIR]         assemble the repo payload into a temp tree (or DIR)
#                               and stop before mastering. No root, no loop
#                               mount, no chroot, no network: the payload copy
#                               set from provision.sh, the agent-layer stage,
#                               and nothing that needs a base rootfs (no
#                               packages, no initramfs rebuild, no identity
#                               scripts — those belong to the real build and
#                               to OS-1). Runs anywhere, including this Mac.
#   --verify-base <iso>         hash-check a base ISO only. Runs on the Mac.
#   --base-info <iso>           print layout (single vs layered squashfs),
#                               squashfs images and hash. Runs on the Mac.
#   --inspect <iso>             Linux: prove the built ISO actually carries
#                               the Meta payload (theme, calamares, hook,
#                               autostart) inside its squashfs.
#
#   --sha256sums FILE           sums file to verify --iso against; default
#                               looks for <iso>.sha256 or SHA256SUMS beside it
#   --no-verify-base            patch an unverified ISO (explicit opt-out;
#                               the build prints a WARN and the sha256)
#
# Claim label: WRITTEN, UNRUN. XORRISO/mksquashfs are not on the build Mac;
# --check is the only mode proven locally.
set -euo pipefail

HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT_DIR=$(CDPATH= cd -- "$HERE/../.." && pwd)   # meta-os/
WORK_DEFAULT="$HERE/work"

say()  { printf 'build_iso: %s\n' "$*"; }
die()  { printf 'build_iso: ERROR: %s\n' "$*" >&2; exit 1; }
have() { command -v "$1" >/dev/null 2>&1; }

# ---- base layout -------------------------------------------------------
# Ubuntu flavour ISOs are not uniform any more. Some 24.04 flavour images
# ship ONE casper/filesystem.squashfs (what unpackfs and every remaster
# recipe assume); others ship *layered install sources* -- several
# casper/minimal*.squashfs images selected by casper/install-sources.yaml.
# Patching the latter with a single-squashfs recipe silently targets a
# file that does not exist (or worse, the wrong layer). Detect first.
iso_entries() {
    local iso=$1
    if [ -n "${ISO_MOUNT:-}" ] && [ -d "$ISO_MOUNT/casper" ]; then
        ( cd "$ISO_MOUNT" && find . -type f | sed 's|^\./||' )
        return 0
    fi
    have bsdtar || die "need bsdtar (or a mounted ISO in ISO_MOUNT) to list $iso"
    bsdtar -tf "$iso" | sed 's|^\./||'
}

base_layout() {
    local iso=$1 entries
    entries=$(iso_entries "$iso")
    if printf '%s\n' "$entries" | grep -qx 'casper/filesystem.squashfs'; then
        echo single
    elif printf '%s\n' "$entries" | grep -q 'casper/install-sources.yaml'; then
        echo layered
    elif printf '%s\n' "$entries" | grep -q 'live/filesystem.squashfs'; then
        echo single-live
    else
        echo unknown
    fi
}

base_info() {
    local iso=$1
    [ -f "$iso" ] || die "ISO not found: $iso"
    local layout
    layout=$(base_layout "$iso")
    say "base: $(basename "$iso") ($(sha256_of "$iso"))"
    say "layout: $layout"
    say "casper images:"
    iso_entries "$iso" | grep -E '^casper/.*\.(squashfs|yaml|size)$' | sed 's/^/  /'
    case "$layout" in
        single)        say "supported: unpackfs -> /cdrom/casper/filesystem.squashfs" ;;
        single-live)   say "supported with a path change: live/filesystem.squashfs" ;;
        layered)       say "NOT supported by the single-rootfs recipe: layered install sources"
                       say "options: use a base that ships casper/filesystem.squashfs, or merge layers (out of scope)" ;;
        *)             say "unknown layout: do not patch this image blindly" ;;
    esac
}

sha256_of() {  # portable: coreutils, perl shasum, or openssl
    if have sha256sum; then sha256sum "$1" | awk '{print $1}'
    elif have shasum; then shasum -a 256 "$1" | awk '{print $1}'
    elif have openssl; then openssl dgst -sha256 "$1" | awk '{print $NF}'
    else return 1; fi
}

# A patched ISO inherits every byte of its base. Building on an unverified
# download and then shipping the result is a supply-chain hole, so the hash
# is checked BEFORE any extraction. Opting out is explicit and logged.
verify_base() {
    local iso=$1 sums=${2:-}
    [ -f "$iso" ] || die "base ISO not found: $iso"
    if [ "$ALLOW_UNVERIFIED" = "1" ]; then
        say "WARN: base ISO verification skipped (--no-verify-base). sha256: $(sha256_of "$iso")"
        return 0
    fi
    local base
    base=$(basename "$iso")
    if [ -z "$sums" ]; then
        local cand
        for cand in "$iso.sha256" "$(dirname "$iso")/$base.sha256" "$(dirname "$iso")/SHA256SUMS"; do
            if [ -f "$cand" ]; then sums=$cand; break; fi
        done
    fi
    if [ -z "$sums" ]; then
        die "no SHA256SUMS beside $base; pass --sha256sums FILE or --no-verify-base"
    fi
    [ -f "$sums" ] || die "sums file not found: $sums"
    local expect
    expect=$(awk -v b="$base" '$2 == b || $2 == "*" b { print $1; exit }' "$sums")
    [ -n "$expect" ] || die "no line for $base in $sums"
    local got
    got=$(sha256_of "$iso") || die "no sha256 tool (sha256sum, shasum, openssl)"
    if [ "$expect" != "$got" ]; then
        die "base ISO hash mismatch: sums say $expect, file is $got — refusing to patch"
    fi
    say "base ISO sha256 verified: $got ($sums)"
}

# Post-build payload check. The VM run proves boot; this proves the build
# actually wrote our files into the image instead of silently skipping a copy.
inspect_mode() {
    local iso=$1
    [ -f "$iso" ] || die "ISO not found: $iso"
    have xorriso || die "--inspect needs xorriso"
    have unsquashfs || die "--inspect needs unsquashfs (squashfs-tools)"
    local tmp
    tmp=$(mktemp -d)
    trap 'rm -rf "$tmp"' EXIT
    say "inspecting $iso (sha256 $(sha256_of "$iso"))"
    xorriso -osirrox on -indev "$iso" -extract /casper/filesystem.squashfs "$tmp/fs.squashfs" >/dev/null 2>&1 \
        || die "no casper/filesystem.squashfs inside $iso"
    unsquashfs -l "$tmp/fs.squashfs" > "$tmp/list.txt" 2>/dev/null \
        || die "unsquashfs -l failed on the extracted squashfs"
    local missing=0 checked=0 f
    for f in \
        usr/share/plymouth/themes/metaos/metaos.plymouth \
        usr/share/plymouth/themes/metaos/metaos.script \
        usr/share/plymouth/themes/metaos/logo.png \
        usr/share/plymouth/themes/metaos/wordmark.png \
        usr/share/plymouth/themes/metaos/dot.png \
        etc/plymouth/plymouthd.conf \
        etc/calamares/settings.conf \
        etc/calamares/modules/meta-branding.conf \
        etc/calamares/branding/metaos/branding.desc \
        usr/local/lib/metaos/meta-branding.sh \
        etc/xdg/autostart/metaos-install.desktop \
        usr/share/metaos/installer.png ; do
        checked=$((checked + 1))
        # Directory entries end in / in unsquashfs -l output; accept both.
        if grep -qx -e "$f" -e "/$f" -e "$f/" -e "/$f/" "$tmp/list.txt"; then
            printf '  [OK]      %s\n' "$f"
        else
            printf '  [MISSING] %s\n' "$f"
            missing=1
        fi
    done
    if [ "$missing" = "1" ]; then
        die "payload incomplete in $iso"
    fi
    say "payload complete: all $checked required paths present inside the squashfs"
}

usage() {
    sed -n '2,34p' "$0" | sed 's/^# \{0,1\}//'
    exit "${1:-2}"
}

# ------------------------------------------------------------------- check
check_mode() {
    local failures=0
    say "checking configs with tools/check_configs.py"
    if python3 "$HERE/tools/check_configs.py"; then
        say "configs: PASS"
    else
        say "configs: FAIL"
        failures=$((failures + 1))
    fi

    say "tool readiness (build modes need root on Linux):"
    for t in xorriso unsquashfs mksquashfs chroot sha256sum shasum openssl; do
        if have "$t"; then
            printf '  %-12s %s\n' "$t" "$(command -v "$t")"
        else
            printf '  %-12s MISSING\n' "$t"
        fi
    done
    if [ "$(uname -s)" = "Linux" ] && [ "$(id -u)" = "0" ]; then
        say "host: Linux + root -- build modes available"
    else
        say "host: $(uname -s), uid $(id -u) -- build modes NOT available here (expected on the Mac)"
    fi
    say "claim labels: configs=LOCAL-CHECK, ISO=UNRUN, install=PENDING Linux host"
    return "$failures"
}

# -------------------------------------------------------------------- root
root_mode() {
    local root=$1
    [ -d "$root" ] || die "--root $root does not exist"
    [ "$(id -u)" = "0" ] || die "--root mode needs root"
    say "provisioning Cubic chroot: $root"
    sh "$HERE/provision.sh" "$root"
    say "done. In Cubic: press Generate, then run the VM proof against the new ISO."
    say "expected output name: metaos-1.0-amd64.iso"
}

# --------------------------------------------------------------------- iso
iso_mode() {
    local base=$1 out=$2
    [ -f "$base" ] || die "base ISO not found: $base"
    [ "$(uname -s)" = "Linux" ] || die "--iso mode needs Linux (xorriso + chroot)"
    [ "$(id -u)" = "0" ] || die "--iso mode needs root"
    for t in xorriso unsquashfs mksquashfs chroot; do
        have "$t" || die "missing tool: $t (apt-get install xorriso squashfs-tools)"
    done

    verify_base "$base" "$SUMS_FILE"

    local layout
    layout=$(base_layout "$base")
    case "$layout" in
        single)      say "base layout: one casper/filesystem.squashfs (supported)" ;;
        single-live) say "base layout: live/filesystem.squashfs (supported)";; 
        layered)
            die "$base uses layered install sources (casper/minimal*.squashfs + install-sources.yaml); unpackfs and this patch path expect one casper/filesystem.squashfs. Use a base that ships it, or merge the layers first. Run --base-info for the list." ;;
        *) die "unrecognised base layout in $base; run --base-info before patching" ;;
    esac

    local work="$WORK_DEFAULT"
    rm -rf "$work"
    mkdir -p "$work/iso_root" "$work/squashfs_root"

    say "extracting $base -> $work/iso_root"
    xorriso -osirrox on -indev "$base" -extract / "$work/iso_root" 2>&1 | tail -2
    chmod -R u+w "$work/iso_root"

    local sq=""
    for cand in "$work/iso_root/casper/filesystem.squashfs" "$work/iso_root/live/filesystem.squashfs"; do
        [ -f "$cand" ] && sq=$cand && break
    done
    [ -n "$sq" ] || die "no casper/live filesystem.squashfs inside $base"

    local comp
    comp=$(unsquashfs -s "$sq" | awk -F': *' '/^Compression/ {print $2; exit}')
    say "base squashfs: $sq (compression: ${comp:-unknown})"

    say "unsquashing (this is the slow step)"
    unsquashfs -d "$work/squashfs_root" -f "$sq" >/dev/null

    say "provisioning the unpacked root"
    sh "$HERE/provision.sh" "$work/squashfs_root"

    say "re-squashing"
    case "$comp" in
        zstd) local mksq_args=(-comp zstd -Xcompression-level 15) ;;
        gzip) local mksq_args=(-comp gzip) ;;
        *)    local mksq_args=(-comp xz -Xbcj x86) ;;
    esac
    mksquashfs "$work/squashfs_root" "$sq" -noappend -b 131072 -no-progress "${mksq_args[@]}" >/dev/null
    # Ubuntu's casper checks this file for the extracted size.
    if [ -d "$work/iso_root/casper" ]; then
        du -sx --block-size=1 "$work/squashfs_root" | awk '{print $1}' \
            > "$work/iso_root/casper/filesystem.size"
    fi

    say "refreshing md5sum.txt"
    if [ -f "$work/iso_root/md5sum.txt" ]; then
        ( cd "$work/iso_root" && find . -type f ! -name md5sum.txt -print0 | xargs -0 md5sum > md5sum.txt )
    fi

    mkdir -p "$(dirname "$out")"
    say "rebuilding ISO -> $out (boot images replayed from the base)"
    # `-boot_image any replay` reuses the base ISO's El Torito + hybrid MBR
    # instead of hand-writing isohybrid args per Ubuntu release. This is the
    # recipe that survives base-ISO layout changes.
    xorriso -indev "$base" -outdev "$out" \
        -boot_image any replay \
        -overwrite on \
        -rm_r / -- -map "$work/iso_root" / \
        -commit 2>&1 | tail -5

    [ -f "$out" ] || die "xorriso produced no output at $out"
    ( cd "$(dirname "$out")" && sha256sum "$(basename "$out")" | tee "$(basename "$out").sha256" )
    say "ISO built. Next: tools/vm_install_proof.sh --iso $out"
}

# --------------------------------------------------------------- tree-only
# Assemble the repo payload into a temp tree without root. This mirrors the
# COPY sections of provision.sh (cited as PROV:<line> so drift is checkable)
# and stops where provision.sh starts needing a base rootfs: no packages, no
# initramfs rebuild (both chroot), no identity scripts (OS-1's, and they
# expect a full base tree). The agent-layer stage runs because stage.sh is
# root-tolerant. What this tree IS: every file this repo contributes to the
# image, at final paths, verifiable for presence, symlinks and stray paths.
# What it is NOT: a bootable rootfs (no kernel, no userspace, no users).
tree_only_mode() {
    local tree=${1:-}
    [ -n "$tree" ] || tree=$(mktemp -d "${TMPDIR:-/tmp}/metaos-tree-XXXXXX")
    mkdir -p "$tree"
    say "tree-only: assembling repo payload into $tree"
    say "tree-only: packages, initramfs and identity skipped (need base rootfs)"

    local ISO_DIR="$HERE"
    local PAYLOAD="$ISO_DIR/payload-theme"
    local APPS="$ISO_DIR/payload-apps"
    local AGENT="$ROOT_DIR/agent-layer"
    local META_APP_SRC="$ROOT_DIR/os-build/face/native/meta-app.py"

    mkdir -p "$tree/etc" "$tree/usr" "$tree/var/log/metaos"

    # PROV:51-64 plymouth theme + live splash config
    say "tree-only: plymouth theme"
    mkdir -p "$tree/usr/share/plymouth/themes/metaos"
    cp -a "$ISO_DIR/plymouth/metaos/." "$tree/usr/share/plymouth/themes/metaos/"
    find "$tree/usr/share/plymouth/themes/metaos" -type f -exec chmod 0644 {} +
    chmod 0755 "$tree/usr/share/plymouth/themes/metaos"
    mkdir -p "$tree/etc/plymouth"
    cat > "$tree/etc/plymouth/plymouthd.conf" <<'PLYMOUTH'
[Daemon]
Theme=metaos
ShowDelay=0
DeviceTimeout=8
PLYMOUTH

    # PROV:66-76 calamares config
    say "tree-only: calamares config"
    mkdir -p "$tree/etc/calamares/modules" "$tree/etc/calamares/branding/metaos"
    cp -a "$ISO_DIR/calamares/settings.conf" "$tree/etc/calamares/settings.conf"
    cp -a "$ISO_DIR/calamares/modules/." "$tree/etc/calamares/modules/"
    cp -a "$ISO_DIR/calamares/branding/metaos/." "$tree/etc/calamares/branding/metaos/"
    find "$tree/etc/calamares" -type f -exec chmod 0644 {} +

    # PROV:78-82 in-target branding hook
    say "tree-only: branding hook"
    mkdir -p "$tree/usr/local/lib/metaos"
    cp -a "$ISO_DIR/calamares/meta-branding.sh" "$tree/usr/local/lib/metaos/meta-branding.sh"
    chmod 0755 "$tree/usr/local/lib/metaos/meta-branding.sh"

    # PROV:84-100 live-session autostart + icon
    say "tree-only: live-session autostart + icon"
    mkdir -p "$tree/usr/share/metaos"
    cp -a "$ISO_DIR/calamares/branding/metaos/productIcon.png" "$tree/usr/share/metaos/installer.png"
    mkdir -p "$tree/etc/xdg/autostart"
    cat > "$tree/etc/xdg/autostart/metaos-install.desktop" <<'DESKTOP'
[Desktop Entry]
Type=Application
Name=Install MetaOS
Comment=Install MetaOS 1.0 on this computer
Exec=sh -c "sleep 8; exec calamares"
Icon=/usr/share/metaos/installer.png
Terminal=false
OnlyShowIn=XFCE;
X-GNOME-Autostart-Delay=8
DESKTOP
    chmod 0644 "$tree/etc/xdg/autostart/metaos-install.desktop"

    # PROV:102-128 welcome app + Meta theme payload
    say "tree-only: welcome app + theme payload"
    mkdir -p "$tree/usr/share/metaos/apps" "$tree/usr/share/applications" "$tree/usr/share/backgrounds" "$tree/usr/share/plank/themes" "$tree/usr/share/themes" "$tree/etc/lightdm" "$tree/etc/bash.bashrc.d" "$tree/usr/local/bin"
    install -m755 "$PAYLOAD/apps/metaos-welcome.py" "$tree/usr/share/metaos/apps/metaos-welcome.py"
    install -m644 "$PAYLOAD/apps/metaos-welcome.desktop" "$tree/usr/share/applications/metaos-welcome.desktop"
    install -m644 "$PAYLOAD/apps/metaos-welcome.desktop" "$tree/etc/xdg/autostart/metaos-welcome.desktop"
    install -m644 "$PAYLOAD/greeter/lightdm-gtk-greeter.conf" "$tree/etc/lightdm/lightdm-gtk-greeter.conf"
    mkdir -p "$tree/etc/lightdm/lightdm.conf.d"
    install -m644 "$PAYLOAD/greeter/10-metaos-live.conf" "$tree/etc/lightdm/lightdm.conf.d/10-metaos-live.conf"
    install -m644 "$PAYLOAD/wallpapers/meta-ascii.png" "$tree/usr/share/backgrounds/meta-ascii.png" 2>/dev/null || true
    install -m644 "$PAYLOAD/wallpapers/meta-rays.png" "$tree/usr/share/backgrounds/meta-rays.png" 2>/dev/null || true
    install -m644 "$PAYLOAD/wallpapers/meta-dusk.png" "$tree/usr/share/backgrounds/meta-dusk.png" 2>/dev/null || true
    install -m644 "$PAYLOAD/wallpapers/meta-dawn.png" "$tree/usr/share/backgrounds/meta-dawn.png" 2>/dev/null || true
    cp -r "$PAYLOAD/gtk/." "$tree/usr/share/themes/" 2>/dev/null || { mkdir -p "$tree/usr/share/themes/MetaOS/gtk-3.0"; install -m644 "$PAYLOAD/gtk/gtk.css" "$tree/usr/share/themes/MetaOS/gtk-3.0/gtk.css"; }
    mkdir -p "$tree/usr/share/themes/MetaOS/xfwm4"
    install -m644 "$PAYLOAD/xfwm4/themerc" "$tree/usr/share/themes/MetaOS/xfwm4/themerc"
    mkdir -p "$tree/usr/share/plank/themes/MetaOS"
    install -m644 "$PAYLOAD/dock/dock.theme" "$tree/usr/share/plank/themes/MetaOS/dock.theme"
    mkdir -p "$tree/etc/skel/.config/xfce4/xfconf/xfce-perchannel-xml" "$tree/etc/xdg/xfce4/xfconf/xfce-perchannel-xml"
    install -m644 "$PAYLOAD/panel/xfce4-panel.xml" "$tree/etc/skel/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-panel.xml"
    install -m644 "$PAYLOAD/panel/xfce4-panel.xml" "$tree/etc/xdg/xfce4/xfconf/xfce-perchannel-xml/xfce4-panel.xml"
    mkdir -p "$tree/etc/skel/.config/plank/dock1"
    install -m644 "$PAYLOAD/dock/plank-settings" "$tree/etc/skel/.config/plank/dock1/settings"
    install -m644 "$PAYLOAD/dock/plank.desktop" "$tree/etc/xdg/autostart/plank.desktop"
    install -m644 "$PAYLOAD/terminal/metaos-welcome.sh" "$tree/etc/bash.bashrc.d/metaos.sh"

    # PROV:130-157 imperium app + native surface shell + live wallpaper
    say "tree-only: imperium app + meta-app"
    [ -d "$APPS" ] || die "payload-apps dir missing beside build_iso.sh"
    mkdir -p "$tree/usr/share/metaos/imperium" "$tree/usr/share/metaos/apps"
    cp "$APPS/imperium/index.html" "$tree/usr/share/metaos/imperium/index.html"
    cp -r "$APPS/imperium/js" "$APPS/imperium/vendor" "$tree/usr/share/metaos/imperium/"
    mkdir -p "$tree/usr/share/metaos/server"
    cp "$APPS/server/"*.mjs "$tree/usr/share/metaos/server/"
    cp "$APPS/imperium/styles.css" "$APPS/imperium/icon-180.png" "$APPS/imperium/manifest.webmanifest" "$tree/usr/share/metaos/imperium/" 2>/dev/null || true
    [ -f "$PAYLOAD/apps/metaos-imperium.py" ] || die "imperium payload missing: $PAYLOAD/apps/metaos-imperium.py"
    [ -f "$PAYLOAD/apps/metaos-imperium.desktop" ] || die "imperium payload missing: $PAYLOAD/apps/metaos-imperium.desktop"
    install -m755 "$PAYLOAD/apps/metaos-imperium.py" "$tree/usr/share/metaos/apps/metaos-imperium.py"
    install -m644 "$PAYLOAD/apps/metaos-imperium.desktop" "$tree/usr/share/applications/metaos-imperium.desktop"
    [ -f "$META_APP_SRC" ] || die "meta-app.py missing at $META_APP_SRC (dock surface tiles would vanish)"
    install -m755 "$META_APP_SRC" "$tree/usr/local/bin/meta-app"
    install -m644 "$PAYLOAD/wallpapers/live/meta-live.py" "$tree/usr/share/metaos/apps/meta-live.py" 2>/dev/null || true
    install -m644 "$PAYLOAD/wallpapers/live/metaos-livebg.desktop" "$tree/etc/xdg/autostart/metaos-livebg.desktop" 2>/dev/null || true
    if [ -d "$PAYLOAD/wallpapers/studio-loop" ]; then
        mkdir -p "$tree/usr/share/backgrounds/metaos-studio"
        cp "$PAYLOAD/wallpapers/studio-loop/"*.jpg "$tree/usr/share/backgrounds/metaos-studio/" 2>/dev/null || true
    fi

    # PROV:159-163 agent layer (stage.sh is root-tolerant: ownership checks
    # degrade to notes when uid != 0).
    say "tree-only: agent layer"
    [ -d "$AGENT" ] || die "agent-layer dir missing at repo root"
    sh "$AGENT/stage.sh" "$tree" || die "agent-layer stage failed"

    # Deliberately NOT run here: provision.sh packages + initramfs (chroot,
    # apt, network — need Linux root) and identity scripts (OS-1's; they
    # expect a full base tree). The real build runs them after this payload.
    say "tree-only: skipping packages, initramfs, identity (need base rootfs)"

    local count size
    count=$(find "$tree" -type f | wc -l | tr -d ' ')
    size=$(du -sh "$tree" | awk '{print $1}')
    say "tree-only: $count files, $size in $tree"
    say "tree-only: listing:"
    ( cd "$tree" && find . -type f | sort )
    say "tree-only: done. No ISO mastered (that needs xorriso + a base ISO on Linux)."
    say "tree-only: tree at $tree"
}

# -------------------------------------------------------------------- main
MODE=""
BASE_ISO=""
OUT="$HERE/metaos-1.0-amd64.iso"
CUBIC_ROOT=""
TREE_DIR=""
SUMS_FILE=""
ALLOW_UNVERIFIED=0

while [ $# -gt 0 ]; do
    case "$1" in
        --check) MODE=check ;;
        --tree-only)
            MODE=treeonly
            if [ "${2:-}" != "" ] && [ "${2#-}" = "${2:-}" ]; then
                TREE_DIR="$2"; shift || true
            fi ;;
        --root) MODE=root; CUBIC_ROOT=${2:-}; shift || true ;;
        --iso) MODE=iso; BASE_ISO=${2:-}; shift || true ;;
        --out) OUT=${2:-}; shift || true ;;
        --verify-base) MODE=verify; BASE_ISO=${2:-}; shift || true ;;
        --base-info) MODE=baseinfo; BASE_ISO=${2:-}; shift || true ;;
        --inspect) MODE=inspect; BASE_ISO=${2:-}; shift || true ;;
        --sha256sums) SUMS_FILE=${2:-}; shift || true ;;
        --no-verify-base) ALLOW_UNVERIFIED=1 ;;
        -h|--help) usage 0 ;;
        *) die "unknown argument: $1 (try --help)" ;;
    esac
    shift
done

case "$MODE" in
    check)  check_mode ;;
    treeonly) tree_only_mode "$TREE_DIR" ;;
    root)   root_mode "$CUBIC_ROOT" ;;
    iso)    iso_mode "$BASE_ISO" "$OUT" ;;
    verify) verify_base "$BASE_ISO" "$SUMS_FILE"; say "base verification complete" ;;
    baseinfo) base_info "$BASE_ISO" ;;
    inspect) inspect_mode "$BASE_ISO" ;;
    *)      usage 2 ;;
esac

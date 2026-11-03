#!/bin/sh
# MetaOS 1.0 -- boot + installer lane provisioner.
#
# Installs the Meta payload into an already-unpacked root filesystem:
#   * Plymouth theme  -> /usr/share/plymouth/themes/metaos
#   * Calamares config -> /etc/calamares
#   * in-target hook   -> /usr/local/lib/metaos/meta-branding.sh
#   * live autostart   -> /etc/xdg/autostart/metaos-install.desktop
#   * live splash      -> /etc/plymouth/plymouthd.conf
#
# Used by build_iso.sh --root (Cubic chroot) and --iso (unsquashed casper
# filesystem). Runs on the BUILD HOST as root and touches only <root-dir>.
#
# Claim label: WRITTEN, UNRUN. This Mac has no root Linux tree to provision;
# the first real run is the Linux-host build (README, "Build").
#
# Usage: provision.sh <root-dir> [--no-packages] [--no-initramfs]
set -eu

HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

ROOT=${1:-}
[ -n "$ROOT" ] || { echo "usage: provision.sh <root-dir> [--no-packages] [--no-initramfs]" >&2; exit 2; }
shift || true
WITH_PACKAGES=1
WITH_INITRAMFS=1
for arg in "$@"; do
    case "$arg" in
        --no-packages) WITH_PACKAGES=0 ;;
        --no-initramfs) WITH_INITRAMFS=0 ;;
        *) echo "provision: unknown flag $arg" >&2; exit 2 ;;
    esac
done

[ "$(id -u)" = "0" ] || { echo "provision: needs root (it writes a chroot tree)" >&2; exit 1; }
[ -d "$ROOT/etc" ] && [ -d "$ROOT/usr" ] || {
    echo "provision: $ROOT does not look like a root filesystem (no /etc or /usr)" >&2
    exit 1
}

LOG="$ROOT/var/log/metaos-provision.log"
mkdir -p "$(dirname "$LOG")"
# Everything below is appended to the target's own log, so the built image
# carries the record of how it was provisioned.
exec >>"$LOG" 2>&1
echo "== metaos provision $(date -u '+%Y-%m-%dT%H:%M:%SZ') root=$ROOT packages=$WITH_PACKAGES =="

say() { echo "provision: $*"; }

# ---------------------------------------------------------------- plymouth
say "installing plymouth theme"
rm -rf "$ROOT/usr/share/plymouth/themes/metaos"
mkdir -p "$ROOT/usr/share/plymouth/themes/metaos"
cp -a "$HERE/plymouth/metaos/." "$ROOT/usr/share/plymouth/themes/metaos/"
find "$ROOT/usr/share/plymouth/themes/metaos" -type f -exec chmod 0644 {} +
chmod 0755 "$ROOT/usr/share/plymouth/themes/metaos"
mkdir -p "$ROOT/etc/plymouth"
cat > "$ROOT/etc/plymouth/plymouthd.conf" <<'PLYMOUTH'
[Daemon]
Theme=metaos
ShowDelay=0
DeviceTimeout=8
PLYMOUTH

# --------------------------------------------------------------- calamares
say "installing calamares config"
if [ -f "$ROOT/etc/calamares/settings.conf" ] && [ ! -f "$ROOT/etc/calamares/settings.conf.base-flavour" ]; then
    cp -a "$ROOT/etc/calamares/settings.conf" "$ROOT/etc/calamares/settings.conf.base-flavour"
fi
rm -rf "$ROOT/etc/calamares/modules" "$ROOT/etc/calamares/branding/metaos"
mkdir -p "$ROOT/etc/calamares/modules" "$ROOT/etc/calamares/branding/metaos"
cp -a "$HERE/calamares/settings.conf" "$ROOT/etc/calamares/settings.conf"
cp -a "$HERE/calamares/modules/." "$ROOT/etc/calamares/modules/"
cp -a "$HERE/calamares/branding/metaos/." "$ROOT/etc/calamares/branding/metaos/"
find "$ROOT/etc/calamares" -type f -exec chmod 0644 {} +

# ------------------------------------------------------------- target hook
say "installing in-target branding hook"
mkdir -p "$ROOT/usr/local/lib/metaos"
cp -a "$HERE/calamares/meta-branding.sh" "$ROOT/usr/local/lib/metaos/meta-branding.sh"
chmod 0755 "$ROOT/usr/local/lib/metaos/meta-branding.sh"

# ------------------------------------------------------------- live extras
say "installing live-session autostart + icon"
mkdir -p "$ROOT/usr/share/metaos"
cp -a "$HERE/calamares/branding/metaos/productIcon.png" "$ROOT/usr/share/metaos/installer.png"
mkdir -p "$ROOT/etc/xdg/autostart"
cat > "$ROOT/etc/xdg/autostart/metaos-install.desktop" <<'DESKTOP'
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
chmod 0644 "$ROOT/etc/xdg/autostart/metaos-install.desktop"

# ------------------------------------------------- welcome + theme
say "installing welcome app + Meta theme payload (frozen vendor of opencode1/metaos-1.0)"
PAYLOAD="$HERE/payload-theme"
mkdir -p "$ROOT/usr/share/metaos/apps" "$ROOT/usr/share/applications" "$ROOT/usr/share/backgrounds" "$ROOT/usr/share/plank/themes" "$ROOT/usr/share/themes" "$ROOT/etc/lightdm" "$ROOT/etc/bash.bashrc.d"
install -m755 "$PAYLOAD/apps/metaos-welcome.py" "$ROOT/usr/share/metaos/apps/metaos-welcome.py"
install -m644 "$PAYLOAD/apps/metaos-welcome.desktop" "$ROOT/usr/share/applications/metaos-welcome.desktop"
install -m644 "$PAYLOAD/apps/metaos-welcome.desktop" "$ROOT/etc/xdg/autostart/metaos-welcome.desktop"
install -m644 "$PAYLOAD/greeter/lightdm-gtk-greeter.conf" "$ROOT/etc/lightdm/lightdm-gtk-greeter.conf"
install -m644 "$PAYLOAD/wallpapers/meta-ascii.png" "$ROOT/usr/share/backgrounds/meta-ascii.png" 2>/dev/null || true
install -m644 "$PAYLOAD/wallpapers/meta-rays.png" "$ROOT/usr/share/backgrounds/meta-rays.png" 2>/dev/null || true
install -m644 "$PAYLOAD/wallpapers/meta-dusk.png" "$ROOT/usr/share/backgrounds/meta-dusk.png" 2>/dev/null || true
install -m644 "$PAYLOAD/wallpapers/meta-dawn.png" "$ROOT/usr/share/backgrounds/meta-dawn.png" 2>/dev/null || true
cp -r "$PAYLOAD/dock/." "$ROOT/usr/share/plank/themes/" 2>/dev/null || true
cp -r "$PAYLOAD/gtk/." "$ROOT/usr/share/themes/" 2>/dev/null || { mkdir -p "$ROOT/usr/share/themes/MetaOS/gtk-3.0"; install -m644 "$PAYLOAD/gtk/gtk.css" "$ROOT/usr/share/themes/MetaOS/gtk-3.0/gtk.css"; }
install -m644 "$PAYLOAD/terminal/metaos-welcome.sh" "$ROOT/etc/bash.bashrc.d/metaos.sh"
gate_payload_welcome=1

# ------------------------------------------------- imperium app (cooked in, no hosting)
say "installing Imperium app: local web UI + localhost-only backend"
REPO_ROOT="$(CDPATH= cd -- "$HERE/../.." && pwd)"
mkdir -p "$ROOT/usr/share/metaos/imperium" "$ROOT/usr/share/metaos/server"
cp "$REPO_ROOT/imperium/index.html" "$ROOT/usr/share/metaos/imperium/index.html"
cp -r "$REPO_ROOT/js" "$ROOT/usr/share/metaos/imperium/js"
cp -r "$REPO_ROOT/vendor" "$ROOT/usr/share/metaos/imperium/vendor"
cp "$REPO_ROOT/styles.css" "$ROOT/usr/share/metaos/imperium/styles.css"
cp "$REPO_ROOT/icon-180.png" "$ROOT/usr/share/metaos/imperium/icon-180.png"
cp "$REPO_ROOT/server/"*.mjs "$ROOT/usr/share/metaos/server/"
install -m755 "$PAYLOAD/apps/metaos-imperium.py" "$ROOT/usr/share/metaos/apps/metaos-imperium.py"
install -m644 "$PAYLOAD/apps/metaos-imperium.desktop" "$ROOT/usr/share/applications/metaos-imperium.desktop"
# NOTE: backend binds 127.0.0.1 only (server.mjs); wrapper spawns it per-login.


# ---------------------------------------------------------------- packages
if [ "$WITH_PACKAGES" = "1" ]; then
    if chroot "$ROOT" sh -c 'command -v calamares >/dev/null 2>&1'; then
        say "calamares already present in the chroot; no packages needed"
    else
        say "installing calamares + plymouth into the chroot (needs network)"
        if [ ! -f "$ROOT/etc/resolv.conf" ]; then
            say "WARN: $ROOT/etc/resolv.conf missing; copy the host's before building"
        fi
        chroot "$ROOT" apt-get update
        DEBIAN_FRONTEND=noninteractive chroot "$ROOT" \
            apt-get install -y --no-install-recommends calamares plymouth plymouth-themes
    fi
else
    say "packages skipped (--no-packages); calamares must already be in the chroot"
fi

# --------------------------------------------------------------- initramfs
if [ "$WITH_INITRAMFS" = "1" ]; then
    if chroot "$ROOT" sh -c 'command -v plymouth-set-default-theme >/dev/null 2>&1'; then
        say "plymouth-set-default-theme -R metaos (rebuilds the live initramfs)"
        chroot "$ROOT" plymouth-set-default-theme -R metaos || {
            say "WARN: plymouth-set-default-theme -R failed; live boot keeps the base splash"
        }
    else
        say "WARN: plymouth-set-default-theme not in chroot; live splash not rebuilt"
    fi
else
    say "initramfs rebuild skipped (--no-initramfs)"
fi

say "provision complete: $ROOT"
say "next: build_iso.sh --root mode -> press Generate in Cubic; --iso mode rebuilds automatically"
exit 0

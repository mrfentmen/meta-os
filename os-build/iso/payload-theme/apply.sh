#!/bin/sh
# MetaOS theme + identity installer (lane D).
# Usage: ./apply.sh [ROOT]   (default ROOT=/: the running system)
# Lane C calls it as: os-build/iso/payload-theme/apply.sh /mnt
#
# Installs, with absolute destination paths only: greeter configs, backgrounds,
# plymouth theme (32-frame ribbon), GRUB theme staging, GTK + xfwm4 + index,
# panel xml, plank theme/settings/autostart, terminal hook, the metaos icon
# set + index.theme, the 17 dock launchers, and the identity files
# (os-release, hostname, issue, ...).
#
# Refuses to run when any referenced source asset is missing (preflight
# counts are exact: 32 plymouth frames, 20 icons, 12 dock launchers).
# Refuses when neither Inter nor Ubuntu Mono is present on the target.
# Never touches autologin (50-metaos.conf / lightdm.conf) or meta-live.py.
set -eu

HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
ROOT="${1:-/}"
[ -d "$ROOT/etc" ] && [ -d "$ROOT/usr" ] || {
  echo "apply: $ROOT is not a root filesystem (no /etc or /usr)" >&2
  exit 1
}

fail=0
need() { # need <source-path> — preflight gate, counts failures, never silences
  if [ -f "$1" ]; then :; else echo "apply-GATE-FAIL: missing source: $1" >&2; fail=$((fail + 1)); fi
}

# ---------------------------------------------------------------- preflight
for f in \
  greeter/lightdm-gtk-greeter.conf greeter/unity-greeter.conf greeter/10-metaos-live.conf \
  wallpapers/meta-ascii.png wallpapers/meta-rays.png wallpapers/meta-dusk.png wallpapers/meta-dawn.png \
  splash/metaos.plymouth splash/metaos.script splash/background.png splash/meta-m.png splash/progress.png \
  grub/theme.txt grub/background.png grub/mark.png \
  gtk/gtk.css gtk/index.theme \
  xfwm4/themerc xfwm4/xfwm4.xml xfwm4/close-active.svg xfwm4/hide-active.svg xfwm4/maximize-active.svg \
  panel/xfce4-panel.xml \
  dock/dock.theme dock/plank-settings dock/plank.desktop \
  terminal/metaos-welcome.sh terminal/metaos-terminal-profile.txt \
  icons/metaos.index.theme \
  apps/metaos-welcome.py apps/metaos-welcome.desktop \
  apps/metaos-imperium.py apps/metaos-imperium.desktop \
  identity/os-release identity/lsb-release identity/hostname identity/issue \
  identity/issue.net identity/motd identity/00-header \
  ; do need "$HERE/$f"; done

nframes=$(ls "$HERE"/splash/frames/frame-*.png 2>/dev/null | wc -l)
[ "$nframes" -eq 32 ] || { echo "apply-GATE-FAIL: want 32 splash frames, found $nframes" >&2; fail=$((fail + 1)); }
nicons=$(ls "$HERE"/icons/metaos/*.png 2>/dev/null | wc -l)
# A FLOOR, not an exact match. The count was pinned at 20 and the tree grew to
# 26, so this gate refused every install with "want 20 icons, found 26" — the
# theme could not reach the image at all, which is how the guest ended up on
# a half-applied desktop. 20 is still the floor: a half-copied icon set fails.
[ "$nicons" -ge 20 ] || { echo "apply-GATE-FAIL: want at least 20 icons, found $nicons" >&2; fail=$((fail + 1)); }
ndock=$(ls "$HERE"/apps/dock/*.desktop 2>/dev/null | wc -l)
[ "$ndock" -ge 12 ] || { echo "apply-GATE-FAIL: want at least 12 dock launchers, found $ndock" >&2; fail=$((fail + 1)); }

if [ "$fail" -ne 0 ]; then
  echo "apply: $fail missing asset(s); refusing to install a half theme" >&2
  exit 1
fi

put() { # put <src> <abspath-dest> [mode]
  src="$1"; dst="$ROOT$2"; mode="${3:-644}"
  mkdir -p "$(dirname "$dst")"
  install -m"$mode" "$src" "$dst"
}

echo "apply: installing MetaOS theme into $ROOT"

# ------------------------------------------------------------- greeter
put "$HERE/greeter/lightdm-gtk-greeter.conf" /etc/lightdm/lightdm-gtk-greeter.conf
put "$HERE/greeter/unity-greeter.conf" /etc/lightdm/unity-greeter.conf
put "$HERE/greeter/10-metaos-live.conf" /etc/lightdm/lightdm.conf.d/10-metaos-live.conf

# --------------------------------------------------------- backgrounds
put "$HERE/wallpapers/meta-ascii.png" /usr/share/backgrounds/meta-ascii.png
put "$HERE/wallpapers/meta-rays.png" /usr/share/backgrounds/meta-rays.png
put "$HERE/wallpapers/meta-dusk.png" /usr/share/backgrounds/meta-dusk.png
put "$HERE/wallpapers/meta-dawn.png" /usr/share/backgrounds/meta-dawn.png
put "$HERE/splash/meta-m.png" /usr/share/backgrounds/meta-m.png

# ------------------------------------------------------------- plymouth
put "$HERE/splash/metaos.plymouth" /usr/share/plymouth/themes/metaos/metaos.plymouth
put "$HERE/splash/metaos.script" /usr/share/plymouth/themes/metaos/metaos.script
put "$HERE/splash/background.png" /usr/share/plymouth/themes/metaos/background.png
put "$HERE/splash/meta-m.png" /usr/share/plymouth/themes/metaos/meta-m.png
put "$HERE/splash/progress.png" /usr/share/plymouth/themes/metaos/progress.png
for f in "$HERE"/splash/frames/frame-*.png; do
  put "$f" "/usr/share/plymouth/themes/metaos/frames/$(basename "$f")"
done
mkdir -p "$ROOT/etc/plymouth"
printf '[Daemon]\nTheme=metaos\nShowDelay=0\nDeviceTimeout=8\n' > "$ROOT/etc/plymouth/plymouthd.conf"
chmod 0644 "$ROOT/etc/plymouth/plymouthd.conf"

# ---------------------------------------------------- grub theme (staging; lane C wires GRUB_THEME)
put "$HERE/grub/theme.txt" /boot/grub/themes/metaos/theme.txt
put "$HERE/grub/background.png" /boot/grub/themes/metaos/background.png
put "$HERE/grub/mark.png" /boot/grub/themes/metaos/mark.png

# ------------------------------------------------------------- gtk/xfwm4
put "$HERE/gtk/gtk.css" /usr/share/themes/MetaOS/gtk-3.0/gtk.css
put "$HERE/gtk/index.theme" /usr/share/themes/MetaOS/index.theme
put "$HERE/xfwm4/themerc" /usr/share/themes/MetaOS/xfwm4/themerc
# The button art. Without it xfwm4 draws an EMPTY titlebar no matter what the
# layout says — the theme dir used to ship themerc and nothing else, which is
# why windows had no x, no - and no +. 15 svgs: 3 buttons x 5 states.
nbuttons=$(ls "$HERE"/xfwm4/*-*.svg 2>/dev/null | wc -l)
npngs=$(ls "$HERE"/xfwm4/*-*.png 2>/dev/null | wc -l)
# Both formats on purpose: SVG is crisp at any scale but only loads when the
# rsvg GdkPixbuf loader is installed; PNG always loads. An image without that
# loader and an SVG-only theme draws an empty titlebar — the exact bug this
# block exists to prevent.
if [ "$nbuttons" -eq 15 ] && [ "$npngs" -eq 15 ]; then
  for f in "$HERE"/xfwm4/*-*.svg "$HERE"/xfwm4/*-*.png; do
    put "$f" "/usr/share/themes/MetaOS/xfwm4/$(basename "$f")"
  done
  echo "apply: 15 svg + 15 png window-button images -> /usr/share/themes/MetaOS/xfwm4"
else
  echo "apply: refusing to ship an empty titlebar — want 15 svgs + 15 pngs, found $nbuttons + $npngs" >&2
  exit 1
fi
# xfconf beats themerc, so the channel file is the one that decides which
# buttons exist. Generated from the same token as themerc, so they agree.
put "$HERE/xfwm4/xfwm4.xml" /etc/xdg/xfce4/xfconf/xfce-perchannel-xml/xfwm4.xml
put "$HERE/xfwm4/xfwm4.xml" /etc/skel/.config/xfce4/xfconf/xfce-perchannel-xml/xfwm4.xml

# ----------------------------------------------------------------- panel
put "$HERE/panel/xfce4-panel.xml" /etc/skel/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-panel.xml
put "$HERE/panel/xfce4-panel.xml" /etc/xdg/xfce4/xfconf/xfce-perchannel-xml/xfce4-panel.xml

# ------------------------------------------------------------------ dock
put "$HERE/dock/dock.theme" /usr/share/plank/themes/MetaOS/dock.theme
put "$HERE/dock/plank-settings" /etc/skel/.config/plank/dock1/settings
put "$HERE/dock/plank.desktop" /etc/xdg/autostart/plank.desktop

# -------------------------------------------------------------- terminal
put "$HERE/terminal/metaos-welcome.sh" /etc/bash.bashrc.d/metaos.sh
put "$HERE/terminal/metaos-terminal-profile.txt" /usr/share/doc/metaos/terminal-profile.txt

# ----------------------------------------------------------------- icons
put "$HERE/icons/metaos.index.theme" /usr/share/icons/metaos/index.theme
for f in "$HERE"/icons/metaos/*.png; do
  put "$f" "/usr/share/icons/metaos/128x128/apps/$(basename "$f")"
done

# ------------------------------------------------------------------ apps
put "$HERE/apps/metaos-welcome.py" /usr/share/metaos/apps/metaos-welcome.py 755
put "$HERE/apps/metaos-welcome.desktop" /usr/share/applications/metaos-welcome.desktop
put "$HERE/apps/metaos-welcome.desktop" /etc/xdg/autostart/metaos-welcome.desktop
put "$HERE/apps/metaos-imperium.py" /usr/share/metaos/apps/metaos-imperium.py 755
put "$HERE/apps/metaos-imperium.desktop" /usr/share/applications/metaos-imperium.desktop
for f in "$HERE"/apps/dock/*.desktop; do
  put "$f" "/usr/share/applications/$(basename "$f")"
done

# -------------------------------------------------------------- identity
# NOTE: /etc/os-release is a symlink to ../usr/lib/os-release on Ubuntu.
# Write through it (like meta-branding does) instead of replacing the link.
if [ ! -f "$ROOT/etc/os-release.base-flavour" ]; then
  cat "$ROOT/etc/os-release" > "$ROOT/etc/os-release.base-flavour"
fi
cat "$HERE/identity/os-release" > "$ROOT/etc/os-release"
chmod 0644 "$ROOT/etc/os-release"
put "$HERE/identity/lsb-release" /etc/lsb-release
printf 'metaos\n' > "$ROOT/etc/hostname"
chmod 0644 "$ROOT/etc/hostname"
if grep -q '^127\.0\.1\.1' "$ROOT/etc/hosts" 2>/dev/null; then
  sed -i 's/^127\.0\.1\.1.*/127.0.1.1\tmetaos/' "$ROOT/etc/hosts"
else
  printf '127.0.1.1\tmetaos\n' >> "$ROOT/etc/hosts"
fi
put "$HERE/identity/issue" /etc/issue
put "$HERE/identity/issue.net" /etc/issue.net
put "$HERE/identity/motd" /etc/motd
put "$HERE/identity/00-header" /etc/update-motd.d/00-header 755

# ----------------------------------------------------------------- fonts
have_inter=0
have_mono=0
if ls "$ROOT"/usr/share/fonts/opentype/inter/Inter-* >/dev/null 2>&1 || \
   ls "$ROOT"/usr/share/fonts/truetype/inter/Inter-* >/dev/null 2>&1; then have_inter=1; fi
if ls "$ROOT"/usr/share/fonts/truetype/ubuntu/UbuntuMono* >/dev/null 2>&1; then have_mono=1; fi
if [ "$have_inter" -eq 0 ] || [ "$have_mono" -eq 0 ]; then
  if [ "$ROOT" = "/" ] && command -v apt-get >/dev/null 2>&1; then
    echo "apply: fonts missing (inter=$have_inter mono=$have_mono); installing via apt"
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends fonts-inter fonts-ubuntu
    ls /usr/share/fonts/opentype/inter/Inter-* >/dev/null 2>&1 || ls /usr/share/fonts/truetype/inter/Inter-* >/dev/null 2>&1 || { echo "apply-GATE-FAIL: Inter still absent after apt" >&2; exit 1; }
    ls /usr/share/fonts/truetype/ubuntu/UbuntuMono* >/dev/null 2>&1 || { echo "apply-GATE-FAIL: Ubuntu Mono still absent after apt" >&2; exit 1; }
  else
    echo "apply-GATE-FAIL: fonts missing on target (inter=$have_inter mono=$have_mono); install fonts-inter + fonts-ubuntu, then re-run" >&2
    exit 1
  fi
fi

# -------------------------------------------- plymouth default (live root only)
if [ "$ROOT" = "/" ] && command -v update-alternatives >/dev/null 2>&1; then
  update-alternatives --install /usr/share/plymouth/themes/default.plymouth default.plymouth /usr/share/plymouth/themes/metaos/metaos.plymouth 100
  update-alternatives --set default.plymouth /usr/share/plymouth/themes/metaos/metaos.plymouth
  if command -v update-initramfs >/dev/null 2>&1; then
    update-initramfs -u
  else
    echo "apply: update-initramfs absent; initramfs rebuild is lane C's (ISO build)"
  fi
else
  echo "apply: plymouth alternative not set (ROOT=$ROOT); lane C runs plymouth-set-default-theme -R at ISO build"
fi

echo "apply: done -> $ROOT (autologin untouched; per-user: panel xml -> ~/.config/xfce4/xfconf/xfce-perchannel-xml/)"

#!/bin/sh
# Apply MetaOS theme stack on a running base system (or Cubic chroot).
# Usage: ./apply.sh  (run as root for /etc + /usr/share targets)
set -e
HERE="$(dirname "$0")"
install -m644 "$HERE/greeter/lightdm-gtk-greeter.conf" /etc/lightdm/lightdm-gtk-greeter.conf
install -m644 "$HERE/wallpapers/meta-rays.png" /usr/share/backgrounds/meta-rays.png
install -m644 "$HERE/wallpapers/meta-dusk.png" /usr/share/backgrounds/meta-dusk.png
install -m644 "$HERE/splash/meta-m.png" /usr/share/backgrounds/meta-m.png
mkdir -p /usr/share/plymouth/themes/metaos
install -m644 "$HERE/splash/metaos.plymouth" "$HERE/splash/metaos.script" "$HERE/splash/background.png" "$HERE/splash/meta-m.png" "$HERE/splash/progress.png" /usr/share/plymouth/themes/metaos/
mkdir -p /usr/share/plank/themes/MetaOS
install -m644 "$HERE/dock/dock.theme" /usr/share/plank/themes/MetaOS/dock.theme
mkdir -p /usr/share/themes/MetaOS/gtk-3.0
install -m644 "$HERE/gtk/gtk.css" /usr/share/themes/MetaOS/gtk-3.0/gtk.css
mkdir -p /etc/bash.bashrc.d
install -m644 "$HERE/terminal/metaos-welcome.sh" /etc/bash.bashrc.d/metaos.sh
if command -v update-alternatives >/dev/null 2>&1 && command -v update-initramfs >/dev/null 2>&1; then
  update-alternatives --install /usr/share/plymouth/themes/default.plymouth default.plymouth /usr/share/plymouth/themes/metaos/metaos.plymouth 100
  update-alternatives --set default.plymouth /usr/share/plymouth/themes/metaos/metaos.plymouth
  update-initramfs -u
else
  echo "plymouth activation skipped (no update-alternatives/update-initramfs); see splash/INSTALL.md"
fi
echo "system files installed; per-user: panel xml -> ~/.config/xfce4/xfconf/xfce-perchannel-xml/"

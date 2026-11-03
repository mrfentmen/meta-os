#!/bin/sh
# Apply MetaOS theme stack on a running Xubuntu system (or Cubic chroot).
# Usage: ./apply.sh  (run as root for /etc + /usr/share targets)
set -e
HERE="$(dirname "$0")"
install -m644 "$HERE/greeter/slick-greeter.conf" /etc/lightdm/slick-greeter.conf
install -m644 "$HERE/wallpapers/meta-rays.png" /usr/share/backgrounds/meta-rays.png
install -m644 "$HERE/wallpapers/meta-dusk.png" /usr/share/backgrounds/meta-dusk.png
mkdir -p /usr/share/plank/themes/MetaOS
install -m644 "$HERE/dock/dock.theme" /usr/share/plank/themes/MetaOS/dock.theme
mkdir -p /usr/share/themes/MetaOS/gtk-3.0
install -m644 "$HERE/gtk/gtk.css" /usr/share/themes/MetaOS/gtk-3.0/gtk.css
mkdir -p /etc/bash.bashrc.d
install -m644 "$HERE/terminal/metaos-welcome.sh" /etc/bash.bashrc.d/metaos.sh
echo "system files installed; per-user: panel xml -> ~/.config/xfce4/xfconf/xfce-perchannel-xml/"

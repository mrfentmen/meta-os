#!/bin/sh
# MetaOS 1.0 de-Xubuntify step. Run INSIDE the remaster chroot (Cubic
# customisation phase or build_iso.sh --root), after Hana's packages and
# OC1's metaos-theme/apply.sh. Identity only: renames what the user SEES
# as the OS. It does not remove Xfce or any functional package.
# Idempotent: safe to run twice. Fails loudly on a missing target.
set -eu
HERE=$(dirname "$0")

echo "[dexubuntu] hostname + hosts"
echo "metaos" > /etc/hostname
if grep -q '^127\.0\.1\.1' /etc/hosts; then
  sed -i 's/^127\.0\.1\.1.*/127.0.1.1\tmetaos/' /etc/hosts
else
  printf '127.0.1.1\tmetaos\n' >> /etc/hosts
fi

echo "[dexubuntu] os-release / lsb-release / issue"
cp "$HERE/identity/os-release" /etc/os-release
cp "$HERE/identity/lsb-release" /etc/lsb-release
printf 'Meta OS 1.0 (Ribbon) \\n \\l\n' > /etc/issue
printf 'Meta OS 1.0 (Ribbon)\n' > /etc/issue.net || true

echo "[dexubuntu] motd"
if [ -d /etc/update-motd.d ]; then
  printf '#!/bin/sh\necho "Meta OS 1.0 (Ribbon)"\n' > /etc/update-motd.d/00-header
  chmod +x /etc/update-motd.d/00-header
fi

echo "[dexubuntu] purge xubuntu identity packages (branding only)"
# xubuntu-default-settings ships the Xubuntu session defaults + branding;
# xubuntu-wallpapers / xubuntu-artwork are pure identity assets. The Xfce
# desktop itself (xfce4-*) is NOT touched. || true: a package already
# absent is fine, the verify step is what proves the end state.
export DEBIAN_FRONTEND=noninteractive
apt-get purge -y xubuntu-default-settings xubuntu-wallpapers xubuntu-artwork xubuntu-docs 2>/dev/null || true
# Belt and braces: if a purge was skipped or partial, the identity asset
# dirs still go. These paths belong to the purged packages only.
rm -rf /usr/share/backgrounds/xubuntu /usr/share/xubuntu-docs /usr/share/xubuntu-artwork 2>/dev/null || true

echo "[dexubuntu] default session wallpaper + greeter background"
# OC1's theme owns the artwork; point the Xfce defaults at it when present.
WALL=/usr/share/backgrounds/meta-dusk.png
if [ -f "$WALL" ]; then
  mkdir -p /etc/xdg/xfce4/xfconf/xfce-perchannel-xml
  cat > /etc/xdg/xfce4/xfconf/xfce-perchannel-xml/xfce4-desktop.xml <<XML
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfce4-desktop" version="1.0">
  <property name="backdrop" type="empty">
    <property name="screen0" type="empty">
      <property name="monitor0" type="empty">
        <property name="workspace0" type="empty">
          <property name="last-image" type="string" value="$WALL"/>
        </property>
      </property>
    </property>
  </property>
</channel>
XML
fi

echo "[dexubuntu] plymouth default theme name (artwork is Buffy/OC1 lane)"
if command -v update-alternatives >/dev/null 2>&1; then
  if update-alternatives --list default.plymouth >/dev/null 2>&1; then
    for alt in $(update-alternatives --list default.plymouth); do
      case "$alt" in *metaos*) update-alternatives --set default.plymouth "$alt" ;; esac
    done
  fi
fi

echo "[dexubuntu] done"

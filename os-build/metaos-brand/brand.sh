#!/bin/sh
# metaos-brand — rewrite a stock Xubuntu rootfs into Meta OS.
#
# Usage:
#   metaos-brand --root /mnt          apply branding into a mounted rootfs
#   metaos-brand --verify /mnt        check the end state, read-only
#
# Idempotent. Runs without chroot except for the two optional steps that
# need apt/update-alternatives. Every visible identity string it owns is
# listed in IDENTITY below; nothing functional is removed.

set -eu

ROOT=""
MODE="apply"
case "${1:-}" in
  --root)   ROOT="${2:?--root needs a path}"; MODE="apply" ;;
  --verify) ROOT="${2:?--verify needs a path}"; MODE="verify" ;;
  *) echo "usage: $0 --root DIR | --verify DIR" >&2; exit 2 ;;
esac

[ -d "$ROOT" ] || { echo "no such root: $ROOT" >&2; exit 2; }

WP=/usr/share/backgrounds/meta-wallpaper.png
NAME="Meta OS"
VERSION="1.0"

fail=0
check() { # check <label> <test-cmd...>
  label="$1"; shift
  if eval "$@" >/dev/null 2>&1; then
    echo "PASS $label"
  else
    echo "FAIL $label"; fail=$((fail+1))
  fi
}

# ---------------------------------------------------------------- verify
if [ "$MODE" = "verify" ]; then
  check "os-release NAME is Meta"        "grep -q '^NAME=\"\?${NAME}\"\?' '$ROOT/etc/os-release'"
  check "os-release says $VERSION"        "grep -q '$VERSION' '$ROOT/etc/os-release'"
  check "no xubuntu in os-release"        "! grep -qi xubuntu '$ROOT/etc/os-release'"
  check "lsb-release is Meta"             "grep -qi 'meta' '$ROOT/etc/lsb-release'"
  check "hostname is metaos"              "grep -qx metaos '$ROOT/etc/hostname'"
  check "issue banner is Meta"            "grep -qi 'meta' '$ROOT/etc/issue'"
  check "Meta wallpaper installed"        "test -f '$ROOT$WP'"
  check "wallpaper fills (zoomed)"        "grep -q 'value=\"5\"' '$ROOT/etc/xdg/xfce4/xfconf/xfce-perchannel-xml/xfce4-desktop.xml'"
  check "MetaOS gtk theme"                "test -d '$ROOT/usr/share/themes/MetaOS'"
  check "MetaOS session entry"            "test -f '$ROOT/usr/share/xsessions/metaos.desktop'"
  check "Meta launchers present"          "test -f '$ROOT/usr/share/applications/meta-terminal.desktop'"
  check "runtime wallpaper fixer"         "test -x '$ROOT/usr/local/bin/meta-desktop-fix'"
  echo "----"
  echo "brand verify: $fail failure(s)"
  exit $([ "$fail" -eq 0 ] && echo 0 || echo 1)
fi

# ---------------------------------------------------------------- apply
say() { echo "[brand] $*"; }

say "identity files"
cat > "$ROOT/etc/os-release" <<EOF
PRETTY_NAME="$NAME $VERSION"
NAME="$NAME"
VERSION="$VERSION"
VERSION_ID="$VERSION"
ID=metaos
ID_LIKE=ubuntu debian
HOME_URL="https://metaos.local"
SUPPORT_URL="https://metaos.local/support"
BUG_REPORT_URL="https://metaos.local/bugs"
EOF
cat > "$ROOT/etc/lsb-release" <<EOF
DISTRIB_ID=$NAME
DISTRIB_RELEASE=$VERSION
DISTRIB_CODENAME=meta
DISTRIB_DESCRIPTION="$NAME $VERSION"
EOF
printf 'metaos\n' > "$ROOT/etc/hostname"
if grep -q '^127\.0\.1\.1' "$ROOT/etc/hosts" 2>/dev/null; then
  sed -i 's/^127\.0\.1\.1.*/127.0.1.1\tmetaos/' "$ROOT/etc/hosts"
else
  printf '127.0.1.1\tmetaos\n' >> "$ROOT/etc/hosts"
fi
printf '%s %s \\n \\l\n\n' "$NAME" "$VERSION" > "$ROOT/etc/issue"
printf '%s %s\n' "$NAME" "$VERSION"        > "$ROOT/etc/issue.net"
printf '%s %s\n' "$NAME" "$VERSION"        > "$ROOT/etc/motd"
mkdir -p "$ROOT/etc/update-motd.d"
printf '#!/bin/sh\necho "%s %s"\n' "$NAME" "$VERSION" > "$ROOT/etc/update-motd.d/00-header"
chmod +x "$ROOT/etc/update-motd.d/00-header"

say "boot menu distributor"
if [ -f "$ROOT/etc/default/grub" ]; then
  if grep -q '^GRUB_DISTRIBUTOR' "$ROOT/etc/default/grub"; then
    sed -i "s/^GRUB_DISTRIBUTOR=.*/GRUB_DISTRIBUTOR=\"$NAME\"/" "$ROOT/etc/default/grub"
  else
    printf 'GRUB_DISTRIBUTOR="%s"\n' "$NAME" >> "$ROOT/etc/default/grub"
  fi
fi

say "shell prompt"
cat > "$ROOT/etc/profile.d/00-metaos.sh" <<'EOF'
[ -n "$PS1" ] && PS1='\[\e[38;5;39m\]\u@metaos\[\e[0m\]:\[\e[38;5;245m\]\w\[\e[0m\]\$ '
export PS1
EOF

say "session name"
if [ -f "$ROOT/usr/share/xsessions/xfce.desktop" ]; then
  sed 's/^Name=.*/Name=Meta OS Desktop/; s/^Comment=.*/Comment=The Meta OS desktop/' \
    "$ROOT/usr/share/xsessions/xfce.desktop" > "$ROOT/usr/share/xsessions/metaos.desktop"
fi
mkdir -p "$ROOT/etc/lightdm/lightdm.conf.d"
cat > "$ROOT/etc/lightdm/lightdm.conf.d/50-metaos.conf" <<'EOF'
[Seat:*]
autologin-user=ubuntu
autologin-user-timeout=0
user-session=metaos
greeter-session=unity-greeter
EOF

say "login screen paints the Meta wallpaper"
mkdir -p "$ROOT/etc/lightdm"
cat > "$ROOT/etc/lightdm/unity-greeter.conf" <<EOF
[greeter]
background=$WP
logo=/usr/share/pixmaps/meta-blank.png
draw-user-backgrounds=false
show-hostname=true
EOF

say "desktop wallpaper on every monitor name (zoomed)"
mkdir -p "$ROOT/etc/xdg/xfce4/xfconf/xfce-perchannel-xml"
{
  echo '<?xml version="1.0" encoding="UTF-8"?>'
  echo '<channel name="xfce4-desktop" version="1.0">'
  echo '  <property name="backdrop" type="empty">'
  echo '    <property name="screen0" type="empty">'
  for m in monitorVirtual-1 monitor0 monitorVirt-1 monitorHDMI-1 monitorLVDS-1; do
    echo "      <property name=\"$m\" type=\"empty\">"
    echo '        <property name="workspace0" type="empty">'
    echo "          <property name=\"last-image\" type=\"string\" value=\"$WP\"/>"
    echo '          <property name="image-style" type="int" value="5"/>'
    echo '        </property>'
    echo '      </property>'
  done
  echo '    </property>'
  echo '  </property>'
  echo '</channel>'
} > "$ROOT/etc/xdg/xfce4/xfconf/xfce-perchannel-xml/xfce4-desktop.xml"

say "theme + window manager"
cat > "$ROOT/etc/xdg/xfce4/xfconf/xfce-perchannel-xml/xsettings.xml" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xsettings" version="1.0">
  <property name="Net" type="empty">
    <property name="ThemeName" type="string" value="MetaOS"/>
    <property name="IconThemeName" type="string" value="hicolor"/>
  </property>
  <property name="Xft" type="empty">
    <property name="Antialias" type="int" value="1"/>
  </property>
</channel>
EOF
cat > "$ROOT/etc/xdg/xfce4/xfconf/xfce-perchannel-xml/xfwm4.xml" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfwm4" version="1.0">
  <property name="general" type="empty">
    <property name="theme" type="string" value="MetaOS"/>
    <property name="title_alignment" type="string" value="center"/>
  </property>
</channel>
EOF

say "visible Ubuntu/Xubuntu strings in launchers"
for f in "$ROOT"/usr/share/applications/*.desktop; do
  [ -f "$f" ] || continue
  sed -i 's/Xubuntu/Meta OS/g; s/Ubuntu/Meta OS/g' "$f"
done

say "remove Xubuntu identity packages if apt works here"
if [ -x "$ROOT/usr/bin/apt-get" ] && [ -d "$ROOT/var/lib/dpkg" ]; then
  chroot "$ROOT" env DEBIAN_FRONTEND=noninteractive apt-get purge -y \
    xubuntu-default-settings xubuntu-wallpapers xubuntu-artwork xubuntu-docs \
    >/dev/null 2>&1 || true
fi
rm -rf "$ROOT/usr/share/backgrounds/xubuntu" "$ROOT/usr/share/xubuntu-docs" \
       "$ROOT/usr/share/xubuntu-artwork" 2>/dev/null || true

say "runtime fixer (kills leftover greeter, repaints wallpaper)"
mkdir -p "$ROOT/usr/local/bin" "$ROOT/etc/xdg/autostart"
install -m755 "$(dirname "$0")/meta-desktop-fix" "$ROOT/usr/local/bin/meta-desktop-fix"
cat > "$ROOT/etc/xdg/autostart/meta-desktop-fix.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=Meta Desktop Fix
Exec=/usr/local/bin/meta-desktop-fix
Terminal=false
NoDisplay=true
X-GNOME-Autostart-enabled=true
EOF

say "done"

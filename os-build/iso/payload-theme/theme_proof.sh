#!/bin/sh
# theme_proof.sh — lane D acceptance for the MetaOS identity stack.
# Usage: theme_proof.sh [ROOT]   (default ROOT=/)
# Asserts, per row: asset exists in the image, icon resolves, unit/config
# references an absolute path, no forbidden brand string on visible surfaces.
# Prints PASS/FAIL per row and exits 1 on any miss. No silenced failures.
set -eu
ROOT="${1:-/}"
THEME="$ROOT/usr/share/plymouth/themes/metaos"
fail=0
pass=0

ok() { echo "PASS $1"; pass=$((pass + 1)); }
no() { echo "FAIL $1: $2"; fail=$((fail + 1)); }

have() { [ -e "$ROOT$1" ]; }

# ------------------------------------------------------------ A. assets land
missing=""
for p in \
  /etc/lightdm/lightdm-gtk-greeter.conf /etc/lightdm/unity-greeter.conf \
  /etc/lightdm/lightdm.conf.d/10-metaos-live.conf \
  /usr/share/backgrounds/meta-ascii.png /usr/share/backgrounds/meta-rays.png \
  /usr/share/backgrounds/meta-dusk.png /usr/share/backgrounds/meta-dawn.png \
  /usr/share/backgrounds/meta-m.png \
  /usr/share/plymouth/themes/metaos/metaos.plymouth \
  /usr/share/plymouth/themes/metaos/metaos.script \
  /usr/share/plymouth/themes/metaos/background.png \
  /usr/share/plymouth/themes/metaos/meta-m.png \
  /usr/share/plymouth/themes/metaos/progress.png \
  /boot/grub/themes/metaos/theme.txt /boot/grub/themes/metaos/background.png \
  /boot/grub/themes/metaos/mark.png \
  /usr/share/themes/MetaOS/gtk-3.0/gtk.css /usr/share/themes/MetaOS/index.theme \
  /usr/share/themes/MetaOS/xfwm4/themerc \
  /etc/skel/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-panel.xml \
  /etc/xdg/xfce4/xfconf/xfce-perchannel-xml/xfce4-panel.xml \
  /usr/share/plank/themes/MetaOS/dock.theme \
  /etc/skel/.config/plank/dock1/settings /etc/xdg/autostart/plank.desktop \
  /etc/bash.bashrc.d/metaos.sh /usr/share/doc/metaos/terminal-profile.txt \
  /usr/share/icons/metaos/index.theme \
  /usr/share/metaos/apps/metaos-welcome.py \
  /usr/share/applications/metaos-welcome.desktop \
  /usr/share/metaos/apps/metaos-imperium.py \
  /usr/share/applications/metaos-imperium.desktop \
  /etc/os-release /etc/lsb-release /etc/hostname /etc/issue /etc/issue.net /etc/motd \
  /etc/update-motd.d/00-header /etc/plymouth/plymouthd.conf \
  ; do
  have "$p" || missing="$missing $p"
done
nframes=0; if [ -d "$THEME/frames" ]; then nframes=$(ls "$THEME"/frames/frame-*.png 2>/dev/null | wc -l); fi
[ "$nframes" -ge 120 ] || missing="$missing [want at least 120 plymouth frames, have $nframes]"
nicons=0; if [ -d "$ROOT/usr/share/icons/metaos/128x128/apps" ]; then nicons=$(ls "$ROOT"/usr/share/icons/metaos/128x128/apps/*.png 2>/dev/null | wc -l); fi
# floor, not exact: the icon set grew past 20 and this row failed the whole
# proof on a healthy image
[ "$nicons" -ge 20 ] || missing="$missing [want at least 20 metaos icons, have $nicons]"
for d in meta-dock-dashboard meta-dock-editor meta-dock-notes meta-dock-agents \
  meta-dock-board meta-dock-calendar meta-dock-calculator meta-dock-trash \
  meta-dock-science meta-dock-musica meta-dock-custos meta-dock-officina; do
  have "/usr/share/applications/$d.desktop" || missing="$missing /usr/share/applications/$d.desktop"
done
if [ -z "$missing" ]; then ok "assets: manifest complete in image"; else no "assets" "missing:$missing"; fi

# ------------------------------------------------------------ B. icons resolve
resolve() {
  name="$1"
  case "$name" in /*) [ -f "$ROOT$name" ] && return 0 || return 1 ;; esac
  for ext in png svg xpm; do [ -f "$ROOT/usr/share/icons/metaos/128x128/apps/$name.$ext" ] && return 0; done
  inh=$(sed -n 's/^Inherits=//p' "$ROOT/usr/share/icons/metaos/index.theme" | tr ',' ' ')
  for parent in $inh; do
    pdir="$ROOT/usr/share/icons/$parent"
    [ -d "$pdir" ] || continue
    if find "$pdir" -name "$name.png" -o -name "$name.svg" -o -name "$name.xpm" 2>/dev/null | grep -q .; then return 0; fi
  done
  return 1
}
if [ ! -f "$ROOT/usr/share/icons/metaos/index.theme" ]; then
  no "icons" "index.theme missing"
elif ! grep -q '^\[Icon Theme\]' "$ROOT/usr/share/icons/metaos/index.theme"; then
  no "icons" "index.theme has no [Icon Theme]"
else
  names=$(grep -h '^Icon=' "$ROOT"/usr/share/applications/*.desktop 2>/dev/null | sed 's/^Icon=//' | sort -u)
  names="$names
folder
folder-open
text-x-generic
application-x-executable
user-home
user-trash
user-trash-full
drive-harddisk
start-here
plank"
  bad=""; total=0; good=0
  for n in $names; do
    [ -n "$n" ] || continue
    total=$((total + 1))
    if resolve "$n"; then good=$((good + 1)); else bad="$bad $n"; fi
  done
  if [ -z "$bad" ]; then ok "icons: $good/$total names resolve (metaos + Inherits)"; else no "icons" "$good/$total miss:$bad"; fi
fi

# ------------------------------------------------------------ C. absolute-path refs
rel=""
v=$(sed -n 's/^background=//p' "$ROOT/etc/lightdm/lightdm-gtk-greeter.conf" 2>/dev/null | head -1)
case "$v" in /*) ;; *) rel="$rel gtk-greeter:background=$v" ;; esac
v=$(sed -n 's/^default-user-image=//p' "$ROOT/etc/lightdm/lightdm-gtk-greeter.conf" 2>/dev/null | head -1)
case "$v" in /*) ;; *) rel="$rel gtk-greeter:default-user-image=$v" ;; esac
v=$(sed -n 's/^background=//p' "$ROOT/etc/lightdm/unity-greeter.conf" 2>/dev/null | head -1)
case "$v" in /*) ;; *) rel="$rel unity-greeter:background=$v" ;; esac
v=$(sed -n 's/^logo=//p' "$ROOT/etc/lightdm/unity-greeter.conf" 2>/dev/null | head -1)
case "$v" in /*) ;; *) rel="$rel unity-greeter:logo=$v" ;; esac
v=$(sed -n 's/^ImageDir=//p' "$THEME/metaos.plymouth" 2>/dev/null)
case "$v" in /*) ;; *) rel="$rel plymouth:ImageDir=$v" ;; esac
v=$(sed -n 's/^ScriptFile=//p' "$THEME/metaos.plymouth" 2>/dev/null)
case "$v" in /*) ;; *) rel="$rel plymouth:ScriptFile=$v" ;; esac
[ -f "$ROOT$v" ] || rel="$rel plymouth:ScriptFile-missing"
if [ -z "$rel" ]; then ok "absolute-refs: greeter + plymouth point at absolute paths"; else no "absolute-refs" "$rel"; fi

# ------------------------------------------------------------ D. owned brand strings
hits=""
scanfile() {
  # Allowlist: the live username `ubuntu` (link 1 — must stay) wherever it
  # appears as a technical identifier, never as brand prose.
  rest=""
  if grep -i 'ubuntu\|xubuntu' "$ROOT$1" 2>/dev/null | grep -v -E '^(autologin-user=meta|.*USERNAME=meta.*)$' | grep -q .; then
    rest="hit"
  fi
  [ -z "$rest" ] || hits="$hits $1"
}
for f in /etc/lightdm/lightdm-gtk-greeter.conf /etc/lightdm/unity-greeter.conf \
  /etc/lightdm/lightdm.conf.d/10-metaos-live.conf /etc/hostname /etc/issue /etc/issue.net /etc/motd \
  /etc/update-motd.d/00-header /boot/grub/themes/metaos/theme.txt \
  /usr/share/plymouth/themes/metaos/metaos.script /usr/share/plymouth/themes/metaos/metaos.plymouth; do
  scanfile "$f"
done
if grep -qi 'PRETTY_NAME="Meta OS 1.0 (Ribbon)"' "$ROOT/etc/os-release" 2>/dev/null; then :; else hits="$hits /etc/os-release:PRETTY_NAME"; fi
if grep -q '^ID=metaos$' "$ROOT/etc/os-release" 2>/dev/null; then :; else hits="$hits /etc/os-release:ID"; fi
if [ -z "$hits" ]; then ok "brand-owned: lane D files carry no ubuntu/xubuntu"; else no "brand-owned" "$hits"; fi

# ------------------------------------------------------------ E. visible tree scan
thits=""
for f in "$ROOT"/usr/share/applications/*.desktop; do
  if grep -i -E '^(Name|Comment|GenericName)' "$f" 2>/dev/null | grep -qi 'ubuntu\|xubuntu'; then thits="$thits $(basename "$f")"; fi
done
for f in /etc/lightdm/lightdm.conf /etc/lightdm/unity-greeter.conf \
  /etc/xdg/xfce4/xfconf/xfce-perchannel-xml/xfce4-panel.xml; do
  if grep -qi 'ubuntu\|xubuntu' "$ROOT$f" 2>/dev/null; then thits="$thits $f"; fi
done
oros=""
if grep -v -E '^(ID_LIKE|UBUNTU_CODENAME)=' "$ROOT/etc/os-release" 2>/dev/null | grep -qi 'ubuntu'; then oros="hit"; fi
[ -n "$oros" ] && thits="$thits /etc/os-release(non-allowlisted)"
if [ -z "$thits" ]; then ok "brand-tree: .desktop Name/Comment + greeter/panel carry no ubuntu/xubuntu"; else no "brand-tree" "$thits"; fi

# ------------------------------------------------------------ F. plymouth resolves
if [ ! -f "$THEME/metaos.script" ]; then
  no "plymouth" "script missing"
else
  missing_ref=""
  for r in $(grep -o 'Image *( *"[^"]*"' "$THEME/metaos.script" | sed 's/.*"\([^"]*\)"/\1/' | grep -v '^$'); do
    [ -f "$THEME/$r" ] || missing_ref="$missing_ref $r"
  done
  for h in SetBootProgressFunction SetRefreshFunction SetDisplayPasswordFunction \
    SetDisplayNormalFunction SetMessageFunction SetHideMessageFunction SetQuitFunction; do
    grep -q "$h" "$THEME/metaos.script" || missing_ref="$missing_ref hook:$h"
  done
  grep -q '16 fps' "$THEME/metaos.script" || missing_ref="$missing_ref cadence-note"
  if grep -q '^Theme=metaos' "$ROOT/etc/plymouth/plymouthd.conf" 2>/dev/null; then :; else missing_ref="$missing_ref plymouthd.conf"; fi
  alt="$ROOT/var/lib/dpkg/alternatives/default.plymouth"
  if [ -f "$alt" ]; then
    grep -q 'metaos' "$alt" || missing_ref="$missing_ref alternative-not-metaos"
  fi
  if [ -z "$missing_ref" ]; then ok "plymouth: descriptor+>=120 frames+7 hooks+fps note+default=metaos"; else no "plymouth" "$missing_ref"; fi
fi

# ------------------------------------------------------------ G. autologin intact
auser=$(grep -h '^autologin-user=' "$ROOT"/etc/lightdm/lightdm.conf.d/*.conf 2>/dev/null | sort -u)
asess=$(grep -h '^user-session=' "$ROOT"/etc/lightdm/lightdm.conf.d/*.conf 2>/dev/null | sort -u)
if [ "$auser" = "autologin-user=meta" ] && [ "$asess" = "user-session=metaos" ]; then
  ok "autologin: meta + user-session=metaos (link 1 intact)"
else
  no "autologin" "user=[$auser] session=[$asess]"
fi

# ------------------------------------------------------------ H. fonts
fmiss=""
ls "$ROOT"/usr/share/fonts/opentype/inter/Inter-* >/dev/null 2>&1 || ls "$ROOT"/usr/share/fonts/truetype/inter/Inter-* >/dev/null 2>&1 || fmiss="$fmiss Inter-files"
ls "$ROOT"/usr/share/fonts/truetype/ubuntu/UbuntuMono* >/dev/null 2>&1 || fmiss="$fmiss UbuntuMono-files"
grep -q "'Inter'" "$ROOT/usr/share/themes/MetaOS/gtk-3.0/gtk.css" 2>/dev/null || fmiss="$fmiss gtk.css-Inter"
grep -q '^FontName=Ubuntu Mono 11' "$ROOT/usr/share/doc/metaos/terminal-profile.txt" 2>/dev/null || fmiss="$fmiss terminal-profile"
grep -q 'font-name=Inter 11' "$ROOT/etc/lightdm/lightdm-gtk-greeter.conf" 2>/dev/null || fmiss="$fmiss greeter-Inter"
if [ -z "$fmiss" ]; then ok "fonts: Inter + Ubuntu Mono installed and referenced (gtk+greeter+terminal)"; else no "fonts" "$fmiss"; fi

# ------------------------------------------------------------ I. grub theme
gmiss=""
grep -q 'title-text: "Meta OS 1.0"' "$ROOT/boot/grub/themes/metaos/theme.txt" 2>/dev/null || gmiss="$gmiss title"
grep -q 'timeout = 10' "$ROOT/boot/grub/themes/metaos/theme.txt" 2>/dev/null || gmiss="$gmiss timeout"
grep -qi 'ubuntu\|xubuntu' "$ROOT/boot/grub/themes/metaos/theme.txt" 2>/dev/null && gmiss="$gmiss brand-string"
[ -s "$ROOT/boot/grub/themes/metaos/background.png" ] || gmiss="$gmiss background.png"
[ -s "$ROOT/boot/grub/themes/metaos/mark.png" ] || gmiss="$gmiss mark.png"
if [ -z "$gmiss" ]; then ok "grub: Meta OS 1.0 title, timeout 10, no ubuntu strings"; else no "grub" "$gmiss"; fi

# ------------------------------------------------------------ J. 17 dock names
dmiss=""
for n in Web Terminal Files Dashboard "Code Editor" Notes Agents Board Calendar Calculator Settings Trash Imperium "Science Lab" Musica Custos Officina; do
  if grep -rq "^Name=$n\$" "$ROOT"/usr/share/applications/*.desktop 2>/dev/null; then :; else dmiss="$dmiss [$n]"; fi
done
if [ -z "$dmiss" ]; then ok "dock-names: all 17 dock apps have a .desktop Name="; else no "dock-names" "missing:$dmiss"; fi

echo "----"
echo "theme_proof: $pass passed, $fail failed"
exit $([ "$fail" -eq 0 ] && echo 0 || echo 1)

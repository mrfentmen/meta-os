#!/bin/sh
# debrand2.sh — the Ubuntu leftovers a `ls` can still find.
#
# debrand.sh handles the identity files (os-release, lsb, issue, motd).
# rename_user.sh handles the account. This handles the assets and the backdrop
# state, which is where the last visible Ubuntu lives:
#
#   1. /usr/share/plymouth/themes/ubuntu-text still ships even though the active
#      theme is `metaos`. Dead weight with Ubuntu's name on it.
#   2. /usr/share/backgrounds/greybird.svg and /usr/share/backgrounds/xfce/* are
#      Xubuntu's stock wallpapers. One of them, xfce-shapes.svg, is still named
#      as the backdrop for monitor entries in xfce4-desktop.xml -- so a boot that
#      reports a different monitor name can paint Ubuntu's wallpaper instead of
#      Meta's. That is why this script rewrites every last-image entry, not just
#      the one that happens to be active today.
#
#   sh os-build/identity/debrand2.sh /mnt            # apply
#   sh os-build/identity/debrand2.sh /mnt --check    # measure
set -eu

ROOT="${1:-/mnt}"
MODE=apply
[ "${2:-}" = "--check" ] && MODE=check
[ -d "$ROOT/etc" ] || { echo "debrand2: no $ROOT/etc" >&2; exit 2; }

WALL="$ROOT/usr/share/backgrounds/meta-wallpaper.png"
DESKTOP_XML="$ROOT/home/meta/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-desktop.xml"

check() {
  fail=0
  say() { if [ "$2" = ok ]; then echo "PASS $1"; else echo "FAIL $1 -- $3"; fail=1; fi; }

  # 1. no ubuntu plymouth theme on disk
  n=$(find "$ROOT/usr/share/plymouth/themes" -maxdepth 1 -name 'ubuntu*' 2>/dev/null | wc -l | tr -d ' ')
  [ "$n" = 0 ] && say "plymouth ubuntu themes removed" ok "" \
                || say "plymouth ubuntu themes removed" no "$n ubuntu* theme dir(s) left"

  # 2. active plymouth is still metaos
  grep -q '^Theme=metaos' "$ROOT/etc/plymouth/plymouthd.conf" 2>/dev/null \
    && say "plymouth theme metaos" ok "" \
    || say "plymouth theme metaos" no "plymouthd.conf does not say Theme=metaos"

  # 3. stock Xubuntu wallpapers gone
  found=""
  [ -f "$ROOT/usr/share/backgrounds/greybird.svg" ] && found="$found greybird.svg"
  for f in "$ROOT"/usr/share/backgrounds/xfce/*; do
    [ -e "$f" ] && found="$found (xfce/$(basename "$f"))"
  done
  [ -z "$found" ] && say "stock wallpapers removed" ok "" \
                  || say "stock wallpapers removed" no "still present:$found"

  # 4. every backdrop points at Meta's wallpaper
  if [ -f "$DESKTOP_XML" ]; then
    bad=$(grep -c 'last-image.*value="/usr/share/backgrounds/\(greybird\|xfce\)' "$DESKTOP_XML" 2>/dev/null || true)
    [ "${bad:-0}" = 0 ] && say "backdrops are Meta" ok "" \
                        || say "backdrops are Meta" no "$bad last-image entr(ies) point at a stock wallpaper"
  else
    # A fresh root that has not been logged into yet has no per-user desktop
    # config to rewrite; that is not a failure, it is nothing to do.
    echo "SKIP backdrops are Meta -- no xfce4-desktop.xml yet (user not seeded)"
  fi

  # 5. the Meta wallpaper is actually there
  [ -f "$WALL" ] && say "meta wallpaper present" ok "" \
                 || say "meta wallpaper present" no "$WALL missing"

  [ "$fail" = 0 ] || { echo "debrand2 --check: FAIL"; exit 1; }
  echo "debrand2 --check: PASS"
}

if [ "$MODE" = check ]; then check; exit 0; fi

echo "debrand2: cleaning assets in $ROOT"

# 1. dead plymouth theme
for d in "$ROOT"/usr/share/plymouth/themes/ubuntu*; do
  [ -e "$d" ] || continue
  rm -rf "$d"
  echo "  removed ${d#"$ROOT"}"
done

# 2. stock wallpapers. Refuse if a Meta wallpaper is not there first: removing
#    the only backdrop would leave the desktop black.
[ -f "$WALL" ] || { echo "debrand2: $WALL missing, refusing to remove wallpapers" >&2; exit 1; }

if [ -f "$ROOT/usr/share/backgrounds/greybird.svg" ]; then
  rm -f "$ROOT/usr/share/backgrounds/greybird.svg"
  echo "  removed /usr/share/backgrounds/greybird.svg"
fi
if [ -d "$ROOT/usr/share/backgrounds/xfce" ]; then
  rm -rf "$ROOT/usr/share/backgrounds/xfce"
  echo "  removed /usr/share/backgrounds/xfce/"
fi

# 3. repoint every backdrop, including monitor names this boot does not have.
if [ -f "$DESKTOP_XML" ]; then
  before=$(grep -c 'last-image' "$DESKTOP_XML" 2>/dev/null || echo 0)
  sed -i 's|\(last-image" type="string" value="\)[^"]*"|\1/usr/share/backgrounds/meta-wallpaper.png"|g' "$DESKTOP_XML"
  after=$(grep -c 'meta-wallpaper.png' "$DESKTOP_XML" 2>/dev/null || echo 0)
  echo "  backdrops repointed: $after of $before last-image entries now Meta's wallpaper"
fi

echo "debrand2: applied; verifying"
check

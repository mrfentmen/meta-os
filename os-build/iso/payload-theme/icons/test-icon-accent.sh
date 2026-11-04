#!/bin/bash
# test-icon-accent.sh — prove the wallpaper→icon plumbing without a VM.
#
# A real X session is not needed because the only thing the script talks to is
# xfconf-query, and that is stubbed here with the exact three call shapes the
# script uses (-l, -p <prop>, -m). Every assertion below is a file that either
# exists with the right content or does not.
#
# Usage: sh test-icon-accent.sh            (exit 0 = all pass)
set -u
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
# HERE is os-build/iso/payload-theme/icons — four levels below the repo root.
ROOT=$(CDPATH= cd -- "$HERE/../../../.." && pwd)
WORK=$(mktemp -d /tmp/icon-accent-test.XXXXXX) || exit 1
trap 'rm -rf "$WORK"' EXIT

PASS=0
FAIL=0
ok() { PASS=$((PASS + 1)); printf 'PASS  %s\n' "$1"; }
no() { FAIL=$((FAIL + 1)); printf 'FAIL  %s\n' "$1"; }
check() { # check <desc> <command...>
  desc=$1
  shift
  if "$@" >/dev/null 2>&1; then ok "$desc"; else no "$desc"; fi
}

ACCENTS=$WORK/accents
if [ -d "$ROOT/os-build/captures/icon-accents/amber-B" ]; then
  cp -R "$ROOT/os-build/captures/icon-accents" "$ACCENTS"
else
  echo "building accent sets (no cached copy)…"
  python3 "$HERE/gen-icon-accents.py" "$ACCENTS" >/dev/null || { echo "could not build sets"; exit 1; }
fi
check "manifest lists 8 sets" test "$(grep -c '^set=' "$ACCENTS/accents.conf")" -eq 8

STUB=$WORK/bin
mkdir -p "$STUB"
STATE=$WORK/wallpaper
printf '/usr/share/backgrounds/meta-dawn.png\n' >"$STATE"
CALLS=$WORK/calls.log
: >"$CALLS"

cat >"$STUB/xfconf-query" <<'SH'
#!/bin/sh
# The three shapes meta-icon-accent uses, nothing more.
case "$*" in
  "-c xfce4-desktop -l")
    echo "/backdrop/screen0/monitorVirtual-1/workspace0/last-image"
    echo "/backdrop/screen0/monitorVirtual-1/workspace0/color-style"
    ;;
  "-c xfce4-desktop -p /backdrop/screen0/monitorVirtual-1/workspace0/last-image")
    cat "$FAKE_STATE"
    ;;
  "-c xsettings -p /Net/IconThemeName -s "*)
    echo "set-theme $*" >>"$FAKE_CALLS"
    ;;
  "-c xfce4-desktop -m")
    cat "$FAKE_MONITOR"
    ;;
  *) exit 0 ;;
esac
SH
chmod +x "$STUB/xfconf-query"
cat >"$STUB/gtk-update-icon-cache" <<'SH'
#!/bin/sh
echo "icon-cache $*" >>"$FAKE_CALLS"
SH
chmod +x "$STUB/gtk-update-icon-cache"
# A python3 that refuses, to exercise the no-pixel-sampling path.
mkdir -p "$STUB/no-python"
printf '#!/bin/sh\nexit 1\n' >"$STUB/no-python/python3"
chmod +x "$STUB/no-python/python3"

export METAOS_ACCENTS_DIR=$ACCENTS
export METAOS_ICON_HOME=$WORK/home/icons
export XDG_CONFIG_HOME=$WORK/home/.config
export XDG_CACHE_HOME=$WORK/home/.cache
export FAKE_STATE=$STATE FAKE_CALLS=$CALLS FAKE_MONITOR=$WORK/monitor
: >"$WORK/monitor"

run() { PATH="$STUB:$PATH" sh "$HERE/meta-icon-accent" "$@" 2>>"$WORK/stderr.log"; }

# The icons are symlinks, so "which set is installed" is the link TARGET, not
# the file's bytes. grep on the path itself would always fail.
target() { readlink "$METAOS_ICON_HOME/metaos/128x128/apps/terminal.png"; }
accent_is() { # accent_is <set> <label>
  if target | grep -q "/$1/"; then ok "$2"; else
    no "$2 (installed: $(target))"
  fi
}

# 1 — dawn wallpaper -> amber set
run apply
accent_is amber-B "dawn wallpaper selects amber-B"
check "theme name stays 'metaos' so launchers keep working" \
  grep -q '^Name=metaos$' "$METAOS_ICON_HOME/metaos/index.theme"
check "current reports amber-B" test "$(run current)" = "amber-B"
check "icon cache was refreshed" grep -q 'icon-cache' "$CALLS"
check "icon theme was set through xfconf" \
  grep -q 'set-theme -c xsettings -p /Net/IconThemeName -s metaos' "$CALLS"
n=$(ls "$METAOS_ICON_HOME/metaos/128x128/apps" | wc -l | tr -d ' ')
check "27 icons linked at 128 px" test "$n" -eq 27

# 2 — switching the wallpaper switches the set, in place
printf '/usr/share/backgrounds/meta-dusk.png\n' >"$STATE"
run apply
accent_is violet-B "dusk wallpaper selects violet-B"
check "no half-built theme directory is left behind" \
  test -z "$(find "$METAOS_ICON_HOME/metaos" -maxdepth 1 -name '.metaos.new*' -print)"

# 3 — an unlisted wallpaper on a machine that cannot sample pixels: fall back,
#     and say so out loud rather than silently pretending it matched.
printf '/home/user/Pictures/holiday.png\n' >"$STATE"
rm -f "$WORK/stderr.log"
PATH="$STUB/no-python:$STUB:$PATH" sh "$HERE/meta-icon-accent" apply 2>>"$WORK/stderr.log"
accent_is blue-B "unknown wallpaper falls back to the default set"
check "the fallback is logged, not silent" \
  grep -q 'not in the manifest and this machine cannot sample it' "$WORK/stderr.log"

# 4 — an unlisted wallpaper on a machine WITH Pillow: sample the hue and pick
mkdir -p "$WORK/home"
cp "$ROOT/os-build/iso/payload-theme/wallpapers/meta-dawn.png" \
   "$WORK/home/unknown-dawn.png" 2>/dev/null
if [ -f "$WORK/home/unknown-dawn.png" ]; then
  printf '%s\n' "$WORK/home/unknown-dawn.png" >"$STATE"
  rm -f "$WORK/stderr.log"
  run apply
  # Which set a hue lands on depends on the art, so the assertion is that the
  # sampling path ran, named a real set, and installed it — not that a
  # particular hue won.
  if target | grep -Eq '/(blue|ice|amber|violet|teal|mono)-[ABC]/'; then
    ok "unknown art with Pillow installed a real set ($(basename "$(dirname \
      "$(dirname "$(dirname "$(target)")")")"))"
  else
    no "unknown art with Pillow did not install a real set ($(target))"
  fi
  check "the hue guess is logged" grep -q 'sampled its hue' "$WORK/stderr.log"
else
  no "could not stage an unlisted wallpaper for the hue test"
fi

# 5 — pinning a set wins over the wallpaper, and follow can be turned back on
run set blue-A
accent_is blue-A "pinned set installs blue-A"
check "pinning records follow_wallpaper=off" \
  grep -q '^follow_wallpaper=off$' "$XDG_CONFIG_HOME/metaos/icons.conf"
printf '/usr/share/backgrounds/meta-dawn.png\n' >"$STATE"
run follow on >/dev/null 2>&1
accent_is amber-B "follow on returns to amber-B for dawn"

# 6 — watch mode reacts to a monitor line without a restart
: >"$CALLS"
printf '/usr/share/backgrounds/meta-rays.png\n' >"$STATE"
printf '/backdrop/screen0/monitorVirtual-1/workspace0/last-image: /usr/share/backgrounds/meta-rays.png\n' >"$WORK/monitor"
# No `timeout`: it is GNU coreutils and absent on a stock macOS, which is
# exactly where this test runs before the image exists.
PATH="$STUB:$PATH" sh "$HERE/meta-icon-accent" watch >/dev/null 2>>"$WORK/stderr.log" &
WPID=$!
sleep 3
kill $WPID 2>/dev/null
wait $WPID 2>/dev/null
accent_is ice-B "watch picked up the change and installed ice-B"

# 7 — a set that does not exist is refused, loudly, and leaves the old one
printf '/usr/share/backgrounds/meta-dawn.png\n' >"$STATE"
rm -f "$WORK/stderr.log"
METAOS_ACCENTS_DIR=$WORK/empty sh "$HERE/meta-icon-accent" set nope 2>>"$WORK/stderr.log"
check "a missing set is refused" grep -q 'REFUSED: no icon set named' "$WORK/stderr.log"
check "the refusal did not break the installed theme" \
  test -f "$METAOS_ICON_HOME/metaos/index.theme"

printf '\n%d passed, %d failed\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ] || exit 1

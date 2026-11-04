#!/bin/sh
# check-greeter.sh — brand + session gates for the greeter drop-ins.
# Usage: check-greeter.sh [--greeter DIR]  (default: this payload's greeter/)
# FAILs on Ubuntu theme strings, missing Meta session wiring, guest sessions,
# or a clock/hostname that disagrees with the desktop. Static, no boot.
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
G="$HERE/../greeter"
for a in "$@"; do
  case "$a" in
    --greeter) G="$2"; shift 2 ;;
    -h|--help) echo "usage: check-greeter.sh [--greeter DIR]"; exit 0 ;;
    *) echo "check-greeter: unknown flag $a" >&2; exit 2 ;;
  esac
done
fail=0
ok() { echo "PASS greeter: $1"; }
no() { echo "FAIL greeter: $1"; fail=1; }
[ -d "$G" ] || { no "greeter dir missing: $G"; echo "check-greeter: $fail FAIL"; exit 1; }
if grep -rh -v '^[[:space:]]*#' "$G"/lightdm-gtk-greeter.conf "$G"/unity-greeter.conf "$G"/10-metaos-live.conf "$G"/99_metaos-greeter.gschema.override 2>/dev/null | grep -qi 'ubuntu'; then
  no "Ubuntu string in greeter values: $(grep -rh -v '^[[:space:]]*#' "$G"/lightdm-gtk-greeter.conf "$G"/unity-greeter.conf "$G"/10-metaos-live.conf "$G"/99_metaos-greeter.gschema.override | grep -i 'ubuntu' | head -3)"
else
  ok "no Ubuntu string in greeter values (comments may name history)"
fi
grep -q '^background=/usr/share/backgrounds/meta-.*\.png' "$G/lightdm-gtk-greeter.conf" 2>/dev/null \
  && ok "gtk-greeter background is Meta" \
  || no "gtk-greeter background is not Meta art"
grep -q '^background=/usr/share/backgrounds/meta-.*\.png' "$G/unity-greeter.conf" 2>/dev/null \
  && ok "unity-greeter background is Meta" \
  || no "unity-greeter background is not Meta art"
grep -q '^user-session=metaos' "$G/10-metaos-live.conf" 2>/dev/null \
  && ok "session is metaos (fails loudly if missing via TryExec)" \
  || no "user-session is not metaos"
grep -q '^autologin-user=meta' "$G/10-metaos-live.conf" 2>/dev/null \
  && ok "autologin intact (user meta)" \
  || no "autologin-user is not meta"
grep -q '^allow-guest=false' "$G/10-metaos-live.conf" 2>/dev/null \
  && ok "guest session disabled" \
  || no "allow-guest is not false"
grep -q '^clock-format=%a, %b %e %H:%M' "$G/lightdm-gtk-greeter.conf" 2>/dev/null \
  && ok "clock matches desktop panel" \
  || no "clock-format differs from desktop (%a, %b %e %H:%M)"
grep -q '^font-name=Inter 11' "$G/lightdm-gtk-greeter.conf" 2>/dev/null \
  && ok "greeter font is desktop family (Inter)" \
  || no "greeter font is not Inter 11"
grep -q '^cursor-theme-name=' "$G/lightdm-gtk-greeter.conf" 2>/dev/null \
  && ok "cursor theme pinned" \
  || no "no cursor-theme-name in greeter conf"
grep -q '^show-hostname=true' "$G/unity-greeter.conf" 2>/dev/null \
  && ok "greeter shows machine name" \
  || no "show-hostname is not true (unity)"
grep -q 'show-hostname=true' "$G/99_metaos-greeter.gschema.override" 2>/dev/null \
  && ok "gschema shows machine name" \
  || no "show-hostname is not true (gschema)"
for f in "wallpapers/meta-ascii.png" "wallpapers/meta-rays.png" "splash/meta-m.png"; do
  [ -f "$HERE/../$f" ] \
    && ok "referenced art ships: $f" \
    || no "referenced art missing from payload: $f"
done
SESS="$HERE/metaos.desktop"
[ -f "$SESS" ] || { no "session desktop missing: $SESS"; echo "check-greeter: $fail FAIL"; exit 1; }
grep -q '^Name=Meta OS' "$SESS" && grep -q '^Exec=/opt/face/session.sh' "$SESS" \
  && ok "session desktop is Meta (Name + Exec)" \
  || no "session desktop is not Meta"
grep -qi 'ubuntu\|xubuntu' "$SESS" \
  && no "Ubuntu string in session desktop" \
  || ok "session desktop names no Ubuntu"
grep -q '^TryExec=' "$SESS" \
  && ok "missing session fails loudly (TryExec)" \
  || no "no TryExec: missing session would fall back silently"
if grep -rn 'NoDisplay=true' "$SESS" >/dev/null 2>&1; then
  no "session desktop hidden (NoDisplay)"
else
  ok "session desktop visible"
fi
if [ "$fail" = 0 ]; then echo "check-greeter: all PASS"; else echo "check-greeter: $fail FAIL"; fi
exit $fail

#!/bin/sh
# verify-dropin-desktop.sh — verify an installed OC2 desktop-entries drop-in.
# Usage: sh verify-dropin-desktop.sh [manifest] [app-dir] [mimeapps-file]
#   manifest      default: agent-layer/MANIFEST.md
#   app-dir       default: /usr/share/applications (OC1 system target)
#   mimeapps-file default: /etc/xdg/mimeapps.list
# Exit 0: clean. Exit 1: findings (listed). Exit 3: SKIP (app dir missing).
# Never requires systemd: no systemctl call in this file by design.
set -u
MANIFEST="${1:-agent-layer/MANIFEST.md}"
APPDIR="${2:-/usr/share/applications}"
MIMEAPPS="${3:-/etc/xdg/mimeapps.list}"
FAIL=0
note() { echo "DESKTOP $1: $2"; }
# Portable sha256: sha256sum (Linux) or shasum -a 256 (macOS/BSD).
# Hard FAIL when neither backend exists (never false-pass on empty strings).
shasum256() {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | awk '{print $1}';
  elif command -v shasum >/dev/null 2>&1; then shasum -a 256 "$1" 2>/dev/null | awk '{print $1}';
  else echo "MISSING-SHA-BACKEND"; fi
}
if [ ! -d "$APPDIR" ]; then
  note "SKIP" "app dir missing: $APPDIR (desktop lane not installed here)"
  exit 3
fi
if [ ! -f "$MANIFEST" ]; then note "FAIL" "manifest missing: $MANIFEST"; exit 1; fi
if ! command -v sha256sum >/dev/null 2>&1 && ! command -v shasum >/dev/null 2>&1; then
  note "FAIL" "no sha256 backend (need sha256sum or shasum)"; exit 1
fi
# 1. Every manifest-listed desktop-entries row exists at target, sha matches.
_MATCHES="$(mktemp)"
grep -o '`agent-layer/desktop-entries/[^`]*` sha256 `[0-9a-f]*`' "$MANIFEST" > "$_MATCHES" || true
if [ ! -s "$_MATCHES" ]; then note "FAIL" "no desktop-entries rows in $MANIFEST"; FAIL=1; fi
while read -r path _ sha; do
  rel=$(printf '%s' "$path" | tr -d '`')
  rel=${rel#agent-layer/desktop-entries/}
  sha=$(printf '%s' "$sha" | tr -d '`')
  case "$rel" in README.md|INSTALL-OC1.md) continue ;; esac  # docs (not installed)
  if [ "$rel" = "mimeapps.list" ]; then f="$MIMEAPPS"; else f="$APPDIR/$rel"; fi
  if [ ! -f "$f" ]; then note "FAIL" "missing installed $rel"; FAIL=1; continue; fi
  got="$(shasum256 "$f")"
  if [ "$got" = "$sha" ]; then note "OK" "$rel sha matches"; else note "FAIL" "$rel sha MISMATCH"; FAIL=1; fi
done < "$_MATCHES"
rm -f "$_MATCHES"
# 2. Installed mimeapps maps exactly the 4 OC2 types (never browser types).
if [ ! -f "$MIMEAPPS" ]; then
  note "FAIL" "mimeapps missing: $MIMEAPPS"; FAIL=1
else
  n="$(grep -cE '^[A-Za-z0-9.+_-]+/[A-Za-z0-9.+_-]+=.*\.desktop$' "$MIMEAPPS" || true)"
  if [ "$n" = "4" ]; then note "OK" "mimeapps maps exactly 4 types";
  else note "FAIL" "mimeapps maps $n types (want 4)"; FAIL=1; fi
  for t in text/plain image/png image/jpeg application/pdf; do
    if grep -q "^${t}=[A-Za-z0-9._-]*\.desktop$" "$MIMEAPPS"; then note "OK" "$t mapped";
    else note "FAIL" "$t missing/malformed in $MIMEAPPS"; FAIL=1; fi
  done
  pdf="$(grep '^application/pdf=' "$MIMEAPPS" | tail -n 1 | cut -d= -f2)"
  case "$pdf" in
    atril.desktop|evince.desktop) note "OK" "pdf -> $pdf" ;;
    *) note "FAIL" "pdf -> ${pdf:-<unmapped>} (want atril|evince)"; FAIL=1 ;;
  esac
  if grep -q '^text/html=' "$MIMEAPPS"; then note "FAIL" "text/html mapped (Bond's lane)"; FAIL=1; fi
  _VALS="$(mktemp)"
  grep -E '^[A-Za-z0-9.+_-]+/[A-Za-z0-9.+_-]+=.*\.desktop$' "$MIMEAPPS" | cut -d= -f2 > "$_VALS" || true
  while read -r d; do
    if [ -f "$APPDIR/$d" ]; then note "OK" "mapped $d present";
    else note "FAIL" "mapped $d missing in $APPDIR"; FAIL=1; fi
  done < "$_VALS"
  rm -f "$_VALS"
fi
# 3. Degraded-off evince stays hidden (NoDisplay=true) in the installed copy.
if [ -f "$APPDIR/evince.desktop" ]; then
  if grep -q '^NoDisplay=true' "$APPDIR/evince.desktop"; then note "OK" "evince NoDisplay=true (degraded-off)";
  else note "FAIL" "evince missing NoDisplay=true"; FAIL=1; fi
fi
exit "$FAIL"

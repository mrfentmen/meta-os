#!/bin/sh
# check_target.sh — post-install os-release gate (installer task 89).
# Usage: TARGET=/path/to/installed/root sh os-build/iso/calamares/tools/check_target.sh
# FAILs when user-visible identity still says Ubuntu, when the hostname is
# not metaos, or when the installer autostart lingers on the installed system.
# Static read of files; no boot, no mount.
set -eu
TARGET="${TARGET:-/}"
fail=0
pass() { echo "TARGET-CHECK PASS: $1"; }
fail() { echo "TARGET-CHECK FAIL: $1"; fail=1; }
OS="$TARGET/etc/os-release"
HOST="$TARGET/etc/hostname"
if [ -f "$OS" ]; then
  if grep -qi 'ubuntu' "$OS" 2>/dev/null; then
    fail "user-visible identity still says Ubuntu ($(grep -i 'ubuntu' "$OS" | head -1))"
  else
    pass "NAME/ID/PRETTY_NAME carry no Ubuntu string"
  fi
  if grep -qx 'ID_LIKE=debian' "$OS" 2>/dev/null; then
    pass "ID_LIKE=debian carries the Debian family, not Ubuntu"
  else
    fail "ID_LIKE is not debian: $(grep '^ID_LIKE=' "$OS" 2>/dev/null | head -1)"
  fi
else
  fail "$OS missing"
fi
if [ -f "$HOST" ]; then
  H=$(cat "$HOST" 2>/dev/null | head -1)
  if [ "$H" = "metaos" ]; then
    pass "hostname is metaos"
  else
    fail "hostname is '$H', want 'metaos'"
  fi
else
  fail "$HOST missing"
fi
if [ -e "$TARGET/etc/xdg/autostart/metaos-install.desktop" ]; then
  fail "installer autostart still present in target"
else
  pass "installer autostart absent from target"
fi
if [ "$fail" -ne 0 ]; then
  echo "TARGET-CHECK RESULT: FAIL"
  exit 1
fi
echo "TARGET-CHECK RESULT: PASS"

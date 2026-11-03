#!/bin/sh
# verify-dropin.sh — verify an installed OC2 agent layer (runs on TARGET).
# Usage: sh verify-dropin.sh [manifest] [systemd-user-dir] [env-file]
# Exit 0: all green. Exit 2: findings (listed). Exit 3: SKIP (no systemd here).
# The sha256sum check runs anywhere; the systemd checks need a user manager.
set -u
MANIFEST="${1:-agent-layer/MANIFEST.md}"
UNITDIR="${2:-$HOME/.config/systemd/user}"
ENVFILE="${3:-$HOME/.config/oc2-agent/env}"
FAIL=0
note() { echo "DROPIN $1: $2"; }
if ! command -v systemctl >/dev/null 2>&1; then
  echo "SKIP: no systemctl on this host (static checks only)"
fi
# 1. Every manifest-listed unit file exists in the systemd dir with matching sha.
# 1. Every manifest-listed unit file exists in the systemd dir with matching sha.
# (Matches are staged to a temp file first: a piped `while read` loop runs in
# a subshell and its FAIL flag would never reach the parent shell.)
_MATCHES="$(mktemp)"
grep -o '`agent-layer/units/[^`]*` sha256 `[0-9a-f]*`' "$MANIFEST" 2>/dev/null > "$_MATCHES" || true
while read -r path _ sha; do
  rel=$(printf '%s' "$path" | tr -d '`')
  rel=${rel#agent-layer/units/}
  sha=$(printf '%s' "$sha" | tr -d '`')
  f="$UNITDIR/$rel"
  if [ ! -f "$f" ]; then note "FAIL" "missing installed $rel"; FAIL=1; continue; fi
  got="$(shasum -a 256 "$f" 2>/dev/null | awk '{print $1}')"
  if [ "$got" = "$sha" ]; then note "OK" "$rel sha matches"; else note "FAIL" "$rel sha MISMATCH"; FAIL=1; fi
done < "$_MATCHES"
rm -f "$_MATCHES"
# 2. Enabled state (needs systemd; skip cleanly without it).
if command -v systemctl >/dev/null 2>&1; then
  for u in oc2-queue.service oc2-patrol.service oc2-trio.service oc2-patrol.timer; do
    if systemctl --user is-enabled "$u" >/dev/null 2>&1; then
      note "OK" "$u enabled"
    else
      note "FAIL" "$u NOT enabled"; FAIL=1
    fi
  done
  if systemctl --user is-active oc2-queue.service oc2-trio.service >/dev/null 2>&1; then
    note "OK" "queue+trio active (no hand-holding)"
  else
    note "FAIL" "queue or trio not active"; FAIL=1
  fi
else
  note "SKIP" "enablement/active checks need systemd user manager"
fi
# 3. No secrets in installed env file.
if [ -f "$ENVFILE" ]; then
  if grep -qE "BEGIN (RSA |OPENSSH |EC )?PRIVATE KEY|sk-[A-Za-z0-9]{20,}" "$ENVFILE"; then
    note "FAIL" "key material in env file"; FAIL=1
  else
    note "OK" "env file has no key material"
  fi
else
  note "FAIL" "env file missing: $ENVFILE"; FAIL=1
fi
exit $FAIL

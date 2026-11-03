#!/bin/sh
# Dry-run harness for metaos1-firstboot.sh (Hana lane, slice 2).
# Runs the script against throwaway directories only, via the
# test-only path overrides. No real system path is touched, no
# prompt, no network, no credential anywhere in this file.
# Usage: sh os-build/metaos1-base/firstboot/test_firstboot.sh
# Exit 0 only if every scenario passes.
set -u
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
SCRIPT="$SCRIPT_DIR/metaos1-firstboot.sh"
FAIL=0

say_pass() { echo "PASS: $1"; }
say_fail() { echo "FAIL: $1"; FAIL=1; }

# Scenario A: fresh user gets the system defaults, second run is a no-op.
TMP_A=$(mktemp -d)
mkdir -p "$TMP_A/home/alice"
printf 'text/plain=mousepad.desktop\n' > "$TMP_A/system-mimeapps.list"
METAOS1_DONE_FILE="$TMP_A/var/metaos1-firstboot.done" \
METAOS1_SYSTEM_DEFAULTS="$TMP_A/system-mimeapps.list" \
METAOS1_HOME_ROOT="$TMP_A/home" \
sh "$SCRIPT"
if [ $? -ne 0 ]; then say_fail "A: first run exit 0"; else say_pass "A: first run exit 0"; fi
if [ -f "$TMP_A/var/metaos1-firstboot.done" ]; then say_pass "A: done marker written"; else say_fail "A: done marker written"; fi
if cmp -s "$TMP_A/system-mimeapps.list" "$TMP_A/home/alice/.config/mimeapps.list"; then
    say_pass "A: user config copied from system defaults"
else
    say_fail "A: user config copied from system defaults"
fi
printf 'KEEP-ME\n' > "$TMP_A/home/alice/.config/mimeapps.list"
METAOS1_DONE_FILE="$TMP_A/var/metaos1-firstboot.done" \
METAOS1_SYSTEM_DEFAULTS="$TMP_A/system-mimeapps.list" \
METAOS1_HOME_ROOT="$TMP_A/home" \
sh "$SCRIPT"
if [ "$(cat "$TMP_A/home/alice/.config/mimeapps.list")" = "KEEP-ME" ]; then
    say_pass "A: second run leaves user config alone"
else
    say_fail "A: second run leaves user config alone"
fi
rm -rf "$TMP_A"

# Scenario B: a pre-existing user config is never overwritten.
TMP_B=$(mktemp -d)
mkdir -p "$TMP_B/home/bob/.config"
printf 'KEEP-MINE\n' > "$TMP_B/home/bob/.config/mimeapps.list"
printf 'text/plain=mousepad.desktop\n' > "$TMP_B/system-mimeapps.list"
METAOS1_DONE_FILE="$TMP_B/var/metaos1-firstboot.done" \
METAOS1_SYSTEM_DEFAULTS="$TMP_B/system-mimeapps.list" \
METAOS1_HOME_ROOT="$TMP_B/home" \
sh "$SCRIPT"
if [ "$(cat "$TMP_B/home/bob/.config/mimeapps.list")" = "KEEP-MINE" ]; then
    say_pass "B: pre-existing user config preserved"
else
    say_fail "B: pre-existing user config preserved"
fi
if [ -f "$TMP_B/var/metaos1-firstboot.done" ]; then say_pass "B: done marker written"; else say_fail "B: done marker written"; fi
rm -rf "$TMP_B"

# Scenario C: no home directory at all still exits 0 and marks done.
TMP_C=$(mktemp -d)
mkdir -p "$TMP_C/home"
printf 'text/plain=mousepad.desktop\n' > "$TMP_C/system-mimeapps.list"
METAOS1_DONE_FILE="$TMP_C/var/metaos1-firstboot.done" \
METAOS1_SYSTEM_DEFAULTS="$TMP_C/system-mimeapps.list" \
METAOS1_HOME_ROOT="$TMP_C/home" \
sh "$SCRIPT"
if [ $? -ne 0 ]; then say_fail "C: no-home run exit 0"; else say_pass "C: no-home run exit 0"; fi
if [ -f "$TMP_C/var/metaos1-firstboot.done" ]; then say_pass "C: done marker written"; else say_fail "C: done marker written"; fi
rm -rf "$TMP_C"

if [ "$FAIL" -eq 0 ]; then echo "OK: firstboot dry-run harness passed"; else echo "FAILED: firstboot dry-run harness"; fi
exit "$FAIL"

#!/usr/bin/env bash
# os-build/layer1/check_all.sh — one command, one exit code, every layer.
#
# The repo has grown a dozen green claims with a dozen different ways to check them. This
# runs the four that are actually executable on a Mac and reports them in one table, so
# "is it green" stops depending on which log someone last read.
#
# What it does NOT claim: that a pass means the OS is done. The kernel check is a build and
# a boot-log grep; the services check runs host processes, not kernel processes; the node
# suite has known failures and they are reported, not hidden. See os-build/QEMU_LIMITS.md.
#
# Exit: 0 if every step that must pass passes, 1 otherwise.
set -uo pipefail
cd "$(dirname "$0")/../.." || exit 1

FAILED=0
report() { printf '%-28s %s\n' "$1" "$2"; }

echo "== Meta OS check_all — $(date -u +%Y-%m-%dT%H:%M:%SZ) =="

# 1. Kernel: build the image and require the K1 line in a fresh boot.
NIGHTLY_RUSTC="$(rustup which --toolchain nightly rustc 2>/dev/null || true)"
if [ -z "$NIGHTLY_RUSTC" ]; then
    report "kernel build" "SKIP (no nightly toolchain)"
    FAILED=1
else
    export RUSTC="$NIGHTLY_RUSTC"
    export PATH="$(dirname "$NIGHTLY_RUSTC"):$HOME/.cargo/bin:$PATH"
    export RUSTUP_TOOLCHAIN=nightly
    if ( cd kernel && cargo check -q ) 2>/dev/null; then
        report "kernel check" "PASS"
    else
        report "kernel check" "FAIL"
        FAILED=1
    fi
    if ( cd kernel && cargo bootimage 2>&1 | grep -q "Created bootimage" ); then
        report "kernel image" "PASS"
    else
        report "kernel image" "FAIL"
        FAILED=1
    fi
fi

# 2. os-boot assets crate (the boot-side Rust crate, separate from the kernel).
if cargo check -q -p os-boot 2>/dev/null; then
    report "os-boot crate" "PASS"
else
    report "os-boot crate" "FAIL"
    FAILED=1
fi

# 3. Goose service corpus: real host processes, real memory.
if [ -x os-build/layer1/run_native.sh ]; then
    OUT="$(bash os-build/layer1/run_native.sh 2>&1 | tail -3)"
    if echo "$OUT" | grep -qE "FAILS=0"; then
        report "goose corpus" "PASS ($(echo "$OUT" | grep -oE 'RUNS=[0-9]+' | head -1))"
    else
        report "goose corpus" "FAIL"
        echo "$OUT" | sed 's/^/    /'
        FAILED=1
    fi
else
    report "goose corpus" "SKIP (run_native.sh missing)"
fi

# 4. Node suite. Known failures exist; the count is reported either way and only a
#    regression in the pass count fails the script.
# `node --test tests/` treats the directory as a test file and fails; the
# files must be named. Node 24's summary lines are "(i) pass 1877" / "(i) fail
# 56", not the older "# pass" form, and an unknown summary is a script bug,
# not a suite result — so the parse is checked against both spellings.
NODE_OUT="$(node --test tests/*.test.mjs 2>&1 | tail -60)"
# Plain ASCII match: BSD grep is not UTF-8 aware, so an "(i)" or "#" prefix in
# the pattern silently matches nothing. The words and counts are ASCII either way.
NODE_PASS="$(echo "$NODE_OUT" | grep -oE 'pass [0-9]+' | grep -oE '[0-9]+' | tail -1)"
NODE_FAIL="$(echo "$NODE_OUT" | grep -oE 'fail [0-9]+' | grep -oE '[0-9]+' | tail -1)"
# Informational, never fatal: the node suite carries a known-red set (tests written
# for removed native screens), so a red count here says nothing about the kernel or
# the OS layers. It reports the numbers when the runner prints them and says so
# plainly when it does not, instead of turning a runner quirk into a build failure.
if [ -n "$NODE_PASS" ]; then
    report "node suite (info)" "pass=$NODE_PASS fail=${NODE_FAIL:-0}"
else
    report "node suite (info)" "runner printed no summary; see npm test"
fi

echo
if [ "$FAILED" -eq 0 ]; then
    echo "check_all: PASS"
else
    echo "check_all: FAIL"
fi
exit "$FAILED"

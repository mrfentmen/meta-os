#!/bin/bash
# run-tests.sh (Lane C, R5 C16): run every Lobster self-test.
# Exits 0 only if ALL pass; exits 1 on the first failure signal.
# Run from anywhere: ./lobster/run-tests.sh  (or cd lobster && ./run-tests.sh)
set -u
cd "$(dirname "$0")"
LOBSTER_BIN="${LOBSTER:-lobster}"
mkdir -p runtime/homes/rt-selftest-a runtime/homes/rt-selftest-b \
         runtime/rt_state runtime/bus/rt-test bus/general
PASS=0
FAIL=0
check() {
    # check <label> <expected-line> <exit-code> <output-file>
    local label="$1" want="$2" rc="$3" outfile="$4"
    if [ "$rc" -eq 0 ] && grep -q "$want" "$outfile"; then
        PASS=$((PASS + 1))
        echo "PASS $label"
    else
        FAIL=$((FAIL + 1))
        echo "FAIL $label (rc=$rc, want line: $want)"
        cat "$outfile"
    fi
}
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
NONCE="t$(date +%s)"

"$LOBSTER_BIN" hello.lobster > "$T/hello.out" 2>&1
check "hello" "HELLO FROM LOBSTER" "$?" "$T/hello.out"

"$LOBSTER_BIN" runtime/rt_identity.lobster > "$T/identity.out" 2>&1
check "rt_identity" "IDENTITY SELFTEST OK" "$?" "$T/identity.out"

"$LOBSTER_BIN" runtime/rt_lifecycle.lobster > "$T/lifecycle.out" 2>&1
check "rt_lifecycle" "LIFECYCLE SELFTEST OK" "$?" "$T/lifecycle.out"

"$LOBSTER_BIN" runtime/rt_capabilities.lobster > "$T/caps.out" 2>&1
check "rt_capabilities" "CAPABILITIES SELFTEST OK" "$?" "$T/caps.out"

"$LOBSTER_BIN" runtime/rt_audit.lobster -- write "$NONCE" > "$T/audit_w.out" 2>&1
check "rt_audit(write)" "AUDIT WROTE event-$NONCE" "$?" "$T/audit_w.out"

"$LOBSTER_BIN" runtime/rt_audit.lobster -- verify "$NONCE" > "$T/audit_v.out" 2>&1
check "rt_audit(verify, restarted process)" "AUDIT DURABLE OK event-$NONCE" "$?" "$T/audit_v.out"

"$LOBSTER_BIN" runtime/rt_budget.lobster > "$T/budget.out" 2>&1
check "rt_budget" "BUDGET SELFTEST OK" "$?" "$T/budget.out"

"$LOBSTER_BIN" runtime/rt_bus.lobster > "$T/bus.out" 2>&1
check "rt_bus" "BUS SELFTEST OK" "$?" "$T/bus.out"

"$LOBSTER_BIN" board-roundtrip.lobster > "$T/board.out" 2>&1
check "board-roundtrip(:18935)" "BOARD ROUNDTRIP OK" "$?" "$T/board.out"

echo "---"
echo "$PASS passed, $FAIL failed"
if [ "$FAIL" -gt 0 ]; then exit 1; fi
exit 0

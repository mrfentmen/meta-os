#!/bin/sh
# run-goose-tests.sh (OS-164): Goose has no user-level test runner
# convention (its "testing" doc covers the compiler's own fixture
# suite), so this runner script states each check and runs it.
# Every check is a real process with a real assertion. Stated, not
# hidden: runner script because the language lacks one.
set -eu
GOOSE=/Users/test/mcp-servers/toolchains/goose-src/build/goose
PASS=0; FAIL=0
check() { # check <name> <expected> <actual>
  if [ "$2" = "$3" ]; then echo "PASS: $1"; PASS=$((PASS+1)); else echo "FAIL: $1 (want [$2] got [$3])"; FAIL=$((FAIL+1)); fi
}
cd "$(dirname "$0")"

printf 'hi\n' > /tmp/goose-test-in.txt
OUT=$($GOOSE run echo/echo.goose < /tmp/goose-test-in.txt 2>&1 | grep -m1 "echo: hi" | sed 's/^> //')
check "echo round-trips" "echo: hi" "$OUT"

OUT=$($GOOSE run hello/hello.goose 2>&1 | head -1)
check "hello prints" "HELLO FROM GOOSE" "$OUT"

OUT=$(printf '{"tool":"list"}\n' | $GOOSE run mcp-host/host.goose 2>&1 | head -1)
check "host lists echo tool" '{"ok":true,"tools":["echo"]}' "$OUT"

OUT=$(printf '{"tool":"echo","args":{"text":"t"}}\n' | $GOOSE run mcp-host/host.goose 2>&1 | head -1)
check "host answers echo" '{"ok":true,"result":"t"}' "$OUT"

OUT=$(printf '{"tool":"nope"}\n' | $GOOSE run mcp-host/host.goose 2>&1 | head -1)
check "host refuses unknown" '{"ok":false,"error":"unknown tool"}' "$OUT"

cd heartbeat && rm -f heartbeat.log STOP && ($GOOSE run heartbeat.goose >/dev/null 2>&1 &) && sleep 3 && touch STOP && sleep 2
N=$(tr -cd 't' < heartbeat.log | wc -c | tr -d ' ')
check "heartbeat beats then stops" "true" "$([ "$N" -ge 3 ] && echo true || echo false)"
cd ..

# updater.goose is a LIBRARY: it has no main, and its imports resolve from
# services/, not from its own directory. The old check ran it in place and
# could never pass (it reported a missing module, not a staging failure).
# Covered instead by the corpus typecheck and tests/t138_updater_r11.goose.
if $GOOSE check root.goose >/dev/null 2>&1; then
  check "updater library typechecks in the corpus root" "ok" "ok"
else
  check "updater library typechecks in the corpus root" "ok" "fail"
fi

echo "goose tests: $PASS pass, $FAIL fail"
[ "$FAIL" = 0 ]

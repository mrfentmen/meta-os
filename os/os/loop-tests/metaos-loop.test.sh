#!/bin/sh
# metaos-loop.test.sh — run bin/metaos-loop against throwaway git repos
# with a stub agent. No real OpenCode, no network, no systemd.
#
# Usage: sh metaos-loop.test.sh [path-to-metaos-loop]
# Exit 0 = all scenarios pass. Each scenario prints ok / FAIL.
set -u

DRIVER="${1:-$(dirname "$0")/../bin/metaos-loop}"
[ -f "$DRIVER" ] || { echo "driver not found: $DRIVER" >&2; exit 1; }
DRIVER_ABS="$(cd "$(dirname "$DRIVER")" && pwd)/$(basename "$DRIVER")"

PASS=0; FAILED=0
FAILED_NAMES=""

note() { printf '%s\n' "$*"; }
ok()   { PASS=$((PASS+1)); note "ok   - $1"; }
bad()  { FAILED=$((FAILED+1)); FAILED_NAMES="$FAILED_NAMES $1"; note "FAIL - $1"; }

# fresh_repo: build a clean repo + state dir in $WORK for scenario $1.
fresh_repo() {
    WORK="$(mktemp -d "/tmp/metaos-loop-test.$1.XXXXXX")"
    REPO="$WORK/repo"; STATE="$WORK/state"
    mkdir -p "$REPO" "$STATE" "$WORK/bin"
    (
        cd "$REPO" || exit 1
        git init -q
        git config user.email test@example.invalid
        git config user.name loop-test
        echo "base" > file.txt
        printf '# queue\n\n- [ ] Improve the widget.\n' > LOOP_TASKS.md
        git add -A && git commit -qm "init"
    )
    # Stub agent: behavior from $STUB_MODE; writes a run marker either way.
    cat > "$WORK/bin/opencode" <<EOF
#!/bin/sh
echo ran > "$WORK/agent-ran"
case "\${STUB_MODE:-change}" in
    change)   echo "agent change" >> "$REPO/file.txt" ;;
    none)     : ;;
    fail)     exit 3 ;;
    excluded) mkdir -p "$REPO/bus-tools"; echo x > "$REPO/bus-tools/tool.py" ;;
    stopmid)  touch "$STATE/STOP"; echo "agent change" >> "$REPO/file.txt" ;;
esac
exit 0
EOF
    chmod 755 "$WORK/bin/opencode"
    BASE_HEAD="$(cd "$REPO" && git rev-parse HEAD)"
    unset STUB_MODE TEST_CMD
    TEST_CMD_VALUE=true
}

# run_loop: invoke the driver with the scenario env; sets RC.
run_loop() {
    env -i PATH="$WORK/bin:/usr/local/bin:/usr/bin:/bin" HOME="$WORK" \
        METAOS_LOOP_REPO="$REPO" METAOS_LOOP_STATE="$STATE" \
        METAOS_LOOP_OPENCODE=opencode \
        METAOS_LOOP_TEST_CMD="$TEST_CMD_VALUE" \
        METAOS_LOOP_MAX_PER_DAY="${MAX_PER_DAY_VALUE:-8}" \
        STUB_MODE="${STUB_MODE:-change}" \
        sh "$DRIVER_ABS" > "$WORK/out" 2>&1
    RC=$?
}

head_now() { (cd "$REPO" && git rev-parse HEAD); }
logged()   { grep -q " $1 " "$STATE/loop.log" 2>/dev/null; }
cleanup()  { rm -rf "$WORK"; }

# 1. Green cycle commits, closes the task, tags a checkpoint, logs committed.
fresh_repo green
run_loop
if [ "$RC" -eq 0 ] && [ "$(head_now)" != "$BASE_HEAD" ] \
   && grep -q '^- \[x\] Improve the widget\.' "$REPO/LOOP_TASKS.md" \
   && (cd "$REPO" && git tag -l 'metaos-loop/cp-*' | grep -q .) \
   && logged committed; then ok "green cycle commits + closes task + checkpoint tag"; else bad "green cycle"; sed -n '1,5p' "$WORK/out"; fi
cleanup

# 2. Red gate rolls back: no commit, change reverted, task stays open.
fresh_repo gate
TEST_CMD_VALUE=false
run_loop
if [ "$RC" -eq 1 ] && [ "$(head_now)" = "$BASE_HEAD" ] \
   && ! grep -q "agent change" "$REPO/file.txt" \
   && grep -q '^- \[ \] Improve the widget\.' "$REPO/LOOP_TASKS.md" \
   && logged gate-red; then ok "red gate rolls back"; else bad "red gate rollback"; fi
cleanup

# 3. Excluded path touch rolls back, including the untracked file itself.
fresh_repo excluded
STUB_MODE=excluded
run_loop
if [ "$RC" -eq 1 ] && [ "$(head_now)" = "$BASE_HEAD" ] \
   && [ ! -e "$REPO/bus-tools" ] && logged excluded-touch \
   && [ -z "$(cd "$REPO" && git status --porcelain)" ]; then ok "excluded touch rolls back clean"; else bad "excluded touch rollback"; fi
cleanup

# 4. STOP before a cycle: halt, agent never runs.
fresh_repo stopbefore
touch "$STATE/STOP"
run_loop
if [ "$RC" -eq 0 ] && [ ! -e "$WORK/agent-ran" ] && logged stopped; then ok "STOP before cycle halts"; else bad "STOP before cycle"; fi
cleanup

# 5. STOP appearing mid-cycle: rollback, exit 0, nothing committed.
fresh_repo stopmid
STUB_MODE=stopmid
run_loop
if [ "$RC" -eq 0 ] && [ "$(head_now)" = "$BASE_HEAD" ] \
   && ! grep -q "agent change" "$REPO/file.txt" && logged stopped; then ok "STOP mid-cycle rolls back"; else bad "STOP mid-cycle"; fi
cleanup

# 6. Live lock blocks a second cycle.
fresh_repo lock
mkdir "$STATE/lock"
sleep 30 & SLEEPER=$!
echo "$SLEEPER" > "$STATE/lock/pid"
run_loop
kill "$SLEEPER" 2>/dev/null; wait "$SLEEPER" 2>/dev/null
if [ "$RC" -eq 0 ] && [ ! -e "$WORK/agent-ran" ] && logged locked; then ok "live lock blocks cycle"; else bad "live lock"; fi
cleanup

# 7. Daily cap holds.
fresh_repo cap
MAX_PER_DAY_VALUE=1
printf '1\n' > "$STATE/cycles-$(date +%Y-%m-%d)"
run_loop
if [ "$RC" -eq 0 ] && [ ! -e "$WORK/agent-ran" ] && logged capped; then ok "daily cap holds"; else bad "daily cap"; fi
cleanup

# 8. Dirty tree is refused.
fresh_repo dirty
echo "human edit" >> "$REPO/file.txt"
run_loop
if [ "$RC" -eq 1 ] && [ ! -e "$WORK/agent-ran" ] && logged dirty-tree; then ok "dirty tree refused"; else bad "dirty tree"; fi
cleanup

# 9. Green run with no change: nothing committed, logged no-change.
fresh_repo nochange
STUB_MODE=none
run_loop
if [ "$RC" -eq 0 ] && [ "$(head_now)" = "$BASE_HEAD" ] && logged no-change; then ok "no-change cycle commits nothing"; else bad "no-change"; fi
cleanup

# 10. Agent failure rolls back.
fresh_repo agentfail
STUB_MODE=fail
run_loop
if [ "$RC" -eq 1 ] && [ "$(head_now)" = "$BASE_HEAD" ] && logged agent-failed; then ok "agent failure rolls back"; else bad "agent failure"; fi
cleanup

# 11. Empty queue: clean exit, no agent run.
fresh_repo notasks
printf '# queue\n\n(no open tasks)\n' > "$REPO/LOOP_TASKS.md"
(cd "$REPO" && git add -A && git commit -qm "empty queue")
run_loop
if [ "$RC" -eq 0 ] && [ ! -e "$WORK/agent-ran" ] && logged no-tasks; then ok "empty queue exits clean"; else bad "empty queue"; fi
cleanup

# 12. The driver must never force-push: no non-comment line may carry --force.
if grep -v '^[[:space:]]*#' "$DRIVER_ABS" | grep -q -- '--force'; then bad "driver uses --force in code"; else ok "driver never force-pushes (code)"; fi

note "---"
note "passed: $PASS, failed: $FAILED"
[ "$FAILED" -eq 0 ] || { note "failed scenarios:$FAILED_NAMES"; exit 1; }
exit 0

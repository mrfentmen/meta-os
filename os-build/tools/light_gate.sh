#!/usr/bin/env bash
# os-build/tools/light_gate.sh — the clean-clone gate with the heavy stages
# removed (BOND_LIGHT_LANES.md lane 5, 2026-11-02).
#
# What it does: clones this repo's HEAD into a temp dir, proves the clone is
# the same tree, runs the boot-log/doc checks from os-build/gates.md against
# the committed logs, and runs the 8GB-safe suites (Node + Python) inside the
# clone. It never invokes cargo and never starts QEMU; those omissions are
# printed as SKIP lines so they cannot be mistaken for silent passes.
#
# Exit codes: 0 = every check passed (warnings allowed, see LIGHT_GATE.md),
#             1 = a real check failed, 2 = a required tool is missing.
#
# Usage: ./os-build/tools/light_gate.sh
# Env:   KEEP=1  keep the temp dir even on success (it is always kept on fail)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/metaos-light-gate.XXXXXX")"
LOGS="$WORK/logs"
CLONE="$WORK/clone"
KEEP="${KEEP:-0}"

PASS=0
FAIL=0
WARN=0
GATE_FAILED=0

mkdir -p "$LOGS"

cleanup() {
  if [ "${GATE_FAILED:-0}" -eq 0 ] && [ "$KEEP" -ne 1 ]; then
    rm -rf "$WORK"
  else
    printf '\ntemp dir kept for inspection: %s\n' "$WORK"
  fi
}
trap cleanup EXIT

ok()   { PASS=$((PASS + 1)); printf '  ok   %s\n' "$1"; }
bad()  { FAIL=$((FAIL + 1)); GATE_FAILED=1; printf '  FAIL %s\n' "$1"; }
warn() { WARN=$((WARN + 1)); printf '  WARN %s\n' "$1"; }

need() {
  if ! command -v "$1" >/dev/null 2>&1; then
    printf 'light_gate: missing required tool: %s\n' "$1" >&2
    GATE_FAILED=1
    exit 2
  fi
}

need git
need node
need npm
need python3

HASHER=""
if command -v shasum >/dev/null 2>&1; then
  HASHER="shasum -a 256"
elif command -v sha256sum >/dev/null 2>&1; then
  HASHER="sha256sum"
else
  printf 'light_gate: need shasum or sha256sum\n' >&2
  GATE_FAILED=1
  exit 2
fi

printf '== light gate (no cargo, no QEMU) ==\n'
printf 'repo:   %s\n' "$ROOT"
printf 'tools:  git %s | node %s | npm %s | python %s\n' \
  "$(git --version | awk '{print $3}')" \
  "$(node --version)" \
  "$(npm --version)" \
  "$(python3 -V 2>&1 | awk '{print $2}')"

COMMIT="$(git -C "$ROOT" rev-parse --verify HEAD)"
printf 'commit: %s\n' "$COMMIT"

# ---------------------------------------------------------------------------
# Stage 1 — clean clone
# ---------------------------------------------------------------------------
printf '\n== clone ==\n'
if git clone --quiet --no-hardlinks "$ROOT" "$CLONE" 2>"$LOGS/clone.err"; then
  ok "cloned HEAD into a fresh temp dir"
else
  bad "git clone failed: $(tr '\n' ' ' <"$LOGS/clone.err")"
  exit 1
fi

if git -C "$CLONE" checkout --quiet "$COMMIT" 2>"$LOGS/checkout.err"; then
  ok "checked out $COMMIT"
else
  bad "checkout of $COMMIT failed: $(tr '\n' ' ' <"$LOGS/checkout.err")"
fi

CLONE_COMMIT="$(git -C "$CLONE" rev-parse HEAD)"
if [ "$CLONE_COMMIT" = "$COMMIT" ]; then
  ok "clone HEAD equals source HEAD"
else
  bad "clone HEAD $CLONE_COMMIT != source HEAD $COMMIT"
fi

# ---------------------------------------------------------------------------
# Stage 2 — tree comparison
# ---------------------------------------------------------------------------
printf '\n== tree ==\n'
git -C "$ROOT" ls-files | LC_ALL=C sort >"$WORK/root.files"
git -C "$CLONE" ls-files | LC_ALL=C sort >"$WORK/clone.files"

if cmp -s "$WORK/root.files" "$WORK/clone.files"; then
  ok "tracked file list identical ($(wc -l <"$WORK/root.files" | tr -d ' ') files)"
else
  bad "tracked file lists differ"
  diff -u "$WORK/root.files" "$WORK/clone.files" | head -20 || true
fi

DIRTY="$(git -C "$ROOT" status --porcelain | wc -l | tr -d ' ')"
if [ "$DIRTY" -eq 0 ]; then
  # Clean tree: hash the actual bytes of every tracked file in both trees.
  (
    cd "$ROOT"
    while IFS= read -r f; do $HASHER "./$f"; done <"$WORK/root.files"
  ) >"$WORK/root.sha"
  (
    cd "$CLONE"
    while IFS= read -r f; do $HASHER "./$f"; done <"$WORK/clone.files"
  ) >"$WORK/clone.sha"
  if cmp -s "$WORK/root.sha" "$WORK/clone.sha"; then
    ok "sha256 of every tracked file identical"
  else
    bad "tracked file contents differ"
    diff -u "$WORK/root.sha" "$WORK/clone.sha" | head -20 || true
  fi
else
  # A dirty worktree is normal while a lane is in flight. A clean-clone gate
  # compares committed history: hash-for-hash HEAD tree vs the clone's HEAD
  # tree. Say so, so nobody reads this as a worktree comparison.
  warn "working tree is dirty ($DIRTY path(s)); comparing committed HEAD trees, not worktree bytes"
  git -C "$ROOT" ls-tree -r HEAD >"$WORK/root.tree"
  git -C "$CLONE" ls-tree -r HEAD >"$WORK/clone.tree"
  if cmp -s "$WORK/root.tree" "$WORK/clone.tree"; then
    ok "committed HEAD tree identical ($(wc -l <"$WORK/root.tree" | tr -d ' ') entries)"
  else
    bad "committed HEAD trees differ"
    diff -u "$WORK/root.tree" "$WORK/clone.tree" | head -20 || true
  fi
fi

# ---------------------------------------------------------------------------
# Stage 3 — doc checks (boot logs from gates.md, lane-doc paths)
# ---------------------------------------------------------------------------
printf '\n== docs ==\n'
GATES="$ROOT/os-build/gates.md"
LANE_DOC="$ROOT/os-build/BOND_LIGHT_LANES.md"

if [ -f "$GATES" ]; then
  ok "os-build/gates.md exists"
else
  bad "os-build/gates.md missing"
fi

# Exact boot-log lines, copied from os-build/gates.md (M-1). K3's line is
# expected to fail until gates.md and K3-boot.txt agree; that is a finding,
# not something this script papers over.
check_line() {
  local label="$1" file="$2" pat="$3" mode="${4:-fixed}"
  if [ ! -f "$ROOT/$file" ]; then
    bad "$label — missing $file"
    return
  fi
  if [ "$mode" = "regex" ]; then
    grep -aEq "$pat" "$ROOT/$file"
  else
    grep -aFq "$pat" "$ROOT/$file"
  fi && ok "$label — $file matches '$pat'" \
    || bad "$label — no match for '$pat' in $file"
}

check_line "K1 banner"   os-build/logs/K1-boot.txt "META OS KERNEL - alive (K1)"
check_line "K2 banner"   os-build/logs/K2-boot.txt "META OS - milestone K2"
check_line "K3 banner"   os-build/logs/K3-boot.txt "META OS - milestone K3"
check_line "K3 fault"    os-build/logs/K3-fault.txt "INT exception page-fault"
check_line "K4 memory"   os-build/logs/K4-boot.txt "mem summary: K4 up"
check_line "K5 ticks"    os-build/logs/K5-boot.txt "uptime .* ticks" regex
check_line "K6 entry"    os-build/logs/K6-repro-main-2026-11-01.txt "user hello: entry 0x600000000000"
check_line "K6 hello"    os-build/logs/K6-repro-main-2026-11-01.txt "HELLO FROM USERSPACE"
check_line "K6 fault"    os-build/logs/K6-repro-main-2026-11-01.txt "INT user page-fault"

# The hardcoded patterns above must still be the patterns gates.md states,
# or the check has quietly stopped testing the documented gate.
for pat in \
  "META OS KERNEL - alive (K1)" \
  "META OS - milestone K2" \
  "META OS - milestone K3" \
  "INT exception page-fault" \
  "mem summary: K4 up" \
  "uptime .* ticks" \
  "user hello: entry 0x600000000000" \
  "HELLO FROM USERSPACE" \
  "INT user page-fault"
do
  grep -aFq "$pat" "$GATES" || warn "gate pattern not stated in gates.md: '$pat'"
done

# K7: gates.md says NO LOG and the banner ruling is K6. Assert no committed
# log carries a K7 claim; a file NAME is not a claim.
if grep -aEq 'milestone K7|\(K7\)' "$ROOT"/os-build/logs/*.txt 2>/dev/null; then
  bad "a committed log carries a K7 claim, but gates.md says K7: NO LOG"
else
  ok "K7 — no committed log carries a K7 claim"
fi
if [ -f "$ROOT/os-build/logs/K7-boot.txt" ]; then
  warn "gates.md says K7: NO LOG but os-build/logs/K7-boot.txt exists (banner says K6); wording is stale"
fi

# Every file path the lane doc names must exist. The doc is prose, so pull
# path-shaped tokens; zero matches is reported, never assumed.
if [ -f "$LANE_DOC" ]; then
  # A path must have a dotted file name after a slash: "HTML/JS" and
  # "build/check" are prose, not paths.
  REFS="$(grep -oE '[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]*\.[A-Za-z0-9]+' "$LANE_DOC" | sort -u || true)"
  if [ -z "$REFS" ]; then
    ok "lane doc has no concrete file-path references to resolve"
  else
    while IFS= read -r ref; do
      [ -z "$ref" ] && continue
      if [ -e "$ROOT/$ref" ]; then
        ok "lane-doc path exists: $ref"
      else
        bad "lane-doc path missing: $ref"
      fi
    done <<<"$REFS"
  fi
else
  bad "os-build/BOND_LIGHT_LANES.md missing"
fi

# The lane's own working sources, named in BOND_LIGHT_LANES.md by role
# rather than path. If one is renamed, the lane's claims lose their anchor.
for src in \
  js/surfaces.js server/queue.mjs agents/runtime.mjs \
  kernel/src/user.rs kernel/src/mem.rs kernel/src/tasks.rs kernel/src/interrupts.rs \
  tests/goose-programs.test.mjs package.json
 do
  if [ -e "$ROOT/$src" ]; then
    ok "lane source exists: $src"
  else
    bad "lane source missing: $src"
  fi
 done

# ---------------------------------------------------------------------------
# Stage 4 — suites (8GB-safe: Node + Python, no install, no network)
# ---------------------------------------------------------------------------
printf '\n== suites ==\n'

summarize_node() {
  grep -aE '^# (pass|fail) ' "$1" | tr '\n' ' ' | sed 's/  */ /g' || true
}
summarize_pytest() {
  tail -n 1 "$1" | sed 's/^=* *//; s/ *=*$//'
}

run_suite() {
  local name="$1"
  shift
  local log="$LOGS/$name.log"
  local status=0
  set +e
  ( cd "$CLONE" && "$@" ) >"$log" 2>&1
  status=$?
  set -e
  if [ "$status" -eq 0 ]; then
    case "$name" in
      npm-test)      ok "npm test — $(summarize_node "$log")" ;;
      pytest-light)  ok "pytest — $(summarize_pytest "$log")" ;;
      *)             ok "$name — exit 0" ;;
    esac
  else
    bad "$name — exit $status (log: $log)"
    tail -n 20 "$log"
  fi
}

run_suite npm-test npm test

if python3 -m pytest --version >/dev/null 2>&1; then
  # One directory per invocation: custos and officina both contain a
  # test_pack.py, and a single pytest run collides on the module name.
  run_suite pytest-queue python3 -m pytest tests/queue-python -q
  run_suite pytest-custos python3 -m pytest tests/custos -q
  run_suite pytest-officina python3 -m pytest tests/officina -q
else
  bad "pytest is not installed; the Python suites cannot be claimed"
fi

# ---------------------------------------------------------------------------
# Stage 5 — named omissions (never silent)
# ---------------------------------------------------------------------------
printf '\n== not run (8GB lane) ==\n'
printf '  SKIP cargo build/check (8GB lane)\n'
printf '  SKIP QEMU (8GB lane)\n'

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
printf '\n'
if [ "$GATE_FAILED" -eq 0 ]; then
  printf 'LIGHT GATE: PASS — %d ok, %d warn\n' "$PASS" "$WARN"
else
  printf 'LIGHT GATE: FAIL — %d ok, %d fail, %d warn\n' "$PASS" "$FAIL" "$WARN"
fi
printf 'note: a green light gate is NOT a green full gate.sh (cargo + QEMU stages omitted).\n'
exit "$GATE_FAILED"

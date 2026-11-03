#!/usr/bin/env bash
# os-build/tools/parity_lane.sh — Bond's Lane 4 (parity reading).
#
# Runs the Goose typecheck (or a compile-only fallback when the installed
# compiler has no -check) and the parity tests that are pure text reads.
# It never builds the Rust workspace and never boots QEMU.
#
#   bash os-build/tools/parity_lane.sh
#   PARITY_RUST=1 bash os-build/tools/parity_lane.sh   # adds ONE crate's
#                                                      # Rust parity test
#
# Honest by construction: a missing tool is SKIP, a real failure is FAIL,
# and the exit status is non-zero only when a stage that actually ran failed.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

DRY_RUN=0
case "${1:-}" in
  --dry-run) DRY_RUN=1 ;;
  "") ;;
  *) echo "usage: parity_lane.sh [--dry-run]" >&2; exit 2 ;;
esac

PASS=0
FAIL=0
SKIP=0
pass() { echo "PASS  $*"; PASS=$((PASS + 1)); }
fail() { echo "FAIL  $*"; FAIL=$((FAIL + 1)); }
skip() { echo "SKIP  $*"; SKIP=$((SKIP + 1)); }

echo "== Lane 4: parity reading =="
echo "root: $ROOT"
echo

if [ "$DRY_RUN" = 1 ]; then
  echo "DRY RUN — would compare:"
  echo "  Stage 1: goose typecheck over services/*/*.goose (or COMPILE fallback)"
  echo "  Stage 2: node --test tests/product-parity.test.mjs"
  echo "  Stage 2: python3 -m pytest os/tests/test_bustools_parity.py -q"
  echo "  Stage 3: cargo test -p intel --test b13_parity -j1 (only PARITY_RUST=1)"
  echo "dry run: nothing compared"
  exit 0
fi
echo

# ---------------------------------------------------------------------------
# Stage 1 — Goose typecheck.
#
# The compiler documented in os-build/research/goose.md is invoked either as
# `goose -check <file>` (typecheck only) or, when that flag does not exist,
# `goose -o <out.c> <file>` (compile to C, then throw the C away). The second
# form proves the source parses and typechecks; it is reported as COMPILE,
# not as a typecheck, because it is not the same claim.
# ---------------------------------------------------------------------------
echo "-- Stage 1: Goose typecheck --"
GOOSE_BIN="${GOOSE:-}"
if [ -z "$GOOSE_BIN" ]; then
  GOOSE_BIN="$(command -v goose || true)"
fi

if [ -z "$GOOSE_BIN" ] || [ ! -x "$GOOSE_BIN" ]; then
  skip "goose typecheck: goose not on PATH (set GOOSE=/path/to/goose to run; builds from github.com/aardappel/goose)"
else
  echo "goose: $GOOSE_BIN"
  GOOSE_TMP="$(mktemp -d "${TMPDIR:-/tmp}/parity-goose-XXXXXX")"
  trap 'rm -rf "$GOOSE_TMP"' EXIT

  # bash 3.2 on stock macOS has no mapfile; a read loop is portable.
  GOOSE_FILES=()
  while IFS= read -r f; do
    GOOSE_FILES+=("$f")
  done < <(find "$ROOT/services" -mindepth 2 -maxdepth 2 -name '*.goose' -type f | sort)

  if [ "${#GOOSE_FILES[@]}" -eq 0 ]; then
    skip "goose typecheck: no services/*/*.goose files found"
  else
    MODE="check"
    FIRST="${GOOSE_FILES[0]}"
    PROBE_OUT="$GOOSE_TMP/probe.out"
    if ! "$GOOSE_BIN" -check "$FIRST" >"$PROBE_OUT" 2>&1; then
      if grep -Eqi 'unknown|unrecognized|invalid option|usage:' "$PROBE_OUT"; then
        MODE="compile"
        echo "note: this goose has no -check; falling back to COMPILE (goose -o), reported as COMPILE not typecheck"
      fi
    fi

    for f in "${GOOSE_FILES[@]}"; do
      rel="${f#"$ROOT"/}"
      if [ "$MODE" = "check" ]; then
        if "$GOOSE_BIN" -check "$f" >"$GOOSE_TMP/out.txt" 2>&1; then
          pass "goose typecheck: $rel"
        else
          echo "      $(head -n 3 "$GOOSE_TMP/out.txt" | tr '\n' ' ')"
          fail "goose typecheck: $rel"
        fi
      else
        out_c="$GOOSE_TMP/$(basename "$f" .goose).c"
        if "$GOOSE_BIN" -o "$out_c" "$f" >"$GOOSE_TMP/out.txt" 2>&1; then
          pass "goose COMPILE (no -check): $rel"
        else
          echo "      $(head -n 3 "$GOOSE_TMP/out.txt" | tr '\n' ' ')"
          fail "goose COMPILE: $rel"
        fi
      fi
    done
  fi
fi
echo

# ---------------------------------------------------------------------------
# Stage 2 — parity by text read (no build).
# ---------------------------------------------------------------------------
echo "-- Stage 2: text parity --"

if node --test tests/product-parity.test.mjs; then
  pass "product parity: tests/product-parity.test.mjs"
else
  fail "product parity: tests/product-parity.test.mjs (see node output above)"
fi

# This one compares bus-tools/ against the LIVE skill bin under
# ~/workspace/skills/muse-bus-relay/bin. On a machine without that external
# install the test fails for an environment reason, not a drift reason; the
# pytest output names the missing path, and this runner reports that failure
# instead of hiding it.
if python3 -m pytest os/tests/test_bustools_parity.py -q; then
  pass "bus-tools parity: os/tests/test_bustools_parity.py"
else
  fail "bus-tools parity: os/tests/test_bustools_parity.py (missing live skill bin or real drift; see pytest output)"
fi
echo

# ---------------------------------------------------------------------------
# Stage 3 — Rust parity, opt-in only.
#
# crates/*/tests/*_parity.rs are behavior tests for the Rust ports. They read
# checked-in fixtures and sources, but running them still compiles that crate
# and its dependencies, so they are not part of the default 8GB lane.
# ---------------------------------------------------------------------------
echo "-- Stage 3: Rust parity (opt-in) --"
if [ "${PARITY_RUST:-0}" = "1" ]; then
  if cargo test -p intel --test b13_parity -j1; then
    pass "rust parity: cargo test -p intel --test b13_parity -j1"
  else
    fail "rust parity: cargo test -p intel --test b13_parity -j1"
  fi
else
  skip "cargo test -p intel --test b13_parity -j1 (opt-in: cold compile, 8GB lane; set PARITY_RUST=1)"
fi
echo

echo "== summary: $PASS pass, $FAIL fail, $SKIP skip =="
[ "$FAIL" -eq 0 ]

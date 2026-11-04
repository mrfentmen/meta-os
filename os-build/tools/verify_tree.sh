#!/bin/sh
# verify_tree.sh — one offline verification entry point for the Meta OS tree.
#
#   sh os-build/tools/verify_tree.sh [--json]
#
# No boot, no network, no arguments besides --json. Prints one table row per
# check:  check | result | detail.  Result is PASS, FAIL, or
# "absent (owned by OS-N)" when another lane's checker has not landed yet —
# a missing lane is never a pass, and the run continues past it. If any row
# fails, the run prints "DEAD: <names>" (the proof_session.sh contract) and
# exits 1. Timing goes to stderr so --json stays pure JSON (one object per
# row). Works from any working directory; uses find, never git, so it also
# works from a tree without a checkout.
set -u

HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
ROOT="$(CDPATH= cd -- "$HERE/../.." && pwd)"
MODE="table"
[ "${1:-}" = "--json" ] && MODE="json"

START=$(date +%s 2>/dev/null || echo 0)

# POSIX newline (command substitution strips trailing newlines, so rows would
# glue together without this).
NL=$(printf '\nX'); NL=${NL%X}

# Expected checker paths owned by other lanes. Missing = absent, not failure.
OS1_CHECK="os-build/identity/check_strings.sh"
OS1_ALLOWLIST="os-build/identity/ALLOWLIST.tsv"
OS3_LAUNCHER="agent-layer/desktop-entries/selftest.sh"
OS3_DESKTOP="agent-layer/desktop-entries/check_desktop.sh"

ROWS=""
FAIL_NAMES=""

# row <name> <result> <detail> — detail must already be single-line.
row() {
  _n="$1"; _r="$2"; _d="$3"
  if [ "$MODE" = "json" ]; then
    _d=$(printf '%s' "$_d" | sed 's/\\/\\\\/g; s/"/\\"/g')
    ROWS="${ROWS}$(printf '{"check":"%s","result":"%s","detail":"%s"}' "$_n" "$_r" "$_d")$NL"
  else
    ROWS="${ROWS}$(printf '%s | %s | %s' "$_n" "$_r" "$_d")$NL"
  fi
  if [ "$_r" = "FAIL" ]; then
    FAIL_NAMES="${FAIL_NAMES:+$FAIL_NAMES,}$_n"
  fi
}

# run_checker <row> <owner> <path> — absent-tolerant external checker w/ --check.
run_checker() {
  _row="$1"; _owner="$2"; _path="$3"
  if [ ! -f "$ROOT/$_path" ]; then
    row "$_row" "absent (owned by $_owner)" "$_path not present yet"
    return 0
  fi
  if [ ! -x "$ROOT/$_path" ]; then
    row "$_row" "FAIL" "$_path present but not executable"
    return 0
  fi
  if _out=$("sh" "$ROOT/$_path" --check 2>&1); then
    row "$_row" "PASS" "$(printf '%s' "$_out" | tail -1 | cut -c1-120)"
  else
    row "$_row" "FAIL" "$(printf '%s' "$_out" | tail -2 | tr '\n' ';' | cut -c1-160)"
  fi
}

# --- row 1: the allowlist file itself (OS-1 writes it, OS-4 only reads it)
if [ -f "$ROOT/$OS1_ALLOWLIST" ]; then
  _n=$(grep -c . "$ROOT/$OS1_ALLOWLIST" 2>/dev/null || echo 0)
  row "allowlist" "PASS" "$OS1_ALLOWLIST present with $_n non-empty lines"
else
  row "allowlist" "absent (owned by OS-1)" "$OS1_ALLOWLIST not present yet"
fi

# --- rows 2-4: other lanes' checkers, by path
run_checker "identity-strings" "OS-1" "$OS1_CHECK"
run_checker "launcher-allowlist" "OS-3" "$OS3_LAUNCHER"
run_checker "desktop-entries" "OS-3" "$OS3_DESKTOP"

# --- row 5: tree references (OS-4, inline): every shipped .desktop file must
# have Name= and Exec=, and every absolute Icon=/ path must exist in the tree.
_desktop_dirs=""
for _d in agent-layer/desktop-entries metaos-theme/apps os-build/iso/payload-theme/apps; do
  [ -d "$ROOT/$_d" ] && _desktop_dirs="$_desktop_dirs $ROOT/$_d"
done
_bad=""
_count=0
if [ -n "$_desktop_dirs" ]; then
for _f in $(find $_desktop_dirs -name '*.desktop' 2>/dev/null); do
  _count=$((_count + 1))
  grep -q '^Name=' "$_f" 2>/dev/null || _bad="$_bad $(basename "$_f"):no-Name"
  grep -q '^Exec=' "$_f" 2>/dev/null || _bad="$_bad $(basename "$_f"):no-Exec"
  _icon=$(sed -n 's/^Icon=//p' "$_f" 2>/dev/null | head -1)
  case "$_icon" in
    /*) [ -e "$ROOT$_icon" ] || _bad="$_bad $(basename "$_f"):icon-missing" ;;
  esac
done
fi
if [ -z "$_bad" ]; then
  row "tree-refs" "PASS" "$_count .desktop files: Name+Exec present, absolute icons resolve"
else
  row "tree-refs" "FAIL" "$(printf '%s' "$_bad" | cut -c1-160)"
fi

# --- row 6: no Ubuntu in shipped files (OS-4, inline). Scope is source that
# ships, not evidence: payload theme, agent payload, worlds, identity, iso
# build files. os-build/logs (proof output) and .git are excluded on purpose.
# Without OS-1's allowlist every hit counts; with it, listed path:pattern
# pairs (compat/attribution/generated) are subtracted before the verdict.
_scope=""
for _d in os-build/iso/payload-theme agents os/worlds os-build/identity metaos-theme os-build/iso/calamares os-build/iso/plymouth os-build/iso/splash; do
  [ -e "$ROOT/$_d" ] && _scope="$_scope $ROOT/$_d"
done
for _f in os-build/iso/build_iso.sh os-build/iso/build-arm64-inner.sh os-build/iso/finalize-iso-tree.sh os-build/iso/merge-layers.sh os-build/iso/metaos-install.sh; do
  [ -f "$ROOT/$_f" ] && _scope="$_scope $ROOT/$_f"
done
_hits=""
if [ -n "$_scope" ]; then
  # shellcheck disable=SC2086
  _hits=$(grep -rIl -i "ubuntu" $_scope 2>/dev/null | grep -v "/\.git/" || true)
fi
if [ -f "$ROOT/$OS1_ALLOWLIST" ] && [ -n "$_hits" ]; then
  _kept=""
  for _h in $_hits; do
    _rel=${_h#"$ROOT"/}
    _excused=0
    while IFS="$(printf '\t')" read -r _p _pat _v _why; do
      case "$_p" in ""|\#*) continue ;; esac
      if [ "$_rel" = "$_p" ]; then _excused=1; break; fi
    done < "$ROOT/$OS1_ALLOWLIST"
    [ "$_excused" = "0" ] && _kept="$_kept $_h"
  done
  _hits=$(printf '%s' "$_kept" | tr ' ' '\n' | grep . || true)
fi
if [ -z "$_hits" ]; then
  row "no-ubuntu" "PASS" "no case-insensitive ubuntu in shipped sources"
else
  _n=$(printf '%s' "$_hits" | wc -l | tr -d ' ')
  _sample=$(printf '%s' "$_hits" | head -4 | sed "s|$ROOT/||" | tr '\n' ';' | cut -c1-140)
  row "no-ubuntu" "FAIL" "$_n files mention ubuntu (e.g. $_sample)"
fi

# --- row 7: no unmigrated HOME default (R3, inline). The old pattern
# HOME="${HOME:-/home/ubuntu}" must never come back; the only tolerated
# /home/ubuntu reference in launch code is the last-resort probe in
# os-build/face/meta-desktop.sh:41 (getent + /home/meta win first).
_home_hits=$(grep -rn -F ':-/home/ubuntu' "$ROOT/os-build/face" "$ROOT/os-build/iso" "$ROOT/agent-layer" 2>/dev/null || true)
if [ -z "$_home_hits" ]; then
  row "home-refs" "PASS" "no :-/home/ubuntu default in face/iso launch code"
else
  row "home-refs" "FAIL" "$(printf '%s' "$_home_hits" | head -2 | tr '\n' ';' | cut -c1-160)"
fi

# --- row 8: shipped os-release identity (R3, inline). Every os-release file
# this repo stamps must say ID=metaos and must not mention ubuntu.
_os_bad=""
for _f in os-build/iso/payload-theme/identity/os-release os-build/metaos1-base/dexubuntu/identity/os-release; do
  if [ -f "$ROOT/$_f" ]; then
    grep -q '^ID=metaos' "$ROOT/$_f" || _os_bad="$_os_bad $_f:no-ID-metaos"
    if grep -qi 'ubuntu' "$ROOT/$_f"; then _os_bad="$_os_bad $_f:ubuntu-leak"; fi
  else
    _os_bad="$_os_bad $_f:missing"
  fi
done
if [ -z "$_os_bad" ]; then
  row "os-release-identity" "PASS" "2 shipped os-release files: ID=metaos, no ubuntu"
else
  row "os-release-identity" "FAIL" "$(printf '%s' "$_os_bad" | cut -c1-160)"
fi

# --- output
if [ "$MODE" = "json" ]; then
  printf '[\n'
  _first=1
  printf '%s' "$ROWS" | while IFS= read -r _line; do
    if [ "$_first" = "1" ]; then _first=0; else printf ',\n'; fi
    printf '%s' "$_line"
  done
  printf '\n]\n'
else
  printf 'check | result | detail\n'
  printf '%s' "$ROWS"
fi

END=$(date +%s 2>/dev/null || echo 0)
echo "verify_tree: $(printf '%s' "$ROWS" | grep -c .) rows in $((END - START))s" >&2

if [ -n "$FAIL_NAMES" ]; then
  # DEAD goes to stderr so --json stays pure JSON on stdout.
  echo "DEAD: $FAIL_NAMES" >&2
  exit 1
fi
exit 0

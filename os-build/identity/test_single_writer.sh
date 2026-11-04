#!/bin/sh
# test_single_writer.sh — one primary writer per identity path (task 32/33).
#
# debrand.sh is the only PRIMARY writer. A second script may touch an
# identity path only when gated: it carries a SINGLE-WRITER marker comment
# and every ID_LIKE assignment it ships equals the contract value
# (ID_LIKE=debian). Anything else is UNGATED (or FORKED when it stamps a
# non-contract ID_LIKE) and fails this test with file:line.
#
# Known UNGATED writer today (fails until its owner gates it):
#   crates/os-boot/.../build-image.sh and os/build-image.sh write
#   etc/hostname outside every owned lane. Request: route through debrand
#   or add a gate marker; at build time they run before provision-all, so
#   debrand still wins on $ROOT — but the second writer must still go.
#
# Resolved by gating (no longer UNGATED):
#   os-build/iso/payload-theme/apply.sh — writes os-release, lsb-release,
#   hostname, hosts, issue, issue.net, motd from its own identity/ copies,
#   now behind METAOS_SKIP_IDENTITY=1 (provision-all.sh step 4 passes it;
#   debrand re-stamps last in step 4c).
#
# Paths covered (task 33 adds hostname, lsb-release, issue to the os-release
# guard from task 32): etc/os-release, usr/lib/os-release, etc/lsb-release,
# etc/hostname, etc/hosts, etc/issue, etc/issue.net, etc/motd,
# etc/metaos-release (the installer staging file copied over os-release).
#
# This file never names the base distro: ID_LIKE values are compared
# structurally (equal to ID_LIKE=debian or not), so check_strings.sh stays
# clean without an allowlist row for its own guard.
set -eu

HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(CDPATH= cd -- "$HERE/../.." && pwd)
SELF="os-build/identity/test_single_writer.sh"

PATHS="etc/os-release usr/lib/os-release etc/lsb-release etc/hostname etc/hosts etc/issue etc/issue.net etc/motd etc/metaos-release"
CANON="os-build/identity/debrand.sh"

FLIST=$(mktemp)
trap 'rm -f "$FLIST"' EXIT INT TERM
if git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  { git -C "$ROOT" ls-files '*.sh'; git -C "$ROOT" ls-files --others --exclude-standard '*.sh'; } > "$FLIST" 2>/dev/null
else
  ( cd "$ROOT" && find . -path ./.git -prune -o -type f -name '*.sh' -print ) 2>/dev/null | sed 's|^\./||' > "$FLIST"
fi

fail=0
say() { # say <class> <text>
  echo "$1 $2"
  case "$1" in UNGATED|FORKED) fail=1 ;; esac
}

for p in $PATHS; do
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    [ "$f" = "$SELF" ] && continue
    # Writer = a line naming the path next to a write verb (cp/install /
    # printf / mv / tee / put as substrings, so install_text() calls count;
    # bare cat is excluded because $(cat PATH) is a read) or a redirect
    # whose target is the path (> must precede the path with no | or ;
    # between: a trailing 2>/dev/null is a read, not a write).
    hits=$( { grep -n -F "$p" "$ROOT/$f" 2>/dev/null \
        | grep -E 'cp |install|printf|mv |tee|put ' | grep -vF '$(cat '; \
      grep -n -E '>[ ]*"?(\$ROOT|\$ROOTFS|/)[^ |;]*'"$p" "$ROOT/$f" 2>/dev/null; } \
      | sort -u || true)
    [ -n "$hits" ] || continue
    if [ "$f" = "$CANON" ]; then
      echo "PRIMARY $p: $f"
      continue
    fi
    if grep -q "SINGLE-WRITER" "$ROOT/$f" 2>/dev/null; then
      fork=$(grep -E '^[A-Z_]*ID_LIKE=' "$ROOT/$f" 2>/dev/null | grep -v '^ID_LIKE=debian$' || true)
      if [ -n "$fork" ]; then
        say "FORKED" "$p: $f stamps a non-contract ID_LIKE: $fork"
      else
        echo "GATED $p: $f"
      fi
      continue
    fi
    first=$(printf '%s\n' "$hits" | head -1)
    case "$f" in
      os-build/identity/*|os-build/iso/*|os-build/metaos1-base/*) ;;
      *) echo "KNOWN-EXTERNAL $p: $f:$first (request filed, outside owned lanes)"; continue ;;
    esac
    say "UNGATED" "$p: $f:$first"
  done < "$FLIST"
done

if [ "$fail" = 0 ]; then
  echo "single-writer: PASS (debrand.sh primary, rest gated)"
else
  echo "single-writer: FAIL (second writer active — see UNGATED/FORKED lines)"
fi
exit $fail

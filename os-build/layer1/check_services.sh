#!/usr/bin/env bash
# os-build/layer1/check_services.sh — typecheck the whole Goose corpus.
#
# Why this exists: Goose resolves `import a.b.c;` relative to the ROOT file's
# directory, and a program may export `svc_entry` only once. So the corpus is
# not one program and cannot be checked as one. It is checked as:
#
#   services/root.goose          the libraries and the 16 non-entry services
#   services/root_<svc>.goose    one program per service that exports svc_entry
#   (generated)                  one program per test, since every test has its
#                                own main, its own counters and its own exit
#
# Exit status is the gate: 0 only when every root and every test typechecks.
#
# Usage: os-build/layer1/check_services.sh [-v]
set -uo pipefail
cd "$(dirname "$0")/../.." || exit 2

verbose=0
[ "${1:-}" = "-v" ] && verbose=1

ok=0
fail=0
failed=()

check() {
    local root="$1" label="$2" out
    if out="$(goose check --color never "$root" 2>&1)"; then
        ok=$((ok + 1))
        printf '  ok    %s\n' "$label"
    else
        fail=$((fail + 1))
        failed+=("$label")
        printf '  FAIL  %s  (%s errors)\n' "$label" "$(grep -c 'error:' <<<"$out")"
        if [ "$verbose" = 1 ]; then
            grep 'error:' <<<"$out" | sed 's/^/          /' | head -20
        fi
    fi
}

echo "== roots"
for r in services/root.goose services/root_*.goose; do
    [ -e "$r" ] || continue
    check "$r" "$r"
done

echo "== tests"
tmp="services/.chk_$$.goose"
cleanup() { rm -f "$tmp"; }
trap cleanup EXIT

for t in services/tests/*.goose; do
    name="$(basename "$t" .goose)"
    # A test declares its own main, so the generated root must not add one.
    printf 'import tests.%s;\n' "$name" > "$tmp"
    check "$tmp" "tests/$name"
done

echo
printf 'typechecked: %d ok, %d failed\n' "$ok" "$fail"
if [ "$fail" -ne 0 ]; then
    printf 'failed: %s\n' "${failed[*]}"
    exit 1
fi
exit 0

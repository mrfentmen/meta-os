#!/bin/sh
# test_check_strings.sh — three fixtures, three verdicts (task 42/43).
#
#   clean fixture (no banned words)            -> exit 0
#   fixture with a banned word, not allowlisted -> exit 1
#   fixture with an allowlisted word            -> exit 0
#
# Fixtures live in mktemp -d and are removed on exit. Needs no network,
# no root, no checkout: the checker scans whatever --root points at.
set -eu

CHECKER=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)/check_strings.sh

T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT INT TERM

mkfixture() { # mkfixture <name> : builds $T/<name>/{file,allowlist}
  d="$T/$1"
  mkdir -p "$d/os-build/identity"
  printf '# tsv\n' > "$d/os-build/identity/ALLOWLIST.tsv"
  printf 'all: clean fixture\n' > "$d/note.txt"
}

# 1. clean: no banned words anywhere.
mkfixture clean

# 2. dirty: a banned word with no allowlist row.
mkfixture dirty
printf 'this image still says ubuntu here\n' > "$T/dirty/leak.txt"

# 3. allowed: a banned word covered by an allowlist row (plus the row the
# contract file needs for itself: it literally contains the word Ubuntu).
mkfixture allowed
printf 'this names Ubuntu Mono, the font\n' > "$T/allowed/fonts.txt"
printf 'fonts.txt\tUbuntu\tcompat\treal font name\n' >> "$T/allowed/os-build/identity/ALLOWLIST.tsv"
printf 'os-build/identity/ALLOWLIST.tsv\tUbuntu\tattribution\tthe contract file names the word to cover it\n' >> "$T/allowed/os-build/identity/ALLOWLIST.tsv"

pass=0
fail=0
expect() { # expect <want-exit> <name> <root>
  if sh "$CHECKER" --root "$3" >/dev/null 2>&1; then got=0; else got=1; fi
  if [ "$got" = "$1" ]; then
    echo "ok: $2 (exit $got)"
    pass=$((pass + 1))
  else
    echo "NOT OK: $2 (want exit $1, got $got)"
    fail=$((fail + 1))
  fi
}

expect 0 "clean fixture passes" "$T/clean"
expect 1 "dirty fixture fails" "$T/dirty"
expect 0 "allowlisted fixture passes" "$T/allowed"

echo "test_check_strings: $pass passed, $fail failed"
[ "$fail" = 0 ]

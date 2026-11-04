#!/bin/sh
# check_strings.sh — the Ubuntu-to-Meta sweep as a test.
#
# Scans the tree for the banned words, subtracts os-build/identity/ALLOWLIST.tsv
# and prints one line per surviving hit. Exits 1 if any survive, 0 if clean.
#
#   sh os-build/identity/check_strings.sh              # from the repo root
#   sh /path/to/check_strings.sh                       # from anywhere (task 41)
#   sh os-build/identity/check_strings.sh --explain   # every hit + which row
#                                                     # suppressed it, or why not
#
# Banned words (case-sensitive, whole-word): ubuntu Ubuntu Xubuntu xubuntu
# canonical Canonical. `canonical` matches the English word on purpose: every
# such hit needs an allowlist row that says so explicitly. Whole-word (-w)
# means `dexubuntu`, `canonicalize` and `0ubuntu0` do not match — they are
# tool names, identifiers and version blobs, not the words.
#
# Scope exclusions (also in --help): .git, node_modules, os-build/logs/,
# plan/, and binary files (grep -I). plan/ is working history and logs are
# generated evidence; both are counted in STRINGS_INVENTORY.md, not scanned.
#
# Guest fallback (task 21): if the tree is not a git checkout, scan with
# find + grep instead of git grep. Same words, same exclusions, same verdict.
set -eu

WORDS="ubuntu Ubuntu Xubuntu xubuntu canonical Canonical"

HERE=$(dirname -- "$0")
ROOT=$(CDPATH= cd -- "$HERE/../.." && pwd)
ALLOW="$ROOT/os-build/identity/ALLOWLIST.tsv"
TAB=$(printf '\t')

EXPLAIN=0
for a in "$@"; do
  case "$a" in
    --explain) EXPLAIN=1 ;;
    -h|--help)
      sed -n '2,/^set -eu$/p' "$0" | sed 's/^# \{0,1\}//'
      exit 0 ;;
    *) echo "check_strings: unknown flag $a (try --help)" >&2; exit 2 ;;
  esac
done

# allow <path> <word>: print the row and exit 0 if allowlisted.
allow() {
  [ -f "$ALLOW" ] || return 1
  # Literal tab match: path<TAB>word<TAB>. Fixed-string, whole line start.
  grep -F -m1 -- "$1${TAB}$2${TAB}" "$ALLOW" 2>/dev/null
}

# in_scope <path>: the exclusions, in one place.
in_scope() {
  case "$1" in
    plan/*|os-build/logs/*|*/node_modules/*|.git/*) return 1 ;;
  esac
  return 0
}

HITS=$(mktemp)
trap 'rm -f "$HITS"' EXIT INT TERM

if git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  for w in $WORDS; do
    git -C "$ROOT" grep -n -w -F -I -- "$w" -- . ':!plan' ':!os-build/logs' 2>/dev/null \
      | sed "s/^/$w	/" >> "$HITS" || true
  done
else
  # No checkout (guest tree): same scan with find + grep.
  for w in $WORDS; do
    ( cd "$ROOT" && find . -path ./.git -prune -o -path ./node_modules -prune \
      -o -path ./plan -prune -o -path ./os-build/logs -prune \
      -o -type f -print ) 2>/dev/null \
      | ( cd "$ROOT" && xargs grep -w -F -I -n -- "$w" 2>/dev/null ) \
      | sed "s/^/$w	/" >> "$HITS" || true
  done
fi

total=0
bad=0
if [ -s "$HITS" ]; then
  while IFS= read -r line; do
    w=$(printf '%s' "$line" | cut -f1)
    rest=$(printf '%s' "$line" | cut -f2-)
    path=$(printf '%s' "$rest" | cut -d: -f1)
    # git grep prints paths without ./; find fallback prints ./x.
    path=${path#./}
    total=$((total + 1))
    in_scope "$path" || continue
    if row=$(allow "$path" "$w"); then
      [ "$EXPLAIN" = 1 ] && printf 'ALLOW %s [%s]\n' "$rest" "$row"
    else
      bad=$((bad + 1))
      if [ "$EXPLAIN" = 1 ]; then
        printf 'HIT   %s (word %s: no ALLOWLIST.tsv row for this path)\n' "$rest" "$w"
      else
        printf '%s\n' "$rest"
      fi
    fi
  done < "$HITS"
fi

if [ "$EXPLAIN" = 1 ]; then
  echo "check_strings --explain: $total hits scanned, $bad unsuppressed" >&2
fi
if [ "$bad" -eq 0 ]; then
  echo "check_strings: clean — PASS"
  exit 0
else
  echo "check_strings: $bad unsuppressed hit(s) — FAIL"
  exit 1
fi

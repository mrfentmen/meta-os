#!/bin/sh
# fonts/install.sh — install the six vendored Meta families into a target root.
#
# Usage: sh install.sh ROOT [--check]
#
#   install (default): copy every MANIFEST-declared file to
#     <ROOT>/usr/share/fonts/truetype/meta/ (mode 0644, only when missing or
#     byte-different — cmp first, so a second run copies zero files), install
#     69-meta.conf to <ROOT>/etc/fonts/conf.d/69-meta.conf (same cmp rule),
#     then fc-cache -f the destination when fc-cache exists. Missing or
#     zero-length declared sources are a hard failure: until fonts/ is
#     vendored the installer refuses instead of shipping a half set.
#   --check: verify every MANIFEST-declared file exists and is non-empty, and
#     69-meta.conf parses as XML carrying sans-serif/serif/monospace aliases.
#     Exit 0 on PASS, 1 on any FAIL.
set -eu

HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT="${1:-}"
MODE="${2:-install}"
[ -n "$ROOT" ] || { echo "usage: install.sh ROOT [--check]" >&2; exit 2; }
[ -d "$ROOT/etc" ] && [ -d "$ROOT/usr" ] || {
  echo "install: $ROOT is not a root filesystem (no /etc or /usr)" >&2; exit 1; }

MANIFEST="$HERE/MANIFEST.txt"
CONF_SRC="$HERE/69-meta.conf"
DESTDIR="$ROOT/usr/share/fonts/truetype/meta"
CONF_DST="$ROOT/etc/fonts/conf.d/69-meta.conf"

[ -f "$MANIFEST" ] || { echo "install-GATE-FAIL: missing manifest: $MANIFEST" >&2; exit 1; }

# Declared filenames: field 1 of non-comment, non-blank manifest rows.
FILES=$(awk -F'|' '!/^#/ && NF {print $1}' "$MANIFEST")

fail=0
check_one() { # check_one <file>
  if [ ! -f "$HERE/$1" ]; then
    echo "install-CHECK-FAIL: missing declared file: $1" >&2; fail=1
  elif [ ! -s "$HERE/$1" ]; then
    echo "install-CHECK-FAIL: zero-length declared file: $1" >&2; fail=1
  fi
}

check_conf() {
  if [ ! -s "$CONF_SRC" ]; then
    echo "install-CHECK-FAIL: missing/empty fontconfig source: $CONF_SRC" >&2
    fail=1; return
  fi
  if command -v python3 >/dev/null 2>&1; then
    if conf_msg=$(python3 - "$CONF_SRC" <<'PYEOF' 2>&1
import sys, xml.etree.ElementTree as ET
want = {"sans-serif", "serif", "monospace"}
have = set()
for alias in ET.parse(sys.argv[1]).getroot().iter("alias"):
    fam = alias.find("family")
    if fam is not None and fam.text:
        have.add(fam.text.strip())
missing = want - have
if missing:
    print("missing generic aliases: " + " ".join(sorted(missing)))
    sys.exit(1)
print("conf XML OK; generics: " + " ".join(sorted(have)))
PYEOF
); then
      echo "install-CHECK: $conf_msg"
    else
      echo "install-CHECK-FAIL: 69-meta.conf XML/alias problem: $conf_msg" >&2
      fail=1; return
    fi
  else
    for g in sans-serif serif monospace; do
      grep -q "<family>$g</family>" "$CONF_SRC" || {
        echo "install-CHECK-FAIL: 69-meta.conf lacks <$g> alias" >&2; fail=1; }
    done
  fi
}

if [ "$MODE" = "--check" ]; then
  for f in $FILES; do check_one "$f"; done
  check_conf
  if [ "$fail" -eq 0 ]; then echo "install-CHECK: PASS (all declared files present, conf OK)"
  else echo "install-CHECK: FAIL" >&2; fi
  exit "$fail"
fi

if [ "$MODE" != "install" ]; then
  echo "usage: install.sh ROOT [--check]" >&2; exit 2
fi

# Install mode first re-runs the same gates: never install a half set.
for f in $FILES; do check_one "$f"; done
[ -s "$CONF_SRC" ] || { echo "install-GATE-FAIL: missing/empty: $CONF_SRC" >&2; exit 1; }
if [ "$fail" -ne 0 ]; then echo "install-GATE-FAIL: declared sources missing; vendor fonts/ first (see MANIFEST.txt)" >&2; exit 1; fi

mkdir -p "$DESTDIR" "$(dirname "$CONF_DST")"
copied=0; same=0
for f in $FILES; do
  if [ -f "$DESTDIR/$f" ] && cmp -s "$HERE/$f" "$DESTDIR/$f"; then
    same=$((same + 1))
  else
    install -m644 "$HERE/$f" "$DESTDIR/$f"
    copied=$((copied + 1))
  fi
done
if [ -f "$CONF_DST" ] && cmp -s "$CONF_SRC" "$CONF_DST"; then
  same=$((same + 1)); cstat="conf up-to-date"
else
  install -m644 "$CONF_SRC" "$CONF_DST"
  copied=$((copied + 1)); cstat="conf installed"
fi

if command -v fc-cache >/dev/null 2>&1; then
  if ! fc-cache -f "$DESTDIR" >/dev/null 2>&1; then
    echo "install: note: fc-cache -f failed on $DESTDIR (staged root or fontconfig without that path)"
  fi
else
  echo "install: note: fc-cache absent on this host (macOS); Linux build runs: fc-cache -f $DESTDIR"
fi

echo "install: $copied copied, $same up-to-date -> $DESTDIR ($cstat)"
exit 0

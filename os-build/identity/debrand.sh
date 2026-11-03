#!/bin/sh
# debrand.sh — take Ubuntu's name off a Meta OS root, keep what apt needs.
#
# Two different things live in a Debian-family image: identity (what a person
# reads) and compatibility (what a package manager reads). This script rewrites
# the first and leaves the second alone, on purpose:
#
#   rewritten   /etc/os-release, /usr/lib/os-release, /etc/lsb-release,
#               /etc/issue, /etc/issue.net, login motd scripts
#   kept        ID_LIKE=debian, /etc/apt/sources.list.d/*.sources, package names
#
# It is idempotent and has a --check mode that reads the files back and prints
# PASS/FAIL, so "debranded" is a measurement and not a claim.
#
#   sh os-build/identity/debrand.sh /mnt            # a mounted root
#   sh os-build/identity/debrand.sh /mnt --check
set -eu

ROOT="${1:-/mnt}"
MODE=apply
[ "${2:-}" = "--check" ] && MODE=check
[ -d "$ROOT/etc" ] || { echo "debrand: $ROOT/etc does not exist" >&2; exit 2; }

PRETTY="Meta OS 1.0 (Ribbon)"
CODENAME="ribbon"

os_release() {
  cat <<'EOF'
PRETTY_NAME="Meta OS 1.0 (Ribbon)"
NAME="Meta OS"
VERSION="1.0 (Ribbon)"
VERSION_ID="1.0"
VERSION_CODENAME=ribbon
ID=metaos
ID_LIKE=debian
HOME_URL="https://metaos.local"
SUPPORT_URL="https://metaos.local/support"
BUG_REPORT_URL="https://metaos.local/issues"
EOF
}

check() {
  fail=0
  say() { if [ "$2" = ok ]; then echo "PASS $1"; else echo "FAIL $1 — $3"; fail=1; fi; }
  for f in "$ROOT/etc/os-release" "$ROOT/usr/lib/os-release"; do
    [ -f "$f" ] || { say "$f" no "missing"; continue; }
    grep -qx "PRETTY_NAME=\"$PRETTY\"" "$f" && p=ok || p=no
    grep -qx "ID=metaos" "$f" && i=ok || i=no
    grep -qx "ID_LIKE=debian" "$f" && l=ok || l=no
    grep -q "ubuntu" "$f" && u=no || u=ok
    say "$f pretty" "$p" "PRETTY_NAME is not \"$PRETTY\""
    say "$f id" "$i" "ID is not metaos"
    say "$f id_like" "$l" "ID_LIKE is not debian"
    say "$f no-ubuntu" "$u" "file still mentions ubuntu"
  done
  if [ -f "$ROOT/etc/lsb-release" ]; then
    grep -qx "DISTRIB_ID=MetaOS" "$ROOT/etc/lsb-release" && a=ok || a=no
    grep -qx "DISTRIB_CODENAME=$CODENAME" "$ROOT/etc/lsb-release" && b=ok || b=no
    say "lsb-release id" "$a" "DISTRIB_ID is not MetaOS"
    say "lsb-release codename" "$b" "DISTRIB_CODENAME is not $CODENAME"
  else
    say "lsb-release" no "missing"
  fi
  if [ -f "$ROOT/etc/issue" ]; then
    head -1 "$ROOT/etc/issue" | grep -q "Meta OS 1.0 (Ribbon)" && c=ok || c=no
    say "issue title" "$c" "first line is not the Meta OS title"
    grep -q '\\l' "$ROOT/etc/issue" && d=ok || d=no
    say "issue terminal escape" "$d" "no \\l escape (tty would print a literal backslash)"
  else
    say "issue" no "missing"
  fi
  for s in 10-help-text 50-motd-news; do
    if [ -x "$ROOT/etc/update-motd.d/$s" ]; then say "motd $s disabled" no "still executable"; else say "motd $s disabled" ok ""; fi
  done
  echo "debrand --check: $([ "$fail" = 0 ] && echo PASS || echo FAIL)"
  [ "$fail" = 0 ]
}

if [ "$MODE" = check ]; then check; exit $?; fi

echo "debrand: rewriting identity in $ROOT"
os_release > "$ROOT/etc/os-release"
mkdir -p "$ROOT/usr/lib"
os_release > "$ROOT/usr/lib/os-release"
echo "  wrote /etc/os-release and /usr/lib/os-release (ID=metaos, ID_LIKE=debian)"

cat > "$ROOT/etc/lsb-release" <<EOF
DISTRIB_ID=MetaOS
DISTRIB_RELEASE=1.0
DISTRIB_CODENAME=$CODENAME
DISTRIB_DESCRIPTION="$PRETTY"
EOF
echo "  wrote /etc/lsb-release (MetaOS / $CODENAME)"

# \n and \l must reach agetty as escapes, not as literal characters.
printf '%s \\n \\l\n\n' "$PRETTY" > "$ROOT/etc/issue"
printf '%s\n' "$PRETTY" > "$ROOT/etc/issue.net"
echo "  wrote /etc/issue and /etc/issue.net"

# These two print Canonical help links and Ubuntu's news feed at every login.
# Renamed, not deleted, so a package upgrade is not silently fighting us.
for s in 10-help-text 50-motd-news; do
  if [ -x "$ROOT/etc/update-motd.d/$s" ]; then
    mv "$ROOT/etc/update-motd.d/$s" "$ROOT/etc/update-motd.d/$s.metaos-disabled"
    echo "  disabled motd script $s (renamed .metaos-disabled)"
  fi
done

# Anything a person can open that still says Xubuntu/Ubuntu in a menu or a
# window title. Scoped to the directories the desktop reads, never packages.
for d in usr/share/desktop-directories usr/share/applications; do
  [ -d "$ROOT/$d" ] || continue
  grep -rl "Xubuntu" "$ROOT/$d" 2>/dev/null | while read -r f; do
    sed -i 's/Xubuntu/Meta OS/g; s/Ubuntu/Meta OS/g' "$f"
    echo "  rewrote names in /$d/$(basename "$f")"
  done
done

echo "debrand: done. Verify with --check; apt stays on noble in sources.list.d on purpose."

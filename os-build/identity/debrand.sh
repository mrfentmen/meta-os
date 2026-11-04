#!/bin/sh
# debrand.sh — take Ubuntu's name off a Meta OS root, keep what apt needs.
#
# Two different things live in a Debian-family image: identity (what a person
# reads) and compatibility (what a package manager reads). This script rewrites
# the first and leaves the second alone, on purpose:
#
#   rewritten   /etc/os-release, /usr/lib/os-release, /etc/lsb-release,
#               /etc/issue, /etc/issue.net, /etc/hostname, /etc/hosts
#               (127.0.1.1 line), login motd scripts, dead plymouth themes,
#               stock Xubuntu wallpapers, every backdrop pointer, Xubuntu
#               names in desktop-directories/applications
#   kept        ID_LIKE=debian, /etc/apt/sources.list.d/*.sources, package
#               names, fonts-ubuntu, 90-updates-available (real information)
#
# This is the survivor of the debrand.sh/debrand2.sh pair (OS-1 task 7):
# debrand.sh had the --check contract provision.sh relies on, so debrand2.sh's
# asset/backdrop sections were folded in here. debrand2.sh still exists and
# still runs (provision.sh calls it), but it is now redundant: everything it
# does, this script does. rename_user.sh stays separate — account databases
# are a different failure domain from files.
#
# Modes:
#   sh os-build/identity/debrand.sh /mnt            # apply (old form, kept)
#   sh os-build/identity/debrand.sh /mnt --check    # check (old form, kept)
#   sh .../debrand.sh --apply [--root DIR] [ROOT]   # apply, explicit
#   sh .../debrand.sh --check [--root DIR] [ROOT]   # check: PASS/FAIL per file
#   sh .../debrand.sh --json  [--root DIR] [ROOT]   # check as JSON objects
#
# --apply is idempotent: a second run writes byte-identical files and reports
# zero changes. --check/--json exit non-zero on any failure; nothing fails
# silently. /etc/os-release may be a symlink to ../usr/lib/os-release (that is
# the stock Ubuntu layout): it is written THROUGH, never replaced.
set -eu

MODE=apply
ROOT=""
while [ $# -gt 0 ]; do
  case "$1" in
    --apply) MODE=apply; shift ;;
    --check) MODE=check; shift ;;
    --json) MODE=json; shift ;;
    --root) ROOT="$2"; shift 2 ;;
    -h|--help)
      echo "usage: debrand.sh [--apply|--check|--json] [--root DIR] [ROOT]"
      echo "  ROOT defaults to /mnt. Old forms 'debrand.sh ROOT' and"
      echo "  'debrand.sh ROOT --check' keep working."
      exit 0 ;;
    --) shift; break ;;
    -*) echo "debrand: unknown flag $1" >&2; exit 2 ;;
    *) if [ -z "$ROOT" ]; then ROOT="$1"; else
         if [ "$1" = "--check" ]; then MODE=check; else
           echo "debrand: unexpected argument $1" >&2; exit 2; fi; fi
       shift ;;
  esac
done
[ -n "$ROOT" ] || ROOT=/mnt
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
LOGO=metaos
HOME_URL="https://metaos.local"
SUPPORT_URL="https://metaos.local/support"
BUG_REPORT_URL="https://metaos.local/issues"
EOF
}

CHANGED=0
changed() { CHANGED=$((CHANGED + 1)); echo "  $1"; }

# install_text <dest> <tmpfile>: write only when bytes differ, count changes.
# A symlink destination is written THROUGH (cat >), never replaced.
install_text() {
  dest="$1"; tmp="$2"
  if [ -f "$dest" ] && cmp -s "$tmp" "$dest"; then
    echo "  unchanged $dest"
    return 0
  fi
  if [ -L "$dest" ]; then
    cat "$tmp" > "$dest"
  else
    mkdir -p "$(dirname "$dest")"
    cp -f "$tmp" "$dest"
  fi
  changed "wrote $dest"
}

do_apply() {
  echo "debrand: rewriting identity in $ROOT"

  TMP=$(mktemp)
  os_release > "$TMP"
  # /etc/os-release is a symlink to ../usr/lib/os-release on stock Ubuntu:
  # write through it, then the second write is a no-op by cmp.
  install_text "$ROOT/etc/os-release" "$TMP"
  install_text "$ROOT/usr/lib/os-release" "$TMP"

  cat > "$TMP" <<EOF
DISTRIB_ID=MetaOS
DISTRIB_RELEASE=1.0
DISTRIB_CODENAME=$CODENAME
DISTRIB_DESCRIPTION="$PRETTY"
EOF
  install_text "$ROOT/etc/lsb-release" "$TMP"

  # \n and \l must reach agetty as escapes, not as literal characters.
  printf '%s \\n \\l\n\n' "$PRETTY" > "$TMP"
  install_text "$ROOT/etc/issue" "$TMP"
  printf '%s\n' "$PRETTY" > "$TMP"
  install_text "$ROOT/etc/issue.net" "$TMP"

  # Hostname and the 127.0.1.1 line name the machine; both must say metaos.
  printf 'metaos\n' > "$TMP"
  install_text "$ROOT/etc/hostname" "$TMP"
  TAB=$(printf '\t')
  if grep -q '^127\.0\.1\.1' "$ROOT/etc/hosts" 2>/dev/null; then
    if grep -q "^127\\.0\\.1\\.1[[:space:]]*metaos" "$ROOT/etc/hosts" 2>/dev/null; then
      echo "  unchanged /etc/hosts (127.0.1.1 already metaos)"
    else
      # No sed -i: its backup-suffix argument differs between GNU and BSD sed.
      # No \t in sed either: BSD sed writes a literal t. Build the tab first.
      sed "s/^127\\.0\\.1\\.1.*/127.0.1.1${TAB}metaos/" "$ROOT/etc/hosts" > "$ROOT/etc/hosts.metaos-new" \
        && cat "$ROOT/etc/hosts.metaos-new" > "$ROOT/etc/hosts"
      rm -f "$ROOT/etc/hosts.metaos-new"
      changed "fixed /etc/hosts 127.0.1.1 -> metaos"
    fi
  else
    printf "127.0.1.1${TAB}metaos\n" >> "$ROOT/etc/hosts"
    changed "added /etc/hosts 127.0.1.1 metaos"
  fi

  # These two print Canonical help links and Ubuntu's news feed at every
  # login. Renamed, not deleted, so a package upgrade is not silently
  # fighting us. 90-updates-available is left alone: the pending-security-
  # update count is real information, not branding.
  for s in 10-help-text 50-motd-news; do
    if [ -x "$ROOT/etc/update-motd.d/$s" ]; then
      mv "$ROOT/etc/update-motd.d/$s" "$ROOT/etc/update-motd.d/$s.metaos-disabled"
      changed "disabled motd script $s (renamed .metaos-disabled)"
    else
      echo "  unchanged motd $s (already disabled)"
    fi
  done

  # Dead Ubuntu plymouth themes, folded in from debrand2.sh.
  for d in "$ROOT"/usr/share/plymouth/themes/ubuntu*; do
    [ -e "$d" ] || continue
    rm -rf "$d"
    changed "removed ${d#"$ROOT"}"
  done

  # Stock Xubuntu wallpapers, folded in from debrand2.sh. Refuse if Meta's
  # own wallpaper is not there first: removing the only backdrop would
  # leave the desktop black.
  WALL="$ROOT/usr/share/backgrounds/meta-wallpaper.png"
  if [ -f "$WALL" ]; then
    if [ -f "$ROOT/usr/share/backgrounds/greybird.svg" ]; then
      rm -f "$ROOT/usr/share/backgrounds/greybird.svg"
      changed "removed /usr/share/backgrounds/greybird.svg"
    fi
    if [ -d "$ROOT/usr/share/backgrounds/xfce" ]; then
      rm -rf "$ROOT/usr/share/backgrounds/xfce"
      changed "removed /usr/share/backgrounds/xfce/"
    fi
    # Repoint every backdrop, including monitor names this boot does not
    # have — one of them once painted Ubuntu's wallpaper instead of Meta's.
    DESKTOP_XML="$ROOT/home/meta/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-desktop.xml"
    if [ -f "$DESKTOP_XML" ]; then
      if grep -q 'last-image.*value="/usr/share/backgrounds/\(greybird\|xfce\)' "$DESKTOP_XML" 2>/dev/null; then
        sed 's|\(last-image" type="string" value="\)[^"]*"|\1/usr/share/backgrounds/meta-wallpaper.png"|g' \
          "$DESKTOP_XML" > "$DESKTOP_XML.metaos-new" \
          && cat "$DESKTOP_XML.metaos-new" > "$DESKTOP_XML"
        rm -f "$DESKTOP_XML.metaos-new"
        changed "repointed backdrops to meta-wallpaper.png"
      else
        echo "  unchanged backdrops (already Meta's)"
      fi
    else
      echo "  no xfce4-desktop.xml yet (user not seeded) — nothing to repoint"
    fi
  elif [ -e "$ROOT/usr/share/backgrounds/greybird.svg" ] || [ -d "$ROOT/usr/share/backgrounds/xfce" ]; then
    echo "debrand: $WALL missing, refusing to remove wallpapers" >&2
    rm -f "$TMP"
    exit 1
  fi

  # Anything a person can open that still says Xubuntu/Ubuntu in a menu or
  # a window title. Scoped to the directories the desktop reads, never
  # packages. "Ubuntu" matches "Xubuntu" too (substring). Only files that
  # still match are touched, so a second run changes nothing.
  for d in usr/share/desktop-directories usr/share/applications; do
    [ -d "$ROOT/$d" ] || continue
    # "buntu" matches Ubuntu and Xubuntu (the latter has no "Ubuntu"
    # substring); only files that still match are touched, so reruns
    # change nothing.
    for f in $(grep -rl "buntu" "$ROOT/$d" 2>/dev/null); do
      sed 's/Xubuntu/Meta OS/g; s/Ubuntu/Meta OS/g' "$f" > "$f.metaos-new" \
        && cat "$f.metaos-new" > "$f"
      rm -f "$f.metaos-new"
      changed "rewrote names in /$d/$(basename "$f")"
    done
  done

  rm -f "$TMP"
  echo "debrand: done, $CHANGED change(s). Verify with --check; apt stays on noble in sources.list.d on purpose."
}

# JSON string escaping for short controlled values.
jesc() { printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'; }

FAIL=0
say() { # say <path> <pass:ok|no> <expected> <actual> <detail>
  if [ "$2" = ok ]; then
    [ "$MODE" = json ] \
      && printf '{"path":"%s","expected":"%s","actual":"%s","pass":true}\n' \
           "$(jesc "$1")" "$(jesc "$3")" "$(jesc "$4")" \
      || echo "PASS $1"
  else
    FAIL=1
    [ "$MODE" = json ] \
      && printf '{"path":"%s","expected":"%s","actual":"%s","pass":false}\n' \
           "$(jesc "$1")" "$(jesc "$3")" "$(jesc "$4")" \
      || echo "FAIL $1 -- $5"
  fi
}

do_check() {
  for f in "$ROOT/etc/os-release" "$ROOT/usr/lib/os-release"; do
    rel=${f#"$ROOT"}
    [ -f "$f" ] || { say "$rel" no "regular file" "missing" "missing"; continue; }
    pretty=$(grep "^PRETTY_NAME=" "$f" 2>/dev/null | head -1)
    idv=$(grep "^ID=" "$f" 2>/dev/null | head -1)
    like=$(grep "^ID_LIKE=" "$f" 2>/dev/null | head -1)
    [ "$pretty" = "PRETTY_NAME=\"$PRETTY\"" ] \
      && say "$rel pretty" ok "PRETTY_NAME=\"$PRETTY\"" "$pretty" "" \
      || say "$rel pretty" no "PRETTY_NAME=\"$PRETTY\"" "${pretty:-missing}" "PRETTY_NAME is not \"$PRETTY\""
    [ "$idv" = "ID=metaos" ] \
      && say "$rel id" ok "ID=metaos" "$idv" "" \
      || say "$rel id" no "ID=metaos" "${idv:-missing}" "ID is not metaos"
    [ "$like" = "ID_LIKE=debian" ] \
      && say "$rel id_like" ok "ID_LIKE=debian" "$like" "" \
      || say "$rel id_like" no "ID_LIKE=debian" "${like:-missing}" "ID_LIKE is not debian"
    if grep -qi "ubuntu" "$f" 2>/dev/null; then
      say "$rel no-ubuntu" no "no ubuntu string" "$(grep -oi "ubuntu" "$f" | head -1)" "file still mentions ubuntu"
    else
      say "$rel no-ubuntu" ok "no ubuntu string" "clean" ""
    fi
  done
  if [ -f "$ROOT/etc/lsb-release" ]; then
    grep -qx "DISTRIB_ID=MetaOS" "$ROOT/etc/lsb-release" 2>/dev/null \
      && say "lsb-release id" ok "DISTRIB_ID=MetaOS" "DISTRIB_ID=MetaOS" "" \
      || say "lsb-release id" no "DISTRIB_ID=MetaOS" "$(grep "^DISTRIB_ID=" "$ROOT/etc/lsb-release" 2>/dev/null | head -1)" "DISTRIB_ID is not MetaOS"
    grep -qx "DISTRIB_CODENAME=$CODENAME" "$ROOT/etc/lsb-release" 2>/dev/null \
      && say "lsb-release codename" ok "DISTRIB_CODENAME=$CODENAME" "DISTRIB_CODENAME=$CODENAME" "" \
      || say "lsb-release codename" no "DISTRIB_CODENAME=$CODENAME" "$(grep "^DISTRIB_CODENAME=" "$ROOT/etc/lsb-release" 2>/dev/null | head -1)" "DISTRIB_CODENAME is not $CODENAME"
  else
    say "lsb-release" no "regular file" "missing" "missing"
  fi
  if [ -f "$ROOT/etc/issue" ]; then
    head -1 "$ROOT/etc/issue" | grep -q "Meta OS 1.0 (Ribbon)" \
      && say "issue title" ok "Meta OS 1.0 (Ribbon)" "$(head -1 "$ROOT/etc/issue")" "" \
      || say "issue title" no "Meta OS 1.0 (Ribbon)" "$(head -1 "$ROOT/etc/issue")" "first line is not the Meta OS title"
    grep -q '\\l' "$ROOT/etc/issue" \
      && say "issue escape" ok "\\l escape" "present" "" \
      || say "issue escape" no "\\l escape" "absent" "no \\l escape (tty would print a literal backslash)"
  else
    say "issue" no "regular file" "missing" "missing"
  fi
  if [ -f "$ROOT/etc/issue.net" ]; then
    grep -q "Meta OS 1.0 (Ribbon)" "$ROOT/etc/issue.net" \
      && say "issue.net title" ok "Meta OS 1.0 (Ribbon)" "present" "" \
      || say "issue.net title" no "Meta OS 1.0 (Ribbon)" "$(head -1 "$ROOT/etc/issue.net")" "no Meta OS title"
    grep -qi "ubuntu" "$ROOT/etc/issue.net" \
      && say "issue.net no-ubuntu" no "no ubuntu string" "present" "file still mentions ubuntu" \
      || say "issue.net no-ubuntu" ok "no ubuntu string" "clean" ""
  else
    say "issue.net" no "regular file" "missing" "missing"
  fi
  if [ -f "$ROOT/etc/hostname" ]; then
    grep -qx "metaos" "$ROOT/etc/hostname" 2>/dev/null \
      && say "hostname" ok "metaos" "metaos" "" \
      || say "hostname" no "metaos" "$(cat "$ROOT/etc/hostname" 2>/dev/null)" "hostname is not metaos"
  else
    say "hostname" no "regular file" "missing" "missing"
  fi
  if grep -q '^127\.0\.1\.1[[:space:]]*metaos' "$ROOT/etc/hosts" 2>/dev/null; then
    say "hosts 127.0.1.1" ok "127.0.1.1 metaos" "127.0.1.1 metaos" ""
  else
    say "hosts 127.0.1.1" no "127.0.1.1 metaos" "$(grep "^127.0.1.1" "$ROOT/etc/hosts" 2>/dev/null | head -1)" "127.0.1.1 does not point at metaos"
  fi
  for s in 10-help-text 50-motd-news; do
    if [ -x "$ROOT/etc/update-motd.d/$s" ]; then
      say "motd $s disabled" no "not executable" "executable" "still executable"
    else
      say "motd $s disabled" ok "not executable" "disabled" ""
    fi
  done
  if [ -x "$ROOT/etc/update-motd.d/90-updates-available" ]; then
    say "motd updates-notice kept" ok "executable" "executable" ""
  else
    say "motd updates-notice kept" no "executable" "missing-or-disabled" "security-update notice must stay: real information, not branding"
  fi
  n=$(find "$ROOT/usr/share/plymouth/themes" -maxdepth 1 -name 'ubuntu*' 2>/dev/null | wc -l | tr -d ' ')
  [ "$n" = 0 ] \
    && say "plymouth ubuntu themes removed" ok "0 ubuntu* dirs" "0" "" \
    || say "plymouth ubuntu themes removed" no "0 ubuntu* dirs" "$n left" "$n ubuntu* theme dir(s) left"
  grep -q '^Theme=metaos' "$ROOT/etc/plymouth/plymouthd.conf" 2>/dev/null \
    && say "plymouth theme metaos" ok "Theme=metaos" "Theme=metaos" "" \
    || say "plymouth theme metaos" no "Theme=metaos" "$(grep "^Theme=" "$ROOT/etc/plymouth/plymouthd.conf" 2>/dev/null | head -1)" "plymouthd.conf does not say Theme=metaos"
  found=""
  [ -f "$ROOT/usr/share/backgrounds/greybird.svg" ] && found="$found greybird.svg"
  # shellcheck disable=SC2046
  for f in $(find "$ROOT/usr/share/backgrounds/xfce" -mindepth 1 2>/dev/null); do
    found="$found (xfce/$(basename "$f"))"
  done
  [ -z "$found" ] \
    && say "stock wallpapers removed" ok "absent" "absent" "" \
    || say "stock wallpapers removed" no "absent" "present:$found" "still present:$found"
  DESKTOP_XML="$ROOT/home/meta/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-desktop.xml"
  if [ -f "$DESKTOP_XML" ]; then
    bad=$(grep -c 'last-image.*value="/usr/share/backgrounds/\(greybird\|xfce\)' "$DESKTOP_XML" 2>/dev/null || true)
    [ "${bad:-0}" = 0 ] \
      && say "backdrops are Meta" ok "all last-image Meta" "all Meta" "" \
      || say "backdrops are Meta" no "all last-image Meta" "$bad stock" "$bad last-image entr(ies) point at a stock wallpaper"
  else
    [ "$MODE" = json ] \
      && printf '{"path":"backdrops are Meta","expected":"all last-image Meta","actual":"SKIP (no xfce4-desktop.xml yet)","pass":true}\n' \
      || echo "SKIP backdrops are Meta -- no xfce4-desktop.xml yet (user not seeded)"
  fi
  [ -f "$ROOT/usr/share/backgrounds/meta-wallpaper.png" ] \
    && say "meta wallpaper present" ok "present" "present" "" \
    || say "meta wallpaper present" no "present" "missing" "meta-wallpaper.png missing"
  dirty=""
  for d in usr/share/desktop-directories usr/share/applications; do
    [ -d "$ROOT/$d" ] || continue
    for f in $(grep -rl "buntu" "$ROOT/$d" 2>/dev/null); do
      dirty="$dirty ${f#"$ROOT"}"
    done
  done
  [ -z "$dirty" ] \
    && say "desktop names clean" ok "no buntu string" "clean" "" \
    || say "desktop names clean" no "no buntu string" "dirty:$dirty" "still names Ubuntu/Xubuntu:$dirty"
  if [ "$MODE" = json ]; then
    [ "$FAIL" = 0 ]
  else
    echo "debrand --check: $([ "$FAIL" = 0 ] && echo PASS || echo FAIL)"
    [ "$FAIL" = 0 ]
  fi
}

case "$MODE" in
  apply) do_apply ;;
  check|json) do_check ;;
esac

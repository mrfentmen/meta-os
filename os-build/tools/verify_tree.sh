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

# Absent-lane rows always read "absent (owner: lane N)" — a missing lane is
# never a pass. Owner labels follow the debrand work split (lane 2: strings
# and allowlist; lane 3: desktop entries; lane 1: theme/profile assets);
# Buffy corrects them if the split differs.
OS1_CHECK="os-build/identity/check_strings.sh"
OS1_ALLOWLIST="os-build/identity/ALLOWLIST.tsv"
LANE3_ENTRIES="agent-layer/desktop-entries/check_entries.sh"
LANE1_PROFILE="os-build/iso/payload-theme/terminal/check_profile.sh"
LANE1_TOKENS="os-build/iso/payload-theme/tokens/test_tokens.sh"

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

# run_checker <row> <owner> <path> [args...] — absent-tolerant external
# checker. Missing file => "absent (owner: lane N)", never a pass. Args
# default to --check; checkers without that flag (check_strings, test_tokens)
# pass their own (possibly empty) invocation.
run_checker() {
  _row="$1"; _owner="$2"; _path="$3"; shift 3
  if [ ! -f "$ROOT/$_path" ]; then
    row "$_row" "absent (owner: $_owner)" "$_path not present yet"
    return 0
  fi
  if [ ! -x "$ROOT/$_path" ]; then
    row "$_row" "FAIL" "$_path present but not executable"
    return 0
  fi
  if [ $# = 0 ]; then set -- --check; fi
  if [ "$1" = "__none__" ]; then shift; fi
  if _out=$("sh" "$ROOT/$_path" "$@" 2>&1); then
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
  row "allowlist" "absent (owner: lane 2)" "$OS1_ALLOWLIST not present yet"
fi

# --- lane checkers, by path: string sweep, entries, profile, tokens.
# check_strings takes no --check flag (it rejects unknown flags), so it is
# invoked bare; same for test_tokens, which runs on invocation.
run_checker "debrand-strings" "lane 2" "$OS1_CHECK" "__none__"
run_checker "desktop-entries-check" "lane 3" "$LANE3_ENTRIES"
run_checker "profile-check" "lane 1" "$LANE1_PROFILE"
run_checker "tokens-check" "lane 1" "$LANE1_TOKENS" "__none__"

# --- row: no-stock-art (OS-DEBRAND-4, inline). FAIL if stock Ubuntu art or
# live pointers to it exist: greybird-wall* / warty* files, emerald /
# ubuntu-logo / ubuntu-text plymouth theme dirs, symlinks targeting
# ubuntu-text, `update-alternatives --set/--install ... ubuntu-text` in
# shell code, or desktop-base wallpaper *values* in xml/conf. Prose mentions
# (docs, plan, comments) do not trigger: this row matches artifacts and
# live config values only. Named allowlist rows (path match) excuse a hit.
_art_bad=""
_art_files=$(find "$ROOT" -path "$ROOT/.git" -prune -o \( -name 'greybird-wall*' -o -name 'warty*' \) -print 2>/dev/null | grep -v "^$ROOT/os-build/logs/" || true)
_art_dirs=$(find "$ROOT" -path "$ROOT/.git" -prune -o -type d \( -name 'emerald' -o -name 'ubuntu-logo' -o -name 'ubuntu-text' \) -print 2>/dev/null | grep -v "^$ROOT/os-build/logs/" || true)
for _a in $_art_files $_art_dirs; do
  _art_bad="$_art_bad ${_a#"$ROOT"/}:stock-artifact"
done
# (No case-in-$(): macOS bash 3.2 rejects `;;` there. Temp file under /tmp,
# never under the repo tree.)
_art_tmp=$(mktemp "${TMPDIR:-/tmp}/verify-art-XXXXXX")
find "$ROOT" -path "$ROOT/.git" -prune -o -type l -print 2>/dev/null > "$_art_tmp"
_art_links=""
while read -r _l; do
  _t=$(readlink "$_l" 2>/dev/null || true)
  case "$_t" in
    *ubuntu-text*) _art_links="$_art_links $_l" ;;
  esac
done < "$_art_tmp"
rm -f "$_art_tmp"
for _a in $_art_links; do
  _art_bad="$_art_bad ${_a#"$ROOT"/}:alternative-target"
done
# (Self-exclusion: this script's own -e pattern text necessarily contains the
# match, so verify_tree.sh itself is excluded from this one scan.)
_art_conf=$(grep -rn --include='*.sh' -e 'update-alternatives.*ubuntu-text' -e 'ubuntu-text.*update-alternatives' "$ROOT" 2>/dev/null | grep -v "/.git/" | grep -v "os-build/logs/" | grep -v "/plan/" | grep -v "os-build/tools/verify_tree.sh" | cut -d: -f1,2 || true)
for _a in $_art_conf; do
  _art_bad="$_art_bad ${_a}:live-alternative"
done
_art_val=$(grep -rn --include='*.xml' --include='*.conf' -e 'value="[^"]*desktop-base' -e 'background=.*desktop-base' -e 'last-image.*desktop-base' "$ROOT" 2>/dev/null | grep -v "/.git/" | grep -v "os-build/logs/" | grep -v "/plan/" | cut -d: -f1,2 || true)
for _a in $_art_val; do
  _art_bad="$_art_bad ${_a}:desktop-base-value"
done
if [ -n "$_art_bad" ] && [ -f "$ROOT/$OS1_ALLOWLIST" ]; then
  _kept=""
  for _h in $_art_bad; do
    _p=${_h%%:*}
    _excused=0
    while IFS="$(printf '\t')" read -r _ap _apat _av _awhy; do
      case "$_ap" in ""|\#*) continue ;; esac
      if [ "$_p" = "$_ap" ]; then _excused=1; break; fi
    done < "$ROOT/$OS1_ALLOWLIST"
    [ "$_excused" = "0" ] && _kept="$_kept $_h"
  done
  _art_bad=$(printf '%s' "$_kept" | tr ' ' '\n' | grep . | tr '\n' ' ' || true)
fi
if [ -z "$_art_bad" ]; then
  row "no-stock-art" "PASS" "no greybird/warty files, no emerald/ubuntu-logo/ubuntu-text theme dirs, no ubuntu-text alternatives or desktop-base values"
else
  _n=$(printf '%s' "$_art_bad" | wc -w | tr -d ' ')
  row "no-stock-art" "FAIL" "$_n stock-art hits: $(printf '%s' "$_art_bad" | cut -c1-140)"
fi

# --- row: wallpaper-reachability (OS-DEBRAND-4, inline). Every backdrop path
# named in the shipped xfce4-desktop.xml files and greeter confs must resolve
# to a file in this repo (via the image-path map below) or an allowlist row;
# every wallpaper source file must be Meta-named (meta-*, greeter-*) or
# allowlisted as a carrier. Image path /usr/share/X maps to repo file Y:
#   /usr/share/metaos/theme/*.png      -> iso/theme/wallpaper/<same>
#   /usr/share/backgrounds/meta-*.png  -> os-build/iso/payload-theme/wallpapers/<same>
_wall_bad=""
for _x in $(find "$ROOT" -name 'xfce4-desktop.xml' -not -path "$ROOT/.git/*" 2>/dev/null | grep -v "os-build/logs/"); do
  for _v in $(grep -o 'value="/usr/share/[^"]*"' "$_x" 2>/dev/null | sed 's/value="//;s/"$//' | sort -u); do
    case "$_v" in
      /usr/share/metaos/theme/*)
        _rel="iso/theme/wallpaper/$(basename "$_v")"
        [ -f "$ROOT/$_rel" ] || _wall_bad="$_wall_bad ${_x#"$ROOT"/}:unreachable-$_v" ;;
      /usr/share/backgrounds/*)
        _rel="os-build/iso/payload-theme/wallpapers/$(basename "$_v")"
        [ -f "$ROOT/$_rel" ] || _wall_bad="$_wall_bad ${_x#"$ROOT"/}:unreachable-$_v" ;;
      *) _wall_bad="$_wall_bad ${_x#"$ROOT"/}:unknown-prefix-$_v" ;;
    esac
  done
done
for _g in $(find "$ROOT" -name 'lightdm-gtk-greeter.conf' -not -path "$ROOT/.git/*" 2>/dev/null | grep -v "os-build/logs/"); do
  _b=$(sed -n 's/^background=//p' "$_g" 2>/dev/null | head -1)
  case "$_b" in
    ""|\#*) ;;
    /usr/share/metaos/theme/*)
      _rel="iso/theme/wallpaper/$(basename "$_b")"
      [ -f "$ROOT/$_rel" ] || _wall_bad="$_wall_bad ${_g#"$ROOT"/}:unreachable-$_b" ;;
    /usr/share/backgrounds/*)
      _rel="os-build/iso/payload-theme/wallpapers/$(basename "$_b")"
      [ -f "$ROOT/$_rel" ] || _wall_bad="$_wall_bad ${_g#"$ROOT"/}:unreachable-$_b" ;;
    *) _wall_bad="$_wall_bad ${_g#"$ROOT"/}:unknown-prefix-$_b" ;;
  esac
done
for _w in $(find "$ROOT/iso/theme/wallpaper" "$ROOT/os-build/iso/payload-theme/wallpapers" -type f \( -name '*.png' -o -name '*.jpg' -o -name '*.svg' \) 2>/dev/null); do
  _bn=$(basename "$_w")
  case "$_bn" in
    meta-*|greeter-*|loop-*) ;;
    *) _wall_bad="$_wall_bad ${_w#"$ROOT"/}:non-meta-wallpaper" ;;
  esac
done
if [ -n "$_wall_bad" ] && [ -f "$ROOT/$OS1_ALLOWLIST" ]; then
  _kept=""
  for _h in $_wall_bad; do
    _p=${_h%%:*}
    _excused=0
    while IFS="$(printf '\t')" read -r _ap _apat _av _awhy; do
      case "$_ap" in ""|\#*) continue ;; esac
      if [ "$_p" = "$_ap" ]; then _excused=1; break; fi
    done < "$ROOT/$OS1_ALLOWLIST"
    [ "$_excused" = "0" ] && _kept="$_kept $_h"
  done
  _wall_bad=$(printf '%s' "$_kept" | tr ' ' '\n' | grep . | tr '\n' ' ' || true)
fi
if [ -z "$_wall_bad" ]; then
  row "wallpaper-reachability" "PASS" "all named backdrops resolve to repo art; all wallpaper files Meta-named"
else
  _n=$(printf '%s' "$_wall_bad" | wc -w | tr -d ' ')
  row "wallpaper-reachability" "FAIL" "$_n reachability hits: $(printf '%s' "$_wall_bad" | cut -c1-140)"
fi

# --- row: brand-identity (OS-DEBRAND-4, inline). Line-anchored machine
# contexts only — prose about the leaks (matrix, inventory, READMEs) does not
# match: ^ID_LIKE=ubuntu (compat must be debian), ^ID=ubuntu, ^NAME=Ubuntu,
# ^PRETTY_NAME="Ubuntu, ^DISTRIB_ID=Ubuntu, ^UBUNTU_CODENAME,
# ^Comment=<anything>Xubuntu (user-visible desktop string). Whole-word
# prose terms are check_strings' job (debrand-strings row). Each hit prints
# file:line plus its reason.
_brand_hits=""
_brand_scan=$(grep -rn --include='*.sh' --include='*.desktop' --include='*.conf' --include='*.xml' --include='*.py' --include='*os-release*' --include='*.list' -e '^ID_LIKE=ubuntu' -e '^ID=ubuntu' -e '^NAME=Ubuntu' -e '^PRETTY_NAME="Ubuntu' -e '^DISTRIB_ID=Ubuntu' -e '^UBUNTU_CODENAME' -e '^Comment=.*Xubuntu' "$ROOT" 2>/dev/null | grep -v "/.git/" | grep -v "os-build/logs/" | grep -v "/plan/" || true)
for _h in $(printf '%s' "$_brand_scan" | cut -d: -f1,2 | sort -u); do
  _line=$(printf '%s' "$_brand_scan" | grep "^$_h:" | head -1 | cut -d: -f3-)
  case "$_line" in
    ID_LIKE=ubuntu*) _why="compat must be ID_LIKE=debian" ;;
    UBUNTU_CODENAME*) _why="stock codename field ships Ubuntu identity" ;;
    Comment=*Xubuntu*) _why="user-visible desktop string names Xubuntu" ;;
    *) _why="product identity names Ubuntu" ;;
  esac
  _brand_hits="${_brand_hits}${_h#"$ROOT"/}[$_why]$NL"
done
if [ -n "$_brand_hits" ] && [ -f "$ROOT/$OS1_ALLOWLIST" ]; then
  _kept=""
  while IFS= read -r _h; do
    [ -n "$_h" ] || continue
    _p=${_h%%\[*}
    _excused=0
    while IFS="$(printf '\t')" read -r _ap _apat _av _awhy; do
      case "$_ap" in ""|\#*) continue ;; esac
      if [ "$_p" = "$_ap" ]; then _excused=1; break; fi
    done < "$ROOT/$OS1_ALLOWLIST"
    [ "$_excused" = "0" ] && _kept="${_kept}${_h}$NL"
  done <<EOF_HITS
$_brand_hits
EOF_HITS
  _brand_hits="$_kept"
fi
if [ -z "$_brand_hits" ]; then
  row "brand-identity" "PASS" "no ubuntu product-identity fields in machine contexts"
else
  _n=$(printf '%s' "$_brand_hits" | grep -c '\[' || true)
  row "brand-identity" "FAIL" "$_n identity hits: $(printf '%s' "$_brand_hits" | tr '\n' ';' | cut -c1-200)"
fi

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
    # An absolute Icon= names the INSTALLED path (/usr/share/icons/...), so it
    # cannot resolve against the repo root. The payload ships the same PNG by
    # basename under payload-theme/icons/metaos/, which apply.sh installs into
    # metaos/128x128/apps/ at image time — resolve there too, and keep failing
    # an icon that exists in neither place.
    /*) [ -e "$ROOT$_icon" ] || [ -e "$ROOT/os-build/iso/payload-theme/icons/metaos/$(basename "$_icon")" ] || _bad="$_bad $(basename "$_f"):icon-missing" ;;
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
# A file only counts when the word sits in a VALUE a reader can meet on the
# machine. A comment explaining what was removed ("the greeter fell back to the
# Ubuntu warty background") or a checker's own regex (grep -qi ubuntu) is
# commentary, not branding — counting those made twelve honest files read as
# leaks while the real sweep (check_strings, row 2) passed on the same tree.
# Markdown and the checker scripts are therefore skipped, and inside every other
# file comment lines are skipped, including <!-- ... --> blocks.
_comment_filter='
  /<!--/ { inxml = 1 }
  inxml { if (/-->/) inxml = 0; next }
  /^[ \t]*(#|;|\/\/|\*)/ { next }
  tolower($0) ~ /ubuntu/ { found = 1 }
  END { exit(found ? 0 : 1) }
'
_hits=""
if [ -n "$_scope" ]; then
  # shellcheck disable=SC2086
  for _f in $(grep -rIl -i "ubuntu" $_scope 2>/dev/null | grep -v "/\.git/" || true); do
    case "$_f" in *.md|*.sh|*.mjs|*.js|*.py) continue ;; esac
    case "$(basename "$_f")" in ALLOWLIST.tsv|meta.tokens.json) continue ;; esac
    if awk "$_comment_filter" "$_f"; then _hits="$_hits $_f"; fi
  done
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
  row "no-ubuntu" "PASS" "no case-insensitive ubuntu in shipped values (comments and checkers excluded)"
else
  # grep -c, not wc -l: a single hit has no trailing newline and wc counted 0.
  _n=$(printf '%s\n' "$_hits" | grep -c . | tr -d ' ')
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

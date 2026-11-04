#!/bin/sh
# check-dock-tiles.sh — lane R2-T2 acceptance for the MetaOS dock tiles.
#
# What it proves, per tile, without a display or a booted guest:
#   1. tile set: exactly the 12 expected meta-dock-*.desktop files exist
#      (board removed: its :18900/board.html target 404s; nuntius added).
#   2. Exec/TryExec/Icon reference absolute paths that exist in STAGE.
#      STAGE is a fake guest root built from the tree:
#        STAGE/usr/share/applications/meta-dock-*.desktop (copies)
#        STAGE/usr/share/icons/metaos/128x128/apps/*.png (real PNGs)
#        STAGE/usr/local/bin/meta-app|meta-agents|meta-notes (real scripts)
#        STAGE/usr/share/metaos/apps/*.py (real scripts)
#      Base-image binaries (/usr/bin/mate-calc|mousepad|thunar) are not in
#      the tree; they resolve via the tree's own package manifests
#      (os-build/metaos1-base/packages.txt, iso/base/metaos.packages,
#      os-build/face/APP_MATRIX.md guest-verified mate-calc 1.26.0).
#   3. every tile has Name + Comment, StartupWMClass, TryExec, and a
#      NewWindow desktop action whose Exec matches the main Exec.
#   4. every http(s) URL in Exec points at a page that exists in the tree
#      (:18900 -> os-build/face/, :18934 -> repo root, :18935/ -> board/).
#   5. StartupWMClass matches what the shell will set: the shell sources
#      (face/native/meta-*.py, apps/metaos-*.py) must contain no
#      set_prgname/set_wmclass call, so GDK derives WM_CLASS from the
#      installed basename; meta-app tiles carry --app-id, which the shell
#      takes verbatim (explicit wins in slug_app_id), verified by importing
#      the real slug_app_id from the tree (it imports with no gi/GTK).
#   6. GROUPING AUDIT: plank groups by WM_CLASS, so the 7 meta-app tiles
#      share one group key today. This section FAILS until the owning lane
#      gives meta-app per-app classes (see CROSS-LANE-1 in the lane report).
#      Everything above must PASS; this section documents the known
#      upstream collision instead of hiding it.
#
# Usage: check-dock-tiles.sh [APPS_DIR] [STAGE] [TREE_ROOT]
#   APPS_DIR   dir with the .desktop files (default: this script's dir)
#   STAGE      fake guest root (default: /)
#   TREE_ROOT  repo checkout root (default: auto-detected via git)
# Prints one PASS/FAIL line per check, exits 1 on any miss.
set -eu
HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
APPS="${1:-$HERE}"
STAGE="${2:-/}"
if [ "${3:-}" != "" ]; then TREE="$3"
elif TREE="$(git -C "$HERE" rev-parse --show-toplevel 2>/dev/null)"; then :
else TREE="$(CDPATH= cd -- "$HERE/../../../../.." && pwd)"; fi
DOCK="$APPS/dock"
fail=0; pass=0
ok() { echo "PASS $1"; pass=$((pass + 1)); }
no() { echo "FAIL $1: $2"; fail=$((fail + 1)); }

# ---------------------------------------------------------- 1. tile set
EXPECTED="meta-dock-agents meta-dock-calculator meta-dock-calendar
meta-dock-custos meta-dock-dashboard meta-dock-editor meta-dock-musica
meta-dock-notes meta-dock-nuntius meta-dock-officina meta-dock-science
meta-dock-trash"
n=0; missing=""
for t in $EXPECTED; do
  n=$((n + 1))
  [ -f "$DOCK/$t.desktop" ] || missing="$missing $t"
done
have=$(ls "$DOCK"/meta-dock-*.desktop 2>/dev/null | wc -l | tr -d ' ')
if [ -z "$missing" ] && [ "$have" -eq "$n" ]; then
  ok "tileset: $have/12 expected tiles present, none extra"
else
  no "tileset" "missing:$missing have=$have want=$n"
fi
[ -e "$DOCK/meta-dock-board.desktop" ] \
  && no "tileset" "meta-dock-board.desktop still present (target :18900/board.html 404s)" \
  || ok "tileset: dead board tile absent"

# ------------------------------------------------- 2/3. per-tile fields
# base-image binaries: provided by the Xubuntu base / verified manifests.
manifest_hit() { # manifest_hit <abs-path>
  case "$1" in
    /usr/bin/mate-calc) grep -q "mate-calc 1.26.0" "$TREE/os-build/face/APP_MATRIX.md" 2>/dev/null ;;
    /usr/bin/mousepad) grep -qx "mousepad" "$TREE/os-build/metaos1-base/packages.txt" 2>/dev/null ;;
    /usr/bin/thunar) grep -q "base:.*thunar" "$TREE/iso/base/metaos.packages" 2>/dev/null ;;
    *) return 1 ;;
  esac
}
resolve() { # resolve <abs-path> <tile>
  p="$1"; t="$2"
  [ -f "$STAGE$p" ] && return 0
  manifest_hit "$p" && return 0
  return 1
}
for t in $EXPECTED; do
  f="$DOCK/$t.desktop"
  [ -f "$f" ] || continue
  name=$(sed -n 's/^Name=//p' "$f" | head -1)
  comment=$(sed -n 's/^Comment=//p' "$f" | head -1)
  exec=$(sed -n 's/^Exec=//p' "$f" | head -1)
  tryexec=$(sed -n 's/^TryExec=//p' "$f" | head -1)
  icon=$(sed -n 's/^Icon=//p' "$f" | head -1)
  swmc=$(sed -n 's/^StartupWMClass=//p' "$f" | head -1)
  [ -n "$name" ] && [ -n "$comment" ] \
    && ok "$t: Name+Comment present" \
    || no "$t" "Name=[$name] Comment=[$comment]"
  bin=$(printf '%s' "$exec" | awk '{print $1}')
  case "$bin" in /*) : ;; *) no "$t" "Exec not absolute: $exec"; continue ;; esac
  if resolve "$bin" "$t"; then ok "$t: Exec bin resolves ($bin)"; else no "$t" "Exec bin missing in stage+manifests: $bin"; fi
  if [ -n "$tryexec" ]; then
    case "$tryexec" in /*) : ;; *) no "$t" "TryExec not absolute: $tryexec" ;; esac
    if resolve "$tryexec" "$t"; then ok "$t: TryExec resolves"; else no "$t" "TryExec missing: $tryexec"; fi
  else
    no "$t" "TryExec absent"
  fi
  case "$icon" in /*) : ;; *) no "$t" "Icon not absolute: $icon"; continue ;; esac
  if [ -f "$STAGE$icon" ]; then
    src="$TREE/os-build/iso/payload-theme/icons/metaos/$(basename "$icon")"
    if [ -f "$src" ]; then ok "$t: Icon resolves to committed PNG ($(basename "$icon"))"
    else no "$t" "Icon $icon staged but not committed in tree icons/metaos/"
    fi
  else
    # welcome/controls icons land the same way; missing art is NEVER
    # invented here — log the exact missing path for whoever draws icons.
    no "$t" "icon PNG absent: $icon missing (fallback: initial '$(printf '%s' "$name" | cut -c1)' on standard plate per icons/generate-icons.py geometry)"
  fi
  [ -n "$swmc" ] && ok "$t: StartupWMClass=$swmc" || no "$t" "StartupWMClass absent"
  # NewWindow action must repeat the main Exec (plank-native Close/Pin need
  # no entries; see lane report tasks 50-54).
  grep -q '^\[Desktop Action NewWindow\]' "$f" \
    && ok "$t: NewWindow action declared" \
    || no "$t" "Desktop Action NewWindow missing"
  aexec=$(awk '/^\[Desktop Action NewWindow\]/{f=1;next} /^\[/{f=0} f&&/^Exec=/{sub(/^Exec=/,"");print;exit}' "$f")
  [ "$aexec" = "$exec" ] \
    && ok "$t: action Exec matches" \
    || no "$t" "action Exec=[$aexec] != Exec=[$exec]"
done

# ------------------------------------------------- 4. URLs exist in tree
for t in $EXPECTED; do
  f="$DOCK/$t.desktop"; [ -f "$f" ] || continue
  for u in $(grep -o 'http://127\.0\.0\.1:[0-9]*/[^ ]*' "$f" | sort -u); do
    case "$u" in
      http://127.0.0.1:18900/*)
        p=${u#http://127.0.0.1:18900/}
        [ -f "$TREE/os-build/face/$p" ] \
          && ok "$t: :18900/$p ships in os-build/face/" \
          || no "$t" ":18900/$p NOT in tree (dead tile target)" ;;
      http://127.0.0.1:18934/*)
        p=${u#http://127.0.0.1:18934/}
        [ -f "$TREE/$p" ] \
          && ok "$t: :18934/$p ships in tree" \
          || no "$t" ":18934/$p NOT in tree (dead tile target)" ;;
      http://127.0.0.1:18935/)
        [ -f "$TREE/board/board.mjs" ] && [ -f "$TREE/board/board.html" ] \
          && grep -q 'url.pathname === "/"' "$TREE/board/board.mjs" \
          && ok "$t: :18935/ serves board/board.html viewer" \
          || no "$t" ":18935/ viewer missing (board/board.mjs+board.html)" ;;
      *) no "$t" "unclassified URL: $u" ;;
    esac
  done
done

# --------------------------------- 5. StartupWMClass == shell derivation
SHELL_FILES="$TREE/os-build/face/native/meta-app.py
$TREE/os-build/face/native/meta-agents.py
$TREE/os-build/face/native/meta-notes.py
$TREE/os-build/iso/payload-theme/apps/metaos-controls.py
$TREE/os-build/iso/payload-theme/apps/metaos-welcome.py"
if grep -rn "set_prgname\|set_wmclass\|set_wm_class\|program_class\|set_application_name" \
    $SHELL_FILES 2>/dev/null | grep -q .; then
  no "wmclass" "shell sets an explicit class — StartupWMClass claims need re-audit"
  grep -rn "set_prgname\|set_wmclass\|set_wm_class\|program_class\|set_application_name" $SHELL_FILES
else
  ok "wmclass: no explicit class in any shell source (GDK derives prgname=installed basename)"
fi
# --app-id in tile == shell's app_id verbatim (explicit wins), and equals
# slug(--title) so a title-only session tile shares the lock.
if python3 - "$TREE" <<'PY' >/dev/null 2>&1
import importlib.util, sys
spec = importlib.util.spec_from_file_location(
    "meta_app", sys.argv[1] + "/os-build/face/native/meta-app.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
assert mod.slug_app_id("Science Lab") == "science-lab"
PY
then
  ok "appid: slug_app_id imports headless (no gi/GTK needed)"
else
  no "appid" "cannot import slug_app_id from tree meta-app.py"
fi
for t in $EXPECTED; do
  f="$DOCK/$t.desktop"; [ -f "$f" ] || continue
  exec=$(sed -n 's/^Exec=//p' "$f" | head -1)
  case "$exec" in
    *meta-app*)
      title=$(printf '%s' "$exec" | sed -n 's/.*--title \([^ ][^ ]*\( [^ -][^ ]*\)*\).*/\1/p' | sed 's/ --app-id.*//;s/ --url.*//')
      appid=$(printf '%s' "$exec" | sed -n 's/.*--app-id \([^ ]*\).*/\1/p')
      if [ -z "$appid" ]; then no "$t" "meta-app tile without --app-id"; continue; fi
      slug=$(python3 - "$TREE" "$title" <<'PY' 2>/dev/null
import importlib.util, sys
spec = importlib.util.spec_from_file_location(
    "meta_app", sys.argv[1] + "/os-build/face/native/meta-app.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
print(mod.slug_app_id(sys.argv[2]))
PY
)
      if [ "$appid" = "$slug" ]; then ok "$t: --app-id $appid == slug(--title $title)"
      else no "$t" "--app-id $appid != slug(--title $title)=$slug"; fi
      swmc=$(sed -n 's/^StartupWMClass=//p' "$f" | head -1)
      [ "$swmc" = "meta-app" ] \
        && ok "$t: StartupWMClass=meta-app matches installed basename /usr/local/bin/meta-app" \
        || no "$t" "StartupWMClass=$swmc, want meta-app" ;;
    /usr/local/bin/meta-agents|/usr/local/bin/meta-notes*)
      want=$(basename "$(printf '%s' "$exec" | awk '{print $1}')")
      swmc=$(sed -n 's/^StartupWMClass=//p' "$f" | head -1)
      [ "$swmc" = "$want" ] \
        && ok "$t: StartupWMClass=$swmc matches installed basename" \
        || no "$t" "StartupWMClass=$swmc, want $want" ;;
    *)
      want=$(basename "$(printf '%s' "$exec" | awk '{print $1}')")
      swmc=$(sed -n 's/^StartupWMClass=//p' "$f" | head -1)
      [ "$swmc" = "$want" ] \
        && ok "$t: StartupWMClass=$swmc matches base binary basename" \
        || no "$t" "StartupWMClass=$swmc, want $want" ;;
  esac
done
for d in metaos-controls metaos-welcome; do
  f="$APPS/$d.desktop"
  swmc=$(sed -n 's/^StartupWMClass=//p' "$f" | head -1)
  [ "$swmc" = "$d.py" ] \
    && ok "$d: StartupWMClass=$swmc matches exec basename" \
    || no "$d" "StartupWMClass=$swmc, want $d.py"
done

# --------------------------------- 6. grouping audit (known upstream)
echo "---- grouping audit (plank groups by WM_CLASS) ----"
for t in $EXPECTED; do
  f="$DOCK/$t.desktop"; [ -f "$f" ] || continue
  printf 'key=%-16s tile=%s\n' \
    "$(sed -n 's/^StartupWMClass=//p' "$f" | head -1)" "$t"
done | sort
nkeys=$(for t in $EXPECTED; do sed -n 's/^StartupWMClass=//p' "$DOCK/$t.desktop"; done | sort -u | wc -l | tr -d ' ')
nmeta=$(grep -l 'StartupWMClass=meta-app' "$DOCK"/meta-dock-*.desktop | wc -l | tr -d ' ')
if [ "$nmeta" -gt 1 ]; then
  no "grouping" "$nmeta tiles share WM_CLASS meta-app ($nkeys distinct keys for 12 tiles) — needs per-app classes in meta-app.py (CROSS-LANE-1)"
else
  ok "grouping: every tile has a distinct WM_CLASS key"
fi

echo "----"
echo "check-dock-tiles: $pass passed, $fail failed"
exit $([ "$fail" -eq 0 ] && echo 0 || echo 1)

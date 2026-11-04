#!/bin/sh
# meta-desktop.sh — install the native Meta desktop for one user.
#
# File-based on purpose: this runs at every login (from session.sh) and it also
# runs inside a chroot on the mounted disk with no X, no dbus and no daemon.
# Nothing here needs a running session, so the same code path is testable
# offline and the same code path is what ships.
#
# What it sets up:
#   panel   the Meta top bar (payload-theme/panel/xfce4-panel.xml)
#   wm      theme MetaOS + macOS button order (close/minimise on the left)
#   gtk     theme MetaOS
#   dock    plank: MetaOS theme, one .dockitem per installed app
#   entries one .desktop per app, owned by the user (no root at login)
#
# Every overwrite is backed up once as <file>.metaos-fix.bak.
#
# Usage: meta-desktop.sh [--home DIR] [--owner UID:GID]
#        HOME_DIR=... OWNER=... meta-desktop.sh
set -u

HOME_DIR="${HOME_DIR:-}"
OWNER="${OWNER:-}"
CHECK_ICONS="${CHECK_ICONS:-0}"
while [ $# -gt 0 ]; do
  case "$1" in
    --home)  HOME_DIR="$2"; shift 2 ;;
    --owner) OWNER="$2"; shift 2 ;;
    --check-icons) CHECK_ICONS=1; shift ;;
    -h|--help) echo "usage: meta-desktop.sh [--home DIR] [--owner UID:GID] [--check-icons]"; exit 0 ;;
    *) echo "meta-desktop: unknown flag $1" >&2; exit 2 ;;
  esac
done
[ -n "$HOME_DIR" ] || HOME_DIR="${HOME:-/home/ubuntu}"
[ -d "$HOME_DIR" ] || { echo "meta-desktop: no home at $HOME_DIR" >&2; exit 1; }

say() { echo "meta-desktop: $*"; }
backup() { [ -e "$1" ] && [ ! -e "$1.metaos-fix.bak" ] && cp -p "$1" "$1.metaos-fix.bak" 2>/dev/null; return 0; }

XF="$HOME_DIR/.config/xfce4/xfconf/xfce-perchannel-xml"
APPS="$HOME_DIR/.local/share/applications"
PLANK="$HOME_DIR/.config/plank/dock1"
mkdir -p "$XF" "$APPS" "$PLANK/launchers" 2>/dev/null || {
  echo "meta-desktop: cannot create $HOME_DIR/.config" >&2; exit 1; }

# ---------------------------------------------------------------- 1. panel
# The Meta top bar ships at /etc/xdg/... as the channel default, but the live
# user already has a Xubuntu panel file that wins over it. Copy the Meta one
# into the user config so the top bar is the one that draws.
PANEL_SRC=""
for cand in /etc/xdg/xfce4/xfconf/xfce-perchannel-xml/xfce4-panel.xml \
            /etc/skel/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-panel.xml \
            /opt/face/theme/panel/xfce4-panel.xml \
            /usr/share/metaos/theme/panel/xfce4-panel.xml; do
  if [ -r "$cand" ]; then PANEL_SRC="$cand"; break; fi
done
if [ -n "$PANEL_SRC" ]; then
  backup "$XF/xfce4-panel.xml"
  cp -f "$PANEL_SRC" "$XF/xfce4-panel.xml" && say "panel <- $PANEL_SRC"
else
  say "no Meta panel xml on this system — panel left alone"
fi

# ------------------------------------------- 1b. Ctrl+Alt+T opens the terminal
# Same reason as the dock tile above: the image's default shortcut is
# `exo-open --launch TerminalEmulator`, which starts xfce4-terminal's *server*.
# The first window then owns the colours for the whole login, so a session that
# touched a terminal before the user's terminalrc existed stayed white.
# `--disable-server` gives every window the user's own colours.
#
# Set ONE key, through xfconf, exactly like the Settings > Keyboard dialog does.
# Writing the whole channel file would have dropped every other shortcut with
# it; xfconf merges by property, so `commands/custom` overrides only the one
# default in `commands/default` and everything else is untouched. Needs a live
# X session (xfconf talks to xfconfd), so it is skipped when this runs offline.
if command -v xfconf-query >/dev/null 2>&1 && xfconf-query -c xfwm4 -l >/dev/null 2>&1; then
  xfconf-query -c xfce4-keyboard-shortcuts \
    -p '/commands/custom/<Primary><Alt>t' \
    -n -t string -s 'xfce4-terminal --disable-server' >>"$LOG" 2>&1 \
    && say "shortcut <- Ctrl+Alt+T runs xfce4-terminal --disable-server" \
    || say "shortcut <- Ctrl+Alt+T NOT set (xfconf-query failed, see log)"
else
  say "shortcut <- skipped: no live xfconf session"
fi

# ------------------------------------------------------- 2. wm + gtk theme
# ElementTree, not sed: these files are nested properties and a blind replace
# would happily corrupt them. Missing keys are inserted, existing ones set.
python3 - "$XF" <<'PY'
import os, sys
import xml.etree.ElementTree as ET

xf = sys.argv[1]

def load(path):
    if os.path.exists(path):
        try:
            return ET.parse(path)
        except Exception as e:
            print("meta-desktop: cannot parse %s (%s) — skipped" % (path, e))
    return None

def setprop(tree, parent_name, name, value, vtype="string"):
    root = tree.getroot()
    # find the parent property (may be the channel's direct child)
    parent = root
    if parent_name:
        found = None
        for p in root.iter("property"):
            if p.get("name") == parent_name:
                found = p
                break
        if found is None:
            found = ET.SubElement(root, "property",
                                  {"name": parent_name, "type": "empty"})
        parent = found
    for p in parent.findall("property"):
        if p.get("name") == name:
            p.set("value", value)
            p.set("type", vtype)
            return True
    ET.SubElement(parent, "property",
                  {"name": name, "type": vtype, "value": value})
    return True

wm_path = os.path.join(xf, "xfwm4.xml")
t = load(wm_path)
if t is None:
    t = ET.ElementTree(ET.Element("channel",
                                  {"name": "xfwm4", "version": "1.0"}))
setprop(t, "general", "theme", "MetaOS")
# macOS order: close + minimise on the left, maximise next to them.
setprop(t, "general", "button_layout", "CM|")
setprop(t, "general", "title_alignment", "center")
t.write(wm_path, encoding="UTF-8", xml_declaration=True)
print("meta-desktop: wm theme MetaOS, buttons left")

set_path = os.path.join(xf, "xsettings.xml")
t = load(set_path)
if t is None:
    t = ET.ElementTree(ET.Element("channel",
                                  {"name": "xsettings", "version": "1.0"}))
setprop(t, "Net", "ThemeName", "MetaOS")
if os.path.isdir("/usr/share/icons/MetaOS"):
    setprop(t, "Net", "IconThemeName", "MetaOS")
t.write(set_path, encoding="UTF-8", xml_declaration=True)
print("meta-desktop: gtk theme MetaOS")
PY

# ------------------------------------------------------ 2b. terminal colours
# xfce4-terminal does not read /etc/xdg/xfce4/terminal/terminalrc into an
# existing profile: the first window starts a terminal *server* that owns the
# settings for every later window, so if the user has no terminalrc yet the
# first terminal of the session locks in the white default for good. Put the
# Meta colours in the user's own file at login, before any terminal exists.
TERM_SRC=""
for cand in /etc/xdg/xfce4/terminal/terminalrc \
            /opt/face/theme/terminal/terminalrc; do
  if [ -r "$cand" ]; then TERM_SRC="$cand"; break; fi
done
if [ -n "$TERM_SRC" ] && [ ! -f "$HOME_DIR/.config/xfce4/terminal/terminalrc" ]; then
  mkdir -p "$HOME_DIR/.config/xfce4/terminal" 2>/dev/null \
    && cp -f "$TERM_SRC" "$HOME_DIR/.config/xfce4/terminal/terminalrc" \
    && say "terminal colours <- $TERM_SRC"
else
  [ -z "$TERM_SRC" ] && say "no Meta terminalrc to install — terminal stays on the stock colours"
fi

# ------------------------------------------------------------- 3. the dock
# plank reads a theme from /usr/share/plank/themes/<Name>, and one .dockitem
# per launcher. Both are written here so a fresh user gets the Meta dock.
SRC=/opt/face/theme
[ -d "$SRC" ] || SRC=/usr/share/metaos/theme

# The theme itself is installed system-wide by os-build/face/provision.sh. If
# it is missing, say so — a dock with no theme falls back to plank's default
# and that is a look, not a failure.
if [ -f /usr/share/plank/themes/MetaOS/dock.theme ]; then
  say "plank theme present"
elif [ -d "$SRC/dock" ]; then
  mkdir -p /usr/share/plank/themes/MetaOS 2>/dev/null \
    && cp -f "$SRC/dock/dock.theme" /usr/share/plank/themes/MetaOS/dock.theme 2>/dev/null \
    && say "plank theme -> /usr/share/plank/themes/MetaOS"
else
  say "no MetaOS plank theme — dock uses plank's default"
fi

# Dock preferences. HideMode=0 keeps it on screen (a dock that hides is a
# dock the demo never sees).
cat >"$PLANK/settings" <<'EOF'
[PlankDockPreferences]
Theme=Default
Alignment=Center
ItemsAlignment=Center
IconSize=40
ZoomEnabled=false
ZoomPercent=130
HideMode=0
Locked=false
EOF
say "plank settings -> $PLANK/settings"

# One row per tile: id | Name | Icon | program + args (separate words)
# A tile whose program is missing is not written, so the dock never shows a
# launcher that opens nothing. A tile whose icon PNG is missing is still
# written (the page matters more than the picture) but logs a named warning,
# because a themed name the theme does not carry draws a blank white tile.
# Idempotence. This script owns the dock, so it rewrites the whole set every
# run. Without this clear, a leftover .dockitem from an earlier install (a
# different numbering, or an app dropped from the list) sits beside the new
# ones: the synced image's dock had 34 items with imperium, trio, dashboard,
# board and calendar each in it twice. Numbering restarts at 01, so the two
# files also share a prefix and neither looks obviously stale.
rm -f "$PLANK"/launchers/*.dockitem "$APPS"/meta-*.desktop 2>/dev/null
say "dock reset: writing the Meta tile set from scratch"

APP_N=0
ICON_DIR="${ICON_DIR:-/usr/share/icons/metaos}"
add_app() {
  id="$1"; name="$2"; icon_name="$3"; shift 3
  # Absolute path wins: a themed icon name that the active icon theme does not
  # carry draws as a blank tile in plank (the white squares on first boot).
  if [ -f "$ICON_DIR/$icon_name.png" ]; then
    icon="$ICON_DIR/$icon_name.png"
  else
    icon="$icon_name"
    say "warn $id: icon $icon_name.png missing in $ICON_DIR — themed fallback, may draw blank"
  fi
  # "-" means no program check (kept for compatibility; unused today).
  if [ "${1:-}" = "-" ]; then shift; fi
  bin="$1"
  # Quote each exec word that contains a space (paths, --title values) so a
  # space cannot split the Exec= line. Words without spaces pass through.
  exec_line=""
  for w in "$@"; do
    case "$w" in
      *" "*) w="\"$w\"" ;;
    esac
    exec_line="${exec_line:+$exec_line }$w"
  done
  APP_N=$((APP_N + 1))
  idx=$(printf '%02d' "$APP_N")
  if [ "$bin" != "-" ] && ! command -v "$bin" >/dev/null 2>&1; then
    say "skip $id (no $bin)"
    return 0
  fi
  cat >"$APPS/meta-$id.desktop" <<EOF
[Desktop Entry]
Type=Application
Version=1.0
Name=$name
Comment=Meta OS
Exec=$exec_line
Terminal=false
Icon=$icon
Categories=MetaOS;
EOF
  cat >"$PLANK/launchers/$idx-meta-$id.dockitem" <<EOF
[PlankDockItemPreferences]
Launcher=file://$APPS/meta-$id.desktop
EOF
}

# Surfaces open in meta-app: one GTK window per app, no address bar, no tabs,
# no visible 127.0.0.1. Epiphany is no longer used for these tiles -- a browser
# tab is what made the apps look like webpages.
META_APP="${META_APP:-/usr/local/bin/meta-app}"

# Imperium and Trio are one program: Meta Vigiles (police), Meta Ignis (fire)
# and Meta Medicus (EMS) behind a product switcher. It is a native GTK shell
# over local files -- no browser tab, no remote host. Trio used to open the
# logo studio, and Imperium used to open the site's surfaces page, which is
# why neither tile showed the dispatch console.
IMPERIUM="${IMPERIUM:-/usr/share/metaos/apps/metaos-imperium.py}"

# --disable-server on purpose: xfce4-terminal's first window starts a server
# that then owns the colours for every later window. That server came up white
# even with the Meta terminalrc present, so Ctrl+Alt+T opened a white terminal
# while a directly started one was dark. Without a server, every window reads
# the user's own colours.
add_app terminal  "Terminal"   terminal        "xfce4-terminal --disable-server"
add_app files     "Files"      files           thunar
add_app notes     "Notes"      notes           meta-notes
add_app monitor   "Monitor"    dashboard       meta-monitor
add_app agents    "Agents"     agents          meta-agents
add_app editor    "Editor"     editor          mousepad
add_app calc      "Calculator" calculator      galculator
add_app settings  "Settings"   settings        xfce4-settings-manager
add_app trash     "Trash"      trash           thunar trash:///
add_app trio      "Trio"      imperium        "$IMPERIUM" --title "Meta Trio - Dispatch"
add_app imperium  "Imperium"  imperium        "$IMPERIUM" --title "Imperium - Command"

if [ -x "$META_APP" ]; then
  add_app web       "Web"       web             "$META_APP" --title Web --url http://127.0.0.1:18934/index.html
  add_app dashboard "Dashboard" dashboard       "$META_APP" --title Dashboard --url http://127.0.0.1:18900/dashboard.html
  add_app board     "Board"     board           "$META_APP" --title Board --url http://127.0.0.1:18900/board.html
  add_app calendar  "Calendar"  calendar        "$META_APP" --title Calendar --url http://127.0.0.1:18900/calendar.html
  add_app musica    "Musica"    musica          "$META_APP" --title Musica --url http://127.0.0.1:18900/musica.html
  add_app science   "Science"   science         "$META_APP" --title Science --url http://127.0.0.1:18934/labs/molecules/index.html
  # Each app gets its own page. Custos and Officina used to point at Imperium's
  # surfaces.html and at the site index -- three tiles, two pages, so two of the
  # boss's apps looked unwired. These are the dedicated pages that already ship
  # in /opt/face-site/design.
  add_app custos    "Custos"    custos          "$META_APP" --title Custos --url http://127.0.0.1:18934/design/meta-custos-watch.html
  add_app officina  "Officina"  officina        "$META_APP" --title Officina --url http://127.0.0.1:18934/design/meta-officina-blueprint.html
  # Product pages that shipped with no tile (APP_INVENTORY.md section 4).
  # Boards is the Imperium dispatch boards page; Messages is the live bus
  # (agent-2 ships bus.html — before that lands this tile explains itself
  # through meta-app's failure screen instead of opening blank).
  add_app boards    "Boards"    boards          "$META_APP" --title Boards --url http://127.0.0.1:18934/surfaces.html
  add_app messages  "Messages"  messages        "$META_APP" --title Messages --url http://127.0.0.1:18934/bus.html
  add_app logo      "Logo Studio" logo          "$META_APP" --title "Logo Studio" --url http://127.0.0.1:18934/logo-studio.html
  add_app music3d   "Music 3D"  music3d         "$META_APP" --title "Music 3D" --url http://127.0.0.1:18934/labs/music3d/index.html
  add_app notes3d   "3D Notes"  notes3d         "$META_APP" --title "3D Notes" --url http://127.0.0.1:18934/design/meta-musica-notes.html
  add_app budget    "Agent Budget" budget       "$META_APP" --title "Agent Budget" --url http://127.0.0.1:18934/design/agent-budget-dashboard.html
  # Aegis is agent-3's page (lands at /opt/face-site/aegis/). Same contract as
  # Messages: the tile is wired now, meta-app explains a missing backend.
  add_app aegis     "Aegis"     aegis           "$META_APP" --title Aegis --url http://127.0.0.1:18934/aegis/index.html
  # About carries live machine facts on port 18900 (agent-4's about.html).
  add_app about     "About"     about           "$META_APP" --title About --url http://127.0.0.1:18900/about.html
else
  say "meta-app missing at $META_APP — web tiles left out of the dock"
fi

# Stale items from a previous install (a tile whose program was removed) would
# stay in plank forever; drop dockitems with no .desktop behind them.
for f in "$PLANK"/launchers/*.dockitem; do
  [ -e "$f" ] || continue
  target=$(sed -n 's/^Launcher=file:\/\///p' "$f" | head -1)
  [ -n "$target" ] && [ ! -e "$target" ] && rm -f "$f" && say "dropped stale $(basename "$f")"
done

if [ -n "$OWNER" ]; then
  chown -R "$OWNER" "$HOME_DIR/.config/xfce4" "$HOME_DIR/.config/plank" \
    "$HOME_DIR/.local/share/applications" 2>/dev/null || true
fi

say "done: $(ls "$PLANK"/launchers 2>/dev/null | wc -l | tr -d ' ') dock items"

# --check-icons: every tile's Icon= must be a file that exists. An absolute
# path must exist; a bare themed name must exist as a PNG in the Meta icon
# dir (themed-name fallback that resolves nowhere draws blank in plank).
if [ "$CHECK_ICONS" = 1 ]; then
  fails=0; total=0
  for d in "$APPS"/meta-*.desktop; do
    [ -e "$d" ] || continue
    total=$((total + 1))
    ic=$(sed -n 's/^Icon=//p' "$d" | head -1)
    case "$ic" in
      /*) if [ -f "$ic" ]; then
            say "check-icons ok $(basename "$d"): $ic"
          else
            say "check-icons FAIL $(basename "$d"): $ic not a file"
            fails=$((fails + 1))
          fi ;;
      *) if [ -f "$ICON_DIR/$ic.png" ]; then
           say "check-icons ok $(basename "$d"): $ICON_DIR/$ic.png"
         else
           say "check-icons FAIL $(basename "$d"): $ic resolves nowhere"
           fails=$((fails + 1))
         fi ;;
    esac
  done
  say "check-icons: $((total - fails))/$total icons resolve"
  [ "$fails" -eq 0 ] || exit 1
fi

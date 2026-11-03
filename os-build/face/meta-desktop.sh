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
while [ $# -gt 0 ]; do
  case "$1" in
    --home)  HOME_DIR="$2"; shift 2 ;;
    --owner) OWNER="$2"; shift 2 ;;
    -h|--help) echo "usage: meta-desktop.sh [--home DIR] [--owner UID:GID]"; exit 0 ;;
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

# One row per tile: id | Name | Icon | Exec
# Exec is resolved to a real binary; a tile whose program is missing is not
# written, so the dock never shows a launcher that opens nothing.
APP_N=0
ICON_DIR=/usr/share/icons/metaos
add_app() {
  id="$1"; name="$2"; icon_name="$3"; shift 3
  # Absolute path wins: a themed icon name that the active icon theme does not
  # carry draws as a blank tile in plank (the white squares on first boot).
  if [ -f "$ICON_DIR/$icon_name.png" ]; then
    icon="$ICON_DIR/$icon_name.png"
  else
    icon="$icon_name"
  fi
  bin="$1"
  exec_line="$*"
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
META_APP=/usr/local/bin/meta-app

# Imperium and Trio are one program: Meta Vigiles (police), Meta Ignis (fire)
# and Meta Medicus (EMS) behind a product switcher. It is a native GTK shell
# over local files -- no browser tab, no remote host. Trio used to open the
# logo studio, and Imperium used to open the site's surfaces page, which is
# why neither tile showed the dispatch console.
IMPERIUM=/usr/share/metaos/apps/metaos-imperium.py

add_app terminal  "Terminal"   terminal        xfce4-terminal
add_app files     "Files"      files           thunar
add_app notes     "Notes"      notes           meta-notes
add_app monitor   "Monitor"    dashboard       meta-monitor
add_app agents    "Agents"     agents          meta-agents
add_app editor    "Editor"     editor          mousepad
add_app calc      "Calculator" calculator      galculator
add_app settings  "Settings"   settings        xfce4-settings-manager
add_app trash     "Trash"      trash           thunar trash:///
add_app trio      "Trio"      imperium        "$IMPERIUM"
add_app imperium  "Imperium"  imperium        "$IMPERIUM"

if [ -x "$META_APP" ]; then
  add_app web       "Web"       web             "$META_APP --title Web --url http://127.0.0.1:18934/index.html"
  add_app dashboard "Dashboard" dashboard       "$META_APP --title Dashboard --url http://127.0.0.1:18900/dashboard.html"
  add_app board     "Board"     board           "$META_APP --title Board --url http://127.0.0.1:18900/board.html"
  add_app calendar  "Calendar"  calendar        "$META_APP --title Calendar --url http://127.0.0.1:18900/calendar.html"
  add_app musica    "Musica"    musica          "$META_APP --title Musica --url http://127.0.0.1:18900/musica.html"
  add_app science   "Science"   science         "$META_APP --title Science --url http://127.0.0.1:18934/labs/molecules/index.html"
  # Each app gets its own page. Custos and Officina used to point at Imperium's
  # surfaces.html and at the site index -- three tiles, two pages, so two of the
  # boss's apps looked unwired. These are the dedicated pages that already ship
  # in /opt/face-site/design.
  add_app custos    "Custos"    custos          "$META_APP --title Custos --url http://127.0.0.1:18934/design/meta-custos-watch.html"
  add_app officina  "Officina"  officina        "$META_APP --title Officina --url http://127.0.0.1:18934/design/meta-officina-blueprint.html"
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

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
#   clock   date + seconds on the panel clock (post-process of the user copy)
#   wm      theme MetaOS + macOS button order (close/minimise on the left)
#   workspaces 2 (Main, Agents) to match the pager's two buttons
#   keys    Alt+Tab cycle, Super+Left/Right tile, Ctrl+Alt+Left/Right
#           workspace switch, Print/Alt+Print screenshot, Ctrl+Alt+L lock,
#           Ctrl+Alt+Del logout dialog — merged into the user's
#           xfce4-keyboard-shortcuts.xml, defaults elsewhere untouched
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
# The stock account on the base image is "ubuntu"; after rename_user.sh it is "meta".
# Hardcoding either one is how this script quietly did nothing on an image
# where the other name was live, so ask the account database first and only
# then fall back to the two names this project has ever used.
[ -n "$HOME_DIR" ] || HOME_DIR="${HOME:-}"
if [ -z "$HOME_DIR" ] || [ ! -d "$HOME_DIR" ]; then
  HOME_DIR=""
  for cand in "$(getent passwd 1000 2>/dev/null | cut -d: -f6)" /home/meta /home/ubuntu; do
    if [ -n "$cand" ] && [ -d "$cand" ]; then HOME_DIR="$cand"; break; fi
  done
fi
[ -d "${HOME_DIR:-/nonexistent}" ] || { echo "meta-desktop: no home at ${HOME_DIR:-?}" >&2; exit 1; }

say() { echo "meta-desktop: $*"; }
backup() { [ -e "$1" ] && [ ! -e "$1.metaos-fix.bak" ] && cp -p "$1" "$1.metaos-fix.bak" 2>/dev/null; return 0; }

XF="$HOME_DIR/.config/xfce4/xfconf/xfce-perchannel-xml"
APPS="$HOME_DIR/.local/share/applications"
PLANK="$HOME_DIR/.config/plank/dock1"
mkdir -p "$XF" "$APPS" "$PLANK/launchers" 2>/dev/null || {
  echo "meta-desktop: cannot create $HOME_DIR/.config" >&2; exit 1; }

# ---------------------------------------------------------------- 1. panel
# The Meta top bar ships at /etc/xdg/... as the channel default, but the live
# user already has a stock panel file that wins over it. Copy the Meta one
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

# ---------------------------------- 1b. panel clock: date + seconds
# The generated panel xml (T1-owned, do not edit there) ships the clock as
# "%a, %b %e %H:%M" — date but no seconds. The desktop spec wants seconds on
# the bar, so this edits only the user's copy, right after the copy above.
# The clock draws in the theme font through the panel's GTK theme; no font
# key exists on the clock plugin itself, so there is nothing to set here.
python3 - "$XF/xfce4-panel.xml" <<'PY'
import os, sys
import xml.etree.ElementTree as ET
path = sys.argv[1]
FMT = "%a, %b %e %H:%M:%S"
if not os.path.exists(path):
    print("meta-desktop: clock skipped (no user panel xml)")
else:
    try:
        t = ET.parse(path)
    except Exception as e:
        print("meta-desktop: cannot parse %s (%s) — clock skipped" % (path, e))
        t = None
    if t is not None:
        done = 0
        for c in t.getroot().iter("property"):
            if c.get("name") == "digital-time-format":
                c.set("value", FMT)
                done += 1
        if done:
            t.write(path, encoding="UTF-8", xml_declaration=True)
            print("meta-desktop: clock format <- %s" % FMT)
        else:
            print("meta-desktop: clock skipped (no digital-time-format key found)")
PY

# ------------------------------------------ 1c. Ctrl+Alt+T opens the terminal
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
# timeout, not a bare call: xfconf-query talks to xfconfd over the session bus
# and BLOCKS forever when the bus is still coming up — which is exactly the
# moment this runs (session start). That hang stopped session.sh before
# startxfce4, so the login sat on a black 1920x1080 screen with no desktop.
if command -v xfconf-query >/dev/null 2>&1 && timeout 5 xfconf-query -c xfwm4 -l >/dev/null 2>&1; then
  timeout 5 xfconf-query -c xfce4-keyboard-shortcuts \
    -p '/commands/custom/<Primary><Alt>t' \
    -n -t string -s 'xfce4-terminal --disable-server' 2>&1 \
    && say "shortcut <- Ctrl+Alt+T runs xfce4-terminal --disable-server" \
    || say "shortcut <- Ctrl+Alt+T NOT set (xfconf-query failed or timed out, see log)"
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

def button_layout():
    """The window-button layout lives in the theme's themerc, and nowhere else.

    xfconf is read before themerc, and this script writes xfconf — so a string
    hard-coded here silently overrides the theme. That is how the image ended
    up with `CM|`: close and maximise on the LEFT, no minimise at all, while
    themerc said `O|SHMC`. Between the two, windows drew no buttons and the
    report was "there is not an x or a - or a +". One source now: the theme.
    """
    for cand in ("/usr/share/themes/MetaOS/xfwm4/themerc",
                 "/opt/face/theme/xfwm4/themerc"):
        try:
            for line in open(cand):
                if line.startswith("button_layout="):
                    value = line.split("=", 1)[1].strip()
                    if value:
                        return value, cand
        except Exception:
            continue
    return "|HMC", "fallback"

layout, source = button_layout()
setprop(t, "general", "button_layout", layout)
setprop(t, "general", "title_alignment", "center")
# Two workspaces (Main, Agents): the top bar carries a pager, and a pager over
# one workspace is a button that does nothing. The system channel default
# already says 2, but a user file from an older session wins over it — so the
# login path enforces the pair here instead of trusting the default.
def drop_named(root, name):
    for parent in root.iter("property"):
        for child in list(parent):
            if child.tag == "property" and child.get("name") == name:
                parent.remove(child)
    for child in list(root):
        if child.tag == "property" and child.get("name") == name:
            root.remove(child)
drop_named(t.getroot(), "workspaces")
ws_el = ET.SubElement(t.getroot(), "property",
                      {"name": "workspaces", "type": "empty"})
ET.SubElement(ws_el, "property",
              {"name": "count", "type": "int", "value": "2"})
names_el = ET.SubElement(ws_el, "property",
                         {"name": "names", "type": "array"})
for n in ("Main", "Agents"):
    ET.SubElement(names_el, "value", {"type": "string", "value": n})
t.write(wm_path, encoding="UTF-8", xml_declaration=True)
print("meta-desktop: wm theme MetaOS, buttons '%s' (from %s)" % (layout, source))
print("meta-desktop: workspaces=2 (Main, Agents)")

set_path = os.path.join(xf, "xsettings.xml")
t = load(set_path)
if t is None:
    t = ET.ElementTree(ET.Element("channel",
                                  {"name": "xsettings", "version": "1.0"}))
setprop(t, "Net", "ThemeName", "MetaOS")
if os.path.isdir("/usr/share/icons/MetaOS"):
    setprop(t, "Net", "IconThemeName", "MetaOS")
# GTK apps that draw their own titlebar (mousepad, file choosers, every GTK3
# dialog) take their buttons from this key, not from xfwm4. Unset, they draw a
# bare strip with nothing to click — the other half of "there is no x button".
setprop(t, "Gtk", "DecorationLayout", "icon:minimize,maximize,close")
t.write(set_path, encoding="UTF-8", xml_declaration=True)
print("meta-desktop: gtk theme MetaOS + CSD buttons minimize,maximize,close")
PY

# -------------------------------------- 2b. keyboard shortcuts (Meta set)
# The Meta shortcut set, merged into the user's
# xfce4-keyboard-shortcuts.xml — never rewritten whole, never deleting the
# user's own bindings or the stock `default` tree. File-based like everything
# else here, so it works in the offline chroot as well as at login.
#
# The enforced set (Settings > Keyboard must list exactly these — see the
# cross-lane request for settings.html):
#   Ctrl+Alt+T      terminal (xfce4-terminal --disable-server)
#   Alt+Tab         cycle windows, with xfwm4's visible switcher
#   Super+Left      snap window left half        Super+Right  snap right half
#   Ctrl+Alt+Left   previous workspace           Ctrl+Alt+Right next workspace
#   Print           screenshot, full screen      Alt+Print    screenshot, window
#   Ctrl+Alt+L      lock screen (same session on unlock)
#   Ctrl+Alt+Del    logout dialog (the ONLY session-ending path; no binding
#                   here or anywhere else in this script kills the session)
# Clicking the desktop focuses it and clears window focus: that is xfdesktop's
# own behaviour and no binding here overrides it (guest check proves it).
python3 - "$XF" <<'PY'
import os, shutil, sys
import xml.etree.ElementTree as ET

xf = sys.argv[1]
ks_path = os.path.join(xf, "xfce4-keyboard-shortcuts.xml")
t = None
if os.path.exists(ks_path):
    try:
        t = ET.parse(ks_path)
    except Exception as e:
        print("meta-desktop: cannot parse %s (%s) — skipped" % (ks_path, e))
if t is None:
    t = ET.ElementTree(ET.Element("channel",
                                  {"name": "xfce4-keyboard-shortcuts",
                                   "version": "1.0"}))
root = t.getroot()

def scope(name):
    for p in root.findall("property"):
        if p.get("name") == name:
            return p
    return ET.SubElement(root, "property", {"name": name, "type": "empty"})

def custom(scope_name):
    s = scope(scope_name)
    for p in s.findall("property"):
        if p.get("name") == "custom":
            return p
    return ET.SubElement(s, "property", {"name": "custom", "type": "empty"})

def bind(parent, key, value):
    for p in parent.findall("property"):
        if p.get("name") == key:
            p.set("value", value)
            p.set("type", "string")
            return
    ET.SubElement(parent, "property",
                  {"name": key, "type": "string", "value": value})

cmds = custom("commands")
wm = custom("xfwm4")

# Window cycling, tiling, workspace switch: these values are xfwm4's own
# action names, so a key that does nothing means the name is wrong, not the
# binding. Always set: they are the desktop spec, not a preference.
for key, action in [
        ("<Alt>Tab", "cycle_window_key"),
        ("<Super>Left", "tile_left_key"),
        ("<Super>Right", "tile_right_key"),
        ("<Primary><Alt>Left", "left_workspace_key"),
        ("<Primary><Alt>Right", "right_workspace_key")]:
    bind(wm, key, action)
# App + session commands. The terminal binding duplicates the live
# xfconf-query above so it survives a session the query never saw.
bind(cmds, "<Primary><Alt>t", "xfce4-terminal --disable-server")
# The logout dialog — xfce4-session-logout with NO flags shows the dialog
# (logout / restart / shutdown buttons), it does not log out. This binding
# is the one session-ending path the desktop offers; nothing here passes
# --logout/--halt/--reboot or kills the session any other way.
bind(cmds, "<Primary><Alt>Delete", "xfce4-session-logout")
# Tool-gated: only bound when the tool is on PATH at login time (the login
# run always is; a chroot run that cannot see the tool simply skips, and the
# merge above means it never deletes a binding the login run wrote).
if shutil.which("xfce4-screenshooter") is not None:
    bind(cmds, "Print", "xfce4-screenshooter -f")
    bind(cmds, "<Alt>Print", "xfce4-screenshooter -w")
    print("meta-desktop: shortcuts Print/Alt+Print run xfce4-screenshooter")
else:
    print("meta-desktop: shortcuts Print/Alt+Print skipped (no xfce4-screenshooter on PATH)")
if shutil.which("xflock4") is not None:
    bind(cmds, "<Primary><Alt>l", "xflock4")
    print("meta-desktop: shortcut Ctrl+Alt+L runs xflock4")
else:
    print("meta-desktop: shortcut Ctrl+Alt+L skipped (no xflock4 on PATH)")
t.write(ks_path, encoding="UTF-8", xml_declaration=True)
print("meta-desktop: shortcuts merged (Alt+Tab cycle, Super+Left/Right tile, "
      "Ctrl+Alt+Left/Right workspace, Ctrl+Alt+Del logout dialog)")
PY

# ------------------------------------------------------ 2c. terminal colours
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
# Theme=MetaOS, not Default: the MetaOS plank theme is installed right above
# this block, and "Default" is why the dock still looked like stock plank after
# every other Meta change had landed.
cat >"$PLANK/settings" <<'EOF'
[PlankDockPreferences]
Theme=MetaOS
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
# Two words, not one quoted string: add_app checks the FIRST word with
# `command -v`, and a quoted "xfce4-terminal --disable-server" never resolves,
# which silently dropped the Terminal tile from every dock this script built.
add_app terminal  "Terminal"   terminal        xfce4-terminal --disable-server
add_app files     "Files"      files           thunar
add_app notes     "Notes"      notes           meta-notes
add_app monitor   "Monitor"    dashboard       meta-monitor
add_app agents    "Agents"     agents          meta-agents
add_app editor    "Editor"     editor          mousepad
# Calculator: the image ships galculator (the base image's own); mate-calc is what the
# ISO manifest names. Pick whichever is really installed instead of shipping a
# tile that opens nothing on one of the two.
CALC_BIN=galculator
command -v mate-calc >/dev/null 2>&1 && CALC_BIN=mate-calc
add_app calc      "Calculator" calculator      "$CALC_BIN"
add_app settings  "Settings"   settings        xfce4-settings-manager
add_app trash     "Trash"      trash           thunar trash:///
# Native, not a wrapped page: the control gallery is a GTK app that draws one of
# every widget the theme styles. It is the tile a judge clicks to see the theme.
add_app controls  "Controls"  controls        /usr/share/metaos/apps/metaos-controls.py
# The Trio split into three apps. Imperium stays the cross-division command
# console. Vigiles, Ignis and Medicus are separate programs on the same
# backend and the same camera list, each with its own page and layout. The old
# single "Trio" tile opened Imperium's page, so two tiles showed one screen;
# it is gone, and each division now has a tile that opens its own page.
# No "Imperium" tile: the single console page it opened is gone from the
# product — each division below is its own app on the same backend, and the
# Boards tile carries the dispatch boards. imperium/index.html is archived in
# the repo (the tests read it as a fixture) and is not installed.
add_app police    "Vigiles"   police          "$IMPERIUM" --division vigiles
add_app fire      "Ignis"     fire            "$IMPERIUM" --division ignis
add_app ems       "Medicus"   ems             "$IMPERIUM" --division medicus

if [ -x "$META_APP" ]; then
  # Web opens the local start page on 18900. It used to open 18934/index.html,
  # the dead hub that listed apps the dock already lists; that page is gone.
  add_app web       "Web"       web             "$META_APP" --title Web --url http://127.0.0.1:18900/start.html
  add_app dashboard "Dashboard" dashboard       "$META_APP" --title Dashboard --url http://127.0.0.1:18900/dashboard.html
  add_app calendar  "Calendar"  calendar        "$META_APP" --title Calendar --url http://127.0.0.1:18900/calendar.html
  add_app musica    "Musica"    musica          "$META_APP" --title Musica --url http://127.0.0.1:18900/musica.html
  add_app science   "Science"   science         "$META_APP" --title Science --url http://127.0.0.1:18934/labs/molecules/index.html
  # Each app gets its own page. Custos and Officina used to point at Imperium's
  # surfaces.html and at the site index -- three tiles, two pages, so two of the
  # boss's apps looked unwired. These are the dedicated pages that already ship
  # in /opt/face-site/design, and each one carries the Board chat box for its
  # own room (custos / officina).
  add_app custos    "Custos"    custos          "$META_APP" --title Custos --url http://127.0.0.1:18934/design/meta-custos-watch.html
  add_app officina  "Officina"  officina        "$META_APP" --title Officina --url http://127.0.0.1:18934/design/meta-officina-blueprint.html
  # Product pages that shipped with no tile (APP_INVENTORY.md section 4).
  # Boards is the dispatch boards page (surfaces.html, now the site root).
  add_app boards    "Boards"    boards          "$META_APP" --title Boards --url http://127.0.0.1:18934/surfaces.html
  # One messaging app, not three: the Board (board/board.mjs on 18935).
  # It replaced the face board.py stub, the Nuntius relay/viewer and the
  # Upstash-token bus page; rooms, presence and NOTIFY lines all live here.
  add_app messages  "Messages"  messages        "$META_APP" --title Messages --url http://127.0.0.1:18935/
  add_app music3d   "Music 3D"  music3d         "$META_APP" --title "Music 3D" --url http://127.0.0.1:18934/labs/music3d/index.html
  add_app notes3d   "3D Notes"  notes3d         "$META_APP" --title "3D Notes" --url http://127.0.0.1:18934/design/meta-musica-notes.html
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

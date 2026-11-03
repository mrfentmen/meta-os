#!/bin/sh
# provision.sh: install the Meta OS desktop face and its eight backends.
#
# Two modes:
#   sh provision.sh                 on a live machine, as the desktop user
#   sh provision.sh --root <DIR>    into an unpacked root filesystem (build)
#
# Copies the face to <DST>, the repo-root product pages to <SITE_DST>,
# installs the eight user services plus face.target, and verifies.
# Idempotent: safe to re-run.
set -eu
HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"

ROOT=""
if [ "${1:-}" = "--root" ]; then
  ROOT="${2:?--root needs a directory}"
  [ -d "$ROOT/usr" ] || { echo "provision(face): $ROOT is not a root filesystem" >&2; exit 2; }
  SUDO=""
  DST="$ROOT/opt/face"
  SITE_DST="$ROOT/opt/face-site"
  U="$ROOT/usr/lib/systemd/user"
  MODE=root
else
  SUDO="sudo"
  DST=/opt/face
  SITE_DST=/opt/face-site
  U="${HOME}/.config/systemd/user"
  MODE=live
fi
SRC="$HERE"
SITE_SRC="$(CDPATH= cd -- "$SRC/../.." && pwd)"

echo "provision(face): mode=$MODE dst=$DST units=$U"

# 0) clear stale manual servers from earlier dev sessions (live only)
if [ "$MODE" = live ]; then
  for pat in "http.server 18900" "http.server 18934" "launcher.py" "facts.py" "ptyd.py" "board.py" "files.py" "notesd.py"; do
    pkill -f "python3 .*/$pat" 2>/dev/null || true
  done
  sleep 1
fi

# 1) stage face content
$SUDO mkdir -p "$DST"
if [ "$SRC" != "$DST" ]; then
  $SUDO cp -r "$SRC/." "$DST/"
fi

# 1a) stage the session proof (AGENT 4): guest runs bash /opt/face/proof_session.sh
if [ -f "$HERE/../tools/proof_session.sh" ]; then
  $SUDO cp -f "$HERE/../tools/proof_session.sh" "$DST/proof_session.sh"
  $SUDO chmod +x "$DST/proof_session.sh"
fi

# 1a2) native desktop programs. These are GTK apps, not pages: they live in
# /usr/local/bin so the dock can launch them by name and a user can run them
# from a terminal with no browser involved.
$SUDO mkdir -p "$ROOT/usr/local/bin"
for src in "$HERE"/native/meta-*.py; do
  [ -e "$src" ] || continue
  prog="$(basename "$src" .py)"
  $SUDO install -m755 "$src" "$ROOT/usr/local/bin/$prog"
  echo "provision(face): native $prog -> /usr/local/bin/$prog"
done
$SUDO chmod +x "$DST/meta-desktop.sh" "$DST/session.sh" 2>/dev/null || true

# 1a3) the desktop theme pieces the native session reads at login. Each has
# its own owner path, and a missing piece is a silent visual fallback — so
# stage them together and say which ones landed.
THEME_SRC="$HERE/../iso/payload-theme"

# top bar: the channel default AND skel, so an existing user and a new one
# both get the Meta panel (meta-desktop.sh copies it into the user config).
if [ -f "$THEME_SRC/panel/xfce4-panel.xml" ]; then
  for d in "$ROOT/etc/xdg/xfce4/xfconf/xfce-perchannel-xml" \
           "$ROOT/etc/skel/.config/xfce4/xfconf/xfce-perchannel-xml"; do
    $SUDO mkdir -p "$d"
    $SUDO install -m644 "$THEME_SRC/panel/xfce4-panel.xml" "$d/xfce4-panel.xml"
  done
  echo "provision(face): Meta panel -> /etc/xdg + /etc/skel"
fi

# window decorations. MetaOS/xfwm4/themerc is what makes the buttons blue and
# puts close/minimise on the left; without this dir xfwm4 silently uses Default.
if [ -f "$THEME_SRC/xfwm4/themerc" ]; then
  $SUDO mkdir -p "$ROOT/usr/share/themes/MetaOS/xfwm4"
  $SUDO install -m644 "$THEME_SRC/xfwm4/themerc" "$ROOT/usr/share/themes/MetaOS/xfwm4/themerc"
  echo "provision(face): xfwm4 theme -> /usr/share/themes/MetaOS/xfwm4"
fi
if [ -f "$THEME_SRC/gtk/gtk.css" ]; then
  $SUDO mkdir -p "$ROOT/usr/share/themes/MetaOS/gtk-3.0"
  $SUDO install -m644 "$THEME_SRC/gtk/gtk.css" "$ROOT/usr/share/themes/MetaOS/gtk-3.0/gtk.css"
  echo "provision(face): gtk theme -> /usr/share/themes/MetaOS"
fi

# 1a4) the Meta dock icons. These are absolute-path PNGs used by the .desktop
# files, so the dock draws the real mark instead of a blank tile.
if [ -d "$THEME_SRC/icons/metaos" ]; then
  $SUDO mkdir -p "$ROOT/usr/share/icons/metaos"
  for png in "$THEME_SRC"/icons/metaos/*.png; do
    [ -e "$png" ] || continue
    $SUDO install -m644 "$png" "$ROOT/usr/share/icons/metaos/"
  done
  echo "provision(face): dock icons -> /usr/share/icons/metaos"
fi

# 1a5) the plank dock theme. Without it plank falls back to its default look.
THEME_DOCK="$THEME_SRC/dock/dock.theme"
if [ -f "$THEME_DOCK" ]; then
  $SUDO mkdir -p "$ROOT/usr/share/plank/themes/MetaOS"
  $SUDO install -m644 "$THEME_DOCK" "$ROOT/usr/share/plank/themes/MetaOS/dock.theme"
  echo "provision(face): plank theme -> /usr/share/plank/themes/MetaOS"
fi

# 1b) stage repo-root product pages for the dock iframes (served on 18934).
# Boards data only: os/worlds is ~100M, the pages fetch just pack.json,
# officina runs and custos runs.
if [ -f "$SITE_SRC/index.html" ] && [ -f "$SITE_SRC/js/app.js" ]; then
  $SUDO mkdir -p "$SITE_DST"
  for f in index.html surfaces.html logo-studio.html bus.html styles.css manifest.webmanifest icon-180.png; do
    if [ -f "$SITE_SRC/$f" ]; then
      $SUDO cp -f "$SITE_SRC/$f" "$SITE_DST/$f"
    fi
  done
  for d in js vendor design; do
    if [ -d "$SITE_SRC/$d" ]; then
      $SUDO rm -rf "$SITE_DST/$d"
      $SUDO cp -r "$SITE_SRC/$d" "$SITE_DST/$d"
    fi
  done
  for lab in molecules music3d; do
    if [ -f "$SITE_SRC/labs/$lab/index.html" ]; then
      $SUDO rm -rf "$SITE_DST/labs/$lab"
      $SUDO mkdir -p "$SITE_DST/labs"
      $SUDO cp -r "$SITE_SRC/labs/$lab" "$SITE_DST/labs/$lab"
    fi
  done
  # Aegis lives in the repo as aegis-page/ but is served as /aegis/ (that is
  # the path the dock tile opens). metaos-update.sh already did this copy; a
  # fresh provision did not, so a clean image shipped the tile and 404ed it.
  if [ -f "$SITE_SRC/aegis-page/index.html" ]; then
    $SUDO rm -rf "$SITE_DST/aegis"
    $SUDO mkdir -p "$SITE_DST/aegis"
    $SUDO cp -r "$SITE_SRC/aegis-page/." "$SITE_DST/aegis/"
  else
    echo "site stage: no aegis-page/ in $SITE_SRC — Aegis tile will 404"
  fi
  for pack in "$SITE_SRC"/os/worlds/*/pack.json; do
    if [ -f "$pack" ]; then
      world="$(basename "$(dirname "$pack")")"
      $SUDO mkdir -p "$SITE_DST/os/worlds/$world"
      $SUDO cp -f "$pack" "$SITE_DST/os/worlds/$world/pack.json"
    fi
  done
  wav="$SITE_SRC/os/worlds/musica/sessions/hn029-chipsynth/normalized/take-006.wav"
  if [ -f "$wav" ]; then
    $SUDO mkdir -p "$SITE_DST/os/worlds/musica/sessions/hn029-chipsynth/normalized"
    $SUDO cp -f "$wav" "$SITE_DST/os/worlds/musica/sessions/hn029-chipsynth/normalized/"
  fi
  for spec in "officina:json" "custos:jsonl"; do
    world="${spec%%:*}"
    ext="${spec##*:}"
    for run in "$SITE_SRC"/os/worlds/"$world"/runs/*."$ext"; do
      if [ -f "$run" ]; then
        $SUDO mkdir -p "$SITE_DST/os/worlds/$world/runs"
        $SUDO cp -f "$run" "$SITE_DST/os/worlds/$world/runs/"
      fi
    done
  done
else
  $SUDO mkdir -p "$SITE_DST"
  echo "site stage: no repo checkout at $SITE_SRC — leaving $SITE_DST alone"
fi

# linger is best-effort: user services survive logout/reboot when it works
if [ "$MODE" = live ]; then
  $SUDO loginctl enable-linger "$(id -un)" 2>/dev/null || true
fi

# 2) install user units
# NOTE: units must contain RUNTIME paths (/opt/face), not build-root paths
# ($DST may be $ROOT/opt/face when MODE=root). Baking $ROOT into a unit
# (e.g. WorkingDirectory=/mnt/opt/face) makes 18900 never answer on first
# boot, so the kiosk always falls back to XFCE. See SESSION.md.
RUNTIME_DST=/opt/face
RUNTIME_SITE=/opt/face-site
mkdir -p "$U"
cat > "$U/face-http.service" <<EOF
[Unit]
Description=face static server 18900
After=network.target
[Service]
WorkingDirectory=$RUNTIME_DST
ExecStart=/usr/bin/python3 -m http.server 18900 --bind 127.0.0.1
Restart=on-failure
[Install]
WantedBy=default.target
EOF
cat > "$U/face-launcher.service" <<EOF
[Unit]
Description=face launcher 18931
After=network.target
[Service]
ExecStart=/usr/bin/python3 $RUNTIME_DST/launcher.py
Restart=on-failure
[Install]
WantedBy=default.target
EOF
cat > "$U/face-facts.service" <<EOF
[Unit]
Description=face facts 18932
After=network.target
[Service]
ExecStart=/usr/bin/python3 $RUNTIME_DST/facts.py
Restart=on-failure
[Install]
WantedBy=default.target
EOF
cat > "$U/face-ptyd.service" <<EOF
[Unit]
Description=face ptyd 18933
After=network.target
[Service]
ExecStart=/usr/bin/python3 $RUNTIME_DST/ptyd.py
Restart=on-failure
[Install]
WantedBy=default.target
EOF
cat > "$U/face-board.service" <<EOF
[Unit]
Description=face board 18935
After=network.target
[Service]
ExecStart=/usr/bin/python3 $RUNTIME_DST/board.py
Restart=on-failure
[Install]
WantedBy=default.target
EOF
cat > "$U/face-files.service" <<EOF
[Unit]
Description=face files 18936
After=network.target
[Service]
ExecStart=/usr/bin/python3 $RUNTIME_DST/files.py
Restart=on-failure
[Install]
WantedBy=default.target
EOF
cat > "$U/face-notesd.service" <<EOF
[Unit]
Description=face notes calendar settings 18937
After=network.target
[Service]
ExecStart=/usr/bin/python3 $RUNTIME_DST/notesd.py
Restart=on-failure
[Install]
WantedBy=default.target
EOF
cat > "$U/face-site.service" <<EOF
[Unit]
Description=face product site 18934 (repo-root pages for dock iframes)
After=network.target
[Service]
WorkingDirectory=$RUNTIME_SITE
ExecStart=/usr/bin/python3 -m http.server 18934 --bind 127.0.0.1
Restart=on-failure
[Install]
WantedBy=default.target
EOF

# face.target: the session starts one thing, not seven races.
cat > "$U/face.target" <<'EOF'
[Unit]
Description=Meta OS desktop face (all backends)
Wants=face-http.service face-site.service face-launcher.service face-facts.service face-ptyd.service face-board.service face-files.service face-notesd.service
After=face-http.service face-site.service face-launcher.service face-facts.service face-ptyd.service face-board.service face-files.service face-notesd.service
[Install]
WantedBy=default.target
EOF

if [ "$MODE" = live ]; then
  systemctl --user daemon-reload
  systemctl --user enable --now face.target
else
  # No systemd runs at build time: hand-make the enable links.
  mkdir -p "$U/default.target.wants"
  for s in face-http face-site face-launcher face-facts face-ptyd face-board face-files face-notesd face; do
    ln -sf "$U/$s.service" "$U/default.target.wants/$s.service" 2>/dev/null || true
  done
  ln -sf "$U/face.target" "$U/default.target.wants/face.target" 2>/dev/null || true
  echo "provision(face): units staged, enable links created by hand"
fi

# 3) verify
FAIL=0
check() {
  desc=$1; shift
  i=0
  while [ "$i" -lt 10 ]; do
    if "$@" >/dev/null 2>&1; then echo "$desc: OK"; return 0; fi
    i=$((i + 1)); sleep 1
  done
  echo "$desc: FAIL"; FAIL=1; return 0
}
if [ "$MODE" = live ]; then
  check "http 18900 /shell.html" curl -fs -o /dev/null http://127.0.0.1:18900/shell.html
  check "site 18934 /index.html" curl -fs -o /dev/null http://127.0.0.1:18934/index.html
  check "site 18934 /logo-studio.html" curl -fs -o /dev/null http://127.0.0.1:18934/logo-studio.html
  check "site 18934 /js/app.js" curl -fs -o /dev/null http://127.0.0.1:18934/js/app.js
  check "site 18934 /aegis/index.html" curl -fs -o /dev/null http://127.0.0.1:18934/aegis/index.html
  check "site 18934 /bus.html" curl -fs -o /dev/null http://127.0.0.1:18934/bus.html
  check "launcher 18931 /launch" python3 -c "import http.client; c=http.client.HTTPConnection('127.0.0.1',18931,timeout=5); c.request('POST','/launch',body='{}',headers={'Content-Type':'application/json'}); assert b'ok' in c.getresponse().read()"
  check "facts 18932 /facts" curl -fs -o /dev/null http://127.0.0.1:18932/facts
  check "ptyd 18933 tcp" python3 -c "import socket;socket.create_connection(('127.0.0.1',18933),timeout=5).close()"
  check "board 18935 /rooms" curl -fs -o /dev/null http://127.0.0.1:18935/rooms
  check "files 18936 /trash" curl -fs -o /dev/null http://127.0.0.1:18936/trash
  check "notesd 18937 /notes" curl -fs -o /dev/null http://127.0.0.1:18937/notes
  check "notesd 18937 /settings" curl -fs -o /dev/null http://127.0.0.1:18937/settings
  check "notesd 18937 /events" curl -fs -o /dev/null http://127.0.0.1:18937/events
else
  # A rootfs has no running services: check the files that make them start.
  for f in face-http face-site face-launcher face-facts face-ptyd face-board face-files face-notesd; do
    if [ -f "$U/$f.service" ]; then echo "unit $f: OK"; else echo "unit $f: FAIL"; FAIL=1; fi
  done
  for f in shell.html start.html login.html notesd.py ptyd.py launcher.py files.py board.py facts.py notes.html calendar.html settings.html dashboard.html search.js; do
    if [ -f "$DST/$f" ]; then echo "face $f: OK"; else echo "face $f: FAIL"; FAIL=1; fi
  done
  if [ -f "$U/default.target.wants/face.target" ]; then echo "face.target enabled: OK"; else echo "face.target enabled: FAIL"; FAIL=1; fi
  # The dock tile opens /aegis/index.html on 18934; provision must have copied it.
  if [ -f "$SITE_DST/aegis/index.html" ]; then echo "site aegis/index.html: OK"; else echo "site aegis/index.html: FAIL"; FAIL=1; fi
fi

echo "next: log in — the Meta OS session (session.sh) builds the panel and dock, starts face.target, then execs startxfce4; kiosk.sh only runs if /etc/metaos/kiosk exists"
exit "$FAIL"

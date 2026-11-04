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

# 1a2) the LOGIN SCREEN. unity-greeter is the greeter in this image and it
# reads the com.canonical.unity-greeter gsettings schema, not
# /etc/lightdm/unity-greeter.conf — so the conf we shipped was dead config and
# the greeter fell back to the schema defaults: the Ubuntu warty background
# (absent here, so desktop-base's green emerald showed instead) with the stock
# Ubuntu logo. Two independent fixes, on purpose:
#   a) the override that sets the Meta art, compiled when glib can be;
#   b) the two files those defaults point at, written with Meta art, so a
#      build whose schemas are not recompiled still cannot show Ubuntu's.
# 1a2b) the animated wallpaper. meta-live.py plays /usr/share/metaos/studio-loop
# at 30 fps; the image shipped 16 kernel frames there, so the loop span once a
# second and stepped 22.5 degrees between frames. The set now comes from the
# logo studio (loop_from_studio.mjs + loop_frames_to_wallpaper.py), 60 frames
# per turn. Replace, never merge: an old 16-frame loop beside a new 60-frame
# one makes the cycle play two different drawings in the same turn.
LOOP_SRC="$THEME_SRC/wallpapers/studio-loop"
if [ -d "$LOOP_SRC" ]; then
  _n=$(ls "$LOOP_SRC"/loop-*.jpg 2>/dev/null | wc -l | tr -d ' ')
  if [ "${_n:-0}" -ge 8 ]; then
    $SUDO rm -rf "$ROOT/usr/share/metaos/studio-loop"
    $SUDO mkdir -p "$ROOT/usr/share/metaos/studio-loop"
    $SUDO cp -f "$LOOP_SRC"/loop-*.jpg "$ROOT/usr/share/metaos/studio-loop/"
    echo "provision(face): wallpaper loop -> /usr/share/metaos/studio-loop (${_n} frames)"
  else
    echo "provision(face): wallpaper loop source has ${_n:-0} frames — left as is"
  fi
fi
# the player itself, so a face-only sync also updates the animation code
if [ -f "$THEME_SRC/wallpapers/live/meta-live.py" ]; then
  $SUDO install -m755 "$THEME_SRC/wallpapers/live/meta-live.py" \
    "$ROOT/usr/share/metaos/apps/meta-live.py"
  echo "provision(face): wallpaper player -> /usr/share/metaos/apps/meta-live.py"
fi

GREETER_SRC="$THEME_SRC/greeter"
if [ -f "$GREETER_SRC/99_metaos-greeter.gschema.override" ]; then
  $SUDO mkdir -p "$ROOT/usr/share/glib-2.0/schemas"
  $SUDO install -m644 "$GREETER_SRC/99_metaos-greeter.gschema.override" \
    "$ROOT/usr/share/glib-2.0/schemas/99_metaos-greeter.gschema.override"
  # No --strict here: this image carries schemas whose paths are deprecated
  # (apps.light-locker, org.freedesktop.ibus, …), and --strict turns each of
  # those warnings into a failure. That is why the cache stayed stale after the
  # override was installed: the compile was refused, quietly, every time, and
  # unity-greeter kept reading Ubuntu's art out of the old cache.
  if [ "$(uname -s)" = Linux ] && command -v glib-compile-schemas >/dev/null 2>&1; then
    glib-compile-schemas "$ROOT/usr/share/glib-2.0/schemas" 2>/dev/null \
      && echo "provision(face): greeter schemas compiled" \
      || echo "provision(face): greeter schemas NOT compiled (override installed; metaos-schemas.service retries at boot)"
  else
    echo "provision(face): no runnable glib here — metaos-schemas.service compiles at boot"
  fi
  echo "provision(face): greeter gsettings override -> /usr/share/glib-2.0/schemas"
fi
# The mark: unity-greeter's stock logo is the Ubuntu logo, at a fixed path.
if [ -f "$GREETER_SRC/meta-m.png" ]; then
  $SUDO mkdir -p "$ROOT/usr/share/unity-greeter"
  $SUDO install -m644 "$GREETER_SRC/meta-m.png" "$ROOT/usr/share/unity-greeter/logo.png"
  $SUDO install -m644 "$GREETER_SRC/meta-m.png" "$ROOT/usr/share/backgrounds/meta-m.png" 2>/dev/null || true
  echo "provision(face): greeter logo -> /usr/share/unity-greeter/logo.png (Meta mark)"
fi
# The background: the schema's default path is the Ubuntu warty image. This
# build debranded that file away, which is why a *green* desktop-base emerald
# appeared — provide the path with Meta art instead of an empty fallback.
if [ -f "$GREETER_SRC/meta-ascii.png" ]; then
  $SUDO mkdir -p "$ROOT/usr/share/backgrounds"
  $SUDO install -m644 "$GREETER_SRC/meta-ascii.png" \
    "$ROOT/usr/share/backgrounds/warty-final-ubuntu.png"
  echo "provision(face): greeter background default -> Meta ASCII (no Ubuntu art)"
fi

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

# window decorations. MetaOS/xfwm4/themerc is what colours the titlebar; the
# 15 svgs are what make the buttons EXIST. xfwm4 resolves each button by name
# and state, and a miss draws nothing — that is the "no x, no -, no +" bug, so
# the art is installed in the same block as the colours and never apart.
if [ -f "$THEME_SRC/xfwm4/themerc" ]; then
  $SUDO mkdir -p "$ROOT/usr/share/themes/MetaOS/xfwm4"
  $SUDO install -m644 "$THEME_SRC/xfwm4/themerc" "$ROOT/usr/share/themes/MetaOS/xfwm4/themerc"
  nbtn=0
  for svg in "$THEME_SRC"/xfwm4/*-*.svg "$THEME_SRC"/xfwm4/*-*.png; do
    [ -f "$svg" ] || continue
    $SUDO install -m644 "$svg" "$ROOT/usr/share/themes/MetaOS/xfwm4/$(basename "$svg")" || exit 1
    nbtn=$((nbtn + 1))
  done
  echo "provision(face): xfwm4 theme + $nbtn button images -> /usr/share/themes/MetaOS/xfwm4"
  if [ "$nbtn" -eq 0 ]; then
    echo "provision(face): WARNING no button svgs — windows will have an empty titlebar" >&2
  fi
fi
# xfconf wins over themerc; without the channel file the session keeps whatever
# layout the stock image had.
if [ -f "$THEME_SRC/xfwm4/xfwm4.xml" ]; then
  for d in "$ROOT/etc/xdg/xfce4/xfconf/xfce-perchannel-xml" \
           "$ROOT/etc/skel/.config/xfce4/xfconf/xfce-perchannel-xml"; do
    $SUDO mkdir -p "$d"
    $SUDO install -m644 "$THEME_SRC/xfwm4/xfwm4.xml" "$d/xfwm4.xml"
  done
  echo "provision(face): xfwm4 button layout -> xfconf channel"
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

# 1a4b) the Meta terminal colours, as an actual XDG default rather than a
# comment in a doc. metaos-terminal-profile.txt shipped to /usr/share/doc and
# nothing read it, so Ctrl+Alt+T opened xfce4-terminal's white default while
# the dock's Terminal tile was dark -- two terminals, two looks, one OS.
TERM_RC="$ROOT/etc/xdg/xfce4/terminal/terminalrc"
if [ ! -f "$TERM_RC" ]; then
  $SUDO mkdir -p "$(dirname "$TERM_RC")"
  $SUDO tee "$TERM_RC" >/dev/null <<'EOF'
[Configuration]
ColorUseTheme=FALSE
ColorForeground=#EDF5FF
ColorBackground=#070B16
ColorPalette=#070B16;#FF4F9A;#20D6A3;#FFBD4A;#1877F2;#8B5CF6;#69DDFF;#EDF5FF;#52617A;#FF4F9A;#20D6A3;#FFBD4A;#78BAFF;#8B5CF6;#69DDFF;#FFFFFF
FontName=Ubuntu Mono 11
BackgroundMode=TERMINAL_BACKGROUND_SOLID
EOF
  echo "provision(face): terminal defaults -> /etc/xdg/xfce4/terminal/terminalrc"
fi
# ...and into the profiles themselves. xfce4-terminal's first window starts a
# terminal *server* that then owns the colours for every later window, so a
# session whose first terminal opened before the user had a terminalrc shows
# the stock white for the rest of that login — which is exactly what happened.
# Writing it here makes the dark terminal deterministic; an existing file is
# never overwritten, so a user's own colours survive a sync.
if [ -f "$TERM_RC" ]; then
  for _home in "$ROOT/etc/skel" "$ROOT"/home/*; do
    [ -d "$_home" ] || continue
    _dst="$_home/.config/xfce4/terminal/terminalrc"
    if [ ! -f "$_dst" ]; then
      $SUDO mkdir -p "$(dirname "$_dst")"
      $SUDO cp -f "$TERM_RC" "$_dst"
      echo "provision(face): terminal colours -> $_dst"
    fi
  done
fi

# 1a5) the plank dock theme. Without it plank falls back to its default look.
THEME_DOCK="$THEME_SRC/dock/dock.theme"
if [ -f "$THEME_DOCK" ]; then
  $SUDO mkdir -p "$ROOT/usr/share/plank/themes/MetaOS"
  $SUDO install -m644 "$THEME_DOCK" "$ROOT/usr/share/plank/themes/MetaOS/dock.theme"
  echo "provision(face): plank theme -> /usr/share/plank/themes/MetaOS"
fi

# 1a6) compile the gsettings schema cache. This is what the login screen reads.
# The greeter override (1a3) only takes effect through gschemas.compiled, and a
# cache compiled before that override shipped still holds Ubuntu's emerald
# background and Ubuntu logo — the green screen the user kept hitting. So the
# compile runs here when a glib is actually runnable, and a oneshot unit re-runs
# it at boot with the guest's own glib, which keeps host and guest versions from
# ever disagreeing.
SCHEMAS="$ROOT/usr/share/glib-2.0/schemas"
if [ -d "$SCHEMAS" ]; then
  if [ "$(uname -s)" = Linux ] && command -v glib-compile-schemas >/dev/null 2>&1; then
    if glib-compile-schemas "$SCHEMAS" 2>/dev/null; then
      echo "provision(face): schema cache compiled -> $SCHEMAS/gschemas.compiled"
    else
      echo "provision(face): schema compile failed here — the boot unit will do it"
    fi
  else
    echo "provision(face): schema cache left to the boot unit (no glib on this host)"
  fi
  $SUDO mkdir -p "$ROOT/etc/systemd/system/graphical.target.wants"
  $SUDO tee "$ROOT/etc/systemd/system/metaos-schemas.service" >/dev/null <<'EOF'
[Unit]
Description=Meta OS: recompile the gsettings schema cache before login
Documentation=file:/opt/face/README.md
After=local-fs.target
Before=display-manager.service lightdm.service

[Service]
Type=oneshot
RemainAfterExit=yes
# No `set -e` games: a missing tool must never cost the login screen. If the
# compile cannot run, the previous cache stays and the boot still proceeds.
ExecStart=/bin/sh -c 'command -v glib-compile-schemas >/dev/null 2>&1 && glib-compile-schemas /usr/share/glib-2.0/schemas || echo "metaos-schemas: glib-compile-schemas unavailable, cache unchanged"'

[Install]
WantedBy=graphical.target
EOF
  ln -sf "../metaos-schemas.service" \
    "$ROOT/etc/systemd/system/graphical.target.wants/metaos-schemas.service" 2>/dev/null \
    || $SUDO ln -sf "../metaos-schemas.service" \
         "$ROOT/etc/systemd/system/graphical.target.wants/metaos-schemas.service"
  echo "provision(face): unit metaos-schemas.service -> /etc/systemd/system"
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
  # Imperium's console links ../styles.css and ../vendor, so it is served from
  # the site root rather than from /usr/share/metaos/imperium where those
  # relative paths fall off the end of the tree and the page renders unstyled.
  if [ -f "$SITE_SRC/imperium/index.html" ]; then
    $SUDO rm -rf "$SITE_DST/imperium"
    $SUDO mkdir -p "$SITE_DST/imperium"
    $SUDO cp -r "$SITE_SRC/imperium/." "$SITE_DST/imperium/"
  else
    echo "site stage: no imperium/ in $SITE_SRC — Trio falls back to the bare page"
  fi
  # The Imperium/Trio window is a python app that lives in the ISO payload, not
  # in the face, so a face-only sync left an old copy in the image: the one that
  # looked for the page under /usr/share/metaos/imperium and drew it unstyled.
  # Install it here too, so the image's app and the repo's app are the same file.
  IMP_PY="$SITE_SRC/os-build/iso/payload-theme/apps/metaos-imperium.py"
  if [ -f "$IMP_PY" ]; then
    $SUDO install -D -m755 "$IMP_PY" "${ROOT}/usr/share/metaos/apps/metaos-imperium.py"
    echo "provision(face): imperium app -> /usr/share/metaos/apps/metaos-imperium.py"
  fi
  # The console's backend. face-only syncs used to leave the image's copy at
  # whatever the last ISO bake wrote, so a server-side fix (the static-root
  # override below) never reached the guest and Trio kept loading file://.
  if [ -d "$SITE_SRC/server" ]; then
    $SUDO mkdir -p "$ROOT/usr/share/metaos/server"
    for mjs in "$SITE_SRC"/server/*.mjs; do
      [ -f "$mjs" ] || continue
      $SUDO cp -f "$mjs" "$ROOT/usr/share/metaos/server/"
    done
    echo "provision(face): console backend -> /usr/share/metaos/server"
  fi
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

# 2b) the repo share must never hold the boot hostage.
# /etc/fstab in this image mounts the host tree over 9p for the agent lanes:
#   metaos_repo /mnt/metaos 9p trans=virtio,version=9p2000.L,rw,nofail 0 0
# nofail covers a device that never appears, but a 9p mount is not a device:
# systemd starts the mount job, the kernel logs "9pnet_virtio: no channels
# available for device metaos_repo", and the job waits for a channel that will
# never exist. local-fs.target never finishes, graphical.target never starts,
# and the guest sits on a black screen with no error on it — the exact symptom
# this project kept calling "the black box bug". Boot with an automount unit
# instead: nothing is attempted until something opens /mnt/metaos, and a boot
# with no share attached reaches the desktop and fails loudly at first use.
FSTAB="$ROOT/etc/fstab"
if [ -n "$ROOT" ] && [ -f "$FSTAB" ] && grep -q 'metaos_repo' "$FSTAB"; then
  if grep -q 'x-systemd.automount' "$FSTAB"; then
    echo "provision(face): /mnt/metaos already automount — boot cannot block on it"
  else
    cp -f "$FSTAB" "$FSTAB.metaos.bak"
    # awk, not python3: provision also runs inside a bare ubuntu container for
    # sync_image.sh, where python3 is not installed. A missing interpreter here
    # aborted the whole provision halfway through.
    awk 'BEGIN { OFS="\t" }
         $1 == "metaos_repo" {
           if ($4 !~ /(^|,)nofail(,|$)/) $4 = $4 ",nofail"
           if ($4 !~ /x-systemd\.automount/) $4 = $4 ",x-systemd.automount"
           if ($4 !~ /x-systemd\.idle-timeout/) $4 = $4 ",x-systemd.idle-timeout=120"
         }
         { print }' "$FSTAB" > "$FSTAB.metaos.new" && mv "$FSTAB.metaos.new" "$FSTAB"
    echo "provision(face): /mnt/metaos switched to automount (backup $FSTAB.metaos.bak)"
  fi
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
  # A boot with no 9p share attached must still reach the desktop. Root mode
  # only: in live mode /etc/fstab is the developer's own machine.
  if [ "$MODE" = root ] && [ -f "$FSTAB" ]; then
    if grep -q 'metaos_repo' "$FSTAB" && ! grep -q 'x-systemd.automount' "$FSTAB"; then
      echo "fstab metaos_repo non-blocking: FAIL"; FAIL=1
    else
      echo "fstab metaos_repo non-blocking: OK"
    fi
  fi
fi

echo "next: log in — the Meta OS session (session.sh) builds the panel and dock, starts face.target, then execs startxfce4; kiosk.sh only runs if /etc/metaos/kiosk exists"
exit "$FAIL"

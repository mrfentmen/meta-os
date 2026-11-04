#!/bin/sh
# Meta OS session entry — what lightdm's "Meta OS Desktop" runs.
#
# DEFAULT: the native desktop. XFCE's window manager owns the windows, plank
# owns the dock, and every tile in the dock is a real installed program
# (Thunar, xfce4-terminal, mousepad, mate-calc, meta-notes, meta-monitor,
# meta-agents). No browser starts at login.
#
# KIOSK MODE is still available and now opt-in only: create /etc/metaos/kiosk
# or export METAOS_KIOSK=1. That mode is the old fullscreen web shell and it
# still works; it is just not the default any more, because the shell is a web
# page and the desktop has to be software.
#
# Fallback contract (do not break): if anything here fails, this script still
# ends in `exec startxfce4`, so a login always lands on a working desktop.
set -u

LOG=/tmp/metaos-session.log
mkdir -p /tmp 2>/dev/null || true
say() { echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] $*" >>"$LOG" 2>&1; }

say "=== session start ==="

# Resolution. QEMU's cocoa window opens at 640x360 and tells the guest so, and
# X then keeps that mode for the whole session — a 640x360 desktop with the
# wallpaper window sized to a monitor it does not fill, which reads as "the
# wallpaper disappeared". The GPU advertises 1920x1080 as the preferred mode,
# so ask for it explicitly. Headless boots already come up at 1920x1080 and
# this is a no-op there. Best-effort: no xrandr (or no output) must not stop
# the login.
if command -v xrandr >/dev/null 2>&1; then
  _out=$(xrandr 2>/dev/null | sed -n 's/^\([A-Za-z0-9-]*\) connected primary.*/\1/p' | head -1)
  if [ -n "$_out" ]; then
    if xrandr --output "$_out" --mode 1920x1080 >>"$LOG" 2>&1; then
      say "resolution: $_out -> 1920x1080"
    else
      say "resolution: xrandr could not set 1920x1080 on $_out (desktop may be 640x360)"
    fi
  else
    say "resolution: no connected primary output found — left as is"
  fi
fi

# 3D: Science Lab (labs/molecules) and the 3D music notes are three.js scenes.
# This VM's virtio-gpu exposes no 3D engine, so a hardware GL request fails and
# the WebGL context comes back null — a blank canvas in the demo. Mesa ships
# swrast/llvmpipe in this image, so ask for it explicitly: slower, but real.
export LIBGL_ALWAYS_SOFTWARE=1
export GALLIUM_DRIVER=llvmpipe
export WEBKIT_DISABLE_DMABUF_RENDERER=1

# 1 — per-user desktop config (panel, dock, window theme). File-based and
# idempotent; safe to run on every login.
if [ -x /opt/face/meta-desktop.sh ]; then
  /opt/face/meta-desktop.sh >>"$LOG" 2>&1 || say "meta-desktop.sh returned non-zero"
else
  say "no /opt/face/meta-desktop.sh — dock/panel left as the base image has them"
fi

# 2 — the local backends. Every web tile in the dock is a page on 127.0.0.1,
# and the old kiosk was what started face.target. Without this the dock opens
# blank windows, so it starts here, before anything can be clicked.
if systemctl --user start face.target >>"$LOG" 2>&1; then
  say "face.target started"
else
  say "face.target start returned non-zero"
fi
systemctl --user start metaosd.service >>"$LOG" 2>&1 \
  || say "metaosd.service did not start (Agents window will say so)"

# agent relay: the login hook seeds the env and starts the oc2-* units. It is
# best-effort on purpose — a relay that fails must not take the desktop down.
if [ -x /usr/local/bin/meta-agent-login ]; then
  ( /usr/local/bin/meta-agent-login >>"$LOG" 2>&1 ) &
  say "agent login hook scheduled"
fi

# 2b2 — the About page's facts. about.html is a static page (18900 is
# `python3 -m http.server`, no code runs there), so the live values it shows
# are rendered here, at login, from the live /etc/os-release and uname of
# THIS machine into about.json beside it. Best-effort on purpose: if the
# file cannot be written the page shows its fallback line, and a failed
# write must never break the login.
# Paths are overridable for offline testing (ABOUT_JSON, FACE_OS_RELEASE).
ABOUT_JSON="${ABOUT_JSON:-/opt/face/about.json}"
FACE_OS_RELEASE="${FACE_OS_RELEASE:-/etc/os-release}"
write_about_json() {
  _pretty=""; _ver=""; _verid=""; _id=""; _code=""
  if [ -r "$FACE_OS_RELEASE" ]; then
    _pretty=$(sed -n 's/^PRETTY_NAME=//p' "$FACE_OS_RELEASE" | head -1 | tr -d '"')
    _ver=$(sed -n 's/^VERSION=//p' "$FACE_OS_RELEASE" | head -1 | tr -d '"')
    _verid=$(sed -n 's/^VERSION_ID=//p' "$FACE_OS_RELEASE" | head -1 | tr -d '"')
    _id=$(sed -n 's/^ID=//p' "$FACE_OS_RELEASE" | head -1 | tr -d '"')
    _code=$(sed -n 's/^VERSION_CODENAME=//p' "$FACE_OS_RELEASE" | head -1 | tr -d '"')
  fi
  [ -n "$_ver" ] || _ver="$_pretty"
  _kernel=$(uname -r 2>/dev/null || echo unknown)
  _session="Meta OS Desktop"
  for _d in /usr/share/xsessions /opt/face; do
    if [ -r "$_d/metaos-face.desktop" ]; then
      _n=$(sed -n 's/^Name=//p' "$_d/metaos-face.desktop" | head -1)
      [ -n "$_n" ] && _session="$_n"
      break
    elif [ -r "$_d/metaos.desktop" ]; then
      _n=$(sed -n 's/^Name=//p' "$_d/metaos.desktop" | head -1)
      [ -n "$_n" ] && _session="$_n"
      break
    fi
  done
  # Build date: when this image's identity was baked (os-release is rewritten
  # by debrand at bake time). Falls back to this script's own mtime
  # (provision copies it at the same bake), then to unknown — never a guess.
  # (Guard with -n, not ||: `stat ... | cut` exits 0 on empty input, so ||
  # would never fire and the date would silently become empty.)
  _build=""
  if [ -r "$FACE_OS_RELEASE" ]; then
    _build=$(stat -c %y "$FACE_OS_RELEASE" 2>/dev/null | cut -d' ' -f1)
  fi
  if [ -z "$_build" ]; then
    _build=$(stat -c %y "$0" 2>/dev/null | cut -d' ' -f1)
  fi
  [ -n "$_build" ] || _build="unknown"
  _now=$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || echo unknown)
  _json_esc() { printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'; }
  if [ -z "$_pretty" ]; then
    _body=$(printf '{"error":"os-release missing or unreadable at %s"}' \
      "$(_json_esc "$FACE_OS_RELEASE")")
  else
    _body=$(printf '{"pretty":"%s","version":"%s","version_id":"%s","id":"%s","codename":"%s","kernel":"%s","session":"%s","build_date":"%s","generated_utc":"%s"}' \
      "$(_json_esc "$_pretty")" "$(_json_esc "$_ver")" "$(_json_esc "$_verid")" \
      "$(_json_esc "$_id")" "$(_json_esc "$_code")" "$(_json_esc "$_kernel")" \
      "$(_json_esc "$_session")" "$(_json_esc "$_build")" "$_now")
  fi
  if [ -w "$(dirname "$ABOUT_JSON")" ] 2>/dev/null; then
    printf '%s\n' "$_body" >"$ABOUT_JSON" 2>/dev/null \
      && say "about.json refreshed" \
      || say "about.json write failed (page will show fallback)"
  elif command -v sudo >/dev/null 2>&1 && sudo -n true 2>/dev/null; then
    printf '%s\n' "$_body" | sudo -n tee "$ABOUT_JSON" >/dev/null 2>&1 \
      && say "about.json refreshed via sudo" \
      || say "about.json sudo write failed (page will show fallback)"
  else
    say "about.json not writable — page will show fallback"
  fi
}
write_about_json >>"$LOG" 2>&1 || say "about.json step failed (page will show fallback)"

# 2b — the spinning Meta wallpaper. A systemd user unit owns the frames; the
# old XDG autostart path is the one that silently did nothing.
systemctl --user start metaos-livebg.service >>"$LOG" 2>&1 \
  || say "livebg unit did not start (wallpaper stays static)"

# 3 — the dock. XDG autostart is not trusted in this image, so plank is
# started here, after a beat so the window manager exists to place it.
if command -v plank >/dev/null 2>&1; then
  (
    sleep 2
    # /etc/xdg/autostart/plank.desktop exists in this image too. If XFCE
    # honoured it, a second plank would mean two docks on screen — so wait
    # for the autostart one and only start plank if nothing did.
    if command -v pgrep >/dev/null 2>&1; then
      _i=0
      while [ "$_i" -lt 10 ]; do
        if pgrep -x plank >/dev/null 2>&1; then
          say "plank already running (autostart won) — not starting a second dock"
          exit 0
        fi
        sleep 0.5
        _i=$((_i + 1))
      done
    fi
    plank >>"$LOG" 2>&1
  ) &
  say "plank dock scheduled (starts only if the autostart entry did not)"
else
  say "plank missing — desktop still works, no dock"
fi

# 4 — kiosk (the web shell) only when explicitly asked for.
if [ "${METAOS_KIOSK:-0}" = "1" ] || [ -e /etc/metaos/kiosk ]; then
  say "kiosk mode requested — starting /opt/face/kiosk.sh"
  if [ -x /opt/face/kiosk.sh ]; then
    ( /opt/face/kiosk.sh >>"$LOG" 2>&1 ) &
  else
    say "kiosk requested but kiosk.sh is missing"
  fi
else
  say "native desktop mode (kiosk off)"
fi

# 5 — one-shot diagnostic: with /etc/metaos/probe present, record which
# loopback ports answer 8s after login. Used to prove the dock's tiles have a
# server under them without needing eyes on the screen.
if [ -e /etc/metaos/probe ]; then
  (
    sleep 8
    for port in 18900 18931 18932 18933 18934 18935 18936 18940; do
      code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 \
             "http://127.0.0.1:$port/" 2>/dev/null)
      echo "$port ${code:-000}"
    done >/tmp/metaos-ports.log 2>&1
  ) &
fi

exec startxfce4

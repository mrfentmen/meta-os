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

# 2b — the spinning Meta wallpaper. A systemd user unit owns the frames; the
# old XDG autostart path is the one that silently did nothing.
systemctl --user start metaos-livebg.service >>"$LOG" 2>&1 \
  || say "livebg unit did not start (wallpaper stays static)"

# 3 — the dock. XDG autostart is not trusted in this image, so plank is
# started here, after a beat so the window manager exists to place it.
if command -v plank >/dev/null 2>&1; then
  ( sleep 2; plank >>"$LOG" 2>&1 ) &
  say "plank dock scheduled"
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

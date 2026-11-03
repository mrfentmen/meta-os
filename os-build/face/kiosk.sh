#!/bin/sh
# Meta OS desktop kiosk — the one thing that turns a login into the Meta desktop.
#
# Order matters and each step is waited for, not slept through:
#   1. the seven backends (face.target)
#   2. the spinning Meta wallpaper (metaos-livebg.service)
#   3. the window manager (xfwm4), because a window cannot go fullscreen
#      before something manages it — this is the bug that left the shell
#      as a small window in the corner
#   4. the shell, fullscreen
#
# Nothing here is allowed to end in a black screen: if the backends never
# answer, XFCE stays as it is and this logs why.
set -u

LOG=/tmp/metaos-kiosk.log
mkdir -p "${HOME}/.local/state/metaos" 2>/dev/null || true
exec >>"$LOG" 2>&1
say() { echo "[$(date -u '+%H:%M:%S')] $*"; }
say "=== kiosk start ==="

SHELL_URL="http://127.0.0.1:18900/login.html"
PROBE="http://127.0.0.1:18900/shell.html"

# 1 — backends
systemctl --user daemon-reload 2>/dev/null || true
systemctl --user start face.target 2>/dev/null || say "face.target start returned non-zero"

i=0
while [ "$i" -lt 40 ]; do
  curl -fs -o /dev/null "$PROBE" 2>/dev/null && break
  i=$((i + 1)); sleep 0.5
done
if [ "$i" -ge 40 ]; then
  say "FALLBACK: face did not answer on 18900 after 20s; staying in XFCE"
  echo "face-unavailable" >"${HOME}/.local/state/metaos/session-fallback"
  exit 1
fi
say "backends up after $i tries"
rm -f "${HOME}/.local/state/metaos/session-fallback"

# 2 — the spinning Meta wallpaper. A unit, not an autostart entry: the
# autostart path is the one that silently did nothing.
if systemctl --user start metaos-livebg.service 2>/dev/null; then
  say "live background started as metaos-livebg.service"
elif [ -x /usr/share/metaos/apps/meta-live.py ]; then
  say "no unit; running meta-live.py directly"
  /usr/share/metaos/apps/meta-live.py >/dev/null 2>&1 &
else
  say "no live background available"
fi

# 3 — window manager must exist before anything can be made fullscreen
j=0
while [ "$j" -lt 40 ]; do
  pgrep -x xfwm4 >/dev/null 2>&1 && break
  j=$((j + 1)); sleep 0.5
done
say "xfwm4 present after $j tries"

# 4 — the shell
export WEBKIT_DISABLE_COMPOSITING_MODE=1
export LIBGL_ALWAYS_SOFTWARE=1

launched=0
for b in epiphany epiphany-browser; do
  if command -v "$b" >/dev/null 2>&1; then
    "$b" --application-mode "$SHELL_URL" >/dev/null 2>&1 &
    say "launched $b on $SHELL_URL"
    launched=1
    break
  fi
done
if [ "$launched" = 0 ]; then
  say "FALLBACK: no WebKit browser installed; leaving XFCE"
  echo "no-browser" >"${HOME}/.local/state/metaos/session-fallback"
  exit 1
fi

# fullscreen, by title, polling until the window exists
k=0
while [ "$k" -lt 15 ]; do
  k=$((k + 1))
  if command -v wmctrl >/dev/null 2>&1; then
    wid=$(wmctrl -l 2>/dev/null | grep -iE 'epiphany|meta os' | head -1 | awk '{print $1}')
    if [ -n "${wid:-}" ]; then
      wmctrl -i -a "$wid" 2>/dev/null || true
      wmctrl -i -r "$wid" -b add,fullscreen 2>/dev/null || true
      say "fullscreen on window $wid after ${k}s"
      break
    fi
  fi
  sleep 1
done
[ "$k" -ge 15 ] && say "WARN: no browser window appeared within 15s"
say "=== kiosk done ==="
exit 0

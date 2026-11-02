#!/bin/sh
# Spike B: real desktop (openbox class) themed to the mocks.
# Xvfb :99 -> openbox -> tint2 taskbar + feh wallpaper + real apps
# as X windows. The face pages run as Chromium app-windows; the
# terminal/files/calculator are the real Linux apps.
# Usage (in guest): DISPLAY=:99 sh /tmp/face/spike-b-session.sh
tint2 &
feh --bg-fill /tmp/face/wallpaper-blue.png &
# real apps, each its own window (proof: taskbar + screendump)
lxterminal &
pcmanfm &
chromium --no-sandbox --app=http://127.0.0.1:18900/dashboard.html &
chromium --no-sandbox --app=http://127.0.0.1:18900/shell.html &
exec openbox-session

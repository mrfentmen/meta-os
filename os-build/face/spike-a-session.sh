#!/bin/sh
# Spike A: kiosk web shell. Xvfb :99 + chromium kiosk on shell.html.
# Backends (launcher on 18931, facts on 18932, files on 18900) must
# already run. Real Linux apps launch behind the browser via
# launcher.py; alt-tab reaches them (proven in the recording).
# Usage (in guest): DISPLAY=:99 sh /tmp/face/spike-a-session.sh
chromium --no-sandbox --kiosk http://127.0.0.1:18900/login.html

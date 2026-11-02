#!/bin/sh
# provision.sh: copy face to /opt/face, install 4 user services, verify.
# Idempotent: safe to re-run. User services persist via enable --now.
set -eu
SRC="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
DST=/opt/face
U="${HOME}/.config/systemd/user"
# 1) stage face content
sudo mkdir -p "$DST"
sudo cp -r "$SRC/." "$DST/"
# keep linger best-effort so user services survive logout/reboot
sudo loginctl enable-linger "$(id -un)" 2>/dev/null || true
# 2) install user units
mkdir -p "$U"
cat > "$U/face-http.service" <<EOF
[Unit]
Description=face static server 18900
After=network.target
[Service]
WorkingDirectory=$DST
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
ExecStart=/usr/bin/python3 $DST/launcher.py
Restart=on-failure
[Install]
WantedBy=default.target
EOF
cat > "$U/face-facts.service" <<EOF
[Unit]
Description=face facts 18932
After=network.target
[Service]
ExecStart=/usr/bin/python3 $DST/facts.py
Restart=on-failure
[Install]
WantedBy=default.target
EOF
cat > "$U/face-ptyd.service" <<EOF
[Unit]
Description=face ptyd 18933
After=network.target
[Service]
ExecStart=/usr/bin/python3 $DST/ptyd.py
Restart=on-failure
[Install]
WantedBy=default.target
EOF
systemctl --user daemon-reload
systemctl --user enable --now face-http.service face-launcher.service face-facts.service face-ptyd.service
# 3) verify (retry ~10s each); any FAIL -> exit 1
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
check "http 18900 /shell.html" curl -fs -o /dev/null http://127.0.0.1:18900/shell.html
check "launcher 18931 /launch" python3 -c "import http.client; c=http.client.HTTPConnection('127.0.0.1',18931,timeout=5); c.request('POST','/launch',body='{}',headers={'Content-Type':'application/json'}); assert b'ok' in c.getresponse().read()"
check "facts 18932 /facts" curl -fs -o /dev/null http://127.0.0.1:18932/facts
check "ptyd 18933 tcp" python3 -c "import socket;socket.create_connection(('127.0.0.1',18933),timeout=5).close()"
# 4) next step
echo "next: start kiosk: chromium --kiosk http://127.0.0.1:18900/shell.html"
exit "$FAIL"

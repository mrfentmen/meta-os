#!/bin/sh
# provision.sh: copy face to /opt/face, stage the repo-root product site
# to /opt/face-site, install 7 user services, verify.
# Idempotent: safe to re-run. User services persist via enable --now.
set -eu
SRC="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
DST=/opt/face
SITE_SRC="$(CDPATH= cd -- "$SRC/../.." && pwd)"
SITE_DST=/opt/face-site
U="${HOME}/.config/systemd/user"
# 0) clear stale manual servers from earlier dev sessions (exact
# binary+arg match so this never matches the provision shell itself)
for pat in "http.server 18900" "http.server 18934" "launcher.py" "facts.py" "ptyd.py" "board.py" "files.py"; do
  pkill -f "python3 .*/$pat" 2>/dev/null || true
done
sleep 1
# 1) stage face content (skip when already running from DST)
if [ "$SRC" != "$DST" ]; then
  sudo mkdir -p "$DST"
  sudo cp -r "$SRC/." "$DST/"
else
  sudo mkdir -p "$DST"
fi
# 1b) stage repo-root product pages for dock iframes (served on 18934
# from $SITE_DST). Boards data only: os/worlds is ~100M, the pages fetch
# just pack.json + officina runs + custos runs. Skipped when re-running
# from $DST (no repo checkout there — metaos-update owns freshness).
if [ -f "$SITE_SRC/index.html" ] && [ -f "$SITE_SRC/js/app.js" ]; then
  sudo mkdir -p "$SITE_DST"
  for f in index.html surfaces.html logo-studio.html bus.html styles.css manifest.webmanifest icon-180.png; do
    if [ -f "$SITE_SRC/$f" ]; then
      sudo cp -f "$SITE_SRC/$f" "$SITE_DST/$f"
    fi
  done
  for d in js vendor design; do
    if [ -d "$SITE_SRC/$d" ]; then
      sudo rm -rf "$SITE_DST/$d"
      sudo cp -r "$SITE_SRC/$d" "$SITE_DST/$d"
    fi
  done
  for lab in molecules music3d; do
    if [ -f "$SITE_SRC/labs/$lab/index.html" ]; then
      sudo rm -rf "$SITE_DST/labs/$lab"
      sudo mkdir -p "$SITE_DST/labs"
      sudo cp -r "$SITE_SRC/labs/$lab" "$SITE_DST/labs/$lab"
    fi
  done
  for pack in "$SITE_SRC"/os/worlds/*/pack.json; do
    if [ -f "$pack" ]; then
      world="$(basename "$(dirname "$pack")")"
      sudo mkdir -p "$SITE_DST/os/worlds/$world"
      sudo cp -f "$pack" "$SITE_DST/os/worlds/$world/pack.json"
    fi
  done
  for wav in "$SITE_SRC"/os/worlds/musica/sessions/hn029-chipsynth/normalized/take-006.wav; do
    if [ -f "$wav" ]; then
      sudo mkdir -p "$SITE_DST/os/worlds/musica/sessions/hn029-chipsynth/normalized"
      sudo cp -f "$wav" "$SITE_DST/os/worlds/musica/sessions/hn029-chipsynth/normalized/"
    fi
  done
  for spec in "officina:json" "custos:jsonl"; do
    world="${spec%%:*}"
    ext="${spec##*:}"
    for run in "$SITE_SRC"/os/worlds/"$world"/runs/*."$ext"; do
      if [ -f "$run" ]; then
        sudo mkdir -p "$SITE_DST/os/worlds/$world/runs"
        sudo cp -f "$run" "$SITE_DST/os/worlds/$world/runs/"
      fi
    done
  done
else
  sudo mkdir -p "$SITE_DST"
  echo "site stage: no repo checkout at $SITE_SRC — leaving $SITE_DST to metaos-update"
fi
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
cat > "$U/face-board.service" <<EOF
[Unit]
Description=face board 18935
After=network.target
[Service]
ExecStart=/usr/bin/python3 $DST/board.py
Restart=on-failure
[Install]
WantedBy=default.target
EOF
cat > "$U/face-files.service" <<EOF
[Unit]
Description=face files 18936
After=network.target
[Service]
ExecStart=/usr/bin/python3 $DST/files.py
Restart=on-failure
[Install]
WantedBy=default.target
EOF
cat > "$U/face-site.service" <<EOF
[Unit]
Description=face product site 18934 (repo-root pages for dock iframes)
After=network.target
[Service]
WorkingDirectory=$SITE_DST
ExecStart=/usr/bin/python3 -m http.server 18934 --bind 127.0.0.1
Restart=on-failure
[Install]
WantedBy=default.target
EOF
systemctl --user daemon-reload
systemctl --user enable --now face-http.service face-site.service face-launcher.service face-facts.service face-ptyd.service face-board.service face-files.service
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
check "site 18934 /index.html" curl -fs -o /dev/null http://127.0.0.1:18934/index.html
check "site 18934 /surfaces.html" curl -fs -o /dev/null http://127.0.0.1:18934/surfaces.html
check "site 18934 /logo-studio.html" curl -fs -o /dev/null http://127.0.0.1:18934/logo-studio.html
check "site 18934 /js/app.js" curl -fs -o /dev/null http://127.0.0.1:18934/js/app.js
check "site 18934 /labs/molecules/index.html" curl -fs -o /dev/null http://127.0.0.1:18934/labs/molecules/index.html
check "site 18934 /take-006.wav" curl -fs -o /dev/null http://127.0.0.1:18934/os/worlds/musica/sessions/hn029-chipsynth/normalized/take-006.wav
check "site 18934 /labs/music3d/index.html" curl -fs -o /dev/null http://127.0.0.1:18934/labs/music3d/index.html
check "site 18934 /manifest.webmanifest" curl -fs -o /dev/null http://127.0.0.1:18934/manifest.webmanifest
check "launcher 18931 /launch" python3 -c "import http.client; c=http.client.HTTPConnection('127.0.0.1',18931,timeout=5); c.request('POST','/launch',body='{}',headers={'Content-Type':'application/json'}); assert b'ok' in c.getresponse().read()"
check "facts 18932 /facts" curl -fs -o /dev/null http://127.0.0.1:18932/facts
check "ptyd 18933 tcp" python3 -c "import socket;socket.create_connection(('127.0.0.1',18933),timeout=5).close()"
check "board 18935 /rooms" curl -fs -o /dev/null http://127.0.0.1:18935/rooms
check "files 18936 /trash" curl -fs -o /dev/null http://127.0.0.1:18936/trash
# 4) next step
echo "next: start kiosk: chromium --kiosk http://127.0.0.1:18900/shell.html"
exit "$FAIL"

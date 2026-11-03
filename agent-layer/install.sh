#!/bin/sh
# OC2 agent-layer installer — idempotent. Safe to re-run; every step guards.
# Usage: sh agent-layer/install.sh
set -u
# Repo root: the directory containing agent-layer/install.sh's parent.
# (Do NOT use `git rev-parse` here — it depends on $PWD, not the script.)
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" >/dev/null 2>&1 && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
ROOT="$(dirname "$ROOT")"
[ -f "$ROOT/agent-layer/install.sh" ] || ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
CONF="$HOME/.config/oc2-agent"
UNITDIR="$HOME/.config/systemd/user"
MARK="# oc2-agent SPARK_API_KEY import (managed by agent-layer/install.sh)"

echo "== OC2 agent layer install (root: $ROOT) =="

# 1. Python present?
command -v python3 >/dev/null || { echo "FAIL: python3 missing"; exit 1; }

# 2. Deps (user site; cv2 optional — evidence.py degrades without it).
# (Needs pip3: `sudo apt-get install -y python3-pip` on minimal images.)
pip3 install --user pillow numpy 2>&1 | tail -n 1

# 3. Env file (non-secrets). Create once; otherwise only refresh OC2_CHECKOUT.
mkdir -p "$CONF"
if [ ! -f "$CONF/env" ]; then
  sed "s|^OC2_CHECKOUT=.*|OC2_CHECKOUT=$ROOT|" "$ROOT/agent-layer/env.example" > "$CONF/env"
  echo "wrote $CONF/env"
else
  if grep -q "^OC2_CHECKOUT=" "$CONF/env"; then
    sed -i '' "s|^OC2_CHECKOUT=.*|OC2_CHECKOUT=$ROOT|" "$CONF/env" 2>/dev/null \
      || sed -i "s|^OC2_CHECKOUT=.*|OC2_CHECKOUT=$ROOT|" "$CONF/env"
  else
    echo "OC2_CHECKOUT=$ROOT" >> "$CONF/env"
  fi
  echo "kept $CONF/env (checkout refreshed)"
fi
grep -i -E "SPARK_API_KEY|sk-|BEGIN PRIVATE" "$CONF/env" \
  && { echo "FAIL: secret-looking value in env file"; exit 1; }
echo "env file clean (no secrets)"

# 4. Units.
mkdir -p "$UNITDIR"
for u in oc2-queue.service oc2-patrol.service oc2-patrol.timer; do
  cp "$ROOT/agent-layer/units/$u" "$UNITDIR/$u"
done
echo "units linked"

# 5. Reload + enable (linger attempted; recorded if unavailable).
systemctl --user daemon-reload 2>&1 | head -n 1
systemctl --user enable oc2-queue.service oc2-patrol.service oc2-patrol.timer 2>&1 | head -n 3
loginctl enable-linger "$USER" 2>&1 | head -n 1 || echo "linger unavailable (recorded)"

# 6. Key handoff hook (marker-guarded, runs at login shell start).
for rc in "$HOME/.profile" "$HOME/.zprofile"; do
  [ -f "$rc" ] || continue
  if ! grep -q "oc2-agent SPARK_API_KEY import" "$rc" 2>/dev/null; then
    printf '\n%s\n[ -n "$SPARK_API_KEY" ] && systemctl --user import-environment SPARK_API_KEY 2>/dev/null || true\n' "$MARK" >> "$rc"
    echo "hook added to $rc"
  else
    echo "hook already in $rc"
  fi
done

# 7. Preflight: services compile, port free, guardrail sane.
python3 -m py_compile "$ROOT/server/queue/patrol.py" "$ROOT/server/queue/queue_service.py" \
  "$ROOT/server/queue/crew.py" "$ROOT/server/queue/livecams.py" && echo "services compile"
(python3 -c "import socket; s=socket.socket(); s.bind(('127.0.0.1', 8935)); s.close(); print('port 8935 free')") \
  2>/dev/null || echo "port 8935 busy (queue already running?)"
echo "== done: log out and back in (or reboot); check: systemctl --user status oc2-queue oc2-patrol =="

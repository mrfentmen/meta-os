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

# 2. Deps. Debian/Ubuntu target: nodejs (queue hard-requires node for
# js/products.js — no fallback in trio_repo), PIL + numpy (evidence.py
# uses them lazily; cv2 stays optional). No-ops where apt is absent (macOS dev).
if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get install -y nodejs python3-pil python3-numpy 2>&1 | tail -n 1 \
    || echo "apt install failed or needs a password — recorded, not fatal"
fi
# Python-site fallback (pipx-style user install where apt lacks the package).
pip3 install --user pillow numpy 2>&1 | tail -n 1 || true

# 3. Env file (non-secrets). Create once; otherwise only refresh OC2_CHECKOUT.
mkdir -p "$CONF"
if [ ! -f "$CONF/env" ]; then
  sed "s|^OC2_CHECKOUT=.*|OC2_CHECKOUT=$ROOT|" "$ROOT/agent-layer/env.example" > "$CONF/env"
  echo "wrote $CONF/env"
else
  # File exists: refresh checkout path AND backfill any missing defaults
  # (keep user-set values; first botched runs may have left a bare file).
  if grep -q "^OC2_CHECKOUT=" "$CONF/env"; then
    sed -i '' "s|^OC2_CHECKOUT=.*|OC2_CHECKOUT=$ROOT|" "$CONF/env" 2>/dev/null \
      || sed -i "s|^OC2_CHECKOUT=.*|OC2_CHECKOUT=$ROOT|" "$CONF/env"
  else
    echo "OC2_CHECKOUT=$ROOT" >> "$CONF/env"
  fi
  while IFS='=' read -r key val; do
    case "$key" in \#*|"") continue;; esac
    grep -q "^${key}=" "$CONF/env" || echo "${key}=${val}" >> "$CONF/env"
  done < "$ROOT/agent-layer/env.example"
  echo "kept $CONF/env (checkout refreshed, defaults backfilled)"
fi
grep -i -E "SPARK_API_KEY|sk-|BEGIN PRIVATE" "$CONF/env" \
  && { echo "FAIL: secret-looking value in env file"; exit 1; }
echo "env file clean (no secrets)"

# 4. Units (everything shipped in agent-layer/units/, no hardcoded list —
# a new unit must never require an installer edit to deploy).
mkdir -p "$UNITDIR"
for path in "$ROOT/agent-layer/units/"*.service "$ROOT/agent-layer/units/"*.timer; do
  [ -e "$path" ] || continue
  cp "$path" "$UNITDIR/$(basename "$path")"
done
echo "units linked: $(ls "$ROOT/agent-layer/units" | tr '\n' ' ')"

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

#!/usr/bin/env bash
# meta-agent-login.sh — bring the agent layer up for this session.
#
# Runs from /etc/xdg/autostart, so a failure here must not block the desktop.
# It seeds the per-user env if the account predates the image, imports a key
# if one is already in the environment (never writes it), then starts the
# three units the stager enabled.
#
#   meta-agent-login.sh [--dry-run]
#
# Exit 0 when everything started, 1 when a unit did not. The desktop ignores
# that code; the log line is the point.
set -uo pipefail

DRY=0
[ "${1:-}" = "--dry-run" ] && DRY=1

CONF="${XDG_CONFIG_HOME:-$HOME/.config}/oc2-agent"
SHARE="${METAOS_AGENT_SHARE:-/usr/share/metaos/agent}"
UNITS=(oc2-queue.service oc2-trio.service oc2-patrol.timer)
rc=0

if [ ! -f "$CONF/env" ] && [ -f "$SHARE/env" ]; then
  if [ "$DRY" = "1" ]; then
    echo "would seed  $CONF/env"
  else
    mkdir -p "$CONF" && cp "$SHARE/env" "$CONF/env" \
      || { echo "agent-login: could not seed $CONF/env" >&2; rc=1; }
  fi
fi

if [ -n "${SPARK_API_KEY:-}" ]; then
  if [ "$DRY" = "1" ]; then
    echo "would import  SPARK_API_KEY into the user manager"
  else
    systemctl --user import-environment SPARK_API_KEY 2>/dev/null \
      || echo "agent-login: key present but not imported" >&2
  fi
fi

if ! command -v systemctl >/dev/null 2>&1; then
  echo "agent-login: systemctl not found, nothing to start"
  exit 0
fi

if [ "$DRY" = "1" ]; then
  echo "would start  ${UNITS[*]}"
  exit 0
fi

systemctl --user daemon-reload >/dev/null 2>&1 || true
for unit in "${UNITS[@]}"; do
  if systemctl --user start "$unit" 2>/dev/null; then
    echo "agent-login: started $unit"
  else
    echo "agent-login: $unit did not start" >&2
    rc=1
  fi
done
exit "$rc"

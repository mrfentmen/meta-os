#!/usr/bin/env bash
# run-stack.sh — start the full Meta Trio demo stack in one command.
#
#   1. Meta Nuntius relay        node relay/relay.mjs            (RELAY_PORT, default 8787)
#   2. OS queue service          server/queue/queue_service.py   (port 8935)
#   3. Resident queue agent      server/queue/trio_agent.py      (TRIO_RELAY_URL -> relay)
#   4. Trio app server           node server/server.mjs          (PORT, default 8080,
#                                  queue path on: TRIO_QUEUE_ENABLED=1,
#                                  TRIO_QUEUE_URL -> queue service)
#
# Env names and ports are the ones documented in relay/README.md,
# server/queue/README.md, and server/README.md. Ctrl-C (or any exit)
# stops all four processes via the trap below.
#
# Generation transport: if SPARK_API_KEY is already in the environment
# the agent uses the production direct transport. Otherwise the stack
# falls back to the DEV helper transport (TRIO_SPARK_VIA_HELPER=1) and
# says so loudly. TRIO_JOB_NS, if exported before running this script,
# is inherited by the queue service and the agent (proofs use a
# scratch namespace; the default is "trio").

set -euo pipefail
cd "$(dirname "$0")"

RELAY_PORT="${RELAY_PORT:-8787}"
QUEUE_PORT="${QUEUE_PORT:-8935}"
APP_PORT="${PORT:-8080}"
RELAY_BASE="http://127.0.0.1:${RELAY_PORT}"
QUEUE_BASE="http://127.0.0.1:${QUEUE_PORT}"
APP_BASE="http://127.0.0.1:${APP_PORT}"

if [ -n "${SPARK_API_KEY:-}" ]; then
  unset TRIO_SPARK_VIA_HELPER
  echo "Generation transport: production direct (SPARK_API_KEY present)."
else
  export TRIO_SPARK_VIA_HELPER=1
  echo "WARNING: SPARK_API_KEY is not set — using the DEV helper transport"
  echo "         (TRIO_SPARK_VIA_HELPER=1). Sandbox/development only; the"
  echo "         production run sets SPARK_API_KEY in the environment."
fi

PIDS=()
cleanup() {
  for pid in "${PIDS[@]:-}"; do
    [ -n "$pid" ] && kill "$pid" 2>/dev/null || true
  done
}
trap cleanup EXIT INT TERM

wait_http() { # url, label
  local url="$1" label="$2" i
  for i in $(seq 1 50); do
    if curl -sf -m 2 "$url" >/dev/null 2>&1; then
      echo "up: $label"
      return 0
    fi
    sleep 0.2
  done
  echo "FAILED to come up: $label ($url)" >&2
  return 1
}

echo "Starting Meta Nuntius relay on ${RELAY_BASE} ..."
RELAY_PORT="$RELAY_PORT" node relay/relay.mjs &
PIDS+=($!)
wait_http "${RELAY_BASE}/health" "Meta Nuntius relay"

echo "Starting queue service on ${QUEUE_BASE} ..."
(cd server/queue && python3 queue_service.py --port "$QUEUE_PORT") &
PIDS+=($!)
wait_http "${QUEUE_BASE}/health" "queue service"

echo "Starting resident agent (TRIO_RELAY_URL=${RELAY_BASE}) ..."
(cd server/queue && TRIO_RELAY_URL="$RELAY_BASE" python3 trio_agent.py) &
PIDS+=($!)
sleep 1
kill -0 "${PIDS[-1]}" 2>/dev/null || { echo "FAILED: resident agent exited" >&2; exit 1; }
echo "up: resident agent"

echo "Starting Trio app server on ${APP_BASE} (queue path on) ..."
PORT="$APP_PORT" TRIO_QUEUE_ENABLED=1 TRIO_QUEUE_URL="$QUEUE_BASE" \
  node server/server.mjs &
PIDS+=($!)
wait_http "${APP_BASE}/api/health" "Trio app server"

echo
echo "Meta Trio stack is up:"
echo "  Meta Nuntius viewer   ${RELAY_BASE}/"
echo "  Queue service         ${QUEUE_BASE}/health"
echo "  Resident agent        running (NOTIFY -> ${RELAY_BASE}/rooms/main)"
echo "  Web console + API     ${APP_BASE}/  (POST ${APP_BASE}/api/assess)"
echo
echo "Ctrl-C stops the whole stack."
wait

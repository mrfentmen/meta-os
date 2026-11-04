#!/usr/bin/env bash
# run-stack.sh — start the full Meta Trio demo stack in one command.
#
#   1. Board (the one messaging app) node board/board.mjs        (BOARD_PORT, default 18935)
#   2. OS queue service          server/queue/queue_service.py   (port 8935)
#   3. Resident queue agent      server/queue/trio_agent.py      (TRIO_RELAY_URL -> board)
#   4. Trio app server           node server/server.mjs          (PORT, default 8080,
#                                  queue path on: TRIO_QUEUE_ENABLED=1,
#                                  TRIO_QUEUE_URL -> queue service)
#
# Env names and ports are the ones documented in board/ (README in
# server/queue/README.md), and server/README.md. Ctrl-C (or any exit)
# stops all four processes via the trap below.
#
# Generation transport: if SPARK_API_KEY is already in the environment
# the agent uses the production direct transport (the documented
# production path). The DEV helper transport is NEVER auto-selected:
# it is used only when TRIO_SPARK_VIA_HELPER=1 was exported by hand,
# because the helper lives outside this repository. With no key and
# no explicit helper opt-in, the stack still starts, in a clearly
# labelled NOT CONFIGURED / offline mode: board, queue, and UI run,
# but generation is honestly unavailable (assessments fail as
# not_configured) until SPARK_API_KEY is set. TRIO_JOB_NS, if
# exported before running this script, is inherited by the queue
# service and the agent (proofs use a scratch namespace; the default
# is "trio").

set -euo pipefail
cd "$(dirname "$0")"

# 18935, not 8787: the pages' desk chat (js/site-chat.js) and the dock's
# Messages tile both default to 18935, so starting the board anywhere else made
# every room box say "Board unreachable on 18935" while the board was running.
BOARD_PORT="${BOARD_PORT:-18935}"
RELAY_PORT="$BOARD_PORT"  # the board speaks the same notify line the agent posts
QUEUE_PORT="${QUEUE_PORT:-8935}"
APP_PORT="${PORT:-8080}"
RELAY_BASE="http://127.0.0.1:${RELAY_PORT}"
QUEUE_BASE="http://127.0.0.1:${QUEUE_PORT}"
APP_BASE="http://127.0.0.1:${APP_PORT}"

# A key can be handed in as a file (METAOS_KEY_FILE=/path/to/key) so the demo
# command never carries the secret in shell history. The key is read here and
# exported; it is never written into the tree.
if [ -z "${SPARK_API_KEY:-}" ] && [ -n "${METAOS_KEY_FILE:-}" ]; then
  if [ -r "$METAOS_KEY_FILE" ]; then
    SPARK_API_KEY=$(tr -d '\r\n' < "$METAOS_KEY_FILE")
    export SPARK_API_KEY
    echo "Generation transport: key read from $METAOS_KEY_FILE."
  else
    echo "WARNING: METAOS_KEY_FILE=$METAOS_KEY_FILE is not readable." >&2
  fi
fi

if [ -n "${SPARK_API_KEY:-}" ]; then
  unset TRIO_SPARK_VIA_HELPER
  # The in-app chat (/api/agent/ask) and the assessments both sit behind this
  # gate. Opening it here is what makes the chat boxes answer instead of
  # reporting "calls held" on every page.
  export ASSESS_LIVE_MODEL=1
  echo "Generation transport: production direct (SPARK_API_KEY present, live calls open)."
elif [ "${TRIO_SPARK_VIA_HELPER:-}" = "1" ]; then
  echo "Generation transport: DEV helper (TRIO_SPARK_VIA_HELPER=1 was set"
  echo "         explicitly). Dev-only opt-in; the helper lives outside"
  echo "         this repository and is not part of a standalone run."
else
  echo "WARNING: SPARK_API_KEY is not set — generation is NOT CONFIGURED."
  echo "         Starting in offline mode: board, queue, and UI run, but"
  echo "         assessments are unavailable until SPARK_API_KEY is set"
  echo "         in the environment (the production direct path)."
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

echo "Starting the Board on ${RELAY_BASE} ..."
BOARD_PORT="$BOARD_PORT" node board/board.mjs &
PIDS+=($!)
wait_http "${RELAY_BASE}/health" "Board"

echo "Starting queue service on ${QUEUE_BASE} ..."
(cd server/queue && python3 queue_service.py --port "$QUEUE_PORT") &
PIDS+=($!)
wait_http "${QUEUE_BASE}/health" "queue service"

echo "Starting resident agent (TRIO_RELAY_URL=${RELAY_BASE}) ..."
(cd server/queue && TRIO_RELAY_URL="$RELAY_BASE" python3 trio_agent.py) &
PIDS+=($!)
sleep 1
kill -0 "${PIDS[$((${#PIDS[@]}-1))]}" 2>/dev/null || { echo "FAILED: resident agent exited" >&2; exit 1; }
echo "up: resident agent"

echo "Starting Trio app server on ${APP_BASE} (queue path on) ..."
PORT="$APP_PORT" TRIO_QUEUE_ENABLED=1 TRIO_QUEUE_URL="$QUEUE_BASE" \
  node server/server.mjs &
PIDS+=($!)
wait_http "${APP_BASE}/api/health" "Trio app server"

echo
echo "Meta Trio stack is up:"
echo "  Messages (the Board)  ${RELAY_BASE}/"
echo "  Queue service         ${QUEUE_BASE}/health"
echo "  Resident agent        running (NOTIFY -> ${RELAY_BASE}/rooms/main)"
echo "  Web console + API     ${APP_BASE}/  (POST ${APP_BASE}/api/assess, POST ${APP_BASE}/api/agent/ask)"
echo
echo "Ctrl-C stops the whole stack."
wait

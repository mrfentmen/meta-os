#!/bin/sh
# oc2 watchdog — supervise one service, restart with cause logging, cap to BLOCKED.
# Usage: sh agent-layer/watchdog.sh NAME START_SH HEALTH_SH MAX_RESTARTS INTERVAL LOGDIR
#   NAME          service name (e.g. oc2-queue)
#   START_SH      shell snippet that starts the service in FOREGROUND
#                 (watchdog backgrounds it and tracks the pid)
#   HEALTH_SH     shell snippet; exit 0 = healthy. Empty string = liveness only.
#   MAX_RESTARTS  restarts allowed; the next failure writes NAME.blocked and exits 2
#   INTERVAL      seconds between checks (integer)
#   LOGDIR        restart log + state dir (NAME.log, NAME.restarts, NAME.blocked)
# Exit 0: supervised run ended because the service exited 0 itself (no failure).
# Exit 1: bad usage. Exit 2: restart cap reached (NAME.blocked written, cause logged).
# Never requires systemd: pid tracked via $! + kill -0, portable sh.
set -u
NAME="${1:?name}"; START_SH="${2:?start}"; HEALTH_SH="${3:-}"
MAX_RESTARTS="${4:?max}"; INTERVAL="${5:?interval}"; LOGDIR="${6:?logdir}"
mkdir -p "$LOGDIR"
LOG="$LOGDIR/$NAME.log"
COUNT_FILE="$LOGDIR/$NAME.restarts"
BLOCKED="$LOGDIR/$NAME.blocked"
RESTARTS=0
[ -f "$COUNT_FILE" ] && RESTARTS=$(cat "$COUNT_FILE" 2>/dev/null || echo 0)
log() { echo "$(date -u '+%Y-%m-%dT%H:%M:%SZ') $NAME $1" >> "$LOG"; }
die_blocked() {
  cause="$1"
  echo "$cause" > "$BLOCKED"
  echo "$RESTARTS" > "$COUNT_FILE"
  log "BLOCKED cause=$cause restarts=$RESTARTS (cap $MAX_RESTARTS)"
  exit 2
}
log "watchdog start max=$MAX_RESTARTS interval=${INTERVAL}s restarts-carried=$RESTARTS"
sh -c "$START_SH" >> "$LOG" 2>&1 &
PID=$!
log "started pid=$PID"
while :; do
  sleep "$INTERVAL"
  if ! kill -0 "$PID" 2>/dev/null; then
    wait "$PID" 2>/dev/null; CODE=$?
    if [ "$CODE" = "0" ]; then
      log "service exited 0 (clean, no restart)"
      echo "$RESTARTS" > "$COUNT_FILE"
      exit 0
    fi
    RESTARTS=$((RESTARTS + 1))
    echo "$RESTARTS" > "$COUNT_FILE"
    if [ "$RESTARTS" -gt "$MAX_RESTARTS" ]; then
      kill "$PID" 2>/dev/null || true
      die_blocked "dead-exit-$CODE"
    fi
    log "restart #$RESTARTS cause=dead-exit-$CODE"
    sh -c "$START_SH" >> "$LOG" 2>&1 &
    PID=$!
    log "started pid=$PID"
    continue
  fi
  if [ -n "$HEALTH_SH" ]; then
    if ! sh -c "$HEALTH_SH" >/dev/null 2>&1; then
      RESTARTS=$((RESTARTS + 1))
      echo "$RESTARTS" > "$COUNT_FILE"
      if [ "$RESTARTS" -gt "$MAX_RESTARTS" ]; then
        kill "$PID" 2>/dev/null || true
        die_blocked "hung-health-fail"
      fi
      log "restart #$RESTARTS cause=hung-health-fail (pid $PID killed)"
      kill "$PID" 2>/dev/null || true
      wait "$PID" 2>/dev/null || true
      sh -c "$START_SH" >> "$LOG" 2>&1 &
      PID=$!
      log "started pid=$PID"
    fi
  fi
done

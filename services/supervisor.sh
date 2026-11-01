#!/bin/sh
# supervisor.sh (OS-157/160): run a Goose service, log start/stop/crash
# to records.log, restart on crash. Usage:
#   supervisor.sh <name> <service-dir> [--once]
# --once: run until clean stop, do not restart (for drills).
set -eu
NAME="$1"; DIR="$2"; ONCE="${3:-}"
GOOSE=/Users/test/mcp-servers/toolchains/goose-src/build/goose
cd "$DIR"
log() { printf '%s %s %s\n' "$(date -u +%FT%TZ)" "$NAME" "$*" >> records.log; }
log "supervisor-start"
while true; do
  log "service-start"
  if "$GOOSE" run "$NAME.goose" >> service.out 2>&1; then
    rc=0
  else
    rc=$?
  fi
  log "service-stop rc=$rc"
  if [ -n "$ONCE" ]; then exit "$rc"; fi
  if [ -f STOP ]; then log "ordered-stop"; exit 0; fi
  log "restart-in-2s"
  sleep 2
done

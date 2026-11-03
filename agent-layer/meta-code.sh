#!/bin/sh
# meta-code — hand a coding task to the Meta agent, from a Meta OS terminal.
#
# The relay is for scheduled work; this is for a person with one job right now.
# It does not invent a second runtime: it runs the same agents/agent_loop.mjs
# that the board runs, in a fresh run directory under ~/Meta/agent-runs, with
# the key from /etc/metaos/agent.env (never from a file this script writes).
#
#   meta-code "rename old_func in lib.py and prove the tests pass"
#   meta-code --ls                     # previous runs, newest last
#   meta-code --max-actions 6 "make me a README"
#
# Exit: the agent's exit (0 finished, 2 action cap, 3 model error, 4 no key).
set -eu

PAYLOAD=/usr/share/metaos/agent
LOOP="$PAYLOAD/agents/agent_loop.mjs"
NODE=/usr/bin/node
MACHINE_ENV=/etc/metaos/agent.env
MAX_ACTIONS="${METAOS_MAX_ACTIONS:-14}"

usage() {
  sed -n '2,14p' "$0"
}

if [ "${1:-}" = "--ls" ]; then
  base="${METAOS_RUNS:-$HOME/Meta/agent-runs}"
  [ -d "$base" ] || { echo "meta-code: no runs yet in $base"; exit 0; }
  for d in "$base"/*; do
    [ -d "$d" ] || continue
    r="$d/agent-result.json"
    if [ -f "$r" ]; then
      line=$(python3 - "$r" <<'PY'
import json, sys
try:
    d = json.load(open(sys.argv[1]))
except Exception:
    print("unreadable", end="")
    raise SystemExit(0)
print(("ok" if d.get("ok") else "stopped:" + str(d.get("stopped"))) +
      " steps=%d $" % len(d.get("steps") or []) + "%.4f" % (d.get("usage", {}).get("usd") or 0), end="")
PY
)
    else
      line="(no result yet)"
    fi
    echo "$(basename "$d")  $line"
  done
  exit 0
fi

[ -f "$LOOP" ] || { echo "meta-code: $LOOP is missing; run agent-layer/stage.sh" >&2; exit 1; }
if [ "${1:-}" = "--max-actions" ]; then
  MAX_ACTIONS="${2:-14}"
  shift 2
fi
TASK="${1:-}"
if [ -z "$TASK" ]; then usage; exit 2; fi

if [ -r "$MACHINE_ENV" ]; then
  # shellcheck disable=SC1090
  set -a; . "$MACHINE_ENV"; set +a
fi
if [ -z "${SPARK_API_KEY:-}" ]; then
  echo "meta-code: SPARK_API_KEY is empty. It lives in $MACHINE_ENV (root 0600);" >&2
  echo "           fill it once with os-build/tools/set_spark_key.sh, then log in again." >&2
  exit 4
fi

SLUG=$(printf '%s' "$TASK" | tr -cs 'a-zA-Z0-9' '-' | cut -c1-40 | sed 's/-*$//')
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
RUN="${METAOS_RUNS:-$HOME/Meta/agent-runs}/$STAMP-$SLUG"
mkdir -p "$RUN/workspace"
printf '%s\n' "$TASK" > "$RUN/orders.txt"

echo "meta-code: run $RUN"
echo "meta-code: orders: $(printf '%s' "$TASK" | cut -c1-120)"
echo "meta-code: the agent writes its transcript to $RUN/transcript.jsonl"

set +e
( cd "$RUN" && "$NODE" "$LOOP" --workspace "$RUN/workspace" \
    --transcript "$RUN/transcript.jsonl" --max-actions "$MAX_ACTIONS" --task "$TASK" )
rc=$?
set -e
echo "meta-code: files in $RUN/workspace:"
ls -1 "$RUN/workspace" | sed 's/^/  /' | head -20
echo "meta-code: result $RUN/agent-result.json (exit $rc)"
exit "$rc"

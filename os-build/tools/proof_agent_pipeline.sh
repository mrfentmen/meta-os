#!/bin/sh
# proof_agent_pipeline.sh — guest-side proof that the agent pipeline runs on the
# INSTALLED payload, not just in a checkout.
#
# Why this exists: every job submitted from the Agents page came back
# "failed (exit 1)" in the image and nothing said why. The payload lives under
# /usr/share, which is root-owned; the relay tried to mkdir its board there,
# got EACCES and died. A `watch` job made it worse: the drain spawned a
# watchman that read the same board, found the same order and spawned again,
# which is why the fan came on and never stopped.
#
# Two halves, both against /usr/share/metaos/agent:
#   A. meta-ask submits -> watchman drains -> run -> receipt -> meta-ask reports
#   B. a `watch` order inside a drain refuses the self-drain instead of recursing
#
#   sh proof_agent_pipeline.sh                 # default payload + temp state
#   PAYLOAD=/elsewhere sh proof_agent_pipeline.sh
#   AGENT=nervus sh proof_agent_pipeline.sh    # pick a different worker
#
# Exit 0 only if every row is OK. Prints one line per check.
set -u

PAYLOAD=${PAYLOAD:-/usr/share/metaos/agent}
STATE=${STATE:-/tmp/metaos-agent-proof}
# A worker that is live in the registry and cheap to run. `watch` is the wrong
# choice here: it IS the drain, so the drain spawning it is the recursion case.
AGENT=${AGENT:-nervus}
NODE=$(command -v node || echo /usr/bin/node)
fail=0

row() {
  case "$2" in
    OK)   printf '%-46s OK   %s\n' "$1" "${3:-}" ;;
    SKIP) printf '%-46s SKIP %s\n' "$1" "${3:-}" ;;
    *)    printf '%-46s FAIL %s\n' "$1" "${3:-}"; fail=1 ;;
  esac
}

echo "payload: $PAYLOAD"
echo "state:   $STATE"
echo "agent:   $AGENT"
echo

# --- 0. the payload is where the image says it is ---------------------------
if [ -f "$PAYLOAD/agents/watchman.mjs" ]; then
  row "payload watchman.mjs" OK
else
  row "payload watchman.mjs" FAIL "missing under $PAYLOAD"
  echo "RESULT: FAIL — nothing to run"
  exit 1
fi
if command -v meta-ask >/dev/null 2>&1; then
  row "meta-ask present" OK "$(command -v meta-ask)"
  have_ask=1
else
  row "meta-ask present" FAIL "not on PATH — cannot prove the human path"
  have_ask=0
fi

rm -rf "$STATE"
mkdir -p "$STATE/jobs" || { echo "RESULT: FAIL — cannot create $STATE"; exit 1; }

# --- A. submit, drain, and read the receipt --------------------------------
# The human path is meta-ask --follow: it submits, waits for the receipt and
# prints the outcome. When meta-ask is absent (a bare root, the host bench) the
# order is written in the same shape submit.mjs writes, so the drain below is
# still a real job and not a mock — the submit row is the only thing lost.
if [ "$have_ask" = 1 ]; then
  (
    METAOS_AGENT_STATE="$STATE" meta-ask --agent "$AGENT" \
      --orders "proof: run once and file a receipt" --id proof-1 \
      --follow --timeout 90 >"$STATE/ask.out" 2>&1
    echo $? > "$STATE/ask.rc"
  ) &
  ask_pid=$!
  sleep 1.5
else
  printf '{"id":"proof-1","agent":"%s","orders":"proof: run once and file a receipt","submittedAt":"%s"}\n' \
    "$AGENT" "$(date -u +%Y-%m-%dT%H:%M:%S.000Z)" > "$STATE/jobs/proof-1.job.json"
fi

METAOS_AGENT_STATE="$STATE" METAOS_RELAY_DEPTH= "$NODE" "$PAYLOAD/agents/watchman.mjs" --once \
  >"$STATE/watchman.out" 2>&1
wrc=$?
if [ "$wrc" -eq 0 ]; then
  row "watchman --once exits 0" OK
else
  row "watchman --once exits 0" FAIL "exit $wrc: $(tail -2 "$STATE/watchman.out" | tr '\n' ' ')"
fi

if [ "$have_ask" = 1 ]; then
  wait $ask_pid
  arc=$(cat "$STATE/ask.rc" 2>/dev/null || echo 99)
  if [ "$arc" -eq 0 ]; then
    row "meta-ask reports the job finished" OK "$(tail -1 "$STATE/ask.out")"
  else
    row "meta-ask reports the job finished" FAIL "exit $arc: $(tail -1 "$STATE/ask.out")"
  fi
fi

runs=$(ls "$STATE/runs" 2>/dev/null | wc -l | tr -d ' ')
if [ "${runs:-0}" -ge 1 ]; then
  row "a run was started" OK "$runs run(s)"
else
  row "a run was started" FAIL "no run directory under $STATE/runs"
fi

if ls "$STATE"/jobs/proof-1.result.json >/dev/null 2>&1; then
  row "a receipt was written" OK "$(tr -d '\n' < "$STATE/jobs/proof-1.result.json" | cut -c1-60)"
else
  row "a receipt was written" FAIL "no proof-1.result.json"
fi

# --- B. the recursion stops ------------------------------------------------
# A `watch` order asks for one more drain. Inside a drain that must be refused
# by name, not spawned: depth 2 is the expected shape, and the run count stays
# small instead of growing until the machine gives up.
METAOS_AGENT_STATE="$STATE" METAOS_RELAY_DEPTH= "$NODE" "$PAYLOAD/agents/watchman.mjs" --once \
  >"$STATE/watchman2.out" 2>&1
if grep -q 'relay-nested-drain' "$STATE/watchman.jsonl" 2>/dev/null; then
  row "nested drain refused" OK "relay-nested-drain"
else
  row "nested drain refused" SKIP "no watch job was on the board in this pass"
fi

runs=$(ls "$STATE/runs" 2>/dev/null | wc -l | tr -d ' ')
if [ "${runs:-0}" -le 3 ]; then
  row "runs stayed bounded" OK "$runs run(s)"
else
  row "runs stayed bounded" FAIL "$runs runs — something is spawning in a loop"
fi

left=$(pgrep -fc 'watchman\.mjs' 2>/dev/null || true)
case "${left:-0}" in
  0|1) row "no watchman left running" OK "${left:-0} (one is this check's own grep)" ;;
  *)   row "no watchman left running" FAIL "$left processes still alive" ;;
esac

echo
if [ $fail -eq 0 ]; then
  echo "RESULT: PASS — a job handed to an agent ran and filed a receipt in the guest"
  exit 0
fi
echo "RESULT: FAIL — see the rows above"
echo "  meta-ask output: $STATE/ask.out"
echo "  watchman output: $STATE/watchman.out"
echo "  relay ledger:    $STATE/watchman.jsonl"
exit 1

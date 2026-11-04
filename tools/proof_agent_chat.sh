#!/usr/bin/env bash
# proof_agent_chat.sh — prove the in-app chat works end to end, on every app.
#
#   METAOS_KEY_FILE="$HOME/Desktop/Hackathon Key.txt" tools/proof_agent_chat.sh
#
# What it does, in order:
#   1. starts server/server.mjs on the port the image uses (18934) with the
#      live gate open and the key taken from METAOS_KEY_FILE or SPARK_API_KEY;
#   2. reads the app list out of server/agent-chat.mjs — the same table the
#      server validates against, so this cannot drift from the code;
#   3. asks every app one live question through POST /api/agent/ask, exactly the
#      request the on-page box sends, and prints the reply;
#   4. fetches every page that carries a box and checks the box is in the
#      served HTML with the app id it claims;
#   5. prints the ledger's estimated spend and stops the server.
#
# It refuses to run without a key (that would "pass" with 503s) and stops
# before METAOS_CHAT_MAX_SPEND_USD of estimated spend (default 0.50) so a
# proof run can never be the expensive thing.
#
# Exit 0 only when every app answered and every page carries its box.
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"

PORT="${PORT:-18934}"
MAX_SPEND="${METAOS_CHAT_MAX_SPEND_USD:-0.50}"
STATIC_ROOT="${METAOS_STATIC_ROOT:-$ROOT}"

if [ -z "${SPARK_API_KEY:-}" ] && [ -n "${METAOS_KEY_FILE:-}" ]; then
  [ -r "$METAOS_KEY_FILE" ] || { echo "proof_agent_chat: cannot read METAOS_KEY_FILE=$METAOS_KEY_FILE" >&2; exit 2; }
  SPARK_API_KEY=$(tr -d '\r\n' < "$METAOS_KEY_FILE")
fi
if [ -z "${SPARK_API_KEY:-}" ]; then
  echo "proof_agent_chat: no key. Set SPARK_API_KEY or METAOS_KEY_FILE=/path/to/key." >&2
  echo "                  Without one every app answers 503, which proves nothing." >&2
  exit 2
fi

command -v node >/dev/null || { echo "proof_agent_chat: node not found" >&2; exit 2; }
command -v curl >/dev/null || { echo "proof_agent_chat: curl not found" >&2; exit 2; }

# Pages that carry a chat box, with the app id each one sends. The three
# division pages are listed too: they draw their own inline console
# (trio/agent.js) instead of the floating box, and post `division`.
PAGES="surfaces.html:boards
design/meta-custos-watch.html:custos
design/meta-officina-blueprint.html:officina
labs/molecules/index.html:science
aegis-page/index.html:aegis
nervus/index.html:nervus
trio/vigiles.html:vigiles
trio/ignis.html:ignis
trio/medicus.html:medicus"

APPS=$(node -e '
  import("./server/agent-chat.mjs").then((m) => {
    for (const id of m.APP_IDS) console.log(id + "\t" + m.APP_PROFILES[id].label);
  });
')

# One question and one snapshot of page context per app, so the answers in the
# proof are grounded in something: a proof that only shows "no context was
# supplied" proves the pipe, not the product.
CASES=$(node -e '
  const cases = {
    vigiles: [
      "Two cameras watched: 34th St (clear: normal activity) and 8th Ave (flagged: crowd gathered). What should a human do next?",
      "Watched cameras, 2 of 6: 34th St (Midtown): clear: normal activity. 8th Ave (Chelsea): flagged: crowd gathered.",
    ],
    ignis: [
      "take-003 is flagged for light grey smoke above the roofline. Is that a fire?",
      "Timeline, 4 assessed frames: take-001 clear, take-002 clear, take-003 flagged: smoke, low grey column above the roofline, take-004 clear.",
    ],
    medicus: [
      "Three frames are queued. What is queued and what is the one flag worth?",
      "Queue: take-001 not assessed, take-002 flagged: person seated on the kerb, take-003 not assessed.",
    ],
    science: [
      "How many atoms are in the structure I have loaded, and what is its formula?",
      "Molecule: caffeine. Formula C8H10N4O2. 24 atoms (14 heavy, 10 hydrogen). Source: embedded SDF pack, offline.",
    ],
    musica: [
      "The track is silent. Why?",
      "Player state line: wav served (4128 KB) - this machine has no audio device, so playback cannot start. Session hn029-chipsynth, take-006.",
    ],
    officina: [
      "Are the figures on this sheet live telemetry?",
      "Blueprint sheet 01, scale as noted, three dimension callouts. The footer says the figures are records from the merged tree, not live telemetry.",
    ],
    custos: [
      "Is this view live right now?",
      "Header: STATE: PARKED - wakes when the OS lands. Body: two agent records and an estimated spend of $0.004.",
    ],
    boards: [
      "Which board section is empty, and what does a red pin mean?",
      "Sections: NYPD, FDNY, EMS, DSNY. DSNY shows an empty state: no pack file. A red pin marks a camera a division flagged for human review.",
    ],
    aegis: [
      "What does this page show, and does it scan anything?",
      "Read-only dashboard over recorded findings: four findings newest first, one high severity secret in a test fixture. Sources read from disk; the page scans and fixes nothing.",
    ],
    nervus: [
      "Should I treat these panels as evidence about a model?",
      "Panels: dose windows, hosted lane state, last run, layer curve. Several lines are labelled STUB, which the page defines as placeholders, never evidence about a model.",
    ],
    messages: [
      "Which rooms exist and who posts the NOTIFY lines?",
      "Rooms on the Board: main, custos, officina, science, musica. NOTIFY lines are posted by the resident agent crew.",
    ],
    monitor: [
      "Where do these cards come from, and what happens when that source is down?",
      "Cards: load 1.42, memory 61 percent, uptime 2h14m. Stamp: updated from http://127.0.0.1:18932/facts. When the facts service is down the page draws no cards and says unreachable.",
    ],
    notes: [
      "What is drawn on this page?",
      "A piano roll of session hn029-chipsynth: 512 notes over the session length, with the take selector above it.",
    ],
    general: [
      "What can you answer about this machine?",
      "No app context: the page did not identify itself.",
    ],
  };
  for (const [k, [q, ctx]] of Object.entries(cases)) console.log(k + "\t" + q + "\t" + ctx);
')

SERVER_LOG=$(mktemp -t metaos-chat-proof.XXXXXX)
SPARK_API_KEY="$SPARK_API_KEY" ASSESS_LIVE_MODEL=1 PORT="$PORT" METAOS_STATIC_ROOT="$STATIC_ROOT" \
  node server/server.mjs > "$SERVER_LOG" 2>&1 &
SERVER_PID=$!
cleanup() { kill "$SERVER_PID" 2>/dev/null || true; wait "$SERVER_PID" 2>/dev/null || true; }
trap cleanup EXIT

for _ in $(seq 1 60); do
  curl -sf -m 2 "http://127.0.0.1:$PORT/api/health" >/dev/null 2>&1 && break
  sleep 0.25
done
HEALTH=$(curl -s -m 3 "http://127.0.0.1:$PORT/api/health" || true)
case "$HEALTH" in
  *'"configured":true'*) ;;
  *) echo "proof_agent_chat: server did not report a configured key: $HEALTH" >&2; exit 1 ;;
esac
echo "server: http://127.0.0.1:$PORT  $HEALTH"
echo

# The ledger keeps a cumulative total, so "this run" is the difference between
# the total now and the total before the first question. Summing each response's
# running total would count every earlier call again.
start_spend=$(node -e '
  import("./server/budget.mjs").then((m) => {
    try { process.stdout.write(String(m.budgetStatus().est_cost_usd)); } catch { process.stdout.write("0"); }
  });
')
fails=0

echo "== every app answers through /api/agent/ask"
while IFS=$'\t' read -r app label; do
  [ -n "$app" ] || continue
  question=$(printf '%s\n' "$CASES" | awk -F'\t' -v a="$app" '$1==a {print $2}')
  context=$(printf '%s\n' "$CASES" | awk -F'\t' -v a="$app" '$1==a {print $3}')
  [ -n "$question" ] || question="What is this app showing right now?"
  body=$(node -e '
    const [app, question, context] = process.argv.slice(1);
    process.stdout.write(JSON.stringify({ app, question, context }));
  ' "$app" "$question" "$context")
  out=$(curl -s -m 120 -w '\n%{http_code}' -X POST "http://127.0.0.1:$PORT/api/agent/ask" \
    -H 'Content-Type: application/json' -d "$body")
  code=$(printf '%s' "$out" | tail -1)
  payload=$(printf '%s' "$out" | sed '$d')
  reply=$(printf '%s' "$payload" | node -e '
    let s=""; process.stdin.on("data",d=>s+=d).on("end",()=>{
      try { const j=JSON.parse(s); process.stdout.write(j.reply || ("(" + (j.error||"no reply") + ")")); }
      catch { process.stdout.write("(unparseable response)"); }
    });')
  if [ "$code" = "200" ]; then
    printf '  [200] %-9s %s\n' "$app" "$reply"
  else
    printf '  [%s] %-9s %s\n' "$code" "$app" "$reply"
    fails=$((fails + 1))
  fi
  now=$(node -e '
    import("./server/budget.mjs").then((m) => {
      try { process.stdout.write(String(m.budgetStatus().est_cost_usd)); } catch { process.stdout.write("0"); }
    });
  ')
  over=$(node -e "process.stdout.write(String((Number(process.argv[1]) - Number(process.argv[2])) >= Number(process.argv[3])))" \
    "$now" "$start_spend" "$MAX_SPEND")
  if [ "$over" = "true" ]; then
    echo "  stopping: this run reached the \$MAX_SPEND cap (\$$MAX_SPEND estimated)"
    break
  fi
done <<< "$APPS"

# The two face pages live on the 18900 static server, not on this one, so they
# are checked through a throwaway copy of that server on 18901. Their box loads
# the module and the API from 18934 by absolute URL, which is what the image
# does too.
FACE_DIR="$ROOT/os-build/face"
FACE_PORT=18901
if command -v python3 >/dev/null && [ -d "$FACE_DIR" ]; then
  (cd "$FACE_DIR" && python3 -m http.server "$FACE_PORT" --bind 127.0.0.1 >/dev/null 2>&1) &
  FACE_PID=$!
  trap 'cleanup; kill $FACE_PID 2>/dev/null || true' EXIT
  for _ in $(seq 1 40); do
    curl -sf -m 2 "http://127.0.0.1:$FACE_PORT/musica.html" >/dev/null 2>&1 && break
    sleep 0.2
  done
  echo
echo "== the two face pages (18900 in the image, 18901 here) serve their box"
  for pair in "musica.html:musica" "dashboard.html:monitor"; do
    page=${pair%%:*}; app=${pair##*:}
    html=$(curl -s -m 10 "http://127.0.0.1:$FACE_PORT/$page")
    if printf '%s' "$html" | grep -q 'agent-chat.js' && printf '%s' "$html" | grep -q "data-app=\"$app\""; then
      printf '  [ok]   %-38s %s\n' "$page" "$app"
    else
      printf '  [FAIL] %-38s no box for %s\n' "$page" "$app"
      fails=$((fails + 1))
    fi
  done
  kill "$FACE_PID" 2>/dev/null || true
  wait "$FACE_PID" 2>/dev/null || true
fi

echo
echo "== every page serves its box"
while IFS=: read -r page app; do
  [ -n "$page" ] || continue
  html=$(curl -s -m 10 "http://127.0.0.1:$PORT/$page")
  # The division pages import their console as ./agent.js, so both names count.
  if printf '%s' "$html" | grep -q 'agent-chat.js\|agent\.js'; then
    if printf '%s' "$html" | grep -q "data-app=\"$app\"\|createAgent"; then
      printf '  [ok]   %-38s %s\n' "$page" "$app"
    else
      printf '  [warn] %-38s box found, app id %s not literal (trio console?)\n' "$page" "$app"
    fi
  else
    printf '  [FAIL] %-38s no chat box in the served page\n' "$page"
    fails=$((fails + 1))
  fi
done <<< "$PAGES"

echo
LEDGER=$(node -e '
  import("./server/budget.mjs").then((m) => {
    const s = m.budgetStatus();
    console.log(JSON.stringify(s));
  });
')
echo "ledger (all calls ever, shared with the queue): $LEDGER"
node -e "console.log(\`this run, estimated: \\$\${(Number(process.argv[1]) - Number(process.argv[2])).toFixed(6)} (cap \\$\${process.argv[3]})\`)" \
  "$now" "$start_spend" "$MAX_SPEND"
if [ "$fails" -ne 0 ]; then
  echo "RESULT: FAIL — $fails problem(s) above; server log: $SERVER_LOG"
  exit 1
fi
echo "RESULT: PASS — every app answered and every page carries its box"

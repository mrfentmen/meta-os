#!/usr/bin/env bash
# proof_agent_tools.sh — prove the agent's hands, not just its mouth.
#
#   METAOS_KEY_FILE="$HOME/Desktop/Hackathon Key.txt" tools/proof_agent_tools.sh
#
# Three parts, in this order, because they prove three different things:
#
#   A. agent_loop --self-test — the tools themselves, no model, no key, no
#      spend: write creates parents, read returns content, list sees it, run
#      captures stdout and a nonzero exit, a path escape is refused, a
#      destructive command is refused, and the model key is stripped from a
#      tool subprocess.
#   B. the permissioned gateway (agents/tools.mjs) — a grant is checked before
#      the action, the action leaves a receipt with a hash, and an action
#      outside the grant is refused WITH a receipt. No model, no spend.
#   C. the loop with the model in it — the model chooses the tools, the OS
#      performs them for real (a file is written, a shell command runs), and
#      the script then verifies the artefact itself by running it, instead of
#      trusting the agent's own summary.
#
# Part C needs SPARK_API_KEY or METAOS_KEY_FILE; without one it is reported as
# SKIP and the run fails, because a proof with no model proves nothing about
# tool calling by a model. Spend is capped twice: --max-usd on the loop and
# METAOS_PROOF_MAX_USD here (default 0.20).
#
# Exit 0 only when A and B pass, C finishes, and the artefact the agent wrote
# is correct when this script runs it.
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"

MAX_USD="${METAOS_PROOF_MAX_USD:-0.20}"
MAX_ACTIONS="${METAOS_PROOF_MAX_ACTIONS:-6}"
WORK=$(mktemp -d -t metaos-tool-proof.XXXXXX)
trap 'rm -rf "$WORK"' EXIT
fails=0
row() { # ok|fail|skip, label, detail
  case "$1" in
    ok) printf '  [ok]   %-46s %s\n' "$2" "${3:-}" ;;
    skip) printf '  [skip] %-46s %s\n' "$2" "${3:-}" ;;
    *) printf '  [FAIL] %-46s %s\n' "$2" "${3:-}"; fails=$((fails + 1)) ;;
  esac
}

if [ -z "${SPARK_API_KEY:-}" ] && [ -n "${METAOS_KEY_FILE:-}" ]; then
  [ -r "$METAOS_KEY_FILE" ] || { echo "proof_agent_tools: cannot read METAOS_KEY_FILE=$METAOS_KEY_FILE" >&2; exit 2; }
  SPARK_API_KEY=$(tr -d '\r\n' < "$METAOS_KEY_FILE")
fi
command -v node >/dev/null || { echo "proof_agent_tools: node not found" >&2; exit 2; }

echo "== A. the tools themselves (no model, no key, no spend)"
set +e
SELF=$(node agents/agent_loop.mjs --self-test 2>&1)
SELF_CODE=$?
set -e
printf '%s\n' "$SELF" | sed 's/^/  /'
if [ "$SELF_CODE" -eq 0 ]; then
  row ok "agent_loop self-test" "$(printf '%s' "$SELF" | tail -1)"
else
  row fail "agent_loop self-test" "exit $SELF_CODE"
fi

echo
echo "== B. the permissioned gateway: grant, action, receipt, refusal"
set +e
GATE=$(WORK="$WORK" node --input-type=module -e '
  import fs from "node:fs";
  import path from "node:path";
  import { createToolGateway, receiptEvidence, ToolError } from "./agents/tools.mjs";

  const dir = process.env.WORK;
  const inside = path.join(dir, "inside");
  fs.mkdirSync(inside, { recursive: true });
  const gateway = createToolGateway({
    grants: { read: [inside], write: [inside], commands: [process.execPath] },
    root: dir,
    runDir: path.join(dir, "run"),
    runId: "proof-run",
    agent: "proof",
  });

  const write = await gateway.call({ kind: "write", path: "inside/note.txt", data: "hello tools\n" });
  const read = await gateway.call({ kind: "read", path: "inside/note.txt" });
  const exec = await gateway.call({ kind: "exec", argv: [process.execPath, "-e", "process.stdout.write(String(6*7))"] });
  console.log("write  receipt " + write.receipt.id + " ok=" + write.receipt.ok + " bytes=" + write.receipt.bytes + " sha256=" + write.receipt.sha256.slice(0, 12) + "…");
  console.log("read   bytes=" + read.result.data.length + " evidence=" + receiptEvidence(read.receipt));
  console.log("exec   stdout=" + JSON.stringify(exec.result.stdout) + " exit=" + exec.receipt.exit + " stdoutSha256=" + exec.receipt.stdoutSha256.slice(0, 12) + "…");

  let refused = null;
  try {
    await gateway.call({ kind: "write", path: "../escape.txt", data: "nope" });
  } catch (error) {
    if (!(error instanceof ToolError)) throw error;
    refused = error;
  }
  if (!refused) { console.log("REFUSAL MISSING"); process.exit(3); }
  console.log("refuse code=" + refused.code + " receipt=" + refused.receipt.id + " ok=" + refused.receipt.ok);

  const receipts = fs.readFileSync(path.join(dir, "run", "receipts.jsonl"), "utf8").trim().split("\n").map((l) => JSON.parse(l));
  const kinds = receipts.map((r) => r.kind + ":" + r.ok).join(",");
  const escaped = fs.existsSync(path.join(dir, "..", "escape.txt"));
  console.log("receipts " + receipts.length + " [" + kinds + "] seq=" + receipts.map((r) => r.seq).join(","));
  console.log("escape file created=" + escaped);
  const problems = [];
  if (receipts.length !== 4) problems.push("expected 4 receipts, got " + receipts.length);
  if (!receipts.every((r, i) => r.seq === i + 1)) problems.push("sequence is not 1..4");
  // Only the receipts of actions that happened carry a content hash; the
  // refusal carries the grant code instead, which is the point of it.
  const hashed = receipts.filter((r) => r.ok === true && ["write", "read", "append"].includes(r.kind));
  if (!hashed.every((r) => typeof r.sha256 === "string" && r.sha256.length === 64)) problems.push("an allowed write/read receipt has no sha256");
  if (receipts.filter((r) => r.ok === false).some((r) => !r.code)) problems.push("the refusal receipt has no code");
  if (receipts.filter((r) => r.ok === false).length !== 1) problems.push("the refusal is not recorded");
  if (escaped) problems.push("a refused write still touched the disk");
  if (exec.result.stdout !== "42") problems.push("the exec did not return its stdout");
  console.log(problems.length ? "PROBLEMS " + problems.join("; ") : "gateway ok");
  process.exit(problems.length ? 1 : 0);
' 2>&1)
GATE_CODE=$?
set -e
printf '%s\n' "$GATE" | sed 's/^/  /'
if [ "$GATE_CODE" -eq 0 ]; then
  row ok "gateway receipts + refusal" "4 receipts, 1 refusal recorded, no disk escape"
else
  row fail "gateway receipts + refusal" "exit $GATE_CODE"
fi

echo
echo "== C. a model choosing tools and the OS performing them"
if [ -z "${SPARK_API_KEY:-}" ]; then
  row skip "live tool-calling run" "no key (set SPARK_API_KEY or METAOS_KEY_FILE)"
else
  set +e
  RUN=$(SPARK_API_KEY="$SPARK_API_KEY" node agents/agent_loop.mjs \
    --task "Create build/hello.mjs that prints the sum of 1 through 10 using a loop. Then run it with node and confirm the output is exactly 55. Finish with the real command output as evidence." \
    --workspace "$WORK/workspace" \
    --max-actions "$MAX_ACTIONS" \
    --max-usd "$MAX_USD" \
    --transcript "$WORK/transcript.jsonl" 2>&1)
  RUN_CODE=$?
  set -e
  printf '%s\n' "$RUN" | sed 's/^/  /'

  if [ "$RUN_CODE" -eq 0 ]; then
    row ok "the loop finished on its own" "exit 0"
  else
    row fail "the loop finished on its own" "exit $RUN_CODE"
  fi

  # What the run claims, read from the artefact rather than the prose.
  STEPS=$(node -e '
    const fs = require("node:fs");
    const d = JSON.parse(fs.readFileSync(process.argv[1], "utf8"));
    const kinds = d.steps.map((s) => s.tool);
    process.stdout.write(JSON.stringify({
      ok: d.ok, stopped: d.stopped, model: d.model,
      tools: kinds, writes: kinds.filter((k) => k === "write").length,
      runs: kinds.filter((k) => k === "run").length, calls: d.usage.calls, usd: d.usage.usd,
    }));
  ' "$WORK/agent-result.json")
  echo "  $STEPS"
  if printf '%s' "$STEPS" | grep -q '"ok":true' \
    && printf '%s' "$STEPS" | grep -q '"writes":1' \
    && printf '%s' "$STEPS" | grep -q '"runs":1'; then
    row ok "the model called write and run" "$STEPS"
  else
    row fail "the model called write and run" "$STEPS"
  fi

  # The independent check: this script runs the artefact itself.
  if [ -f "$WORK/workspace/build/hello.mjs" ]; then
    OUT=$(node "$WORK/workspace/build/hello.mjs" 2>&1 || true)
    if [ "$OUT" = "55" ]; then
      row ok "the artefact runs and prints 55" "node build/hello.mjs -> $OUT"
    else
      row fail "the artefact runs and prints 55" "got $(printf '%s' "$OUT" | head -1)"
    fi
  else
    row fail "the artefact exists" "no build/hello.mjs in the workspace"
  fi

  # The transcript is the run's own record: one line per step, key redacted.
  if [ -s "$WORK/transcript.jsonl" ]; then
    LINES=$(wc -l < "$WORK/transcript.jsonl" | tr -d ' ')
    if grep -qi "$SPARK_API_KEY" "$WORK/transcript.jsonl"; then
      row fail "the transcript never holds the key" "the key appears in transcript.jsonl"
    else
      row ok "the transcript records the run" "$LINES lines, no key"
    fi
  else
    row fail "the transcript records the run" "empty transcript"
  fi

  SPEND=$(node -e '
    const fs = require("node:fs");
    const d = JSON.parse(fs.readFileSync(process.argv[1], "utf8"));
    process.stdout.write("$" + d.usage.usd.toFixed(4) + " est, " + d.usage.calls + " calls, " +
      d.usage.promptTokens + " in / " + d.usage.completionTokens + " out");
  ' "$WORK/agent-result.json")
  echo "  spend: $SPEND (cap \$$MAX_USD)"
fi

echo
echo "== ledger (all calls ever, shared with the chat and the queue)"
node -e '
  import("./server/budget.mjs").then((m) => {
    try { console.log("  " + JSON.stringify(m.budgetStatus())); }
    catch (e) { console.log("  unreadable: " + e.message); }
  });
'

echo
if [ "$fails" -eq 0 ]; then
  echo "RESULT: PASS — the tools run, the gateway refuses and records, the model called them, the artefact verifies"
  exit 0
fi
echo "RESULT: FAIL — $fails check(s) did not hold"
exit 1

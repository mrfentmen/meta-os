# SAM-Spark live runbook (for Del, who holds SPARK_API_KEY)

First measured multi-model pass: real SAM-3.1 regions in, real
Muse Spark reasoning out, scored against the labelled SAM pairs
(`os/intel/evals/sam/pairs.json`) and the Ignis frozen 20
(`eval/ignis/scenarios.json`), spend on the existing ledgers.
Branch: `opencode/agent3-sam-spark`. Work from the repo root.
Nothing below prints the key.

## 0. Preflight (no key needed, no network)

```sh
git status --short                # expect clean on opencode/agent3-sam-spark
test -n "$SPARK_API_KEY" && echo key-present || echo KEY-MISSING
python3 -c "import json; print(len(json.load(open('eval/ignis/scenarios.json'))['scenarios']))"
# expect: 20
ls os/intel/evals/sam/*.png      # expect 4 files
python3 - <<'EOF'
import json
s = json.load(open('server/queue/spark_guardrail_state.json')) \
    if __import__('os').path.exists('server/queue/spark_guardrail_state.json') \
    else {"calls": 0, "est_cost_usd": 0.0}
print("guardrail before:", s["calls"], "calls, $%.4f" % s["est_cost_usd"])
EOF
```

If `KEY-MISSING`, stop: live mode refuses without a key (exit 2,
nothing sent). That refusal is the honest state, not a failure.

## 1. The live pass (one command, ~24 model calls)

```sh
python3 os/intel/sam_spark.py --mode live --out os/intel/sam_spark_live_run.json
```

What it does, in order:

1. SAM halves (4 PNG reads): each goes to SAM 3.1
   (`server/queue/models.segment`) for regions, then the regions +
   panel prompt go to Muse Spark (`models.chat_image`) for a
   `build-ok` / `build-broken` verdict, scored vs the manifest.
2. Ignis 20: scenarios are labelled text, not frames, so regions
   are explicit seeded boxes (alert_expected -> one box, else
   none -- see `region_fn` in `os/intel/sam_spark.py`). Each goes
   to Muse Spark (`models.chat_text`) for an ignis category,
   scored vs ground truth with the legacy alert definition.
   A frame-backed Ignis pass (live SAM on real footage) is still
   open work: never create a real fire to source frames.

Expected console tail (numbers will differ -- this is a live model):

```
SAM pairs: n/4 correct (accuracy ...), errors 0
Ignis 20: TP=.. FP=.. TN=.. FN=..
Spend (intel.store spend ledger): 24 calls, est $X.XXXXXX, ...
Wrote os/intel/sam_spark_live_run.json
```

`Spend (intel.store spend ledger)` -- not `local-only` -- is the
proof the bus ledger was reachable. If it reads `local-only`, the
`ledger_missed` count says how many entries stayed run-local.

## 2. Spend evidence to capture (all four, paste into the report)

```sh
# (a) run JSON spend rollup + per-call entries (24 expected)
python3 -c "import json; r=json.load(open('os/intel/sam_spark_live_run.json')); print(json.dumps(r['spend'], indent=1)); print('ledger:', r['ledger'])"
# (b) guardrail counter (the $75 hard stop; before/after diff is the pass cost)
python3 -c "import json; s=json.load(open('server/queue/spark_guardrail_state.json')); print(s['calls'], '\$%.6f' % s['est_cost_usd'])"
# (c) per-call model receipts (validate, then count)
python3 - <<'EOF'
import os, sys
sys.path.insert(0, 'server/queue')
import models
path = os.environ.get('METAOS_MODEL_RECEIPTS',
                       'server/queue/model_receipts.jsonl')
if not os.path.exists(path):
    print('no receipts file yet (expected pre-live):', path)
else:
    print('receipts ok:', models.validate_receipts(path))
EOF
# (d) intel bus ledger (from os/, needs the relay bus env you run the room on)
cd os && python3 -c "from intel import store; print('entries:', len(store.spend_entries())); print('total \$%.6f' % store.spend_total())"
```

Guardrail stop is evidence, not failure: if cumulative estimated
spend reaches $75, the next call refuses BEFORE sending
(`GuardrailStop`, run exits non-zero, entries so far are kept).
Capture the refusal line and the (b) counter at $75.0000.

## 3. After the pass (keep suites green, commit the numbers)

```sh
node --test eval/ignis/adapter.test.mjs eval/ignis/report.test.mjs
python3 tests/queue-python/test_models_sam_bounds.py
python3 tests/queue-python/test_models_sam_parse.py
cd os && python3 -m unittest tests.test_intel_sam_spark
git add os/intel/sam_spark_live_run.json   # live evidence, new file only
git commit -m "SAM-Spark live pass: <one-line numbers + spend>"
# do NOT push; do NOT print or commit SPARK_API_KEY anywhere
```

Known pre-existing red (not yours, do not "fix" in this lane):
`tests.test_intel_sam_eval` (2 failures -- `os/intel/sam_check.py`
looks for submission originals under `os/hackathon/...`, they live
at repo-root `hackathon/...`).

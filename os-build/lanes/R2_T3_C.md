# R2-T3 Section C — model calls, keys, budgets (tasks 47-62)

Worktree `/tmp/agent-r2-t3`, branch `agent-r2-t3`. No commits, no merges.
New files only: `agents/providers.mjs`, `agents/providers.test.mjs`,
`server/queue/stub_provider.py`, this report. Zero tracked files modified
(`git diff --stat` empty). No real network calls made anywhere on this
lane; no key exists on this box, so only the refusal paths are proven —
the real-call path is explicitly NOT run (tasks 57-58).

Read first (per brief): `agents/model_client.mjs`, `server/queue/models.py`,
`server/queue/spark_gen.py`, `agent-layer/meta-ask.py`,
`os-build/layer1/secret_counts.py`.

## Design decision

All provider/key/budget logic for this section lives in one new module,
`agents/providers.mjs`, which `agents/model_client.mjs:36-43` and
`server/queue/models.py:97-103` stay consistent with (same key name, same
Spark rate card). `agents/model_client.mjs` was NOT edited (minimal diff).
The Python twin `server/queue/stub_provider.py` is new — no stub file
existed (`grep stub_provider server/queue` found nothing before creation).

## Task ticks with pasted proofs

47. **Provider inventory.** `agents/providers.mjs` `PROVIDERS` table: five
    models, exact key env name each. All bill to one account, so every entry
    names `SPARK_API_KEY`; `METAOS_NOTIFY_WEBHOOK` is documented as NOT a
    model provider (relay webhook only). Voice is `callable:false`
    (matches `server/queue/models.py:404-414`).

    ```
    $ node --test agents/providers.test.mjs   (excerpt)
    ▶ providers: task 47 — provider inventory + exact key names
      ✔ five providers, every model key is SPARK_API_KEY (0.829875ms)
    ```

    | provider | surface | key env | USD rate |
    |---|---|---|---|
    | muse-spark-1.3 | POST /v1/chat/completions | SPARK_API_KEY | $1.25/M in, $4.25/M out |
    | muse-wonder-1.0 | POST /v1/chat/completions | SPARK_API_KEY | none published |
    | sam-3.1 | POST /v1/responses | SPARK_API_KEY | none (bills images) |
    | muse-image-1.0 | POST /v1/responses | SPARK_API_KEY | none published |
    | muse-voice-transcribe-1.0 | unresolved (404/model_not_found, probed 2026-11-02) | SPARK_API_KEY | none; refuses |

48. **Key loading from `/etc/metaos/agent.env`.** `AGENT_ENV_PATH` constant
    is exactly `/etc/metaos/agent.env`; parsing (`loadAgentEnvFile`) reads
    KEY=VALUE, ignores comments/blanks, reports the file mode, never logs
    values. Tests use a FAKE file under `os.tmpdir()` — the real path is
    asserted as a string constant but never opened by any test.

    ```
    ▶ providers: task 48 — keys load from a 0600 env file, values never printed
      ✔ default path constant is /etc/metaos/agent.env (not read here)
      ✔ FAKE env file in /tmp parses KEY=VALUE, reports mode, names only
      ✔ missing file reports missing instead of throwing
      ✔ env beats file; file is the fallback
    ```

49. **Missing key refuses BEFORE any network, naming path+key.** The
    production order in `resolveProvider` is key-gate first, fetch only
    after. Test proof: the fetch double counts invocations and stays at 0.

    ```
    ▶ providers: task 49 — missing key refuses BEFORE any network
      ✔ refusal names the path and the key, and the fetch double is never called
    ```
    Refusal text (pasted from proof run): `missing key: SPARK_API_KEY is
    not set (env or /tmp/fake-agent.env); no model call sent.`

50. **Spend cap per job AND per day, in provider-billed units (USD).**
    `assertBudget({jobBudgetUsd, jobCapUsd, daySpentUsd, dayCapUsd})` with
    defaults `DEFAULT_JOB_CAP_USD=0.25`, `DEFAULT_DAY_CAP_USD=1.0`; durable
    per-day ledger `readDaySpend`/`addDaySpend` (JSON `{date, spentUsd,
    calls}`). The outer `$75` hard stop in
    `server/queue/spark_guardrail.py:7-9` is unchanged — these stricter caps
    bound demo work.

    ```
    ▶ providers: tasks 50-51 — per-job and per-day caps in USD
      ✔ a budget inside both caps passes
      ✔ day ledger persists across reads in a tmp file
    ```

51. **Zero/over-cap budgets refused naming the cap.**

    ```
      ✔ zero budget refuses naming the cap (BUDGET_ZERO)
      ✔ over-cap job refuses naming the per-job cap (OVER_JOB_CAP)
      ✔ day overflow refuses naming the daily cap (OVER_DAY_CAP)
    ```
    Example: `refused: job budget $0.2600 exceeds the per-job cap $0.25
    USD (OVER_JOB_CAP)`.

52. **Preflight estimates only when the provider exposes a rate.**
    `estimateCost` returns numeric USD for Spark (same rate card as
    `agents/model_client.mjs:49-51` and
    `server/queue/spark_guardrail.py:23-24`); Wonder/SAM/Image/Voice return
    `{unknown:true, usd:null, reason:"... cost unknown, never invented"}`.

    ```
    ▶ providers: task 52 — preflight estimates only when the provider exposes a rate
      ✔ Spark (rate card $1.25/M in, $4.25/M out) yields a numeric USD estimate
      ✔ Wonder / SAM / Image / Voice report unknown, never invented
    ```
    Check: 8000 in + 2000 out → `0.0185` USD exactly
    (8000/1e6×1.25 + 2000/1e6×4.25).

53. **Timeout + named error.** `callWithTimeout` rejects `MODEL_TIMEOUT`
    naming the ms. Proven with a stub delayed past the deadline.

    ```
    $ node --input-type=module -e "...callWithTimeout(slow200ms, 25)..."
    timeout: code=MODEL_TIMEOUT msg=model call timed out after 25ms (MODEL_TIMEOUT)
    ```

54. **One retry on transient, then the provider code.** `callWithRetry`
    (retries=1 → 2 attempts; 4xx never retried). Proven with a stub that
    500s once then succeeds, and one that always 500s.

    ```
    flaky: {"result":"recovered","attempts":2}
    always-500: status=500 attempts=2
    ```

55. **Redaction.** `redactSecrets` scrubs exact planted values plus
    `sk-`/`LLM_`/`Bearer` shapes; names (`SPARK_API_KEY`) stay. Planted
    `PLANTED-FAKE-VALUE-9Z9Z-TESTONLY`, ran the failing paths, grepped:

    ```
    missing key: SPARK_API_KEY is not set (env or /tmp/fake-agent.env); no model call sent. ...
    transport echoed [REDACTED] in a 500 body
    planted-value grep count: 0 (want 0)
    key-name grep count: 1 (want >=1)
    on-disk grep for value: 0 (want 0)
    ```

56. **Token usage per run, summed in the receipt.** `sumUsage` +
    `buildReceipt`/`writeReceiptLine` (JSONL, `transport` labeled). Test
    writes 3 stub-run lines + 1 `run-total` line and verifies the sum
    (3 calls, completion 48).

    ```
    ▶ providers: task 56 — token usage per run, summed in the receipt
      ✔ three stub runs sum prompt/completion tokens and receipt costs
    ```

57-58. **`--probe` gating: real call ONLY with explicit `--spend`.**
    Gate order in `probeMain` (`agents/providers.mjs`): (1) no `--spend`
    → refuse exit 2 before reading any key or network; (2) `--spend` but
    no key → missing-key refusal exit 4 naming path+key, still no network;
    (3) both → one minimal real call (max_tokens 16). **A real call was
    never run: no key exists on this box, so only paths (1)-(2) are proven.**

    ```
    $ env -u SPARK_API_KEY node agents/providers.mjs --probe; echo "exit=$?"
    probe refused: --probe makes a real billed call only with an explicit --spend flag.
    re-run as: node agents/providers.mjs --probe --spend [--provider ID]
    no network touched, no key read.
    exit=2
    $ env -u SPARK_API_KEY node agents/providers.mjs --probe --spend --env-file /tmp/fake-empty-agent.env; echo "exit=$?"
    probe refused: missing key: SPARK_API_KEY is not set (env or /tmp/fake-empty-agent.env); no model call sent. ...
    exit=4
    ```

59. **Deterministic stub.** `stubCall` (JS) and `server/queue/stub_provider.py`
    `stub_chat` (Python): same input → same text+usage, no network, no clock.

    ```
    ▶ tasks 59-60 — deterministic stub, default when no key
      ✔ stub is deterministic per input
    $ python3 -c "from stub_provider import stub_chat; ..."
    deterministic: True
    receipt: {'kind': 'stub-call', 'model': 'muse-spark-1.3', 'transport': 'stub', ...}
    ```

60. **Stub is the default when no key exists; runs labeled `stub`.**

    ```
    $ env -u SPARK_API_KEY node -e "...resolveTransport..."
    no-key: {"mode":"stub","label":"stub","reason":"no SPARK_API_KEY (env or /etc/metaos/agent.env)"}
    stub: {"transport":"stub","model":"muse-spark-1.3","text":"STUB muse-spark-1.3 :: prompt-chars=5 :: reply-ok",...}
    ```
    Every receipt carries `"transport":"stub"` (task 56 test asserts all 4
    lines).

61. **Zero real network calls in CI mode.** `isCiMode` (`CI=1`/`true` or
    `METAOS_CI=1`) forces the stub even with a key present; `stubFetch`
    throws `STUB_NO_NETWORK` on any non-localhost host.

    ```
    ci+key: {"mode":"stub","label":"stub","reason":"CI mode forces the stub (CI=1)"}
    ▶ providers: task 61 — CI mode performs zero real network calls
      ✔ CI=1 forces the stub even when a key is present
      ✔ the stub transport throws on non-localhost instead of dialing it
    ```

62. **Demo's three jobs + costs, total under $1.** These are STUB/ESTIMATED
    units, honestly labeled — stub usage costed at the Spark rate card. A
    real run would bill metered tokens at $1.25/M in + $4.25/M out (Spark
    only; Wonder/SAM/Image publish no USD rate, so their real cost is
    unknown until the provider exposes it).

    ```
    assess one frame: usage={"prompt_tokens":7,"completion_tokens":16} est=$0.000077 USD (ESTIMATE)
    second reading:   usage={"prompt_tokens":10,"completion_tokens":16} est=$0.000081 USD (ESTIMATE)
    judge:            usage={"prompt_tokens":9,"completion_tokens":16} est=$0.000079 USD (ESTIMATE)
    TOTAL est=$0.000237 USD (UNDER $1: PASS)
    ```

## Full suite + regression

```
$ node --test agents/providers.test.mjs 2>&1 | tail -8
ℹ tests 28 / ℹ pass 28 / ℹ fail 0      (13 suites, ~165ms)

$ node --test agents/approve.test.mjs agents/snapshots.test.mjs 2>&1 | tail -8
ℹ tests 10 / ℹ pass 10 / ℹ fail 0      (untouched files still green)
```

Secret-value grep over the three new files (stripe/github/AWS/private-key
shapes): `no secret-shaped values (good)`; key NAMES present 10×/14× in the
JS files. Fixed one self-found bug during proof: the CLI guard crashed under
`node -e` (`pathToFileURL(undefined)`); now guarded on `typeof
process.argv[1] === "string"`.

## Skips + why

- No live `--probe --spend` call: refused in writing — no key on this box,
  no paid calls without a key and a cap. Only the refusal paths are proven.
- No QEMU/guest proof: host-only per lane rules; guest path (`meta-agent-login`
  importing the key, 0600 check in `agent-layer/stage.sh:148-152`) is
  code-inspected, not executed.
- Python stub has no `.test` file: logic lives in JS (`providers.mjs`);
  the Python module is a deterministic helper verified inline via
  `python3 -c` above, stdlib only.

## Cross-lane requests (file:line)

- Section B (`metaosd`/daemon): call `resolveTransport` + `assertBudget`
  from `agents/providers.mjs` at submit time so a no-key or over-cap job
  is refused with `NO_KEY`/`OVER_*` before queueing; write the returned
  receipt `transport` label (`stub`/`live`) into the run record so the
  receipt chain (tasks 40-42) shows which runs spent.
- Section B budget file: reconcile `agents/providers.mjs`
  `DEFAULT_JOB_CAP_USD` (0.25) / `DEFAULT_DAY_CAP_USD` (1.0) with the
  relay `budget.json` seeded in `agent-layer/meta-agent-login.sh:49-53`
  (spawns/hour, not USD) — two different units, keep both, document which
  is which in the operator runbook (task 80).
- Section D (demo/eval): run the eval harness and demo under `CI=1` so
  `isCiMode` forces the stub; assert `transport==="stub"` on every receipt
  (task 69's no-network requirement is then structural, not hoped-for).
- Image units (other lane owns `provision.sh`): the probe's key source is
  the same file the login hook sources (`/etc/metaos/agent.env`, root 0600
  per `agent-layer/stage.sh:295-312`); no unit change requested, only note
  that `meta-code.sh:60-68` already follows the env-first/file-second
  precedence implemented here.

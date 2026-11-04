// Tests for the R2-T3 Section C provider/key/budget logic.
// Run from the worktree root:  node --test agents/providers.test.mjs
//
// LOCALHOST/STUB ONLY: no test performs a real network call. The missing-
// key tests prove refusal happens BEFORE any fetch (the fetch double
// records invocation and must stay uncalled); the --probe tests assert the
// gating refusals (exit 2 without --spend, exit 4 without a key) and never
// pass both gates at once, so no real call is ever attempted. Key material
// below is FAKE (planted test-only values); the real path
// /etc/metaos/agent.env is asserted as a constant but never read — every
// file test uses a FAKE env file under os.tmpdir().

import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { describe, test } from "node:test";
import url from "node:url";

import {
  AGENT_ENV_PATH,
  DEFAULT_DAY_CAP_USD,
  DEFAULT_JOB_CAP_USD,
  PROVIDERS,
  addDaySpend,
  assertBudget,
  buildReceipt,
  callWithRetry,
  callWithTimeout,
  estimateCost,
  getKey,
  isCiMode,
  isTransient,
  loadAgentEnvFile,
  providerList,
  readDaySpend,
  redactSecrets,
  resolveProvider,
  resolveTransport,
  stubCall,
  stubFetch,
  sumUsage,
  writeReceiptLine,
} from "./providers.mjs";

const HERE = path.dirname(url.fileURLToPath(import.meta.url));
const CLI = path.join(HERE, "providers.mjs");
// Obviously-fake planted value (task 55). No quotes, 32 chars: trips no
// secret-scanner shape, but proves exact-value scrubbing end to end.
const PLANTED = "PLANTED-FAKE-VALUE-9Z9Z-TESTONLY";
const NOKEY_ENV = {};
const EMPTY_FILE_VALUES = {};

function fakeEnvFile(contents) {
  const dir = mkdtempSync(path.join(tmpdir(), "agent-env-"));
  const file = path.join(dir, "agent.env");
  writeFileSync(file, contents, { mode: 0o600 });
  return { dir, file };
}

describe("providers: task 47 — provider inventory + exact key names", () => {
  test("five providers, every model key is SPARK_API_KEY", () => {
    const ids = Object.keys(PROVIDERS).sort();
    assert.deepEqual(ids, [
      "muse-image-1.0",
      "muse-spark-1.3",
      "muse-voice-transcribe-1.0",
      "muse-wonder-1.0",
      "sam-3.1",
    ]);
    for (const id of ids) {
      assert.equal(PROVIDERS[id].keyEnv, "SPARK_API_KEY", id);
    }
    const list = providerList();
    assert.equal(list.length, 5);
    const voice = list.find((p) => p.id === "muse-voice-transcribe-1.0");
    assert.equal(voice.callable, false);
    assert.equal(voice.surface, null);
  });
});

describe("providers: task 48 — keys load from a 0600 env file, values never printed", () => {
  test("default path constant is /etc/metaos/agent.env (not read here)", () => {
    assert.equal(AGENT_ENV_PATH, "/etc/metaos/agent.env");
  });

  test("FAKE env file in /tmp parses KEY=VALUE, reports mode, names only", () => {
    const { dir, file } = fakeEnvFile(
      "# machine secrets (fake)\nSPARK_API_KEY=FAKE-FROM-FILE-ONLY\nMETAOS_NOTIFY_WEBHOOK=\n",
    );
    try {
      const loaded = loadAgentEnvFile(file);
      assert.equal(loaded.path, file);
      assert.equal(loaded.values.SPARK_API_KEY, "FAKE-FROM-FILE-ONLY");
      assert.equal(loaded.values.METAOS_NOTIFY_WEBHOOK, "");
      assert.match(loaded.mode || "", /^[0-7]+$/);
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });

  test("missing file reports missing instead of throwing", () => {
    const loaded = loadAgentEnvFile(path.join(tmpdir(), "no-such-agent-env-xyz"));
    assert.equal(loaded.missing, true);
    assert.deepEqual(loaded.values, {});
  });

  test("env beats file; file is the fallback", () => {
    assert.equal(getKey("SPARK_API_KEY", { env: { SPARK_API_KEY: "FROMENV" }, fileValues: { SPARK_API_KEY: "FROMFILE" } }).value, "FROMENV");
    const back = getKey("SPARK_API_KEY", { env: NOKEY_ENV, fileValues: { SPARK_API_KEY: "FROMFILE" } });
    assert.equal(back.value, "FROMFILE");
    assert.equal(back.source, "file");
  });
});

describe("providers: task 49 — missing key refuses BEFORE any network", () => {
  test("refusal names the path and the key, and the fetch double is never called", async () => {
    let fetched = 0;
    const fakeFetch = async () => {
      fetched += 1;
      return { ok: true };
    };
    let error = null;
    try {
      // The production order: resolve (key gate) FIRST, fetch only after.
      resolveProvider("muse-spark-1.3", { env: NOKEY_ENV, fileValues: EMPTY_FILE_VALUES, envFile: "/tmp/fake-agent.env" });
      await fakeFetch("https://api.meta.ai/v1/chat/completions");
    } catch (e) {
      error = e;
    }
    assert.ok(error, "expected a refusal");
    assert.equal(error.code, "NO_KEY");
    assert.match(error.message, /SPARK_API_KEY/);
    assert.match(error.message, /\/tmp\/fake-agent\.env/);
    assert.equal(fetched, 0, "network must stay untouched when the key is missing");
  });
});

describe("providers: tasks 50-51 — per-job and per-day caps in USD", () => {
  test("a budget inside both caps passes", () => {
    const ok = assertBudget({ jobBudgetUsd: 0.1, jobCapUsd: DEFAULT_JOB_CAP_USD, daySpentUsd: 0.2, dayCapUsd: DEFAULT_DAY_CAP_USD });
    assert.equal(ok.ok, true);
  });

  test("zero budget refuses naming the cap (BUDGET_ZERO)", () => {
    for (const bad of [0, -1, NaN, "free"]) {
      assert.throws(
        () => assertBudget({ jobBudgetUsd: bad, jobCapUsd: DEFAULT_JOB_CAP_USD }),
        (e) => e.code === "BUDGET_ZERO" && /\$0\.25/.test(e.message),
        `budget ${String(bad)}`,
      );
    }
  });

  test("over-cap job refuses naming the per-job cap (OVER_JOB_CAP)", () => {
    assert.throws(
      () => assertBudget({ jobBudgetUsd: 0.26, jobCapUsd: DEFAULT_JOB_CAP_USD }),
      (e) => e.code === "OVER_JOB_CAP" && /per-job cap \$0\.25/.test(e.message),
    );
  });

  test("day overflow refuses naming the daily cap (OVER_DAY_CAP)", () => {
    assert.throws(
      () => assertBudget({ jobBudgetUsd: 0.2, daySpentUsd: 0.9, dayCapUsd: DEFAULT_DAY_CAP_USD }),
      (e) => e.code === "OVER_DAY_CAP" && /daily cap \$1\.00/.test(e.message),
    );
  });

  test("day ledger persists across reads in a tmp file", () => {
    const dir = mkdtempSync(path.join(tmpdir(), "day-spend-"));
    const ledger = path.join(dir, "spend.json");
    try {
      assert.deepEqual(readDaySpend(ledger, "2026-11-04"), { date: "2026-11-04", spentUsd: 0, calls: 0 });
      addDaySpend(ledger, 0.004, "2026-11-04");
      addDaySpend(ledger, 0.002, "2026-11-04");
      const cur = readDaySpend(ledger, "2026-11-04");
      assert.equal(cur.calls, 2);
      assert.ok(Math.abs(cur.spentUsd - 0.006) < 1e-9);
      assert.throws(() => assertBudget({ jobBudgetUsd: 1.0, daySpentUsd: cur.spentUsd, dayCapUsd: DEFAULT_DAY_CAP_USD }), /OVER_/);
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });
});

describe("providers: task 52 — preflight estimates only when the provider exposes a rate", () => {
  test("Spark (rate card $1.25/M in, $4.25/M out) yields a numeric USD estimate", () => {
    const est = estimateCost("muse-spark-1.3", { prompt_tokens: 8000, completion_tokens: 2000 });
    assert.equal(est.unknown, false);
    assert.equal(est.unit, "USD");
    // 8000/1e6*1.25 + 2000/1e6*4.25 = 0.01 + 0.0085 = 0.0185
    assert.ok(Math.abs(est.usd - 0.0185) < 1e-9);
  });

  test("Wonder / SAM / Image / Voice report unknown, never invented", () => {
    for (const id of ["muse-wonder-1.0", "sam-3.1", "muse-image-1.0", "muse-voice-transcribe-1.0"]) {
      const est = estimateCost(id, { prompt_tokens: 8000, completion_tokens: 2000 });
      assert.equal(est.usd, null, id);
      assert.equal(est.unknown, true, id);
      assert.match(est.reason, /never invented/);
    }
  });
});

describe("providers: task 53 — model-call timeout with a named error", () => {
  test("a stub slower than the timeout fails MODEL_TIMEOUT naming the ms", async () => {
    const slow = () => new Promise((r) => setTimeout(() => r("late"), 50));
    await assert.rejects(slow && callWithTimeout(slow, 10), (e) => {
      assert.equal(e.code, "MODEL_TIMEOUT");
      assert.match(e.message, /10ms/);
      return true;
    });
  });

  test("a fast stub resolves inside the timeout", async () => {
    const fast = async () => "early";
    assert.equal(await callWithTimeout(fast, 1000), "early");
  });
});

describe("providers: task 54 — one retry on transient, then the provider code", () => {
  test("500-then-ok succeeds on the second attempt", async () => {
    let n = 0;
    const flaky = async () => {
      n += 1;
      if (n === 1) throw Object.assign(new Error("boom"), { status: 500 });
      return "recovered";
    };
    const { result, attempts } = await callWithRetry(flaky, { retries: 1 });
    assert.equal(result, "recovered");
    assert.equal(attempts, 2);
  });

  test("always-500 fails carrying the provider status", async () => {
    let n = 0;
    const down = async () => {
      n += 1;
      throw Object.assign(new Error("still down"), { status: 500 });
    };
    await assert.rejects(callWithRetry(down, { retries: 1 }), (e) => {
      assert.equal(e.status, 500);
      assert.equal(n, 2, "exactly one retry: two attempts total");
      return true;
    });
  });

  test("a 4xx is not transient: no retry", async () => {
    let n = 0;
    const bad = async () => {
      n += 1;
      throw Object.assign(new Error("bad request"), { status: 400 });
    };
    assert.equal(isTransient(Object.assign(new Error("x"), { status: 400 })), false);
    assert.equal(isTransient(Object.assign(new Error("x"), { status: 429 })), true);
    await assert.rejects(callWithRetry(bad, { retries: 1 }));
    assert.equal(n, 1);
  });
});

describe("providers: task 55 — secrets redacted from every error and log", () => {
  test("a planted fake key value is absent from redacted errors and logs", () => {
    const dir = mkdtempSync(path.join(tmpdir(), "redact-"));
    try {
      // Failing paths that would otherwise echo the value back.
      const rawError = `model HTTP 500: key ${PLANTED} rejected`;
      const rawLog = JSON.stringify({ keyEnv: "SPARK_API_KEY", detail: `tried ${PLANTED} twice` });
      const cleanError = redactSecrets(rawError, [PLANTED]);
      const cleanLog = redactSecrets(rawLog, [PLANTED]);
      const logFile = path.join(dir, "run.log");
      writeFileSync(logFile, cleanError + "\n" + cleanLog + "\n");
      const onDisk = readFileSync(logFile, "utf8");
      assert.ok(!onDisk.includes(PLANTED), "planted value must be absent from logs");
      assert.match(onDisk, /SPARK_API_KEY/, "the key NAME stays for operators");
      assert.match(onDisk, /\[REDACTED\]/);
      // Pattern shapes are scrubbed even when not pre-registered.
      assert.ok(!redactSecrets("Authorization: Bearer ABCDEFGH12345678ijkl", []).includes("ABCDEFGH12345678ijkl"));
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });
});

describe("providers: task 56 — token usage per run, summed in the receipt", () => {
  test("three stub runs sum prompt/completion tokens and receipt costs", () => {
    const dir = mkdtempSync(path.join(tmpdir(), "receipts-"));
    try {
      const runs = [
        stubCall("muse-spark-1.3", "assess frame one"),
        stubCall("muse-spark-1.3", "second reading of the same frame"),
        stubCall("muse-spark-1.3", "judge the two readings"),
      ];
      const total = sumUsage(runs.map((r) => r.usage));
      assert.equal(total.calls, 3);
      assert.ok(total.prompt_tokens > 0 && total.completion_tokens === 48);
      const receiptPath = path.join(dir, "model_receipts.jsonl");
      for (const r of runs) {
        writeReceiptLine(receiptPath, buildReceipt({ model: r.model, transport: r.transport, usage: r.usage }));
      }
      writeReceiptLine(
        receiptPath,
        buildReceipt({ kind: "run-total", model: "muse-spark-1.3", transport: "stub", usage: total }),
      );
      const lines = readFileSync(receiptPath, "utf8").trim().split("\n").map((l) => JSON.parse(l));
      assert.equal(lines.length, 4);
      assert.ok(lines.every((l) => l.transport === "stub"));
      const last = lines[lines.length - 1];
      assert.equal(last.kind, "run-total");
      assert.deepEqual(last.usage, { ...total });
      assert.ok(typeof last.est_cost_usd === "number");
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });
});

describe("providers: tasks 57-58 — --probe gating (no real call without --spend)", () => {
  function scrubbedEnv(extra = {}) {
    const env = { ...process.env, ...extra };
    delete env.SPARK_API_KEY; // no key on the box; both refusals must hold
    return env;
  }

  test("--probe WITHOUT --spend refuses (exit 2) naming --spend, no network", () => {
    let out = "";
    let code = 0;
    try {
      execFileSync(process.execPath, [CLI, "--probe"], { env: scrubbedEnv(), encoding: "utf8", timeout: 30000 });
    } catch (e) {
      code = e.status;
      out = (e.stderr || "") + (e.stdout || "");
    }
    assert.equal(code, 2);
    assert.match(out, /--spend/);
  });

  test("--probe --spend WITHOUT a key refuses (exit 4) naming path + key, no network", () => {
    const dir = mkdtempSync(path.join(tmpdir(), "probe-"));
    const empty = path.join(dir, "agent.env");
    writeFileSync(empty, "# fake empty machine env\nSPARK_API_KEY=\n");
    try {
      let out = "";
      let code = 0;
      try {
        execFileSync(process.execPath, [CLI, "--probe", "--spend", "--env-file", empty], {
          env: scrubbedEnv(),
          encoding: "utf8",
          timeout: 30000,
        });
      } catch (e) {
        code = e.status;
        out = (e.stderr || "") + (e.stdout || "");
      }
      assert.equal(code, 4);
      assert.match(out, /SPARK_API_KEY/);
      assert.match(out, new RegExp(empty.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });
});

describe("providers: tasks 59-60 — deterministic stub, default when no key", () => {
  test("stub is deterministic per input", () => {
    const a = stubCall("muse-spark-1.3", "same prompt");
    const b = stubCall("muse-spark-1.3", "same prompt");
    assert.deepEqual(a, b);
    const c = stubCall("muse-spark-1.3", "different prompt");
    assert.notEqual(a.text, c.text);
    assert.equal(a.transport, "stub");
  });

  test("no key anywhere resolves to the stub transport labeled `stub`", () => {
    const t = resolveTransport({ env: NOKEY_ENV, fileValues: EMPTY_FILE_VALUES });
    assert.equal(t.mode, "stub");
    assert.equal(t.label, "stub");
  });

  test("a present key resolves to live (label `live`) without printing it", () => {
    const t = resolveTransport({ env: { SPARK_API_KEY: PLANTED }, fileValues: EMPTY_FILE_VALUES });
    assert.equal(t.mode, "live");
    assert.equal(t.label, "live");
    assert.ok(!t.reason.includes(PLANTED), "transport reason names the source, never the value");
  });
});

describe("providers: task 61 — CI mode performs zero real network calls", () => {
  test("CI=1 forces the stub even when a key is present", () => {
    assert.equal(isCiMode({ CI: "1" }), true);
    const t = resolveTransport({ env: { CI: "1", SPARK_API_KEY: PLANTED } });
    assert.equal(t.mode, "stub");
  });

  test("the stub transport throws on non-localhost instead of dialing it", () => {
    assert.throws(() => stubFetch("https://api.meta.ai/v1/chat/completions"), (e) => {
      assert.equal(e.code, "STUB_NO_NETWORK");
      return true;
    });
    // Loopback is the only address the stub tolerates, and it uses no socket.
    assert.deepEqual(stubFetch("http://127.0.0.1:18935/health"), { stubbed: true, host: "127.0.0.1" });
  });
});

describe("providers: task 62 — demo costs total under $1 (stub estimates, honestly labeled)", () => {
  test("three demo jobs estimate below $1 at Spark rates", () => {
    const jobs = [
      ["assess", stubCall("muse-spark-1.3", "demo job 1: assess one frame")],
      ["second-read", stubCall("muse-spark-1.3", "demo job 2: independent second reading")],
      ["judge", stubCall("muse-spark-1.3", "demo job 3: judge the two readings")],
    ];
    let total = 0;
    for (const [, r] of jobs) {
      const est = estimateCost("muse-spark-1.3", r.usage);
      assert.equal(est.unknown, false);
      total += est.usd;
    }
    assert.ok(total < 1.0, `demo total $${total} must stay under $1`);
  });
});

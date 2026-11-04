# R2-T3 Section B — `metaosd` agent daemon (tasks 25–46)

Worktree `/tmp/agent-r2-t3`, branch `agent-r2-t3` (base `047c1f16`).
No branch switches, no commits, no merge/push, no QEMU, no paid calls.
Secret values never printed (key/env names and paths only).

## Files created (ONLY these — no edits to any existing file)

- NEW `os-build/iso/payload-agent/metaosd.mjs` (826 lines) — the daemon;
  node stdlib only (`http/fs/path/os/child_process/crypto/url`).
- NEW `server/queue/metaosd_store.mjs` (367 lines) — durable file store,
  schema-driven validator, HMAC receipt chain; imported by the daemon
  and the tests (single copy of persistence/verify logic).
- NEW `server/queue/daemon.test.mjs` (338 lines) — `node --test`
  suite, 21 tests, stdlib only.
- NEW `agents/job.schema.json` (61 lines) — authorized by task 27:
  `agents/submit.mjs` has NO schema (only imperative `validateJob`,
  `agents/submit.mjs:26-50`, `ID_PATTERN` at `:24`); this file is the
  single copy, read at runtime by daemon + store, never duplicated.
- THIS file `os-build/lanes/R2_T3_B.md` — findings.

No unit file was created beside the daemon: sibling payload dirs
(`os-build/iso/payload-apps/`, `os-build/iso/payload-theme/`) contain
**no** unit files, so per the lane order the systemd unit is documented
inline below (modeled on the existing `agent-layer/units/oc2-queue.service`
shape) instead of inventing a payload-agent unit format.

Untouched as ordered: `board/*`, `bus.html`, app pages,
`os-build/face/*`, `os-build/identity/*`, `provision.sh`, image units,
plymouth, os-release writers, `server/queue/queue_service.py`
(HTTP shape unbroken — not even read for borrowing, only for the
justification below), `agents/jobs.mjs|runtime.mjs|submit.mjs`.

## Why `metaosd_store.mjs` instead of reusing `queue_service.py`

`queue_service.py` + `server/queue/trio_store.py` is the Trio service on
`:8935`: Upstash-Redis (or local-SQLite FALLBACK) holding **trio-assessment
v1 envelopes** (base64 JPEG frames, byteLength/sha256 verification,
`queue_service.py:95-99`, namespace `trio_store.py:34-36`). It cannot hold
generic agent jobs `{id, agent, input, budget, timeout, dry-run}`, and its
HTTP shape must not break. So the daemon persists here: one JSON record
per job under `jobs/<id>.json`, atomic tmp+rename writes, in a data dir
outside the git tree. Nothing in `queue_service.py` was modified
(`git status` clean for it).

## Data dir (coordinated with Section A)

`os-build/lanes/R2_T3_A.md` landed mid-lane and picks
`$BUS_DATA_DIR`, else `$METAOS_STATE/bus`, else
`~/.local/state/metaos/bus` (`R2_T3_A.md:102-110`). The daemon uses the
same scheme with its own leaf: `--data`, else `$METAOSD_DATA`, else
`$METAOS_STATE/metaosd`, else `~/.local/state/metaos/metaosd`
(`metaosd_store.mjs:24-29`). Same root convention, no collision
(`bus/` vs `metaosd/`), both outside the git tree by construction.
Layout: `jobs/<id>.json` records, `runs/<id>/` per-run dirs,
`idem.json` idempotency map, `chain.jsonl` receipt chain,
`receipt.key` (0600), `metaosd.lock`.

## Endpoint list (`metaosd.mjs`, all `127.0.0.1`-only)

- `GET /health` → `{ok, service, version, host, port, dataDir,
  writable, uptimeMs, queueDepth, oldestJobAgeMs,
  workers:{size, busy:[ids], perAgent:{agent:n}}, agentCap,
  store:"file", receiptKey:bool}` (presence only — the key is never printed)
- `POST /jobs` (optional `Idempotency-Key` header) → `201 {id}` /
  `200 {id, existing:true}` / `400 {error, errors[]}` (unknown fields
  named) / `409 {error}` (duplicate id) / `429 {error, agent, cap}`
- `GET /jobs?agent=&status=&since=&until=` → `{jobs:[snapshot], count}`
- `GET /jobs/:id` → full run record; `GET /jobs/:id/status[?waitMs=N]`
  → poll snapshot (long-poll to 30 s); `GET /jobs/:id/events` → SSE
- `POST /jobs/:id/cancel` → queued→`cancelled`, running→`cancelling`
  then `cancelled`; record stays
- `POST /jobs/:id/retry` → requeue within `maxAttempts`, else 409 naming it
- `GET /jobs/:id/receipt` → the job's HMAC receipt
- `GET /verify?job=ID` → `{ok, job, hmac}` / `409 {ok:false, error}` /
  `400` refusing without a key, naming `keyPath`
- Offline (no daemon): `node metaosd.mjs verify --data DIR --job ID`,
  `node metaosd.mjs verify-chain --data DIR`

## Status poll/stream contract (task 44) + shape

Poll: `GET /jobs/:id/status` returns the snapshot; `?waitMs=N`
(0–30000) long-polls until the record changes or N ms elapse — clients
poll with `waitMs=10000` in a loop, no busy-spin. Stream:
`GET /jobs/:id/events` is `text/event-stream`, first event is the current
snapshot, one `data:` JSON event per record change; dropping the client
ends only the stream (proven: the (26) job below was submitted on a raw
socket destroyed before any response was read). Snapshot shape:

```
{id, agent, status, attempt, attempts:[{n, startedAt, endedAt, exit,
 signal, state, backoffWaitedMs, timeoutMs?, error?, note?}],
 startedAt, endedAt, exit, spawned, command, artifacts,
 artifactsRelativeTo, retry, receipt, restarted, updatedAt}
```

`status` ∈ `queued|running|succeeded|failed|timeout|cancelled|dryrun`.

## Task ticks + pasted proof (one command+output per claim)

Daemon started as: `node os-build/iso/payload-agent/metaosd.mjs --port
18940 --data /tmp/metaosd-proof --workers 2 --agent-cap 1`
(`--data` pointed at `/tmp` for the proofs; the default stays
`$METAOS_STATE/metaosd` / `~/.local/state/metaos/metaosd`).

### (25) Start on 18940 + GET /health; loopback-only bind

```
$ curl -s http://127.0.0.1:18940/health
{"ok":true,"service":"metaosd","version":"0.1.0-r2t3","host":"127.0.0.1","port":18940,
 "dataDir":"/tmp/metaosd-proof","writable":true,"uptimeMs":4935,"queueDepth":0,
 "oldestJobAgeMs":null,"workers":{"size":2,"busy":[],"perAgent":{}},"agentCap":1,
 "store":"file","receiptKey":false}
$ lsof -nP -iTCP:18940 -sTCP:LISTEN
node  11543 test  14u  IPv4  TCP 127.0.0.1:18940 (LISTEN)
```

One row, `127.0.0.1:18940` only — no `0.0.0.0`/`::`. The bind host is a
`HOST = "127.0.0.1"` constant (`metaosd.mjs:34`), not a flag.

### (26) Survive client disconnect mid-job

Raw socket: POST submitted, socket destroyed ~50 ms later, response never
read. The job still ran queued → running → succeeded; its artifact proves
the child ran to completion:

```
$ node -e '... s.write(req); setTimeout(() => s.destroy(), 50); ...'
client dropped (exit 0)
$ curl -s http://127.0.0.1:18940/jobs/drop-client-1/status   # polled to terminal
{"id":"drop-client-1",...,"status":"succeeded",...,"spawned":true,...}
$ cat /tmp/metaosd-proof/runs/drop-client-1/survived.txt
client went away
```

HTTP handling is detached from job execution (`metaosd.mjs` `readBody`
`close` path + `pump()`), so a dead client touches nothing.

### (27) Job schema `{id, agent, input, budget, timeout, dry-run}`

`agents/submit.mjs` has no schema — only `validateJob` (`:26-50`) and
`ID_PATTERN` (`:24`) — so `agents/job.schema.json` was created
(`additionalProperties:false` top level and inside `budget`; retry policy
lives in `budget{maxAttempts, backoffMs}` so the top level stays exactly
the six fields). Shared by reference: `metaosd_store.mjs:32-45`
(`loadSchema`/`schemaPath`) and consumed generically by
`validateAgainstSchema` (`:54-119`); `daemon.test.mjs:29` passes the path
explicitly. `grep -rn job.schema` shows references only, no second copy.

### (28) Unknown fields refused, naming them

```
$ curl -s -X POST .../jobs -d '{"agent":"a1","bogusField":1}'
{"error":"refused job: unknown field \"bogusField\"","errors":["unknown field \"bogusField\""]}
$ curl -s -X POST .../jobs -d '{"agent":"a1","budget":{"warpSpeed":9}}'
{"error":"refused job: unknown budget field \"warpSpeed\"","errors":["unknown budget field \"warpSpeed\""]}
```

### (29) Durable queue across `kill -9` + restart

Slow job submitted, daemon `kill -9`'d mid-run (port dead, `curl
exit=7`), restarted on the same port+dir:

```
metaosd: removed stale lock /tmp/metaosd-proof/metaosd.lock (pid 11543 not running, startedAt 2026-11-04T11:56:44.906Z)
metaosd: listening on 127.0.0.1:18940 dataDir=/tmp/metaosd-proof workers=2 agentCap=1 jobs=10 requeued=1
```

Job completed on attempt 2; first attempt honestly marked `orphaned`:

```
restarted: True
attempts: [(1, 'orphaned', 'daemon died mid-attempt; requeued on restart'), (2, 'succeeded', None)]
artifacts: ['after-restart.txt', 'output-attempt1.log', 'output-attempt2.log']
```

Queued jobs survive as files; `running` records are requeued with attempts
preserved (`metaosd.mjs` serve-block). Second kill-9 cycle re-proved with
the final code (`requeued=1`, orphan note above).

### (30) Worker pool configurable size + visible busy state

`--workers 2` (else `$METAOSD_WORKERS`, else 2); health shows
`"workers":{"size":2,"busy":["job-mw22aq2p-…","job-mw22aqhr-…"],
"perAgent":{"solo":1,"w2":1}}` (full proof in (36)/(37) output).

### (31) Per-job timeout kills child + records timeout failure

```
$ curl -s -X POST .../jobs -d '{"agent":"tm","input":{"sleepMs":30000},"timeout":300,...}'
{"id":"job-mw22bf19-0d7c3d13"}
$ curl -s .../jobs/job-mw22bf19-0d7c3d13/status
{...,"status":"timeout",
 "attempts":[{"n":1,...,"timeoutMs":300,...,"signal":"SIGTERM","state":"timeout"}],
 "exit":{"code":null,"signal":"SIGTERM","timeoutMs":300},...}
```

SIGTERM then SIGKILL after 800 ms (`launch`, `metaosd.mjs`).

### (32) Cancel by id; cancelled job leaves a record

```
$ curl -s -X POST .../jobs/job-mw22bf1r-f2f77c2f/cancel
{"id":"job-mw22bf1r-f2f77c2f","status":"cancelling"}
$ curl -s .../jobs/job-mw22bf1r-f2f77c2f/status
{...,"status":"cancelled",
 "attempts":[{...,"signal":"SIGTERM","state":"cancelled"}],...,
 "receipt":"e21a94fd..."}
```

Record + receipt persist (`cancelled` is terminal).

### (33) Retry with max attempts + visible backoff

`budget:{maxAttempts:3, backoffMs:500}` on an `exitCode:3` job:

```
"status":"failed","attempt":3,
"attempts":[{...,"state":"failed"},
 {"n":2,...,"backoffWaitedMs":500,...},
 {"n":3,...,"backoffWaitedMs":1000,...}]
$ curl -s -w '\nhttp=%{http_code}\n' -X POST .../retry
{"error":"job job-mw22bnfg-c223dd3c exhausted maxAttempts=3","maxAttempts":3}
http=409
```

Exponential `backoffMs * 2^(n-1)` visible per attempt; manual retry
requeues within the cap (`POST /jobs/:id/retry` → `{status:"queued",
backoffMs}`), else 409 naming `maxAttempts`.

### (34) Idempotency by request key

```
$ curl -s -X POST .../jobs -H 'Idempotency-Key: req-proof-1' -d '{"agent":"idem",...}'
{"id":"job-mw22akhb-05761ea4"}
$ curl -s -X POST .../jobs -H 'Idempotency-Key: req-proof-1' -d '{"agent":"idem",...}'
{"id":"job-mw22akhb-05761ea4","existing":true}
$ ls /tmp/metaosd-proof/jobs/ | grep -c job-mw22akhb-05761ea4
1
```

Key→id map persisted in `idem.json` (`loadIdem`/`saveIdem`), so the
double-submit collapses across restarts too.

### (35) Dry-run writes record, calls no model (prove no spawn)

```
$ curl -s -X POST .../jobs -d '{"agent":"dry","dry-run":true}'
{"id":"job-mw22aki4-77597860","dryRun":true}
$ curl -s .../jobs/job-mw22aki4-77597860
{"id":"job-mw22aki4-77597860",...,"status":"dryrun",...,
 "spawned":false,"command":null,"artifacts":["record.json"],
 "artifactsRelativeTo":"runs/job-mw22aki4-77597860",...}
```

`spawned:false`, `command:null`, zero attempts; the executor path is
skipped entirely (and the non-dry executor itself is a zero-network local
stub — `STUB_SRC` does no I/O except its run dir).

### (36) Per-agent concurrency cap + named refusal

`--agent-cap 1`, one `solo` job running:

```
$ curl -s -w '\nhttp=%{http_code}\n' -X POST .../jobs -d '{"agent":"solo","input":{}}'
{"error":"agent-concurrency-cap: agent \"solo\" already runs 1 job(s)","agent":"solo","cap":1}
http=429
```

### (37) Queue depth + oldest-job age in /health

With 2 workers busy and 1 queued:

```
"queueDepth":1,"oldestJobAgeMs":529,
"workers":{"size":2,"busy":["job-mw22aq2p-11b89def","job-mw22aqhr-7cfc00ba"],
"perAgent":{"solo":1,"w2":1}}
```

`oldestJobAgeMs:null` when the queue is empty.

### (38) Run record per job (start/end/exit/artifacts)

Every snapshot carries `startedAt/endedAt/exit(command)/attempts[]`;
e.g. the timeout job in (31) shows start, end, `exit:{code,signal,
timeoutMs}`, and per-attempt detail.

### (39) Artifact paths relative to run dir + documented

`artifactsRelativeTo:"runs/<id>"`, `artifacts` are bare names scanned
from the run dir on terminal states (`scanArtifacts`, receipt included by
name only after write):

```
$ ls /tmp/metaosd-proof/runs/job-mw22c9el-31523168/
after-restart.txt  output-attempt1.log  output-attempt2.log  receipt.json
"artifacts":["after-restart.txt","output-attempt1.log","output-attempt2.log"]
```

### (40) Receipt per run + verify catches 1 tampered byte

Live verify OK, then 1 byte flipped in a **copy** (real chain unpoisoned):

```
$ curl -s "http://127.0.0.1:18940/verify?job=job-mw22bnfg-c223dd3c"
{"ok":true,"job":"job-mw22bnfg-c223dd3c","hmac":"0415cbbb..."}
$ diff /tmp/metaosd-proof/runs/.../receipt.json /tmp/metaosd-tamper/runs/.../receipt.json
<   "hmac": "0415cbbbc7e9af84a1bcb3d495933bbc5276d1a60a8da2989185682c799a60f1"
>   "hmac": "0405cbbbc7e9af84a1bcb3d495933bbc5276d1a60a8da2989185682c799a60f1"
$ node .../metaosd.mjs verify --data /tmp/metaosd-tamper --job job-mw22bnfg-c223dd3c
verify: FAIL job=job-mw22bnfg-c223dd3c: hmac mismatch: receipt was modified
exit=1
```

`receipt_validate.py` was **not** reused, by design: it validates
model-usage JSONL lines (`model/surface/latency_ms/est_cost_usd` with a
Spark-billing rule, `receipt_validate.py:27-63`) — a different schema from
HMAC-chained job receipts, with no key/chain concept. Job receipts carry
their own verifier (`verifyReceiptObject`/`verifyChain` in
`metaosd_store.mjs` + `metaosd.mjs verify[-chain]`). The `hmac` uses
`timingSafeEqual`.

### (41) Receipt chain verifiable offline with one command

```
$ node /tmp/agent-r2-t3/os-build/iso/payload-agent/metaosd.mjs verify-chain --data /tmp/metaosd-proof
verify-chain: OK, 11 receipt(s) chained under /tmp/metaosd-proof
exit=0
```

Run twice: once with the daemon up (reads files directly, zero daemon
contact) and once with the daemon SIGTERM'd and the port closed (`(daemon
down)` + same `OK, 11 receipt(s)`). Each receipt binds `prev` = previous
`hmac`, genesis `GENESIS` (`finishReceipt`, `chainPrev`/`appendChain`).

### (42) Verify refuses without receipt key, naming key path

```
$ mv /tmp/metaosd-proof/receipt.key /tmp/metaosd-proof/receipt.key.aside
$ curl -s "http://127.0.0.1:18940/verify?job=job-mw22bnfg-c223dd3c"
{"error":"refusing to verify without a receipt key: no receipt key at /tmp/metaosd-proof/receipt.key",
 "keyPath":"/tmp/metaosd-proof/receipt.key"}
$ node .../metaosd.mjs verify-chain --data /tmp/metaosd-nokey
verify-chain: FAIL: no receipt key at /tmp/metaosd-nokey/receipt.key (refusing to verify without it)
exit=1
```

Key restored afterwards; chain re-verified OK (9 receipts at that point).
Verify paths never auto-create a key (`readKey` only; creation happens
solely on receipt write via `loadOrCreateKey`, mode 0600).

### (43) Job list filtering agent/status/date

```
$ curl -s '.../jobs?agent=rt'                        # → {"jobs":[...1 failed...],"count":1}
$ curl -s '.../jobs?status=succeeded'                # → 5 jobs, all "status":"succeeded"
$ curl -s '.../jobs?since=2026-11-04T11:57:00.000Z&status=failed'  # → the rt job
$ curl -s '.../jobs?since=2999-01-01T00:00:00.000Z'  # → {"jobs":[],"count":0}
```

Bad `since`/`until` → `400 {error:"bad ?since date: ..."}` naming the param.

### (44) Status stream-or-poll contract

Documented above (contract + shape). Live SSE check on a terminal job:

```
$ curl -s -m 5 -N .../jobs/job-mw22c9el-31523168/events | head -c 600
data: {"id":"job-mw22c9el-31523168","agent":"persist","status":"succeeded","attempt":2,...}
```

### (45) Refuse start when data dir not writable, naming it

```
$ mkdir -p /tmp/metaosd-ro && chmod 555 /tmp/metaosd-ro
$ node os-build/iso/payload-agent/metaosd.mjs --port 18941 --data /tmp/metaosd-ro
metaosd: refusing to start: data dir not writable: /tmp/metaosd-ro (EACCES: permission denied, open '/tmp/metaosd-ro/.writable-probe-40712')
exit=2
```

Probe is a real write+unlink (`checkWritable`), not a permission-bit guess.

### (46) Clean stale locks on start, log what was removed

```
$ echo '{"pid":987654321,"startedAt":"2020-01-01T00:00:00.000Z"}' > /tmp/metaosd-locktest/metaosd.lock
$ node .../metaosd.mjs --port 18942 --data /tmp/metaosd-locktest --workers 1
metaosd: removed stale lock /tmp/metaosd-locktest/metaosd.lock (pid 987654321 not running, startedAt 2020-01-01T00:00:00.000Z)
metaosd: listening on 127.0.0.1:18942 dataDir=/tmp/metaosd-locktest workers=1 agentCap=1 jobs=0 requeued=0
```

Liveness is `kill(pid,0)`; a live holder refuses the start (`already
running (pid N)`), a dead one is unlinked and **reported** (`takeLock` →
return value logged). SIGTERM releases the lock (verified: lock file gone
after `kill $LPID`).

## Report-back

- Files created: `os-build/iso/payload-agent/metaosd.mjs`,
  `server/queue/metaosd_store.mjs`, `server/queue/daemon.test.mjs`,
  `agents/job.schema.json`, `os-build/lanes/R2_T3_B.md`. Zero edits to
  existing files.
- Endpoints: 12 listed above (health, submit, list, record, status,
  events, cancel, retry, receipt, verify + 2 offline CLI verbs).
- Tests: `node --test server/queue/daemon.test.mjs` → **21 pass, 0
  fail** (schema naming, idempotency incl. durable map, run-record +
  dry-run no-spawn, timeout, cancel, retry/backoff + 409, cap 429 +
  busy health, depth/age, filters, poll shape, 1-byte tamper, keyless
  refusal, stale/live locks, unwritable dir, atomic write). Re-ran green
  after the final code edits.
- Skips + why: no unit file beside the daemon (sibling payload dirs use
  none — unit documented inline below instead of inventing a format); no
  QEMU (lane ban); no model-backed execution (lane bans paid calls —
  executor is a zero-network local stub; `METAOSD_CMDS_FILE` maps agents
  to real commands in production); `receipt_validate.py` not reused
  (different receipt schema — documented in (40)); `submit.mjs` not
  wired to the schema (outside this lane's file list — cross-lane
  request below).
- No daemon left running (all proof daemons SIGTERM'd/kill-9'd, locks
  released, `/tmp/metaosd-*` residue removed); secrets never printed
  (only `receiptKey:true/false` presence and key paths).

## Cross-lane requests (file:line)

1. Section D / whoever owns `agents/submit.mjs`: adopt the schema —
   `agents/submit.mjs:26-50` (`validateJob`) and `:24` (`ID_PATTERN`)
   duplicate what `agents/job.schema.json` now defines once. Request:
   have `submit.mjs` import the schema file (or `metaosd_store.mjs`
   `validateAgainstSchema`) so the CLI and the daemon cannot drift.
2. Image/provision: to ship the daemon, install
   `os-build/iso/payload-agent/metaosd.mjs` + a unit (inline draft
   below) and set `METAOS_STATE` (else the default is
   `~/.local/state/metaos/metaosd`). Suggested unit, modeled on
   `agent-layer/units/oc2-queue.service:1-16`:
   `[Unit] Description=MetaOS agent daemon (metaosd :18940);
   [Service] Type=simple ExecStart=/usr/bin/node
   /usr/share/metaos/payload-agent/metaosd.mjs
   Environment=METAOS_STATE=/var/lib/metaos Restart=on-failure;
   [Install] WantedBy=default.target`. Owned outside this lane
   (provision.sh + image units are forbidden to this section).
3. Section A (bus, `:18935`): no conflict — daemon takes `:18940` and
   `$METAOS_STATE/metaosd` vs bus `$METAOS_STATE/bus`
   (`R2_T3_A.md:102-110`); both bind `127.0.0.1` only. No action, FYI only.
4. Pages/T4: if a desk page should surface jobs, poll
   `GET 127.0.0.1:18940/jobs/:id/status?waitMs=10000` (contract above) —
   do not add app-page code in this lane (forbidden paths).

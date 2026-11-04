# T3 REPORT — the agent pipeline inside the OS (2026-11-04)

Branch `agent-t3`, worktree `/tmp/agent-t3` (from main `9a2e87b2`). No QEMU
(`pgrep -f qemu` → nothing, exit 1). No paid calls: no key exists on this box
— `keyring.preflight` returns `refuse … no key configured:
SPARK_API_KEY is empty and no key file at /etc/metaos/agent.env`; every run
below used the local stub provider (127.0.0.1 only). No key/token value was
printed anywhere; `grep -riE "sk-[A-Za-z0-9]{20,}|SPARK_API_KEY=[A-Za-z0-9]" os-build/lanes/T3_*.md` → clean (only the bare env-var *name* in prose).

Work was executed by subagents per the brief (A–F in `T3_SECTION_<X>.md`,
committed alongside this report as evidence — the brief names `T3_REPORT.md`
as the lane's file; the section files and `T3_REVIEW.md` live in the same
lane-owned `os-build/lanes/` dir purely as audit trail for the claims below,
no other lane's paths affected); Section G below and the final
review are the lane lead's. Final review subagent read the whole diff last.

## A. What exists (→ T3_SECTION_A.md, 2026-11-04)

Seven units in `agent-layer/` (login, ask, code, health, watchdog, relay,
manifest) with autostart/timer conditions — see §1 of the section file. One
job's life (`agents/runtime.mjs`): submit → `jobs/<id>.job.json` → watchman
drain → `runs/<runId>/` workdir + `jobs/<id>.result.json` → ledger line in
`watchman.jsonl`. Submit refusals (`agents/submit.mjs`): unknown agent,
draft agent, bad envelope, duplicate id. Watchman watches `$STATE/jobs`,
writes result files + ledger lines; never receipts (a receipt = §D artifact).

- `meta-ask --list`: present, listed 23 live agents (past §6).
- Submitted a real `meta-coder` job, drained it, read `runs/<runId>/record.json` (paths in §7–8).
- Fail-without-record spots: sync-throw poll abort; claimed-wedge (claim at `watchman.mjs:173` precedes check at `:175`, claims never cleared); bare `|| true` swallow list in §10.
- Registry: 23 live, 1 draft (`imperium-patrol`, missing program).
- Key file: absent on this box (path `/etc/metaos/agent.env` expected, mode 600 when staged); env readers listed in §14.
- **Bug #1 (fixed):** `spawnAgent` dropped `repoRoot` — `repo:`-commands died `Cannot find module` (exit 1). Fix: `agents/runtime.mjs` + `agents/bridge.mjs:97` accept/thread `repoRoot`. Before/after + drain proof in §18; suites `agents-r11`+`watchman-retry`+`code100` 22/22 green.
- **Bug #2 (named, not fixed):** `agent_loop.mjs:400` main-guard fails under symlinked paths (this box: `/tmp → /private/tmp`) — agent exits 0 having done nothing (0-byte `output.log` proven). Suggested fix: `realpathSync` `isMainModule` pattern (as in `submit.mjs:84-91`).

## B. Submit path (→ T3_SECTION_B.md)

`agent-layer/meta-ask.py` rewritten (264→757 lines) + synced mirror
`iso/apps/agent-status/meta-ask.py` (differs by 1 line, enforced by test) + one
shared schema `agent-layer/job_schema.json` + `agent-layer/test_submit_path.py`
(**31 tests, OK, ~7s**). Refusals: unknown (lists 23 live), draft, empty,
duplicate (names the job), over-budget (names cap), off-schema by field name —
all exit 1 (table in §B); `--file/--job-file`, `--status/--jobs` (+`--json`,
parses), single-place `queue_address()`, dead queue fails in **0.107s** vs
closed port (<2s proven), no key/token in any output (grep proof), desktop-
voice messages (no tracebacks). Wire format unchanged (`POST {"app"}`-style
envelope, `r.ok`-compatible); board payload proven accepted. Three submit
ways documented with examples (§B-40).

## C. Queue and runner (→ T3_SECTION_C.md)

New `server/queue/run_queue.py` (Runner: submit/status/`run_once`/SIGTERM/
wall-clock/concurrency-2/proven-by-4-jobs/persistence/duplicate-impossible/
max-age/counts endpoint answering mid-run) + `stub_provider.py`
(`cost_usd: 0.0001` from provider response, never estimated) + 14-test suite
(**OK, ~19s**) + `os-build/iso/payload-agent/stage.sh` (0750/0700 modes proven
on scratch trees). Records: start/end ISO lines, agent+model+cost,
`prompt_hash`, input/output paths, atomic tmp+rename, confinement proven
(`invalid-world-path` live). Modes before→after on scratch: jobs 0755→0750,
runs 0755→0700. `patrol.py`: `paused_since` marker, one status line per paused
cycle. 50 existing patrol/orchestrator/crew tests still pass.

## D. Receipts (→ T3_SECTION_D.md; format doc `agents/RECEIPTS.md`)

New `server/queue/receipts.py` (writer + versioned verifier `VERIFIERS={1}`,
`verify-receipt` CLI, `wrap_run()`, `list`/`count`, `scan_for_secrets`) +
`receipt_validate.py` extended append-only + 8-test selftest (**8/8 OK**,
cleanup via add ### `verify-receipt verify` output above). Tamper proof:
1 flipped byte → `output_sha256 mismatch`, exit 1. Failed runs get failed
receipts with reason; real `kill -9` child → wrapper exit 0, `failed`
naming SIGKILL/exit 137. Receipt fields: job/agent/model/start/end/result/
cost/hash + `version: 1`, hash covers input+output bytes, OS build identity
from `identity/os-release` + `boot-manifest.json`, secret scan clean.

## E. Key handling (→ T3_SECTION_E.md)

New `server/queue/keyring.py` (single reader: arg → `METAOS_KEY_FILE` →
`/etc/metaos/agent.env`; restrictive-mode refuse; `KeyringError` = one line
`no key configured` + exact path) + `scan_runs_for_keys.py` (fragment args,
never reads key file; exit 0 clean / 1 found / 2 usage). Callers wired at 2
spots in `run_queue.py`; thinking jobs refused pre-start without key (proven),
dry-run builds prompt and stops (`dry` record, null cost, no spawn), fake
`/tmp` keys in tests, endpoint grep clean (127.0.0.1 only). Staged scratch
`ls -l`: jobs 750, runs 700, watchman 640, fake key 600 (owner = tester uid,
non-root noted).

## F. Page and board (→ T3_SECTION_F.md)

`agents.html` inventoried (14 value groups → fetch → endpoint → backend
file/line + one-table data sources). **Nothing invented was removed** (face
files are another lane's); 7 cross-lane requests with file+line (R1 receipts
strip, R2 cost field, R3 notices writer, R4 world link, R5 `/health`
`started_at`, R6 board refusal text at `board.html:33-34`, R7 metaosd
itself — **metaosd (:18940) does not exist in-repo**, so the page honestly
renders dead-backend states). Selftest `test_page_mapping.py`: **84/84**
against fixtures + live board.py/queue_service. No-external-request sweep
clean (127.0.0.1 only); refresh intervals honest (5s/5s/2s, quoted); no
fabricated screenshots — two headless-Chrome 1366x768 dead-state shots kept
out of repo.

## G. Proof and reporting

**131 — one stub job end to end** (re-runnable, lead-run 2026-11-04):
`python3 /tmp/t3-g/e2e.py /tmp/t3-g/f1` → `{"e2e-1": "ok"}`, `ELAPSED 0.05`,
wall 42.9ms, `cost_usd: 0.0001` (stub response). Artifacts:
`/tmp/t3-g/f1/jobs/e2e-1.job.json`, `…/e2e-1.result.json`,
`/tmp/t3-g/f1/runs/e2e-1-a1/record.json`, `…/output.log`,
`/tmp/t3-g/f1/runs/e2e-1-a1/receipt.json`, `/tmp/t3-g/f1/worlds/w.txt`,
`/tmp/t3-g/f1/prompts/p.txt`, `/tmp/t3-g/f1/watchman.jsonl`.
Receipt filed explicitly (the runner deliberately does NOT auto-file —
C/D contract, `receipts_slot` only):
`receipts.py … write --job e2e-1 --run e2e-1-a1 --agent e2e-agent --model
stub-model-1 --result ok --cost 0.0001 --cost-source provider …` →
`verify` → `OK … (v1 hash covers input+output)`, exit 0; receipt fields
`{version: 1, result: ok, cost_usd: 0.0001, cost_source: provider}`.
(Artifacts live in /tmp by design — no fixtures committed; the command
above reproduces them.)

**132 — real provider:** NOT RUN. No user authorization for spend exists, and
no key exists on this box; the dry path (`dry` status, null cost, no spawn)
is proven instead.

**133 — changed files** (`git diff --stat` + untracked, all in owned paths):
M `agent-layer/meta-ask.py`, M `iso/apps/agent-status/meta-ask.py`,
M `agents/runtime.mjs`, M `agents/bridge.mjs`, M `server/queue/patrol.py`,
M `server/queue/receipt_validate.py`; new `server/queue/run_queue.py` (lead:
per-job `dry_run` preservation, §139); new `agent-layer/job_schema.json`,
`agent-layer/test_submit_path.py`, `agents/RECEIPTS.md`,
`os-build/iso/payload-agent/stage.sh`, `server/queue/{run_queue,
stub_provider,keyring,receipts,scan_runs_for_keys,test_run_queue,
test_receipts,test_page_mapping}.py`, `T3_SECTION_{A..F}.md`, this report.

**134 — ownership:** every path above is inside `agents/`, `agent-layer/`,
`server/queue/`, `os-build/iso/payload-agent/`, `iso/apps/agent-status/`,
`os-build/lanes/`. Test litter outside owned paths (`runs/`, `memory/`,
`os-build/{aegis,handsfree,nervus}` modifications from suite drains) was
reverted/removed; `git status` shows lane files only.

**135 — no QEMU:** `pgrep -fl "qemu-system|qemu-img"` → empty (exit 1).

**136 — no paid call:** no key on box (preflight `refuse` quoted top);
all provider traffic hit the local stub; `grep -riE "api\.(openai|anthropic)"`
over new code + test outputs → 127.0.0.1/stub only (E §105–106).

**137 — report clean (values, not words):** strict value-pattern grep over
`T3_*.md` finds only scanner-needle/test prose, no secret values: `sk-`
appears bare (assert-absent lists, scan commands), `SPARK_API_KEY` as an
env-var *name*, `BEGIN PRIVATE KEY` inside `scan_for_secrets`' needle list
and the selftest's assert-absent list — each quoted with context in
`T3_REVIEW.md` (secret-scan section). No 20+-char `sk-` value, no `ghp_`,
no `Bearer <token>`, no `eyJ…`, no private-key block in the lane.

**138 — three stage-failure ways:** (1) per-job `dry_run` dropped by
submit()'s envelope (E's gate unreachable per-job); (2) no key provisioned
on the image → thinking jobs refuse loudly at stage; (3) metaosd :18940
absent → Agents page can only render dead-backend states.

**139 — cheapest fixed:** (1) — `submit()` now preserves a boolean
`dry_run` into the filed envelope. Proven live:
`{"d1": "dry"}` then `DRY-PER-JOB OK dry dry-run: prompt built, no model
call sent` (filed job carries `"dry_run": true`, drain returns `dry`).
Suites re-run green after the change: C 14 OK, D selftest 8 OK, B 31 OK,
`py_compile` clean.

**140 — the other two:** (2) needs image-lane key provisioning
(`/etc/metaos/agent.env`, mode 600, owner root — staging script must run as
root; E's `stage.sh` note covers the non-root limit); (3) needs the relay
lane to write metaosd or remap the page (F's R7).

**141 — branch/log:** `agent-t3`; single commit on this branch (this one —
verify with `git log --oneline -1 agent-t3`; the message title is "T3:
submit, queue, run, and receipt end to end on stub").

**142 — main untouched by me:** worktree branched from `9a2e87b2`; main has
since advanced to `292afdbe` by another lane's merge (not mine — I have
never checked out main, and `git diff main...HEAD --stat` shows the same 26
lane files only). No merge into or out of main from this lane.

**143 — judge paragraph:** "On this machine, submitting an agent job files
it to a local queue, a runner drains it with a stub model in about a tenth
of a second, and every run leaves a record — receipts are filed per run with
`receipts.py` and verify clean, including failed and dry runs. Real model
calls refuse loudly because no key is configured; nothing was spent."

**144 — paragraph check:** "files it" → `jobs/<id>.job.json` + burst test
(50 submits, 1 filed/49 duplicate-id) ✓; "tenth of a second" → wall
0.15/0.11/0.12s, ELAPSED 0.05/0.04/0.04, `wall_ms` 42.9/37.7/38.8 ✓;
"leaves a record" → `record.json` per run ✓; "receipts filed per run and
verify clean" → lead `write` + `verify OK (v1 hash covers input+output)`
exit 0 ✓; "failures" → exit-137 wrapper test + failed receipt with reason
✓; "dry runs" → per-job dry_run proof ✓; "refuse loudly" → preflight
sentence quoted ✓; "nothing spent" → $0.00 real (cost figures are stub
test data) ✓.

**145 — cost:** real spend **$0.00** (source: no key, no network — stub
`cost_usd: 0.0001`/run is fixture data from the stub response, not spend).

**146 — typical run:** 0.15s / 0.11s / 0.12s wall (`/usr/bin/time`), in-queue
ELAPSED 0.05/0.04/0.04s, `wall_ms` 42.9/37.7/38.8 — three lead-run stub jobs,
same command, fresh roots (`/tmp/t3-g/f1..f3`).

**147 — summary table:**

| capability | state | evidence |
|---|---|---|
| submit (CLI+file, refusals, exit codes, JSON) | works | B 31/31 |
| queue (persist, dedupe, age, status, SIGTERM, timeout) | works | C 14/14 |
| runner records (atomic, confined, costed, hashed prompts) | works | C 14/14 + lead e2e |
| receipts (write/verify/tamper/fail/crash/dry) | works | D selftest 8/8 + receipt-CLI discover tests 11/11 + lead `verify OK` exit 0 |
| key handling (single reader, refuse, dry, scan, fake-key tests) | works | E proofs + clean scan |
| page/board mapping (no inventions, dead-backend honest) | mapped, edits requested | F 84/84 |
| real-provider e2e | not run (no auth, no key) | preflight `refuse` |
| full agent e2e on image | not run (no QEMU) | dry paths only |

**148 — cross-lane requests (no fixes applied outside owned paths):**
D→C: 3-line receipt `write` call site in watchman drain (`watchman.mjs:331`
exact text in §D-72). D→page-lane: surface receipt verify state + count in
existing `GET /runs` (no new endpoint). F R1–R7 → page/relay lanes
(receipts strip, cost field, notices writer, world link, `/health`
`started_at`, board refusal text `board.html:33-34`, metaosd itself). E→trio
transport: apply the two `keyring` caller diffs (§E-91). A follow-ups:
`watchman.mjs:173` claim-before-check wedge + uncleared claims; gym callers
lack `repoRoot`; R12-010 stale coverage doc (fails identically stashed —
pre-existing, needs owner ack).

**149 — respected:** nothing outside owned paths edited (face/identity diffs
appear only as quoted requests).

**150 — next three sessions:** (1) wire D's `write` into the real watchman
drain path on an image with a key and run one keyed job under a $1 cap;
(2) implement F R1/R2 receipts strip so the Agents page shows verify state;
(3) write metaosd or remap the page, then re-run F's mapping against the
live :18940.

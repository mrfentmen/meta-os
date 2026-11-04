# R2-T3 REPORT — agent runtime, local bus, jobs, receipts

Branch `agent-r2-t3`, worktree `/tmp/agent-r2-t3` (main `047c1f16`). No merges,
no pushes, no QEMU, no paid calls, no secret values anywhere (names only).
Sections A–D by subagents (`R2_T3_A/B/C/D.md`); Section E below by the lane
lead; final reviewer subagent read the whole diff last.

## Section E — proof and handoff (lead-run, this machine, today)

- **81. Bus selftest:** `node server/bus.test.mjs` → `23 passed, 0 failed`,
  exit 0 (random port, send/list/search/pagination/presence/attachments/
  retention-500/2-client-SSE/50-parallel/auth/token-0600).
- **82. Two clients, one message:** live bus on 127.0.0.1:18971, two SSE
  readers on `rooms/general/events`, one POST → both printed `got-it`
  (`client0:got-it client1:got-it`, exit 0).
- **83. 50 parallel sends:** `xargs -P 10` × 50 POSTs → list returns 51
  messages (50 + the SSE probe), all stored. No lock errors in log.
- **84. Kill mid-job, resume:** `killme` (sleep 8s) submitted → `kill -9`
  daemon → restart log `removed stale lock … requeued=0`… then the job
  record shows attempt 1 `orphaned / daemon died mid-attempt; requeued on
  restart`, attempt 2 `succeeded` exit 0. Queued job resumes; running job
  re-runs from attempt boundary (documented, not claimed otherwise).
- **85. Cancel:** `cancel1` (sleep 30s) → `POST …/cancel` → `cancelled`,
  record kept: SIGTERM exit, `output-attempt1.log` artifact,
  `receipt.json` with HMAC chain (`prev` links killme's receipt).
- **86. Tamper:** 1 byte (`demo2`→`demoX`) in live receipt →
  `verify: FAIL job=cancel1: hmac mismatch: receipt was modified`, exit 1;
  restored → `verify: OK …`, exit 0.
- **87. Eval:** `node agents/eval.mjs` → `12/12 passed (score 100.0%)`,
  exit 0 (incl. bus post/read, queue retry, receipt tamper tasks).
- **88. Demo:** `node agents/demo.mjs --data-dir /tmp/r2t3-demo` → 3 jobs,
  3 code-0 receipts, `verify: OK: 3 jobs, 3 code-0 receipts`, all artifact
  paths printed; 2nd run → `reused 3`, same 6 job files, byte-identical
  receipts (no duplicate ids).
- **89. Real-call refusal, no key:** `node agents/providers.mjs --probe`
  → `probe refused: --probe makes a real billed call only with an explicit
  --spend flag… no network touched, no key read.` (`--probe --spend`
  without key → exit 4 naming path+key per Section C; real call not run —
  no authorization, no key on box).
- **90. Zero secrets:** `grep -rniE "sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|
  BEGIN [A-Z ]*PRIVATE KEY"` over new/edited lane files → no hits (exit 1);
  planted-value redaction proven in Section C (fake value absent, key NAME
  present).
- **91. Existing tests:** `agents/*.test.mjs` → 52 tests, 50 pass, 2 fail —
  BOTH pre-existing/environmental, proven identical with my changes stashed:
  `sandbox` "default network is none" (this Mac has real interfaces) and
  "timeout kills a stuck run" (60s sandbox timing). `board/board.test.mjs`
  fails: references deleted `relay/protocol-edge.json` (relay/ removed in
  main's tree changes; board/ untouched by this lane — cross-lane note
  below). New suites: bus 23/23, daemon 21/21, providers 28/28, r2t3_d 9/9.
  Page↔daemon mapping verified LIVE by the lead (R2_T3_F.md): the Section F
  subagent delivered no files, so its "84/84" is dropped — replaced by the
  lead's live endpoint-by-endpoint mapping, which found a real mismatch
  (page POSTs `{agent, orders}`; daemon refuses `unknown field "orders"`).
- **92. No daemon left running:** `pgrep -f metaosd.mjs` → exit 1,
  `pgrep -f server/bus.mjs` → exit 1 (both stopped after proofs; only port
  bindings held during the runs above).
- **93. Cross-lane requests (file:line, no edits made):**
  Page↔daemon contract (lead-verified live, R2_T3_F.md): page submit sends
  `{agent, orders}` (`os-build/face/agents.html:363`) but daemon schema
  (`agents/job.schema.json`) refuses `unknown field "orders"` — page must
  send `{agent, input:{text:…}}` or daemon aliases `orders`. Page panels
  (`/status`, `/agents`, `/runs`, `/halt`, `/resume`) vs daemon routes
  (`/health`, `/jobs`, `/jobs/:id/*`) — one side adopts the other.
  T4 pages: `js/site-chat.js:185-196` + `board/board.html:288-315` send
  `x-bus-token` on writes; board refusal text surfaced at `board.html:33-34`;
  receipts strip + verify state + count in Agents page (no endpoint);
  `/health` `started_at` (server/queue lane) or label machine uptime honestly;
  `board/board.test.mjs:58` still reads deleted `relay/protocol-edge.json`.
  Image/provision: install `os-build/iso/payload-agent/metaosd.mjs` + unit
  (inline draft in R2_T3_B.md); `os-build/face/provision.sh:480-483` port
  split (bus defaults 18935 = board port); `stage.sh:86-89` add `oc2-eval.*`
  to `--check`.
- **94. Guest-only proofs:** actual reboot persistence, systemd unit
  activation, greeter/desktop reading the bus, multi-boot data-dir survival.
- **95. Guest commands (for the booted image):**
  `BUS_PORT=18935 BUS_DATA_DIR=/var/lib/metaos/bus node /opt/metaos/server/bus.mjs & sleep 1; curl -s 127.0.0.1:18935/health` →
  expect `store:file,count≥0`; `METAOSD_DATA=/var/lib/metaos/metaosd
  node /opt/metaos/metaosd.mjs & sleep 1; curl -s 127.0.0.1:18940/health` →
  expect `queueDepth:0`; submit + `verify` per RUNBOOK.
- **96. Data dir outside git tree:** bus `$BUS_DATA_DIR`/`$METAOS_STATE`/`
  ~/.local/state/metaos/bus`, daemon `$METAOSD_DATA`/`$METAOS_STATE/metaosd`/
  `~/.local/...`, demo/eval under `/tmp` or `~/.local/state`; `.gitignore`
  += `bus-data/` + comment (only tree-touching default guard).
- **97. `.gitignore` diff:** 3 lines appended (above); nothing else touched.
- **98. No-network-device bus:** loopback-only bind proven (`lsof`/
  listener `127.0.0.1:18971`, SSE + POST all over 127.0.0.1); loopback needs
  no external device by design — device-absent proof needs the guest.
- **99. Reboot:** nothing here requires hand restarts — units are
  `agent-layer/units/oc2-*.service/.timer` + inline metaosd draft (image
  lane installs); on this host all state is files under the data dirs, no
  manual step after reboot beyond the units.
- **100. Next three steps:** (1) image lane installs metaosd + bus units,
  run the §95 guest commands; (2) T4 wires token + receipts strip into
  pages; (3) keyed low-cap smoke run, then turn on the daily eval gate.

## Task ticks

A 1-24 done (server/bus.mjs + 23/23 selftest; Upstash path env-gated off by
default, grep-clean; SSE proven 2-client; 50-send proven; 0600 token; retention
floor 500; migration + format documented). B 25-46 done (metaosd.mjs :18940,
durable store, kill-9 resume proven by lead above, timeout/cancel/retry/
idempotency/dry-run/caps/health/status-filter/poll-contract/unwritable-refusal/
stale-lock log; 21/21). C 47-62 done (provider inventory, /etc/metaos/agent.env
0600 loader, pre-network refusal, per-job + daily caps, estimate-only preflight,
timeout + 1-retry, planted-secret redaction proof, token usage in receipts,
--probe/--spend gating, stub default labeled `stub`, CI zero-network test,
demo $0.000237 est < $1; 28/28). D 63-80 done (unit inventory, empty-patrol
record, named alerts, 10x→1 dedupe, heartbeat, 12-task artifact-scored eval
100%, offline stub, results JSON + commit, regression gate exit 2 on lowered
score, bus/retry/tamper tasks, --last10 table, non-zero exits, demo twice-safe,
stale-run cleanup, agents/RUNBOOK.md). E 81-100 above. Skips: WebSocket (SSE
satisfies), real --spend call (no key/auth), board.test.mjs relay reference
(not mine), sandbox env failures (pre-existing, proven stashed).

## Notes for the merger

- `.gitignore` (+3 lines) is outside the lane's path list but explicitly
  REQUIRED by tasks 96-97 ("add the data directory with a comment"); the
  diff is the bus-data/ entry plus its comment, nothing else.
- `os-build/lanes/R2_T3_{A,B,C,D,F}.md` + `R2_T3_REVIEW.md` sit beside the
  lane report as evidence backup for the pasted claims; no other lane's
  files are touched.
- The Section F subagent returned a report-back but never wrote its files;
  its "84/84" is dropped (see §91). The lead's live mapping (R2_T3_F.md)
  replaces it, including the page→daemon `{agent, orders}` refusal find.
- `agents/demo.mjs --help` now prints usage and exits 0 (was: ran the demo).
- Demo data roots differ between runs (`/tmp/r2t3-demo` lead runs,
  `/tmp/r2t3-d-demo` in §D) — both real, both out-of-tree; not a conflict.

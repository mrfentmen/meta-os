# Agent R2-T3 lane: agent runtime, local bus, jobs, receipts

## Tree changes after this lane file (2026-11-04, Buffy) — read before starting

These are merged into `main` already. Nothing below is a task; it is the map.

- **One messaging system: `board/`.** `relay/` (Nuntius relay + viewer) and
  `os-build/face/board.py` / `board.html` are deleted. `board/board.mjs` runs on
  18935: `GET /rooms/<room>/messages?since=<n>`, `POST {nick,text}`,
  `POST /rooms/<room>/notify`. The dock's Messages tile opens it; the shell bell
  (`notify.js`) polls its `general` room. Do not add a second transport.
- **`index.html` (repo root) is deleted.** It was the app hub; the dock lists
  apps. The site root is `surfaces.html`, and `server/server.mjs` serves it for
  `/`. `bus.html` stays: it is the dashboard page the DSH tests cover.
- **`imperium/index.html` is archived**, not in the product: no dock tile, not
  copied into the image. The tests read it as a fixture — leave the file alone
  and do not wire a tile to it. The three divisions (`trio/vigiles.html`,
  `ignis.html`, `medicus.html`) are the product.
- **Both logo studio pages are deleted** (`logo-studio.html`,
  `design/meta-ascii-logo-studio.html`), and with them the
  `design/agent-budget-dashboard.html` mock. The spinning loop is
  `js/logo-background.js` / `os-build/face/logo-background.js`; the studio-only
  tests were removed with the pages.
- **Shared chat box: `js/site-chat.js`.** `<script src="js/site-chat.js"
  data-room="..." data-label="...">` gives a page the Board rooms (surfaces.html,
  labs/molecules, labs/music3d, labs/science-lab-review, Custos, Officina,
  face/musica.html). On surfaces.html the room follows `#board-<room>`.

Paste this whole file to the agent. Work on branch `agent-r2-t3` in worktree
`/tmp/agent-r2-t3`. Commit there. Do not merge. Do not push. Do not switch any
other worktree's branch.

## Mission

The agent pipeline works on a stub, and the messaging app still needs an
external Upstash account to say anything. Round 2 makes the agent layer real on
this machine: a local message bus with no third-party dependency, a daemon that
survives restarts, jobs that are bounded and cancellable, receipts that catch
tampering, and an evaluation that scores outcomes instead of vibes.

You own the services and their APIs. T4 owns the pages that call them, Buffy
owns typography and the Trio. Do not edit `bus.html` or any app page.

## Owned paths (only these)

- `agents/` (runtime, submit, watchman, agent loop, schemas)
- `agent-layer/` (stage, units, hooks, meta-ask)
- `server/` (HTTP servers, queue, bus, storage)
- `os-build/iso/payload-agent/metaosd.mjs` and its units
- `os-build/agents/` or any new runtime config you add
- `os-build/lanes/R2_T3_REPORT.md` (yours to write)

Request changes to the image units, `provision.sh`, and the pages in the
report; other lanes own those.

## Rules

- **No QEMU.** Prove on the host with the stub runner, real files, and unit
  tests. State what needs a booted guest.
- No paid model calls unless the user has given a key and a cap in writing.
  With no key, every real call must refuse loudly with the config path.
- No secret values in code, logs, fixtures, or the report. Key names only.
- Call subagents. At least four, one per section, plus one reviewer.
- Every claim needs a command and pasted output.
- Do not leave a server or daemon running when you finish.

## Section A. Local message bus (1-24)

1. Inventory every place the bus requires Upstash or another remote service.
2. Make the default bus local: a file-backed store under one documented data directory.
3. Keep the existing HTTP shape so `bus.html` still works; list every endpoint.
4. Add rooms with create/list/join, and a default `general` room.
5. Add message create/list with stable ids and server timestamps.
6. Add pagination with a documented page size and a cursor.
7. Add search by text across the room, case-insensitive and accent-insensitive.
8. Add presence: join, leave, heartbeat, and a 60-second expiry.
9. Add delivery state per message: sent, stored, failed, with a reason.
10. Add attachments with a size cap, MIME allowlist, and a named rejection.
11. Store attachments outside the message JSONL and keep the path relative.
12. Add a retention policy that never silently deletes the last 500 messages.
13. Add a local-only auth token written 0600; refuse writes without it.
14. Make the remote Upstash path optional and off by default.
15. Add a health endpoint that reports store path, message count, and last write.
16. Add a WebSocket or SSE stream for new messages; prove two clients see one message.
17. Make a dropped connection reconnect with a cursor, not a full reload.
18. Make concurrent writes safe with a lock or a single writer; prove 50 parallel sends.
19. Add a selftest that starts the server on a random port, sends, lists, searches, and exits 0.
20. Add a negative test for a malformed message and one for an oversized attachment.
21. Make the server bind to 127.0.0.1 only; prove the bind address.
22. Add structured logs with the room, message id, and result; never the body.
23. Document the on-disk format and the migration from the old relay.
24. Remove every reference to a required Upstash token from the default startup path.

## Section B. Agent daemon (25-46)

25. Make `metaosd` start on 18940 with a documented health endpoint.
26. Make the daemon survive a client disconnect mid-job.
27. Add a job schema with id, agent, input, budget, timeout, and dry-run.
28. Validate the schema on submit; refuse unknown fields with a named error.
29. Add a queue that is durable across restart; prove a queued job survives a kill.
30. Add a worker pool with a configurable size and a visible busy state.
31. Add a per-job timeout that kills the child and records a timeout failure.
32. Add cancellation by job id; prove a cancelled job leaves a record.
33. Add retry with a max attempt count and a backoff that is visible in the record.
34. Add idempotency by request key so a double submit makes one job.
35. Add a dry-run mode that writes a record but calls no model.
36. Add a per-agent concurrency cap and a named refusal when full.
37. Add a queue depth and oldest-job metric to `/health`.
38. Add a run record per job with start, end, exit code, and artifacts.
39. Make every artifact path relative to the run directory and documented.
40. Add a receipt file per run and make `verify` catch a tampered byte.
41. Add a receipt chain that a judge can verify offline with one command.
42. Refuse to verify when the receipt key is missing; name the key path.
43. Add a job list endpoint that filters by agent, status, and date.
44. Add a status stream or poll contract for the UI; document the shape.
45. Make the daemon refuse to start when the data dir is not writable; name it.
46. Make the daemon clean up stale locks on start and log what it removed.

## Section C. Model calls, keys, budgets (47-62)

47. Document every provider the runtime supports and the exact key name for each.
48. Load keys from `/etc/metaos/agent.env` 0600; never print values.
49. Make a missing key refuse before any network call, naming the path and key.
50. Add a spend cap per job and per day, in the same unit the provider bills.
51. Refuse a job whose budget is zero or above the daily cap.
52. Add a preflight that estimates cost only when the provider exposes it.
53. Add a timeout on the model call and a named error on expiry.
54. Add one retry on a transient network error, then fail with the provider code.
55. Redact secrets from every error and log line; prove with a planted key.
56. Record token usage per run and sum it in the receipt.
57. Add a `--probe` command that makes one minimal real call only when explicitly allowed.
58. Make the probe refuse without an explicit `--spend` flag.
59. Add a provider stub that returns deterministic text for tests.
60. Make the stub the default when no key exists, and label the run `stub`.
61. Add a test that no real network call happens in CI mode.
62. Document the cost of the demo's three jobs and keep the total under $1.

## Section D. Patrol, watchman, eval (63-80)

63. Inventory every scheduled agent and its unit timer.
64. Make the patrol write a record even when it finds nothing.
65. Make the watchman alert on a failed unit with the unit name and reason.
66. Add a dedupe window so one failure does not alert ten times.
67. Add a daily heartbeat record proving the scheduler ran.
68. Add an eval harness with at least ten tasks and a pass/fail definition each.
69. Make the eval run without network using the stub provider.
70. Score each eval task on the artifact, not the model's prose.
71. Record eval results in a JSON file with a timestamp and git commit.
72. Add a regression gate: fail when the score drops below the last recorded run.
73. Add one eval task for the bus, one for a queue retry, one for receipt tamper.
74. Add a command that prints the last ten eval runs as a table.
75. Make the eval harness exit non-zero on any task failure.
76. Add a runnable demo script that submits three jobs and waits for receipts.
77. Make the demo script print every artifact path and the verify result.
78. Make the demo script safe to run twice; prove no duplicate ids.
79. Add a stale-run cleanup that marks runs older than a day as abandoned.
80. Document the operator runbook: start, stop, inspect, retry, cancel, verify.

## Section E. Proof and handoff (81-100)

81. Run the full bus selftest and paste exit 0.
82. Prove two browser clients receive one message over the stream.
83. Run 50 parallel sends and paste the stored count.
84. Kill the daemon mid-job and prove the queued job resumes.
85. Submit a job, cancel it, and paste the record.
86. Tamper one byte in a receipt and paste the verify failure.
87. Run the eval harness and paste the score table.
88. Run the demo script and paste all artifact paths.
89. Prove the real-call refusal with no key, naming the path.
90. Prove zero secrets with a grep for key-shaped strings in the diff.
91. Run every existing agent test and paste before/after.
92. Confirm no daemon or server is left running.
93. List every cross-lane request with file:line for the UI and units.
94. State what only a booted guest can prove.
95. Write the exact guest commands for the booted proof.
96. Confirm the new data directory is not inside the git tree.
97. Add the data directory to `.gitignore` with a comment.
98. Confirm the bus still works with no network device.
99. Confirm no page or service is required to be restarted by hand after a reboot.
100. Write `os-build/lanes/R2_T3_REPORT.md` with task ticks, proofs, skips, and next three steps.

# R2-T3 Section F — Agents page vs daemon (lead-verified, 2026-11-04)

NOTE ON PROVENANCE: the Section F subagent returned a report-back but never
wrote its files (`R2_T3_F.md`, `server/queue/test_page_mapping.py` do not
exist; searched the worktree and /tmp). Its "84/84" claim is therefore
UNVERIFIED and is not repeated here. Everything below was verified live by
the lane lead against `metaosd.mjs` on 127.0.0.1:18982 today; commands pasted.

## What the page reads (os-build/face/agents.html, read-only, NOT edited)

Base `http://127.0.0.1:18940` (line 105). Endpoints called:
- `GET /status` → expects `{stateDirExists, stateDir, queueUrl, heartbeat[{file, ageSeconds}], notices[{ts, level, message}]}` (lines 145-170)
- `GET /agents` → expects `{ok, agents[{name, lane, draft, draftReason, halted}]}` (lines 172-219; drafts shown with reason, halted get resume button)
- `GET /jobs` → expects `{files[{name, mtimeMs}], halted[], stateDir}` (lines 221-237)
- `GET /runs?limit=30` → expects `{runs[{run, agent, orders, startTime, …}]}` newest-first, 30 cap (lines 248-276)
- `GET /runs/<id>?n=200` → expects `{run, agent, exit{refused|code|signal}, meta{durationMs}, result{id}, orders, stdout{lines,truncated}, stderr{lines}}` (lines 281-319)
- `POST /jobs {agent, orders}` → expects `{ok, id}` or `{error}` shown VERBATIM (lines 356-378: `out.textContent = "refused: " + …`)
- `POST /halt {agent}`, `POST /resume {agent}` (lines 196-207)

Refresh: `setInterval(refreshSlow, 5000)` + `setInterval(refreshRuns, 5000)`
(lines 381-382); run log polls `GET /runs/<id>` every 2 s only while a run
is selected, paused otherwise (lines 322-325 + comment 278-280). Honest and
cheap. Layout: 3-column grid collapsing at 1100px/760px — 1366×768 shows all
three columns (read from CSS, lines 22-24).

No-external-request sweep: `grep -c "http://|https://|ws://|wss://"` = 1,
the single hit being `const API = "http://127.0.0.1:18940"`. Clean.

## What the daemon serves (os-build/iso/payload-agent/metaosd.mjs)

`GET /health` (service/version/host/port/dataDir/writable/uptimeMs/
queueDepth/oldestJobAgeMs/workers/agentCap/store/receiptKey — pasted live
below), `POST /jobs`, `GET /jobs`, `GET /jobs/:id[/status|/events|/receipt]`,
`GET /verify`. No `/status`, `/agents`, `/runs`, `/halt`, `/resume`.

## MISMATCH (verified live, the section's main finding)

Every page endpoint except the base URL 404s or shape-mismatches against
the new daemon:
- `GET /status`, `/agents`, `/runs?limit=30` → `{"error":"not found"}` → page
  renders its named dead-backend messages (lines 332/339/344/352 — honest,
  but the page cannot work).
- `POST /jobs {agent, orders}` (exactly what the submit button sends) →
  `{"error":"refused job: unknown field \"orders\""}` — the submit path is
  broken end to end, and the page WILL show the refusal verbatim (line 372),
  which is the correct behavior displaying a real incompatibility.
- `GET /jobs` exists on both sides but shapes differ: daemon returns
  `{jobs:[], count:0}`; page reads `j.files` → falls into the
  `board is empty (undefined)` branch (no crash: `!j.files` short-circuits).
- Good news: daemon `/health` already carries `uptimeMs`, `queueDepth`,
  `oldestJobAgeMs` (pasted below) — the page's R5 "no uptime source" gap from
  the old relay world does not apply to metaosd; the page simply doesn't call
  `/health`.

Live paste (daemon on :18982, today):
`GET /health` → `{"ok":true,"service":"metaosd","version":"0.1.0-r2t3",
"host":"127.0.0.1","port":18982,…,"uptimeMs":14209,"queueDepth":0,
"oldestJobAgeMs":null,"workers":{"size":2,"busy":[]},"agentCap":1,
"store":"file","receiptKey":false}`.
`POST /jobs {"agent":"demo","orders":"sweep the tree"}` →
`{"error":"refused job: unknown field \"orders\""}`.

## Cross-lane requests (page lane owns agents.html; not edited)

F1 (blocks the demo path): page submit sends `{agent, orders}`; daemon
schema (`agents/job.schema.json`) has no `orders` — either the page sends
`{agent, input: {text: orders}}` (agents.html:363) or the daemon aliases
`orders→input.text`. F2: page panels (`/status`, `/agents`, `/runs`,
`/halt`, `/resume`, run-log shape) vs daemon routes (`/health`, `/jobs`,
`/jobs/:id/*`) — one side must adopt the other's contract; recommendation:
page adopts the daemon (the new contract), keeping the verbatim-refusal and
named-dead-backend behavior. F3: board filter by agent/state + board full-life
timeline (tasks 114, 119) have no UI in agents.html or board.html — new page
work, no source to map.

## Downgraded from the original F brief

Tasks 121-122 (screenshots with live job / queue down): no live job can be
shown because submit is refused (above) — the dead-backend state IS the
honest screenshot, textually recorded here instead of pixels. Task 125
(mapping selftest): covered by this live mapping, not a committed script.
Task 127 (OS build + uptime): uptime source EXISTS (`/health.uptimeMs`);
OS build is not served by the daemon — needs a `/health` field or the page
reads `GET /facts` (:18932) and labels it.

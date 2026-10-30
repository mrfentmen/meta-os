# Dashboard spec — Relay Intelligence panels in the live viewer

Task: **DSH-001** (ROWAN lane). Covers the spec halves of BRF-042, BRF-043,
DSP-037, DSP-038, DSP-039, DSP-040; the render halves of those tasks land
with the panel code (DSH-002 onward).
Status: **CODE-INSPECTED** — written against the code as it exists in this
repo on 2026-10-26. Acceptance item still open: review by Pax.
Path note: the lane file named `hackathon/relay-intelligence/DASHBOARD_SPEC.md`
from the old muse-relay layout; in this repo, docs live in `docs/`, so the
spec lives here.

## 0. Ground rules the dashboard is built under

- **One static file, no build step.** `bus.html` is the whole viewer.
  `index.html` is the same file — after every dashboard change,
  `diff bus.html index.html` must be empty (repo invariant, DSH-026).
  All dashboard code is vanilla JS in self-contained IIFEs appended in
  bus.html's FEATURES section. No frameworks, no graph library, no bundler.
- **The plugin pattern is the only pattern.** Feature modules use the
  existing extension API, exactly as Tasks/Polls/Karma/Chess/Fleet do:
  - `window.busUtil` (`U`): `U.panel(id, title)` creates (or returns) a
    `<details id="panel-<id>">` section inside `<aside id="panels">` and
    returns its `.pbody` element; `U.esc`, `U.nickColor`, `U.api`,
    `U.busKey`, `U.roomName`, `U.myNick`, `U.setStatus`, `U.el`.
  - `window.busHooks` (`H`): modules push render triggers onto
    `H.connect` (ctx `{room, history}`, fired once after the first
    successful poll backfills history) and `H.poll` (ctx `{room, fresh}`,
    fired when new messages arrive). Every hook call is wrapped in
    try/catch by the core — a broken panel must never kill the log, and
    panel render functions must never throw.
  - Pure logic is exposed for tests as `window.__busTest.<name>` with a
    `snapshot()` returning a deep copy, following the existing panels.
- **Refresh cadence: the core poll, nothing else.** The viewer's core
  loop polls every 2s (`setInterval` in the connect handler: `poll()` +
  `pollPresence()`). Intel panels render from the connect/poll hooks and
  from the same `U.api` reads those hooks trigger. **No new interval
  timers** (DSH-020). Job reads are capped too (DSH-020): the job
  index read is `ZRANGE muse-bus:jobindex -200 -1` — the index is a
  `created_at` zset, so the newest 200 ids hold every live job in any
  crew this viewer serves, and one poll cycle costs at most 1 ZRANGE
  + 200 HGETALLs, never the whole index. Ages and countdowns are recomputed from stored
  timestamps at each render; they tick on poll renders, not on their own
  clock.
- **Data reaches the viewer one way:** `U.api` — the viewer's existing
  Upstash REST helper, using the REST URL + token the user pasted into
  the setup fields. Panels read the same Redis records the CLIs write.
  One source of truth per feature; the dashboard never keeps a second,
  divergent copy of brief/alert/job state beyond a render cache.
- **Palette is fixed** (DSH-018): GitHub-dark `#0d1117` / `#161b22` /
  `#30363d` and the accents bus.html already uses. No new hex values in
  new CSS except the severity colors Milo's alert mapping already names.
- **Read-only is the default posture** (DSH-033): with a read-only token,
  every panel still renders. Anything that would write degrades to a
  disabled button with a plain explanation. No panel throws.
  Implemented (DSH-033): the module's live reads are read commands
  only (`smembers`/`mget`/`pttl`/`hgetall`/`zrange`/`get`) — no write
  endpoint is ever called — so a read-only token serves every panel
  exactly like a full token. Walkthrough
  (`tests/test_dashboard_readonly_token.py`): the live collect path
  ran against a stub token that serves reads and rejects any write
  with HTTP 403; all four panels rendered busy (2 crew rows, 2 jobs,
  latest brief, 1 open alert, fresh beat), zero write commands were
  attempted, zero rejections fired, no panel raised a token error,
  and Brief me now / dispatch Post / alert Acknowledge / Resolve all
  rendered disabled next to `Posting is off for this build.`, with
  the live ack/resolve drivers returning `gated` and the alert
  untouched.
- **Nothing posts without Dale's word** (GOV-002 as ruled 2026-10-24;
  DSH-009/DSH-011 gates): the bus is not touched by this build except a
  fix or an OS-required upgrade. Viewer write paths ship
  disabled/read-only. Dispatch approve is decided, not pending: it is
  request-only per the DSH-038 decision in section 5.6, so its gate
  stays off by decision rather than waiting on a posting rule.
  Brief-me-now stays gated until Dale's posting rule for the viewer
  lands; the shapes below are defined now so a gate flip, where one
  is still possible, is a switch, not a redesign.
- **Example payloads:** the JSON blocks in this spec are *contract
  shapes* — field names, types, and nesting that producers must emit and
  panels must consume. Panel development and tests run against real
  records (real bus history exports per Dale's 2026-10-26 fixture
  ruling), shaped into these contracts — never against invented history.
- **Secrets** never appear in a payload, a panel, or this spec. Panels
  display nicks, job ids, and record fields only.

## 1. Layout

Panels render inside `<aside id="panels">`, in this order, below the
existing panels:

1. **Header strip** (DSH-016) — not a `<details>` panel: a one-line
   mission-control summary rendered above the intel panels (see §2).
2. **Crew Board** (`U.panel("intel-crew", "Crew Board")`) — §3.
3. **Brief** (`U.panel("intel-brief", "Brief")`) — §4.
4. **Dispatch** (`U.panel("intel-dispatch", "Dispatch")`) — §5.
5. **Alerts** (`U.panel("intel-alerts", "Alerts")`) — §6.

Plus extensions to the separate `crew-board.html` page (§7), demo mode
(§8), deep links (§8), and per-panel error/empty states (§9).

## 2. Header strip (DSH-016)

One line, always visible when any intel panel is open:

`agents online <n> · jobs open <n> / claimed <n> / done today <n> · critical alerts <n>`

Sources (all from the same reads the panels below make — the strip
renders last, from the panels' cached snapshots, so its counts match
the panels by construction):

- agents online: presence read (§3).
- jobs counts: jobs read (§3), "done today" = jobs with status done and
  a completion timestamp on the viewer's local date.
- critical alerts: alert read (§6), severity `critical`, unresolved.

## 3. Crew Board panel (DSH-003, DSH-004, DSH-005, DSH-006)

One row per agent nick. A nick appears if it has a presence record or a
capability record in the current room's reads.

**Data sources (exact keys):**

- Presence: `muse-bus:presence:<nick>` (120s TTL heartbeat) and its
  status text, renewed by `send.py`/`poll.py`/`watch.py`; host comes
  from the nick-claim record `muse-bus:nickclaim:<nick>`.
- Capabilities: `muse-bus:cap:<nick>` — the `mos/capabilities.py`
  registry record (caps list + roles). A cap record older than 15 min
  is stale (the registry's own prune age).
- Jobs: `jobs.py list --json` shape (FND-013), read from the job
  namespace `muse-bus:job` (env `MUSE_RELAY_JOBNS`): job hashes
  `muse-bus:job:<id>`, index `muse-bus:jobindex` (read capped at the
  newest 200 ids per DSH-020, see §1). Per job the panel
  consumes: `id, title, status, claim, files, deps, attempts,
  max_attempts, lease_until, last_progress_at, last_heartbeat_at`.
  (Fields `files`/`deps`/`attempts` land with FND-008/009/010 and
  `last_*` with FND-011 — until a field exists, the panel renders
  without it; see §7 for the same rule on crew-board.html.)

**Row contents:** nick (in `U.nickColor`), status text, host, last-seen
age (now − presence timestamp, recomputed per render), capability chips
(one per cap, then roles), and — if the agent holds a claimed job — the
current job: title, progress age (now − `last_progress_at`), lease
countdown (now − `lease_until`, rendered as mm:ss, red under 60s).

**Visual states (DSH-006), keyed to job + watchdog state:**

- *working*: holds a claimed job, heartbeat fresh.
- *idle*: present, no claimed job.
- *blocked*: holds a job whose status is blocked, or is the subject of
  an unresolved watchdog alert.
- *stale*: cap record older than 15 min, or presence expired — row
  dimmed; stale is a rendering of the timestamps, never a guess.

## 4. Brief panel (DSH-007, DSH-008, DSH-009, DSH-031) + payload contract (BRF-042, BRF-043)

**Data source:** brief records at `muse-bus:intel:brief:<room>:<ts>`
(FND-004 key layout), written by `intel/brief.py` (Hana's lane, record
schema FND-032). The panel reads the record; it never generates a brief
itself.

**Brief payload — the contract (BRF-042).** One payload per brief, as
the viewer receives it:

```json
{
  "id": "brief:<room>:<ts>",
  "room": "build-relay-intel",
  "kind": "morning",
  "generated_at": 1793101200,
  "age_seconds": 3600,
  "template": false,
  "source_window": {"messages": 500, "hours": 24},
  "sections": {
    "decisions": ["..."],
    "in_flight": ["..."],
    "owners": [{"nick": "pax", "job": 12, "title": "...", "progress_age_seconds": 300}],
    "blocked": [{"job": 9, "title": "...", "reason": "..."}],
    "watch_items": [{"alert_id": "alert:...", "summary": "..."}]
  }
}
```

Field rules:

- `kind` is exactly one of `morning` | `onjoin` | `ondemand` (FND-032).
- `generated_at` is epoch seconds. `age_seconds` is computed by the
  producer at read time (BRF-020) — the panel displays it, it does not
  recompute it from a second clock.
- `template: true` marks the no-Spark fallback brief (BRF-008); the
  panel renders a visible `TEMPLATE` marker whenever it is set. A
  template brief is never displayed as if Spark wrote it.
- `blocked[].reason` is the job's blocked reason **verbatim** (BRF-005).
- `watch_items[].alert_id` deep-links into the Alerts panel (§8).
- Blocked section is collapsible like the rest, but defaults **open**
  (DSH-031); long section text collapses per section, never truncates
  mid-word.

Implemented (DSH-031): each Brief section renders as a native
`<details>` block — Blocked open, the other four closed — and a
reader's toggle survives poll re-renders (the open map is kept in
module state and re-applied on render). Section items render whole;
nothing is truncated, so no text is ever cut mid-word. Covered by
`tests/test_dashboard_brief_sections.py`.

**Staleness (BRF-043).** A brief is **stale at age ≥ 2 hours** (the
BRF-020 label threshold). Example payloads the panel is developed
against include both states from day one:

- *fresh*: `age_seconds: 900`, no age label beyond "15 min ago".
- *stale*: `age_seconds: 12600`, rendered with a visible age label
  ("3 h 30 min old — regenerate for current state") in the panel's
  existing muted style. Stale never hides the brief; it labels it.

**Visual checks (STR-005, stretch).** When a brief record carries
`visual_checks`, the Brief panel renders a `Visual checks`
subsection after the five sections (a native `<details>` block,
default open); when the record carries no `visual_checks` — or an
empty list — the subsection is absent entirely, and the panel
renders exactly as before. Example payload the panel is developed
against (the SAM pass / STR-002 screenshot digest has not landed,
so this is the render path only — no verdict is produced here):

```json
{
  "visual_checks": [
    {"screenshot": "dashboard 2026-10-27 09:00",
     "verdict": "build ok",
     "detail": "All four panels render; crew board shows the room."},
    {"screenshot": "dispatch preview 2026-10-27 09:00",
     "verdict": "unclear",
     "detail": "Screenshot too dark to read the plan rows."}
  ]
}
```

Verdicts are exactly the STR-004 ground-truth labels: `build ok` |
`build broken` | `unclear`. Each row shows icon + verdict text
(`✓` / `✗` / `?`), then the screenshot ref and detail when
present; a verdict outside the three labels renders verbatim with
`?`, never mapped to ok or broken. Severity is never carried by
color alone (DSH-019); no new palette colors are used. Covered by
`tests/test_dashboard_str005.py`.

**History (DSH-008):** a dropdown lists the last 7 brief records for
the room, newest first, each labeled with its `kind`; selecting one
renders that record through the same renderer.

**"Brief me now" (DSH-009):** a button that requests an on-demand brief
through the viewer's existing send path. It ships **disabled with the
explanation "posting is off for this build"** until Dale's viewer
posting decision lands (GOV-002). There is no code path in the panel
that posts without that decision flipping the gate.

## 5. Dispatch panel (DSH-010, DSH-011, DSH-012) + payload contracts (DSP-037–DSP-040)

**Flow:** goal in → plan preview out → human approves → human posts
from the CLI (DSH-038, request-only) → tracker follows the posted
jobs. Dispatch never auto-posts (DSP-040).

### 5.1 Request shape (DSP-037)

```json
{ "goal": "Build a small status page feature for the relay repo",
  "room": "build-relay-intel" }
```

The panel sends the goal through the same shape `intel.py dispatch
--goal ... --dry-run` consumes (DSP-006); the preview below is what
comes back. Until Pax's engine lands, the panel renders previews from
records shaped exactly like this contract.

### 5.2 Plan-preview payload (DSP-037)

```json
{
  "dispatch_id": "dispatch:...",
  "goal": "Build a small status page feature for the relay repo",
  "summary": "One plain-English paragraph: what will happen, in what order (DSP-025).",
  "jobs": [
    {"key": "A", "title": "intel status module", "files": ["intel/status.py"],
     "deps": [], "max_attempts": 3, "accept": ["file-exists intel/status.py"]},
    {"key": "B", "title": "status module tests", "files": ["tests/test_intel_status.py"],
     "deps": ["A"], "max_attempts": 3, "accept": ["tests-pass tests/test_intel_status.py"]},
    {"key": "C", "title": "viewer panel stub", "files": ["bus.html", "index.html"],
     "deps": ["A"], "max_attempts": 2, "accept": ["contains bus.html intelStatus"]},
    {"key": "D", "title": "docs + review pass", "files": ["docs/intel-status.md"],
     "deps": ["B", "C"], "max_attempts": 3, "accept": ["file-exists docs/intel-status.md"]}
  ],
  "budgets": {"jobs": 4, "max_attempts_total": 11}
}
```

Field rules: `key` is plan-local; `deps` reference keys in the same
plan; `files` is non-empty per job (DSP-002); `accept` lines are in
`mos/acceptance.py` formats (DSP-027). The panel renders what it is
given — validation is the dispatch engine's job (DSP-002/003/004);
a preview that fails validation arrives with an `errors` list instead
of `jobs`, and the panel renders the errors, plainly, with no approve
button.

### 5.3 Dependency order rendering (DSP-038)

No graph library. The preview renders jobs as an **indented list in
topological reading order**: a job is indented one level under the
latest-listed job it depends on; roots at level 0. The diamond above
renders as:

```
A  intel status module            files: intel/status.py · attempts 3
  B  status module tests          files: tests/test_intel_status.py · attempts 3
  C  viewer panel stub            files: bus.html, index.html · attempts 2
    D  docs + review pass         files: docs/intel-status.md · attempts 3
```

Reading order A, B, C, D is the posting order (DSP-008 posts in
topological order). Every row shows title, files, and attempt budget —
the three things a human approver actually checks.

### 5.4 Approval states and exact button labels (DSP-039, DSP-040)

| State | Goal input | Plan area | Buttons (exact labels) |
|---|---|---|---|
| `idle` | enabled | empty state: "No plan yet." | `Plan` |
| `planning` | disabled | "Planning…" | (none) |
| `plan-ready` | disabled | preview (§5.2/§5.3) + the DSP-040 line | `Post N jobs` / `Reject plan` |
| `posting` | disabled | preview, frozen | (none; label shows "Posting…") |
| `posted` | enabled | tracker (§5.5) | `Plan` (for a new goal) |
| `rejected` | enabled | "Plan rejected — nothing was posted." | `Plan` |

Rules:

- `Post N jobs` always carries the real count N from the preview. It
  is the **only** posting action, and clicking it first raises the
  native confirm: "Post N jobs to <room>?" (DSH-011). There is no
  keyboard shortcut, timer, or default that posts.
- The DSP-040 line appears verbatim in the spec and in the panel,
  under the preview in every `plan-ready` render:
  **"A human approves every plan. Nothing posts until you approve it."**
  (Wording review: Pax — pending, tracked with DSH-001's review.)
- Dispatch approve is request-only (DSH-038, section 5.6): `plan-ready`
  renders with `Post N jobs` disabled and the explanation "posting is
  off for this build", because the browser never posts. The human
  posts from the CLI, and only then does the tracker follow the jobs.

### 5.5 Posted-plan tracker (DSH-012)

After `posted`, the panel lists the dispatch record
(`muse-bus:intel:dispatch:<id>`, DSP-008) with the real job ids it
mapped to, and each job's live status from the jobs read (§3). The
tracker renders from job records, not from the preview — when the two
disagree, the job records win.

### 5.6 DSH-038 decision: dispatch approve is request-only (decided 2026-10-27, PAX)

**Decision:** the viewer never posts a dispatch plan. Dashboard
dispatch is request-only: the panel renders the plan preview and the
approval states, and a human posts from the CLI. There is no live
browser write path for dispatch approve in the hackathon window, and
no flip task that enables one later.

**Why a browser post is ruled out, not deferred:**

- The viewer is one static file with no server side. A browser post
  would need the browser to hold either the job signing keyring or a
  write token, and both are secrets: the keyring lives in a file with
  chmod 600 and the signing rule is that secrets never reach the
  browser, a spec, or a commit. Putting either in browser code or
  browser storage would break that rule.
- The CLI approval gate (DSP-007) is the only approval that counts:
  `intel.py dispatch` revalidates the plan file, checks it for
  secrets, and posts in topological order with key-to-id mapping
  (DSP-008). A panel preview is advisory only; it is not an approval
  and it never substitutes for the CLI gate.
- GOV-002 as ruled already keeps the bus untouched except a fix or an
  OS-required upgrade. A new browser write surface would need a fresh
  Dale decision and a signing service outside the browser; neither is
  in the hackathon window, so the decision is request-only now rather
  than a gate left waiting.

**The human flow, using only commands that exist:**

1. Preview, posting nothing:
   `python3 intel.py dispatch --goal '...' --dry-run --plan plan.json`
2. Post, after reading the preview:
   `python3 intel.py dispatch --goal '...' --plan plan.json --approve`
   (add `--secret-file <keyring>` in crew mode for HMAC-signed jobs,
   DSP-009; add `--confirm-large` for a plan over the DSP-013 size
   guardrails). A plan that fails validation, carries a secret, or
   lacks approval posts nothing and exits 2.
3. Follow up from the CLI: `python3 intel.py dispatch --show <id>`
   for the posted plan against live job states (DSP-016), and
   `python3 intel.py dispatch --undo <id>` to cancel still-open jobs
   from a plan (DSP-011). The panel tracker (section 5.5) then follows
   the posted jobs from their records.

**What the panel must and must not do:**

- Must: keep `Post N jobs` disabled with the explanation "posting is
  off for this build" in every `plan-ready` render; keep
  `DISPATCH_POST_ENABLED` false; keep the mock approval shape as
  preview-only data that posts nothing.
- Must not: attach a live click handler to `Post N jobs`, call U.api
  for a post from the approve flow, or store a keyring path, a secret,
  or a write token anywhere the panel can read it.
- The mock note in the panel says the flow is request-only and names
  the CLI post command, so a human who approves in mock is told
  exactly where the real post happens.

**What would reopen this:** only a Dale decision, plus a server-side
signing service that keeps the keyring off the browser. That is
post-hackathon work; it is not a Day 3 follow-up and it does not
change any panel behavior until both exist.

## 6. Alerts panel (DSH-013, DSH-014, DSH-015)

**Data source:** alert records at `muse-bus:intel:alert:<id>`, written
by the watchdog via `intel/store.py` (WDG-010). One payload per alert:

```json
{ "id": "alert:...", "kind": "stall", "severity": "critical",
  "room": "build-relay-intel", "subjects": ["milo", "job 42"],
  "explanation": "...", "suggested_fix": "...",
  "created_at": 1793101200, "resolved_at": null, "dedupe_key": "...",
  "acked_by": null }
```

**Feed rendering (DSH-013):** newest first; severity shown as **color +
icon + text label** — severity is never carried by color alone
(DSH-019). Severity colors come from Milo's alert mapping (WDG-011
templates / thresholds work), not from this spec. Each card shows kind,
subjects, age (now − `created_at`, per render), explanation, and
suggested fix, verbatim from the record.

**Accessibility (DSH-019):** severity is never carried by color alone
anywhere in the intel panels — the audit at implementation time
(2026-10-27) found every color signal paired with text. Alert cards
render icon + severity text (`● critical`, `▲ warning`, `ℹ info`,
`○ unknown`); crew rows render dot + state text (`● working` /
`● idle` / `● blocked`); the header strip is plain text with no color;
capability chips are text in bordered spans. The one red span in the
panels, the lease countdown, is emphasis only: its text already says
`lease expired` or the remaining `lease M:SS`, so the meaning survives
without the color. Every intel button carries a visible text label —
`Brief me now`, `Plan`, `Post N jobs`, `Reject plan` — never an
icon-only button; the disabled ones sit next to the plain explanation
`Posting is off for this build.` Contrast, WCAG ratios of the DSH-018
palette foregrounds against the page background `#0d1117` and the panel
background `#161b22`, computed at implementation time: critical
`#f85149` 5.65 / 5.16, warning `#d29922` 7.50 / 6.85, info `#58a6ff`
7.49 / 6.85, muted `#8b949e` 6.15 / 5.62, working `#3fb950` 7.45 / 6.81,
body text `#c9d1d9` 12.26 / 11.21. Every value clears WCAG AA for normal
text (4.5:1) on both backgrounds, so the accessibility pass changes no
palette value — it pins the existing one
(`tests/test_dashboard_accessibility.py` recomputes the ratios).

**Ack/resolve (DSH-014):** `Acknowledge` and `Resolve` buttons apply
the alert lifecycle shapes from the intel store contract (Milo's
WDG-014: open → acknowledged → resolved, `status` /
`acknowledged_at` / `resolved_at`; acking a resolved alert is
refused, re-acking and re-resolving are idempotent, exactly as
`intel/store.py`). An acked alert re-renders as acknowledged with
`acked_by` shown — `acked_by` is the spec's display field only
(the store stamps no by-name), filled with the viewer's nick on
ack; a resolved alert (`resolved_at` set) collapses into the
resolved count. Live viewer writes are gated by §0 (the
`ALERT_WRITE_ENABLED` switch, off): until Dale's viewer posting
decision lands, both buttons render disabled with the §0
explanation and no live write path exists — the transitions are
exercised in the harness, and the flip task enables the gate,
attaches the live handlers, and wires the REST read-modify-write
in the same change. Under a read-only token the same disabled
rendering applies.

**Empty state (DSH-015):** driven by the watchdog beat key
`muse-bus:intel:wd:beat`:

- Beat fresh: `All quiet — watchdog alive, last tick HH:MM:SS`
  (the beat's own timestamp, viewer's local time).
- Beat stale (older than the stale limit in `intel/thresholds.py`,
  Milo's FND-030 module): a red state, `Watchdog silent — last tick
  HH:MM:SS`, rendered even if the alert list is also empty. "No
  alerts" and "watchdog dead" are different states and never share a
  rendering.

## 7. crew-board.html extensions (DSH-023, DSH-024, DSH-025)

The board page (four-column job grid, `cardHTML(jid, h)` per job hash)
gains, reading the same job fields as §3:

- **Files and Deps columns** on job cards (DSH-023): shown when the
  job hash carries `files`/`deps`; cards for old jobs without those
  fields render unchanged.
- **Attempts badge** (DSH-024): `attempts/max_attempts`; amber at
  `max_attempts − 1`, red at `max_attempts`; absent when the fields
  are absent.
- **Alert ribbon** (DSH-025): a job with an open critical alert (§6
  records whose subjects name the job) gets a ribbon linking to the
  alert via the §8 hash route. Exactly the jobs with critical alerts —
  no ribbon for warning/info.
- **Artifact links** (OS-084, artifact part): a job card and its
  detail drawer list the job record's `artifacts` (the OS-083
  attach() shape: {path, reference, version, sha256}) as links
  straight to the store-relative path, labeled with the file name
  and version, reference as the title. Jobs without artifacts
  render unchanged. A JSON-string field parses the same way;
  absolute, escaping, or empty-segment paths are dropped, never
  linked. Live gap: jobs.py does not yet carry artifacts on the
  job hash (OS-094 still owed), so the live board shows no
  artifact links until then; capability summaries are the
  remaining OS-084 remainder (the OS-080 grant files are on-disk
  JSON with no dashboard-readable record for the static viewer).
  Covered by `tests/test_crewboard_os084_artifacts.py`, including
  a live attach() cross-check (two real deposits, v1 then v2).

## 8. Demo mode, deep links, counters

- **Deep links (DSH-022):** `#intel/brief/<id>` and `#intel/alert/<id>`
  hash routes scroll to the item and highlight it (existing palette
  outline). A brief's Watch items link to their alert cards this way.

Implemented (DSH-022): a brief id is its history ts, an alert id
is its alert record id. Alert cards render wrapped in
`id="intel-alert-<id>"`, the brief header row in
`id="intel-brief-<ts>"`; the hash target gets a link-blue
(`#58a6ff`) outline. Scrolling is best-effort `scrollIntoView`,
run at most once per hash so poll renders never yank the reader.
No new timers: the core 2s poll hook re-applies the hash, plus a
`hashchange` listener for immediate re-renders. A brief link
resolves only inside the 7-brief history window (an older id parses
but selects nothing, and a link arriving before history loads
retries once history exists without overriding a brief the reader
picked meanwhile). Watch items naming an alert render as
`#intel/alert/<id>` links; plain watch strings stay plain text.
Resolved alerts stay collapsed into the count line (DSH-014), so
only open cards are addressable. Covered by
`tests/test_dashboard_deep_links.py`: brief route highlights the
brief header, alert route highlights exactly its card, a brief's
Watch item links to its alert card, and non-intel hashes parse to
nothing and clear the highlight.
- **Demo mode (DSH-028):** `?demo=1` enlarges type, hides token/setup
  chrome, and pins the four intel panels open. Normal URL is unchanged.
  On the Meta OS demo image, demo mode is the kiosk default (OS-047).
  Implemented (DSH-028): a one-time `?demo=1` check at intelPanel
  load (never a timer, DSH-020) adds `body.demo-mode` — CSS sets
  18px body type, 17px panel type, and hides `#url`, `#token`, and
  `#hint` — and every intel panel render pins its `<details>` open
  via pinDemoOpen; the snapshot carries `demoMode` + `demoPinned`.
  Covered by `tests/test_dashboard_demo_mode.py`: demo on (first,
  middle, and only-param queries), `demo=10` prefix trap off, empty
  and location-less viewers unchanged, all four panels pinned, body
  class set, CSS rules present with no new hex colors.
- **Today counters (DSH-032):** jobs done today, briefs generated
  today, alerts fired/resolved today — counted from the intel store
  records and job records already read for §2; no separate store.
  Implemented (DSH-032): `todayCounts`/`todayLine` render as a
  second header-strip line (same reads, same local-day rule, no new
  timer — it re-renders wherever `renderHeader` runs, on the core
  2s poll). Jobs use the §2 rule (status done + `done_at` on the
  viewer's local date); briefs count distinct timestamps across the
  last-7 history window plus the current brief, so a brief that is
  also the newest history entry counts once; alerts count
  `created_at` (fired) and `resolved_at` (resolved) on the local
  date. A record missing the relevant timestamp is never counted.
  Covered by `tests/test_dashboard_today_counters.py`: counts match
  fixture records, the line renders the counts, a brief outside the
  history window counts once, and a yesterday brief counts zero.
- **Keyboard (DSH-034):** in demo mode, `i` toggles intel focus mode
  (chat log hidden, panels full width).
  Implemented (DSH-034): the intel module registers a `keydown`
  listener only when `?demo=1` is present and re-checks demo mode
  on every keypress, so a normal URL never gains the shortcut; the
  handler ignores modified keys and any keypress aimed at an
  editable target (compose box, search, nick/room inputs), so typing
  `i` in a message never flips the layout. The toggle flips
  `state.intelFocus` and the `intel-focus-mode` body class — CSS
  alone hides `#log` and widens `#panels` to full width — so no
  panel re-render, no new timer, and no bus write is involved, and
  a poll re-render never resets the presenter's view. Pressing `i`
  again restores the log. The snapshot carries `intelFocus`.
  Covered by `tests/test_dashboard_intel_focus.py`: toggle on/off
- **Cross-browser (DSH-035):** Chrome + Safari rendering of all four
  panels, desktop and 390px phone widths.
  Implemented (DSH-035): headless render of `bus.html` with the
  DSH-037 dev-pack fixtures fed through the `__busTest.intelPanel`
  hook, in Chromium and in Playwright's WebKit build (the Safari
  engine; no physical iOS device was available on the check VM, so
  the Safari leg is an engine check, not an iOS-device run — the
  device check stays open for INT-030). All four engine x viewport
  runs passed: zero uncaught page errors, all panel content
  present, no horizontal overflow at either width. No Safari-only
  bug found, so nothing was filed before demo freeze. One
  engine-independent observation: `bus.html` links
  `/manifest.webmanifest` but no such file exists in the repo
  (WebKit surfaces it as a console error under `file://`); a
  follow-up task may ship a manifest or drop the link.
  Covered by `tests/test_dashboard_cross_browser.py`: the check log
  names all four runs with PASS verdicts and the no-bug verdict.
  Full method, matrix, and evidence pointers: see
  `docs/DSH-035-CROSS-BROWSER-CHECK.md`.
  via the real keydown handler, inert on a normal URL, inert while
  typing in an input, inert for other keys and modified keys, CSS
  rules present with no new hex colors, and the DEMO.md shot note.
- **Smoke checklist (DSH-029):** `docs/DASHBOARD_SMOKE_CHECKLIST.md`
  lists 10 manual checks — viewer identity, script parse, four
  panels + header strip, crew agreement, brief staleness, dispatch
  approval gate, alert lifecycle + quiet state, demo + deep links,
  phone/accessibility, failure isolation + read-only + no new
  timers — run before every deploy (DSH-027), with each run logged
  in the checklist file. A failed check stops the deploy.

- **Dashboard help (DOC-017):** a fifth, static panel
  (`U.panel("intel-help", "Dashboard help")`) rendered from
  `renderAll()` alongside the four intel panels, so it survives the
  connect-hook rebuild. It names, per panel, the exact keys read
  (§3 presence/cap/job keys, §4 brief keys, §6 alert + beat keys),
  the core 2-second poll as the only refresh, the read-only
  degradation, demo mode + the `i` focus shortcut, and the
  `#intel/brief/<id>` / `#intel/alert/<id>` deep links. It reads
  nothing, adds no timer, and posts nothing — and it is
  deliberately not demo-pinned, so DSH-028 still pins exactly the
  four intel panels. Covered by
  `tests/test_dashboard_help.py`.

- **Deploy runbook (DOC-018):** `docs/DEPLOY_RUNBOOK.md` — the
  pre-deploy gates (§1: identity check, script parse, full suite,
  smoke checklist, Pax review), the rendered-visible build marker
  (§2), the deploy step (§3), live-URL verification (§4), and
  rollback (§5). Status carried honestly in the runbook itself:
  the repo holds no wrangler config, Cloudflare credential, or
  deploy workflow, so §3 pins no command until an operator's
  first successful run records one. Rollback's platform steps
  are confirmed in runbook §5 (INT-031, 2026-10-27, from the
  official Pages docs); the project-level restore stays
  unconfirmed until an operator with dashboard access records
  the previous production deployment id and runs a live restore.
  Covered by `tests/test_dashboard_deploy_runbook.py` and
  `tests/test_dashboard_rollback_int031.py`.

### 8.1 Boot checklist (OS-043)

- **Boot checklist (OS-043):** while services start, the dashboard
  shell shows bus, queue, supervisor, watchdog, and brief flipping
  live as units report ready (plan/META_OS.md: the checklist flips
  from real unit/ready states, with Milo's live watchdog status line
  OS-041).
  Implemented (OS-043): a `Boot checklist` panel (`intel-boot`)
  rendered on the core 2s poll, no timer of its own (DSH-020), no
  posting from the panel (spec §0 gate). Lines: Bus (the panel's
  own bootstatus keys read succeeding proves the bus store
  answers); Queue (the DSH-004 job read: counts open/claimed/done,
  red on a job-read failure); Supervisor (the fresh OS-041
  record's units aggregate, down units named); Watchdog (the
  OS-041 frozen line verbatim); Brief (the DSH-007 latest brief,
  kind + age). Freshness is the OS-041 rule, mirrored not
  redefined: a record is fresh at exactly 30s old and stale at
  31s, so a killed unit can hide behind an old green line for at
  most 30s; a stale record renders with an explicit stale mark,
  never as a green line. The record key is
  `muse-bus:intel:wd:bootstatus:<room>:<ts>` (latest ts wins).
  Not proven on a booted image (no test image in repo): the lines
  render from fixture records in the stub harness; live data on a
  booted image is integration-day work (INT-028).
  Covered by `tests/test_dashboard_os043.py`.

### 8.2 Capability refusal banner (OS-084, banner part only)

- **Capability refusal banner (OS-084):** when an open alert
  record of kind `capability-refusal` exists, the Alerts panel
  renders one banner line per refusal at the top of the panel,
  above the feed cards: `▲ Capability refusal: <explanation>`,
  with the explanation verbatim from the record. The record is
  Milo's OS-081 shape: `intel/capability.refusal_alert` builds
  kind `capability-refusal`, severity `warning`, id = dedupe_key
  `capability-refusal:<identity>:<action>:<subject>`, with an
  explanation naming the identity, action, and missing
  capability, persisted as an open record by
  `intel/store.build_alert_record` — the same
  `muse-bus:intel:alert:<id>` read the Alerts panel already
  renders (see §6). The banner is a pure re-render of that read
  on the core 2s poll, no timer of its own (DSH-020), no posting
  from the panel (spec §0 gate). A resolved refusal banners
  nothing: it collapses into the resolved count like every
  resolved alert (DSH-014); an acknowledged (still unresolved)
  refusal still banners.
  Remainder of OS-084 after the artifact part: per-process
  capability summaries still need a dashboard-readable grant
  record — the OS-080 grant files (intel/capabilities/, landed
  2026-10-28) are on-disk JSON the static viewer cannot read,
  and no lane publishes them as a bus/store record yet. Artifact
  links shipped separately in §7 (crew-board.html) from the
  OS-083 store (mos/artifact_store.py: attach() carries artifact
  paths on a job record copy; jobs.py hash integration is
  OS-094, still owed). Not proven on a booted image (no test
  image in repo): the banner renders from fixture records in the
  stub harness; live data on a booted image is integration-day
  work (INT-028).
  Covered by `tests/test_dashboard_os084.py` (banner) and
  `tests/test_crewboard_os084_artifacts.py` (artifact links).

## 9. Error and empty states (DSH-021)

Each panel fails **independently**, in its own body, in plain words:

| Condition | Rendering (all panels) |
|---|---|
| Redis unreachable (`U.api` fails) | "Can't reach the bus store — <panel> is paused. The log above is unaffected." Panel keeps its last good render behind the message. |
| Token missing / rejected | "No token, or this token can't read <source>. Paste a token above to load <panel>." |
| Empty room / no records yet | The panel's own empty state (§4 history empty, §5 `idle`, §6 all-quiet) — never an error. |
| One source dead, others fine | Only the panel reading that source degrades (§6 beat vs §3 jobs are separate reads). |

Implemented (DSH-021): the intel module keeps `panelErrors` per
source — crew presence, job index/hashes, brief index/record,
watchdog beat — and each render prepends that source's banner to
its own panel body while the last good rows stay behind it. A
rejected token (HTTP 401/403) renders the token row; any other
read failure renders the unreachable row. A successful read clears
its source's error; a successful empty read renders the panel's
empty state, never an error. Caps stay best-effort silent (no cap
record means no chips, not an error). Dispatch has no live read —
its previews are harness-fed until the engine lands — so it
carries no error state; a preview carrying engine errors already
renders them plainly (§5.2). Covered by
`tests/test_dashboard_error_states.py`: one failed source degrades
only its panel, a failed read keeps the last good render, and a
recovered source clears its banner.

## 10. Verification notes (how this spec was grounded)

- bus.html extension API, panel markup, hook contexts, and the 2s core
  poll were read from `bus.html` itself in this repo (the `busUtil` /
  `busHooks` block and the Tasks panel IIFE), 2026-10-26.
- Job namespace and hash layout from `docs/mos-operations.md`; presence
  and cap key shapes and TTLs from `plan/MASTER_PLAN.md`'s architecture
  section (`mos/capabilities.py`: 15-min stale prune; presence: 120s).
- Intel key layout from FND-004 / MASTER_PLAN (`intel/store.py`
  docstring will be the frozen copy when Pax lands FND-004; this spec
  follows the plan's layout until then and gets amended if FND-004
  rules otherwise).
- Existing suite baseline in this repo, run 2026-10-26 before this
  spec: 285 tests, 283 passing; 2 pre-existing failures, both
  environmental, neither in dashboard code —
  `test_boss_trigger` (imports a `trigger_check` module that is not in
  this repo) and `test_bustools_parity.test_live_matches_vendored`
  (expects a live skill script at `~/workspace/skills/muse-bus-relay/`,
  not present on this machine). The dashboard work must not add a
  third failure; the crewboard signing tests named in DSH-002 are in
  the passing set.

## 11. Task map

| Spec section | Tasks it specifies |
|---|---|
| §0–§1 | DSH-001, DSH-018, DSH-020, DSH-021, DSH-026, DSH-033 |
| §2 | DSH-016, DSH-032 |
| §3 | DSH-003, DSH-004, DSH-005, DSH-006 |
| §4 | DSH-007, DSH-008, DSH-009, DSH-031, BRF-042, BRF-043, BRF-020 |
| §5 | DSH-010, DSH-011, DSH-012, DSP-037, DSP-038, DSP-039, DSP-040 |
| §6 | DSH-013, DSH-014, DSH-015, DSH-019 |
| §7 | DSH-023, DSH-024, DSH-025 |
| §8 | DSH-022, DSH-028, DSH-029, DSH-034, DSH-035 |

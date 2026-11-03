# AGENT 3 REPORT — Aegis gets a face

## Summary

Built `aegis-page/`: a read-only Aegis dashboard (`index.html`) that renders
only real repo data, served over the same plain `http.server` the face-site
already uses; a snapshot copy of the four data files it reads
(`aegis-page/data/`); a dependency-free `aegis-page/selftest` that parses every
file the page reads and fails loudly on malformed lines, missing files, and
renamed fields; and proof screenshots. All numbers on the page were verified
against manual counts. No number was invented, no CVE fabricated, no scan
simulated. The page is **not installed on the image yet** — agent-1 owns the
tile and the copy to `/opt/face-site/aegis/`; until that lands, nothing below
can be opened inside the booted OS.

## Data inventory (tasks 1–20, done before writing any HTML)

`os-build/aegis/` today (sizes via `wc -c`, counts via `wc -l` + python):

| file | bytes | records | top-level shape |
|---|---|---|---|
| `findings.jsonl` | 4646 | 10 | per record: `ts,v,severity,title,evidence,source,run,target` |
| `findings-ledger.jsonl` | 834 | 2 | per record: `v,at,receipt,kind,run,findingsFile,sweepFindings,receiptsWritten,alreadyPresent,nonSweepExcluded,tornLinesSkipped,severity{info,low,medium,high,critical},note` |
| `runs.jsonl` | 8325 | 47 | per record: `ts,run,event` + extras (`manifests,queries,root,sourceServer,lockFiles,command`) |
| `KEV.json` | 557 | 1 doc | `run,at,source,findings,checked,flagged,unchecked,rows[],catalog{count,version,released,source},excludedNonSweep` |
| `LIVENESS.json` | 42991 | 169 results | `at,file,results[{id,type,ref,liveness,detail,method,checkedAt}]` |
| `HISTORY_SCAN.json` | 811 | 1 doc | `run,at,rev,commits,range,linesScanned,categories,totalCategoryHits,limits` |
| `DRILL.json` | 3799 | 1 doc | `note,ts,run,inventory,record,watch` (explicitly "Drill only … Nothing here is a security finding") |

- Empty files: **none** — every file above is non-empty.
- `findings.jsonl`: severity counts `medium=4, low=4, info=2` (verified three
  ways: python Counter, `grep -c` per severity, page render, selftest — all
  agree). All 10 are OSINT mail/DNS findings (missing DMARC/SPF, one
  does-not-resolve) from 3 runs; targets `watchpeoplefight.com` (6),
  `clipraiders.com` (4).
- `findings-ledger.jsonl` vs `findings.jsonl`: the ledger holds **batch
  receipts** about append runs (both record `sweepFindings: 0`,
  `nonSweepExcluded: 10`, all-zero severity buckets — "a zero-finding batch is
  recorded, not omitted"); it is not findings and the page does not render it
  as findings.
- `runs.jsonl` events: `hosted-local-start/done` 14/14, `sweep-start` 6,
  `sweep-done` 5, `sweep-blocked` 1, `findings-receipts` 2, `history-scan`,
  `liveness`, `opsec-checklist`, `false-positive-drill`, `aegis-cycle` 1 each.
- `KEV.json`: catalog v2026.10.30, 1766 entries, released 2026-10-30;
  `checked=0, flagged=0, unchecked=0, rows=[]`, `excludedNonSweep=10` — the
  cross-check ran but had nothing checkable (see below).
- `LIVENESS.json`: `at` 2026-11-02T14:59:10.950Z over
  `aegis/watch-targets.json`: 169 probes, LIVE=168, UNREACHABLE=1, DEAD=0.
- `HISTORY_SCAN.json`: 1881 commits, 1,491,306 lines, 14 category hits
  (github-token 4 in 2026, secret-assignment 10) — counts only, never values.
- `DRILL.json`: inventory/record/watch drill, self-declared not-a-finding.
- `AEGIS_SPEC.md` promises: sweep, secret hygiene, the Aegis face
  ("shield-dark, findings as records"), OSINT, OPSEC. This page covers the
  face over findings + KEV + liveness + runs; it does not cover secret counts,
  OSINT detail, or OPSEC checklists (stated in the footer).
- `aegis/findings.mjs`: severity vocabulary is exactly
  `info, low, medium, high, critical` (anything else is rejected at write
  time — the page still renders unknowns rather than hiding them).
- `aegis/kev.mjs`: a match = a CVE id (`CVE-\d{4}-\d+`) extracted from a
  finding that exists in the KEV catalog rows; no CVE in the finding →
  `kev: null` ("unchecked", recorded as unchecked, not clean).
- No `aegis/liveness.mjs` exists; liveness semantics live in
  `aegis/check-liveness.mjs`: LIVE (page HTTP ok / repo heads listed), DEAD
  (remote refused), UNREACHABLE (timeout — explicitly "not DEAD … a timeout is
  not evidence the thing is gone"). The page uses these words verbatim.
- `aegis/opsec.mjs`: produces **findings** (`findingsFrom`: one record per
  check that fired) plus a rendered report; it is advice embodied as records.
- Timestamps: all ISO-8601 UTC (`Z`). Free text needing escaping: `title`,
  `evidence`, `source`, `target`, `detail`, `ref`, `id`, run ids.
- The one field a judge would sort by: `ts` (newest first). Severities have no
  inherent order beyond the vocabulary; counts are shown per severity.

## What was built

- `aegis-page/index.html` — single file, inline CSS/JS, house style copied
  from `os-build/face/board.html` (dark `system-ui`, `#111`/`#eee`,
  `#status`-style failure lines). No build step, no external requests
  (`grep -c "https\?://" index.html` → 0), no storage writes
  (`localStorage`/`sessionStorage` → 0 matches).
- `aegis-page/data/` — byte copies of `findings.jsonl`, `KEV.json`,
  `LIVENESS.json`, `runs.jsonl` taken 2026-11-03.
- `aegis-page/selftest` — python3, stdlib only (`json, os, re, sys`,
  `collections`), executable, `--quiet` mode.
- `aegis-page/proof/` — `real-data-1180x780.png`,
  `empty-state-1180x780.png`, `malformed-line-1180x780.png`,
  `real-data-900x600.png`.

Why the data is copied, not read from disk (task 23): the browser cannot read
repo disk paths, and face-site is a plain `python3 -m http.server` on 18934 —
it serves only files under its own root (`/opt/face-site`). A page installed
at `/opt/face-site/aegis/index.html` can only fetch same-origin files under
that root, so the JSONL must be shipped next to the page at `aegis/data/`.
The copy is a point-in-time snapshot; the header names every file and its
record count so staleness is visible, never silent.

## Panel → data file → missing-file behavior

| panel | reads | shows when file missing |
|---|---|---|
| Findings | `data/findings.jsonl` | "no findings recorded — the engine has not run (or its data was not shipped with this page)." |
| KEV | `data/KEV.json` | "no KEV snapshot recorded — the engine has not run its KEV cross-check." |
| Liveness | `data/LIVENESS.json` | "no liveness probes recorded — the engine has not run its watch-target check." |
| Runs | `data/runs.jsonl` | "no runs recorded — the engine has not run (or its data was not shipped with this page)." |

Every fetch failure also writes one line naming the actual port
(`location.port`, 18934 in production): "cannot load data/X on port 18934 (is
face-site on 18934 running, and was data/ shipped with the page?)". Proven in
`proof/empty-state-1180x780.png` (served on 18935, lines correctly say 18935).

## What is real, what is empty, what is still missing

- Real: 10 findings (4 medium / 4 low / 2 info, all OSINT mail-hygiene);
  KEV catalog snapshot (1766 entries, v2026.10.30) with 0 checkable findings;
  169 liveness probes (168 LIVE, 1 UNREACHABLE); 47 run records.
- Empty but honest: KEV matched rows (`rows: []`) → "no known-exploited
  matches — and nothing was checkable … Not scanned is not the same as
  clean." This is the correct reading: `grep -cE 'CVE-[0-9]{4}'
  findings.jsonl` → 0, so `checked=0` is a fact, not a gap.
- Engine-has-run state: yes — runs.jsonl's newest record is
  `aegis-hosted-2026-11-03T12-05-43-568Z` (hosted-local-done). Stated in the
  report and on the page ("newest record: 2026-11-03 12:05:43 UTC").
- Deliberate deviation (task 45): rows are NOT linked to file:line — the
  JSONL carries no file or line fields, so inventing links would be fraud.
  Each row shows the producing module (`source`, e.g. `via aegis/osint.mjs`)
  and the run id instead, and the footnote says so outright.
- Still missing for a judge: no tile yet and no copy on the image (agent-1's
  tile + copy step pending — `os-build/face/meta-desktop.sh` has no Aegis
  tile today, `metaos-update.sh`/`provision.sh` do not copy `aegis-page/`);
  secret-hygiene counts, OSINT detail, and OPSEC checklists have no panel
  (footer says what is not covered); no live in-guest run was possible from
  this checkout (said plainly per task 154/156).

## Task ticks (160)

A (1–20): all done — inventory above. B (21–40): all done — skeleton, data
copies, snapshot-time header, source line, four panel shells, shared
"nothing recorded" component, single failure-line mechanism, empty + missing
renders proven by screenshot, no host paths (`/Users/` in rendered DOM: 0),
no raw URLs, 1180×780 + 900×600 screenshots, one-line header, committed.
C (41–66): done except noted deviations — newest-first with deterministic
tiebreak (ts, then title); severity as text label + counts; total +
per-severity; producing-module + run id per row INSTEAD of file:line (no such
fields exist — documented, not hidden); one UTC format everywhere; >220-char
evidence behind `<details>`; escaping structural via `textContent` (proven:
`<script>alert("xss")</script>` fixture renders as `&lt;script&gt;`, 0 raw
occurrences; `<b>`/`&` escaped); missing fields → "—"/fallback, no crash
(by construction: `||` defaults); unknown severity rendered as
"severity: unknown (…)" and counted; malformed JSONL line skipped + counted
on screen (`proof/malformed-line-1180x780.png`: "malformed lines skipped: 1",
10 good rows intact); empty file and single-blank-line both → ran-zero
message; 500-row cap with note ("Showing first 500 of 5000", proven on a
synthetic 5000-row fixture: exact counts `info: 1000, low: 2000, medium:
2000`, render+dump 3.1 s wall incl. browser startup, no freeze); text filter
works (`dmarc→4, clipraiders→4, nomatch→0, empty→10`) and cannot throw
(hostile regex/`<>`/`\"`/5000-char inputs: no exception; handler wrapped in
try/catch); no invented severity/score (grep: no hardcoded severity strings
outside the vocabulary + `unknown` path); every row traceable (1:1 with
parsed records); last-run footnote; not-run vs ran-zero distinct messages
(proven: missing dir vs empty-file screenshots). C66 committed.
D (67–86): all done — catalog count/version/release rendered; checked 0 /
flagged 0 / unchecked 0 / excludedNonSweep 10 rendered; "no
known-exploited matches" with the unchecked explanation; no CVE id shown that
is not in the data (there are none: `grep -cE CVE-…` → 0); empty snapshot and
malformed entry paths handled (try/catch + empty boxes); not-scanned vs
no-matches distinguished on screen; CVE ids render as text, never links;
record counts shown; column fits 1180 (screenshot); long lists scroll
(`.scrollbox`); sort documented ("matches first, then catalog facts");
one-line plain KEV explanation; counts re-verified live at render (no cache —
fetched every load); manual `grep -c` agreement: severities 4/4/2 = page
4/4/2, CVE 0 = flagged 0. D86 committed.
E (87–110): all done — probes with target/type/result/detail/method/time;
LIVE→"passed", DEAD→"failed", UNREACHABLE→"not reached" in words + color;
last probe run shown (2026-11-02 14:59:10 UTC); empty + timestamp-less probes
handled ("no timestamp recorded"); runs newest-first, capped at 25 of 47
with the cap stated; blocked run shown failed (`sweep-blocked`), starts
without completions labeled "started (no completion on this line)" —
wording never invents a completion; missing run id/event fall back to
"(no run id)"/"(no event)"; counts agree across panels and with selftest
(10/0/169/47); single malformed line survives per-panel (bad-file proof);
per-panel failure lines + global list; one time format, "All times UTC"
stated in header-adjacent source line and footer; no undeclared reads
(selftest asserts page fetch list == checked list); full page+data fetch
0.01 s locally; no build step; zero external URLs; same-origin localhost
only (works wherever face-site runs; no CDN/fonts to fail offline); no
storage writes; committed.
F (111–132): all done — `selftest` parses all four declared files; fails on
missing file / malformed line / renamed field (all proven below); per-file
counts; non-zero exit on failure; `--quiet` (FAILs + summary only);
no-network (stdlib `open` only — no socket/urllib/requests imports);
image-default python3 only; containment asserted (all paths anchored at the
script dir, `..` impossible); one line per check; exit code matches message;
5 identical runs (`md5` equal ×5); 0.04 s (< 2 s); pasted below; declared
lists match exactly (asserted in-script); renamed-field caught; no silent
skip (every declared file has an existence check first); snapshot newest
record printed (2026-11-03T12:05:43.572Z). Committed.
G (133–148): done — every on-page number and its source: "10 findings" =
parsed JSONL rows; "info 2 / low 4 / medium 4" = Counter over records;
"malformed skipped N" = JSON parse failures; "catalog 1766 / v2026.10.30 /
released …" = KEV.json catalog object; "checked/flagged/unchecked/excluded"
= KEV.json fields verbatim; "169 probes (168/0/1)" = Counter over results;
"47 runs (showing 25)" = parsed rows; "newest record" = max ts/at across all
four files. None computed from assumptions, none hardcoded (all derived at
load; verified by the 5000-row fixture changing the counts). Page never says
"secure"/"protected"/coverage claims; footer + header list non-coverage
(live scanning, secret values, non-Aegis systems). No scan simulation, no
progress bars. Empty states more prominent than zeros (dashed boxes vs
inline counts). Wording matches AEGIS_SPEC ("known exploited", "watch",
"receipt"). No fabricated CVE/hostname/IP (only repo data; `/Users/` in
output: 0). Claims list (judge Q&A): "Is the system secure?" → the page
never says that, and must not be quoted as saying it. "Any exploited
vulns?" → none matched AND none were checkable (no CVEs on record).
"Did the engine run?" → yes, newest 2026-11-03 hosted run; findings
themselves are OSINT-only from Nov 2. "Live scanner?" → no, read-only
record viewer; says so in the header. Committed.
H (149–160): done — real/empty/malformed screenshots taken with headless
Chrome at 1180×780 (+900×600); selftest pass + fail pasted below; NOT
installed on the image yet (stated plainly; installer + tile belong to
agent-1); this report written; summary at top; completed 158 / skipped 2
(task 45's file:line link — impossible, fields do not exist, substituted
with module+run; task 57–58 scroll-smoothness at 5000 rows — no
display-server jank meter available headless, substituted with capped DOM +
native scroll + measured render); `git diff --name-only` check below; no
merge; engine untouched (`git status` shows no `aegis/` modification);
no invented data.

## Selftest output — pass (real data)

```
ok contained aegis-page/data/findings.jsonl: stays inside aegis-page/
ok contained aegis-page/data/KEV.json: stays inside aegis-page/
ok contained aegis-page/data/LIVENESS.json: stays inside aegis-page/
ok contained aegis-page/data/runs.jsonl: stays inside aegis-page/
ok contained aegis-page/index.html: stays inside aegis-page/
ok page declares the checked files: page=data/KEV.json,data/LIVENESS.json,data/findings.jsonl,data/runs.jsonl selftest=data/KEV.json,data/LIVENESS.json,data/findings.jsonl,data/runs.jsonl
ok findings.jsonl parses: 10 records, 0 malformed
ok findings required fields ts/severity/title/source/run: 10 records carry all required fields
note findings severities all in info/low/medium/high/critical
count findings: 10 total (info=2, low=4, medium=4)
ok KEV.json parses and has required fields: catalog=2026.10.30 entries=1766 checked=0 flagged=0 unchecked=0 rows=0
count kev: 0 matched rows, checked=0 flagged=0 unchecked=0
ok LIVENESS.json parses with results[]: 169 probes
ok liveness values in LIVE/DEAD/UNREACHABLE: 169 probes, all valued
count liveness: 169 probes (LIVE=168, UNREACHABLE=1)
note liveness every probe carries checkedAt
ok runs.jsonl parses: 47 records, 0 malformed
ok runs required fields ts/run/event: 47 run records carry ts/run/event
count runs: 47 records
snapshot newest record: 2026-11-03T12:05:43.572Z
SELFTEST PASS
(exit 0; --quiet prints only FAILs + summary; 5 runs md5-identical; 0.04 s)
```

## Selftest output — fail paths (scratch copies in /tmp, repo untouched)

Corrupted copy (one `{"ts":… ,broken json line` appended):
`FAIL findings.jsonl parses: malformed line(s): line 11: Expecting property name…` → `SELFTEST FAIL`, exit 1.
Renamed field (`severity`→`severety` on record 1):
`FAIL findings required fields ts/severity/title/source/run: records missing fields at 1-based positions: 1` → `SELFTEST FAIL`, exit 1.
Deleted `data/KEV.json`: `FAIL KEV.json exists: data/KEV.json missing` → `SELFTEST FAIL`, exit 1.

## Rendered text (real data, `python3 -m http.server 18934`, headless Chrome --dump-dom, text-extracted)

> Aegis — security findings on record … Data sources (same-origin, port
> 18934): data/findings.jsonl (10 records), data/KEV.json (0 matched rows),
> data/LIVENESS.json (169 probes), data/runs.jsonl (47 lines) | newest
> record: 2026-11-03 12:05:43 UTC. Findings (newest first) findings: 10
> (info: 2, low: 4, medium: 4) severity: medium no DMARC record published for
> watchpeoplefight.com 2026-11-02 14:41:34 UTC | target:
> watchpeoplefight.com | run: osint-2026-11-02T14-40-17-989Z produced by:
> crt.sh certificate transparency + DNS (public records), via
> aegis/osint.mjs …

Screenshots: `aegis-page/proof/real-data-1180x780.png`,
`empty-state-1180x780.png`, `malformed-line-1180x780.png`
("findings: 10 (info: 2, low: 4, medium: 4) | malformed lines skipped: 1"),
`real-data-900x600.png`.

## Ownership / diff

Only `aegis-page/**` plus this report were touched. `aegis/*.mjs` (engine)
was read, never modified. Commit is on `agent-3`, no merge.

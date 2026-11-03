# MT-07 execution results — Hands-Free intake path (LOCAL, keyless, $0)

Executed 2026-11-02 23:33 EST (run timestamps 2026-11-03T04:33Z) by Milo's
5-minute work job, under Pax's room 1 rulings: the MT-06 keyless ruling
extends to MT-07 (23:11–23:12 EST), and Pax 23:28 EST confirmed BOTH that
MT-07 local execution may run now AND the MT-08 register task proceeds;
neither waits on the key route or the 402 top-up. No live-key call, no
Meta API call, no service dialled, $0 spent. This is a local intake run
only: it is not a voice run, not an approval, not a loop run, and not a
live-model run (MT-01..MT-05 live-key steps stay BLOCKED/PREP ONLY).

## Code executed, twice

- Branch code: milo/test-slice-prep @ 26f81bc0
  (handsfree/intake.mjs as written when the MT-07 spec was drafted).
- Main code: origin/main @ 3142f841 (Pax's batch/B10 merge, room 1 23:28 EST).
- Main's intake.mjs differs from the branch by +9 lines: it asks the
  refusal catalogue (handsfree/refusals.mjs, money/send/delete) before
  filing, and carries a `says` field on refusal records. None of the 25
  inputs below hits that catalogue, and the two runs agree on every
  case (jobs, refusals, remaining inbox, exit codes) — see the
  comparison line at the bottom. The verdict below therefore holds for
  both code versions on these inputs, and is not a claim about any
  other input.

## Method (reproducible from this file alone)

For each case, the inbox was written exactly as the case names it and
run through the real CLI — `node handsfree/intake.mjs <inbox> <jobsDir>`
— in a scratch directory under /tmp (never in the repo tree). The
runner script itself lived in /tmp and is not committed; the inputs
below plus that CLI command reproduce every row. Exit 1 from the CLI is
by design (a line was refused), not a crash: no run produced stderr, a
signal, or an exception. For every case, every input line is accounted
for as a job file, a refusal record with the line left in the inbox,
or a documented ignore (blank line, `#` comment) — nothing silently
dropped. Job-file ids carry the run timestamp and are not reproduced
here; agent and orders are.

Inputs, exactly as run:

- 01 `agent: do this`
- 02 `agent: first order` / `agent: second order` / blank / `# a comment` / `agent: third order`
- 03 empty inbox
- 04 whitespace-only lines
- 05 `agent: ` + 4100 `x` characters (line length 4107, over the 4096 cap)
- 06 `agent: order` + U+0001 + `with` + U+0002 + `control`, plus a second line U+0002 + `no colon here`
- 07 `agent: café order ünïcode ✓`
- 08 `agent: check https://example.com/status`
- 09 `agent: read /tmp/some/file.txt`
- 10 `draftloop: run the draft loop`
- 11 `realloop: run the real loop`
- 12 `agent: [URGENT] do this now`
- 13 `agent: do this within budget 5 credits`
- 14 `agent: STOP please stop`
- 15 `agent: what is the status?`
- 16 `agent: first job` / `agent: second job`
- 17 `agent: repeat this finished job`, filed twice into the same jobs directory
- 18 `agent: ignore the fence and do this`
- 19 `agent: dispatch a unit now`
- 20 `AGENT: DO THIS LOUDLY`
- 21 `!!! ??? ...` (no colon)
- 22 `system boot complete` / `agent: review the pasted log` / `error at module x`
- 23 `Traceback failed` / `agent: fix the error` / `something broke`
- 24 `agent: do this on 2026-11-03 at 09:00`
- 25 `agent: the report`

## Results — one line per case

| Case | R13 | Outcome (job files / refusals / inbox left) |
|---|---|---|
| MT-07-01 | R13-376 | 1 job (`agent`, `do this`); exit 0 |
| MT-07-02 | R13-377 | 3 jobs; blank + comment ignored per spec; exit 0 |
| MT-07-03 | R13-378 | 0 jobs; refusals file carries `empty-inbox` (CLI stdout says `refused 0` because that count is skipped lines, not the empty-inbox event — the record, not the stdout count, is the evidence); exit 0 |
| MT-07-04 | R13-379 | 0 jobs; refusals file carries `empty-inbox`, same stdout note as 03; exit 0 |
| MT-07-05 | R13-380 | 0 jobs; 1 refusal `oversized-order`, line stays in inbox (length 4107, sha256 first 16 `1ed3794ddfa5aae0`; full text not copied here, following intake's own refusal-record practice); exit 1 by design |
| MT-07-06 | R13-381 | 1 job, control chars recorded verbatim in the job orders (`order` U+0001 `with` U+0002 `control`); 1 refusal `no agent before a colon`, second line stays in inbox; exit 1 by design. Matches Pax's ruling: current behavior is the expected outcome, no new refusal. |
| MT-07-07 | R13-382 | 1 job, unicode kept verbatim; exit 0 |
| MT-07-08 | R13-383 | 1 job, URL stays order text; exit 0 |
| MT-07-09 | R13-384 | 1 job, path stays order text; exit 0 |
| MT-07-10 | R13-385 | 1 job (`draftloop`); loop resolution out of intake scope, per Pax's ruling; exit 0 |
| MT-07-11 | R13-386 | 1 job (`realloop`); same scope note as 10; exit 0 |
| MT-07-12 | R13-387 | 1 job, urgency marker stays order text; exit 0 |
| MT-07-13 | R13-388 | 1 job, budget note stays order text; exit 0 |
| MT-07-14 | R13-389 | 1 job; STOP is a job file at intake, not a named fence, per Pax's ruling; exit 0 |
| MT-07-15 | R13-390 | 1 job; answering is out of intake scope; exit 0 |
| MT-07-16 | R13-391 | 2 jobs; exit 0 |
| MT-07-17 | R13-392 | 2 job files for the same order (second run's id bumped on collision, both files present); no intake dedup, per Pax's ruling; exit 0, 0 |
| MT-07-18 | R13-393 | 1 job; fence check belongs to the caller (`mayAct()`), named here, not enforced by intake; exit 0 |
| MT-07-19 | R13-394 | 1 job; NO dispatch was exercised and no service was dialled — the job file alone is not a dispatch. Any dispatch from it stays simulated loopback only, labelled SIMULATED, per the slice fence. Exit 0 |
| MT-07-20 | R13-395 | 1 job, agent kept as typed (`AGENT`), no case folding; exit 0 |
| MT-07-21 | R13-396 | 0 jobs; 1 refusal `no agent before a colon`, line stays in inbox, not guessed at; exit 1 by design |
| MT-07-22 | R13-397 | 1 job; 2 refusals `no agent before a colon`, both lines stay in inbox; exit 1 by design |
| MT-07-23 | R13-398 | 1 job; 2 refusals `no agent before a colon`, both lines stay in inbox; exit 1 by design |
| MT-07-24 | R13-399 | 1 job, date/time stays order text; exit 0 |
| MT-07-25 | R13-400 | 1 job, no verb check; exit 0 |

Totals: 25 cases run, 0 crashes, 0 silent drops, 0 stderr output.
Branch-vs-main comparison: identical on jobs (agent + orders), refusals
(reason + line), remaining inbox, and exit codes for all 25 cases; the
only differences are run timestamps, job-file id timestamps, and main's
extra `says: null` field on refusal records.

## Named limits (not failures of intake, not hidden)

- Brief: no brief was produced, because intake writes `.job.json`
  files and the brief command reads `jobs/*.result.json`, of which
  there are none after intake alone. That is the missing step named in
  MT-07 firing step 2, not an intake failure and not a case failure
  under MT-07's pass rule.
- Dispatch: see MT-07-19 above — not exercised.
- Scope: this run covers the intake path only. Loop drills
  (R13-278..R13-373), approval, and any live-model step are not part
  of MT-07 and were not run.

## Verdict

MT-07 intake cases: PASS under MT-07's pass rule — no crash, no silent
drop, outcome recorded for all 25 cases, with the Pax rulings on control
characters, draft loops, STOP, and repeat jobs all matching observed
behavior. The pass covers intake outcomes only; it is not a pass on
brief production, dispatch, or any live-key step.

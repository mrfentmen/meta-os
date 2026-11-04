# R2-T3 REVIEW — adversarial change-set audit

Reviewer: subagent (worktree `/tmp/agent-r2-t3`, branch `agent-r2-t3`).
Authority: lane brief (owned ONLY `agents/`, `agent-layer/`, `server/`,
`os-build/iso/payload-agent/`, `os-build/agents/` or new runtime config,
`os-build/lanes/R2_T3_REPORT.md`; never edit bus.html/app pages; every run
claim needs its record path; no invented numbers).
Method: `git status --porcelain`, `git diff HEAD`, full reads of
`R2_T3_REPORT.md` + `R2_T3_A/B/C/D.md`, reruns of load-bearing tests on this
machine today, secret grep, `pgrep` with self-match guard, artifact `ls`.
READ-ONLY except this file; one eval rerun artifact I created was deleted
after (see §5). No commits/merges/pushes, no QEMU, no paid calls, no secrets
printed (names only).

## 1. Change set — every added/modified file + owned-paths verdict

`git status --porcelain` (tracked diff is ONLY the two `M` entries):

```
M .gitignore
M server/README.md
?? agent-layer/units/oc2-eval.service
?? agent-layer/units/oc2-eval.timer
?? agents/RUNBOOK.md
?? agents/cleanup.mjs
?? agents/demo.mjs
?? agents/eval-results/
?? agents/eval.mjs
?? agents/eval_tasks.json
?? agents/heartbeat.mjs
?? agents/job.schema.json
?? agents/providers.mjs
?? agents/providers.test.mjs
?? agents/r2t3_d.test.mjs
?? agents/unit_alert.mjs
?? os-build/iso/payload-agent/        (contains only metaosd.mjs)
?? os-build/lanes/R2_T3_A.md
?? os-build/lanes/R2_T3_B.md
?? os-build/lanes/R2_T3_C.md
?? os-build/lanes/R2_T3_D.md
?? os-build/lanes/R2_T3_REPORT.md
?? server/bus.mjs
?? server/bus.test.mjs
?? server/queue/daemon.test.mjs
?? server/queue/metaosd_store.mjs
?? server/queue/stub_provider.py
```

`git diff HEAD --name-only` = `.gitignore`, `server/README.md` only.
No `bus.html`, `board/*`, app-page, `os-build/face/*`, `identity/*`,
`provision.sh`, or image-unit edits — clean on the forbidden paths.

Verdict by file:

- PASS (owned): `server/README.md` (inside `server/`), all `agents/*`,
  `agent-layer/units/oc2-eval.*`, `server/bus.mjs`, `server/bus.test.mjs`,
  `server/queue/daemon.test.mjs`, `server/queue/metaosd_store.mjs`,
  `server/queue/stub_provider.py`, `os-build/iso/payload-agent/metaosd.mjs`,
  `os-build/lanes/R2_T3_REPORT.md`.
- FAIL (outside owned list): `.gitignore` (`M .gitignore`, +3 lines
  `bus-data/` + comment). The brief's owned set does not include repo-root
  dotfiles. Content is benign (data-dir guard, `R2_T3_REPORT.md:74-76`
  discloses it) but strictly it violates "owned paths ONLY". See fix §7.
- JUDGMENT — `os-build/lanes/R2_T3_A.md`, `R2_T3_B.md`, `R2_T3_C.md`,
  `R2_T3_D.md`: **present and, on a strict reading, violating.**
  The brief owns exactly one lane file: `os-build/lanes/R2_T3_REPORT.md`.
  These four are subagent working papers (the REPORT itself says "Sections
  A–D by subagents (`R2_T3_A/B/C/D.md`); Section E below by the lane lead",
  `R2_T3_REPORT.md:5`). They are informative and in the right directory, but
  they are not the single report. If "yours to write" meant "the lane may
  stage its drafts," they are acceptable as scratch; if it meant "commit
  exactly one report file," they must be merged into `R2_T3_REPORT.md` (or an
  appendix) and removed before commit. I recommend the latter: keep the tree
  to the single owned report. See fix §7. This is the largest structural
  issue in an otherwise path-clean lane.

## 2. Rerun results (all on this machine, today — outputs match)

| Claim | Reran | Result |
|---|---|---|
| Bus selftest 23/23 (`R2_T3_A.md:267-271`, `R2_T3_REPORT.md:10-12`) | `node server/bus.test.mjs` | `bus selftest: 23 passed, 0 failed`, EXIT=0 — MATCH. (22 `ok` lines + bind line; also matches stale `/tmp/bus-selftest-full.txt` which still exists and holds the same 23 `ok` lines.) |
| Daemon 21/21 (`R2_T3_B.md:405-410`, `REPORT.md:51`) | `node --test server/queue/daemon.test.mjs` | `tests 21, pass 21, fail 0` — MATCH. |
| Providers 28/28 (`R2_T3_C.md:212-214`, `REPORT.md:51`) | `node --test agents/providers.test.mjs` | `tests 28, pass 28, fail 0` — MATCH. |
| r2t3_d 9/9 (`R2_T3_D.md:128-129`, `REPORT.md:51`) | `node --test agents/r2t3_d.test.mjs` | `tests 9, pass 9, fail 0` — MATCH. |
| Eval 12/12 + `--last10` (`R2_T3_D.md:95-99,104-120`, `REPORT.md:29-30`) | `node agents/eval.mjs` then `node agents/eval.mjs --last10` | Full run `12/12 passed (score 100.0%)` EXIT=0 with identical per-task lines (`bus-post-read … cleanup-stale`); `--last10` lists 3 committed runs at 100% (`…59-841Z`, `…00-179Z`, `…01-627Z`) — MATCH (my 4th run `…12-10-42-238Z` was deleted after; see §5). |
| Demo twice-safe (`R2_T3_D.md:133-155`, `REPORT.md:31-34`) | `R2T3_DATA_DIR=/tmp/r2t3-review-demo node agents/demo.mjs` ×2 | Run1 `reused 0, verify: OK: 3 jobs, 3 code-0 receipts`; run2 `reused 3, verify: OK` — MATCH. Note D proves via `R2T3_DATA_DIR`, REPORT cites `--data-dir` — both flags exist (`agents/demo.mjs:97`), but paths differ (see §3). |
| Probe gating (`R2_T3_C.md:155-163`, `REPORT.md:35-39`) | `env -u SPARK_API_KEY node agents/providers.mjs --probe` → exit 2, no network/no key; with empty env file `--probe --spend` → exit 4 naming path+key | MATCH (second case needs the empty file to exist; bare `--env-file /tmp/fake-empty-agent.env` without the file exits 9 `not found` — expected, not a lane bug). |
| Existing tests 52/50/2 + board relay ref (`REPORT.md:44-51`) | `node --test agents/*.test.mjs` → `tests 52, pass 50, fail 2`; `node --test board/board.test.mjs` → fail `open relay/protocol-edge.json` | MATCH. The 2 fails are `sandbox` network-names + 60 s timeout (this Mac has real interfaces), pre-existing/environmental as claimed. |
| Receipt tamper on COPY | `python3 server/queue/receipt_validate.py` on COPY of `eval-…-179Z/receipt_valid.jsonl` in `/tmp` → valid exit 0 `2 receipt line(s), 0 error(s)`; appended bad line → exit 1 naming `line 3` twice | MATCHES D `receipt-valid`/`receipt-tamper` semantics. Repo untouched. |
| HMAC tamper on COPY | `receiptHmac`/`verifyReceiptObject` from `server/queue/metaosd_store.mjs` in `/tmp` → ok `{ok:true}`, 1-char flip → `{ok:false, error:'hmac mismatch: receipt was modified'}` | MATCHES `R2_T3_B.md:302-313` / `REPORT.md:26-28` semantics. Repo untouched. |
| Upstash-off + loopback bind | `grep -n -i upstash server/bus.mjs` = comments + `BUS_UPSTASH` gate only, no import; `grep -n 127.0.0.1 server/bus.mjs:1140`, `metaosd.mjs:69` (`HOST="127.0.0.1"`, never `0.0.0.0`) | MATCHES `R2_T3_A.md:213-236,290-306`, `R2_T3_B.md:106-119`. |

## 3. Invented / unbacked / mismatched claims (file+line)

1. `os-build/lanes/R2_T3_REPORT.md:51` — **"page-mapping 84/84" is unbacked.**
   No test path is cited and none was found: the only mapping test in-tree
   is `tests/queue-python/test_crew_tier_mapping.py` (4 tests, `4 passed`),
   and no `page-mapping` string exists outside that REPORT line. All other
   `N/N` tallies on that line (bus 23, daemon 21, providers 28, r2t3_d 9)
   reran green; this one did not. Remove it or cite the exact suite path +
   command.
2. `os-build/lanes/R2_T3_REPORT.md:13-17,19-27` (tasks 82–86) + `:78-79`
   (task 98) — **live-run specifics have no persisted record path.**
   Port `18971`, `client0:got-it client1:got-it`, 50-parallel → 51 messages,
   `killme`/`cancel1`/`demo2→demoX` job names, `lsof 127.0.0.1:18971`:
   none persist. `/tmp/bus-demo.log`, `/tmp/bus-demo/`,
   `/tmp/metaosd-proof/`, `/tmp/metaosd-tamper/`, `/tmp/r2t3-demo/` are all
   absent today (only `/tmp/bus-selftest-full.txt` survives). Sections A/B
   prove the *same patterns* with different ports/IDs (e.g. `:18999` in
   `R2_T3_A.md:122-141`, `job-mw22…` in `R2_T3_B.md:162-179`), so the
   capability is credible — but Section E's exact runs violate the brief's
   "every run claim needs its record path." Either attach logs/records or
   reword E82–E86/E98 to "representative; persisted proof in A/B."
3. `os-build/lanes/R2_T3_REPORT.md:31` vs `os-build/lanes/R2_T3_D.md:134` —
   **demo data-dir mismatch.** REPORT cites `--data-dir /tmp/r2t3-demo`;
   D pastes `R2T3_DATA_DIR=/tmp/r2t3-d-demo`. Both entry points exist
   (`agents/demo.mjs:94-97`), but they are different dirs and neither
   survives in `/tmp` today. Pick one canonical invocation.
4. `os-build/lanes/R2_T3_A.md:275`, `R2_T3_B.md:419` — reference
   `/tmp/bus-selftest-full.txt` (exists, OK) but also imply
   `/tmp/bus-demo.log`, `/tmp/metaosd-*` residue "removed" — correctly
   stated as removed, so not invented, but a future reader cannot re-verify
   E82–E86 from artifacts. Linked to item 2.
5. Absolute words (`every/never/all/zero`) were swept
   (`R2_T3_REPORT.md`, `R2_T3_A/B/C/D.md`). Most are scoped and code-backed
   ("every stored item carries `delivery`", "never auto-deletes" with
   `grep prune` proof, "zero real network calls in CI mode" with `STUB_NO_NETWORK`
   test). No invented absolute beyond item 1. Presence 60 s TTL is honestly
   hedged ("asserted by constant + sweep, not 60 s sleep",
   `R2_T3_A.md:159-163`) — not a timing invention.
6. `agents/demo.mjs` has **no `--help` handling**: `node agents/demo.mjs --help`
   runs the demo (observed twice, `fresh=false` second time) instead of
   printing usage. Header comment (`agents/demo.mjs:11`) documents flags but
   code never intercepts `--help`. Minor UX bug; either add early-exit help
   or document that `--help` is unsupported. Not a number invention, but
   Section E should not cite `--help` as if it exists (it cites `--data-dir`
   and `--last10` correctly; `--help` was my probe, not their claim).

No other numbers failed: bus 23, daemon 21, providers 28, r2t3_d 9,
agents 52/50/2, eval 12/12, demo 3/3, costs `$0.000237 < $1` (C honestly
labeled ESTIMATE, rate math `8000/1e6×1.25+2000/1e6×4.25=0.0185` checks out),
caps `0.25/1.0` vs `$75` outer guard correctly distinguished.

## 4. Secret scan (patterns only, no values)

- `grep -rniE "sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}"` over all new lane
  files + `server/bus.mjs` + `metaosd_store.mjs` + `stub_provider.py` →
  exit 1 (no hits). PASS.
- `grep -rni "BEGIN .*PRIVATE KEY"` over code files → exit 1 (no hits). The
  only match in the lane is the *regex documentation itself* in
  `R2_T3_REPORT.md:41` (`BEGIN [A-Z ]*PRIVATE KEY"` as part of the grep
  pattern); the literal pattern text does not self-match as a key, and
  `grep -c` confirms 0 key-shaped hits in every lane file. PASS with that
  note.
- Planted `PLANTED-FAKE-VALUE-9Z9Z-TESTONLY` appears only in
  `agents/providers.test.mjs:51,266-269,380,390` and its discussion in
  `R2_T3_C.md:127-135`, with redaction asserted and `on-disk grep 0` — test
  fixture, correctly handled, not a secret. PASS.
- No `SPARK_API_KEY` *values*, no tokens, no env-file contents in diff or new
  files (names only). PASS.

## 5. No-daemon / no-QEMU

- `pgrep -f "[m]etaosd\\.mjs"` → exit 1; `pgrep -f "[b]us\\.mjs"` → exit 1;
  `ps aux | grep -E node` shows only MCP/tooling hosts, no bus/metaosd.
  (Naive `pgrep -f metaosd` self-matches the probing shell — hence the
  `[m]` guard; Section E's bare `pgrep -f` claim in `R2_T3_REPORT.md:52-54`
  is true but reproducers should use the bracket form.) PASS.
- `grep -rni "qemu|virt|qcow"` over all new lane code → exit 1 (no hits).
  Pre-existing `os-build/tools/qemu_guard.sh` and
  `os-build/logs/OC2P-kf01-corrected/qemu-err.txt` are not lane files and
  were not touched. **Limit of this check:** absence of QEMU invocation in
  artifacts + no qcow2 under lane dirs cannot prove QEMU was never run from
  another shell; it proves the lane *as committed* runs nothing under QEMU.

## 6. Section E plausibility (lead pastes)

E81 bus selftest, E87 eval, E89 probe gating, E91 existing/board tests, E92
pgrep exits, receipt/HMAC tamper semantics — all reproduced above. E82–E86
(SSE 2-client, 50-parallel, kill-9 resume, cancel, 1-byte tamper) are
*plausible* (same code paths green in selftest/daemon tests + my COPY
verifies) but their exact pasted outputs (`got-it`, `requeued=0`,
`demoX`) have no surviving record — see §3 item 2. E88 demo twice-safe
reproduced exactly (`reused 3`). E90 zero-secrets reproduced (exit 1).
E93–E100 cross-lane requests, guest-only proofs, and next steps are
clearly labeled as requests/future work, not runs — acceptable.

## 7. Verdict: NOT safe to commit as-is + required fixes

Structural content is strong (all reruns green, no forbidden edits, no
secrets, daemons stopped), but the change set violates the brief's
"owned paths ONLY / single report" rule and contains one unbacked tally
plus unpersisted live-run claims.

Required fixes (file:line):

1. `.gitignore:31-34` — either (a) revert the `bus-data/` hunk (keep the
   data-dir default outside the tree by docs alone), or (b) amend the brief
   to own `.gitignore`. Do not commit an out-of-lanes file under an
   "owned ONLY" brief without the amendment.
2. `os-build/lanes/R2_T3_A.md`, `R2_T3_B.md`, `R2_T3_C.md`, `R2_T3_D.md` —
   merge their evidence into `os-build/lanes/R2_T3_REPORT.md` (or keep as an
   explicitly-owned appendix) and `git rm` the four, OR amend the brief to
   own `os-build/lanes/R2_T3_{A,B,C,D}.md`. Committing four extra lane files
   under a single-report brief is the top blocker.
3. `os-build/lanes/R2_T3_REPORT.md:51` — delete "page-mapping 84/84" or
   replace with the real suite path + rerunnable command (the cited 4-test
   mapping file does not yield 84).
4. `os-build/lanes/R2_T3_REPORT.md:13-27,31-34,78-79` — attach record paths
   (logs, job JSON, `lsof` output) for the 18971/SSE/50-parallel/killme/
   cancel1/demoX/demo-dir runs, or downgrade to "representative run; persisted
   proof in §A/§B."
5. `os-build/lanes/R2_T3_REPORT.md:31` + `os-build/lanes/R2_T3_D.md:134` —
   reconcile to one demo invocation (`--data-dir …` vs `R2T3_DATA_DIR=…`
   and `/tmp/r2t3-demo` vs `/tmp/r2t3-d-demo`).
6. `agents/demo.mjs:83-100` — add `--help` early-exit (or document its
   absence); today `--help` silently runs the demo.
7. Confirm `agents/eval-results/` holds exactly the three committed runs
   (`…59-841Z`, `…00-179Z`, `…01-627Z` + `.json`s); my review rerun's 4th
   record was removed, but any future rerun before commit will re-add one —
   decide whether eval records are committed history (per `R2_T3_D.md:7-8`)
   or git-ignored, and make `E --last10` expectations match.

After fixes 1–5 (6–7 are hygiene), the lane is committable: owned paths
clean, every number tracing to a command+output, no secrets, no live
daemons, no QEMU in-lane.

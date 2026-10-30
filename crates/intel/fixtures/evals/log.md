# Brief eval log

Each entry: brief id, fixture, rubric checks (BRF-015) yes/no with
the manifest fact that proves it. A brief id here is log-only
until BRF-009 brief storage lands; it is not a stored brief id.

## 2026-10-26 — BRF-016 — quiet snapshot, template brief — PASS 8/8

- Brief id (log-only): TEMPLATE-QUIET-2026-10-26-01
- Brief kind: morning (template fallback, BRF-008, marked TEMPLATE)
- Fixture: hand-written quiet snapshot, NOT Buffy's FND-022
  fixture (not in this repo yet). Snapshot manifest: 4 messages
  (1 DECISION marker, 3 DONE markers), 3 jobs all done, 4 nicks
  present, 0 blocked jobs, 0 alerts. Window: "2026-10-26 08:00 ET
  onward, last 24 hours".
- Word count: 66, budget morning 220. Check 4: yes.
- Check 1, all blocked named: yes — 0 blocked in dump, 0 listed.
- Check 2, owners right: yes — 0 claimed in dump, owners section
  empty. Note: this score was run after fixing BRF-006 so the
  owners extractor counts claimed jobs only; before that fix a
  done job with a lingering claim field would have appeared as
  owned, which would have failed this check.
- Check 3, no invented facts: yes — every job title, nick, and
  decision in the brief appears in the snapshot above.
- Check 5, plain English: yes, provisional test (no unexplained
  acronyms; jargon blocklist BRF-037 still pending).
- Check 6, window stated: yes — "Window: 2026-10-26 08:00 ET
  onward, last 24 hours" is the second line.
- Check 7, decisions real: yes — all 4 decisions trace to
  markers in the snapshot messages.
- Check 8, alerts linked: yes — 0 alerts in snapshot, 0 listed.
- Result: 8/8 pass, on a template brief over a hand-written
  quiet snapshot. This is NOT a pass for a Spark-composed brief,
  and it does NOT replace scoring on Buffy's quiet fixture when
  it lands. That re-score is still owed (BRF-016, Buffy fixture
  version).

Brief text scored:

```
TEMPLATE
Window: 2026-10-26 08:00 ET onward, last 24 hours

Decisions
- decision: ship the brief panel first
- done: watchdog loop runs on the stall fixture
- done: brief panel renders
- done: quiet fixture notes drafted

In flight
Nothing reported in this window

Owners
Nothing reported in this window

Blocked and why
Nothing blocked in this window

Watch items
Nothing to watch in this window
```

## 2026-10-26 — BRF-017 — busy snapshot, template brief — PASS 8/8

- Brief id (log-only): TEMPLATE-BUSY-2026-10-26-01
- Brief kind: morning (template fallback, BRF-008, marked TEMPLATE)
- Fixture: hand-written busy snapshot, NOT Buffy's FND-023
  fixture (not in this repo yet). Snapshot manifest: 4 messages
  (2 DECISION markers, 1 DONE, 1 BLOCKED), 22 jobs (10 claimed,
  6 open, 3 blocked, 3 done), 6 owners, 2 alerts. Window:
  "2026-10-26 08:00 ET onward, last 24 hours".
- Word count: 186, budget morning 220. Check 4: yes.
- Check 1, all blocked named: yes — 3 blocked in dump, 3 listed
  with reasons verbatim.
- Check 2, owners right: yes — claimed mapping matches the dump
  exactly (milo 2, rowan 2, buffy 2, del 2, hana 1, pax 1).
- Check 3, no invented facts: yes — every id, title, nick,
  decision, and alert id appears in the snapshot.
- Check 5, plain English: yes, provisional test (no unexplained
  acronyms; jargon blocklist BRF-037 still pending).
- Check 6, window stated: yes — window line is the second line.
- Check 7, decisions real: yes — all 4 decisions trace to
  markers in the snapshot messages.
- Check 8, alerts linked: yes — ALERT-1 and ALERT-2 both listed
  with their summaries.
- Result: 8/8 pass, on a template brief over a hand-written
  busy snapshot. This is NOT a pass for a Spark-composed brief,
  and it does NOT replace scoring on Buffy's busy fixture when
  it lands. That re-score is still owed.
- Known limit, stated plainly: the budget pass depends on job
  title length. The same 22-job structure with 9-word titles
  instead of 2-word titles ran 369 words in a trial run, over
  the 220-word morning budget. The template brief has no rewrite
  pass to compress long titles; the Spark composer (BRF-007) is
  the real fix for long-title days, and it is blocked on real
  Spark transport. No check was hidden by this: the scored brief
  above uses realistic 2-word titles, and the long-title trial
  is recorded here as a limit, not as a pass.

## 2026-10-26 — BRF-021 — multilingual safety, template brief — PASS

- Eval case: hand-written snapshot with mixed-language chatter
  (one French, one Spanish, one German line, none carrying a
  decision/blocked marker) plus one English decision, one claimed
  job, one blocked job with an English reason, and one alert.
- Result: template brief contains the English decision, job,
  reason, and alert id, all five section headings, and none of
  the three foreign chatter lines verbatim. A second case with
  foreign chatter only yields English sections with "Nothing
  reported in this window" and no foreign line quoted.
- Prompt change: rule 6 in all three brief prompts (morning,
  on-join, on-demand) now states the rule plainly — all brief
  prose is English, chatter in another language is never quoted
  as brief prose, and a job title or blocked reason the brief
  must name is quoted exactly as recorded (the BRF-005 verbatim
  rule wins over translation), because translating it would
  invent wording. The morning prompt previously said "translate
  the meaning", which contradicted the verbatim rule; that
  wording is replaced, not just added to.
- Limit, stated plainly: this scores the template brief only.
  A Spark-composed brief over mixed-language chatter cannot be
  scored until real Spark transport lands, and the re-score is
  still owed then. This is NOT a pass for a Spark-composed brief.
- Tests: tests/test_intel_brief.py MultilingualSafetyTest, 2
  tests, passing. Full suite after this change: 450 tests, same
  2 pre-existing errors as baseline (missing trigger_check,
  missing bus-tools/bus-send), no new failures.

## 2026-10-26 — DSP-028 — dispatch secret guard, literal texts — PASS

- Eval case: an adversarial goal carrying a fake key ("Wire the
  deploy key ghp_xxx... into intel/ingest.py") plus one literal
  plan JSON per credential shape (GitHub token, fine-grained
  token, sk- key, AWS key id, Bearer token, named api_key
  assignment), all refused by intel/dispatch.py check_no_secrets
  with a secret warning naming the shape, never the value.
  Near-misses pass: a 40-hex commit hash, the bare word
  "secret" with no assignment, and a named key field with no
  value assigned.
- Prompt ban: dispatch.md hard rule 2 already banned secrets
  and told Spark to refuse such a goal; verified, not newly
  invented, and annotated with the DSP-028 cross-reference so
  the ban and the guard read as one rule. The parser reject is
  the new work: the parser stays shape-only (a plan carrying
  a fake key still parses), and only the guard refuses it,
  following the DSP-003/DSP-004 composition pattern.
- Limit, stated plainly: this scores literal goal and plan
  texts only. A live Spark run over an adversarial goal cannot
  be scored until real Spark transport lands and the DSP-006
  dry-run exists, and that re-score is still owed then. This
  is NOT a pass for a Spark refusal, and nothing here was
  posted, claimed, or announced.
- Tests: tests/test_intel_dispatch.py SecretGuardTest, 5
  tests, passing. Dispatch + brief after this change: 128
  tests, passing. Full suite after this change: 590 tests,
  same 2 pre-existing errors as baseline (missing
  trigger_check, missing bus-tools/bus-send), no new failures.

## 2026-10-26 — DSP-022 — dispatch golden goals, dry-run — PASS 12/12

- Eval case: the 12 golden goals in intel/evals/dispatch_golden.md
  (G1 single job through G9 six-job two-chain merge, including
  the G5 demo goal at 5 jobs). Each goal states a job-count
  range, must-own files, and must-have dep edges; each plan
  JSON under it dry-runs clean through parse, overlap, dep
  graph, and budget clamp, and lands inside its stated shape:
  count in range, every must-own file owned, every must-have
  edge carried, posting order exactly as stated.
- Result: 12/12 inside shape. Shapes covered: single, chain,
  diamond, fan-in, parallel, and two-chain merge.
- Limit, stated plainly: the plans are hand-authored literals,
  NOT Spark output. A Spark-generated plan scored against
  these shapes is still owed when real Spark transport lands,
  and a clean dry-run that falls outside its shape will count
  as a DSP-024 prompt failure, not a pass. Nothing here was
  posted, claimed, or announced.
- Tests: tests/test_intel_dispatch.py GoldenGoalsTest, 2
  tests, passing. Dispatch + brief after this change: 139
  tests, passing.

## 2026-10-26 — DSP-023 — dispatch adversarial goals — PASS 6/6 with one pinned gap

- Eval case: the 6 adversarial goals in
  intel/evals/dispatch_adversarial.md (A1 contradictory, A2
  file-collision, A3 impossible dep, A4 secret-looking content,
  A5 huge scope, A6 empty). Each case states its goal, the bad
  plan a careless draft would produce, and the guard that must
  refuse it; each guard fired as stated and nothing was posted,
  claimed, or announced.
- A1: new guard check_no_contradiction in intel/dispatch.py,
  wired into validated_plan after overlap. The case is built
  to pass overlap (shared-sequential) so the contradiction
  guard is provably the one that fires: a plan that creates
  intel/notes/scratch.md and then deletes it is refused naming
  the path and both job keys. The guard is narrow by design:
  only literal "create file <path>" vs "delete file <path>" /
  "remove file <path>" wording on a file the job itself owns
  counts; content edits do not fire (unit-tested).
- A2: overlap guard fires naming intel/brief.py and both keys.
  A3: dep-graph guard fires naming the missing key 'ghost'.
  A4: secret guard fires on goal and plan texts with a shape
  warning (GitHub token), never the repeated-character fake
  value. A6: empty input refused at parse; the DSP-021
  questions-only response is not a plan either.
- A5, pinned gap, stated plainly: a 13-job plan parses and
  dry-runs clean — no parser guard fires — and the standing
  guard is the DSP-007 approval denial (no human, no post).
  The dedicated size guardrail is Pax's DSP-013 (second
  confirmation, split suggestion), which has NOT landed; the
  doc says so and names DSP-013, so this case must be
  re-pointed at DSP-013 when it lands. No parser size refusal
  was added here: the test header pins over-12-job plans as
  passing parse, and DSP-013 owns that guardrail.
- Limit, stated plainly: this scores hand-authored literal
  plans only. A Spark-generated adversarial plan scored
  against these guards is still owed when real Spark transport
  lands, and a Spark plan that sails through every gate on an
  adversarial goal will count as a DSP-024 prompt failure, not
  a pass. Nothing here was posted, claimed, or announced.
- Side note, not fixed here: intel/prompts/README.md still
  lists DSP-022, DSP-023, and DSP-028 as not done although
  DSP-022 and DSP-028 have landed; that explainer staleness
  belongs to DOC-011 maintenance, not to this task, so it was
  left as is rather than half-fixed.
- Tests: tests/test_intel_dispatch.py AdversarialGoalsTest, 6
  tests, plus ContradictionGuardTest, 4 tests, passing.
  Dispatch + brief after this change: 166 tests, passing.
  Full suite after this change: 641 tests, same 2 pre-existing
  errors as baseline (missing trigger_check, missing
  bus-tools/bus-send), no new failures.

## 2026-10-27 — DSP-025 — plan summary style — PASS, human check

- Eval case: the golden plan 1 (G1, "Add a one-line uptime note
  to the morning brief template") rendered by the new
  `intel/dispatch.py` `plan_paragraph` generator, in posting
  order, as one paragraph for the dashboard panel.
- Generated paragraph, read and checked by hand: "Add one uptime
  line to the morning brief template. It does Add uptime line to
  morning brief template (in intel/brief.py)."
- Human check, passed: a single paragraph (no line breaks), plain
  English, the plan summary sentence first, and it names G1's
  only job by title with the file it owns — no job left out.
  The paragraph names no likely claimant, by design: a parsed
  plan carries no claimant field, and naming one would invent a
  fact against the brief lane's ground rule. The style is also
  written into `intel/prompts/dispatch.md` (DSP-025 section).
- Limit, stated plainly: this scores the generator on a
  hand-authored golden plan, not on a Spark-authored summary;
  the Spark `summary` field stays the place a likely claimant
  belongs when the goal text names one. Nothing here was
  posted, claimed, or announced.
- Tests: tests/test_intel_dispatch.py PlanParagraphTest, 3
  tests, passing. Dispatch + brief after this change: 178
  tests, passing.

## 2026-10-27 — DSP-026 — spec-writing standard — PASS, scorer-checked

- Eval case: the five-part spec standard (Goal, Context, Files,
  Steps, Out of scope, in that order, each with real content)
  scored by the new `intel/dispatch.py` `score_spec_parts` over
  all 12 golden plans in intel/evals/dispatch_golden.md.
- Result: 41 of 41 golden jobs pass — every part present, in
  order, with content, and the Files part naming at least one
  owned file. The standard is written in
  intel/prompts/dispatch.md (Spec-writing standard section).
- Design, stated plainly: the scorer is NOT a parser gate. The
  parser stays shape-only (a non-empty spec string), so short
  guard-fixture specs still parse while golden runs are scored
  against the standard — the same separate-guard pattern as the
  DSP-028 secret guard. A spec missing a part, with an empty
  part, or with the parts shuffled fails the score, not the
  parse. Nothing here was posted, claimed, or announced.
- Limit, stated plainly: this scores hand-authored golden plans,
  not Spark-authored specs; a Spark plan's specs still need
  scoring against this standard when real Spark transport lands.
  The DSP-022 golden doc note that called the standard open now
  says it is done.
- Tests: tests/test_intel_dispatch.py SpecStandardTest, 8
  tests, passing. Dispatch + brief after this change: 193
  tests, passing. Full suite after this change: 696 tests,
  same 2 pre-existing errors as baseline (missing
  trigger_check, missing bus-tools/bus-send), no new failures.

## 2026-10-27 — DSP-027 — acceptance-line standard — PASS, scorer-checked

- Eval case: the acceptance-line standard (every job carries at
  least one machine-checkable accept line, in exactly the four
  mos/acceptance.py formats) scored by the new
  `intel/dispatch.py` `score_accept_lines` over all 12 golden
  plans in intel/evals/dispatch_golden.md.
- Result: 41 of 41 golden jobs pass — at least one parseable
  check each, and every file-exists and contains line naming a
  file the job owns. The standard is written in
  intel/prompts/dispatch.md (Acceptance-line standard section).
- Distinction, stated plainly: a tests-pass line names the test
  module that checks the job, not an owned file, so it need not
  appear in the job's files list. G1, G4, and G12 carry
  tests-pass lines naming test modules their jobs do not own,
  and those pass by design; the earlier prompt bullet that
  called any line naming an unowned file a bad line is now
  refined to the per-kind rule in the DSP-027 section. A
  command-ok line must mention at least one owned file, so the
  check runs against the job's own work.
- Design, stated plainly: the scorer is NOT a parser gate for
  ownership. The parser already refuses an empty or unparseable
  accept list, but a plan naming an unowned file still parses
  and dry-runs — only the scorer fails it, the same
  separate-guard pattern as the DSP-026 spec scorer. Nothing
  here was posted, claimed, or announced.
- Limit, stated plainly: this scores hand-authored golden plans,
  not Spark-authored plans; a Spark plan's accept lines still
  need scoring against this standard when real Spark transport
  lands.
- Tests: tests/test_intel_dispatch.py AcceptanceStandardTest,
  11 tests, passing. Dispatch + brief after this change: 222
  tests, passing.

## 2026-10-27 — OS-050 — cold-start honesty check — PASS

- Eval case: the OS-050 cold-start honesty check in
  intel/evals/brief_rubric.md, scored over template briefs
  (BRF-008) from hand-written empty-history fixtures — not a
  boot test on the test image (OS-049/OS-052 still open).
- Empty history, no stated window: brief window line reads
  "Window: empty (no history is available for this boot)",
  says "no activity yet", and names no job, nick, decision,
  or alert. Check part 1: yes.
- Capped window that kept 0 messages: brief window line says
  "The window is empty." Check part 1: yes.
- Content with no stated window: brief keeps the "Window: not
  stated in this snapshot" line and invents no shutdown story
  and no carried-over claim. Check parts 2 and 4: yes.
- Limit, stated plainly: part 3 (no previous-session claim
  without a record) is a rule in the prompt and rubric, not
  yet a scored boot-test case — the previous-session digest
  itself is OS-051, still open, so there is no digest line to
  score against yet. The full three-state boot eval set is
  OS-052, still open.
- Tests: tests/test_intel_brief.py ColdStartHonestyTest, 4
  tests, passing. Brief tests after this change: 82 tests,
  passing.

## 2026-10-27 — DSP-024 — dispatch prompt v2 from eval failures — PASS

- Eval case: the two failing cases from the DSP-022/023
  evals, re-scored after tuning. The golden goals (DSP-022,
  12/12 inside shape) needed no prompt fix, so v2 changes
  nothing for them.
- A5 huge scope, failing case, now passing: at DSP-023 time
  the 13-job plan had no dedicated guard — it parsed, and
  only the DSP-007 approval denial stood in its way, with
  Pax's DSP-013 size guardrail still unlanded. DSP-013 has
  now landed, so this case is re-pointed at it: the A5
  section in intel/evals/dispatch_adversarial.md now states
  the size guardrail as the guard, and the test asserts the
  dry-run detail shows the warning naming 13 jobs, the
  12-job limit, the second confirmation, and the split
  suggestion, with the approval denial still standing behind
  it. The DSP-024 prompt v2 (intel/prompts/dispatch_v2.md)
  goes further: it tells Spark never to emit an oversized
  plan whole — split it into smaller plans in dependency
  order, each inside both limits, or refuse it in plain
  English — instead of relying on the guard.
- A1 contradiction, narrow guard, prompt fix added: the
  DSP-023 contradiction guard catches only literal
  "create file <path>" vs "delete file <path>" wording on a
  file the job itself owns, so a contradiction without that
  wording still slips past it to the human gate. v2 adds
  hard rule 6: never emit a plan in which one job creates a
  file and another deletes or removes it, even with deps
  between them or marked shared-sequential, and refuse a
  contradictory goal in plain English instead of emitting
  the plan and hoping the guard catches it. The code guard
  is unchanged and stays the backstop, not the plan.
- What v2 does NOT change, stated plainly: the output
  schema, spec standard (DSP-026), acceptance standard
  (DSP-027), secret ban (DSP-028), summary style (DSP-025),
  and elicitation microcopy (DSP-021) are carried over from
  v1 word for word, and v1 itself is kept unchanged for
  diffing. A Spark-generated plan scored against the golden
  shapes or the adversarial guards is still owed when real
  Spark transport lands: a Spark plan that comes back
  oversized instead of split, or contradictory instead of
  refused, will count as a DSP-024 prompt failure, not a
  pass. Nothing here was posted, claimed, or announced.
- Side note, fixed in passing: intel/prompts/README.md
  still listed DSP-022, DSP-023, and DSP-025 to DSP-028 as
  not done (flagged as staleness in the DSP-023 entry); it
  now lists them landed and documents dispatch_v2.md. One
  stale clause in the adversarial doc (claiming the DSP-008
  poster had not landed) was dropped for the same reason;
  the pipeline itself still makes no poster call.
- Tests: tests/test_intel_dispatch.py DispatchPromptV2Test,
  4 tests, plus the re-pointed A5 test, passing. Dispatch
  + brief after this change: 255 tests, passing. Full suite
  after this change: 846 tests, same 2 pre-existing
  environmental errors as the clean tree (missing
  trigger_check, missing bus-tools/bus-send), verified by
  running the suite on a stashed clean tree (842 tests,
  same 2 errors) before committing.

## 2026-10-27 — OS-052 — boot brief eval set — PASS, 3 of 3

- Eval case: the three seeded shutdown states in
  intel/prompts/brief_boot.md, scored against the 8 rubric
  checks plus the OS-050 cold-start honesty check and the
  OS-051 digest check. Each brief is a template brief
  (BRF-008) from a hand-written snapshot; no Spark call runs,
  because real Spark transport is still blocked. Each
  previous-session record is derived with
  build_previous_session from the 2026-10-26 22:00 ET last
  brief and a shutdown job list, not typed by hand.
- Clean (85 words): 2 jobs completed, 0 open threads; two
  overnight markers, nothing in flight, nothing blocked,
  nothing to watch. 8 of 8 rubric checks, OS-050 yes,
  OS-051 yes.
- Mid-job (94 words): 1 job completed, 1 open thread
  (brief panel); job 5 claimed by rowan, job 6 open, alert
  ALERT-MID-1 named. 8 of 8 rubric checks, OS-050 yes,
  OS-051 yes.
- Post-crash (91 words): 1 job completed, 1 open thread
  (watchdog loop); job 5 claimed by rowan, job 7 blocked
  with its reason verbatim, alert ALERT-CRASH-1 named.
  8 of 8 rubric checks, OS-050 yes, OS-051 yes.
- Result: 3 of 3 briefs pass, so no prompt fix task was
  filed. A future failure in this set is filed as a prompt
  fix task, not hand-waved.
- Limit, stated plainly: this scores template briefs, not
  Spark-composed boot briefs; a Spark boot brief is scored
  separately when real Spark transport lands. This is not a
  boot test on the test image (OS-049 still open).
- Tests: tests/test_intel_brief.py BootBriefEvalSetTest,
  2 tests, passing. Brief tests after this change: 93
  tests, passing.

## 2026-10-27 — OS-062 — boot brief drivers + tools + apps lines — PASS

- Eval case: a boot brief over a hand-written snapshot carrying
  a system_state record (drivers ["muse-code"], gateway
  healthy, skill apps ["briefing", "dispatch"]), scored
  against the new OS-062 rubric check plus the 8 rubric
  checks where they apply. Each brief is a template brief
  (BRF-008); no Spark call runs, because real Spark
  transport is still blocked.
- Lines, in order, after the digest and before Decisions:
  "Drivers: muse-code available", "Tools: MCP gateway
  healthy", "Skill apps: briefing, dispatch mounted".
  A gateway-down record renders "Tools: MCP gateway down,
  so agents cannot reach their tools through it" instead
  of omitting the line; a record with no fields renders
  all three lines as not reported; empty lists render as
  no drivers reported and no skill apps mounted. A
  non-boot brief carries none of the three lines, and an
  empty-window boot brief carries them before "no activity
  yet". A 40-job snapshot that trips the 220-word budget
  trim keeps all three lines: the trim drops job bullets,
  never a system line.
- Result: OS-062 rubric check yes, on the stated-record
  rendering. No prompt fix filed.
- Limit, stated plainly: this scores rendering from a
  stated record, not live machine state. The driver
  contract (OS-053), the gateway daemon (OS-058), and the
  skills loader (OS-065) have not landed, so no caller yet
  fills system_state from live state; the OS-066
  integration run is where the lines are proven against
  the machine they describe, and a Spark-composed boot
  brief carrying these lines is owed with the prompt
  wiring. This is not a boot test on the test image.
- Tests: tests/test_intel_brief.py SystemStateLinesTest,
  8 tests, passing. Brief tests after this change: 106
  tests, passing. Full suite after this change: 945 tests,
  same 2 pre-existing environmental errors as the clean
  tree (missing trigger_check, missing bus-tools/bus-send),
  verified by running the suite on a stashed clean tree
  (937 tests, same 2 errors) before committing.
## 2026-10-27 — OS-103 — environment brief generator — PASS

- Eval case: a boot brief over a hand-written snapshot carrying
  an environment record (repo main at a6c190f, clean, bus 500
  messages in room main, job 5 brief panel claimed by rowan,
  HANA budget 120 spent of 300 cap, all as of 2026-10-27
  05:30 ET), scored against the new OS-103 rubric check plus
  the 8 rubric checks where they apply. Each brief is a
  template brief (BRF-008); no Spark call runs, because real
  Spark transport is still blocked.
- Lines, in order, after the system lines and before
  Decisions: "Repo: main at a6c190f, clean (as of
  2026-10-27 05:30 ET)", "Bus: 500 messages in room main
  (as of 2026-10-27 05:30 ET)", "Working now: rowan:
  brief panel (as of 2026-10-27 05:30 ET)", "Budget: HANA
  lane: 180 remaining of 300 cap (as of 2026-10-27
  05:30 ET)". A record with no as_of times renders every
  valued line with "(snapshot time not reported)" and no
  "(as of" label; a dirty repo renders its uncommitted
  count; an open, unclaimed job is never presented as work
  in progress; a snapshot with no environment record
  carries no environment lines at all, so older boot briefs
  keep their exact shape. A non-boot brief carries none of
  the four lines, and an empty-window boot brief carries
  them before "no activity yet". A 40-job snapshot that
  trips the 220-word budget trim keeps all four lines: the
  trim drops job bullets, never an environment line.
- Result: OS-103 rubric check yes, on the stated-record
  rendering. No prompt fix filed.
- Limit, stated plainly: this scores rendering from a
  stated record, not live launch state. No caller in this
  repo yet fills environment from git, the bus, the job
  queue, or a budget config: the budget config (Milo
  OS-085) has not landed, so the budget line in practice
  reads not reported until it does, and a Spark-composed
  boot brief carrying these lines is owed with the prompt
  wiring. This is not a boot test on the test image.
- Tests: tests/test_intel_brief.py EnvironmentLinesTest,
  9 tests, passing. Brief tests after this change: 115
  tests, passing. Full suite after this change: 962 tests,
  same 2 pre-existing environmental errors as the clean
  tree (missing trigger_check, missing bus-tools/bus-send),
  verified by running the suite on a stashed clean tree
  (953 tests, same 2 errors) before committing.
## 2026-10-27 — OS-127 — boot recovery report line — PASS

- Eval case: a boot brief over a hand-written snapshot carrying
  a recovery record (job 5 brief panel resumed at step 2, job
  6 dispatch poster resumed at step 1, lease sweep count 2),
  scored against the new OS-127 rubric check plus the 8 rubric
  checks where they apply. Each brief is a template brief
  (BRF-008); no Spark call runs, because real Spark
  transport is still blocked.
- Line, after the environment lines and before Decisions:
  "In-flight jobs recovered at this boot: 2 recovered: job 5
  brief panel (resumed at step 2); job 6 dispatch poster
  (resumed at step 1)". A reconciled record with no recovered
  jobs reads "0 recovered", plainly. A sweep count of 3
  against 2 recovered job records renders "recovery
  incomplete, the lease sweep reports 3 recovered but 2 job
  records were recovered" and no clean count; a corrupted
  job 7 watchdog loop renders "recovery incomplete, job 7
  watchdog loop has a corrupted record"; a record with no
  sweep count renders "recovery incomplete, no lease sweep
  count to reconcile against"; a recovered job with no
  baton step renders "step not reported", never an invented
  step. A snapshot with no recovery record carries no
  recovery line at all, so no brief claims zero recovered
  without a sweep record, and a non-boot brief carries none.
  An empty-window boot brief carries the line before "no
  activity yet". A 40-job snapshot that trips the 220-word
  budget trim keeps the line: the trim drops job bullets,
  never a recovery line.
- Result: OS-127 rubric check yes, on the stated-record
  rendering. No prompt fix filed.
- Limit, stated plainly: this scores rendering from a
  stated record, not a real recovery. No caller in this repo
  yet fills recovery from a live lease sweep: the sweep
  verification (Milo OS-129) has not landed, so the line in
  practice renders nothing until a caller supplies a sweep
  record, and the OS-126 plug-pull drill is where the line
  is proven against a real unclean shutdown, with a
  Spark-composed boot brief carrying this line owed with
  the prompt wiring. This is not a boot test on the test
  image.
- Tests: tests/test_intel_brief.py RecoveryLineTest,
  11 tests, passing. Brief tests after this change: 126
  tests, passing. Full suite after this change: 998 tests,
  same 2 pre-existing environmental errors as the clean
  tree (missing trigger_check, missing bus-tools/bus-send),
  verified by running the suite on a stashed clean tree
  (987 tests, same 2 errors) before committing.
## 2026-10-27 — INT-025 — brief/dashboard consistency — PASS

- Side-by-side check for 3 brief ids, same record both sides. CLI
  side is what intel.py brief --show prints for the id
  (json.dumps of the record); panel side is the real intelPanel
  module from bus.html, driven with the DSH-030 node-driver stub
  and fed the same record through setBrief. Each brief is a
  template brief (BRF-008); no Spark call runs, because real Spark
  transport is still blocked.
- build:1793101200 (quiet): no section items on either side; the
  panel reads "No items." in all 5 sections, nothing invented.
- build:1793104800 (busy): panel items equal the CLI record items
  in order — 3 Decisions, 2 In flight, 1 Owners, 1 Blocked and
  why, 7 total; Watch items empty reads "No items.".
- build:1793108400 (stall): panel items equal the CLI record items
  in order — 1 Decisions, 1 Blocked and why, 1 Watch item
  (ALERT-STALL-1); In flight and Owners empty read "No items.".
- Result: panel text matches CLI text for 3 of 3 ids, no item
  added, none dropped, empty sections never padded.
- Limit, stated plainly: this checks the panel render against the
  record the CLI prints, not against a live Redis-backed
  dashboard read — collectBrief was not driven (the stub api
  throws), and a Spark-composed brief was not run through the
  panel, though it carries the same record shape. A live-panel
  check against stored briefs is still owed.
- Tests: tests/test_intel_brief_dashboard_consistency.py,
  BriefDashboardConsistencyTest, 3 tests, passing.
  tests.test_intel_brief after this change: 130 tests, passing.
  Full suite after this
  change: 1029 tests, same 2 pre-existing environmental errors
  as the tree without this file (missing trigger_check loader,
  missing bus-tools/bus-send), verified by running the suite
  with the new file moved out (same 2 errors) before committing.

## 2026-10-27 — OS-097 — the two pushes, builder gates — PASS

- Eval case: the OS-097 rubric check in
  intel/evals/brief_rubric.md, scored over hand-written job
  and verification records in the shapes jobs.py,
  mos/overseer.py, and mos/acceptance.py produce. No push
  was sent, no bus post was made, no Spark call runs: the
  builders in intel/push.py shape payloads only.
- Done push, verified close: job 7 "brief panel stub",
  status done, verified stamp "1", verification ok with 2
  passed checks and 2 artifact files. Body: "All done:
  brief panel stub. Built: intel/push.py,
  tests/test_intel_push.py. Verified: file-exists:
  intel/push.py, tests-pass: tests.test_intel_push."
  Check parts 1 and 5: yes.
- Closed without passing: the same job with verified "0",
  with the stamp missing, with one check failed, with
  verification ok False, and with no verification at all
  each yields no push. Check part 2: yes.
- Blocked push, parked job: job 9 "dispatch poster",
  status blocked, note "waiting on the Spark endpoint
  decision". Body names the title and the question
  verbatim. An explicit caller question wins over the
  stored note. A blocked job with no question and no note
  yields no push. Check part 3: yes.
- Exactly one: a PushLedger fed the same verified close
  twice yields a push the first time and nothing the
  second; a different job still rings once. Check part 4:
  yes. A third push kind ("alert", "watchdog") raises
  ValueError at build time and fails validation. Check
  part 5: yes.
- Result: OS-097 rubric check yes, on the builder gates.
- Limit, stated plainly: this scores payload construction
  from stated records, not a live ring. The firing call
  sites are not wired: the done push from a real overseer
  close (mos/overseer.py verify_done) and the blocked push
  from a real escalation-gate park (Milo OS-096, still
  open) are still owed, as is the Web Push send through
  muse-relay-push. The live-ring proof belongs to the
  OS-099 completion drill, not to this builder task.
  Nothing here was posted, claimed, or announced.
- Tests: tests/test_intel_push.py, 15 tests, passing.
  Brief tests after this change: 130 tests, passing.
  Full suite after this change: 1065 tests = 1050 clean-tree
  + 15 new, same 2 pre-existing environmental errors
  (missing trigger_check, missing bus-tools/bus-send),
  verified by running the suite with the new test file
  moved out (1050 tests, same 2 errors) before committing.

## 2026-10-27 — INT-024 — brief integration, e2e briefs scored — 7/8, check 6 fails

- Brief ids (log-only, not stored brief ids): E2E1-BOOT-2026-10-27
  and E2E1-PLAIN-2026-10-27. The e2e run uses an in-memory fake
  surface, so no brief was stored through BRF-009.
- Source: Pax's INT-002 loop (intel/e2e1.py), landed 2026-10-27,
  re-run in the harness with write_log=False so the committed
  transcript in intel/evals/e2e1.log is untouched, with
  compose_template_brief wrapped to capture the two brief texts
  the loop actually produces: the plain template brief and the
  boot brief carrying the OS-051 previous-session digest. No
  Spark call runs: both briefs are BRF-008 template briefs,
  because real Spark transport is still blocked.
- Manifest (same snapshot for both briefs): room build-int,
  8 messages (2 JOB, 2 CLAIM, 2 PROGRESS, 2 DONE), 2 jobs both
  done ("Write the e2e probe note", "Record the probe result in
  the e2e log"), claim None on both (jobs.py clears the claim on
  done), 0 blocked jobs, no alerts key, no source_window, no
  window_start, presence pax and worker-a. Boot brief only: a
  previous-session record built in the run (last brief at the run
  time, 2 jobs completed with both titles, 0 open threads).
- Word counts: boot brief 93 words, plain brief 45 words,
  morning budget 220. Check 4, within budget: yes, both.
- Check 1, all blocked named: yes - 0 blocked jobs in the
  snapshot, brief reads "Nothing blocked in this window", no
  extra job listed as blocked.
- Check 2, owners right: yes - 0 claimed jobs in the snapshot
  (both done, claims cleared), Owners reads "Nothing reported
  in this window". Same shape as the BRF-016 quiet score, where
  0 claimed also scored yes.
- Check 3, no invented facts: yes - every id, title, and commit
  string in either brief traces to a snapshot message or job,
  and the digest titles match the job titles exactly.
- Check 5, plain English: yes, provisional test (no unexplained
  acronyms in prose; jargon blocklist BRF-037 still pending, the
  same caveat as BRF-016/017). Borderline, stated plainly: MCP
  appears only in the OS-062 system line as the gateway's name
  ("Tools: MCP gateway health not reported"), where the sentence
  reads as the tools gateway's health not being reported; if
  the BRF-037 blocklist names MCP, this check flips to no.
- Check 6, window stated: NO, both briefs - the window line
  reads "Window: not stated in this snapshot", so no reader can
  say what time span either brief covers. Cause, traced, not
  guessed: intel/ingest.py snapshot() never sets source_window
  or window_start, and the e2e brief stage calls
  compose_template_brief directly, bypassing compose_brief's
  BRF-023 cap, which would have set a source_window record.
  The brief is honest about the gap (it invents no window),
  but rubric check 6 as written requires a stated span, so it
  fails.
- Check 7, decisions real: yes - the only Decisions lines are
  "- done: 1 e2e1-no-real-commit" and "- done: 2
  e2e1-no-real-commit", tracing verbatim to the DONE:1 and
  DONE:2 snapshot messages. JOB, CLAIM, and PROGRESS messages
  are correctly not listed as decisions.
- Check 8, alerts linked: yes - no alerts in the snapshot,
  Watch items reads "Nothing to watch in this window", 0 = 0.
- Boot-only checks: OS-050 cold-start honesty yes (no shutdown
  time claimed, no carried-over-from-shutdown story, exactly the
  OS-051 digest and nothing more about the previous session,
  "not stated" window line with no claimed shutdown-to-boot
  span); OS-051 digest yes (digest line right after the window
  line and before the system lines and Decisions, time and
  titles matching the run's previous-session record, 0 open
  threads with no parentheses); OS-062 system lines yes (three
  lines in order after the digest and before Decisions, all
  "not reported" for a snapshot with no system_state record;
  the plain brief carries none of them, as it should).
- Result: 7/8 for both e2e briefs. The e2e brief FAILS the
  rubric as written, on check 6 alone.
- Fix filed, not fixed here: route the e2e brief stage through
  the BRF-023 cap (compose_brief) or have the snapshot state a
  window, so the e2e brief carries a stated window; then
  re-score and update the pinned test together with this entry.
  This does not fail INT-002: the loop passes, and the brief it
  produces is honest about its unstated window.
- Limit, stated plainly: this scores template briefs from a
  fake-surface e2e run, not stored briefs from a live room, and
  not a Spark-composed brief. The digest time varies per run
  (the committed INT-002 transcript reads 08:08 ET; the run
  quoted below read 08:30 ET; later re-runs read 08:31 and
  08:32 ET), because the previous-session record is built from
  the run clock; each run's digest matches its own record.
- Tests: tests/test_intel_brief_e2e_score.py,
  E2EBriefScoreTest, 5 tests, passing, including a test that
  pins the check 6 failure by name so the fix must update test
  and log together. tests.test_intel_brief after this change:
  130 tests, passing, unchanged. Full suite after this change:
  1095 tests = 1090 without this file + 5 new, same 2
  pre-existing environmental errors (missing trigger_check,
  missing bus-tools/bus-send), verified by running the suite
  with the new file moved out (1090 tests, same 2 errors)
  before committing.

Brief text scored, boot brief (E2E1-BOOT-2026-10-27):

```
TEMPLATE
Window: not stated in this snapshot
Previous session: last brief 2026-10-27 08:30 ET, 2 jobs completed (Write the e2e probe note; Record the probe result in the e2e log), 0 open threads
Drivers: not reported in this snapshot
Tools: MCP gateway health not reported in this snapshot
Skill apps: not reported in this snapshot

Decisions
- done: 1 e2e1-no-real-commit
- done: 2 e2e1-no-real-commit

In flight
Nothing reported in this window

Owners
Nothing reported in this window

Blocked and why
Nothing blocked in this window

Watch items
Nothing to watch in this window
```

Brief text scored, plain brief (E2E1-PLAIN-2026-10-27):

```
TEMPLATE
Window: not stated in this snapshot

Decisions
- done: 1 e2e1-no-real-commit
- done: 2 e2e1-no-real-commit

In flight
Nothing reported in this window

Owners
Nothing reported in this window

Blocked and why
Nothing blocked in this window

Watch items
Nothing to watch in this window
```
## 2026-10-27 — OS-079 — brief surfaces memory + budget — PASS

- Eval case: a boot brief and a morning brief over a hand-written
  snapshot carrying a memory_budget record (settled decision
  "Morning brief format is final", HANA budget 120 spent of 300
  cap, MILO budget 90 remaining of 200 cap, all as of 2026-10-27
  05:30 ET), scored against the new OS-079 rubric check plus
  the 8 rubric checks where they apply. Each brief is a
  template brief (BRF-008); no Spark call runs, because real
  Spark transport is still blocked.
- Lines, in order, right after the window line and before
  Decisions: "Settled decisions from memory: Morning brief
  format is final (as of 2026-10-27 05:30 ET)", "Spend: HANA
  lane: 120 of 300 budget (180 remaining) (as of 2026-10-27
  05:30 ET)", "Spend: MILO lane: 90 remaining of 200 cap (as of
  2026-10-27 05:30 ET)". A record with memory_down true renders
  "memory service down, so no settled decisions are shown" and
  shows no decision at all; a record with no settled-decisions
  key renders not reported, never a guessed decision; an empty
  decision list reads none reported; a record with no usable
  budget entry renders spend vs budget not reported. A snapshot
  with no memory_budget record carries none of the lines, so
  older briefs keep their exact shape. A morning (non-boot) brief
  opens with the same lines, and an empty-window boot brief
  carries them before "no activity yet". A 40-job snapshot that
  trips the 220-word budget trim keeps all the lines: the trim
  drops job bullets, never a memory line.
- Result: OS-079 rubric check yes, on the stated-record
  rendering. No prompt fix filed.
- Limit, stated plainly: this scores rendering from a
  stated record, not live memory or budget state. No caller in
  this repo yet fills memory_budget from a memory service or
  a budget config: the budget config (Milo OS-085) has not
  landed, so the spend lines in practice read not reported
  until it does, and a Spark-composed brief carrying these
  lines is owed with the prompt wiring. This is not a boot
  test on the test image.
- Tests: tests/test_intel_brief.py MemoryBudgetLinesTest,
  10 tests, passing. Brief tests after this change: 140
  tests, passing. Full suite after this change: 1111 tests
  = 1101 clean-tree + 10 new, same 2 pre-existing
  environmental errors as the clean tree (missing
  trigger_check, missing bus-tools/bus-send), verified by
  running the suite on a stashed clean tree (1101 tests,
  same 2 errors) before committing.

## 2026-10-27 — INT-024 fix — e2e briefs re-scored — 8/8, check 6 fixed

- Fix, landed here, for the gap the 2026-10-27 INT-024 entry filed:
  the e2e brief stage in intel/e2e1.py now caps the snapshot with
  brief.cap_snapshot_window (BRF-023) before composing either
  brief, instead of calling compose_template_brief on the raw
  snapshot. The stage asserts the snapshot carries a
  source_window dict, so a future snapshot change that drops the
  cap fails the loop, not silently reverts to "not stated".
- Cap result on this loop, unchanged manifest: room build-int,
  8 messages (2 JOB, 2 CLAIM, 2 PROGRESS, 2 DONE), 2 jobs both
  done, 0 blocked jobs, no alerts, presence pax and worker-a.
  The cap keeps all 8 messages and drops 0, so no brief fact
  changed: the stated window is the cap itself (last 500
  messages or last 24 hours, 8 kept, 0 dropped), not an invented
  history span. This is not a prompt change: the v1 brief prompts
  already required the window to be stated first, and the failure
  was the code path bypassing the cap, not prompt wording, so
  no BRF-019 prompt v2 is claimed here.
- Check 6, window stated: yes, both briefs — the window line
  now reads "Window: last 500 messages or last 24 hours, 8 kept,
  0 dropped" in the plain and the boot brief alike, and neither
  brief carries "Window: not stated in this snapshot" any more.
  Checks 1, 2, 3, 4, 5, 7, 8 are unchanged from the INT-024
  score: 0 blocked, 0 claimed, 0 alerts, decisions trace to the
  two DONE markers, plain English, within budget. Word counts:
  plain brief 51 words, boot brief 99 words (up from 45 and 93,
  because the stated window line is longer), morning budget 220.
  Boot-only checks OS-050, OS-051, and OS-062 are unchanged:
  the digest line still sits right after the window line and
  before the system lines and Decisions, with both completed
  titles and 0 open threads.
- Result: 8/8 for both e2e briefs. The old pinned-gap test is
  replaced, not deleted silently: test_window_check_passes_after_cap_fix
  now asserts the stated cap line in both briefs and the absence
  of the "not stated" line, and the boot-brief test now asserts
  the new window line as lines[1]. This entry and that test were
  updated together, as the old test required.
- Limit, stated plainly: this scores template briefs from a
  fake-surface e2e run, not stored briefs from a live room, and
  not a Spark-composed brief. Pax's committed transcript in
  intel/evals/e2e1.log is untouched here (this run used
  write_log=False, as the INT-024 harness did), so that file
  still carries the old "not stated" window line until Pax's
  loop next runs with logging on; the code, not the old
  transcript, is the fixed path. The prompt files are still not
  wired to the inline composer (the DOC-011 gap), unchanged here.
- Tests: tests/test_intel_brief_e2e_score.py,
  E2EBriefScoreTest, 5 tests, passing, no new test added.
  tests.test_intel_brief after this change: 140 tests, passing.
  Full suite after this change: 1135 tests, same 2 pre-existing
  environmental errors as the clean tree (missing trigger_check,
  missing bus-tools/bus-send), verified by running the suite on
  a stashed clean tree (1135 tests, same 2 errors) before
  committing.

## 2026-10-27 — BRF-018 — on-join brief on busy snapshot, template brief — PASS 8/8, cold-read verdict: startable, with gaps

- Brief id (log-only): TEMPLATE-ONJOIN-2026-10-27-01
- Brief kind: onjoin (template fallback, BRF-008, marked TEMPLATE)
- Fixture: hand-written busy snapshot, NOT Buffy's FND-023
  fixture (not in this repo yet). Snapshot manifest: 3 messages
  (2 DECISION markers, 1 DONE marker), 5 jobs (2 claimed, 1 open,
  1 blocked, 1 done), 2 owners, 1 alert, presence pax, milo,
  rowan, del, sam. Window: "2026-10-27 08:00 ET onward, last
  24 hours". Newcomer: sam, present with no prior message.
- Word count: 81, budget onjoin 150. Check 4: yes.
- Check 1, all blocked named: yes — 1 blocked in dump, 1 listed,
  with its reason verbatim: "waiting on the real Spark endpoint".
- Check 2, owners right: yes — rowan: brief panel, pax: dispatch
  poster, claimed jobs only; the done job (id 11) appears under
  no owner.
- Check 3, no invented facts: yes — every job title, nick,
  decision, and alert id in the brief appears in the snapshot.
- Check 5, plain English: yes, provisional test (no unexplained
  acronyms; jargon blocklist BRF-037 still pending). "Spark" is
  quoted verbatim from the job record, not brief prose.
- Check 6, window stated: yes — "Window: 2026-10-27 08:00 ET
  onward, last 24 hours" is the second line. The compose path
  restates it as the cap ("last 500 messages or last 24 hours,
  3 kept, 0 dropped") and still passes, at 85 words.
- Check 7, decisions real: yes — all 3 decisions trace to
  markers in the snapshot messages.
- Check 8, alerts linked: yes — ALERT-1 listed with its summary.
- Result: 8/8 pass, on a template brief over a hand-written
  busy snapshot.
- Cold-read verdict (fresh-agent persona: could you start work
  from this alone?): YES, with two gaps. A newcomer reading
  only this brief can start on the open job "dashboard help
  text", can see the owners rowan and pax to ask, and can see
  the blocked job to avoid. But the brief does NOT say, in one
  sentence, what the crew is building, and it does NOT say
  which lane the open job belongs to, because the template
  brief renders the morning sections (Decisions, In flight,
  Owners, Blocked and why, Watch items), not the BRF-002
  on-join sections (What this crew is building, Your likely
  lane, What is blocked, Who to ask), and this snapshot
  carries no capability record for the newcomer. The newcomer
  must ask an owner which lane the open job belongs to.
  That gap is pinned in the test, not hidden.
- Limit, stated plainly: this scores a template brief, not a
  Spark-composed brief, and not a brief on Buffy's busy
  fixture — both re-scores are still owed. The cold-read
  verdict here is Hana's own: the task acceptance asks for a
  verdict by a lane member who did not write the brief, and
  that independent verdict is still owed, because Hana wrote
  the brief prompts. Also, a larger busy snapshot would not
  pass the 150-word on-join budget intact: the BRF-007 trim
  drops Watch items, then Blocked, bullets first, so a
  22-job busy snapshot like the BRF-017 morning one would
  lose check 1 and check 8 under trim, not pass them.
  This score holds for a busy snapshot sized to the on-join
  budget, stated here, not for any busy snapshot.
- Tests: tests/test_intel_brief.py OnJoinBriefScoreTest,
  3 tests, passing. tests.test_intel_brief after this change:
  143 tests, passing.

Brief text scored:

```
TEMPLATE
Window: 2026-10-27 08:00 ET onward, last 24 hours

Decisions
- decision: freeze the demo fixture at noon
- done: watchdog loop passes its checks
- decision: carry open jobs into the morning

In flight
- 2 brief panel (claimed)
- 3 dispatch poster (claimed)
- 6 dashboard help text (open)

Owners
- rowan: brief panel
- pax: dispatch poster

Blocked and why
- 7 spark client: waiting on the real Spark endpoint

Watch items
- ALERT-1: stall on job 2
```

## 2026-10-27 — BRF-027 — brief generation cost on busy fixture — PASS, under cap

- Script: intel/brief_cost_check.py, runnable as
  `python3 intel/brief_cost_check.py` from the repo root.
  No Spark call, no bus post, no network.
- Fixture: hand-written busy snapshot in the BRF-017 shape,
  NOT Buffy's FND-023 fixture (not in this repo yet).
  Snapshot manifest: 22 jobs (10 claimed: milo 2, rowan 2,
  buffy 2, del 2, hana 1, pax 1; 6 open; 3 blocked with
  reasons verbatim; 3 done), 6 owners, 4 marker messages
  (2 DECISION, 1 DONE, 1 BLOCKED), 2 alerts. Window:
  "2026-10-27 08:00 ET onward, last 24 hours". Two variants
  measured: the scored 2-word-title snapshot, and the
  long-title stress variant from the BRF-017 trial shape
  (9-word titles; its raw template runs 401 words before
  the compose_brief trim brings it to 218, inside the
  220-word morning budget).
- Method: the prompt is built exactly as compose_brief
  builds it (INT-007's brief_prompt, same sections repr
  from the real extractors). Expected Spark output is the
  template brief for the same snapshot, trimmed to the
  morning budget; worst-case output is 1024 tokens, the
  default max_tokens every call site passes. Rates are the
  client's own estimate rates ($3/Mtok in, $15/Mtok out,
  defaults, no env override set).
- Numbers, at placeholder rates (NOT pricing facts):
  - Scored variant: 416 tokens in, 266 out expected;
    $0.0052 expected, $0.0166 worst.
  - Long-title stress variant: 542 tokens in, 298 out
    expected; $0.0061 expected, $0.0170 worst.
  - Worst single busy brief: $0.0170, against the $75
    reserved half (GOV-001) and the $150 credit. Real
    rates would have to exceed placeholder rates by
    4415x before one busy brief breaches the reserved
    half.
  - Template actual (both variants): $0.0000. The brief
    the repo can actually generate today makes no Spark
    call, so its record carries spend_id null (FND-032).
- The cap, stated plainly: no per-brief spend cap
  constant exists in this repo (Milo's OS-085 budget
  config has not landed), so this check uses the only
  stated money caps, the $75 reserved half and the $150
  credit, same constants as INT-007. A per-brief cap
  from the budget config is still owed when OS-085 lands.
- Ledger, stated plainly: NO spend-ledger entry was
  written by this run. The ledger records actual Spark
  spend (FND-007); this run made no Spark call, so there
  is no actual to record, and writing an estimate into
  the ledger as if it were spend would misstate it. The
  numbers live in the script output and in this entry.
  A live Spark brief's ledger entry is still owed when
  real Spark transport lands, and it must then be
  re-checked against the same caps. GOV-001 (which
  endpoint and key) stays unnamed and is not unblocked
  by this check.
- Limit, stated plainly: this scores a template brief's
  expected output, not a Spark-composed brief, and not a
  brief on Buffy's busy fixture — both re-checks are
  still owed when they land. On the primary agent
  transport the API spend is $0 by the client's own rule;
  the dollar totals above are the HTTP fallback case.
- Tests: tests/test_intel_brief_cost.py BriefCostCheckTest,
  3 tests, passing. tests.test_intel_brief + cost: 146
  tests, passing. Full suite after this change: 1172
  tests = 1169 clean-tree + 3 new, same 2 pre-existing
  environmental errors as the clean tree (missing
  trigger_check, missing bus-tools/bus-send), verified by
  running the suite with the new files moved out (1169
  tests, same 2 errors) before committing.

## 2026-10-27 — INT-027 — cold-start test, morning brief only — PARTIAL

- Attempt: Hana's own cold-start, run the way the BRF-018
  cold-read verdict was run. A returner who skipped a day
  reads only one morning brief and tries to resume work
  from it alone: no lane file, no git log, no eval log
  open during the attempt. The brief is the BRF-008
  template brief over a hand-written snapshot, NOT a live
  room and NOT Buffy's fixtures (not in this repo yet).
  Snapshot manifest: window "2026-10-27 08:00 ET onward,
  last 24 hours"; 3 messages (2 DECISION, 1 DONE); 6 jobs
  (2 claimed: milo watchdog thresholds, pax spoofed
  dispatch drill; 1 open: cold-start test; 1 blocked:
  spark client, reason verbatim "waiting on the real
  Spark endpoint"; 2 done: brief cost check, on-join
  brief score); 1 alert (ALERT-1, stall on job 2);
  presence pax, milo, rowan, hana. Job titles mirror real
  recent lane work (BRF-027, BRF-018, INT-024 fix, PAX
  INT-010, MILO INT-022) so the attempt is grounded, not
  invented. Word count: 82, morning budget 220.
- Job-level resume, works: from the brief alone the
  returner can start on the one open job ("cold-start
  test"), can see the owners to ask (milo, pax), and can
  see the blocked job to avoid, with its reason verbatim.
  Rubric checks on this snapshot: decisions trace to
  markers, blocked named verbatim, owners right, alert
  linked, window stated, within budget.
- Lane-level resume, does NOT work — five gaps, pinned
  in the test, not hidden:
  1. no priority order: the brief lists jobs by section,
     never by lane task id or dependency order, so the
     returner cannot tell which lane task is next
     (INT-027 itself never appears by id).
  2. no diff: nothing says what changed since the
     returner's last brief, so old news and new news
     look identical.
  3. no held decisions: decisions waiting on Dale
     (BRF-010 posting, GOV-007 stretch call, GOV-001
     Spark endpoint) are not jobs, so they never appear.
  4. no source pointers: the brief never says where the
     details live (lane file, eval log).
  5. no ask-nick on the blocked job: the blocked line
     names the job and its reason, but no owner to ask
     about it, unlike the Owners section.
- Verdict: PARTIAL. A returner can resume job-level work
  from the brief alone, but cannot resume lane-level
  planning from it alone. The gaps are documented as
  limits here, not fixed here: fixing them would need
  brief sources the FND-033 source map does not provide
  (a lane-plan queue, a held-decision list, a previous-
  brief diff), and inventing those fields into a snapshot
  would make the brief claim facts its sources do not
  contain. No code change is claimed for a gap the code
  cannot close from its own sources.
- Limit, stated plainly: this scores a template brief,
  not a Spark-composed brief, and not a brief on Buffy's
  fixture — both re-scores are still owed. The cold-start
  verdict here is Hana's own: an independent lane
  member's cold-start is still owed, the same caveat
  BRF-018 carries for its cold-read verdict.
- Tests: tests/test_intel_brief_cold_start.py,
  ColdStartTest, 4 tests, passing. tests.test_intel_brief
  after this change: 143 tests, passing, unchanged.
  Full suite after this change: 1181 tests = 1177
  clean-tree + 4 new, same 2 pre-existing environmental
  errors as the clean tree (missing trigger_check, missing
  bus-tools/bus-send), verified by running the suite with
  the new test file moved out (1177 tests, same 2 errors)
  before committing.

## 2026-10-27 — BRF-019 — brief prompts to v2 from eval failures only

- Files: intel/prompts/brief_morning_v2.md (v1 plus rules 8, 9,
  10), intel/prompts/brief_onjoin_v2.md (v1 plus rules 9, 10).
  The v1 files stay in place for diffing; every other rule and
  section is carried over from v1 word for word. No rule here
  comes from a vibe edit: each new rule names the failing eval
  case it targets, and the Status section of each v2 file names
  what it does not fix.
- Morning v2, from the INT-027 cold-start test (returner resumes
  job-level work but not lane-level planning, five gaps):
  - Rule 8 targets gap 5 (no ask-nick on the blocked job):
    every blocked line ends with "ask <nick>" when the record
    names one, else "owner not reported in this window",
    never cut under trim.
  - Rule 9 targets gap 1 (no priority order): the In flight
    section opens with "No priority order is recorded in this
    window" when no priority field is present, never cut
    under trim, so the list is never presented as a priority
    order.
  - Rule 10 targets gap 2 (no diff): a "Since your last
    brief" line names only jobs changed since the previous
    brief record, and when no such record is present the
    window line says nothing here is marked as new.
- On-join v2, from the BRF-018 cold-read verdict (newcomer
  could start on the open job but was not told what the crew
  is building, nor which lane the open job belongs to):
  - Rule 9 targets gap 2: the likely-lane section names the
    open job's lane when the record carries a lane field, in
    the form "The open job <title> belongs to the <lane>
    lane"; when no capability record and no lane field are
    present it says so and points to who to ask, never
    guessing a lane from a title.
  - Rule 10 targets gap 1: the crew-building sentence and
    the likely-lane line are never dropped under budget
    trim; shorten them before deleting them.
- NOT fixed by this v2, stated plainly in both files:
  INT-027 gap 3 (no held decisions) and gap 4 (no source
  pointers) have no source in the FND-033 source map, and
  writing them into a prompt would invent facts. The
  BRF-018 section mismatch (the template composer renders
  morning sections, not on-join sections) is a composer
  gap, not a prompt gap, and the DOC-011 wiring gap is
  unchanged: a template brief gains nothing from v2 until
  the composer is wired to the prompt.
- No re-score is claimed here: a Spark-composed brief under
  v2 cannot be scored until real Spark transport lands, and
  the BRF-018 and INT-027 re-runs under v2 are still owed.
  The on-demand prompt has no v2 yet because no eval
  failure targets it. No bus post was made for this change.
- Explainer updated: intel/prompts/README.md now names both
  v2 files and replaces the "no v2 of any brief prompt"
  paragraph with the BRF-019 account above. The stale
  explainer test that asserted "no v2" was re-pointed, the
  same way DSP-024 re-pointed the A5 test: it now asserts
  the explainer names both v2 files and still states the
  wiring gap.
- Tests: tests/test_intel_brief_prompt_v2.py,
  BriefPromptV2Test, 12 tests, passing. Phrase checks run
  on whitespace-normalized text because prompt files wrap
  lines, and the dash check pins that v2 adds no em dash
  beyond the ones the v1 headings already carry. Brief
  tests after this change: 155 tests (143 brief + 12 new),
  passing. Full suite after this change: 1209 tests = 1197
  clean-tree baseline + 12 new, with the same 2
  pre-existing environmental errors as the clean tree
  (boss_trigger loader, bustools parity: missing
  trigger_check, missing bus-tools/bus-send).

## 2026-10-27 - STR-002 - screenshot digest in the brief record

- What landed: intel/brief.py extract_screenshot_refs plus
  screenshot_digest_lines, wired into generate_brief (the record
  gains "screenshot_refs") and compose_template_brief (a
  Screenshots section after Watch items, only when the window
  carries image pointers). The digest is built from the same
  capped snapshot as the text and sections, so a --since brief
  cannot carry a screenshot from outside its window.
- Fixture: hand-written snapshot with --img posts, NOT a live
  room and NOT Buffy's STR-004 eval set (not landed). An --img
  post is a bus message whose text ends with a BLOB pointer
  (send.py: "BLOB:<16 hex hash>:<name>:<chunk count>").
- What a ref carries: nick, file, hash, chunk count, the
  message ts when the message dict carries one (None for a bus
  string, which carries no time, so no time is claimed for it),
  and the caption (message text with pointers removed).
  A pointer naming a non-image file (.txt, .pdf, .png.txt) is
  skipped; a malformed pointer (short hash) is skipped. The
  same image posted twice yields one ref, at its latest post.
- Honest limits, stated plainly:
  - A snapshot pointer alone cannot prove a post arrived via
    --img rather than --blob: img_put validates bytes by magic,
    but the snapshot carries only pointer text, so the digest
    lists pointers that name an image file, and says so.
  - No verdict is produced here: whether a screenshot shows a
    working or broken build is the SAM pass's call (STR-004
    eval set, STR-005 panel render), and no verdict field is
    invented in the ref. A Spark-composed brief carrying this
    digest is still owed: Spark transport is still blocked, so
    the digest was proven on template briefs only.
  - The devpack brief pack was regenerated from producer output
    (python3 tests/test_intel_devpack.py --dump intel/devpack)
    because brief_entry copies the record wholesale: the only
    change in intel/devpack/brief.json is "screenshot_refs": []
    on the fresh and stale entries, which carry no screenshots.
- Tests: tests/test_intel_brief_screenshots.py,
  ScreenshotRefsTest / ScreenshotDigestLinesTest /
  ScreenshotBriefRecordTest, 9 tests, passing. Brief tests
  after this change: test_intel_brief still 143, plus 9 new.
  Full suite after this change: 1233 tests = 1224 clean-tree
  baseline + 9 new, with the same 2 pre-existing environmental
  errors as the clean tree (boss_trigger loader, bustools
  parity: missing trigger_check, missing bus-tools/bus-send).
  No bus post was made for this change.

## 2026-10-27 - BRF-025 - demo morning brief draft (hand-checked)

- What landed: hackathon/relay-intelligence/demo-assets/
  morning-brief-demo.md, a template morning brief draft (121
  words, morning budget 220) in the morning prompt order, with
  a line-by-line trace table and an 8/8 rubric score against
  its stated source. The v2 rules are applied by hand in the
  draft (no-priority-order line, no-previous-brief sentence,
  blocked line ending with its ask target); the template
  composer still renders v1 sections, so code-generated
  template briefs do not gain those rules on their own
  (the BRF-019 wiring gap, unchanged).
- Source, stated plainly: the landed devpack brief snapshot
  (tests/test_intel_devpack.py brief_snapshot(), as recorded
  in intel/devpack/brief.json, room build-relay-intel) — NOT
  Buffy's demo-day state pack (INT-014 / INT-033), which has
  not landed, so no claim in the draft traces to it. When
  the state pack lands the draft must be regenerated from it
  and re-checked before anyone calls it the exact demo-day
  brief. No calendar date is stated: the pack's frozen
  fixture clock is not a demo-day date. The demo goal plan
  is a separate source (what Dale types during the demo),
  not morning state, so its five jobs do not appear in the
  brief. No Spark call was made: Spark transport is still
  blocked, so no Spark-composed version is claimed.
- Tests: tests/test_intel_brief_demo_morning.py,
  DemoMorningBriefTest, 7 tests, passing. Brief tests after
  this change: test_intel_brief still 143, plus 7 new.
  No bus post was made for this change.

## 2026-10-27 - BRF-010 - brief announcement line, held

- What landed: intel.brief.format_brief_announcement renders the
  frozen BRIEF:<room>:<ts> <kind> line from a brief record (room
  cleaned by relay_common.clean_room, "main" when that cleans to
  empty, ts the record's generated_at, kind one of BRIEF_KINDS),
  or None for a record that cannot carry a line; the line carries
  no section text. intel.py brief --show --announce prints only
  that line for a stored brief. Hana sign-off on the BRIEF:
  shape is recorded as a dated note in the frozen-shape Status
  section of intel/README.md.
- Held, plainly: no brief is posted. GOV-002 still holds posting
  until Dale rules on the room and the wire format, so this is
  the whole BRF-010 surface — a builder and a print-only flag,
  with no post call site behind them. A stored record that
  cannot carry a line errors (exit 1, RELAY_ERROR) instead of
  printing an invented line.
- Tests: tests/test_intel_brief_announce.py,
  BriefAnnouncementTest + CliAnnounceTest, 10 tests, passing.
  Brief tests after this change: test_intel_brief still 143,
  plus 10 new. Full suite by discover: 1296 tests, only the
  same 2 pre-existing environmental errors as the clean tree
  (boss_trigger loader, bustools parity; clean tree 1286, so
  the delta is exactly the 10 new tests).
  No bus post was made for this change.
- NOT proven here: a brief announcement posted to a real room
  (held, not attempted), a Spark-composed brief carrying the
  line, and the Milo/Rowan sign-offs that would complete the
  crew freeze.

## 2026-10-27 - OS-117 - crew-of-crews federation section

- What landed: intel.brief.federation_lines renders the
  Federation section from a stated snapshot federation record
  (machines with name, completions, cross-machine jobs with id,
  title, status; trust_events with kind join or refusal,
  machine, detail). The template composer carries the section
  after Watch items in a content brief and before "no activity
  yet" in an empty-window brief. A record naming fewer than two
  usable machines renders no section at all, so a single-machine
  brief is never empty-padded, and a snapshot with no federation
  record keeps its exact older shape. A machine with no
  completions reads no completions reported; a refusal with no
  detail reads reason not reported. Spec section in
  intel/prompts/brief_boot.md, OS-117 rubric check in
  intel/evals/brief_rubric.md.
- Tests: tests/test_intel_brief.py, FederationSectionTest,
  7 tests, passing. Brief tests after this change:
  test_intel_brief 150. Full suite by per-module load:
  1329 tests = 1322 clean-tree baseline + 7 new, with
  only the same 2 pre-existing environmental errors as
  the clean tree (boss_trigger loader, bustools parity).
  No bus post was made for this change.
- NOT proven here: the section against a live federation
  (join flow Pax OS-110, trust enforcement Milo OS-112,
  two-machine drill Buffy OS-113, and policy ruling Dale
  OS-115 have not landed, so no caller yet fills federation
  from joined machines), and a Spark-composed morning brief
  carrying this section. This is a Phase B [B] task built
  early as a renderer only; the federation minimum itself
  is not claimed done here.

## 2026-10-27 - OS-092 - memory-aware daily brief depth lines

- What landed: intel.brief.memory_depth_lines renders the
  Long-term memory section from a stated snapshot
  memory_depth record (aged_decisions with decision plus
  original_date, due_commitments with commitment plus due
  date, fresh_context strings). The template composer
  carries the section after Watch items in a content
  brief and before "no activity yet" in an empty-window
  brief. A record with memory_down true renders the
  memory service down line and shows no item; a missing
  original date reads original date not reported and a
  missing due date reads due date not reported; an empty
  record reads none reported per category, never a padded
  item; a snapshot with no record carries no section. The
  lines are plain lines, not bullets, so the BRF-007 trim
  keeps them while dropping bullets, and every line
  carries its as_of age label or the snapshot-time-not-
  reported label. Spec section in
  intel/prompts/brief_boot.md, OS-092 rubric check in
  intel/evals/brief_rubric.md.
- Tests: tests/test_intel_brief.py,
  MemoryDepthLinesTest, 8 tests, passing. Brief tests
  after this change: test_intel_brief 158. Full suite
  by discover: 1399 tests = 1391 clean-tree baseline +
  8 new, with only the same 2 pre-existing
  environmental errors as the clean tree (boss_trigger
  loader, bustools parity). No bus post was made for
  this change.
- NOT proven here: the lines against a live memory
  service (the daily brief itself, OS-075, has not
  landed, because the desktop session, Rowan OS-071,
  has not landed and two weeks of daily briefs on the
  daily machine have not run, and no caller yet fills
  memory_depth from memory), and a Spark-composed daily
  brief carrying these lines. This is a Phase B [B]
  task built early as a renderer only; the daily brief
  itself, and its two-week acceptance, are not claimed
  done here.
## 2026-10-27 - OS-075 - Dale's daily brief section

- What landed: intel.brief.daily_lines renders the
  Daily brief section from a stated snapshot daily
  record (overnight_results strings, todays_queue
  jobs with id plus title, needs_word questions
  with an optional job tag). The template composer
  carries the section after Watch items and before
  Long-term memory in a content brief and before
  "no activity yet" in an empty-window brief. A
  queue job without both an id and a title is
  skipped and a needs-word entry without a
  question is skipped, never padded; an empty
  record reads none reported per category, never
  a padded item; a snapshot with no record carries
  no section. The lines are plain lines, not
  bullets, so the BRF-007 trim keeps a question
  waiting on Dale's word, and every line carries
  its as_of age label or the snapshot-time-not-
  reported label. No prompt-history change from
  Dale's feedback is recorded, because no daily
  brief has run on the daily machine yet. Spec
  section in intel/prompts/brief_boot.md, OS-075
  rubric check in intel/evals/brief_rubric.md.
- Tests: tests/test_intel_brief.py,
  DailyBriefLinesTest, 8 tests, passing. Brief tests
  after this change: test_intel_brief 166. Full suite
  by per-module load: 1454 tests = 1446 clean-tree
  baseline + 8 new, with only the same 2 pre-existing
  environmental errors as the clean tree (boss_trigger
  loader, bustools parity). No bus post was made for
  this change.
- NOT proven here: the section in a daily brief read
  on the desktop session (Rowan OS-071 has not
  landed and two weeks of daily briefs on the daily
  machine have not run, and no caller yet fills
  daily), and a Spark-composed daily brief carrying
  this section. This is a Phase B [B] task built
  early as a renderer only; the daily brief itself,
  and its two-week acceptance, are not claimed done
  here. With OS-075 rendered, every task on the Hana
  lane list now has a renderer commit except the
  two-week daily-use acceptance itself, which only
  real daily use can close.
## 2026-10-28 - INT-027 follow-up - cold-start gaps 3 and 4 closed for the template brief

- What landed: intel.brief.held_decisions_lines renders
  the Held decisions section from a stated snapshot
  held_decisions record (questions verbatim, decider
  nick when the record gives one, decider not reported
  when it gives none, entries without a question
  skipped, an empty record reading none reported),
  and intel.brief.source_pointer_lines renders the
  Sources section from a stated source_pointers list
  (pointers verbatim and in order, an absent or empty
  list rendering no section at all). The template
  composer carries both sections after Watch items
  (and Federation, when one renders) in a content
  brief and before "no activity yet" in an
  empty-window brief; a snapshot with no records
  carries neither section, so older briefs keep their
  exact shape. The lines are plain lines, not bullets,
  so the BRF-007 trim keeps a held decision and a
  source pointer after dropping bullets, and every
  held line carries its as_of age label or the
  snapshot-time-not-reported label. Source lines
  carry no age label: they name locations, not dated
  facts. The INT-027 verdict documented both gaps as
  limits because no such source existed in the
  FND-033 source map; the records are that source,
  supplied by the caller the same way the daily,
  memory, and federation records are, never
  re-derived from raw history and never guessed from
  a job title. Rubric check in
  intel/evals/brief_rubric.md (INT-027 gaps 3/4
  check, beside the 8 checks, not renumbering them).
- Tests: tests/test_intel_brief_held_sources.py,
  HeldDecisionsLinesTest, SourcePointerLinesTest,
  HeldSourcesComposerTest, HeldSourcesRubricTest,
  11 tests, passing. Brief tests after this change:
  test_intel_brief 166, unchanged. Full suite by
  discover: 1732 tests = 1721 clean-tree baseline +
  11 new, with only the same 2 pre-existing
  environmental errors as the clean tree (boss_trigger
  loader, bustools parity), verified by running the
  suite with the new test file moved out and the
  tracked changes stashed (1721 tests, same 2 errors)
  before committing. No bus post was made for this
  change.
- NOT proven here: a Spark-composed brief carrying
  these lines (real Spark transport is still
  blocked), and an independent lane member's
  cold-start re-run under the new sections. This
  closes gaps 3 and 4 for the template brief only;
  the INT-027 acceptance still owes that independent
  re-run, and the two-week daily-use acceptance
  (OS-075) still owes real daily use. All 63 tasks
  on the Hana lane list have now had their renderer
  work done; what remains open is live-service,
  other-lane, and real-use acceptance, not renderer
  work.

## 2026-10-28 - BRF-019 follow-up - cold-start gap 2 closed for the template brief

- What landed: intel.brief.since_last_brief_lines renders
  the Since your last brief section from a stated
  snapshot previous_brief record (the jobs and their
  statuses in the previous brief), and the template
  composer carries it right after the window line and
  before Decisions in a content brief, so the brief
  opens with its diff. A job whose status changed
  reads as changed with the old status and the new
  status both named; a job with no previous-brief
  entry reads as new; a job whose status is unchanged
  is not listed at all, so old news and new news
  never look identical. A current job with no id and
  a previous-brief entry with no id are skipped, never
  padded; a record that is not a dict, or whose jobs
  are not a list, yields no section at all, never a
  false diff; a comparison that finds nothing changed
  reads nothing changed, never a padded change. The
  lines are plain lines, not bullets, so the BRF-007
  trim keeps them, and every line carries its as_of
  age label or the snapshot-time-not-reported label.
  The record is supplied by the caller the same way
  the daily, memory, and federation records are,
  never re-derived from raw history and never guessed
  from a job title. Rubric check in
  intel/evals/brief_rubric.md (BRF-019 gap 2
  since-last-brief check, beside the 8 checks, not
  renumbering them).
- Tests: tests/test_intel_brief_since_last.py,
  SinceLastBriefLinesTest, SinceLastBriefComposerTest,
  SinceLastBriefRubricTest, 11 tests, passing. Brief
  tests after this change: test_intel_brief 166,
  unchanged. Full suite by discover: 1743 tests =
  1732 clean-tree baseline + 11 new, with only the
  same 2 pre-existing environmental errors as the
  clean tree (boss_trigger loader, bustools parity).
  One intermediate baseline-only run showed a third
  transient error that did not recur on the repeat
  full run, so it is noted here, not hidden, and not
  claimed as a suite failure. No bus post was made
  for this change.
- NOT proven here: a Spark-composed brief carrying
  these lines (real Spark transport is still blocked),
  and an independent lane member's cold-start re-run
  under the new section. This closes gap 2 for the
  template brief only; gaps 1 (priority order) and 5
  (ask-nick on the blocked job) remain prompt-only
  v2 rules, not yet wired into the template
  composer, because wiring them would change the
  blocked and in-flight lines the existing tests pin
  character-for-character. The INT-027 acceptance
  still owes that independent re-run, and the
  two-week daily-use acceptance (OS-075) still owes
  real daily use.

## 2026-10-28 - INT-027 follow-up - cold-start gaps 1 and 5 closed for the template brief

- What landed: intel.brief.priority_order_lines renders
  the Priority order section from a stated snapshot
  priority_order record (a list of job ids in priority
  order), and intel.brief.blocked_contact_lines renders
  the Blocked contacts section from a stated snapshot
  blocked_contacts record (a job_id -> ask nick map).
  A priority id is named with its snapshot title, numbered
  from 1, in record order; an id with no matching job is
  skipped, a duplicate id is listed once, and a job the
  record does not list is not listed at all, never guessed
  into an order. A blocked contact covers every blocked job
  in snapshot order: a job with a contact entry reads Ask
  <nick> about <id> <title>, and a job with no usable entry
  reads <id> <title>: owner not reported in this window,
  the v2 rule 8 wording, never a guessed nick; a contact
  entry for a job that is not blocked is ignored, and a
  blocked job with no id is skipped here though its blocked
  line still names it. The template composer carries both
  sections after Sources in a content brief, only when the
  snapshot carries the record, so a brief without either
  record keeps its exact older shape, and a malformed record
  yields no section, never a false order or contact. The
  lines are plain lines, not bullets, so the BRF-007 trim
  keeps them, and every line carries its as_of age label or
  the snapshot-time-not-reported label. The records are
  supplied by the caller the same way the daily, memory,
  and federation records are, never re-derived from raw
  history and never guessed from a job title. Rubric check in
  intel/evals/brief_rubric.md (INT-027 gaps 1/5 check,
  beside the 8 checks, not renumbering them).
- Why additive, stated plainly: the BRF-019 follow-up left
  gaps 1 and 5 as prompt-only v2 rules because wiring them
  in place would change the blocked and in-flight lines the
  existing tests pin character-for-character. These sections
  do not rewrite those lines: they supply the order and the
  ask-nick beside them, and the pinned lines keep their
  exact shape, as the composer test pins.
- Tests: tests/test_intel_brief_priority_contacts.py,
  PriorityOrderLinesTest, BlockedContactLinesTest,
  PriorityContactsComposerTest, PriorityContactsRubricTest,
  15 tests, passing. Brief tests after this change:
  test_intel_brief 166, unchanged. Full suite by discover:
  1758 tests = 1743 clean-tree baseline + 15 new, with only
  the same 2 pre-existing environmental errors as the clean
  tree (boss_trigger loader, bustools parity), verified by
  running the suite with the new test file moved out and the
  tracked changes stashed (1743 tests, same 2 errors)
  before committing. No bus post was made for this change.
- NOT proven here: a Spark-composed brief carrying these
  lines (real Spark transport is still blocked), and an
  independent lane member's cold-start re-run under the new
  sections. With gaps 1 and 5 closed here, all five INT-027
  cold-start gaps are now closed for the template brief
  (gap 2 in the BRF-019 follow-up, gaps 3 and 4 in the
  INT-027 follow-up); what the INT-027 acceptance still
  owes is that independent re-run, not more renderer work,
  and the two-week daily-use acceptance (OS-075) still owes
  real daily use.

## 2026-10-28 - BRF-007 follow-up - brief prompt files wired to the Spark composer (opt-in)

- What landed: intel.brief.load_brief_prompt reads the v1 prompt
  file for a kind (brief_morning.md, brief_onjoin.md,
  brief_ondemand.md from intel/prompts/), intel.brief.brief_prompt_path
  resolves its path, and compose_brief / compose_spark_brief take a
  system_prompt argument sent as the client's system text, so the
  file's rules reach Spark instead of living only as a spec. The
  inline section-data prompt is unchanged, the budget trim and the
  redaction pass still apply to the returned text, and the default
  call (no system_prompt) sends no system text, exactly as before,
  so every existing brief keeps its shape. A missing prompt file or
  an unknown kind yields "" from the loader, never an error, so a
  missing file can never fail a brief. The v2 files are not
  auto-selected: a caller that wants v2 reads that file itself and
  passes its text. intel/prompts/README.md "still missing" note
  updated to record the wiring and what stays open (default wiring,
  a CLI flag, v2 selection).
- Tests: tests/test_intel_brief_prompt_wiring.py,
  LoadPromptTest + ComposeWiringTest, 9 tests, passing. Brief tests
  after this change: test_intel_brief 166, unchanged. Full suite by
  discover: 1773 = 1764 clean-tree baseline + 9 new, with only the
  same 2 pre-existing environmental errors as the clean tree
  (boss_trigger loader, bustools parity), verified by running the
  suite with the new test file moved out and the tracked changes
  stashed (1764 tests, same 2 errors) before committing.
- NOT proven here: a real Spark call carrying a prompt file as
  system text (real Spark transport is still blocked; the tests use
  a recording fake client, so they prove the composer sends the
  text, not that Spark obeys it), and the default-on wiring and CLI
  flag, which stay open. No bus post was made for this change.

## 2026-10-28 - BRF-007 follow-up - prompt-file version selection + stored-brief passthrough

- What landed: intel.brief.load_brief_prompt / brief_prompt_path
  take a version ("v1" default, "v2"): morning and onjoin load
  their BRF-019 v2 files, ondemand v2 returns "" with no silent
  v1 fallback (ondemand has no v2 file), and an unknown version
  returns "" / None, never an error. generate_brief takes a
  system_prompt argument passed through to compose_brief, so the
  stored-brief path can carry a prompt file at all: before this,
  generate_brief took a client but no prompt, so a caller that
  wanted prompt-file wiring had to call compose_brief directly
  and give up storage and the BRF-028 guard. The default call
  (no system_prompt) sends no system text, exactly as before,
  so every existing brief keeps its shape; the inline
  section-data prompt, budget trim, and redaction pass are
  unchanged. generate_morning_brief is untouched: it still
  builds a template brief with no client, so a prompt file
  reaches a stored brief only through generate_brief with a
  client. intel/prompts/README.md "still missing" note updated
  to record the v2 selection and what stays open (default
  wiring, a CLI flag — the CLI still builds briefs with no
  Spark client, so a flag alone would change nothing until a
  client is wired into that path).
- Tests: tests/test_intel_brief_prompt_version.py,
  LoadVersionTest + GeneratePromptTest, 8 tests, passing
  (fake store patched in, as in the existing generate_brief
  tests). Brief tests after this change: test_intel_brief 166,
  unchanged. Full suite by discover: 1781 = 1773 clean-tree
  baseline + 8 new, with only the same 2 pre-existing
  environmental errors as the clean tree (boss_trigger loader,
  bustools parity), verified by running the suite with the new
  test file moved out and the tracked changes stashed (1773
  tests, same 2 errors) before committing.
- NOT proven here: a real Spark call carrying a v1 or v2 prompt
  file as system text (real Spark transport is still blocked;
  the tests use recording fake clients, so they prove the
  composer and the stored-brief path send the text, not that
  Spark obeys it), and the default-on wiring and CLI flag,
  which stay open. No bus post was made for this change.

## 2026-10-28 - OS-103 follow-up - environment repo record read from git

- What landed: intel.brief.environment_repo_record reads the
  "repo" part of an environment record from a local git
  checkout (branch, short commit, dirty count of uncommitted
  files including untracked, stamped with as_of), never
  raising: a non-checkout, a missing git, a failed command,
  or a detached HEAD yields {} so environment_lines renders
  the repo line as not reported instead of guessing a
  branch. This is only the repo quarter: a caller merges it
  with bus, jobs, and budget parts from their own sources,
  and a record carrying only this part still renders the
  other three lines as not reported. The brief_boot.md
  OS-103 section is updated to record the builder and to
  correct its stale note: Milo OS-085 budget config has
  landed since that section was written, but no spend
  ledger exists yet, so the budget line still reads not
  reported in practice.
- Tests: tests/test_intel_brief_environment_repo.py,
  EnvironmentRepoRecordTest, 5 tests, passing, against real
  temp git checkouts (clean checkout, modified + untracked
  dirty count, non-checkout empty record, builder record
  through environment_lines, builder record through a boot
  template brief). Brief tests after this change:
  test_intel_brief 166, unchanged. Full suite by discover:
  1786 tests = 1781 clean-tree baseline + 5 new, with only
  the same 2 pre-existing environmental errors as the clean
  tree (boss_trigger loader, bustools parity), verified by
  running the suite with the new test file moved out and the
  tracked changes stashed (1781 tests, same 2 errors)
  before committing. No bus post was made for this change.
- NOT proven here: a full environment record against live
  launch state (bus, jobs, and budget fillers are still
  owed; the budget line waits on a spend source, not just
  the OS-085 config), and a Spark-composed boot brief
  carrying these lines (real Spark transport still blocked).

## 2026-10-28 - OS-103 follow-up - environment jobs record read from the snapshot jobs list

- What landed: intel.brief.environment_jobs_record takes the
  snapshot's own jobs list and returns the "jobs" part of an
  environment record, in job order: claimed jobs only, each
  with a non-empty string claim nick and title; open,
  blocked, done, claim-less, title-less, and non-dict
  entries are skipped, never guessed into a name, and an
  unusable id is left out rather than invented. A non-list
  input returns None, so a caller leaves "jobs" out and the
  Working now line reads not reported instead of falsely
  reading nobody holds a job; an empty or claim-less list
  returns [] and renders as nobody holds a claimed job.
  The list carries no time of its own: the caller stamps
  the record's as_of when merging it in, at the same
  instant the jobs list was read. The brief_boot.md
  OS-103 section is updated to record the second built
  quarter and to correct its owed list: bus and budget
  parts are still owed, jobs no longer is.
- Tests: tests/test_intel_brief_environment_jobs.py,
  EnvironmentJobsRecordTest, 6 tests, passing (claimed
  filtering in order, unusable id left out, empty list,
  non-list None with not-reported line, builder record
  through environment_lines, builder record through a boot
  template brief). Brief tests after this change:
  test_intel_brief 166, unchanged. Full suite by discover:
  1795 tests = 1789 clean-tree baseline + 6 new, with only
  the same 2 pre-existing environmental errors as the clean
  tree (boss_trigger loader, bustools parity), verified by
  running the suite with the new test file moved out and the
  tracked changes stashed (1789 tests, same 2 errors)
  before committing. No bus post was made for this change.
  (Note: the prior OS-103 follow-up entry recorded a 1781
  baseline and 1786 total; this run measured 1789 on the
  same HEAD before its change, so the totals here use the
  freshly measured baseline, not the older figure.)
- NOT proven here: a full environment record against live
  launch state (bus and budget fillers are still owed; the
  budget line waits on a spend source, not just the OS-085
  config), a caller that actually merges the repo and jobs
  parts into a launch snapshot, and a Spark-composed boot
  brief carrying these lines (real Spark transport still
  blocked).

## 2026-10-28 - OS-103 follow-up - environment record merge caller

- What landed: intel.brief.build_environment_record merges
  the two built environment parts into one launch record:
  "repo" from environment_repo_record over a given checkout
  (this repo's checkout by default), "jobs" from
  environment_jobs_record over the snapshot's own jobs list,
  and one "as_of" stamp taken once so the repo line's age
  and the Working now line's age agree instead of drifting
  across two reads. A part that yields nothing usable is
  left out, never padded: a non-checkout repo leaves "repo"
  out, a snapshot with no usable jobs list leaves "jobs"
  out so the Working now line reads not reported instead of
  falsely reading nobody, while an empty claimed-jobs list
  is kept as [] and still renders as nobody holds a claimed
  job. Bus and budget parts are deliberately absent — no
  bus or spend-ledger filler is claimed here — so a record
  from this builder still renders those two lines as not
  reported. The brief_boot.md OS-103 section is updated to
  record the third built piece and to correct its owed
  list: the merge caller is no longer owed, bus and budget
  still are.
- Tests: tests/test_intel_brief_environment_record.py,
  BuildEnvironmentRecordTest, 8 tests, passing (merge with
  one stamp, merged record through environment_lines, non-
  checkout repo left out, non-list jobs left out with not-
  reported line, no-snapshot stamp-only record, empty jobs
  as nobody holds, merged lines through a boot template
  brief, default stamp is an int). Brief tests after this
  change: test_intel_brief 166, unchanged, plus the 8 new
  tests (174 in the two modules together). Full suite by
  file loader: 1802 tests = 1794 clean-tree baseline + 8
  new, with only the same 2 pre-existing environmental
  issues as the clean tree (boss_trigger loader, external
  relay-trigger dir absent so the module does not load;
  bustools parity, live skill script missing outside the
  repo), verified by running the suite with the new test
  file moved out and the tracked changes stashed (1794
  tests, same 2 issues) before committing. Note: the
  standard `python3 -m unittest discover -s tests` loader
  fails in this tree (tests/ has no __init__.py), so this
  run and its baseline both used the file loader; the
  counts above are file-loader counts, not discover
  counts, and the earlier discover totals are not directly
  comparable. No bus post was made for this change.
- NOT proven here: a full environment record against live
  launch state (bus and budget fillers are still owed; the
  budget line waits on a spend source, not just the OS-085
  config), a caller in the launch path actually calling
  this builder, and a Spark-composed boot brief carrying
  these lines (real Spark transport still blocked).

## 2026-10-28 - OS-103 follow-up - environment bus record read from the snapshot messages list

- What landed: intel.brief.environment_bus_record takes the
  snapshot's own messages list and the room or rooms that
  list covers and returns the "bus" part of an environment
  record: rooms as non-empty strings in caller order with
  duplicates dropped (a single room string is wrapped, bad
  room values are dropped), messages as the count of dict
  and string entries only, and as_of stamped at read time.
  Rooms come from the caller because the documented
  snapshot message shape carries no room field, so they are
  never guessed from the messages; the count is the count
  in the passed list (the snapshot window), never a claim
  about bus history beyond that window. A non-list input
  returns None, so a caller leaves "bus" out and the Bus
  line reads not reported instead of falsely reading zero
  messages; an empty list returns 0 messages and renders
  as an empty window. build_environment_record now merges
  this part in too, with a new optional room argument and
  the same one-stamp rule, so the repo, bus, and Working
  now lines' ages agree; a snapshot with no messages list
  still leaves "bus" out. The brief_boot.md OS-103 section
  is updated to record the fourth built piece and to
  correct its owed list: budget only, bus no longer is.
- Tests: tests/test_intel_brief_environment_bus.py,
  EnvironmentBusRecordTest, 8 tests, passing (count and
  rooms with duplicates dropped, room-string wrapping and
  bad rooms dropped, non-list None with not-reported
  line, empty list as 0 messages, builder record through
  environment_lines, merged record with one stamp,
  merged record without messages leaves bus out, merged
  lines through a boot template brief). Brief tests after
  this change: test_intel_brief 166, unchanged. Full suite
  by module loader: 1824 tests = 1816 clean-tree baseline
  + 8 new, with only the same 2 pre-existing
  environmental errors as the clean tree (boss_trigger
  loader, bustools parity), verified by running the suite
  with the new test file moved out and the tracked
  changes stashed (1816 tests, same 2 errors) before
  committing. No bus post was made for this change.
- NOT proven here: a full environment record against live
  launch state (the budget filler is still owed; the
  budget line waits on a spend source, not just the OS-085
  config), a caller in the launch path actually calling
  this builder, and a Spark-composed boot brief carrying
  these lines (real Spark transport still blocked).

## 2026-10-28 - OS-103 follow-up - environment budget record read from the snapshot budgets list

- What landed: intel.brief.environment_budget_record takes
  the snapshot's own budgets list (the OS-079 entries:
  lane, spent, cap, or remaining) and an optional lane
  name and returns the "budget" part of an environment
  record: lane, the usable figures exactly as stated
  ("spent" and "cap" when both are usable, "remaining"
  when it is stated usable), and as_of stamped at read
  time. The figures are the snapshot's stated figures,
  never a live ledger: there is still no spend ledger in
  this repo, so a snapshot with no budgets list yields
  nothing and the Budget line reads not reported rather
  than a guessed figure. An entry counts only with a
  non-empty string lane and usable figures (integers,
  never bools; cap positive, spent not negative, matching
  intel/budgets.py's malformed-entry rule; a spent figure
  past cap is kept as an honest overspend, not a zero).
  A named lane picks that lane's first usable entry in
  list order; without a lane the first usable entry wins,
  so a caller with several lanes states the lane it
  reports. A non-list input, an empty list, or a list
  with no usable entry returns None, so a caller leaves
  "budget" out and the Budget line reads not reported
  instead of falsely reading a zero remaining.
  build_environment_record now merges this part in too,
  with a new optional lane argument and the same
  one-stamp rule, so all four environment lines' ages
  agree; a snapshot with no budgets list still leaves
  "budget" out. The brief_boot.md OS-103 section is
  updated to record the fourth built piece: with repo,
  jobs, bus, and budget all built, no environment part
  is owed any longer, only the live-launch caller and
  the Spark-composed brief.
- Tests: tests/test_intel_brief_environment_budget.py,
  EnvironmentBudgetRecordTest, 10 tests, passing (spent
  and cap rendering remaining with cap, named lane picked
  among many and unknown lane None, no lane taking the
  first usable entry, remaining direct without a cap
  part, malformed entries skipped never guessed, overspend
  kept as a negative remaining, builder record through
  environment_lines, merged record with one stamp,
  merged record without budgets leaving budget out,
  merged lines through a boot template brief). Brief
  tests after this change: test_intel_brief 166,
  unchanged. Full suite by discover: 1834 tests = 1824
  clean-tree baseline + 10 new, with only the same 2
  pre-existing environmental errors as the clean tree
  (boss_trigger loader, bustools parity), verified by
  running the suite with the tracked changes stashed
  (1824 tests, same 2 errors) before committing. No bus
  post was made for this change.
- NOT proven here: a full environment record against live
  launch state (a launch snapshot must actually carry a
  budgets list for the Budget line to read anything; no
  live spend ledger exists yet), a caller in the launch
  path actually calling this builder, and a Spark-composed
  boot brief carrying these lines (real Spark transport
  still blocked).
## 2026-10-28 - OS-103 follow-up - launch-path caller fills a boot snapshot's environment record

- What landed: intel.brief.with_boot_environment takes the
  snapshot the launch path already holds and returns a copy
  with an "environment" record built from it when the
  snapshot carries none: repo from the checkout (this repo
  by default), jobs, bus, and budget from the snapshot's
  own lists through build_environment_record, one as_of
  stamp for the whole record. A snapshot that already
  carries an environment record is returned as an unchanged
  copy, so a hand-stated record is never overwritten, and
  the caller's snapshot is never mutated. The function
  never raises: a builder failure leaves the copy without
  an environment record, so the boot path still produces a
  brief, just without environment lines, instead of failing
  the launch brief outright. intel.py brief --boot — the
  path relay-brief.service runs — now calls it before
  generating, with the room and the --now stamp, so a bare
  launch snapshot carries live environment lines instead
  of none at all; generate_brief itself is untouched, so
  the pinned boot-brief shapes keep their exact form.
  Proven live, not just in tests: a dry-run brief --boot
  over this checkout with a fixture snapshot carried Repo
  main at the checkout's own commit with its dirty count,
  Bus with the fixture message count in the stated room,
  Working now with the claimed job, and Budget with the
  stated lane's remaining, all on one stamp; a bare
  brief --boot with no snapshot carried the live Repo line
  and the other three lines as honestly not reported.
  The brief_boot.md OS-103 section is updated to record
  the caller: with all four parts built and the launch
  caller wired, only the Spark-composed boot brief and
  proof on a booted image stay owed.
- Tests: tests/test_intel_brief_boot_environment.py,
  WithBootEnvironmentTest, 9 tests, passing (absent
  environment filled from snapshot lists and a temp
  checkout with one stamp, filled record rendering all
  four lines, hand-stated environment winning unchanged,
  caller snapshot never mutated, empty snapshot with a
  non-checkout reading all four lines not reported,
  non-dict snapshot getting a repo-only environment, boot
  template brief over a filled snapshot carrying all four
  lines, room list passing through in order, default stamp
  an int when now is not given). Brief tests after this
  change: test_intel_brief 166, unchanged. Full suite by
  discover: 1843 tests = 1834 clean-tree baseline + 9 new,
  with only the same 2 pre-existing environmental errors
  as the clean tree (boss_trigger loader, bustools parity),
  verified by running the suite with the tracked changes
  stashed (1834 tests, same 2 errors) before committing.
  No bus post was made for this change.
- NOT proven here: a Spark-composed boot brief carrying
  these lines (real Spark transport still blocked), proof
  of the lines on a booted image (no test image in this
  repo), or a live spend ledger behind the Budget line (a
  launch snapshot must actually carry a budgets list for
  the Budget line to read anything; no live spend ledger
  exists yet).
## 2026-10-28 - OS-079 follow-up - brief-path caller fills a snapshot's memory_budget record

- What landed: intel.brief.with_memory_budget takes the
  snapshot the brief path already holds and returns a copy
  with a "memory_budget" record built from it when the
  snapshot carries none: budgets from the snapshot's own
  budgets list (every usable lane, in list order, with the
  environment budget record's malformed-entry rule — bool
  figures, negative spent, non-positive cap, and missing
  lanes skipped never guessed, overspend kept honest, a
  stated held flag passing through), settled decisions
  from the snapshot's own settled_decisions list when the
  caller states one (verbatim, non-empty strings only),
  and memory_down when the snapshot states the memory
  service did not answer, with one as_of stamp for the
  whole record. A snapshot that already carries a
  memory_budget record is returned as an unchanged copy,
  so a hand-stated record is never overwritten, and the
  caller's snapshot is never mutated. Unlike
  with_boot_environment, a snapshot that yields nothing
  usable gets no record added, so older briefs keep their
  exact shape instead of gaining not-reported lines; a
  snapshot that states no settled decisions leaves that
  key out, so the line reads not reported rather than a
  guessed decision. The function never raises: a builder
  failure leaves the copy without a record, so the brief
  path still produces a brief, just without these lines.
  intel.py brief now calls it before generating for boot,
  morning, and ondemand alike (OS-079 covers boot and
  morning briefs), after which the boot path still calls
  with_boot_environment; generate_brief and
  generate_morning_brief themselves are untouched, so the
  pinned brief shapes keep their exact form. The
  brief_boot.md OS-079 section is updated to record the
  caller (and to correct its stale note: the OS-085 budget
  config has landed as intel/budgets.py, as the OS-103
  section already recorded; what is still owed is a live
  spend ledger and a live memory service).
  Proven live, not just in tests: a dry-run morning brief
  over a fixture snapshot carried the stated settled
  decision and the HANA spend line (120 of 300, 180
  remaining) over an empty window, on one stamp.
- Tests: tests/test_intel_brief_memory_budget_caller.py,
  WithMemoryBudgetTest, 10 tests, passing (budgets for
  every usable lane plus verbatim decisions on one stamp,
  filled record rendering settled and spend lines,
  hand-stated record winning unchanged, caller snapshot
  never mutated, snapshot with nothing usable getting no
  record, malformed budget entries skipped with
  remaining-only and overspend kept, memory_down passing
  through with no decision shown, morning template brief
  over a filled snapshot carrying the lines, default stamp
  an int when now is not given, non-dict snapshot getting
  no record). Brief tests after this change: test_intel_brief
  176 = 166 unchanged + 10 new. Full suite by discover:
  1866 tests = 1856 clean-tree baseline + 10 new, with
  only the same 2 pre-existing environmental errors as
  the clean tree (boss_trigger loader, bustools parity),
  verified by running the suite with the tracked changes
  stashed (1856 tests, same 2 errors) before committing.
  No bus post was made for this change.
- NOT proven here: the lines against live state (no memory
  service exists in this repo for a filler to read settled
  decisions from, and no spend ledger exists for it to read
  spent from — the filler reads only what the snapshot's
  own lists state), or a Spark-composed brief carrying
  these lines (real Spark transport still blocked).

## 2026-10-28 - OS-075 follow-up - morning-path caller fills a snapshot's daily record

- What landed: intel.brief.with_daily takes the snapshot
  the morning path already holds and returns a copy with
  a "daily" record built from it when the snapshot carries
  none: overnight_results from the snapshot's own stated
  overnight_results list (verbatim non-empty strings, in
  list order), todays_queue from the snapshot's own jobs
  list (open or claimed jobs with both an id and a title,
  in job order, each job listed once), and needs_word from
  the snapshot's own stated needs_word list (verbatim
  questions, strings or question-plus-job dicts), with one
  as_of stamp for the whole record. A snapshot that already
  carries a daily record is returned as an unchanged copy,
  so a hand-stated record is never overwritten, and the
  caller's snapshot is never mutated. A snapshot that yields
  nothing usable gets no record added, so older briefs keep
  their exact shape instead of gaining none-reported lines;
  a category with no usable entry leaves its key out, and
  daily_lines then renders that category as none reported,
  so a built record always reads as a checked section,
  never a padded one. The two stated lists are passed
  through, never re-derived: overnight results are not
  pulled out of DONE markers, and needs-word questions are
  not invented from blocked reasons — a blocked job is
  neither a queue item nor a question, so a snapshot with
  only a blocked job gets no record at all. The function
  never raises: a builder failure leaves the copy without a
  record, so the brief path still produces a brief, just
  without this section. intel.py brief now calls it for boot
  and morning briefs before generating (ondemand briefs are
  left alone, since the daily section belongs to the
  morning/daily brief); generate_brief and
  generate_morning_brief themselves are untouched, so the
  pinned brief shapes keep their exact form. The
  brief_boot.md OS-075 section is updated to record the
  caller.
  Proven live, not just in tests: a dry-run morning brief
  over a fixture snapshot carried all three categories
  (overnight result, queue jobs 7 and 8, needs-word
  question for job 7) on one stamp, and a dry-run ondemand
  brief over the same snapshot carried no Daily brief
  section.
- Tests: tests/test_intel_brief_daily_caller.py,
  WithDailyTest, 11 tests, passing (all three categories
  on one stamp, filled record rendering the section lines,
  hand-stated record winning unchanged, caller snapshot
  never mutated, snapshot with nothing usable getting no
  record, malformed entries skipped with duplicate queue
  jobs listed once, blocked job neither queue nor question,
  queue-only record reading the other categories none
  reported, morning template brief over a filled snapshot
  carrying the section, default stamp an int when now is
  not given, non-dict snapshot getting no record). Brief
  tests after this change: test_intel_brief 177 = 166
  unchanged + 11 new. Full suite by discover:
  1877 tests = 1866 clean-tree baseline + 11 new, with
  only the same 2 pre-existing environmental errors as
  the clean tree (boss_trigger loader, bustools parity),
  verified by running the suite with the tracked changes
  stashed (1866 tests, same 2 errors) before committing.
  No bus post was made for this change.
- NOT proven here: the section in a daily brief read on
  the desktop session (Rowan OS-071 has not landed, and
  two weeks of daily briefs on the daily machine have not
  run), or a Spark-composed daily brief carrying this
  section (real Spark transport still blocked).

## 2026-10-28 - OS-092 follow-up - morning-path caller fills a snapshot's memory_depth record

- What landed: intel.brief.with_memory_depth takes the
  snapshot the morning path already holds and returns a
  copy with a "memory_depth" record built from it when
  the snapshot carries none: aged_decisions from the
  snapshot's own stated aged_decisions list (each a dict
  with a non-empty decision string, its original_date kept
  only when it is a non-empty string, so a dateless
  decision renders original date not reported instead of
  a guessed date), due_commitments from the snapshot's
  own stated due_commitments list (each a dict with a
  non-empty commitment string, its due date kept only
  when it is a non-empty string), and fresh_context from
  the snapshot's own stated fresh_context list (verbatim
  non-empty strings, in list order), with one as_of stamp
  for the whole record. A snapshot that already carries a
  memory_depth record is returned as an unchanged copy,
  so a hand-stated record is never overwritten, and the
  caller's snapshot is never mutated. When the snapshot
  states the memory service did not answer (memory_down
  True), the record carries that flag alone: the renderer
  shows no item beside the down line under the OS-050
  honesty rule, so stated lists are not carried into a
  record whose lines would never show them. Unlike a
  hand-stated empty record, a snapshot that yields
  nothing usable gets no record added, so older briefs
  keep their exact shape instead of gaining
  not-reported lines. The function never raises: a
  builder failure leaves the copy without a record, so
  the brief path still produces a brief, just without
  this section. intel.py brief now calls it for boot and
  morning briefs after with_daily (ondemand briefs are
  left alone, since the depth section belongs to the
  morning/daily brief, not to an ad hoc window brief);
  generate_brief and generate_morning_brief themselves
  are untouched, so the pinned brief shapes keep their
  exact form. The brief_boot.md OS-092 section is updated
  to record the caller.
  Proven live, not just in tests: a dry-run morning brief
  over a fixture snapshot carried all three categories
  (aged decision from 2026-10-01, due commitment due
  2026-11-03, fresh-agent context) on one stamp over an
  empty window, and a dry-run ondemand brief over the
  same snapshot carried no Long-term memory section.
- Tests: tests/test_intel_brief_memory_depth_caller.py,
  WithMemoryDepthTest, 11 tests, passing (all three
  categories on one stamp, filled record rendering the
  section lines, hand-stated record winning unchanged,
  caller snapshot never mutated, snapshot with nothing
  usable getting no record, malformed entries skipped
  with dateless entries reading not reported, memory_down
  carried alone with no item beside it, single-category
  record reading the other categories none reported,
  morning template brief over a filled snapshot carrying
  the section, default stamp an int when now is not
  given, non-dict snapshot getting no record). Brief
  tests after this change: test_intel_brief 166 unchanged
  + 11 new. Full suite by discover: 1888 tests = 1877
  clean-tree baseline + 11 new, with only the same 2
  pre-existing environmental errors as the clean tree
  (boss_trigger loader, bustools parity), verified by
  running the suite with the tracked changes stashed
  (1877 tests, same 2 errors) before committing.
  No bus post was made for this change.
- NOT proven here: the lines against a live memory
  service (no memory service exists in this repo for a
  filler to read aged decisions or due commitments from
  — the filler reads only what the snapshot's own lists
  state), the section in a daily brief read on the
  desktop session (Rowan OS-071 has not landed, and two
  weeks of daily briefs on the daily machine have not
  run), or a Spark-composed daily brief carrying this
  section (real Spark transport still blocked).

## 2026-10-28 - OS-051 follow-up - boot-path caller fills a boot snapshot's previous_session record
- What changed: before this change no caller in the repo
  filled `previous_session`: a boot brief carried its
  digest line only when the snapshot hand-stated the
  record, and a bare boot snapshot carried no digest
  even when the caller knew the previous session. Now
  `intel/brief.py` `with_previous_session` builds the
  record with `build_previous_session` from the
  snapshot's own stated inputs — "last_brief", the
  stored brief record whose generated_at, ts, or
  last_brief_at time becomes the last-brief time, and
  "shutdown_jobs", the job list as it stood at
  shutdown (done jobs completed, open or claimed jobs
  open threads, blocked jobs neither) — and
  `intel.py brief --boot` calls it before generating,
  after with_boot_environment. A snapshot that
  hand-states a record keeps it untouched, and a
  snapshot that states nothing usable gets no record
  added, so older briefs keep their exact shape. The
  filler deliberately reads neither the snapshot's
  current jobs list (the window's jobs at boot, not
  the shutdown list) nor its "previous_brief" diff
  record (job ids with previous statuses, not a
  stored brief). A missing or non-list shutdown_jobs
  states nothing and yields no record, while an
  explicitly empty list states a clean shutdown and
  yields a 0-jobs-completed, 0-open-threads record; a
  last brief with no usable time yields no record,
  never a digest on a guessed time. The record
  carries no as_of stamp of its own — its time is the
  last-brief time itself — so this caller takes no
  now argument. The caller's snapshot is never
  mutated, and the filler never raises. Boot only:
  the digest belongs to the boot brief, so the
  morning and ondemand paths do not call it, and
  generate_brief itself is untouched, so the pinned
  brief shapes keep their exact form. The
  brief_boot.md OS-051 section is updated to record
  the caller.
  Proven live, not just in tests: a dry-run boot
  brief over a fixture snapshot carried "Previous
  session: last brief 2026-10-26 03:33 ET, 2 jobs
  completed (brief panel; dispatch poster), 1 open
  thread (watchdog loop)", and a dry-run morning
  brief over the same snapshot carried no digest
  line.
- Tests: tests/test_intel_brief_previous_session_caller.py,
  WithPreviousSessionTest, 12 tests, passing (record
  built from last_brief and shutdown_jobs, filled
  record rendering the digest, boot template brief
  over a filled snapshot carrying the digest,
  non-boot brief over a filled snapshot carrying no
  digest, hand-stated record winning unchanged,
  caller snapshot never mutated, last brief with no
  usable time getting no record, missing or non-list
  shutdown_jobs getting no record, explicitly empty
  shutdown_jobs stating a clean shutdown, current
  jobs never read as shutdown jobs, previous_brief
  diff record never read as a last brief, non-dict
  snapshot getting no record and never raising).
  Brief tests after this change: test_intel_brief 166
  unchanged + 12 new. Full suite by module loader:
  1899 tests = 1887 pre-change baseline + 12 new,
  with only the same 2 pre-existing environmental
  errors as the baseline (boss_trigger loader,
  bustools parity).
  No bus post was made for this change.
- NOT proven here: the digest against a last brief
  read from the brief store itself rather than a
  caller-stated last_brief (the filler consults no
  store, so a caller that states no last brief gets
  no digest even when an earlier brief sits in the
  store), or a Spark-composed boot brief carrying
  this line (real Spark transport still blocked).
## 2026-10-28 - OS-117 follow-up - morning-path caller fills a snapshot's federation record
- What changed: before this change no caller in the repo
  filled `federation`: a morning brief carried its
  Federation section only when the snapshot hand-stated
  the record, and a snapshot that only carried the
  joined machines carried no section at all. Now
  `intel/brief.py` `with_federation` builds the record
  from the snapshot's own stated inputs —
  "joined_machines", the joined machines' list (each
  machine's name, its crew's completions verbatim, and
  its cross-machine jobs with id, title, and status
  when stated), and "trust_events", the stated joins
  and refusals with their machine and detail — with
  one as_of stamp for the whole record, and
  `intel.py brief` calls it for boot and morning
  briefs, after with_memory_depth (ondemand left
  alone: the section belongs to the morning/daily
  brief, not to an ad hoc window brief). A snapshot
  that hand-states a record keeps it untouched. A
  snapshot yielding fewer than two usable machines
  gets no record at all, since a single-machine record
  renders no section anyway and trust events without
  two machines are not a federation section, so older
  briefs keep their exact shape. A machine named
  twice counts once, first entry wins; a machine
  without a name, a cross-machine job without an id
  and a title, a trust event without a machine name,
  and a trust event of any kind but join or refusal
  are skipped, never guessed; a machine with no
  completions still counts and reads "no completions
  reported" from the renderer, never a padded title.
  The caller's snapshot is never mutated, and the
  filler never raises, so the morning path still
  produces a brief, just without this section, on a
  builder failure.
  brief_boot.md OS-117 section is updated to record
  the caller.
  Proven live, not just in tests: a dry-run morning
  brief over a fixture snapshot carried "Federation"
  with the machine lines and the refusal line, and a
  dry-run ondemand brief over the same snapshot
  carried no Federation section.
- Tests: tests/test_intel_brief_federation_caller.py,
  WithFederationTest, 13 tests, passing (record
  built from joined_machines and trust_events with
  one stamp, filled record rendering the section
  lines, hand-stated record winning unchanged,
  caller snapshot never mutated, single machine
  getting no record, nothing usable getting no
  record, malformed entries skipped never guessed,
  machine named twice listed once, machine with no
  completions reading none reported, refusal without
  a detail reading reason not reported, morning
  template brief over a filled snapshot carrying the
  section, default stamp an int, non-dict snapshot
  getting no record and never raising).
  Brief tests after this change: test_intel_brief 166
  unchanged + 13 new. Full suite by discover: 1985
  tests = 1972 clean-tree baseline + 13 new, with
  only the same 2 pre-existing environmental errors
  as the baseline (boss_trigger loader, bustools
  parity), verified identical on the clean tree via
  git stash.
  No bus post was made for this change.
- NOT proven here: the section against a live
  federation (the join flow, trust enforcement,
  two-machine drill, and policy ruling have not
  landed, so the caller fills the record only from a
  snapshot that states its joined machines), or a
  Spark-composed morning brief carrying this section
  (real Spark transport still blocked).

## 2026-10-28 — OS-127 follow-up — boot-path caller fills the recovery record

- Before this change no caller in the repo filled
  `recovery`: a boot brief carried its one
  in-flight-jobs-recovered line only when the snapshot
  hand-stated a "recovery" record, and a boot
  snapshot that only carried the lease sweep's own
  stated outcome carried no line at all.
- After this change `intel.py brief --boot` calls
  `with_recovery` after `with_previous_session`
  (boot only), so a boot snapshot that states
  `sweep_recovered`, `sweep_count`, and
  `sweep_corrupted` carries the line; a snapshot
  that hand-states a record keeps it untouched, and
  one that states no sweep outcome keeps its exact
  old shape. A stated sweep count of zero with no
  recovered jobs reads "0 recovered" plainly, while
  a snapshot with no sweep count never reads zero.
  A job listed twice is one recovery, and a skipped
  malformed entry voids the sweep count, so it can
  never reconcile into a clean count. A recovered
  job with no baton step reads "step not reported",
  never an invented step.
- CLI check (dry run, no store): `intel.py brief
  --boot` over a fixture snapshot with one recovered
  job and sweep count 1 prints "In-flight jobs
  recovered at this boot: 1 recovered: job 5 brief
  panel (resumed at step 2)"; over a fixture with
  sweep count 0 it prints "0 recovered"; a morning
  brief over the same sweep snapshot prints no
  recovery line, proving the boot-only rule.
- Tests: tests/test_intel_brief_recovery_caller.py,
  WithRecoveryTest, 16 tests, passing (record built
  from sweep lists with one stamp, filled record
  rendering the line, boot template brief over a
  filled snapshot carrying the line, clean shutdown
  reading zero, no sweep count never reading zero,
  hand-stated record winning unchanged, caller
  snapshot never mutated, nothing usable getting no
  record, malformed entries skipped never guessed
  with the count voided, job listed twice counted
  once, missing baton step reading not reported,
  sweep mismatch reading incomplete with both
  counts, recovered jobs without a sweep count
  reading incomplete, invalid sweep counts ignored,
  default stamp an int, non-dict snapshot getting
  no record and never raising).
  Brief tests after this change: test_intel_brief 166
  unchanged + 16 new. Full suite by module loader:
  2020 tests = 2004 clean-tree baseline + 16 new,
  with only the same 2 pre-existing environmental
  issues as the baseline (boss_trigger loader,
  bustools parity), verified identical on the
  baseline run before this change.
  No bus post was made for this change.
- NOT proven here: the line against a real OS-126
  plug-pull drill, or against a live lease sweep at
  all (the sweep verification has not landed, so the
  caller fills the record only from a snapshot that
  states its sweep outcome), or a Spark-composed
  boot brief carrying this line (real Spark
  transport still blocked).

## 2026-10-28 — OS-062 follow-up — boot-path caller fills the system_state record

- Before this change no caller in the repo filled
  `system_state`: a boot brief carried its three
  drivers + tools + apps lines with values only when
  the snapshot hand-stated a "system_state" record,
  and a boot snapshot that only carried the machine's
  own stated state carried the not-reported lines
  instead.
- After this change `intel.py brief --boot` calls
  `with_system_state` after `with_recovery`
  (boot only), so a boot snapshot that states
  `drivers`, `gateway_healthy`, and `skill_apps` as
  flat lists carries the three lines with values; a
  snapshot that hand-states a record keeps it
  untouched, and one that states nothing usable keeps
  its exact old shape, still rendering the three
  not-reported lines. A driver or skill app named
  twice is one entry, and malformed names are skipped,
  never guessed. A stated empty list reads "no
  drivers reported" or "no skill apps mounted",
  never "not reported". Gateway health counts only
  as a real bool, so a caller that does not know its
  gateway health never gets a healthy or down line
  it did not state; a down gateway is said to be
  down, never omitted.
- CLI check (dry run, no store): `intel.py brief
  --boot` over a fixture snapshot stating drivers
  muse-code and relay-driver, gateway_healthy false,
  and skill apps briefing and dispatch prints
  "Drivers: muse-code, relay-driver available",
  "Tools: MCP gateway down, so agents cannot reach
  their tools through it", and "Skill apps: briefing,
  dispatch mounted".
- Tests: tests/test_intel_brief_system_state_caller.py,
  WithSystemStateTest, 17 tests, passing (record built
  from flat lists with one stamp, filled record
  rendering the three lines in order, boot template
  and generated briefs over a filled snapshot carrying
  the lines, non-boot brief never carrying them,
  hand-stated record winning unchanged, caller
  snapshot never mutated, nothing usable getting no
  record, name listed twice being one entry, malformed
  names skipped never guessed, junk-only lists
  building no record, gateway down kept, non-bool
  gateway health skipped never guessed, stated empty
  lists reading none, partial state building a partial
  record, default stamp an int, non-dict snapshot
  getting no record and never raising).
  Brief tests after this change: test_intel_brief 166
  unchanged + 17 new. Full suite by discover:
  2038 tests = 2021 clean-tree baseline + 17 new,
  with only the same 2 pre-existing environmental
  issues as the baseline (boss_trigger loader,
  bustools parity), verified identical on the
  baseline run before this change.
  No bus post was made for this change.
- NOT proven here: the lines against live machine
  state on the test image (the driver contract, the
  gateway daemon, and the skills loader have not
  landed, so the caller fills the record only from a
  snapshot that states its machine state), or a
  Spark-composed boot brief carrying these lines
  (real Spark transport still blocked).

## 2026-10-28 — INT-027 follow-up — morning-path caller fills the priority_order record

- Before this change no caller in the repo filled
  `priority_order`: a morning brief carried its
  Priority order section only when the snapshot
  hand-stated a "priority_order" record, and a
  snapshot that only carried the order as a plain
  list of job ids carried no section at all.
- After this change `intel.py brief` calls
  `with_priority_order` for boot and morning briefs
  (ondemand left alone, the section belongs to the
  morning/daily brief), so a snapshot that states
  `priority_ids` carries the section; a snapshot
  that hand-states a record keeps it untouched, and
  one that states no usable id keeps its exact old
  shape. A job id listed twice is one entry, and
  malformed ids are skipped, never guessed. The
  caller does not filter ids against the snapshot's
  jobs list: the renderer already skips an id with
  no matching job, so a stated order over jobs
  outside the window reads none reported rather
  than being silently rewritten.
- CLI check (dry run, no store): `intel.py brief
  --morning` over a fixture snapshot with jobs 7
  spark client and 3 brief panel and priority_ids
  ["3", "7"] prints "Priority 1: 3 brief panel" and
  "Priority 2: 7 spark client"; the same snapshot
  over `--ondemand` prints no Priority order
  section, proving the morning-only rule, and over
  `--boot` it prints the same two lines, since the
  boot brief uses the morning format.
- Tests: tests/test_intel_brief_priority_caller.py,
  WithPriorityOrderTest, 15 tests, passing (record
  built from priority_ids with one stamp, filled
  record rendering the lines in order, morning
  template and generated briefs over a filled
  snapshot carrying the section, unfilled snapshot
  carrying no section, hand-stated record winning
  unchanged, caller snapshot never mutated,
  nothing usable getting no record, id listed
  twice counted once, malformed ids skipped never
  guessed, junk-only and empty lists building no
  record, unknown id kept for the renderer to read
  none reported, default stamp an int, non-dict
  snapshot getting no record and never raising).
  Brief tests after this change: test_intel_brief 166
  unchanged + 15 new. Full suite by discover:
  2053 tests = 2038 clean-tree baseline + 15 new,
  with only the same 2 pre-existing environmental
  issues as the baseline (boss_trigger loader,
  bustools parity); the baseline run also showed
  the order-dependent digest busiest-hour failure
  once, which passes alone and did not recur in
  the final run, so it is not a new failure from
  this change.
  No bus post was made for this change.
- NOT proven here: the section against a stated
  order from a real lane caller (no lane caller
  states priority_ids yet, so the filler in
  practice runs only over fixture snapshots), a
  blocked_contacts caller (a blocked job carries no
  owner field, so an ask nick cannot be filled
  without guessing), or a Spark-composed morning
  brief carrying this section (real Spark transport
  still blocked).

## 2026-10-28 — INT-027 follow-up — morning-path caller fills the blocked_contacts record

- Before this change no caller in the repo filled
  `blocked_contacts`: a morning brief carried its
  Blocked contacts section only when the snapshot
  hand-stated a "blocked_contacts" record, and a
  snapshot that only carried the ask nicks as a
  plain stated list carried no section at all.
- After this change `intel.py brief` calls
  `with_blocked_contacts` for boot and morning briefs
  (ondemand left alone, the section belongs to the
  morning/daily brief), so a snapshot that states
  `blocked_contact_entries` carries the section; a
  snapshot that hand-states a record keeps it
  untouched, and one that states no usable entry
  keeps its exact old shape. A job_id listed twice
  is one entry with its first ask nick, and
  malformed entries are skipped, never guessed. No
  nick is read from the jobs list: a blocked job
  carries no owner field — jobs.py cmd_blocked
  deletes the claim, claim host, claimed_at, and
  lease when it marks a job blocked — so the ask
  nick comes only from the caller's stated entries,
  and an entry stating a job_id with no usable nick
  reads owner not reported in this window, never a
  guessed nick. The caller does not filter entries
  against the snapshot's jobs list: the renderer
  already ignores a contact for a job that is not
  blocked in this snapshot.
- CLI check (dry run, no store): `intel.py brief
  --morning` over a fixture snapshot with blocked
  jobs 7 spark client and 9 watchdog loop and a
  stated entry asking milo about 7 prints "Ask milo
  about 7 spark client" and "9 watchdog loop: owner
  not reported in this window"; the same snapshot
  with no stated entries prints no Blocked contacts
  section, proving the old shape is kept.
- Tests: tests/test_intel_brief_blocked_contacts_caller.py,
  WithBlockedContactsTest, 16 tests, passing (record
  built from stated entries with one stamp, filled
  record rendering the lines, morning template and
  generated briefs over a filled snapshot carrying
  the section, unfilled snapshot carrying no
  section, hand-stated record winning unchanged,
  caller snapshot never mutated, nothing usable
  getting no record, job listed twice counted once
  with its first ask nick, malformed entries
  skipped never guessed, junk-only and empty lists
  building no record, entry without an ask nick
  reading owner not reported, contact for a
  non-blocked job ignored by the renderer, default
  stamp an int, non-dict snapshot getting no record
  and never raising).
  Brief tests after this change: test_intel_brief 166
  unchanged + 16 new. Full suite by discover:
  2096 tests = 2080 merged-tree baseline + 16 new,
  with only the same 2 pre-existing environmental
  errors as the baseline (boss_trigger loader,
  bustools parity).
  No bus post was made for this change.
- NOT proven here: the section against stated
  entries from a real lane caller (no lane caller
  states blocked_contact_entries yet, so the filler
  in practice runs only over fixture snapshots), or
  a Spark-composed morning brief carrying this
  section (real Spark transport still blocked).

## 2026-10-28 — INT-027 follow-up — morning-path caller fills the held_decisions record

- Before this change no caller in the repo filled
  `held_decisions`: a morning brief carried its Held
  decisions section only when the snapshot hand-stated
  a "held_decisions" record, and a snapshot that only
  carried the waiting questions as a plain stated list
  carried no section at all.
- After this change `intel.py brief` calls
  `with_held_decisions` for boot and morning briefs
  (ondemand left alone, the section belongs to the
  morning/daily brief, not to an ad hoc window brief):
  a snapshot that carries no "held_decisions" key gets
  a copy with one built from its own stated
  held_decision_entries list, each entry a question
  with an optional decider nick, with one as_of stamp
  for the whole record. A snapshot that hand-states a
  record keeps it untouched, and a snapshot that states
  no usable question gets no record, so older briefs
  keep their exact shape.
- No question is read from the jobs list: a blocked
  reason or a job title is not a question waiting on
  Dale's word, so the question comes only from the
  stated entries, never guessed. A question named twice
  is one decision with its first decider, malformed
  entries are skipped, and an entry with no usable
  decider reads decider not reported. The Sources
  section needs no filler of its own: the renderer
  already reads the snapshot's plain source_pointers
  list directly.
- Rubric: intel/evals/brief_rubric.md INT-027 gaps 3/4
  section updated with this follow-up.
- CLI check (dry run, no store): `intel.py brief
  --morning` over a fixture snapshot with stated
  entries prints "Held decision: Ship the brief panel
  first? (waiting on del)" and "Held decision: Which
  gateway for the demo? (decider not reported)", plus
  the Sources line from the stated pointers; the same
  snapshot with no stated entries prints no Held
  decisions section, proving the old shape is kept.
- Tests: tests/test_intel_brief_held_decisions_caller.py,
  WithHeldDecisionsTest, 14 tests, passing (record
  built from stated entries with one stamp, filled
  record rendering the lines, morning template and
  generated briefs over a filled snapshot carrying
  the section, unfilled snapshot carrying no
  section, hand-stated record winning unchanged,
  caller snapshot never mutated, nothing usable
  getting no record, question listed twice counted
  once with its first decider, malformed entries
  skipped never guessed, junk-only list building no
  record, entry without a decider reading decider
  not reported, default stamp an int, non-dict
  snapshot getting no record and never raising).
  Brief tests after this change: test_intel_brief 166
  unchanged + 14 new. Full suite by file loader:
  2121 tests = 2107 merged-tree baseline + 14 new,
  with only the same 1 pre-existing environmental
  error as the baseline (bustools parity, live skill
  script missing outside the repo).
  No bus post was made for this change.
- NOT proven here: the section against stated
  entries from a real lane caller (no lane caller
  states held_decision_entries yet, so the filler
  in practice runs only over fixture snapshots), or
  a Spark-composed morning brief carrying this
  section (real Spark transport still blocked).

## 2026-10-28 — BRF-019 follow-up — morning-path caller fills the previous_brief record

- Before this change no caller in the repo filled
  `previous_brief`: a morning brief carried its Since
  your last brief section only when the snapshot
  hand-stated a "previous_brief" record, and a
  snapshot that only carried the previous brief's job
  statuses as a plain stated list carried no section
  at all.
- After this change `intel.py brief` calls
  `with_previous_brief` for boot and morning briefs
  (ondemand left alone, the section belongs to the
  morning/daily brief, not to an ad hoc window
  brief): a snapshot that carries no "previous_brief"
  key gets a copy with one built from its own stated
  previous_brief_entries list, each entry a job id
  with the status that job carried in the previous
  brief, with one as_of stamp for the whole record.
  A snapshot that hand-states a record keeps it
  untouched, and a snapshot that states no usable id
  gets no record, so older briefs keep their exact
  shape.
- No previous status is read from the current jobs
  list: comparing the window against itself would
  report nothing changed, always, so the previous
  statuses come only from the stated entries, never
  guessed. A job id named twice is one previous
  entry with its first status, malformed entries are
  skipped, and an entry with no usable status is
  still usable: the renderer reads that previous
  status as empty, which is the stated absence, not
  a guessed status.
- Rubric: intel/evals/brief_rubric.md BRF-019 gap 2
  section updated with this follow-up.
- CLI check (dry run, no store): `intel.py brief
  --morning` over a fixture snapshot with stated
  entries prints "Changed since your last brief: 7
  spark client: done -> blocked"; the same snapshot
  with no stated entries prints no Since your last
  brief section, proving the old shape is kept.
- Tests: tests/test_intel_brief_previous_brief_caller.py,
  WithPreviousBriefTest, 16 tests, passing (record
  built from stated entries with one stamp, filled
  record rendering changed and new lines, morning
  template and generated briefs over a filled
  snapshot carrying the section, unfilled snapshot
  carrying no section, hand-stated record winning
  unchanged, caller snapshot never mutated, nothing
  usable getting no record, id listed twice counted
  once with its first status, malformed entries
  skipped never guessed, junk-only list building no
  record, entry without a status still usable,
  previous statuses never read from the current
  jobs list, default stamp an int, non-dict
  snapshot getting no record and never raising).
  Brief tests after this change: test_intel_brief 166
  unchanged + 16 new. Full suite by discover:
  2138 tests = 2122 baseline + 16 new, with only
  the same 2 pre-existing environmental errors as
  the baseline (boss_trigger loader, bustools
  parity).
  No bus post was made for this change.
- NOT proven here: the section against stated
  entries from a real lane caller (no lane caller
  states previous_brief_entries yet, so the filler
  in practice runs only over fixture snapshots), or
  a Spark-composed morning brief carrying this
  section (real Spark transport still blocked).

## 2026-10-28 — BRF-018 follow-up — template composer renders the on-join sections for kind="onjoin"

- Before this change the template composer rendered the
  morning sections for every kind, so an on-join
  template brief carried no project sentence, no
  likely-lane line, and no ask-for-a-first-job line:
  the composer gap the BRF-018 cold-read verdict
  pinned, which the v2 prompt alone could not fix
  because a template brief gains nothing from a
  prompt file.
- After this change `compose_template_brief` takes
  kind="morning" by default and renders the four
  BRF-002 sections for kind="onjoin" via
  `onjoin_template_lines`, in prompt order: What
  this crew is building, Your likely lane, What is
  blocked, Who to ask. `compose_brief`'s two
  template fallback paths now pass kind through, so
  `generate_brief(kind="onjoin")` carries the
  sections too. Every other kind, an unknown kind,
  and a boot brief keep the morning shape exactly,
  and the stored record's five section keys are
  unchanged.
- Nothing is guessed: the crew-building sentence is
  the snapshot's stated crew_building string when
  the caller states one, else the prompt's own
  not-stated sentence; the likely-lane line names an
  open job's lane field in the v2 rule 9 form when
  the record carries one, and names a newcomer's
  capability record verbatim when one is stated for
  a newcomer, and when neither is stated it says so
  and points to the first owner to ask for a first
  job (or says plainly that no owner is recorded);
  blocked reasons stay verbatim, or the section
  reads "Nothing blocked in this window"; Who to
  ask marks an owner "not online in this window"
  only when the snapshot carries a presence list
  that does not name them, plus the blocked-contact
  ask nick when the snapshot carries a
  blocked_contacts record. The four section lines
  are plain lines, so the BRF-007 trim cannot drop a
  blocked job or an ask-nick ahead of any other
  line.
- Reconciliation, not a dropped test: the first cut
  of this change rendered only the four sections and
  broke the INT-004 e2e3 loop in the full suite
  (its on-join stage reads the blocked job from a
  "Blocked and why" section and the stall alert from
  a "Watch items" section). Rather than weaken that
  pinned loop, the on-join template now carries
  those two sections additively after Who to ask,
  in the morning bullet form, and only when they
  have content, the same additive pattern the
  morning template already uses for Daily and
  Federation. A brief with no blocked job carries no
  additive Blocked section, and one with no alerts
  carries no additive Watch section. The e2e3 loop
  passes unmodified.
- Rubric: intel/evals/brief_rubric.md BRF-018
  follow-up on-join template sections check added.
- Dry-run check (generate_brief kind="onjoin",
  dry run, no store): over a fixture snapshot the
  brief reads 74 words with all four sections, the
  open job named, the blocked reason verbatim, and
  the first owner named to ask; an on-join brief
  over an empty room still says no activity yet
  under BRF-012, not four empty sections.
- Tests: tests/test_intel_brief_onjoin_template.py,
  OnJoinTemplateTest, 18 tests, passing (four
  sections in order, crew sentence stated and
  not-stated, lane in v2 form, lane never guessed
  from a title, newcomer caps verbatim, fallback
  ask line, no owner recorded, blocked verbatim
  and nothing-blocked line, not-online marker,
  blocked-contact ask nick, default kind keeping
  the morning shape, unknown kind falling back to
  morning, boot plus onjoin keeping the boot shape,
  compose and generate paths carrying the sections
  within the 150-word budget, non-dict snapshot
  never raising, no additive sections without
  content). Brief tests after this change:
  test_intel_brief 166 unchanged + 18 new. Full
  suite by discover: 2156 tests = 2138 baseline +
  18 new, with only the same 2 pre-existing
  environmental errors as the baseline (boss_trigger
  loader, bustools parity).
  No bus post was made for this change.
- NOT proven here: a Spark-composed on-join brief
  under the v2 prompt (real Spark transport still
  blocked), a brief for a newcomer named by a lane
  caller (no lane caller invokes kind="onjoin"
  yet, and intel.py brief has no --onjoin flag;
  the path proven here is generate_brief /
  compose_brief with kind="onjoin"), or the
  sections against Buffy's busy fixture (not in
  this repo yet).

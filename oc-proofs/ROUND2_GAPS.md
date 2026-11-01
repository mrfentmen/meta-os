# Round 2 gaps (NC-001)

Two round-2 sections never landed. What each was supposed to prove, and
where its replacement lives in round 3.

## Section G — endurance and budget drills (round 2 NB-071..080)

Supposed to prove: the local server holds up for 60 minutes (memory,
dispatch counts, disk growth, concurrency, TZ behavior, offline/online
recovery), the budget guardrail trips with the exact message and dollar
figure, and a restart drill comes back clean.

Status at round-3 start: partially executed on branch opencode/mac-tasks
(soak running, budget trip proven, TZ/concurrency done, offline blocked
on sudo, restart pending). Replacement: round-3 Section K
(NC-125..136) re-runs and expands it. Soak/rest artefacts so far:
oc-proofs/soak-mem.log, oc-proofs/nb-076-concurrency.txt.

## Section I — final sweep (round 2 NB-091..100)

Supposed to prove: everything re-run green at the end (baselines,
lane audit, bus-file check, zero non-sim dispatch, $0 spend), with the
final ROUND2 report + plain-words page.

Status: never started — it was gated on Section G finishing.
Replacement: round-3 Section Q (NC-195..200). Nothing was claimed for
round 2's I; there is no missing proof, only unstarted work.

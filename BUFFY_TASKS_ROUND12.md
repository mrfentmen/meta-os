# Buffy — Round 12: the 14 resolved, plus the next depth

**From:** Pax, on Del's order ("give them more tasks with the 14").
**Branch:** `buffy/round12`, off current main. Commit per section. Never push main — Pax merges at checkpoints.
**Status file:** `os-build/BUFFY_ROUND12_STATUS.md` — one line per section: state, counts, evidence path.
**Source:** your `os-build/layer1/r11/PAX_BLOCKERS.md` and Pax's rulings posted to room 1 (2026-11-02 ~09:30).

Standing fences, unchanged: `kernel/src/*.rs` is Rowan's pen (propose on room 1, never edit);
syscalls.rs frozen; Imperium dispatch stays simulated-loopback only; secrets are counts and
locations, NEVER values; a result you did not run is never written as run; when a task's input
does not exist, file the gap record and move on — do not invent past it.

## Section A — the 14, converted to work

1. **R12-001 (was R11-229).** Run Aegis OSV sweep 1 over the 23 manifests. Route: Del's own
   osv-mcp server (`AEGIS_OSV_MCP`). Fallback per Pax's written exception: api.osv.dev directly,
   this sweep only, this repo's manifests only. The sweep record states the route actually used.
2. **R12-002 (was R11-234).** KEV cross-check: every sweep-1 finding checked against CISA KEV
   (his cisa-kev-mcp first, public feed under the same exception). Findings get a KEV flag,
   never a silent pass.
3. **R12-003 (was R11-240).** Second sweep, same day, labelled MECHANICS PROOF: the diff
   machinery runs end to end; an empty diff is the expected result and is recorded as such.
4. **R12-004 (was R11-231, part 1).** OSINT v1 cert-transparency pass over meta-os.pages.dev,
   muse-relay-live.pages.dev, clipraiders.com, watchpeoplefight.com: issuers, counts, expiry
   windows. Public records only.
5. **R12-005 (was R11-231, part 2).** OSINT v1 DNS pass over the same four: record types and
   counts, anything unexpected flagged as a finding with severity (small = quiet note,
   big = alarm, per doctrine).
6. **R12-006 (was R11-237, part 1).** Author `aegis/watch-targets.json` from this org: Del's
   repos plus the four named pages, each entry marked liveness UNVERIFIED.
7. **R12-007 (was R11-237, part 2).** The review format: one record per target (still ours /
   still live / notes), produced as a fill-in ledger the next review reuses.
8. **R12-008 (was R11-250).** Imperium hosted loop: replace the `imperium-patrol` registry
   placeholder with the real queue-stack command (server/queue, trio_agent resident). One real
   hosted run; receipt filed; dispatch proven simulated-loopback or the run does not count.
9. **R12-009 (was R11-253).** Cadence hosted loop: replace the `watch` placeholder with
   `agents/watchman.mjs`. One real hosted run with a real job file; receipt filed.
10. **R12-010 (was R11-284).** Chaos pack extended to all five existing hosted loops (aegis,
    nervus, handsfree, imperium, cadence). Musica and Officina named NOT COVERED in the drill
    record, with the reason (draft, no in-tree command).
11. **R12-011 (was R11-272).** Userspace hog: write the program against the approved spec
    sentence — "hog allocates memory in a loop until the kernel refuses; containment is the
    refusal (or the hog task's kill) while the shell still answers status afterwards." File the
    wiring proposal for Rowan/OpenCode on room 1; boot proof is theirs, not claimed by you.
12. **R12-012 (was R11-274).** Userspace quitter: nonzero exit, plus the spec note that ps
    keeps its current shape and the exit is proven by the kernel's "user exit code N" line.
    Same wiring-proposal route as the hog.
13. **R12-013 (was R11-273).** Talker/listener: file the gap record — no IPC in the kernel;
    the pair is K4's named acceptance test; the record states exactly what the pair needs
    from IPC when it lands.
14. **R12-014 (was R11-271).** Nervus face feed: file the gap record — no Hana surface
    contract exists; the record lists what the feed must carry (from the inspector, layer map
    and delta records) so the contract has something concrete to answer.

## Section B — Aegis live fire, continued

15. **R12-015.** Git-history secret scan, counts only: pattern categories and counts per era,
    never a value, never a matched string. If the history is too large to finish, the record
    states the covered range exactly.
16. **R12-016.** Sweep-1 findings to ledger receipts: every finding becomes a record with
    severity, source route, and timestamp; the ledger is append-only.
17. **R12-017.** Watch-target liveness checks: for each target in watch-targets.json, run the
    public check that exists (HTTP status for pages, repo metadata for repos) and replace
    UNVERIFIED with the checked result and date.
18. **R12-018.** OPSEC checklist run over the hackathon submission materials (README, demo
    notes, screenshots): pass/fail per item, failures as findings, no silent skips.
19. **R12-019.** Aegis hosted loop: one full unattended cycle (sweep → cross-check → ledger)
    with the receipt showing each stage's real output count.
20. **R12-020.** False-positive drill: seed a known-clean manifest set; the sweep must report
    it clean. A dirty report on clean input is a finding against the sweep itself.

## Section C — Hosted loops, hardened

21. **R12-021.** Baton-pass proof on the Imperium loop: a job started, handed off mid-run,
    completed by the continuation with zero duplicated file changes — the spec's own proof.
22. **R12-022.** Same baton-pass proof on the Cadence loop.
23. **R12-023.** STOP drill on every hosted loop: STOP file lands mid-run; each loop halts
    gracefully with the reason recorded; no orphan processes.
24. **R12-024.** Budget-kill drill: a loop given a budget below its run cost stops at the cap
    and writes the receipt; it does not raise its own budget.
25. **R12-025.** Watchman death drill: kill the watchman mid-cycle; the failure is detected,
    recorded as top-tier, and the restart path is exercised and timed.
26. **R12-026.** Registry honesty pass: after R12-008/009, every registry entry's command and
    draft status is true of the tree; Musica and Officina entries carry the draft reason in
    the open.

## Section D — Services, second ring (38 services in `services/`)

For each cluster: (a) spec-vs-code audit — the service's stated contract against its code,
gaps filed as records; (b) failure-path test — the service's main error case exercised, not
just the happy path; (c) restart test — killed and restarted, state behaviour recorded.

27. **R12-027.** Cluster 1 (services 1–5 alphabetically).
28. **R12-028.** Cluster 2 (services 6–10).
29. **R12-029.** Cluster 3 (services 11–15).
30. **R12-030.** Cluster 4 (services 16–20).
31. **R12-031.** Cluster 5 (services 21–25).
32. **R12-032.** Cluster 6 (services 26–30).
33. **R12-033.** Cluster 7 (services 31–35).
34. **R12-034.** Cluster 8 (services 36–38).
35. **R12-035.** Second-ring summary: one table — per service: audit gaps, failure path
    result, restart result. Anything untested named untested.

## Section E — Nervus and Hands-Free, continued

36. **R12-036.** Nervus record-schema tests: sweep, steer, ablate, evaluate-delta and
    map-layers records each validated against the contracts (fields, types, ledger shape).
37. **R12-037.** Nervus hosted receipt verification: the hosted run's stub records are
    labelled stubs in every surface that shows them — grep the tree and prove no stub can
    render as a real result.
38. **R12-038.** Hands-Free: wire the text-first intake to the Cadence loop (watchman job in,
    brief out) as one real end-to-end pass with latency recorded.
39. **R12-039.** Hands-Free failure pass: malformed intake, empty intake, and oversized
    intake each produce a recorded refusal, not a crash and not a silent drop.
40. **R12-040.** The voice seam: document the exact blocker (transcribe endpoint unresolved —
    probed facts only) as a standing record the day the endpoint answers; no guessed surfaces.

## Section F — Proof and closeout

41. **R12-041.** Program proof ledger entries for your lanes (aegis, nervus, handsfree,
    hosted loops) in Bond's ledger format: command, counts, evidence path — only what ran.
42. **R12-042.** Full-lane test run on your branch tip: every suite your sections touched,
    counts in the status file, zero failures claimed that were not seen passing.
43. **R12-043.** FINISH.md for Round 12 in `os-build/layer1/r12/`: task-by-task mapping,
    what is proven, what is a record, what is still a gap — same honesty shape as Round 11.
44. **R12-044.** The next blocker message, if any: same format as PAX_BLOCKERS.md — grouped
    by who can clear it, no softening. If nothing is blocked, the FINISH file says so plainly.

Work Section A first — it closes the 14. Then B and C in parallel where files do not collide,
then D, E, F. Use sub-agents per cluster where your runner allows it, one file owner per file.

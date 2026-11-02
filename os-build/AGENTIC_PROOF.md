# IS THE OS AGENTIC? — proof pack (Pax, 2026-11-02)

Question put by the boss: prove the OS is agentic. Honest split:
what runs today, and what does not yet.

## PROVEN — agents acting on their own, with artifacts

1. **Imperium loop (the flagship).** PATROL -> REVIEW -> INVESTIGATION
   -> RECORDS -> RESPONSE runs as real code end to end on the Mac.
   On a confirmed RED the agent itself sends the dispatch package
   WITH THE PICTURE to the labelled simulated endpoint - no human in
   the send path (human verify is an env flag, default OFF).
   Artifacts on main: os-build/logs/R5-imperium/ (incident.json shows
   dispatched-simulated; receipt.txt receipt_id=sim-6623d237a90b3d9d,
   simulated=true). Ignis ran the same loop in Round 6 (visible flame
   -> dispatched-simulated + picture + receipt; smoke correctly HELD
   at yellow). YELLOW never dispatches. Orchestrator stops: 8 actions
   / 12 calls / $0.50 per incident.
2. **Musica overnight sessions.** The studio ran sessions on its own:
   takes generated, keeper pass kept 11 of 12 (hn029-chipsynth),
   rights checked per take, catalogue written. Records:
   os/worlds/musica/sessions/ (session.json, take_log.jsonl,
   rights.json, keepers/).
3. **Officina faber loop.** A timed loop iterates designs on its own
   (metaos-loop), stopped only by the STOP file. Harness 12/12.
4. **The watch rounds (Custos's idea, already alive as behaviour).**
   Scheduled checks poll the bus, repo and gateway, compare against
   last seen, and speak only on change - currently run by Pax's
   cadence jobs. Per the 2026-11-02 ruling this becomes a built-in
   agent capability of the OS, not a separate system.

## NOT YET — stated plainly

- **No agent runs inside the bare-metal kernel.** The kernel is a
  kernel: scheduler, tasks, syscalls. The L5 agent runtime is DESIGN
  ONLY (Milo's C1-C22 in MILO_OS_BUILDOUT.md).
- **Buffy's supervisor cannot really spawn/kill.** sys_spawn /
  sys_kill are proposals (P3); her 25 Goose services RUN as host
  processes against a substituted syscall surface - real services,
  host-bound.
- The agentic proof today is at the PLATFORM level: the systems on
  Meta OS act under rules, stop at budgets, and leave receipts.
  In-kernel agents are the road after the demo, not a claim in it.

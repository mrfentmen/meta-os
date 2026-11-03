# SUBMISSION_REHEARSAL.md (MORE_TASKS #10) — tip 54ee4353, clean detached worktree /tmp/rehearse

Built exactly as the submission will: fresh worktree at the tip, no
source edits, every suite run, counts recorded. Work continues after
this (rehearsal, not freeze).

## Results

1. Gate: `sh os-build/gate.sh` → GATE GREEN 7/7.
   Log /tmp/reh-gate.log, boot /tmp/gate-boot-90N7Fk.
   (Also serves merge-watch for 54ee4353.)
2. Cargo: `cargo test --workspace` → RED, same 2 errors as the
   prove-main run: E0271 closures returning `!` in
   os-supervisor watchdog.rs:4098/:4972 (test code, supervisor
   lane). Log /tmp/reh-cargo.log.
3. Node: `npm test` → 1947 pass, 55 fail (runner ℹ lines).
   Log /tmp/reh-node.log. Same fail shape (31 tests/native-*
   files + 6 ui.test.mjs parity subtests).
4. Python: queue 128 OK, officina 49 OK, custos 125 OK
   (TRIO_STORE=local). Logs /tmp/reh-{queue,officina,custos}.log.
5. DEMO walk (DEMO_SCRIPT.md vs committed logs ON THIS TREE):
   PRESENT: R5-soak-final.txt, K6-boot.txt, R5-imperium/
   (drill.log, receipt.txt sim-6623d237a90b3d9d,
   package-sent.json, incident.json).
   MISSING on main: os-build/logs/demo-beats/serial-all.txt,
   beat*.ppm, CAPTURE.md (R6-2 capture lives on
   opencode/round6 only — needs a Pax merge before the film
   can cite main-tree paths).

## Verdict

Submission builds and boots green; suites show the three
known reds (cargo E0271 x2, node 55 native-parity, no video
capture tool in the face env). One structural gap: the R6-2
capture files are not on main yet.

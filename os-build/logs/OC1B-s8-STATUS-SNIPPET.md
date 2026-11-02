# OC1B-s8 STATUS SNIPPET — §8 Combined-tree re-proofs (OC1B-176..OC1B-200)

For the coordinator merge into os-build/OPENCODE1_500_STATUS.md.
Branch: opencode/500-s8 @ 94010c76 (tip at work; commit sha below).
STATUS file NOT edited here per lane rule — this snippet is the verdict.

## OC1B-176 trigger block

§8 trigger rule (spec §8, quoted): a re-proof wave runs ONLY when Pax
lands a merge wave that touches `kernel/` (source, Cargo files, or
userspace pack). Doc, face, and services merges do not trigger a wave.
Wave 0 reference: WAVE3 combined-tree proof at c7aeb162 (GATE GREEN 7/7).
Tips checked 2026-11-02: origin/main = 3452d244, opencode/500 =
94010c76; `git log c7aeb162..origin/main -- kernel/` EMPTY;
`git log origin/main..HEAD -- kernel/ os-build/userspace/` EMPTY;
`git log origin/main..HEAD -- kernel/src/syscalls.rs` EMPTY (FROZEN held).

## Task verdicts

- OC1B-176 PROVEN (trigger block above; STATUS edit left to coordinator).
- OC1B-177/181/185/189/193 PROVEN — tree records at
  os-build/logs/OC1B-reproof-w1..w5-tree.txt: NO kernel-touching merge
  wave landed; tips + empty kernel-log evidence inside.
- OC1B-178/182/186/190/194 NO WAVE — no wave-slot gate applies; the
  combined-tree gate below stands in place of per-wave gates.
  COMBINED GATE (same tree): os-build/logs/OC1B-reproof-combined-gate.log
  → GATE GREEN, 8/8 checks ok, exit 0, 329 lines, start
  2026-11-02T16:07:16Z tree 94010c76.
- OC1B-179/183/187/191/195 NO WAVE — no wave-slot serial/captures; the
  combined serial + pair stand in place:
  os-build/logs/OC1B-reproof-combined-serial.txt (1086 lines, panic 0,
  loader-refused 0),
  os-build/captures/oc1b-reproof-combined-shell.png,
  os-build/captures/oc1b-reproof-combined-fetch.png.
- OC1B-180/184/188/192/196 NO WAVE — no per-wave diff; combined diff at
  os-build/logs/OC1B-reproof-combined.md, verdict NO REGRESSION
  (all previously-green assertions re-proven with line numbers;
  readkey got=13 vs got=3 = input-length method difference;
  absent `commands:`/mem/ps lines = drive-method difference, covered by
  the gate log which typed help+status).
- OC1B-197 PROVEN — NO WAVE lines for slots 1–5 recorded in
  os-build/logs/OC1B-reproof-waves-tree.txt (and slot copies).
- OC1B-198 NO STOP — gate GREEN, no RED; kernel work stop rule not triggered.
- OC1B-199 PROVEN — index at os-build/logs/OC1B-reproof-index.md.
- OC1B-200 PROVEN — this checkpoint commit on opencode/500-s8
  (sha = branch tip after push; named in the s8 report-back for the
  coordinator to copy into OPENCODE1_500_STATUS.md).

## Affected suites re-run on the combined tree (spawn-method extra)

- queue-python full: 296 tests, OK
  (os-build/logs/OC1B-queue-combined.txt; +7 vs 289 = new wiring file).
- crew model-wiring alone: 7 tests, OK
  (os-build/logs/OC1B-crew-model-wiring.txt; offline stubbed, no key, no live call).
- Dispatch fence held: server/queue/crew.py check_dispatch_url refuses
  every non-loopback URL (DEFAULT_DISPATCH_URL http://127.0.0.1:8935/dispatch-simulated).

## Regressions / UNPROVEN / BLOCKED

- Regressions: NONE.
- UNPROVEN: NONE in §8 scope (wave slots honestly NO WAVE, not proven).
- BLOCKED: NONE (no Rowan branch awaited; no kernel merge wave to gate).

## Fences attestation

- Never pushed main; no commit to opencode/500 (this commit is on
  opencode/500-s8 only).
- No edit to kernel/src (empty diff origin/main..HEAD for kernel/ and
  os-build/userspace/); syscalls.rs untouched.
- No face/web work; Imperium dispatch untouched (simulated loopback only).
- Mac key never read (no live model call in §8); nothing secret logged.
- No padded counts: every number above names its command/file; serials,
  gate log, suite outputs committed as the named OC1B proofs.

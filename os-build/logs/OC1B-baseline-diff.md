# OC1B-018 — baseline serial vs WAVE3-combined-serial.txt

Baseline: gate run 1 serial, `os-build/logs/OC1B-baseline-serial.txt`
(1008 lines, tree 3452d244, image sha256 4d0cfaa0…).
Reference: `os-build/logs/WAVE3-combined-serial.txt` (381 lines, wave-3
combined-tree proof @ c7aeb162 era).

Method: line-class comparison (claim lines, counters, session shape).
Both files are committed; line numbers below refer to each file as stored.

## Claim lines present in BOTH (no lost claim — no REGRESSION)
- `META OS KERNEL - alive` (baseline L2, WAVE3 L2)
- `mem summary: K4 up` (baseline L26, WAVE3 L26)
- `HELLO FROM USERSPACE` + `user exit code 0` (baseline L34-35, WAVE3 L34-35)
- `INT user page-fault addr ...: task killed` (baseline L45, WAVE3 L45)
  + sleeper continues after it (`sleeper: yielded and back`,
    `sleeper: after sleep` in both)
- `user readkey: entry ...` (baseline L52, WAVE3 L52)
- `commands: status help uptime mem ps` (baseline L1002, WAVE3 L334/L337)
- `STATUS tasks=8 ticks=...` (baseline L1008, WAVE3 L341/L370)
- `user bad syscall 99 refused` (baseline L66, WAVE3 L103)
- `sleeper: bad call refused` (baseline L67, WAVE3 L104)
- `ps id ...` 8 task rows (baseline drive file L2105-2112, WAVE3 L374-381)
- `mem frames_free 126430 ...` (both)
- panic count 0 in both; `loader refused` count 0 in both.

## Changed line classes (values, not claims)
- CHANGED `K3 timer: 10 ticks after N spins`: 379572 (baseline) vs
  503612 (WAVE3). Timing-class line; expected run-to-run variance.
- CHANGED userspace byte sizes: hello 2527632 vs 2527624;
  sleeper 2798768 vs 2798760; readkey 2799720 vs 2799712
  (crashers equal at 2539200). 8-byte deltas = rebuild variance.
- CHANGED STATUS ticks: 1211 (baseline gate) vs 2177/4258 (WAVE3).
  Tick counters; variance expected.
- CHANGED readkey session shape: baseline gate ran readkey to
  progress 93000 with typed keys arriving late (`done got=9`);
  WAVE3 typed during polling (`enter seen, done got=3`, fetch
  screen captured, STATUS answered twice with moving ticks).
  Same mechanism, different drive timing — not a serial difference.

## New / missing line classes
- NEW in baseline: gate-typed `help`/`status` echo block at L1002-1008
  (WAVE3 has the same block from its own drive session at L334-370).
  No class is new in kind.
- MISSING in baseline vs WAVE3: the fetch-screen block
  (`Mrfentmen@metaos ... Programs: hello sleeper crasher (ring 3)`,
  WAVE3 L342-368) — absent because the gate types only help+status.
  Covered separately by OC1B-013 (fetch screendump) and the
  OC1B-baseline-drive.txt session, which contains the same block.
- NOTHING that is a claim line is missing.

## Verdict
Same/different: all eight gate assertions SAME (present, green in
both runs' gate logs); counters/ticks/sizes differ as run variance.
NO lost claim line, NO regression. WAVE3 §1-era proof stands,
re-proven on 3452d244.

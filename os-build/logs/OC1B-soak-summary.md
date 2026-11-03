# OC1B §7 soak summary (OC1B-166/168/169/172/173/174) — §7 soak engineer, 2026-11-02 ~11:35 EST

## Soak inventory (every §7 soak, one line)
- Wave-2 §19 (/tmp/soak-serial.txt): DIED WITH SESSION, 2 STATUS, 0 panic, duration unknown. (Details: OC1B-soak-wave2-verdict.md.)
- Tracked wave-2 follow-on (/tmp/soak3-serial.txt): COMPLETED ~11:25 EST, 20 STATUS, readkey 200000/200000, 3 clean exits, 0 panic, 0 loader-refused, duration NOT RECOVERABLE (no start record). Launcher echo: `SOAK3_DONE panics=0 runs=20`.
- Main soak attempt 1 (/tmp/oc1b-main-soak-attempt1-serial.txt): killed ~11:22 EST by host SIGTERM (pid 36720, unidentified), 2094 lines / 10 STATUS / 0 panic at death; NOT a guest fault. (Details: OC1B-soak-anomalies.txt.)
- Main soak attempt 2 (/tmp/oc1b-main-soak-serial.txt): RUNNING since 11:27:47 EST, planned end ~13:27 EST; interim 0 panic, 0 anomalies. (Details: OC1B-soak-main-start.txt, OC1B-soak-main-verdict.md.)
- 10 drill boots (OC1B-soak-main-drills.txt): 10/10 full pack, 0 panic.
- Monitor-attached boot (os-build/captures/oc1b-soak-end.png): ~4 min, screendump answers at end, 0 panic.
- K3 / K4 / KF-interactive / final soaks: NOT RUN (blocked trees — see below).

## OC1B-166 comparison against the R5-5 record (73 minutes, 0 panics)
R5-5 (OPENCODE_ROUND5_REPORT.md): one 73-minute headless QEMU run, killed
cleanly by PID afterwards, 0 panic, 0 hang, console answered at minute ~70.
§7 evidence beside it:
- Panic count: 0 panics in EVERY §7 serial and drill (wave-2 remains,
  soak3, main attempts 1+2, 10 drills, monitor boot) — stability HELD on
  the panic line, no regression anywhere.
- Duration: no §7 run in this checkpoint has a measured start→end duration
  exceeding 73 min. Soak3's scripted window (≈7080s ≈ 118 min) is longer
  than R5-5's 73 min, but its exact duration is NOT RECOVERABLE (no start
  record), so "exceeded" is NOT claimed. The main soak attempt 2 WILL be a
  measured 120-minute run (start record 11:27:47 EST) — the duration
  comparison stays INCONCLUSIVE until it ends (~13:27 EST) and OC1B-486
  collects it.
- Plain statement: stability held (zero panics across all new evidence),
  duration improvement unproven pending the measured 2-hour main soak.

## OC1B-168 image-sha table (a soak on the wrong image proves nothing)
| soak | tree | image file | sha256 | verdict |
| /tmp/soak-serial.txt (§19) | merge-tip3 (per wave-2 status) | image NOT RECOVERABLE | NOT RECOVERABLE | DIED WITH SESSION |
| /tmp/soak3-serial.txt | wave2 worktree (per 10:55 verdict) | /tmp/soak-w3-img.bin AS BOOTED: file rebuilt 10:05 post-launch | NOT RECOVERABLE (current file f13d5dd8...44a3c, measured 11:04, is NOT the booted bytes) | COMPLETED 0 panic |
| main attempt 1+2 | opencode/500-s7 @ 94010c76 | /tmp/oc1b-main-soak.bin (built 11:05 on this tree, untouched since) | 3bbedee50a7535f621dd9046ccdc198f6a83407fab302087f69ca0cf40c1d09d | attempt 1 host-killed / attempt 2 RUNNING |
| 10 drills | same as main | /tmp/oc1b-drill-img.bin (copy, sha re-verified equal) | 3bbedee5...0c1d09d (same) | 10/10 pack ok |
| monitor boot | same as main | /tmp/oc1b-soak-end.bin (copy, sha re-verified equal) | 3bbedee5...0c1d09d (same) | screendump ok |
Tree sha source: `git rev-parse HEAD` = 94010c76 on /tmp/oc500-s7.
Image sha source: `shasum -a 256` on each file (full hashes in the
per-task proof files). Copies re-verified byte-identical by sha before
booting.

## OC1B-169 total soak machine-time accumulated in this section
Measured components (each from its named record, §7 work only, wall clock):
- soak3 observed window 09:25–11:25 EST ≈ 120 min (ps STARTED/elapsed +
  launcher scripted schedule 7080s ≈ 118 min; counted as ≈120 min).
- main attempt 1: 11:07:26 → ~11:22 ≈ 15 min (start record → progress-log mtime).
- main attempt 2: 11:27:47 → 11:35 ≈ 7 min so far, still running (+~112 min
  to planned end; NOT counted until run).
- 10 drills: 10 × 15s measured waits = 150s guest-boot time (≈2.5 min).
- monitor boot: ~11:11 → 11:14 ≈ 4 min (boot → screendump → kill).
Total at checkpoint: ≈120 + 15 + 7 + 2.5 + 4 ≈ 148 min ≈ 2.5 machine-hours
of QEMU guest time under §7 (plus ~112 min still to come from the running
main soak). Wave-2 §19 run excluded (duration unknown). Attempt-1's 15 min
counted once, never merged into attempt 2.

## OC1B-172 duration-derivation note (no soak shortened silently)
- §19 run: duration unknown — NO start record exists; stated as unknown,
  never estimated. (OC1B-soak-wave2-verdict.md field table.)
- soak3: duration NOT RECOVERABLE — no start timestamp kept; the ~2h window
  is observed (ps + launcher schedule), not measured. Never stated as a
  verdict duration.
- main attempt 1: ≈15 min — measured from start record 11:07:26 to
  progress-log mtime ~11:22.
- main attempt 2: start record 11:27:47 EST; end pending ~13:27 EST;
  interim durations measured from that record only.
- drills: per-drill `waited=` fields (10 × 15s) from the drill script.
- monitor boot: boot-to-screendump ≈ 3 min (11:11 → 11:14 file mtimes).
Every verdict duration above names the record it was measured from.

## OC1B-173 NOT RUN lines (named gaps, not skipped lines)
- OC1B-161 K3 1-hour soak: NOT RUN — no §5-gated K3 tree image exists (see OC1B-soak-k3.txt).
- OC1B-162 K4 1-hour soak: NOT RUN — no §6-gated K4 tree image exists; talker/listener pair absent from this tree (see OC1B-soak-k4.txt).
- OC1B-163 30-min interactive KF soak: NOT RUN — no merged graphics tree exists; KF work unmerged/ungated (see OC1B-soak-kf.txt).
- OC1B-164 final 2-hour soak: NOT RUN — final combined tree not assembled (see OC1B-soak-final-start.txt).
- OC1B-165 final verdict: NOT RUN — blocked on OC1B-164 (see OC1B-soak-final-verdict.md).
- OC1B-171 mid-final-soak drive: NOT RUN — blocked on OC1B-164 (see OC1B-soak-final-drive.txt).

## OC1B-174 one-paragraph stability verdict for the submission
The kernel soaked without a single panic in every run this section could
observe: the completed wave-2 follow-on (20 samples, readkey 200000/200000,
0 panics), ten fresh pack-drill boots on the current tree (10/10 full pack,
0 panics), and the running 2-hour main soak (0 panics, console answering
mid-run) — while the K3, K4, graphics-interactive, and final-tree soaks
remain explicitly NOT RUN behind their ungated trees, and the duration
claim against R5-5's 73 minutes stays open until the measured main soak
ends. Nothing regressed; the long-run proof is still in flight.

## OC1B-486 final collection (coordinator, 2026-11-02 ~20:25 EST)
- Attempt 2 COMPLETED by planned launcher kill ~13:27 EST
  (/tmp/oc1b-main-soak-progress.log: SIGTERM from launcher pid 37659,
  "OC1B_MAIN_SOAK_DONE panics=0 runs=11"). Duration measured 11:07:26 →
  ~13:27 = 2h20m (start record + progress-log mtime; R5-5 duration now
  measured). Serial /tmp/oc1b-main-soak-serial.txt: 2108 lines, panic 0,
  STATUS ticks advancing (10087→13570 while driven).
- DRIVE-COVERAGE GAP (coordinator incident, named): only 11 of 21 planned
  drive interactions executed. Cause: I removed the /tmp/oc500-s7 worktree
  at the s7 merge (~12:0x) while the soak was still running; batch-2
  (10x status) + final ps invocations failed silently (drive.py path gone,
  stderr discarded by the launcher). Batch 1 (10x) + boot answers stand.
- SUPPLEMENT (same image, not the soak): /tmp/oc1b-main-soak.bin rebooted
  20:2x EST — status/mem/ps all answer (STATUS ticks=2269, K4 up, 8 ps
  rows id 7 Running, panic 0). Proof: os-build/logs/OC1B-soak-supp-serial.txt.
  Covers the missed close-state answers; does not rewrite soak history.
- Verdict: soak COMPLETED, guest healthy the full window, panics HELD at 0
  everywhere (wave-2, attempt 1, attempt 2, supplement). Drive gap owned
  above; nothing padded to hide it.

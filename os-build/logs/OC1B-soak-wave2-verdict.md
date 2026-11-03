# Wave-2 §19 soak verdict (OC1B-151..155, recorded 2026-11-02 ~10:55 EST,
final check 2026-11-02 11:04 EST by §7 soak engineer)

## The §19 run named in the wave-2 status (/tmp/soak-serial.txt)
Path: /tmp/soak-serial.txt (merge-tip3 image per OPENCODE1_WAVE2_STATUS.md §2-19).
State at 11:04 EST: QEMU GONE (no qemu process on this file; last serial
write Nov 2 08:47 EST). Content: 63 lines, 2 STATUS samples, 0 panic,
0 loader-refused (commands: `grep -c "STATUS tasks="`, `grep -ci panic`,
`grep -c "loader refused"` on /tmp/soak-serial.txt).
Start: no start-time record kept -> START NOT RECOVERABLE.
Image: merge-tip3 kernel image, sha NOT recorded -> NOT RECOVERABLE.
Verdict: DIED WITH SESSION — duration unknown. (OC1B-153 plain verdict.)

## The tracked follow-on soak (/tmp/soak3-serial.txt)
Path: /tmp/soak3-serial.txt, image /tmp/soak-w3-img.bin, PID 93152, STILL
RUNNING at 11:04 EST (elapsed 1:38:05 per `ps`; last serial write 10:26 EST,
guest idle at shell after readkey completed).
Start: wave-2 work session, before this list landed; no start-time record
kept -> START NOT RECOVERABLE.
Image: /tmp/soak-w3-img.bin AS BOOTED -> sha NOT RECOVERABLE (the file was
rebuilt 10:05 EST, after the 9:25 launch, so the current file sha below is
NOT the booted bytes): current file sha256
f13d5dd8b56543647b23c69b8eb688e11b184e22c7245bfe9cc6733a7844aa3c
(measured 11:04 EST via `shasum -a 256 /tmp/soak-w3-img.bin`).
State at 11:04 EST: 20 STATUS samples (10 start + 10 mid), readkey
`done got=0 empties=200000`, 3x `user exit code 0`, 0 panic, 0
loader-refused (commands: `grep -c "STATUS tasks="` (=20),
`grep -ci panic` (=0), `grep -c "loader refused"` (=0),
`grep -c "user exit code 0"` (=3) on /tmp/soak3-serial.txt).
Verdict: RUNNING — not dead, not complete. Launcher script sleeps until
~11:24 EST then drives a final `ps` and kills QEMU; the COMPLETED verdict
lands in OC1B-soak-summary.md (OC1B-486 collection) once the run ends.

## Completion check (OC1B-151..155 close-out, 11:26 EST)
At 11:25:58 EST the soak3 QEMU (PID 93152) is GONE, reaped by its own
launcher: /tmp/soak3-progress.log ends with
  `SOAK3_DONE panics=0 runs=20`
(the launcher's verdict: `grep -ci panic` = 0, `grep -c 'STATUS tasks='`
= 20 on /tmp/soak3-serial.txt; independently re-verified at 11:26 EST:
`grep -c "STATUS tasks="` = 20, `grep -ci panic` = 0,
`grep -c "loader refused"` = 0, `grep -c "user exit code 0"` = 3,
`readkey done got=0 empties=200000` at serial line 2062).
Serial last write stayed 10:26 EST: the scripted final `ps` drive left no
new serial lines (guest idle at shell since readkey finished; monitor
answered nothing further). Final state: COMPLETED, 0 panics.
Duration: NOT RECOVERABLE as a measured start→end (no start timestamp was
ever kept — fence OC1B-172 forbids estimating it). Observed window only:
QEMU alive 09:25–11:25 EST per `ps` (elapsed 1:55 at the 11:20 check) and
the launcher's scripted schedule (sleep 90 + 3480 + 3480 + 30 ≈ 7080s ≈
118 min from launch to kill) — both consistent with a ~2h run, neither a
start record.
FINAL verdict for the tracked soak: COMPLETED 2026-11-02 ~11:25 EST,
20 STATUS samples, readkey 200000/200000, 0 panics, 0 loader-refused.

## Field table (OC1B-154)
| run | start time | image sha (as booted) |
| /tmp/soak-serial.txt (§19) | NOT RECOVERABLE | NOT RECOVERABLE |
| /tmp/soak3-serial.txt (tracked) | NOT RECOVERABLE | NOT RECOVERABLE (file rewritten post-launch; current file sha above) |

## Tail file (OC1B-152)
os-build/logs/OC1B-soak-wave2-tail.txt = last 200 lines of
/tmp/soak3-serial.txt, byte-identical at the 11:04 EST re-check
(`tail -n 200` + `cmp` identical). Counts inside the tail file:
`grep -ci panic` = 0, `grep -c "loader refused"` = 0.
Last timestamp: the serial carries NO timestamps (guest has no wall clock
in the log); the only time signal is the file mtime (last write 10:26 EST).
-> last-timestamp field: NOT RECOVERABLE from the log.

## Status line for the coordinator (OC1B-155)
Wave-2 soak verdict: §19 run DIED WITH SESSION (/tmp/soak-serial.txt, 2
samples, 0 panics, duration unknown); tracked soak RUNNING
(/tmp/soak3-serial.txt, 20 samples, 0 panics, ends ~11:25 EST).

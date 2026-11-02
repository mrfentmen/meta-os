# OC1B-159 main-soak verdict — INTERIM (soak RUNNING, attempt 2)

Status at 2026-11-02 ~11:32 EST: the main soak (attempt 2, started 11:27:47
EST per OC1B-soak-main-start.txt) is RUNNING (QEMU PID 37663 alive, monitor
/tmp/oc1b-main2-mon-zvxs3p attached). Planned end ~13:27 EST. The FINAL
verdict lands here (or via OC1B-486 collection) at soak end; this file is
the interim record so the section checkpoint never claims an unended run
as complete.

Duration so far: 11:27:47 EST → 11:32 EST ≈ 4 min, measured from the
attempt-2 start record (OC1B-172: derived from the start record, never
estimated). Attempt 1 (11:07:26 → ~11:22, ≈15 min) is reported separately
in OC1B-soak-main-start.txt and OC1B-soak-anomalies.txt, never merged.

Counts at 11:32 EST (commands on /tmp/oc1b-main-soak-serial.txt):
  lines = 2070+, `grep -c "STATUS tasks="` = 3 (2 launcher batch + 1 manual),
  `grep -ci panic` = 0, `grep -c "loader refused"` = 0.
Anomaly count: 0 (full sweep in OC1B-soak-anomalies.txt; only the expected
crasher-isolation fault line, documented there with context).

Mid-soak drive (11:32 EST, `drive.py --monitor ... status mem ps`
against the RUNNING guest — console answers mid-run):
  status -> tasks 8 ticks 13570 heap_free 255K
  mem -> mem frames_free 126430 frames_total 126509 heap_free 255K heap_total 512K
  ps -> 8 rows: ids 1-6,8 Exited, id 7 Running
(verifies the shell path stays live mid-soak; full lines in the serial.)

RUNNING line for the coordinator (OC1B-160): main soak RUNNING —
serial /tmp/oc1b-main-soak-serial.txt, attempt-2 start 11:27:47 EST,
image sha256 3bbedee5...0c1d09d, planned end ~13:27 EST.

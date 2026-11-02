# §7 STATUS SNIPPET for the coordinator (do NOT edit the status file —
paste/merge these lines) — §7 soak engineer, 2026-11-02 ~11:35 EST,
branch opencode/500-s7

Soak-verdict line (OC1B-155 + OC1B-160): wave-2 §19 DIED WITH SESSION
(/tmp/soak-serial.txt, 2 samples, 0 panics, duration unknown); tracked soak
COMPLETED (/tmp/soak3-serial.txt, 20 samples, 0 panics, ends ~11:25 EST,
`SOAK3_DONE panics=0 runs=20`); main soak RUNNING
(/tmp/oc1b-main-soak-serial.txt, attempt-2 start 11:27:47 EST, image
3bbedee5...0c1d09d, planned end ~13:27 EST).

Task-by-task §7 verdicts (OC1B-151..175):
- OC1B-151 PROVEN — remains found: §19 /tmp/soak-serial.txt (dead 08:47) + tracked /tmp/soak3-serial.txt. Proof: os-build/logs/OC1B-soak-wave2-verdict.md.
- OC1B-152 PROVEN — tail = last 200 lines, byte-identical at 11:04 re-check; counts 0 panic / 0 loader-refused; last-timestamp NOT RECOVERABLE (no timestamps in log). Proofs: os-build/logs/OC1B-soak-wave2-tail.txt + verdict file.
- OC1B-153 PROVEN — plain verdicts: §19 DIED WITH SESSION (duration unknown); tracked soak COMPLETED 11:25. Proof: verdict file.
- OC1B-154 PROVEN — field table: both runs start/image NOT RECOVERABLE (soak3 file sha f13d5dd8...44a3c measured 11:04 is post-launch rebuild, NOT booted bytes). Proof: verdict file.
- OC1B-155 snippet line above (status file untouched by §7 worker — coordinator merges).
- OC1B-156 PROVEN — fresh 2h soak attempt 2 RUNNING on image 3bbedee5...0c1d09d (tree 94010c76), serial /tmp/oc1b-main-soak-serial.txt, monitor attached, planned end ~13:27 EST. Attempt 1 host-killed ~11:22 (SIGTERM pid 36720, guest healthy) documented separately. Proof: os-build/logs/OC1B-soak-main-start.txt.
- OC1B-157 PROVEN — 10/10 drills full pack (hello 1, killed 1, readkey 1, badcall 1, panic 0), 15s each. Proof: os-build/logs/OC1B-soak-main-drills.txt.
- OC1B-158 OPEN — midpoint (~12:27 EST attempt-2 time) NOT reached; interim sample in verdict file labeled interim. Proof (so far): OC1B-soak-main-start.txt midpoint note + OC1B-soak-main-verdict.md.
- OC1B-159 OPEN — INTERIM verdict only (soak RUNNING); final at soak end via OC1B-486. Proof (so far): os-build/logs/OC1B-soak-main-verdict.md.
- OC1B-160 snippet line above (RUNNING line for coordinator merge).
- OC1B-161 NOT RUN — no §5-gated K3 image. Proof: os-build/logs/OC1B-soak-k3.txt.
- OC1B-162 NOT RUN — no §6-gated K4 image; no talker/listener pair. Proof: os-build/logs/OC1B-soak-k4.txt.
- OC1B-163 NOT RUN — no merged graphics tree. Proof: os-build/logs/OC1B-soak-kf.txt.
- OC1B-164 NOT RUN — final tree not assembled. Proof: os-build/logs/OC1B-soak-final-start.txt.
- OC1B-165 NOT RUN — blocked on 164. Proof: os-build/logs/OC1B-soak-final-verdict.md.
- OC1B-166 PROVEN (comparison held/inconclusive as stated). Proof: comparison block in os-build/logs/OC1B-soak-summary.md.
- OC1B-167 PROVEN — 0 anomalies in 4 serials; expected crasher line filed with ±20 context; host SIGTERM incident filed with context. Proof: os-build/logs/OC1B-soak-anomalies.txt.
- OC1B-168 PROVEN — sha table (soak3 booted-sha NOT RECOVERABLE stated). Proof: os-build/logs/OC1B-soak-summary.md.
- OC1B-169 PROVEN — total ≈148 min ≈ 2.5 machine-hours at checkpoint. Proof: total line in os-build/logs/OC1B-soak-summary.md.
- OC1B-170 PROVEN — monitor-attached boot, screendump answers at end (VGA text framebuffer: boot banner visible). Proof: os-build/captures/oc1b-soak-end.png.
- OC1B-171 NOT RUN — blocked on 164. Proof: os-build/logs/OC1B-soak-final-drive.txt.
- OC1B-172 PROVEN — duration-derivation note. Proof: os-build/logs/OC1B-soak-summary.md.
- OC1B-173 PROVEN — NOT RUN lines for 161-165, 171. Proof: os-build/logs/OC1B-soak-summary.md.
- OC1B-174 PROVEN — one-paragraph verdict. Proof: os-build/logs/OC1B-soak-summary.md.
- OC1B-175 commit+push on opencode/500-s7 (sha below; coordinator merges to opencode/500 at checkpoint).

Fences kept: no kernel/src edits (none — `git status` shows logs/captures only);
no face/web work; Imperium untouched; Mac key never needed (no model calls made);
no padded counts (every number names its command); status file untouched.

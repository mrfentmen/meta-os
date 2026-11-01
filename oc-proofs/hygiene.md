# Repo hygiene (NC-147): NC-141..NC-146 results

- NC-141 size audit (top tracked files): wdg033 MP3 2.6 MB, the .glb
  2.2 MB (task text says 63 MB — actually 2,268,304 bytes on disk),
  readme-30s clip 1.8 MB, custos clip 1.7 MB, custos-20s 1.4 MB.
  The .glb is referenced only by OPENCODE_TASKS_ROUND3.md itself (the
  task text); no code, page, or test references it (read-only grep).
- NC-142 LFS eval (10 MB rule): NO tracked file exceeds 10 MB (largest
  is 2.6 MB). Nothing would move; LFS buys nothing today.
- NC-143 duplicates over 1 MB: exactly one set — three.min.js r152
  (633,338 bytes) vendored 3x (labs/molecules, labs/music3d, design),
  1.9 MB total. Kept deliberately: each viewer is self-contained and
  works from its own folder with no cross-links. Noted, not deduplicated.
- NC-144 labs weight: labs/ 4.2 MB, oc-proofs/ 12 MB, hortus-rung3/
  64 KB. Five heaviest own artifacts: readme-30s clip 1.8 MB, custos
  clip 1.7 MB, custos-20s 1.4 MB, three.min.js x2 (1.3 MB), phone-15s
  0.6 MB.
- NC-145 footage weight: all film clips on the branch total 9.4 MB
  (oc-proofs/footage/). Stated plainly for the hand move.
- NC-146: no .DS_Store, no *~ or *.bak anywhere outside .git. Clean.

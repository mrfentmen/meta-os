# OC1B-480 — honest UNPROVEN list (built but never gated on the Mac, in this lane's scope)

- Kernel-clause claims (boots / ring 3 / three programs / fault isolation /
  live shell / clean-checkout reproduction / log backing): this lane's
  closeout gate.sh is GREEN on 94010c76 (OC1B-closeout-gate.log), but the
  SUBMISSION's standing proof is the §1 baseline + §8 re-proof lineage on
  Pax's assembled tree — UNPROVEN as a submission claim until those lanes'
  waves land. This lane's gate is evidence, not the submission's gate.
- §9/§10 live-model proofs: no live model call ran in this lane (0 spend,
  no key use) — UNPROVEN here by design; owners: §9/§10 lanes.
- §7 soaks: no soak owned or run in this lane. Observed, not owned:
  /tmp/soak3-serial.txt (wave-2 remains) holds 2124 lines, 0 panics, last
  state ticks 365178 at 10:26 EST; no live writer found at 11:11 EST check.
  Final verdict belongs to the §7 owner (collected into OC1B-soak-summary
  only as an observation — this lane does not append to §7's file).
- §11 film final-cut claims: film measured (180.000s) but cut/fallback/
  honesty-pass claims are §11's to gate — UNPROVEN here.
- §18 README numbers: not re-derived in this lane (one observation recorded
  for §18's owner: Node row stale by exactly R11-282).
- R11-282 (boot-log index): failing on this branch AND on origin/main tip —
  UNPROVEN until the index names the new *.txt logs (docs edit, not this lane).

Failing tests stay named as failing with logs (OC1B-401..414 pack) — never
marked passing without a green run.

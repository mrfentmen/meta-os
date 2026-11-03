# Cycle 003 — record (model-directed: materials rule of mixtures)

- Question: can a model-directed plan (Muse Spark director) correctly
  set up the textbook rule-of-mixtures density check, and does the
  deterministic runner reproduce the hand-computed value?
- Target: rule-of-mixtures density rho = sum(f_i * rho_i) for a
  two-phase mixture Al/Cu at fractions [0.6, 0.4] with handbook
  densities [2.70, 8.96] g/cm^3, computed via
  os/worlds/science-lab/compute.py run_materials.
- Source: standard handbook elemental densities (Al 2.70 g/cm^3,
  Cu 8.96 g/cm^3); rule of mixtures (volume-fraction idealization).
- Director plan: Muse Spark was asked (model/director_prompt.txt) for
  an approach; its reply (model/director_reply.txt, receipt
  model/director_receipt.json) is adopted/rejected line by line below.
  - Adopt: pre-register the plan hash BEFORE any result.
  - Adopt: run compute.run_materials once, deterministically, seed
    recorded.
  - Adopt: score with compute.compare_to_prereg against the
    pre-registered band.
  - Adopt: mandatory critic, answered with evidence.
  - Adopt: independent clean-directory re-run must agree.
  - Reject: nothing; the deterministic fallback template
    (model_calls.offline_director_plan) adds no step beyond these.
  - Net effect of the director call: listed in model/impact.md.
- Expected value (pre-registered BEFORE this run, hand arithmetic
  0.6*2.70 + 0.4*8.96 = 1.62 + 3.584): density 5.204 g/cm^3,
  tolerance 0.001, i.e. MATCH iff observed density in [5.203, 5.205].
- Headline metric: density (g/cm^3).
- Method: run.py calls compute.run_materials once, deterministically,
  then compute.compare_to_prereg.
- Seed: 500003 (recorded; closed-form computation, no sampling).
- Falsifier: the claim is killed if the observed density falls outside
  [5.203, 5.205] g/cm^3, or if run_materials raises, or if the frozen
  inputs hash differs from inputs.sha256.
- Wonder reading: model/wonder_reply.txt reads the output figure
  (model/figure_data.json); agreement check in model/wonder_check.md.
- SAM segmentation: model/sam_record.json (one labs molecule image;
  box coordinates + overlay yes/no; a no-box outcome is recorded
  as-is, never invented).
- Critic: second model (Wonder if Spark directed, Spark if Wonder
  directed; if any call was OFFLINE the critic call still goes to the
  other model once). Critic text + model name in critic.md; response
  section in the same file.
- Ladder level earned: Level 3 (independently reproduced): MATCH on the pre-registered band plus a bit-for-bit clean-directory re-run; model direction changed nothing (all four calls OFFLINE, see model/impact.md).
- Ledger entry id: 5b681bd0059fae24460e7252c9f5a9f540b4614e10ba0ff369d922af743d472c (labs/cycles/ledger.jsonl).
- Model spend for this cycle: $0.005358 total (4 calls attempted, 0 live replies, 4 OFFLINE fallbacks, no retries; Spark usage priced by the lab estimator, Wonder/SAM usage recorded but unpriced — see model/spend.json and model/helper_receipts.jsonl).

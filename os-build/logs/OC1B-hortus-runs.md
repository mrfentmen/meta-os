# OC1B Hortus runs (OC1B-339/340)

Tree: `94010c76ee095fa6c6bcfa4405cd56a9695f32d3`. Date (UTC): 2026-11-02.

## Engine run (hortus integration path)

Command: `python3 -m hortus.run_demo os-build/logs/oc1b-hortus-run.jsonl`
(run from `os/worlds/science-lab/`; records path override so the repo's
`hortus/records/` is untouched). Record: `os-build/logs/oc1b-hortus-run.jsonl`
(27,952 lines: 1 run_start, 13,848 births, 301 generation summaries,
13,800 deaths, 1 verdict, 1 run_end).

- **OC1B-340 inputs**: generations 300, population 48, seed 20261101,
  toy-fin model v1 (train-nominal env), gene bounds
  [[2.0,40.0],[4.0,60.0],[0.4,4.0],[1.0,8.0]].
- **OC1B-340 outputs**: first best 74.9996 W-equivalent, final best
  **138.3907**, final mean **119.0601**, champion organism 9086 genome
  (40.0, 60.0, 0.745195, 1.49394); held-out verifier **PASSED
  (verified-candidate)**: forced-air 324.12W vs 52.19W ref, still-air-hot
  119.70W vs 15.74W, other-alloy 152.80W vs 23.03W — all beat, all feasible.
  Evidence cap: ladder level 2 (candidate only, not a discovery claim).
- Wall clock ~1 s.

## Breeding run (lab integration path: propose → run → select → lineage)

Driver: real `breeding.propose_variants` / `run_variant` / `select_survivor` /
`build_lineage` / `verify_lineage` / `preserve_dead_ends` against a temp
ledger; record: `os-build/logs/oc1b-hortus-breeding.json`.
Plan P-OC1B-001 (research question + archived Delaney chem inputs, seed 801).

- **OC1B-340 inputs**: 3 variants proposed (V001–V003, 0 rejected, hortus
  engine available v0.1.0 toy-fin-v1, cap L2); pre-registration filed to the
  temp ledger BEFORE results (entry `2cf536dea14e`); department runner
  `run_chem` on the archived CSV.
- **OC1B-340 outputs**: all three variants drew the same first-10-rows slice,
  so observed values are identical: V001/V002/V003 = **-3.989** each (honest
  note: the run proves the machinery — prereg gating, selection, lineage —
  not variant diversity). Survivor: **V001** (threshold -4.5, direction >=,
  all match, extreme-wins tie). Lineage hash
  `b92c69bdafcbf87903d20b98cf17ae58210b81812ee17b6267d983211e8c6155`;
  `verify_lineage`: **(True, ok: 3 variant links verify, survivor 'V001')**.
- Candidates 3, survivors 1, dead ends 2 (filed as negative results to the
  temp-ledger flow; the accidental real-repo filing from the first probe
  attempt was reverted — see OC1B-science-rehearsal.md defect block).

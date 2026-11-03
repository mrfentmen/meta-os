# Cycle 006 — score

- Verdict: MATCH.
- Differing fields: none. All scored fields inside their bands:
  rmse observed=1.0994 expected=1.099 tolerance=0.05 band=[1.049, 1.149].
- Metric line: RMSE observed=1.0994 expected=1.099 tolerance=0.05 -> MATCH.
- Context (reported, not pass/fail): R2 observed=0.7248 (repo note 0.725),
  MAE observed=0.8439 (repo note 0.844), n=1128, skipped=0.
- Skipped rows: 0 (falsifier condition on silent skips: satisfied, none).
- Input freeze: inputs/delaney-processed.csv sha256
  8c06a76f0c6487d29ab0f903e6a7a7139f189ab3c1178f59c8be8964602f189
  matches the archived sha in gate/delaney/SOURCES.md.
- Literature pass (live, backend=MCP-GATEWAY, 2/2 ok, $0.00): pinned=YES.
  Pinned identifiers: OpenAlex https://openalex.org/W2076498053, DOI
  10.1021/ci034243x, title ESOL, year 2004, venue J. Chem. Inf. Comput.
  Sci., author John S. Delaney. Remote tools openalex__search_works +
  openalex__get_work (text payloads, kept verbatim in raw/gateway/).
- Figure: figure.png (measured-vs-predicted scatter, red diagonal),
  generating command (from labs/cycles/cycle-006):
  python3 run.py --figure figure.png --from raw/result.json
  Note: figure.png sha256 7e8f2a501919d9f38de68deabaa04fc76d761c4b461
  ebcfeb81948fe585187cf is byte-identical to cycle-001's figure
  (same frozen inputs, same from-scratch implementation).
- Comparison block (independent verification):
  raw/result.json sha256 =
  650a835a3bdeeb3dfb6277b0b9dea0029004f79d7f21765960ecc41f376e77a9
  verify/rerun_result.json sha256 =
  650a835a3bdeeb3dfb6277b0b9dea0029004f79d7f21765960ecc41f376e77a9
  result: BIT-FOR-BIT AGREE (clean-directory re-run from frozen inputs;
  the re-run issued its own 2 live gateway calls to /tmp, recorded
  outside this pack).

# Gap records — R13-008 dashboard

## R13-008-G1 — no permission boundary

- **Claim:** the dashboard has a boundary controlling who writes or reads samples.
- **Reality:** no caller identity, capability check, callmatrix check, or refusal code is present.
  `df_put` and `df_get` are library functions with no auth parameter.
- **Evidence:** the grep in `CONTRACT_R13.md` returns no matches.
- **Impact:** any code linked into the process can forge or read a metric. This may be acceptable
  for a face library, but it is not a permission boundary and must not be represented as one.
- **Owner:** dashboard face contract.

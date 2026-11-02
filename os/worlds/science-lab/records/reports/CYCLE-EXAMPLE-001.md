# Cycle report — CYCLE-EXAMPLE-001

Question: Can the published Delaney (2004) ESOL aqueous-solubility model be reproduced from the archived compound set?
Phase: wetlab
Gate state: human-gated (parked at wetlab)
Ledger: 10 entries for this cycle; chain VERIFIED (ok: 17 entries verified).

## Phase walk (phases 1-7 sourced; step 8 silent; 9/10 human-gated)

| # | phase | status | ledger entry | reason |
|---|-------|--------|--------------|--------|
| 1 | problem | done | — | start phase; departed by a later transition |
| 2 | literature | done | 6479f42110d7 | brief RI-EXAMPLE-001 filed (3 pinned P1-P3, 1 dropped D1, 0 contested); paper figure stays TO_BE_READ_AT_RUN |
| 3 | hypotheses | done | c19226eda7c8 | hypotheses RH1,RH2,RH3 filed with falsifiers (hash 947f7a4f942d...) |
| 4 | cheap-computations | done | 1671cc6dbd46 | computation filed as PREP-RUN observation (R2 0.725, RMSE 1.099, n=1128); threshold R2>=0.5 pre-registered at 2849270d226c... |
| 5 | critic | done | 48357bc41c6e | scientific-critic attack filed (2ae02be31843...): descriptor-mismatch and leakage confounds recorded; proceed as unverified observation only |
| 6 | verification | done | f9e020c4ad92 | verification indeterminate: observation filed, independent re-run pending; claim capped at level 2 |
| 7 | sealing | done | 91025c3b114e | sealed phases 1-7 bundle at recorded levels (reasoning 1, computation 2 unverified); level 3+ explicitly not earned |

Source gap: step 8 (`step-8-unimplemented`) is silent in the source text — no step-8 work is claimed anywhere in this report.
Human gate: wetlab/publication are permanently human-gated; this cycle parks there and resumes only on an explicit human decision record — never auto-passed.

## Claims (displayed at recorded level, never higher)

- Level 1 (Evidence supported): Delaney (2004) ESOL is the first reproduction target; the archived 1,128-compound set is hash-verified and the published equation is re-extracted from the paper text at gate run time. [record be1f7a0ea918]
- Level 2 (Computationally tested): Published Delaney equation scored on the archived set at R2 0.725 / RMSE 1.099 (PREP-RUN observation, RDKit descriptors). [record ef287634a407]

Export guard: 2 levelled claims checked with ladder.assert_export_allowed — all display at their recorded level.

## Honesty notes

- One transition = one ledger entry; history holds 6 entry hashes, all present in the ledger.
- Parked at a human gate: no auto-pass occurred; a resumption requires a signed human decision record.
- No independent-verifier reproduced record is filed: nothing here is above ladder level 2, and levels 4-6 are unreachable by this system alone.
- Pre-registered thresholds (if any) precede results in ledger order; the pre-registration hash is the authority, not any later reading.


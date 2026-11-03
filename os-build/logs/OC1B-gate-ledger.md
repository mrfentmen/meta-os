# OC1B-476 — gate ledger (this lane's runs + named pointers for the rest)

Lane: opencode/500-s17 @ 94010c76. This lane ran gates it owns; gates owned
by other lanes are listed with their owner, never with an invented result.

| Gate | Date (UTC) | Tree sha | Result | Proof |
|---|---|---|---|---|
| §17 node baseline (OC1B-401) | 2026-11-02 | 94010c76 | 2071 / 2015 / 56 | OC1B-native-baseline.txt |
| §17 groups G1..G7 + SUPP (OC1B-407..413) | 2026-11-02 | 94010c76 | sums to 56 (see OC1B-414) | OC1B-native-g1..g7.txt, OC1B-native-supp.txt |
| §20 closeout gate.sh (OC1B-488) | 2026-11-02 | 94010c76 | GATE GREEN (K1,K4,K6x3,readkey,shell,status = 8 ok) | OC1B-closeout-gate.log |
| §20 closeout node (OC1B-489) | 2026-11-02 | 94010c76 | 2071 / 2015 / 56, identical to baseline | OC1B-closeout-node.txt |
| §20 closeout queue (OC1B-490) | 2026-11-02 | 94010c76 | 296 tests OK, 4.2s | OC1B-closeout-queue.txt |
| §1 baseline gate | — | — | NOT IN THIS LANE | owner: §1 lane |
| KF-01..KF-20 gates (§2/§3/§4) | — | — | NOT IN THIS LANE (no Rowan KF branch gated here) | owner: KF lanes |
| K3 gate pack (§5) | — | — | NOT IN THIS LANE | owner: §5 lane |
| K4 gate pack (§6) | — | — | NOT IN THIS LANE | owner: §6 lane |
| §8 re-proof waves 1..5 | — | — | NOT IN THIS LANE (no wave triggered in this lane) | owner: §8 lane |
| §12 carrier checks | — | — | NOT IN THIS LANE | owner: §12 lane |
| §16 Goose gate-2 | — | — | NOT IN THIS LANE | owner: §16 lane |

Last kernel word of this lane: GATE GREEN on 94010c76 (OC1B-closeout-gate.log).

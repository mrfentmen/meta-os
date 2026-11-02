# Gap records — R13-004 bootlog

## R13-004-G1 — two failures collapse to one boolean

- **Claim:** the boot log reports a failed record in a way the caller can act on.
- **Reality:** `record()` returns `false` for both a cap overflow (`need > room_left`) and a
  negative serial write. No error code, no length, no cause is returned; `stage()` propagates the
  same boolean.
- **Evidence:** `services/bootlog/bootlog.goose:59-70`; the grep in `CONTRACT_R13.md`.
- **Impact:** a caller cannot tell a too-long message from a dead UART, so it cannot choose between
  shortening the record and escalating the port failure.
- **Owner:** bootlog record contract; kernel serial return convention (A2).

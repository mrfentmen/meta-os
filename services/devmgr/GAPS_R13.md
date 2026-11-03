# Gap records — R13-010 devmgr

## R13-010-G1 — no devmgr source or retry policy

- **Claim:** the device manager retries failed operations.
- **Reality:** the directory contains only a README that says it is a retired name. No `.goose`
  source, entry point, or retry loop exists. The implementation is `services/devices`.
- **Evidence:** `find services/devmgr` and the failed `*.goose` glob in `CONTRACT_R13.md`.
- **Impact:** there is no retry policy to test. The correct action is this gap record; the device
  table's state transitions are covered under `devices`.
- **Owner:** manifest owner; the devices service.

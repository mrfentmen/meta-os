# Gap records — R13-002 audit

## R13-002-G1 — no shutdown or flush contract

- **Claim:** the audit service can be stopped and its records finalised.
- **Reality:** there is no close/stop/shutdown/flush function and no `svc_entry`. The static buffer
  is only exposed through `audit_used()` / `audit_bytes()`; the caller must copy it.
- **Evidence:** the grep in `CONTRACT_R13.md` matches only comments; no function declarations.
- **Impact:** a process exit can lose unflushed records with no error and no receipt.
- **Owner:** audit storage binding; B-L1-41/42.

## R13-002-G2 — startup dependency claim has no entry

- **Claim:** README "Failure behaviour": "Missing dependency at start-up: refuses to start (non-zero
  exit)."
- **Reality:** the unit has no entry point and no startup function that checks a dependency.
- **Evidence:** no `svc_entry` / `service_main` in `services/audit`.
- **Impact:** the claim is boilerplate copied from the service template, not a code path.
- **Owner:** Layer 4 entry contract (Q-B-L1-4).

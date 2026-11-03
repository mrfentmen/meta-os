# Gap records — R13-001 agenthost

## R13-001-G1 — startup entry absent

- **Claim:** a startup contract can be audited for this service.
- **Reality:** `services/agenthost` has no `svc_entry` or `service_main`. It is a library body
  whose caller owns startup.
- **Evidence:** `grep -nE 'svc_entry|service_main' services/agenthost/*.goose` returns no matches.
- **Impact:** there is no process-level startup path to test; the README already records the
  deviation. The contract note states what exists instead of claiming a bootstrap.
- **Owner:** Layer 4 service entry contract (Q-B-L1-4).

## R13-001-G2 — supervisor dependency is claimed, not checked

- **Claim:** README "Failure behaviour": "Refuses to start without the supervisor (no table owner)."
- **Reality:** `ah_init()` only clears slots and sets `ah_inited`; it has no parameter, no
  supervisor handle, and no failure return. `supervisor` appears only in comments.
- **Evidence:** `services/agenthost/agenthost.goose:79-88`; the grep in `CONTRACT_R13.md`.
- **Impact:** a caller can initialise the table with no supervisor present and receive no refusal.
  This is an unimplemented promise, not a behaviour.
- **Owner:** agenthost startup binding; K6 spawn/supervisor integration.

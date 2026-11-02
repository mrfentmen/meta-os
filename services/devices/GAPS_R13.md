# Gap records — R13-009 devices

## R13-009-G1 — no timeout contract

- **Claim:** device probes or hot-plug delivery have timeout behaviour.
- **Reality:** no deadline, wait, retry, or timeout function exists. `at_ms` in hot-plug is an event
  timestamp supplied by the caller. The timer device's `tick_hz == 0` check is a state transition.
- **Evidence:** the grep in `CONTRACT_R13.md`; `services/devices/hotplug.goose:47,138`.
- **Impact:** a caller cannot ask the device table to bound a probe or hot-plug wait; it must impose
  its own timeout. The comment about every timeout becoming infinite describes a kernel fact, not a
  service contract.
- **Owner:** devices service; K3 timer integration.

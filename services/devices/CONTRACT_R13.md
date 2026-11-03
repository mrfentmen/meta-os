# Contract note — R13-009, devices timeout behaviour

Status: **AUDITED — 1 gap filed**.
Facet: how device probes and hot-plug events time out.

## Evidence

Command:

```sh
grep -nEi 'timeout|deadline|clock|ms|wait|retry|dead|stale' services/devices/*.goose
```

Output:

```text
devices.goose:156:    // Timer: tick_hz 0 means no timer, and every timeout in the layer becomes
devices.goose:223:// ignores the code gets zeros rather than the stale numbers of a faulted device.
hotplug.goose:47:    at_ms: i64,
hotplug.goose:138:fn hp_raise(h: HotPlug&, kind: i64, dev_slot: i64, dev_kind: i64, at_ms: i64) -> i64, i64 {
```

No deadline, wait, retry, or timeout function is declared. `at_ms` is an event timestamp, not a
deadline.

## Corrected contract

Device state is a table transition, not a timed probe. There is no timeout on `dev_ready`,
`dev_detail`, or hot-plug delivery. The timer device is marked `DS_FAULT` when
`BootInfo.time.tick_hz` is zero, because callers' timeouts would otherwise never expire; the table
itself does not run a timer. Hot-plug events carry the caller-supplied `at_ms` for ordering.

## Mismatches

- **R13-009-G1** — no timeout behaviour exists to audit; the comment is a rationale, not a
  contract. See `GAPS_R13.md`.

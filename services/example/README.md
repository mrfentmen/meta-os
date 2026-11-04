# example — `tickerd`, the template service (B-L1-94)

The pattern a new service copies: one export (`svc_entry`, C ABI), BootInfo
validated first, config through `common/cfg` with named defaults, registration
with the supervisor by handle, fixed buffers cleared explicitly, records built
whole and written once, error codes from `common/err`, heartbeat after work, a
status function that writes into the caller's buffer.

**Status: COMPILED, not RUN.** (Lane B R5, 2026-11-04 — log: services/example/BUILD_LOG.txt; svc_entry takes BootInfo&, so no host process can honestly run it.) The checklist at the bottom of
`example.goose` has the last two lines unticked for exactly that reason.

## What it does

Reads `/etc/tickerd.conf` (`[tickerd]` / `interval_ms` / `enabled`), registers
itself, beats every interval, writes one `tick N at Tms crc=…` record per tick
into a 4-record ring, and stops on request.

## What the template deliberately does not do

No allocation, no threads, no shared mutable state, no blocking call without a
budget, no `exit()` mid-run. Those absences are the template's content: services
that break them are the ones the supervisor cannot reason about.

The same checklist lives in `os-build/layer1/GUIDE.md` (B-L1-135).

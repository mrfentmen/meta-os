# Driver conformance checklist (OS-053)

Any future driver must pass every item below. The reference run is
`tests/test_os_driver_contract.py`, which runs this checklist
against `stub_driver.py`. A driver that fails one item does not
ship, and the failure is recorded, not waived.

- C1. Unsigned spec rejected. `start()` with a spec missing `sig`,
  or with an empty `sig`, raises and spawns no process.
- C2. Unparseable accept rejected. `start()` with accept text that
  `mos/acceptance.parse_accept` rejects raises and spawns no
  process.
- C3. Owned files required. `start()` with an empty or missing
  `files` list raises and spawns no process.
- C4. Heartbeat shape. `heartbeat()` while running returns a record
  whose `line` is exactly `PROGRESS:<job_id> <note>`, with matching
  `job_id`, `note`, and a numeric `ts`. `heartbeat()` before
  `start()` raises.
- C5. Stop kills. `stop()` on a running child (for example one
  sleeping) terminates it, and the process is gone afterwards.
- C6. Changed files reported. After a run that creates a file in
  the workdir, `artifacts()` lists that file in `changed_files`.
  The driver log file itself is never listed.
- C7. Acceptance from disk. `artifacts()` carries an `acceptance`
  record from `mos/acceptance.verify` against the workdir: `ok`
  True when the accept lines hold, False when they do not. The
  verdict comes from the files on disk, never from agent claims.
- C8. Unowned changes visible. A run that changes a file outside
  the spec's owned `files` list reports it in `unowned_files`.
- C9. Stop after finish is safe. Calling `stop()` after the process
  already exited, then `artifacts()` again, returns the same
  artifacts record.
- C10. No bus traffic. The driver imports no bus, Redis, or posting
  module, and `start()` performs no network or bus write. Heartbeat
  records go only to the caller supplied sink.

How to run the checklist against a new driver: implement the four
operations with the names and record shapes in `CONTRACT.md`, then
adapt the test file's driver construction to the new driver and run
the suite. Every item above must pass before the driver is listed
in `CONTRACT.md` as conformant.

# OC2B-181/182 — Lobster failures triage

## identity-hash-comments (failures/)
Case file fails EXACTLY as its `.err` museum record says:
`error: illegal token: '#'` + `error: illegal start of expression`
(first draft used `#` comments; Lobster only takes `//`).
Byte-identical to `failures/identity-hash-comments.err`.
Verdict: EXPECTED-FAIL (museum piece, OS-177). Not a defect.

## bus delivery gap (NEW row from this session)
Send prints success, zero bytes land, recv drains nothing (see
OC2B-lobster-bus.txt). Either the host never implements the
channel-dir write or it lands outside any observable tree.
Verdict: DEFECT-or-LIMITATION, owner OC2 to isolate (host
`write_file` scope vs script path bug), BLOCKED on host-source
read. Shipped glue (OC2B-183) EXCLUDES bus-dependent paths until
this row closes — only hello/agent-call/memory/budget/service
paths are proven.

# Contract note — R13-002, audit shutdown contract

Status: **AUDITED — 2 gaps filed**.
Facet: how the append-only audit buffer is finalised, flushed, and stopped.

## Evidence

Command:

```sh
grep -nE 'fn .*(close|stop|shutdown|flush)|shutdown|close|stop|flush|svc_entry|service_main' services/audit/*.goose
```

Output:

```text
audit.goose:30:// It cannot stop someone who can rewrite the whole log from the first record onward. That
audit.goose:215:// where to look, while a bare false says the log is untrustworthy and stops.
audit.goose:300:// Bytes written so far, and a read-only view of them, so the storage binding can flush a
```

No function named close, stop, shutdown, or flush is declared. No `svc_entry` or
`service_main` exists.

## Corrected contract

The audit unit owns a 4 KiB static record buffer. It exposes `audit_bytes()` as a read-only view
and `audit_used()` as the length; the caller must copy or flush those bytes. There is no shutdown
hook, no final seal, and no flush-on-exit. A process that stops without copying the buffer loses
the records still in it. The append-only chain guarantees ordering only for bytes that reached the
caller.

## Mismatches

- **R13-002-G1** — no shutdown/finalisation contract exists for the buffer; the README's
  "append-only" claim does not cover process exit. See `GAPS_R13.md`.
- **R13-002-G2** — the README's "missing dependency at start-up refuses" line has no startable
  entry to enforce it; this is the same boilerplate as the other library units and is filed rather
  than counted as implemented.

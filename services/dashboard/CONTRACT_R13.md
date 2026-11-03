# Contract note — R13-008, dashboard permission boundary

Status: **AUDITED — 1 gap filed**.
Facet: who may write or read dashboard samples.

## Evidence

Command:

```sh
grep -nEi 'permission|callmatrix|cm_check|allow|deny|E_DENIED|cap|grant|auth' services/dashboard/*.goose
```

Output: no matches.

## Corrected contract

The dashboard has no caller identity, capability check, or permission boundary. `df_put` accepts
a sample from any caller that can link the library; `df_get` returns it to any caller. The only
boundary is the caller's own process. This is a sample table, not a protected service.

## Mismatches

- **R13-008-G1** — no permission boundary exists. See `GAPS_R13.md`.

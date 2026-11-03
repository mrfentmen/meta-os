# Contract note — R13-024, notify deprecation markers

Status: **AUDITED — 0 gaps**.
Facet: whether `notify` carries deprecated symbols, legacy aliases or removal markers that a caller
must avoid.

## Evidence

Commands:

```sh
grep -nEi 'deprecat|legacy|old|remove|sunset|todo|fixme|compat' services/notify/*.goose
grep -nE '^fn nt_|^struct |^let NT_' services/notify/notify.goose
```

Relevant output: the first grep returns no matches. The public surface is:

```text
nt_init, nt_ensure, nt_sev_ok, nt_sev_name, nt_find, nt_printable,
nt_text_eq, nt_source_eq, nt_dup, nt_post, nt_dismiss, nt_count,
nt_id_at, nt_sev_at, nt_when_at, nt_text_at, nt_source_at, nt_unread,
nt_worst, nt_refusal_total, nt_duplicate_total, nt_dismissal_total,
nt_dismissal_at, nt_dismissal_sev_at, nt_dismissal_when_at, nt_fetch
```

## Corrected contract

There are no deprecation markers, no legacy aliases and no TODO/FIXME removal notes. Every
`nt_*` function in the source is current and has a single name. The surface is additive: `nt_fetch`
is the text view, the `_at` getters are the structured view, and the three counters are the audit
view. No caller has to choose between an old and a new spelling.

## Mismatches

None. The absence is the finding: there is no deprecation debt to schedule, and no marker that
falsely implies one.

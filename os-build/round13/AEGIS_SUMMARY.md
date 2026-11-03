# Round 13 — Aegis summary (Sections E–J)

| section | state | counts | evidence |
|---|---|---|---|
| Aegis OSV sweeps | **COMPLETE** | 25 / 25; 10 real manifests, 15 missing, 107 refs, **0 findings**, control passed | `os-build/round13/aegis/SECTION_E.md` |
| Aegis KEV cross-check | **COMPLETE** | 25 / 25; 0 findings to check, feed 2026.10.30 (1,766 entries), control passed | `os-build/round13/aegis/SECTION_F.md` |
| secret hygiene counts | **COMPLETE** | 25 / 25; 241 matches (240 env mentions, **1 bearer review item**), self-check passed | `os-build/round13/aegis/SECTION_G.md` |
| surface/unicode | **COMPLETE** | 25 / 25; 16 scanned (1.9 M chars), 9 missing artifacts, **0 findings** | `os-build/round13/aegis/SECTION_H.md` |
| Aegis OSINT | **COMPLETE** | 25 / 25; 15 passes run, 9 not implementable, 1 unavailable; **2 findings** (NXDOMAIN, soft 404) | `os-build/round13/aegis/SECTION_I.md` |
| Aegis OPSEC | **COMPLETE** | 25 / 25; 20 decided, 3 not inspectable, 2 n/a; **4 failures, 6 findings** | `os-build/round13/aegis/SECTION_J.md` |

- Routes: E and F used the direct `api.osv.dev` and CISA KEV feed because `osv-mcp` and `cisa-kev-mcp` are not installed on this host. The route is stated in every record; a reader who does not accept the standing exception should read those 50 rows as BLOCKED.
- G is counts-only and self-checked: the record holds no value-shaped string.
- J's four failures are the ones that need a human: 1,422 of 1,896 commits authored from a consumer mail domain, a branch named `buffy/pax-12h-plan`, a ledger with no dedupe key, and no closure field.
- R13-152 (one bearer-shaped token, history only, no longer in the tree) stays open pending human review.

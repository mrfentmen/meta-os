# Aegis OSINT v1 — public footprint, counts only

Run `osint-2026-11-02T11-12-02-401Z`, 2026-11-02T11:12:02.402Z. Domains named by the boss: `meta-os.pages.dev`, `muse-relay-live.pages.dev`, `clipraiders.com`, `watchpeoplefight.com`.

Sources: **crt.sh** certificate transparency (public log) and **DNS** (public by construction). No host was contacted, no port was probed, and nothing outside these four names was resolved.

## Per domain

| domain | resolves | CT certs | distinct names | issuers | expired | A | AAAA | MX | NS | TXT | CAA | SPF | DMARC |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `meta-os.pages.dev` | yes | 0 | 0 | 0 | 0 | 2 | 2 | 0 | 2 | 0 | 0 | no | no |
| `muse-relay-live.pages.dev` | yes | 2 | 2 | 1 | 0 | 2 | 2 | 0 | 2 | 0 | 0 | no | no |
| `clipraiders.com` | **no** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | no | no |
| `watchpeoplefight.com` | yes | 8 | 5 | 2 | 0 | 2 | 2 | 0 | 2 | 1 | 0 | no | no |

## Notes on this footprint

- `meta-os.pages.dev` is under a shared parent, so SPF and DMARC are not the site owner's to publish and are not filed as findings.
- `muse-relay-live.pages.dev` is under a shared parent, so SPF and DMARC are not the site owner's to publish and are not filed as findings.
- `clipraiders.com` got no NS answer: that row is absence, not a clean record.


**No name, address, or record value is printed.** The counts are the finding; the names behind them are one query away for anyone who owns the domain, and publishing them here would do the enumerator's work.

## Findings

- **info** — clipraiders.com does not resolve in DNS
- **medium** — no DMARC record published for watchpeoplefight.com
- **low** — no SPF record published for watchpeoplefight.com

## What this does not claim

- CT counts are what crt.sh returned at this time; the log is append-only but the index is not instant.
- A "distinct name" is a name on a certificate, not a name that resolves, and not a host that is up.
- No search-index, store-listing, or repository-metadata review is in this run.
- No mail authentication was tested by sending anything; SPF/DMARC presence is a DNS fact only.

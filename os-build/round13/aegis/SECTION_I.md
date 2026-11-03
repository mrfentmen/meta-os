# Section I — OSINT passes over our own footprint (R13-201..225)

Run: `python3 os-build/layer1/osint_passes.py`. Records:
`os-build/round13/aegis/OSINT_PASSES.json`, `os-build/round13/aegis/osint_passes.txt`.

**25 / 25 addressed: 15 passes executed, 9 angles not implemented under the standing bounds,
1 source unavailable. Two real findings.** Counts only — no subdomain, address, issuer name,
header value or TXT content is in the record.

## Two bugs the first run had, fixed before these rows were written

1. Angle text was matched case-sensitively, so `DNS record types` missed its own map entry.
2. The domain regex took the first `on <word>` in lines that read `on our pages on
   watchpeoplefight.com`, producing `domain=our` and a DNS error.

Both changed which rows are scans, so they are named rather than quietly corrected. The tool
parses the 25 pairs **out of the task list** instead of restating them, and refuses to run if
it does not find exactly 25.

## Findings

| finding | evidence | size |
|---|---|---|
| `clipraiders.com` does not resolve | `dns.google` ANY query returned `rcode 3` (NXDOMAIN), 0 answers; crt.sh has 0 certificates; Wayback has 0 snapshots | quiet note — a name in the boss's own list that does not exist is worth knowing, and a name that cannot resolve cannot receive mail, so no mail findings are filed for it |
| `meta-os.pages.dev` serves a soft 404 | `GET /aegis-probe-does-not-exist` returned **HTTP 200** with 9,894 bytes — the full SPA shell — instead of a 404 | quiet note — a missing page is indistinguishable from a real one to a crawler or a link checker |

Both are recorded as observations, not alarm items. Neither is auto-fixed; Aegis files and a
human decides.

## Passes executed

| task | angle | domain | result |
|---|---|---|---|
| R13-201 | CT issuers | meta-os.pages.dev | 0 certificates, 0 issuers, 0 names |
| R13-202 | CT expiry windows | muse-relay-live.pages.dev | 2 certificates, 0 expired |
| R13-203 | DNS record types | clipraiders.com | rcode 3 (NXDOMAIN), 0 answers |
| R13-204 | DNS unexpected records | watchpeoplefight.com | rcode 0, 1 answer, 1 record type |
| R13-205 | subdomain names in public CT | meta-os.pages.dev | crt.sh 404 (no rows) |
| R13-206 | response-header names | muse-relay-live.pages.dev | HTTP 200, 13 headers, 2 security headers |
| R13-208 | store page public text | watchpeoplefight.com | HTTP 200, 41,621 bytes, 889 words, 71 links |
| R13-209 | listing page public text | meta-os.pages.dev | HTTP 200, 9,894 bytes, 802 words, 3 links |
| R13-211 | CT first-seen date | clipraiders.com | 0 certificates, no first-seen date exists |
| R13-212 | DNS TXT types (SPF/DMARC) | watchpeoplefight.com | 1 TXT answer, **not SPF-shaped** |
| R13-213 | public release notes exposure | meta-os.pages.dev | HTTP 200, 802 words, 3 links (served the site root; no releases page exists) |
| R13-216 | hosting headers | watchpeoplefight.com | HTTP 200, 24 headers, 5 security headers |
| R13-217 | error pages | meta-os.pages.dev | HTTP **200** for a nonexistent path (see soft-404 finding) |
| R13-218 | robots/sitemap contents | muse-relay-live.pages.dev | robots 200 with 0 disallow rules, sitemap 200 with 0 URLs |
| R13-223 | Wayback inventory | clipraiders.com | 0 snapshots, 0 years |

R13-213 is a substitution: no releases page exists, so the pass read the site root. The counts
are the root page's counts, and the row says so instead of implying a releases page was read.

## Not implemented — filed, not skipped

| task | angle | why it is not implemented under the standing bounds |
|---|---|---|
| R13-207 | search-index visibility | needs a search provider's API; calling one is third-party scraping |
| R13-210 | TLS SAN entries vs expected | needs a TLS handshake and an expected-names list; no list exists in the tree |
| R13-214 | public image metadata | needs a media/EXIF pipeline; none exists in `aegis/` |
| R13-219 | public bucket or upload paths | path enumeration is scanning, not reading public records |
| R13-220 | old deployment URLs still live | needs a candidate URL list; none is supplied or derivable without guessing |
| R13-221 | public test pages still live | same |
| R13-222 | public logs reachable by URL | same |
| R13-224 | public key-shaped filenames | same |
| R13-225 | public backup-shaped filenames | same |

## Unavailable

| task | angle | domain | what happened |
|---|---|---|---|
| R13-215 | domain registration public fields | clipraiders.com | RDAP returned 404 — consistent with the NXDOMAIN above; there is no registration record to read |

## What this section cannot claim

- That the footprint is small. 15 passes over 4 domains is a sample of public records, not a
  complete inventory; the 9 unimplemented angles are exactly the ones that would widen it.
- That `mix`-shaped angles were answered as asked. R13-213 substituted the site root for a
  releases page, and R13-208 read `watchpeoplefight.com`'s root as its "store page".
- That the soft 404 is harmless. It is recorded because a link checker and a person get
  different answers from the same URL, and only one of them is told the page is missing.

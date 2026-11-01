# Meta Custos world pack: machine infrastructure watch

Status: **PARTIAL.** The patrol loop runtime is built and pinning-tested, and stage 2 wires it as a standing Meta OS service (driver + systemd timer); the service has not yet run on a booted Meta OS image. The manifest (`pack.json`, checked by `worlds/validate_pack.py`) and this document are the definitions; no runtime code in this pack runs a real operations room, touches a real responder, or changes any machine it watches.

## Runtime status (what runs, honestly)

| Part | Status | Proven | Not proven |
|---|---|---|---|
| `worlds/custos/runtime/patrol.py`: the patrol loop | BUILT, pinning-tested (tests/custos/) | Pure core on injected signals: certificate tier boundaries (expired / expiring / normal), KEV feed matching against the configured inventory with cross-patrol dedupe, exposure classification for undeclared sensitive ports, yellow observations produce ZERO escalation calls, red observations escalate only to the labelled SIMULATED endpoint, one record per observation plus a patrol summary, a failed certificate probe or unparseable certificate date is an error in the summary (never data, never a patrol crash). Plus one live feed patrol: the real CISA KEV feed (1,766 entries) matched against the example inventory produced 5 real records, committed under `runs/`; security-headers audit pinned on injected headers (all five present is baseline normal, any gap is a yellow record carrying the missing list, a failed fetch is a summary error, a down host gets no headers record, and the audit never auto-fixes anything); DNS drift pinned on injected snapshots (first sighting silent, change yellow with added/removed diff, failed resolution a summary error); subdomain exposure sweep pinned on injected CT + resolver signals (a subdomain resolving inside its domain's expected networks is baseline normal, any address outside is a yellow subdomain-unexpected-network record carrying the unexpected addresses, an unresolvable subdomain is a summary error, a domain with no expected networks configured is not graded, wildcard patterns are not concrete hosts and are skipped); KEV ageing priority pinned on injected feeds (matched CVEs sorted oldest-first by days since dateAdded, more than 30 days flagged aged and red, boundary 30/31 pinned, undated entries recorded unaged and sorted last, threshold configurable via kev_age_red_days); false-positive log pinned on injected signals (RW-009: a dismissed signature is suppressed every patrol as a `dismissed` audit record with its reason and never escalates, a different host or key still raises, a reasonless dismissal and a malformed review file suppress nothing) | Not yet run on a booted Meta OS image, not a systemd unit, never run inside a real operations room; host probes (cert, liveness, exposure) are pinned on injected signals only — the development machine has no direct network path to watched hosts, so they have never run live |
| `os/os/bin/metaos-custos` + `metaos-custos.service`/`.timer`: the standing service (stage 2) | BUILT, pinning-tested (tests/custos/) | Driver behaviour on a stub patrol: STOP file halts before anything runs, live lock blocks / stale lock is stolen, missing config is a logged no-op that never calls the patrol, configured run passes the records and seen-state paths under the state dir, patrol failure propagates its exit code. Both image builds install the driver, enable the timer, and create the state root (build wiring reviewed, carried-mirror byte-identical) | Not yet run on a booted Meta OS image; the timer has never fired on real hardware |
| `worlds/custos/runtime/dedup.py`: alert dedup (RW-008) | BUILT, pinning-tested (tests/custos/) | Identical yellow/red findings inside `dedup_window_seconds` collapse into one record with a count (a synthetic repeat feed — the same missing headers on every patrol — emits once, then suppresses with a growing count in the patrol summary; a changed detail is a new finding, not a repeat; a repeat red finding produces no duplicate escalation; baseline normal records are never folded, so liveness history keeps one record per patrol); the dedup state rides the patrol state file (`seen_dedup`), and with no window or no state the patrol records everything exactly as before | Not yet run on a booted Meta OS image; the window is an operator choice, not a default — the example config sets 24 hours |

## Purpose

Machines fail quietly at night: a certificate lapses, a service stops answering, a database port ends up exposed, a vulnerability in the installed stack lands on the known-exploited list. Each of those is a real, observable machine state, and each is usually discovered late by a human who was asleep.

Custos is the night watch pointed at that problem: Imperium's machinery — watchers, a sealed record, yellow/red tiers — aimed at infrastructure instead of camera scenes. It patrols on a clock, classifies only what it actually observes, and writes every observation down.

## What it watches

- **Known-exploited vulnerabilities.** The CISA KEV feed, matched against the installation's configured software inventory. A match records that the inventory names a listed product. It is an exposure record, never a claim that an exploit happened. KEV ageing priority (RW-006): matched CVEs are recorded oldest listing first by days since the feed's `dateAdded`, each record carrying `days_since_listing`; a match listed more than `kev_age_red_days` ago (default 30) is flagged aged and stays red. "Unpatched" means only that the product is still in the configured inventory; the patrol never verifies patch state on a host.
- **Certificate expiry.** The certificate each watched host actually presents, in days remaining: baseline normal, expiring inside the configured warning window, or expired.
- **Service liveness.** Whether each watched host's service port answers at all.
- **Anomalous exposure.** Whether a sensitive port (database, cache, search, shell) answers on a watched host without being declared expected for that host.
- **Newly issued certificates.** Certificate Transparency logs for watched domains: a cert id not yet in the seen-state becomes a certificate-issued record. `ct_since` bounds a first patrol so a domain with years of history does not flood the record.
- **DNS drift.** A/AAAA/MX/TXT snapshots for watched domains (`dns_domains`, defaulting to the CT watch list): a first sighting only establishes the baseline, and any later change becomes a dns-drift record carrying the added/removed diff per record type. A failed resolution is a summary error, never an empty snapshot.
- **Subdomain exposure.** CT entries for watched domains are enumerated for subdomains; each subdomain is resolved and compared against that domain's configured expected networks (`subdomain_expected_networks` in the config). A subdomain resolving outside its expected networks is flagged yellow. The sweep only ever resolves names CT returned for a watched domain, and it never changes DNS or the host.
- **Security headers.** The response headers each live watched host actually serves (HSTS, CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy), scored 0–5: all five is baseline normal, any gap is a security-headers-missing record carrying the missing list. Audit only — the patrol never fixes a header, rewrites a config, or touches the host beyond reading its response.
- **Alert dedup.** When the config sets `dedup_window_seconds`, identical alert findings (yellow/red, never baseline normal) inside that window collapse into one record with a count: the first patrol in the window emits the record, later patrols in the window emit nothing for it, increment the count in the patrol state file, and report the suppression in their patrol summary (`dedup_suppressed`, `dedup_counts`). A finding whose detail changes is a new finding. With no window set, or no dedup state supplied, the patrol records everything exactly as before.
- **False-positive log (RW-009).** Every dismissed Custos alert lands in a review file with a reason (`false_positive_review`, JSONL; `patrol.py dismiss` writes it). The patrol reads it and stops re-raising the same finding: a dismissal matches one signature (category + host + finding key — CVE, CT id, unexpected addresses, drift diff, missing-header list, or port), never a whole category and never another host. A suppressed finding becomes a `dismissed` audit record carrying the reason, counted in no observation tally and never escalated. A dismissal without a reason is ignored with a review error, and a malformed review file suppresses nothing (fail open).

## Categories and tiers

Every observation lands in exactly one of ten categories:

| Category | Tier | What happens |
|---|---|---|
| baseline normal | none | Recorded. Nothing else. |
| certificate expiring | yellow | Record + flag only. Zero escalation calls. |
| anomalous exposure | yellow | Record + flag only. Zero escalation calls. |
| certificate expired | red | Escalation chain runs. |
| known-exploited vulnerability present | red | Escalation chain runs. |
| service down | red | Escalation chain runs. |
| certificate issued | yellow | Record + flag only. Zero escalation calls. |
| security headers missing | yellow | Record + flag only. Zero escalation calls. |
| dns drift | yellow | Record + flag only. Zero escalation calls. |
| subdomain unexpected network | yellow | Record + flag only. Zero escalation calls. |

In stage 1 the escalation chain is real bookkeeping that ends at a **labelled SIMULATED endpoint**: the steps (record, notify, page, ticket) are written to the patrol record with `endpoint: "SIMULATED"`, and no real responder, vendor, or service is ever contacted. Yellow means a human reads it in the morning; red means the record says, in so many words, that a page *would* have gone out.

## Privacy

The patrol record is local: hostnames, certificate details, match detail, and probe results never leave the installation. The only thing that may cross the bus is the escalation summary — red counts by category and the patrol timestamp, never hostnames, addresses, certificate contents, or vulnerability detail (the manifest's `never_carries` list is the contract, and the validator enforces its presence).

## What it never does

- Never patches, restarts, reconfigures, or otherwise changes a watched machine.
- Never scans or probes a host it was not given in its configuration.
- Never invents an observation: a feed it cannot fetch or a host it cannot probe is recorded as an error in the patrol summary, not as data.
- Never escalates a yellow observation, and never escalates anything to a real endpoint in stage 1.
- Never suppresses a finding without a recorded reason, and never suppresses a whole category or host on the strength of one dismissal: suppression is per finding signature, audited as a `dismissed` record.

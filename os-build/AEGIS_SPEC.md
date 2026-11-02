# META AEGIS — the cybersecurity system (boss naming, 2026-11-02)

Named by the boss 2026-11-02 (tap: Meta Aegis). Un-parked the same
morning: the cybersecurity program he had held "until the OS is
done" — the OS has its face and its agent layer now, so Aegis
opens.

## What it is (his formula)

An institution built FOR a security agent: a watchtower and a
testing ground over the boss's own digital ground — his repos, his
servers, his sites — exploiting where humans lack: it does not
sleep, it does not skim a dependency list at 2 AM and miss the one
bad line. Its output compounds: every sweep leaves the ground
measurably harder than it found it, and the record proves it.

## Its ground (v1 scope — his assets only)

- His GitHub repos (352+) and the MCP servers he ships publicly.
- His websites and stores.
- The Meta OS tree itself.

## What it does

1. **Sweep:** dependency and package checks against known-
   vulnerability data (OSV) and the exploited-in-the-wild catalog
   (CISA KEV) — through his own MCP servers, the arsenal he
   already built.
2. **Secret hygiene:** pattern counts over the trees (the
   secret-hygiene scanner reports counts only, never values).
3. **Surface checks:** unicode-confusable and invisible-character
   checks on shipped text and listings (unicode-security).
4. **Report:** findings land as records with severity, evidence,
   and a receipt in the agent layer's ledger — small = quiet
   note, big = full alarm (the standing sizing rule).
5. **Watch:** on the agent layer, Aegis is a registry agent with
   watch targets (repo tips, listing pages) — rounds, compare,
   speak only on change. The watch idea, aimed at security.


## Two more wings (boss order, 2026-11-02: "add OSINT and OPSEC")

6. **OSINT — his own footprint, read the way a stranger reads
   it.** What the open internet already says about his ground:
   public repo metadata, DNS records, certificate-transparency
   logs (which name his domains and subdomains in public),
   store and listing pages, search-index visibility of things
   never meant to be public. Sources are public records and
   indexes only. The point is defensive: find the exposure
   before someone hostile does.
   Bounds: reading public records about HIS assets only. No
   gathering on other people — ever, including people who
   interact with his stores. No account creation to reach data,
   no contacting anyone, no social engineering. Addresses and
   identifiers found in his own public records are reported as
   COUNTS and locations (which repo, which record), never
   republished as values — main is a public repo.
7. **OPSEC — how the operation leaks, checked as practice.**
   Not a scan: a set of standing checks on how work goes out.
   Commit metadata in public repos (names and addresses riding
   in history), machine names, usernames, and file paths inside
   shipped code, screenshots, and listings, and a pre-publish
   review of anything public-facing (submission materials, the
   launch post, store copy) against one question: does this
   tell a stranger something we did not decide to tell? OPSEC
   findings file as records like everything else; the fix is a
   practice change, and practice changes are the boss's call.

## What it never does

- Never scans, probes, or tests anything that is not the boss's.
  Defensive only, his ground only. No exceptions, no "just
  checking" against third parties.
- Never prints a secret value — counts and categories only.
- Never auto-fixes a live system: it files the finding; fixes go
  through the normal lane (Pax merges, the boss decides money
  and exposure calls).
- Never claims a sweep it did not run. Every report names its
  data source and its run.

## First build (v1)

- [ ] Aegis registered as an agent (manifest, budget, ledger).
- [ ] Sweep v1: OSV batch check over the meta-os tree's package
      manifests + the shipped MCP servers' manifests; report on
      main under os-build/aegis/.
- [ ] Secret-hygiene count over the meta-os tree (counts only).
- [ ] The Aegis face: its own window in the OS face (shield-dark,
      findings as records) — after the sweep is real, not before.
- [ ] OSINT v1: certificate-transparency + DNS review over his
      named domains; public-repo metadata review (commit
      addresses present: counts per repo, no values).
- [ ] OPSEC v1: the pre-publish checklist written, and run once
      over the hackathon submission materials before Nov 4.

## Proof obligations

A sweep counts when its report names: the manifests checked, the
data source versions, the findings with severities, and the
ledger lines of the run. Zero findings is a valid result and is
reported as zero, never padded.

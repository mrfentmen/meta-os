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

## Proof obligations

A sweep counts when its report names: the manifests checked, the
data source versions, the findings with severities, and the
ledger lines of the run. Zero findings is a valid result and is
reported as zero, never padded.

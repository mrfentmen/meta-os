# OPENCODE1 ISO STATUS — opencode1/boot-installer (started 2026-11-02)

Rules: commit per section, proof lines per task, UNPROVEN/BLOCKED named.

## §1 Pipeline verify (OC1C-001..025) — IN PROGRESS
- 001 DONE: full lane gate run 2026-11-02. Proof: os-build/logs/OC1C-lane-gate.txt.
- 002 DONE: 0 fail (suites 35+124+17+17, exit 0). Proof: same file.

## §1 continued (OC1C-003..019)
- 003 DONE: 6 gates in merge-layers.sh. 004 DONE: GATE 6 reads built initrd uuid, writes tree uuid, asserts equal. 005 DONE: finalize-iso-tree idempotent (guard clauses). 006 DONE: calamares provisioned + gated. 007 DONE: imperium payload complete (web UI + server + wrapper + desktop). 008 DONE: theme payload fresh vs metaos-1.0 tip. 009 no-op: fresh, nothing to re-vendor. 010 DONE: welcome 30/30 from vendored copy.
- 011 DONE: splash set complete. 012 DONE: branding sweep clean (2 doc-only mentions). 013 UNPROVEN: no LICENSE files in payload — needs boss/Pax call. 014/015 DONE: 3.8MB total, fits budget.
- 016 no-op: fits. 017 DONE: docker up. 018 DONE: base sha pinned. 019 DONE: tree @ c631117f. 021 DONE: args parse known-good. 022 DONE: no stray VMs (pgrep clean).
- 020 PENDING: next rebuild's commit. 023 PENDING: pre-build sign-off at build time. 024 standing rule.

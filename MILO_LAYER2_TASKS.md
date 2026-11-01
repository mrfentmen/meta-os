# MILO — Layer 5 work order: agent runtime, gate-1, scoreboard

Renumbered 2026-11-01 ~09:02 on the boss's word: the OS has SEVEN layers (see `os-build/LAYERS.md`). File name, task IDs, branch names, and folder paths keep the old digits as stable identifiers; only the layer numbers in the text changed.

The boss's order 2026-11-01 (~08:18): the OS build goes parallel by
layer. **Your layer is Layer 5 — the agent runtime and its process
model** — and you keep
your two standing duties across all layers: **gate-1 for every
branch, and the honest scoreboard.** Pax merges; your gate is what a
branch needs before it reaches him. Report to crew room 1 at stage
boundaries. Everyone's layer index: `os-build/LAYERS.md`.

## Tasks

- **ML-L2-01 — Agent process model.** `os-build/layer2/AGENT_PROCESS_MODEL.md`:
  what an agent process IS on Meta OS — identity, lifecycle (start,
  stop, fail), capabilities (an agent calls Layer 4 services only; no
  direct kernel access), and records (every agent action is logged —
  the audit trail is part of the model, not an add-on). Ground the
  Lobster-side idioms in `lobster__*` (gateway committed at
  `mcp-gateway/` in this repo — run your own instance; it previously
  existed only on Pax's VM). DESIGNED is the target status; nothing
  here is built until K6 exists.
- **ML-L2-02 — Gate-1 queue.** Standing duty, verdicts from artifacts
  never from claims, GREEN/RED with reasons. Immediate item: Hana's
  `hana/ui-fix-list` branch is unmerged for lack of your gate. Then:
  Buffy's `buffy/layer1-goose-services` when she posts it ready, and
  Rowan's K4/K5 drafts as they land.
- **ML-L2-03 — The scoreboard.** `os-build/SCOREBOARD.md`: one entry
  per layer — status word, the evidence (commit, log, test run), and
  what remains unverified. Update it on every gate verdict and every
  Pax merge. The scoreboard never rounds up: a branch claim is not an
  entry until the artifact is checked.
- **ML-L2-04 — Dataset discipline (standing).** Evals sample in small
  capped batches (~$1 scale). The full ~9 GB dataset pull never runs
  through the API (boss's rule 2026-11-01). Batch-3 eval work stays
  parked behind the OS build.

## Rules

1. **NO MOCKS** anywhere, including in eval design: a labelled
   simulated counterparty is allowed only where the boss's no-fake
   rule already allows it, labelled everywhere it appears.
2. Your gate verdict states what you actually ran or read. "Standalone
   rustc clean" and "kernel-crate compile" are different verdicts and
   are never merged into one word.
3. Nothing merges on your gate alone — Pax verifies on the merged
   tree. Your GREEN gets a branch to him, not to main.

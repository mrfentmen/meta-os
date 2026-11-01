# Layer map (OS-130): every design note, placed

- Layer 2 kernel (Rust): scheduler notes live here (scheduler.md);
  the kernel enforces page tables + rings and nothing else.
- Layer 4 services (Goose): supervisor contract (OS-157), IPC
  contract (OS-158), MCP host (mcp-host.md here), updater with
  the A/B rule (ab-update.md), tool processes.
- Layer 5 agent runtime (Lobster): identity (agent-identity.md),
  lifecycle, capabilities, raudit records (records.md), budgets
  enforced at serve time (budgets.md).
- Layer 6 shell/apps (Lobster): home surface, appliance boot
  (appliance.md), bus readers, the human views from every note's
  last paragraph.
- Layer 7 programs: everything in this repo today (Imperium,
  Custos, Officina, ...). Programs call down through tools and
  the bus; they never touch kernel or service internals.
- Cross-layer: bus.md (identity + runtime + shell), memory
  (agent-memory.md, runtime + shell), attention (runtime),
  sandboxing (runtime, enforced at every layer boundary).

OS-131 drift check: read against KERNEL_SPEC rules 1-6 — no
stock kernel anywhere, proof standard kept (QEMU logs), small
steps, old spec stays dead, no mocks (every note marks its
NOT BUILT parts), Debian carrier only. No drift found; the
notes never touch the spec, so there is nothing to fix in it.

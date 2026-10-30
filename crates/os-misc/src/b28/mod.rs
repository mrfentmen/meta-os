//! B28 — OS docs, roles & root docs — **CARRIED, not ported**.
//!
//! Docs only — no code, no tests. All 16 files inventoried 2026-10-30,
//! confirmed logic-free (markdown, gitignore, _redirects), left in
//! place under `os/`. Any file found carrying logic would bounce to
//! Pax for re-batching; none did.

/// Files carried by B28 (exactly `BATCHES.md` §B28).
pub const FILES: &[&str] = &[
    "os/.gitignore",
    "os/INSTANCES.md",
    "os/README.md",
    "os/ROADMAP.md",
    "os/_redirects",
    "os/docs/DEPLOY_RUNBOOK.md",
    "os/docs/DSH-035-CROSS-BROWSER-CHECK.md",
    "os/docs/ROWAN_OS_SCOUT_20261026.md",
    "os/docs/briefs-gallery.md",
    "os/docs/mos-operations.md",
    "os/roles/builder.md",
    "os/roles/documenter.md",
    "os/roles/overseer.md",
    "os/roles/planner.md",
    "os/roles/reviewer.md",
    "os/roles/tester.md",
];

/// B28 carries no logic — always true (checked at inventory time).
pub fn is_logic_free() -> bool {
    true
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn inventory_complete() {
        assert_eq!(FILES.len(), 16);
        assert!(is_logic_free());
    }
}

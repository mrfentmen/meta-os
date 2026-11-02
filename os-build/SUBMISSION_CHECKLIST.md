# Submission checklist — DRAFT (ML4-5)

Draft only, from the event rules as stated in MILO_TASKS_ROUND4.md.
Pax and the boss work this into the final submission. Anything
marked UNVERIFIED below was not checked against the official rules
text or the live repo state from this VM; nothing here is claimed
as verified unless it says so.

- [ ] Repo public and fresh — UNVERIFIED: submission repo is
  mrfentmen/meta-os; public visibility and freshness not confirmed
  from this VM. Pax to confirm before submitting.
- [ ] Meta model use named — UNVERIFIED: the submission must name
  the Meta model it uses. Which model the OS submission names is
  still open; the Trio server's Spark use is a different lane and
  must not be copied in as the OS answer without Pax's call.
- [ ] 3-minute demo video — OPEN: no demo video is on main. The
  demo must stand on the H+24 claim audit (ML4-4), not on claims
  without logs.
- [ ] Library attributions for anything not built in the window —
  OPEN: needs an audit. Known non-window pieces already visible:
  rust-osdev bootloader 0.9.35 (see kernel/src/main.rs header),
  QEMU/SeaBIOS in boot logs. Full list not compiled here.
- [ ] One project only — UNVERIFIED: confirm this submission is the
  single project entered; the Trio, Custos, and other lanes must
  not be entered as separate projects without Pax's call.
- [ ] Claim audit landed (ML4-4, due H+24) — OPEN: the demo and the
  submission stand on it; no submission goes out on scoreboard
  prose alone.
- [ ] No secrets in the repo — VERIFIED pattern, re-check at submit
  time: prior merges carried a 0-hit secret scan per Pax's merge
  verification; re-run before submitting.

# HANA — FINAL PUSH (Pax, 2026-11-02 ~02:10 EST)

Freeze is 05:12 EST. Demo and surface lane. In order.

## H-FP1 — DEMO_SCRIPT.md, by 03:00 EST

The 3-minute demo script, `os-build/DEMO_SCRIPT.md`. Claim order:
boot, ring 3, three programs, fault isolation, shell reporting real
state, then the Imperium run with its receipt. Printable facts only —
every line traceable to a committed log or a run that exists. The
capture pass uses this script; at 03:00 without it, the fallback is
claim order with no script, which is worse. This is the critical
path item of the night.

## H-FP2 — The clear spec text

Owed since RW4-2: the paragraph in `os-build/shell-spec.md` that
rules `clear` (it exists in the kernel, unlisted in help, pending
your text). One paragraph closes the last spec gap.

## H-FP3 — Site copy pass

meta-os.pages.dev: the words match the claim sentence and nothing
overclaims it. Check the live page, fix copy on main, Pax redeploys.

## H-FP4 — Dispatch card (HN4-2), only if 1–3 land early

Builds against `package.picture`, `dispatch_mode: auto`, receipt id.
Otherwise it waits past freeze; the demo does not depend on it.

Standing rules: no invented facts, statuses measured not remembered,
post each landing to room 1. After 05:12: fixes only.

# OC2P H4-4 gap check — plank / fonts-inter / lightdm-gtk-greeter

Q: which of the 3 is missing where?
A: **None missing — gap closed.** All three files list all three packages.

| File | plank | fonts-inter | lightdm-gtk-greeter |
|---|---|---|---|
| `os-build/metaos1-base/packages.txt:39-41` | L39 present | L40 present | L41 present |
| `iso/base/metaos.packages:11-13` | L11 present | L12 present | L13 present |
| `metaos-contracts/PACKAGES.md:3-5` | L3 present | L4 present | L5 present |

History: `packages.txt:35-38` records the cut-2 append by Pax 2026-11-03
per Milo QA H4-4 — these three were missing from `packages.txt` before and
are named in the frozen contract + `iso/base`. The cut-2 base flow consumes
BOTH lists (`packages.txt` + `iso/base/metaos.packages`), not either/or.

OC2 action: none. No workaround, no edit. If OC1's T+1h pack assumes the
dock/greeter/font install, both lists cover it.

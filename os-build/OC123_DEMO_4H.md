# OC1 + OC2 + OC3 — 4-hour demo coordination (boss order)

GOAL (T+4h): one boot to the Meta spinning ASCII logo, with applications that open.
Nobody merges to main except Pax. Nobody posts except Pax. This file coordinates only.

## Iron rules (binding on all three — no exceptions, no extensions)
1. **ONLY OC1 boots any VM/QEMU.** OC1 owns the single furnace. OC2 and OC3 run ZERO QEMU — no local boots, no exceptions. OC1 kills its furnace the moment anyone's fans spin up and continues static work.
2. **No shared-file edits.** Handoffs are copy-only drop-ins with sha256 (receiver copies, never the sender pushing into another tree). Nobody edits another lane's files or branches. OC1 may READ OC3's published ISO bytes (never write to OC3's tree).
3. **No waiting.** Every task below lists inputs that ALREADY exist. If an input is missing, take the named degraded path and keep moving — never idle on another agent.
4. **No fakes.** VERIFIED (ran it) / CODE-INSPECTED (read it) / UNPROVEN (named gap). A parts demo is honorable; a faked full demo is not.

## OC1 — desktop + login + SOLE VM OWNER (the only furnace)
Inputs (all on main): `iso/plymouth/`, `os-build/face/`, `os-build/iso/docs/theme-mock.png`, `os-build/LAYERS.md`. Plus read access to OC3's published ISO bytes + sha (read-only, never write to OC3's tree) and OC2's drop-ins (copy by sha).
- T1: theme asset pack (GTK recolor per frozen `tokens.json`, wallpaper set, Xfwm4 + Plank session defaults). Proof: files + Milo original-asset self-check (no Apple assets/pixels/fonts).
- T2: greeter/autologin config (lightdm drop-in, no credentials baked). Proof: config files + static validation (keys present, no password strings — grep evidence).
- T3: boot the ISO yourself (OC3's published bytes + your theme + OC2 drop-ins) and capture the shot list: login, desktop, dock, launcher, one app open + close each. Post serial + screendumps + shas to YOUR status file AND commit proofs to your branch. No other agent boots.
- T4: installer test only if T3 is green with 90+ min left. Otherwise re-file as BLOCKED with one line.
- Degraded: if tokens.json is ambiguous, ship the mock-faithful subset and name the open decision. Never guess a hex value. If the ISO won't boot by T+3, declare the fallback (below) yourself in the STATUS file and stop burning hours. Your call, no shame.

## OC2 (me) — agents + proof (NO VM, ZERO QEMU)
Inputs (all on main/branch): `agent-layer/`, `server/queue/`, `os-build/OPENCODE2_500_STATUS.md`, OC1's posted boot logs (read-only).
- T1: `.desktop` + `mimeapps.list` apps-defaults drop-in pack for the 4 KEEP apps + agent-status (mousepad/ristretto/atril/thunar + meta-agent-status), with a static validator test (Exec/Name/Icon refs resolve, MIME coverage complete). Home: `agent-layer/desktop-entries/` on my branch. OC1 copies ONE directory by sha — I never push into their tree. Proof: validator suite green.
- T2: cross-check OC1's boot evidence AFTER they post it (read-only): recompute shas, verify no-panic claims against posted serials, file AGREE/DISAGREE. Never touch their files.
- T3: my lane upkeep only: proof-index append, status blocks, sweeps. KF-02 battery + dashboard-forwarded + GUI spike stay PARKED (they need VM; explicitly out of the 4h path — OC1 owns all boots).
- Degraded: if an app has no Exec target on the base, ship its .desktop with `TryExec=` + `NoDisplay=true` and name it (degraded-off, honest).

## OC3 — ISO assembly (NO VM, ZERO QEMU)
Inputs: `/private/tmp/xubuntu-base.iso` (present), `/private/tmp/isowork/` (live tree), Hana specs, OC1 theme pack (copy by sha when posted), OC2 drop-ins (copy by sha when posted).
- T1: assemble the ISO, publish bytes + sha256 to YOUR status file AND commit proofs to your branch. Do NOT boot — OC1 does all boots. No other agent touches isowork.
- T2: re-cut with OC1's theme + OC2's drop-ins included when they post (copy by sha, record sha). Publish new bytes + sha. Still no boot — hand off to OC1.
- T3: installer config only (unattended seed, firstboot script static check). Boot test is OC1's lane, not yours.
- Degraded: if assembly blocks, publish the exact error + last good sha and keep doing static work. Never boot to debug — post logs for OC1.

## Handoffs (copy-only, with sha)
- OC2 → OC1: `agent-layer/desktop-entries/` + validator log + `agent-layer/MANIFEST.md` (OC1 copies, records sha).
- OC3 → OC1: published ISO bytes + sha + file list (OC1 copies/reads, records sha, never writes to OC3 tree).
- OC1 → OC2/OC3: STATUS file + serials/screenshots (read-only for us; cross-checks reference, never edit).
- OC2 → Pax: cross-check verdicts in my status file (merge-ready, no action needed from Pax until checkpoint).

## Timeline
- T+0: this file live. All three start their T1s immediately, no kickoff meeting.
- T+1h: OC1 theme pack posted. OC2 drop-in pack + validator green. OC3: assembly state posted (ISO bytes + sha, boots / doesn't-boot is OC1's call, not OC3's).
- T+2h: OC1 boot attempt with OC1 theme + OC2 drop-ins + OC3 bytes included, OR fallback declared early.
- T+3h: boot proof posted by OC1 (serial + screendumps + shas) OR fallback demo locked (below). No extensions — decide, don't drift.
- T+4h: demo. Full if T+3 passed; honest-parts if not.

## Fallback demo (decided at T+3 by OC1, no extensions)
If the ISO doesn't boot: (1) kernel QEMU boot serial (PROVEN, OC2P S1 logs), (2) appliance agent demo — fresh boot, autostart, patrol cycle, spend tracked (PROVEN, OC2 logs), (3) theme + installer assets as stills (OC1/Buffy packs). Label every part VERIFIED vs CODE-INSPECTED. A parts demo with labels beats a faked whole.

## Kill-switch
Only OC1 holds a furnace. OC1 kills it the moment fans spin up and continues static work. OC2/OC3 never boot so never need to kill. Static work never stops for anyone.

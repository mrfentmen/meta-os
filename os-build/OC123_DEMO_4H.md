# OC1 + OC2 + OC3 — 4-hour demo coordination (boss order)

GOAL (T+4h): one boot to the Meta spinning ASCII logo, with applications that open.
Nobody merges to main except Pax. Nobody posts except Pax. This file coordinates only.

## Iron rules (binding on all three — no exceptions, no extensions)
1. **ONLY OC3 boots any VM.** OC1 and OC2 run ZERO QEMU. No cargo builds anywhere (fan discipline).
2. **No shared-file edits.** Handoffs are copy-only drop-ins with sha256 (receiver copies, never the sender pushing into another tree). Nobody edits another lane's files, branches, or `/private/tmp/isowork/` except OC3.
3. **No waiting.** Every task below lists inputs that ALREADY exist. If an input is missing, take the named degraded path and keep moving — never idle on another agent.
4. **No fakes.** VERIFIED (ran it) / CODE-INSPECTED (read it) / UNPROVEN (named gap). A parts demo is honorable; a faked full demo is not.

## OC1 — desktop + login (NO VM)
Inputs (all on main): `iso/plymouth/`, `os-build/face/`, `os-build/iso/docs/theme-mock.png`, `os-build/LAYERS.md`.
- T1: theme asset pack (GTK recolor per frozen `tokens.json`, wallpaper set, Xfwm4 + Plank session defaults). Proof: files + Milo original-asset self-check (no Apple assets/pixels/fonts).
- T2: greeter/autologin config (lightdm drop-in, no credentials baked). Proof: config files + static validation (keys present, no password strings — grep evidence).
- T3: login-to-desktop proof prep (exact screenshot list for OC3 to capture: login, desktop, dock, launcher — shot list file, so OC3 just executes it).
- Degraded: if tokens.json is ambiguous, ship the mock-faithful subset and name the open decision. Never guess a hex value.

## OC2 (me) — agents + proof (NO VM)
Inputs (all on main/branch): `agent-layer/`, `server/queue/`, `os-build/OPENCODE2_500_STATUS.md`, OC3's posted logs (read-only).
- T1: `.desktop` + `mimeapps.list` apps-defaults drop-in pack for the 4 KEEP apps + agent-status (mousepad/ristretto/atril/thunar + meta-agent-status), with a static validator test (Exec/Name/Icon refs resolve, MIME coverage complete). Home: `agent-layer/desktop-entries/` on my branch. OC3 copies ONE directory by sha — I never push into their tree. Proof: validator suite green.
- T2: cross-check OC3's boot evidence AFTER they post it (read-only): recompute shas, verify no-panic claims against posted serials, file AGREE/DISAGREE. Never touch their files.
- T3: my lane upkeep only: proof-index append, status blocks, sweeps. KF-02 battery + dashboard-forwarded + GUI spike stay PARKED (they need VM; explicitly out of the 4h path).
- Degraded: if an app has no Exec target on the base, ship its .desktop with `TryExec=` + `NoDisplay=true` and name it (degraded-off, honest).

## OC3 — ISO assembly + SOLE VM RIGHTS (the only furnace)
Inputs: `/private/tmp/xubuntu-base.iso` (present), `/private/tmp/isowork/` (live tree), Hana specs, OC1 theme pack (copy by sha when posted), OC2 drop-ins (copy by sha when posted).
- T1: assemble + boot to login. Post serial + screendumps + sha to YOUR status file (`/private/tmp/isowork/OC3-STATUS.md`) AND commit proofs to your branch. No other agent touches isowork.
- T2: run OC1's shot list (login, desktop, dock, launcher, one app open + close each). Post the set.
- T3: installer only if T1+T2 are green with 90+ min left. Otherwise re-file as BLOCKED with one line.
- Degraded: if the ISO won't boot by T+3, declare the fallback (below) yourself in the STATUS file and stop burning hours. Your call, no shame.

## Handoffs (copy-only, with sha)
- OC2 → OC3: `agent-layer/desktop-entries/` + validator log (OC3 copies, records sha).
- OC1 → OC3: theme pack + shot list (OC3 copies, records sha).
- OC3 → OC1/OC2: STATUS file + serials/screenshots (read-only for us; cross-checks reference, never edit).
- OC2 → Pax: cross-check verdicts in my status file (merge-ready, no action needed from Pax until checkpoint).

## Timeline
- T+0: this file live. All three start their T1s immediately, no kickoff meeting.
- T+1h: OC1 theme pack posted. OC2 drop-in pack + validator green. OC3: assembly state posted (boots / doesn't boot yet + exact error if not).
- T+2h: OC3 boot attempt with OC1/OC2 packs included OR fallback declared early.
- T+3h: boot proof posted (serial + screendumps + shas) OR fallback demo locked (below). No extensions — decide, don't drift.
- T+4h: demo. Full if T+3 passed; honest-parts if not.

## Fallback demo (decided at T+3 by whoever owns the blocker, no extensions)
If the ISO doesn't boot: (1) kernel QEMU boot serial (PROVEN, OC2P S1 logs), (2) appliance agent demo — fresh boot, autostart, patrol cycle, spend tracked (PROVEN, OC2 logs), (3) theme + installer assets as stills (OC1/Buffy packs). Label every part VERIFIED vs CODE-INSPECTED. A parts demo with labels beats a faked whole.

## Kill-switch
Any agent kills its furnace the moment fans spin up and continues static work. Static work never stops for anyone.

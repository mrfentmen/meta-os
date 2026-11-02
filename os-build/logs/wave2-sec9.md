# Wave2 Section 9 — Site + submission surfaces (81–90) recon

Date: 2026-11-02. Host: /tmp/wave2. Recon only; nothing proven here, pointers only.

## 1. Site claims vs records — 5-claim spot-check (site/site/index.html)

| # | Site claim | Record checked | Verdict |
|---|---|---|---|
| 1 | K1 boot proven in QEMU | `os-build/logs/K6-boot.txt` carries `META OS KERNEL - alive (K1)` | PROVEN. Note banner drift: K6-boot prints `milestone K3`, R5-soak-final prints `META OS 0.1 (K6)` — already flagged in FREEZE_CERT. |
| 2 | Ring 3 + three userspace programs | `os-build/logs/R5-soak-final.txt`: loader addrs 0x600000000000 / 0x610000000010 / 0x620000000110 + `HELLO FROM USERSPACE` | PROVEN. Matches `records/syscall-path.md` (gate 0xEE, DPL 3). |
| 3 | Fault isolated to one task | Same log: `crasher: about to read zero` → `INT user page-fault … task killed`, other tasks continue | PROVEN. Matches `records/fault-path.md` ring-3 branch. |
| 4 | Shell reports real state | Same log: `STATUS tasks=7 ticks=11739` → `ticks=441232` (ticks move); `records/console-shell.md` | PROVEN w/ caveat: `ps ticks_used` reads 0 at steady console (quantum, not lifetime — recorded finding, not drift). |
| 5 | Reproduced by one command, gate 7/7 (`OPENCODE_ROUND5_REPORT.md`) | Report says `GATE GREEN, 7/7`; logs `gate-run-r5-1.txt`, `GATE-boot-main4702e5c.txt` present | PROVEN for R5 branch. FLAG: `MERGED-boot.txt` is 0 bytes — merged-tree boot unproven, consistent w/ site's own `NEXT PROOF` pill. |

Extras (not counted): `layer1/DEMO_FACTS.md` 33/33 programs, 1253 checks — file present, generator-backed, and site honestly labels it SOURCE ONLY/host-shim. Board `tests 9/9` claim — only ref found is `BUILD_WAVE_2026-11-02.md:77`; no board test log located → FLAG for Milo audit (task 87).

## 2. SUBMISSION_REHEARSAL.md (opencode/round6, task 84)

ABSENT. `find -iname "*SUBMISSION_REHEARSAL*"` returns nothing. Referenced by `OPENCODE_MORE_TASKS.md` §10 and task 84 text. NOT copied anywhere. Closest existing, different thing: `os-build/layer1/BOOT_REHEARSAL.md` (BF5-01 boot-order/entry rehearsal, host runtime, explicitly not Lobster) — do not confuse.

## 3. FREEZE_CERT

Present: `os-build/FREEZE_CERT.md`, status DRAFT, all facts/clauses TBD. Per `PAX_12H_RESPONSE.md` the 05:12 fill is CANCELLED → converts to submission-day snapshot (task 88). Named-owed items listed in-file (goose gate-2, Mac readkey log, boot-test.sh banner grep).

## 4. Forms draft (task 89)

ABSENT. No forms-draft file found. Closest: `os-build/SUBMISSION_CHECKLIST.md` (DRAFT ML4-5; mostly UNVERIFIED/OPEN: repo public/fresh, Meta model naming, 3-min video OPEN, library attributions OPEN, claim audit OPEN). Gaps are named there — that file is the draft's starting point.

## 5. Asset inventory (task 90)

- Film: NO OS demo film on main. `demo/SHOT_LIST.md` capture marked owed (OpenCode R6-2). `oc-proofs/*.mp4` are other-lane cuts, not the OS demo. `test-footage/clips/` empty by design (stills only, per MANIFEST); 24 frames in `test-footage/frames/`.
- Stills: `logs/*.png` (6: K2-boot/console/panic/shell, O-shell, pipeline-screen); `captures/face-web/` (4: login, desktop-apps/dark/light); `demo/beats/*.ppm` (8: beat1–beat5); `face/*.jpg` carrier screens. SHOT_LIST stills (shot-01..06, prog-*) live partly on Pax's machine path, landing in captures.
- Logs: 43 .txt+.png in `logs/` + `face-medicus/` + `R5-imperium/` subdirs; `demo/serial-all.txt`; per-service rehearsal logs under `layer1/host/build/rehearsal/` per BOOT_REHEARSAL.
- Snapshot: FREEZE_CERT draft only (TBD). Forms draft: absent (see §4).

## Gaps for tasks 81–90

84 rehearsal doc absent; 88 cert still TBD; 89 forms draft absent; 90 inventory is this file (needs locations pinned at pack time); 82/83/85/86 screenshots, profile text, runbook, X draft not assessed here.

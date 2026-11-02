# PAX — OS BUILD-OUT (my own list, boss order 2026-11-02 02:22)

My lanes: the reference face page, merges, the website, the
queue's health, submission packaging, dispatch. Posted publicly
so the crew can hold me to it the same way.

## A. The reference face (web desktop in-repo, `face/`)
A1. Desktop page: ribbon live behind, top bar, dock — the mocks
   as working HTML/CSS/JS, ribbon = the real renderer.
A2. Window manager in-page: open/drag/resize/minimise/close.
A3. Light + dark modes; bar colour white/blue/black (settings).
A4. Wallpaper picker with the v1 set (renderer parameters).
A5. Background colour setting, applies + persists (localStorage).
A6. Login screen: glass card, Mrfentmen, password gate (demo
   gate, labelled as such in code + README).
A7. Boot splash sequence → login → desktop, timed transitions.
A8. Terminal window: status card answering with the page's real
   state + a working in-page shell demo backed by committed logs.
A9. Dashboard window: live browser-side numbers + the image's
   four checks displayed from image-status (sourced, dated).
A10. Board window: talks to the in-repo board server locally.
A11. Systems windows: Imperium/Science/Musica/Custos/Officina
   pages embedded as the apps (same honesty labels).
A12. Settings window: every A3–A5 control + animation speed and
   pause + About (version, build, sources).
A13. Files/Notes/Calendar/Calculator/Trash: small real in-page
   apps, localStorage-persisted, honestly scoped in README.
A14. This page is what the kiosk loads if OpenCode's spike picks
   the web shell; if it picks the real desktop, this page is the
   fidelity reference + the website's interactive demo.
A15. Playwright screendump set of the face (dark/light, each
   window) into os-build/captures/face-web/.

## B. Merges and gates (standing, now written)
B1. Merge every gated crew slice the day it gates; verify merged
   content markers, never branch claims.
B2. Readkey merge the same run the Mac boot log lands.
B3. Face slices from opencode/face merged as sections close.
B4. Nightly stale-branch sweep vs the boss's merge calls.
B5. Test baseline guard: main_fails.txt re-measured after any
   tests/ change; new failures stop merges until explained.

## C. Repo and service health
C1. trio_store portability fix — DONE tonight (117/117 held).
C2. Portability sweep: every server/ module imports clean on a
   bare interpreter (no /opt paths); fix or list each failure.
C3. Queue suite on the merged tree after each products change.
C4. package.json name question + README OS-pivot refresh —
   decision packets for the boss, not silent edits.
C5. Board: verify 9/9 on the merged tree; wire plan into shell
   UI stays a listed post-OS item until he says go.

## D. Website
D1. Redeploy after Hana's E-pass; verify live bytes.
D2. Face section embeds the A15 screendumps + (later) OpenCode's
   real image screendumps, dated and labelled.
D3. Download page: image parts + JOIN + hash (with OpenCode 67).

## E. Submission packaging
E1. SUBMISSION_CHECKLIST.md kept live to the deadline (Nov 4,
   21:00 ET): repo public, demo video, Devpost fields, credits.
E2. Demo capture coordination: Hana's script → OpenCode capture
   → my QA pass (facts vs logs) → boss's upload.
E3. Freeze certificate published with Milo at 05:12.
E4. Post-freeze fix lane: only gate fixes + packaging, per rules.
E5. Final verification sweep Nov 4: every checklist item opened
   and checked at its source, none from memory.

## F. Dispatch
F1. Room 1 fed with state as things land (standing order).
F2. Each crew list tracked: landed / in flight / blocked, on the
   hourly status; blockers escalated only when they need the boss
   (Mac results, money, his open decisions).
F3. The boss's open decisions kept as tap choices, short, never
   buried: syscalls.rs wire-or-delete (due today), Hana audit
   cherry-pick, native panel, 21 stale tests.

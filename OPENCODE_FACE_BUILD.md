# OPENCODE — THE FACE BUILD (boss order 2026-11-02 02:21 EST)

Build the Meta OS face: **Meta and Mac had a baby.** Boot the
machine and you land on the polished desktop from the approved
mocks — live blue ribbon wallpaper, glass login, top bar, dock,
real windows, the systems as apps. Spec of record: `PREINSTALL.md`
+ the logo ruling (the logo is the spinning ASCII infinity ribbon,
blue; the generated M is dead). This list is the job. Work it in
order, section by section, all night and past the freeze — the
freeze governs the kernel/submission lanes; the boss has ordered
this lane open.

## Rules of the road

- Every task ends PROVEN or BLOCKED with the blocker named. Proof =
  a committed screendump, log, or recording. No claim without an
  artifact. "Looks right" is not proof; a screendump is.
- Commit per task or per small batch, push to `opencode/face`.
  Pax merges slices to main as they gate green.
- DEMO INTERRUPT: when `os-build/DEMO_SCRIPT.md` lands on main,
  pause this list, run the demo capture (R6-2), then resume.
- Nothing fake: every window opens a real app or a real local page.
  A button that does nothing is a defect, list it as one.
- Simulated things stay labelled SIMULATED everywhere they appear.
- The kernel is untouched by this build. The face rides the Debian
  carrier image. If the bare-metal kernel work needs the Mac, the
  readkey boot log still outranks face tasks — it is one gate run.

## Section 1 — Architecture spike and decision (do first, ~1 hour)

1. Boot the delivered carrier image; record boot time, memory at
   idle, what is installed. Numbers into `os-build/face/STATUS.md`.
2. Spike A: kiosk web shell — a fullscreen browser surface running
   the desktop page (top bar, dock, windows in-page), real Linux
   apps launched behind it.
3. Spike B: lightweight real desktop (openbox/labwc class) themed
   to the mocks, our pages as apps.
4. Judge both on: time to desktop, fidelity to the mocks (side-by-
   side screendumps), real-app launching, build effort to finish.
5. Pick one, write the decision and the evidence into STATUS.md.
   Pax ratifies or overrules on room 1 within one cycle; no answer
   in one cycle = proceed with your pick, the evidence stands.
6. Scaffold `os-build/face/` in-repo: build scripts, assets, and
   the STATUS.md scoreboard every later section updates.

## Section 2 — Image foundation

7. Rebuild/extend the carrier from script (the image build must be
   reproducible from the repo, not hand-edited): one command in,
   one .img out, hash printed.
8. Autologin proven: boot to a session with no typing; screendump.
9. DHCP proven: lease in the boot log + shown in Dashboard later.
10. Hostname `metaos`, timezone America/New_York, locale set.
11. Crew toolchain baked in: node, OpenCode, Freebuff, git —
    version printouts in the build log.
12. Passive updater: systemd timer, git pull of the OS repo,
    applies face updates, logs every run, STOP file honoured.
    Prove one real pull cycle against a test commit.
13. The four standing image checks (autologin, DHCP, dashboard
    HTTP, updater) all land in `os-build/image-status-2026-11-02.md`
    as PROVEN with logs, closing group C of the finish list.

## Section 3 — Boot screen

14. Black boot screen: ribbon spinning centre (the real renderer,
    not a video of it), short white boot lines, thin progress bar.
15. Boot lines are the machine's real stages, not theatre.
16. Screendumps at early / mid / late boot into `os-build/captures/`.
17. Boot-to-login time measured and recorded; budget: under 45 s
    in QEMU, stated as measured.

## Section 4 — Login

18. Ribbon faint behind a glass card; avatar, name Mrfentmen, one
    password box. Matches the approved login mock.
19. Correct password enters the desktop; wrong password shakes and
    stays. Both paths screendumped.
20. Light/dark follows the saved setting; default dark.
21. Login is a gate, not a wall for the demo path: document the
    demo autologin switch and leave it OFF in the shipped image.

## Section 5 — The desktop shell

22. Live ribbon wallpaper as the desktop background, full screen,
    still spinning behind windows, blue.
23. Top bar per the mocks: ribbon mark left, app name + menus,
    clock centre or right per mock, status icons right (network,
    battery where present, sound).
24. Bar colour setting honoured: white, blue, or black.
25. Light mode: white bar, black letters. Dark mode: black bar,
    white letters. Both screendumped.
26. Windows: open, drag, resize, minimise to dock, close, snap
    halves. Each behaviour proven in the proof recording.
27. Desktop right-click or long-press menu: change wallpaper,
    change background colour, open Settings. All three work.
28. Keyboard: alt-tab between windows; the terminal opens by
    shortcut. Proven in the recording.

## Section 6 — Live wallpapers and background

29. The ribbon renderer runs natively in the shell at a steady
    frame rate; measure and record fps on the Mac's QEMU.
30. Wallpaper set v1 (each live/interactive, each previewed in the
    picker): Ribbon Blue, Ribbon Dark, Ribbon Light, plus two more
    built from the renderer's own parameters (speed, density,
    palette within the blue/white/black family).
31. Background colour setting: solid colour behind/between, picker
    in Settings, applies instantly, persists across reboot.
32. Wallpaper picker: live previews, click applies, persists.
    Screendump the picker.
33. Pause the animation when a window is fullscreen (battery/perf),
    resume on exit. State recorded.

## Section 7 — The dock

34. Dock per the mocks: Chrome, Terminal, Files, Dashboard, Code
    Editor, Notes, Calendar, Calculator, Settings, Trash + the
    five systems (Section 10) pinned after a divider.
35. Icons: systems use the approved marks (shield, badge, flame,
    cross, flask, note, eye, gear-wrench); generic apps use clean
    drawn icons in the same style — no Apple art, no stock photos.
36. Hover labels, running-dot indicator, click launches or raises.
37. Every dock entry launches its real target; a launch proof table
    in STATUS.md (app, target, screendump link).

## Section 8 — Terminal

38. Terminal app opens a real shell on the machine.
39. First tab (or the pinned first window) is the Meta OS status
    page: the machine's real state — uptime, memory, tasks,
    storage, network — the same facts the kernel shell reports.
40. `clear`, scrollback, copy/paste all work. Proven in recording.

## Section 9 — Dashboard

41. Dashboard window: CPU, memory, storage, network cards, live
    numbers from the machine itself (not cached, not staged).
42. Network card shows the real DHCP lease (closes the loop with
    task 9). Updater card shows last pull + result (task 12).
43. Refresh cadence 2 s or better; record a 10 s series proving
    the numbers move when load is applied.

## Section 10 — The systems as apps

44. Imperium app: opens to its three services — Vigiles, Ignis,
    Medicus — the real product pages served locally.
45. A staged RED runs the full loop from inside the OS face:
    flag, investigation, auto-dispatch WITH picture to the
    SIMULATED endpoint, receipt shown in the app. Recording +
    artifacts committed. (Rides the R5-4 proven path.)
46. Science Lab app: opens the real Science Lab page locally.
47. Musica app: opens Musica; one generated track plays end to end.
48. Custos app: opens its console page; Officina app: opens its
    workshop page. Each with a screendump.
49. Every system app carries the same honesty labels as the web
    versions (SIMULATED where simulated, UNCONFIRMED where
    unconfirmed). No label regressions.

## Section 11 — Board

50. Board app: the in-repo board wired into the desktop — rooms
    list, post, receive, persistence across restart.
51. Proof: post from the board app, restart the image, the post is
    still there. Screendumps both sides.

## Section 12 — The everyday apps

52. Files: real file manager or a real local equivalent that
    browses the actual disk; open a text file from it.
53. Code Editor: opens repo files, edits, saves; the save is real
    (diff shown in git status inside Terminal).
54. Notes: local notes, persisted, survive reboot.
55. Calendar: local calendar, add an event, survives reboot.
56. Calculator: works, keyboard entry included.
57. Chrome (or the installed browser): opens meta-os.pages.dev.
58. Trash: delete a file from Files, it lands in Trash, restore
    works.
59. Settings app: wallpaper, background colour, bar colour, light/
    dark, animation speed + pause (the web panel's controls), and
    About — real version, build hash, machine facts. Every control
    applies + persists + proven by screendump pairs.

## Section 13 — First run and polish

60. First-boot experience: straight to the face, no setup wizard
    unless the boss asks; a one-line welcome in the board room.
61. Sleep/wake and reboot from the top-bar menu; both return to
    the desktop with settings intact.
62. Sound: silent by default; no surprise audio anywhere.
63. Performance pass: idle CPU/memory recorded; wallpaper fps
    under an open window recorded; boot time re-measured.
64. Fidelity pass: side-by-side, mocks vs screendumps, differences
    listed honestly in STATUS.md and the top five closed.

## Section 14 — Proof pack and handoff

65. Screendump set: boot (3 stages), login (dark + light), desktop
    (dark + light), every app open once, Settings, picker.
66. A 60-second screen recording: boot → login → open Terminal,
    Dashboard, Imperium → run the staged dispatch → done.
67. Fresh image artifact built from script, hash recorded, upload
    in parts as before with a JOIN note (boss's Drive path).
68. STATUS.md final for the night: every task PROVEN / BLOCKED
    with its artifact named. Pax merges from `opencode/face` in
    slices as sections gate green.

## Section 15 — The long tail (after tonight, in order)

69. Lock screen with the ribbon dimmed + clock.
70. Notifications: updater + board + Imperium receipts surface in
    the top bar, dismissible, logged.
71. More live wallpapers (six more, same family discipline).
72. Window tiling quarters + workspaces.
73. Search from the top bar across Files, Notes, apps.
74. The face served from the bare-metal line later — research note
    only, no code: what the kernel would need. File it, stop.

Report per section to room 1 as you close it. Pax is dispatch.

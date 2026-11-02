# face/ — the Meta OS reference desktop (web)

Pax's lane (PAX_OS_BUILDOUT.md, Section A). This page is:

1. The **fidelity reference** for the desktop in the approved
   mocks — live blue ribbon (the real `js/logo-background.js`
   renderer, copied in unchanged), glass login, top bar, dock,
   draggable windows, light/dark, bar colours white/blue/black.
2. The **thing the kiosk loads** if OpenCode's face spike picks
   the web shell (OPENCODE_FACE_BUILD.md, Section 1).
3. The website's interactive demo of the face.

Honesty scope, stated in the windows themselves: the Terminal
answers with the recorded K7 kernel-session shapes (source log
named in the window); the Dashboard labels which cards are LIVE
(this page) and which are RECORD (the committed boot log); the
Imperium window shows the R5-4 recorded run with its SIMULATED
label and says the vision readings were staged; the login is a
demo gate (any password enters) until the real image gate lands
(face task 19).

Built so far: login, desktop, top bar + clock, dock (11 apps),
window manager (drag/focus/close/minimise), Terminal, Dashboard,
Board (browser-local), Imperium record window, Settings (mode,
bar colour, wallpaper speed + pause, wallpaper variants,
background colour — all persisted), About, and working mini
apps: Calculator (buttons + keyboard), Notes (persisted),
Calendar (events persisted), Files + Trash (a small persisted
file store: create/open/delete/restore/empty).
Verified by an automated browser pass (9/9 checks: arithmetic,
persistence, the full file lifecycle, settings) — rerun via
Playwright against face/index.html.
Next slices: Musica window, Science Lab window, boot splash
sequence (A7).

# Native app findings (NC-106) — build OK, defects and gaps only

Provenance: clean clone of origin/main to /tmp/nativeclone, swift build
clean in 38 s (NC-097). make-app.sh assembles MetaTrio.app. No Swift
file edited anywhere (protected).

1. NO APP ICON (gap): the bundle carries zero icon assets (no .icns, no
   asset catalog; make-app.sh writes only the binary + Info.plist). The
   app shows the default executable icon. macOS expects 16–1024 px icon
   sets; all are missing. Proof: find for *.icns/*.appiconset under
   native/ returns nothing.
2. UI IS the server (architecture, not a bug): ContentView loads
   http://127.0.0.1:8080 — nothing is bundled (NC-105, verified by
   source grep: CommandWebView.swift root defaults to 127.0.0.1:8080,
   AppModel.defaultEndpoint localhost:8080). Consequence: with no
   server on :8080 the app has no UI content to show (NC-099: launched
   against dead :8080, process alive 12 s+, RSS 129 MB, no crash, quit
   clean; the web layer shows the standard connection-refused state,
   proven headless against the same URL).
3. Camera permission state (NC-101): across 4 launches no system prompt
   appeared (camera flow never started — no clicks made). The user TCC
   database is unreadable under SIP (verified attempt), so prior
   grant/deny state is unknown. To see the prompt, a human must click
   through the camera flow (tonight's test).
4. Memory (NC-103): 126–129 MB resident at idle map view (2 samples).
5. Cold start (NC-104): AX window in 1 s, 3/3 launches (median 1 s);
   web content (camera list) follows in ~2–4 s per committed footage.
6. Window sizes (NC-100): PARTIAL. Resizing via AppleScript works, but
   live screen capture of the user's display was stopped after one
   wide frame (privacy: it caught terminals, browser, dock — deleted).
   Laptop-size native shots exist in committed round-2 footage
   (nb-067-nativeapp-10s.mp4, tight app-only crops). Small/large native
   sizes unverified by screenshot; web UI responsive behavior at 390 px
   is proven separately (nb-065-phone-15s.mp4).

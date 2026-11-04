# Meta OS — hackathon readiness

Written 2026-11-03, after the desktop booted, the user was renamed, and the
surfaces became app windows. Everything below was run. Where something was not
run, it says so.

## The one-sentence pitch

Meta OS is a desktop Linux you can boot and use, where the apps are Meta's own
surfaces and the machine can hand a job to an agent that actually does it — the
first agentic OS from Meta's side of the fence.

## Demo order (7 minutes)

1. **Boot.** Splash is Meta's, the desktop comes up on the ribbon wallpaper with
   the Meta top bar. No Ubuntu anywhere on screen.
2. **Terminal.** The prompt reads `metaos` in Meta blue. `lsb_release -a` says
   `Meta OS 1.0 (Ribbon)`, codename `ribbon`, `ID=metaos`. One command, no
   explanation needed — this is the de-branding proof.
3. **The dock.** 27 tiles, every one backed by an installed program or a local
   page, every one with its own icon (all 26 PNGs are tracked in git now).
   Open Board, Musica, Science, Officina, Aegis from the dock. Each one opens
   its own window with the app's name in the title bar. **No address bar, no
   localhost, no tabs.** This is the "it's an OS, not a website" beat, and it is
   the one people disbelieve, so do it twice.
4. **Trio.** One click opens Imperium: Vigiles (police), Ignis (fire), Medicus
   (EMS) behind a product switcher. This is the product a first responder would
   actually open.
5. **The agent.** In Terminal: `meta-code "..."`. It calls the model, runs
   tools, writes a real file, and reports cost. Then the same thing from the
   Agents window: pick an agent, type an order, watch the run appear.
6. **The eval.** Show `evals/agentic/report-*.md`: 8/8 tasks, graders are shell
   scripts scoring the files the agent left behind, and the report has a
   "what this does not prove" section. Judges trust the section more than the
   score.

## Tonight's rebuild (2026-11-04)

The image was re-synced from `main` and booted four times. Read
`os-build/STATUS_2026-11-04.md` before quoting anything here: it has the
desktop capture, the 9/9 session proof, the 27-tile dock check, `sudo -n id`
returning root, and a short list of what still must not be claimed (the
physical mouse path, Calamares, an ISO rebuilt from tonight's tree).

## What you can claim, with the receipt

| Claim | Receipt |
|---|---|
| Meta identity, not Ubuntu | `sh os-build/identity/debrand.sh --check` → PASS, plus `lsb_release -a` on the image reading `Meta OS 1.0 (Ribbon)` / `ribbon` / `MetaOS` |
| No `ubuntu` user or home | `rename_user.sh --check` → PASS, `grep -r /home/ubuntu` → 0, the account is `meta` |
| The OS boots | `proof_boot.sh` → PASS, framebuffer 1920×1080 not single-colour, capture `captures/proof-boot-1920x1080-20261103T203318Z.png` |
| Apps open as windows, no URL | **Board only, proven by capture** (`captures/app-window-board-2026-11-03.png`). The other tiles use the same `meta-app` line — say "same mechanism", not "all verified" |
| Calendar has a real backend | `notesd --selftest` inside the image → 11/11 PASS (note survives restart, ICS export, import, settings) |
| The agent registry is not decorative | 24 agents, 23 live, 1 draft, 0 missing entry files (checked from `agents/registry.json`) |
| Agents can think and act | `evals/agentic/report-*` → 8/8 + relay, 43 model calls |
| Runs inside the OS, not just on my Mac | in-guest self-test 8/8, `meta-code` exit 0 |
| Key never in the repo | image `/etc/metaos/agent.env`, root 0600, sha-verified |
| The dock is really on screen | `captures/dock-live-1920x1080-20261103T2109Z.png` — live guest 21:09 UTC: Meta OS top bar, ASCII wallpaper, blue `metaos` prompt, dock along the bottom |
| The dock is 27 real tiles, not bookmarks | `grep -cE '^\s*add_app ' os-build/face/meta-desktop.sh` → 27; every tile's page path and icon file resolved from the tree by script |
| No tile can lose its icon | `git ls-files os-build/iso/payload-theme/icons/metaos \| wc -l` → 26; `shasum -a 256 -c SOURCES.sha256` → 26 OK |
| A 3D app never shows a blank canvas | headless Chrome `?force2d=1` on all four WebGL pages prints the "3D unavailable" line; without it the structures still render |

## What you must NOT claim

- **Not a rewritten Linux.** The kernel is Linux, the window manager is XFCE.
  Say "a Meta distribution", never "we rewrote Linux". If a judge asks, the
  honest answer is: we took the parts that work and replaced everything a
  person sees, then added the agent layer.
- **Not an installer-proven OS.** Calamares has never completed an install. Live
  boot only. Demo from the live image.
- **Not a sandbox.** The agent's tool guard is a denylist, not a jail.
- **The eval is 8 tasks.** It is a demonstration that the loop works, not a
  benchmark. Do not put it on a slide as a percentage of general capability.
- **Musica audio.** GStreamer, the WAV decoder and the PulseAudio output plugin
  are all on the image and the file it plays exists (`take-006.wav`, 320 KB, valid
  RIFF/WAVE). The VM used to have **no sound card at all**; `show_os.sh` now adds
  one. Say "it decodes and plays through a virtual sound card" — do not say
  "hi-fi" and do not claim audio works if you booted without that device.
- **3D is software-rendered.** This host's QEMU has no GPU 3D backend
  (`none`, `curses`, `cocoa`, `dbus` only). Mesa's software rasteriser draws it.
  Never say "GPU accelerated". All four WebGL pages (Science Lab, Music 3D,
  3D Notes, Scientia) now probe for a context first and print an honest "3D
  unavailable" line instead of a blank canvas — verified in headless Chrome
  with `?force2d=1`.
- **Aegis.** The engine's receipts are real and there is now a read-only page
  over them (`aegis-page/`, self-test 18 checks PASS, 10 findings / 1766-entry
  KEV snapshot with 0 checkable / 169 liveness probes / 47 runs). Tile + copy to
  `/opt/face-site/aegis/` are wired in `meta-desktop.sh` and `metaos-update.sh`.
  What is not proven: that copy landing on the live image tonight. Say "the page
  is here, the tile is wired", do not say "the security app is finished". It
  never says "secure" and must not be quoted as saying it.
- **Messages needs a relay.** `bus.html` ships and has a tile, but it is a
  client: it shows "Status: not connected" and asks for a relay REST URL and
  token (kept in the browser only). Without those it is a configure screen, not
  a messenger. If the demo has no relay, skip the tile — do not click it live
  and improvise.
- **Not every dock tile has been clicked.** Board has. The rest are the same
  command line — that is inference, and if a judge asks, say so.

## The three questions you will be asked

1. *"Is this just a browser kiosk?"* — No. Open two apps from the dock and point
   at the title bars. Then `ps aux | grep meta-app`. There is no browser in the
   tile path at all; Epiphany is still installed but unused by the dock.
2. *"Did an agent write this OS?"* — Partly, and here is the queue:
   `plan/BACKLOG.md` (142 achievements) and `plan/QUEUE.jsonl` (401 file-scoped
   items). Show the queue, not a vibe.
3. *"What is still Ubuntu?"* — apt, the package names, `ID_LIKE=debian`, and the
   XFCE binaries. That is deliberate: it is compatibility, not branding. Say it
   before they find it.

## What a judge will click first

In this order, because it is the order they will use:

1. the dock — are those tiles real apps or bookmarks?
2. Board or Calendar — is there a backend or a mock?
3. Trio — does the product actually exist behind the brand?
4. Agents — can you show a run, or only a screenshot of one?
5. Security — "where is your security app?" (answer: the engine is here, the
   screen is not — yet)
6. Terminal — `cat /etc/os-release`, `uname -a`, and whether `apt` says Ubuntu

Have those six open in your head. Nothing else on this page matters if one of
them collapses live.

## If you have 30 more minutes

1. Run `os-build/tools/proof_session.sh` in the guest. It exits 1 with a DEAD
   port list if a backend is down — that is your pre-flight.
2. Record the demo in one take, live. A live fumble beats a polished video that
   a judge suspects was staged.
3. Put `evals/agentic/report-*.md` on screen, not a summary of it.

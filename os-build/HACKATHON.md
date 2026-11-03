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
3. **The dock.** Open Board, Musica, Science, Officina from the dock. Each one
   opens its own window with the app's name in the title bar. **No address bar,
   no localhost, no tabs.** This is the "it's an OS, not a website" beat, and it
   is the one people disbelieve, so do it twice.
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

## What you can claim, with the receipt

| Claim | Receipt |
|---|---|
| Meta identity, not Ubuntu | `debrand.sh --check` → 14 PASS |
| No `ubuntu` user or home | `rename_user.sh --check` → PASS, `grep -r /home/ubuntu` → 0 |
| Apps open as windows, no URL | 8 tiles through `meta-app`, WebKit binding verified in-guest |
| Agents can think and act | `evals/agentic/report-*` → 8/8 + relay, 43 model calls |
| Runs inside the OS, not just on my Mac | in-guest self-test 8/8, `meta-code` exit 0 |
| Key never in the repo | image `/etc/metaos/agent.env`, root 0600, sha-verified |

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
- **Musica audio** is only real once Milo lands the GStreamer path. Until then,
  say "it opens and the decode timeline runs" — not "it plays".

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

## If you have 30 more minutes

1. Run `os-build/tools/proof_session.sh` in the guest. It exits 1 with a DEAD
   port list if a backend is down — that is your pre-flight.
2. Record the demo in one take, live. A live fumble beats a polished video that
   a judge suspects was staged.
3. Put `evals/agentic/report-*.md` on screen, not a summary of it.

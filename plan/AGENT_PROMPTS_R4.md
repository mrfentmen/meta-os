# AGENT PROMPTS — ROUND 4 (4 lanes, non-overlapping)

Paste one block per opencode session. Each lane owns a disjoint file set, so four
agents can run at once without stomping each other. Read
`os-build/APP_INVENTORY.md` first — it is the map of what exists.

**Rules that apply to all four lanes**

- Work on a branch. Name it `r4/<lane>`.
- No mock code, no placeholder handlers, no `TODO: implement`. If something
  cannot be done, write down exactly why in the report and stop.
- Never claim "proven" from reading a file. Proven = a command you ran and its
  output, pasted.
- Do not edit the other lanes' files. If you need a change there, say so in your
  report instead of making it.
- Do not reboot the whole build. One boot to verify your own work at the end,
  nothing more.

---

## LANE A — Dock and app surfaces

**Goal:** every app that already ships a page is reachable by clicking a tile,
with its own icon, and it opens as a chromeless window.

**Read first:** `os-build/face/meta-desktop.sh` (the `add_app` table),
`os-build/face/metaos-update.sh` (the site copy list),
`os-build/iso/payload-theme/icons/metaos/` (which icons exist),
`os-build/iso/payload-theme/icons/generate-icons.py`.

**Do:**

1. `/opt/face-site/bus.html` is missing from the image — that file **is** the
   messaging app ("muse-relay — live bus"). Copy it in with the rest of the site
   payload and make the build always include it (`metaos-update.sh` already
   lists it; the image predates it).
2. Same for `labs/science-lab-review/index.html`.
3. Add dock tiles, each pointing at a page already on the image:
   - **Boards** → `/surfaces.html` (the Imperium dispatch boards, nine city
     world packs — the biggest asset with no tile)
   - **Messages** → `/bus.html` (after step 1)
   - **Logo Studio** → `/logo-studio.html`
   - **Music 3D** → `/labs/music3d/index.html`
   - **3D Notes** → `/design/meta-musica-notes.html`
   - **Agent Budget** → `/design/agent-budget-dashboard.html`
4. **You need six icons that do not exist.** `add_app` falls back to a themed
   icon name when `$ICON_DIR/<name>.png` is absent, and a themed name the theme
   does not carry draws as a **blank white tile** — that bug has already bitten
   this project once. So: generate `boards`, `messages`, `logo`, `music3d`,
   `notes3d`, `budget` PNGs in the same style and size as the existing set,
   using the existing generator. Do not point two tiles at one icon.
5. Keep the icon fallback honest: if an icon is genuinely missing, print a
   warning in the login log rather than silently drawing blank.

**Must not touch:** `agents/`, `kernel/`, `os-build/identity/`, `aegis/`,
`os-build/face/session.sh`, any `labs/` or `design/` page content.

**Definition of done:** `meta-desktop.sh --home /tmp/x --owner $(id -u):$(id -g)`
runs offline, reports N tiles, and every generated `.dockitem` names a
`.desktop` whose `Icon=` is an existing file. Paste the tile count and any
warnings.

**Report:** `os-build/lanes/R4_A_DOCK.md` — table of tile → page → icon path,
what you generated, what you could not, and the offline run output.

---

## LANE B — Aegis, the security app

**Goal:** Aegis stops being an engine nobody can open. It gets a page and a tile.

**Read first:** `aegis/*.mjs` (the engine), `os-build/aegis/runs.jsonl`,
`findings.jsonl`, `findings-ledger.jsonl`, `KEV.json`, `LIVENESS.json`,
`HISTORY_SCAN.json`, `os-build/AEGIS_SPEC.md`, and three existing surfaces to
copy the house style from: `os-build/face/board.html`, `calendar.html`,
`os-build/iso/payload-site` / repo-root `surfaces.html`.

**Do:**

1. Write `aegis-page/index.html` (repo) — a **read-only** dashboard over data
   that already exists on disk. Sections: findings by severity, KEV matches,
   liveness probe results, the last N runs with timestamps and pass/fail. No
   fake numbers: if a JSONL is missing or empty, the page says exactly that
   ("no findings recorded — engine has not run").
2. It must survive being opened with a dead backend. Every fetch has a visible
   failure line naming the port, in the same style as the other pages. A blank
   window is a bug.
3. Serve it: add it to the site copy list so it lands on the image and is
   reachable on 18934.
4. Add an **Aegis** tile to `os-build/face/meta-desktop.sh` using the icon that
   already exists at `payload-theme/icons/metaos/aegis.png`.
5. Add a `--selftest` to whatever small helper you write, so the page's data
   path can be checked offline without a browser.

**Must not touch:** `os-build/face/meta-desktop.sh` **except** the single
`add_app aegis …` line (Lane A owns the rest of that file — coordinate by only
appending one line at the end of the app block), `aegis/*.mjs` engine logic,
`agents/`, `kernel/`.

**Definition of done:** the page renders from real repo JSONL in a local
`python3 -m http.server`, with a screenshot or pasted DOM text as evidence, and
the "engine has not run" path is demonstrated by pointing it at an empty dir.

**Report:** `os-build/lanes/R4_B_AEGIS.md` — what data each panel reads, the
exact file paths, what you proved and how, and what a judge would still find
missing.

---

## LANE C — 3D: prove it, then fix it

**Goal:** the Science Lab molecule viewer and Music 3D actually draw in the VM,
with a measured frame rate. No rewrite of the scenes.

**Read first:** `labs/molecules/index.html` (line 230 has the WebGL guard),
`labs/music3d/index.html`, `design/meta-scientia-molecules.html`,
`design/meta-musica-notes.html`, `os-build/face/session.sh` (software GL is
already exported there), `os-build/face/native/meta-app.py` (WebGL properties
already set), `os-build/APP_INVENTORY.md` §6.

**Context you must respect:** this host's QEMU has no `gl=on` and no GTK display
backend, so hardware 3D is impossible here. The image has Mesa `swrast` /
`llvmpipe`. The accepted approach is software WebGL.

**Do:**

1. Prove the current state: boot, open the molecule page through `meta-app`,
   capture the screen, and say plainly whether the model drew. If it did not,
   capture what the page printed instead.
2. If it did not draw, find the actual cause and fix it at the smallest level —
   missing Mesa package, missing WebKit feature flag, sandbox, DRI path, or a
   page bug. Do not guess: each change gets its own before/after capture.
3. Measure. Report the frame rate or render time at 1180×780 and at
   1920×1080, and the atom count you used. If it is below 10 fps at full screen,
   say so and give the window size that is smooth.
4. The page's no-WebGL path must remain honest and must never be removed to make
   a screenshot look good.

**Must not touch:** `os-build/face/meta-desktop.sh`, `aegis/`, `agents/`,
`kernel/`, `os-build/identity/`. You may edit the four 3D pages and
`meta-app.py` only if step 2 proves the change is needed.

**Definition of done:** a capture showing the molecule, the fps number, and the
exact command to reproduce it. If hardware 3D is needed for the demo, say that
plainly instead of faking it.

**Report:** `os-build/lanes/R4_C_3D.md`.

---

## LANE D — Agent pipeline in the guest, plus the About panel

**Goal:** prove an agent actually runs *inside* the booted OS and produce one
honest number judges can read; then give the OS an About panel.

**Read first:** `agents/registry.json` (24 agents), `agents/runtime.mjs`,
`agents/watchman.mjs`, `agent-layer/README.md`, `agent-layer/stage.sh`,
`os-build/iso/payload-agent/metaosd.mjs`, `os-build/face/agents.html`,
`/usr/local/bin/meta-ask`, `os-build/RELAY_STATUS.md` if present.

**Do:**

1. Inside the booted guest, submit one real job through `meta-ask` (or the
   18940 relay) for an agent that is live, and follow it to a recorded run in
   `runs`. Paste the job id, the agent, the timestamp, and the run record.
2. Count how many of the registry's agents can actually accept a job. The rest
   are "draft" or unbacked — list them by name. This number goes in the report;
   it is more useful than a percentage of nothing.
3. If the relay cannot start in the guest, that is the finding. Document the
   exact failure (unit state, log lines) and stop — do not paper over it.
4. Build the **About this OS** panel: a small page or native window showing
   version (from `/etc/os-release`), build date, kernel line, session name, and
   a one-paragraph statement of what this OS is. Reachable from Settings and
   from a dock tile. It must read live values, not hardcoded ones, except the
   prose.
5. Do not use the API key in any committed file. If a key is needed, read it
   from the environment and say so.

**Must not touch:** `os-build/face/meta-desktop.sh` (except a single `add_app`),
`aegis/`, `labs/`, `os-build/identity/`.

**Definition of done:** a run record from inside the guest for a named agent,
the live/draft agent counts, and an About panel whose values match
`/etc/os-release` on the image.

**Report:** `os-build/lanes/R4_D_AGENTS_ABOUT.md` — including a short list of
claims a judge could make that this OS cannot back up.

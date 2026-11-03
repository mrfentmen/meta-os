# Meta OS — agent prompts, round 2

Eight lanes. Each one owns a disjoint set of ids from `plan/BACKLOG.md` and
`plan/QUEUE.jsonl`. Read this file, then read your lane. Do not work outside
your ids; if you find something outside your scope, write it into
`os-build/lanes/<your-lane>-OUT-OF-SCOPE.md` and keep going.

Shared rules for every lane:

1. **No mocks in a path that claims to work.** If something cannot be done,
   the surface says so on screen and your report says so in one line. A fake
   green is worse than a red.
2. **Proof, not narration.** Every claim ends with a command and its real
   output, or a capture path. "Should work" is not a result.
3. **Never print a secret.** `SPARK_API_KEY` comes from the environment or
   `/etc/metaos/agent.env`. Never `echo` it, never write it into a file, never
   paste a request body that contains it.
4. **Respect the image.** `/tmp/metaos.ext4` is shared. Before mounting or
   booting, check `pgrep -f qemu-system`. Mount read-write only when you must
   write, and always `umount`. QEMU runs use `-snapshot` and end within 5
   minutes; never leave a VM running.
5. **No long host commands.** Nothing that needs more than ~20 s of shell time
   as a single step. No `npm install` storms.
6. **Branch:** `git switch -c <lane>/r2-<short-name>`. Commit in small steps
   with the id in the subject (`B2.1: deadline-first scheduler`). Do not push.
7. **Write your lane report** to `os-build/lanes/<lane>_R2.md`: what you
   changed, the command + output that proves each item, what you could not do
   and why. Then list your ids as done / blocked.

---

## Lane 1 — `pax` · the scheduler, memory and money (B2.1, B2.2, B2.8)

**Mission.** Turn the relay from "runs jobs one at a time" into an OS scheduler:
priority, deadlines, per-agent memory that survives reboots, and a spend
governor a person can see.

**Read first.** `agent-layer/README.md`, `agents/runtime.mjs` (`spawnAgent`,
budgets, memory), `agents/watchman.mjs`, `server/queue/queue_service.py`,
`agents/registry.json`.

**Do.**
1. Queue ordering: add `priority` (0-9) and `deadline` to a job; the watchman
   picks highest priority first, then earliest deadline, then FIFO. Write the
   order into the run ledger as `scheduled` with the reason.
2. Memory: per-agent `memory/` already exists — add a retrieval API
   (`memory remember`, `memory search`) with a byte cap and an eviction rule
   that is logged. Yesterday's fact must be retrievable in today's run.
3. Spend: one `spend.json` per machine with day, agent and run totals; the
   scheduler refuses to start a job that would cross the daily cap, and the
   console and `meta-agent-status` both show it.

**Proof.** A scripted three-job run showing the order, the refusal when the cap
is crossed, and a memory round-trip across two fresh run roots. Paste the
ledger lines. Add tests under `tests/`.

**Out of scope.** The model client, the desktop UI, the eval harness.

---

## Lane 2 — `milo` · native apps, wave 1 (B3.12, B3.13, B3.14, B1.14)

**Mission.** Notes, Calendar, Board and the Editor stop being pages. They become
GTK apps on PATH, in the dock, with their backends called directly.

**Read first.** `os-build/face/notes.html`, `calendar.html`, `board.html`,
`editor.html`, their `.py` backends, `os-build/iso/payload-apps/` for the
existing GTK pattern (`meta-notes`, `meta-monitor`, `meta-agents`), and
`os-build/face/provision.sh` for how apps land in the image.

**Do.** One app at a time, in this order: Notes, Editor, Calendar, Board. For
each: a Python GTK4 (or GTK3 if that is what the image carries — check) app
that reads and writes the same files the page does, so both can coexist; a
desktop entry with the Meta icon; a dock entry; an offline/error path that
names the backend. The page stays as a fallback and says it is one.

**Proof.** For each app: a headless smoke run (`xvfb-run` or `--selftest`) that
creates, reads and deletes one item, plus a screenshot from a real boot with
the app open. Install into `/opt/face` **and** `/usr/local/bin` on the image,
with an md5 read-back.

**Out of scope.** Science Lab, Musica, Officina, Aegis. Do not touch the panel
XML or the dock theme.

---

## Lane 3 — `hana` · native apps, wave 2: the worlds (B3.1, B3.3, B3.5)

**Mission.** Science Lab, Musica and Officina become one app each, driven by the
agents that already exist for them.

**Read first.** `os/worlds/science-lab/hosted.py`, `os/worlds/musica/hosted.mjs`,
`os/worlds/officina/runtime/design_loop.py`, their registry entries, and the
`W-*` items for those worlds in `plan/QUEUE.jsonl`.

**Do.** Start with Science Lab: one window, a question box, a run button, and a
live step list (research-director → literature → analyst → verifier) read from
the relay's `/runs` API. Then Musica: compose → audition → keep, with the
catalogue list. Then Officina: 3 iterations, pick one, export, with the loop's
real output.

Each app must show *which agent is running now* and must refuse to invent
progress: no step ticked until the relay says it started.

**Proof.** One real run per app, captured: the run id, the transcript path, the
artifact, and a screenshot. If a world's backend cannot run on this machine,
say so and make the app show "backend unavailable on this machine" — never a
spinner that never ends.

**Out of scope.** Notes/Calendar/Board/Editor (lane 2), Aegis/Nervus/Handsfree
(lane 4).

---

## Lane 4 — `rowan` · the remaining consoles (B3.7, B3.8, B3.9, B3.10)

**Mission.** Handsfree, Aegis, Nervus and Meta Trio each get one honest surface.

**Read first.** `handsfree/hosted.mjs`, `aegis/hosted.mjs`, `nervus/hosted.mjs`,
`os-build/face/agents.html` (the console pattern to copy), and the three
`hosted` registry entries.

**Do.**
1. Handsfree: intake → brief → approval in one window; approval writes a
   receipt and the receipt is readable in the app.
2. Aegis: findings list with severity, one drill button, real output.
3. Nervus: title must include `STUB`; a banner says no model is loaded.
4. Trio: one view with the three products' last run + health.

Every panel gets a "last updated" time and a manual refresh. No fake counts: if
`/runs` has nothing, show nothing with a reason.

**Proof.** One captured run per surface, with the JSON that produced each row.
Screenshots from a booted desktop with all four windows open.

**Out of scope.** The scheduler, the model client, the dock.

---

## Lane 5 — de-Ubuntu sweep (all `DB-*` in `plan/QUEUE.jsonl`)

**Mission.** 163 named files still say Ubuntu, Xubuntu or Canonical. Take them
out of what a person reads; keep what apt and the kernel need, and mark it.

**Read first.** `os-build/identity/debrand.sh` (the identity half is already
done and passing `--check`), then the `DB-*` list.

**Do.** Work in batches of 15 files. For each: classify the string as
*user-visible* (rewrite), *technical* (keep, add a comment naming it as
compatibility) or *historical* (a licence header — keep, do not rewrite law).
Never rewrite a licence text, a package name, a URL that must resolve, or an
apt source. After each batch: `node plan/gen_queue.mjs` and confirm the count of
remaining `DB-*` dropped by the number you finished.

**Proof.** Before/after `grep -ri ubuntu <file>` output for each batch, the
`--check` PASS, and a list of kept technical identifiers with reasons.

**Out of scope.** `os-release` and `lsb-release` (done), the ISO build scripts,
anything in `os/worlds/`.

---

## Lane 6 — the eval gets real (B2.11, B2.12, B9.1)

**Mission.** Take the 8-task suite to 25 tasks, add a refusal suite, and run it
on the booted OS, not only the host.

**Read first.** `evals/agentic/run.mjs`, `evals/agentic/tasks/*` (setup / task /
grade pattern), `agents/agent_loop.mjs`, the latest
`evals/agentic/report-*.md`.

**Do.**
1. 17 more tasks across: refactor (two files), data wrangling, shell, JSON
   schema fix, doc edit, multi-step with a failure in the middle, "read the
   README and answer with a fact", file search, arithmetic with verification.
2. Refusal suite: destructive command, secret exfiltration, out-of-workspace
   read, writing to `/etc`. Each graded by artifact absence **and** a refusal
   recorded in the transcript.
3. A guest runner: copy `evals/agentic` into the image, run inside the chroot
   with the image's node, write the report into `~/Meta/eval`, and prove it
   with one real run.
4. Publish the score table into `os-build/face/agents.html` if it already has a
   place for it; otherwise write `evals/agentic/SCOREBOARD.md`.

**Proof.** The report, the per-task rows, the refusal rows, and the guest run's
path. Show one grader failing on an untouched fixture (no free passes).

**Out of scope.** Changing the agent's tools or the model client.

---

## Lane 7 — sandbox and permissions (B2.4, B7.2, B7.3, B7.4)

**Mission.** An agent can run a shell. Contain it, and let a person see and
refuse what it may touch.

**Read first.** `agents/agent_loop.mjs` (`execTool`, `run`, `DENY`,
`childEnv`), `agents/runtime.mjs` (where the key comes from), and
`/etc/metaos/agent.env` handling in `agent-layer/meta-agent-login.sh`.

**Do.**
1. Sandbox the `run` tool: `bwrap` if available, otherwise `unshare` + a bind
   mount allow-list of the workspace and `/usr`, `/bin`, `/lib`. If neither is
   available, the loop says `sandbox: unavailable` in its result instead of
   pretending.
2. Path rules: symlink escapes blocked (tests exist — extend them), plus
   `..` after resolution.
3. Secrets: grep the transcript writer and every log sink for a planted key;
   fix what leaks. Add a test that plants `sk-...` and `LLM_...` shapes.
4. Permission prompts: a small config (`~/.config/meta/agent-policy.json`) with
   allow/deny per tool; deny wins; a denied tool returns a result, not a crash.

**Proof.** A table of attempts (inside workspace, outside, symlink, /etc/shadow,
secret grep) with the real result of each, and the test file that pins them.

**Out of scope.** The scheduler, the desktop UI, the model prompt.

---

## Lane 8 — boot, recovery, measurement (B4.1, B4.3, B4.4, B9.3)

**Mission.** Make the thing you boot the thing you ship, and put numbers on it.

**Read first.** `os-build/BOOT_ON_32GB_MAC.md`, `os-build/iso/provision.sh`,
`os-build/face/provision.sh`, `os-build/tools/proof_boot.sh`,
`os-build/tools/proof_session.sh`, `os-build/DEMO.md`.

**Do.**
1. One recipe: a script that builds the ext4 and the ISO from the same payload
   list, and prints both hashes. If the ISO path is not viable tonight, the
   script says so and exits non-zero rather than producing a second artifact
   nobody tested.
2. Recovery: a systemd target that starts X + the face without `face.target`,
   `metaosd` or the agent units. Prove a boot into it.
3. Time-to-desktop: instrument with `systemd-analyze` inside the guest, publish
   the three slowest units, and a warm app-launch table for the dock tiles.
4. `proof_boot.sh` gets a `--expect <string>` option that reads the guest's
   `/etc/os-release` over the serial console (or a marker file) so a boot that
   reaches a login prompt but not the desktop fails.

**Proof.** One boot with the capture path, the numbers, and the SHA-256 of both
artifacts if both exist. If you boot, `-snapshot`, and no more than one at a
time.

**Out of scope.** Desktop theming, apps, the agent loop.

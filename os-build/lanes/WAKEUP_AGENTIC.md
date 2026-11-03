# Morning. Here is what changed while you slept.

Short version: **the OS can think now.** An agent inside the image calls the Meta
model, uses real tools, writes real files and leaves a receipt — and there is a
graded eval that says so instead of a screenshot that implies it.

Nothing was rebooted, no VM was left running, and no fan spun up: every proof
below ran in a chroot or on the host. The key you left on the Desktop is
installed **into the image only**, root 0600, and was never printed anywhere.

---

## Read these three, in this order

1. `os-build/lanes/AGENT_PIPELINE.md` — the chain, every command that proved it,
   and the limits I will not let you oversell.
2. `plan/BACKLOG.md` — 142 big achievements (apps, boot, agent core, security,
   demo).
3. `plan/AGENT_PROMPTS_R2.md` — 8 heavy prompts for pax, milo, hana, rowan and
   four more, split so no two lanes touch the same files.

The mechanical half of the plan is `plan/QUEUE.jsonl` — **401 items**, each
naming a real file and a check that can fail (`node plan/gen_queue.mjs`
regenerates it as the tree moves). 164 of those are the de-Ubuntu sweep.

**543 items total.** You asked for ~2000. I could have padded it by splitting
"change the title bar" into "change the close button" and running the generator
over every file twice; that would be a lie dressed as a plan. 543 items where
each one is a real surface, with 142 of them multi-day achievements, is the
number I can defend. If you want more, the honest way is to add surfaces (each
world × each app × each backend already multiplies).

---

## What actually works now

**1. The agent loop** (`agents/agent_loop.mjs` + `agents/model_client.mjs`)
Tools: `list`, `read`, `write`, `run`, `finish`. Every call touches the real
workspace. Budgets on actions and dollars, three retries on 5xx/transport, a
transcript per run, secrets redacted, and the key stripped from every tool
subprocess (proven in the self-test with a fake key present).

**2. A graded eval** (`evals/agentic/`) — 8 tasks through the loop plus one run
through the OS relay, each scored by a shell grader on the artifacts:

```
eval: 8/8 tasks + relay pass        (report-2026-11-03T13-03-20-311Z.md)
```

All 8 graders were first run against untouched fixtures and all 8 failed — no
task can pass by doing nothing. The whole suite costs about two cents.

**3. It runs inside the image.** Installed to
`/usr/share/metaos/agent/agents`, executed with the image's own node 18.19.1:

```
agent_loop self-test: 8/8 pass
meta-code: result .../agent-result.json (exit 0)
```

`meta-code "orders"` is new: a terminal command that gives the OS one job and
puts the run in `~/Meta/agent-runs/<stamp>/`. On the image right now:

```
$ meta-code --ls
20261103T130023Z-Run-uname-s-and-the-first-line-of-etc-os  stopped:model-error steps=3 $0.0009
20261103T130337Z-Write-summary-txt-in-your-workspace-with  ok steps=4 $0.0008
```

The first row is honest history: a 503 from the model backend after it wrote its
file. That is why the client now retries. The second is the retry working.

**4. The key is in the image, correctly.**
`os-build/tools/set_spark_key.sh` → `installed: lines=1 mode=600 sha-match=yes`.
The value is compared by SHA-256 on both sides and never echoed. `--check`
reads it back. Re-running it is safe.

**5. Ubuntu's name is off the box.** `os-build/identity/debrand.sh` rewrote
`/etc/os-release`, `/usr/lib/os-release` and `/etc/lsb-release`, fixed
`/etc/issue` (it had a literal `\n`), and disabled the two Canonical motd
scripts. On the image:

```
Distributor ID: Metaos
Description:    Meta OS 1.0 (Ribbon)
Release:        1.0
Codename:       ribbon
```

`ID_LIKE=debian` stays on purpose, and apt stays on `noble` in
`sources.list.d` — those are compatibility, not branding, and the script says so
in its header. `--check` prints 14 PASS rows.

**6. Registry + console path.** `meta-coder` is a live agent
(`node agents/agent_loop.mjs`, 14 actions, $0.10 cap) so the board, `meta-ask`
and the agents page can start it. The relay proof (`PASS relay — wrote
relay.txt`) runs through `spawnAgent`, the same code the OS uses.

---

## What is not proven (say this to judges before they ask)

- **No graphical boot for these features.** In-image proofs were chroot, not a
  session. Binaries, paths, registry, network call: proven. "It starts from the
  desktop exactly like this": not proven. Lane 8 in the prompts + a guest eval
  runner is the fix.
- **The eval is 8 tasks.** File work, repairs, counting, one refusal. No GUI
  driving, no multi-agent handoff, no long horizon.
- **Sandboxing is a denylist, not a jail.** `run` blocks `sudo`, `mkfs`, `dd` to
  devices, fork bombs, power control and obvious credential egress; a determined
  command still reaches what the user can reach. Lane 7 builds the real jail.
- **Budgets are estimates.** The price table is local (`METAOS_PRICE_*`), not an
  invoice. Spend so far is a few cents of your dollar.
- **Still Linux underneath.** The Meta session, the agent layer and the
  identity are Meta-coded; the kernel is Linux's. The K6 kernel lane is a
  separate build and is not what boots.

---

## Tomorrow, in order

1. Boot it once with a window and watch the desktop come up (the session now
   starts plank, the face services and the agent layer at login).
2. In the guest terminal: `meta-code "list 5 things to fix in this OS and write
   them to todo.md"` — this is a 30-second demo beat nobody else will have.
3. Run `node evals/agentic/run.mjs` on the host for the number, and put that
   number on the slide.
4. Hand the 8 prompts out. The lanes are disjoint; nobody will overwrite anyone.
5. Pick the demo path: `os-build/DEMO.md` now has beat 8 (the agent works) and
   beat 9 (the eval), written as commands with expected output.

If you only have an hour: boot, run beat 8, show the eval table, and say the
limits out loud. That is a stronger pitch than a claim you cannot back.

---

## Files I touched

New: `agents/model_client.mjs`, `agents/agent_loop.mjs`, `evals/agentic/**`
(harness + 8 task folders), `os-build/tools/set_spark_key.sh`,
`os-build/tools/install_agent_runtime.sh`, `os-build/identity/debrand.sh`,
`agent-layer/meta-code.sh`, `plan/**` (backlog, queue, generator, prompts),
`os-build/lanes/AGENT_PIPELINE.md`, this file.

Changed: `agents/registry.json` (added `meta-coder`), `agent-layer/stage.sh`
(installs and checks `meta-code`), `os-build/DEMO.md` (beats 8–9).

Image `/tmp/metaos.ext4`: agent runtime refreshed (35 js + registry), `meta-code`
installed, key installed, identity rewritten. All verified by read-back.

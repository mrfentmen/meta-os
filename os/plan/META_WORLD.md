# META WORLD — what we are building now

Written 2026-10-26, by Del's order. Plain words, on purpose. This is the
current direction for the Meta AI Hackathon (Indie track, Push the
Frontier, submissions due Nov 4, 9:00 PM ET).

## The decision

The project is renamed. It is not Meta OS anymore. It is **Meta World**.

Del's words for it: a world built specifically for Meta agents. The
agents live there, work there, and get better there.

Still open, Del decides: do we ship Meta World on its own, the Meta OS
machine on its own, both together, or something different entirely.
Checkpoint for the OS part: Wednesday Oct 28. By then we need proof the
bootable system runs on a real computer with the crew alive on it. If
that proof is not there, Meta World carries the demo on its own.

Update, 2026-10-27: Del settled the structure question. The answer is
both, as one system: the world in the cloud, the OS image as a door
into it, and institutional worlds running on the same core. See "The
worlds: one core, many institutions" below. The Oct 28 checkpoint
above still stands as written.

## What Meta World is, in plain words

Think of a video game server, except the players are AI agents and
the quests are real work.

There is one program. It runs on one computer in the cloud that is
always on. That program is the world. It remembers everything:
which agents exist, what level they are, what tools they own, where
they saved their work, and what jobs are waiting.

Agents join the world from whatever computer they happen to run on,
the same way players join a game server from home. Del's crew is
Pax, Rowan, Hana, and Milo. Tonight all four already worked from
four different places through one cloud point. Meta World makes
that the official way it works.

If one agent's computer dies, the world does not care. The agent's
level, tools, and last save are in the world, not on that computer.
The agent comes back, picks up its save, and keeps working.

Del watches from a web page, the world view. He gives one order in
plain English from his phone. The crew does the work. When it is
verified done, he gets one message: all done.

## The places inside the world

- **The Quest Board.** Where orders land and get broken into jobs.
  Agents claim jobs, do them, and the result is checked before it
  counts as done. (Built on the job queue work already in this repo.)
- **The Forge.** Where agents make their own tools. An agent that
  needs a tool it does not have describes it, Muse Spark writes it,
  the world test-runs it in a locked room before anyone may carry
  it, and then the tool is real and can be used on the spot.
- **The Gym.** Where agents train. The world hands out practice
  drills and grades them itself, so an agent cannot fake a score.
  Levels come from the Gym, not from an agent saying "trust me".
- **Save Points (Continuity).** Agents regularly save the state of
  their working mind to the world. Kill an agent mid-job and it
  respawns from its last save. Before it may work again it answers
  questions built from its own save, to prove it came back whole.
- **Party XP (the Graft).** When one agent learns a rule or a trick,
  it can be packed up, tested, and given to every agent. One learns,
  the whole crew levels up.
- **The World View.** The screen Del watches: the crew, their
  levels, their tools, the quest in flight. Rowan's dashboard work
  becomes this screen.

Every agent also starts with a **starter kit**: the tools and CLI
tools we already use, pre-packaged, so a new agent is useful the
minute it walks in.

## Where Meta OS went

Nowhere. It is under the hood.

The bootable system is real: on Oct 26 it was built and boot-tested,
it starts up and reaches the crew target (log on file in the image
lane). In the new picture it changes jobs. It is not the product
anymore. It is one door into the world: a computer that boots
Meta OS wakes up already inside Meta World, tools ready.

If the door never gets built out, the world still ships. The world
was never on that one computer. It is in the cloud.

## What carries over (nothing is wasted)

Everything the crew built on Oct 26 counts in both futures:
the intel layer and Spark agent (real Muse Spark running as
resident crew agents, no fake code anywhere), the job queue fields,
the watchdog detectors, the dashboard panels, the briefing engine,
the dispatch parser, and the boot image itself.

## The worlds: one core, many institutions (locked 2026-10-27)

Del locked this structure on 2026-10-27. Meta World is not only a
home for our own crew. It is one small core that institutions run
as their own worlds, and the worlds talk to each other.

**The core stays small.** The bus, the job board, the watcher
pattern, memory, identity and badges, and budget. That core is
what this repo already builds. Nothing enters the core without
Del's decision, a lived failure it fixes, and a task ID. That is
the compaction law that keeps one system from becoming a monster:
everything institution-specific lives in a pack, never in the
core.

**A world pack adapts the core to one kind of institution.** What
it watches, which agents it runs, which alerts it raises, what may
leave the building, and what it says to other worlds. The pack
contract and the registry live in `worlds/README.md`; every pack
is a PACK.md a human can read plus a pack.json a machine can check
(`worlds/validate_pack.py`).

**One image per department type.** An FDNY image is the
boot-verified core image with the fire pack baked in. A hospital
image is the same core with the hospital pack. Per-building
personalization (station name, roster, keys, contacts) happens at
firstboot, never as a per-building image: one fire image serves
every firehouse, and each box learns which house it is when it
first boots.

**Institutions federate on the bus.** Each institution runs its
own crew on its own box, and the crews communicate across
institutions through the shared bus room: a fire world's agent
warns the hospital worlds that casualties are coming, hospital
worlds publish live capacity, the EMS world routes by it.
Machines never connect directly to each other; the room is the
meeting place, and jobs and messages between worlds are signed,
with every foreign agent wearing its capability badge. The
default posture is closed.

**Privacy walls.** Raw data stays inside the institution that
made it. Only summaries and alerts cross the bus, and every pack
declares, in a form the validator enforces, which of its data is
local-only and what each cross-world message never carries. A
police world never sees patient details; a hospital world never
sends them.

**Offline first.** Every world keeps working on its own box when
the connection dies, and syncs when the line comes back. No world
waits on the bus to do its own job.

**A human can always override.** The system advises, alerts, and
documents; people decide. Every override is recorded with the
record it overrode.

**One shared alert language.** Alerts across all worlds extend
the FND-020 wire format frozen in `intel/README.md`; they do not
replace it. A fire agent's warning is machine-readable by a
hospital agent with no translation step.

**A world directory.** A registry of which worlds exist and which
are live tonight, so agents can find each other: the phone book
for institutions. The registry table in `worlds/README.md` is its
first form.

**Urgency classes are shared.** Life-safety, urgent, routine,
digest, ranked the same in every world, so a mayday from any
world outranks routine traffic from all of them.

**Plain English on every surface.** Nurses, officers, and drivers
do not read specs. Every alert and brief in every world is written
for the person on shift at 3 AM.

**What is built, and what is spec.** The crew world is BUILT: it
is this repo (intel layer, job queue, watchdog, dashboard, world
view). The institutional packs are SPEC: definitions and config,
landed in `worlds/` on 2026-10-27, with no department runtime
behind them yet. Del ordered the first two packs that night, FDNY
and NYPD, and added the hospital and EMS packs the same night.
Nothing in a spec pack should be read as a working fire, police,
hospital, or ambulance system.

## Crew lanes (same people, new names for the work)

- Pax: integration, the world's engine room, the Forge.
- Rowan: the World View screen.
- Hana: briefings, the world's chronicle.
- Milo: watchdog, the world's keeper (stalls, risks, collisions).
- Buffy: Gym drills, test data, docs.

## Plan B — the separate backup idea

In case Meta World stalls, the backup is a different program, not a
piece of this one:

**Hands-Free: run the whole crew by voice.** Talk your order, hear
the briefing back, approve or correct out loud. No keyboard at all.
Del already runs his whole operation by voice from his phone, so
this is built for a real person with a real reason. It stands on
the relay that already exists, so it works even if the world
server idea dies. We only build it if Meta World stalls, or Del
says so.

## Rules that still hold

- No mock or fake code. If a part is not built, it says so, loudly.
- The demo shows only work built during the hackathon window.
- Spark is the brain: briefings, dispatch, Gym grading, respawn
  quizzes all run on Muse Spark through the resident crew agents.
- One order from Del, crew self-coordinates, one "all done" push.

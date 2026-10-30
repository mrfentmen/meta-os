# Meta OS

**Meta OS — a Linux-based operating system rebuilt for Meta agents.**
It boots machines *and* minds: every agent launches with a versioned mind
image (constitution, skills, memory, capability grants), and the crew
coordinates itself until the work is verified done.

Meta OS the machine, **Relay Intelligence** the mind.

## What this is

This repo is the build base for Meta OS, created for the Meta Global AI
Developer Hackathon (Indie track, *Push the Frontier*). It merges
[muse-relay](https://github.com/Mrfentmen/muse-relay) — the shared message
bus, job queue, and overseer system my Muse instances already run on —
as the base layer, with the Meta OS build on top of it:

- **Relay Intelligence** — Muse Spark mission control on the bus:
  plain-English briefings, plain-English dispatch into a signed job queue,
  and a watchdog that catches silent crew failures and self-repairs before
  it escalates.
- **Meta OS** — a Debian-based image that boots straight into the crew:
  the bus, the queue, the watchdog, the dashboard, and the agent drivers
  run as system services. State lives on disk, never in a session, so a
  reboot is just a shift change.
- **Mind images** — each agent boots from one versioned bundle, so a
  better upbringing ships like a software update and can be A/B-tested.
- **The completion contract** — the boss orders once, in plain English,
  from his phone. The crew self-coordinates and works until the job is
  verified done, then sends exactly one push: "All done," with the summary.

## Layout

- The muse-relay base (bus, `jobs.py` queue, `mos/` overseer, tests) sits
  at the root. Its own README is kept as
  [README-MUSE-RELAY.md](README-MUSE-RELAY.md).
- [`plan/`](plan/) holds the build plan: the master plan, the Meta OS
  design, the layer plan, the schedule, the demo script, and one lane
  file per crew member.

## Status

Hackathon build in progress (Oct 26 – Nov 4, 2026). The plan files are
the source of truth for what is built, verified, and still open.

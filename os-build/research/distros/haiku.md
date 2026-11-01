# Haiku — a single purpose revival OS, and the focus lesson

Lane: Buffy, research and tools. Task B2 (Section H mirror, OS-112).
Written 2026-11-01. RESEARCH, nothing built or tested.

## What it is

An open source reimplementation of BeOS, in development since 2001, released
as a usable beta in 2018. Same API, same feel, same responsiveness. It exists
to keep one idea alive: a desktop OS that responds instantly and has a coherent
API, with no compatibility layer to Linux underneath.

## The model, mechanically

- **One audience, one job.** A desktop for people who liked BeOS. Everything
  else is out of scope, permanently.
- **API fidelity over novelty.** Existing BeOS applications compile and run, so
  the project has a real application catalog without writing one.
- **Pervasive multithreading** in the design: the UI is responsive because
  operations do not block it, a BeOS inheritance.
- **Package management arrived late** (2019) and was contentious, because it
  changed the "everything is just files you can drop in" character.
- **Small team, long horizon**, funded mostly by donations.

## What it does better

1. **Consistency of purpose for 25 years.** No pivot, no rebrand, no platform
   chase. The project has never had an identity crisis.
2. **A stable API is a form of user respect.** A program from 2001 that still
   runs is a promise kept, and almost no OS on this list can say that.
3. **Latency as the design goal.** Responsiveness is specified and defended,
   not an accident of hardware.
4. **Clear scope lets a tiny team win.** They have one thing to be good at.

## What it costs

1. **25 years and still beta.** The most honest cost on this whole list. Focus
   buys coherence and does not buy speed.
2. **No ecosystem momentum.** Few new applications, few new users.
3. **One platform, one architecture lineage**, so relevance is bounded.
4. **Late, contested decisions** (packaging) cost years of goodwill, a warning
   about how a change lands culturally even when it is right.

## One borrowable idea

**Make latency a specified property, and defend it.**

For an agent first OS, the equivalent promise is **time to first useful
action**: how long from power-on to an agent's first completed tool call, and
from boot to a user's first completed command. That is a number, it can be
stated in the milestone spec, and it can be checked. Haiku's lesson is that
stating it as a property (and refusing changes that break it) is what makes an
OS feel alive, and our OS will be judged by agents on the same clock.

Concretely: K1 through K6 should each add a measured number to the report, not
just a log line. K1's is "serial line to halt". By K6 it is "first process to
first answered tool call". That belongs in Milo's scoreboard
(`os-build/gates.md`) as a column, not a separate doc.

## License position

- **MIT** (per the Haiku project's own license page). Permissive, so the source
  is legally readable.
- **BeOS compatibility means the heritage has its own terms.** BeOS itself was
  proprietary and its API is documented by a community book, so do not treat
  any BeOS-era binary or SDK as ours to use.
- **Some bundled pieces differ** (fonts, third party libraries). Check a
  directory before assuming.
- **Verdict: idea only, and specifically the measured latency property.**

## Verdict for Meta OS

Take the latency-as-specification habit into the milestone table, where it
pairs with the boot log rule: a milestone gets a log *and* a number. And take
the 25-years-still-beta datapoint as a planning input, not a discouragement:
our scope is narrower than an entire desktop, and it is still a long road.

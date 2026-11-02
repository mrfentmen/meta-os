# BUFFY 2 — VERIFICATION + HOST LANE (boss order 2026-11-02)

You run on the 8 GB Mac. Your job is the two blocks nobody else
can close from inside the sandbox: real tool hosts, and a second
pair of eyes on a real machine. Report to room 1 as buffy2.

## A. Tool hosts (closes two standing blocks)
A1. Install the Goose toolchain; `goose version` output posted.
A2. Run `goose check` on the merged services corpus from a clean
    clone of main; full counts to room 1 (this is Milo's gate-2 —
    BLOCKED until you land it).
A3. Re-run weekly or on Milo's ask; each run dated in
    os-build/layer1/GOOSE_GATE2.md.
A4. Stand up a Lobster host from Buffy's F-pack runbook when it
    lands; run her caller skeleton; transcript to room 1. Until
    the pack lands, this task is BLOCKED-on-pack, stated so.

## B. Second gate lane
B1. Clean-clone `os-build/gate.sh` on every main tip Pax names;
    verdict + log name to room 1. You are the second gate, after
    Milo's gate-1; disagreements get flagged, never averaged.
B2. The kernel readkey boot, if OpenCode's plate is full: boot
    Rowan's merge-pack branch, log to os-build/logs/, verdict to
    room 1. (One gate run; Pax merges on green.)

## C. Image reality checks
C1. Boot the carrier image in UTM (or the Mac's emulator);
    record: boots or not, how far, screendump. Emulation speed
    stated honestly, never dressed as hardware speed.
C2. When OpenCode ships the face image: same boot check + the
    four image checks re-run on your machine as a second source.

## D. Overflow from Buffy 1 (parallel-safe)
D1. Section B deepening tasks (failure drivers, boundary sweeps)
    for services Buffy 1 assigns you on room 1 — coordinate there,
    never double-claim a service.
D2. Your slices land on `buffy2/services`; Milo gates, Pax merges.

Rules: nothing claimed without an artifact; UNCOMPILED and
UNPROVEN are honest words, use them; 8 GB is tight — one heavy
job at a time, say so when the machine is the blocker.

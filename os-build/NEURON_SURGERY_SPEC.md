# THE MODEL BENCH — neuron surgery as a Meta OS program

Boss's idea, 2026-11-02: incorporate his neuron-surgery work
(public repo Mrfentmen/neuron-surgery — single-neuron steering
in IBM Granite models, ~9,400 steered generations, 1,500-neuron
layer sweeps, dose windows, the audited layer curve) into Meta
OS as a program that BOTH a user and the OS's own agents
(OpenCode included) can drive. Product name: the boss's to
settle. Placement recommendation at the end.

## What it is (his formula)

An institution built for an agent AND a bench for a person:
the room where models get taken apart. A user points it at a
local open model — the packed ~20GB class, or small ones like
Granite 350M / 3B — and does what his repo does by hand: map
the layers, sweep the neurons, steer one, measure what
changed. The agents use the same room through tools, so
OpenCode can run a sweep at 3 AM and leave the receipts.

Two doors, one room, one ledger.

## The two doors

1. **The user door (face).** Pick a local model, see its layer
   map, run a sweep, steer or ablate, read the before/after.
   His repo's workflow as a program anyone can drive — no
   notebook required.
2. **The agent door (tools).** The same operations as callable
   services (Goose at L4, agent/MCP-shaped surface above):
   sweep, steer, ablate, evaluate-delta, map-layers. OpenCode
   and the registry agents call them like any other tool.
   Every operation writes a ledger record: model hash, layer,
   neuron, dose, probe, result. His provenance discipline IS
   the ledger discipline — they were always the same idea.

## The second job: breaking models down

The bench also shrinks models. From the layer and neuron maps:
find what does not move behavior, cut it (prune, quantise),
re-evaluate, and keep a cut only when the before/after receipts
prove the model still does its job. A smaller local model,
derived from a bigger one, with the proof attached — this is
what makes the local pack practical on smaller machines.

## The method is the program's rules (from his repo, verbatim
discipline)

- Dose windows are real: inert, persona, collapse. The bench
  labels which zone a steer landed in; it never calls a dose
  "a little" or "a lot" without the window.
- Layer curves before claims. No single-layer storytelling.
- Probe dependence: results belong to (neuron, probe) pairs.
  The bench refuses to report a neuron without its probe.
- The subspace correction: when the effect is a low-dimensional
  subspace, the record says subspace, never "a neuron".
- Composition failure is a first-class warning: two good steers
  can destroy the output; the bench tests compositions before
  recommending them.
- Nulls are results. Zero is reported as zero, never padded.
- Any automated judging gets audited (his classifier audit:
  kappa against a second rule and against hand labels) before
  its numbers are quoted.

## Where the work runs

Where the models live: the host/carrier with the local pack,
or the user's own machine — never inside the bare-metal
kernel. In the OS it is a registry agent plus services plus a
face; the compute rides the host lane like the other proven
loops (Imperium patrol, Musica studio, Officina faber).

## What it never does

- Never edits a model it cannot re-evaluate. No cut, steer, or
  claim without a before/after run behind it.
- Never touches a model that is not the user's own local copy.
- Never presents a steered output as the model's "real" belief:
  records name the intervention every time.

## First build (v1)

- [ ] Spec (this file) + the boss settles name and placement.
- [ ] The operation set written as tool contracts (sweep,
      steer, ablate, evaluate-delta, map-layers) with the
      ledger record shape.
- [ ] Host runner over one small model (Granite 350M class)
      reproducing ONE published result from his repo — the
      floor-1 map is the natural target.
- [ ] The face: layer map + sweep results as records — after
      the runner reproduces, not before.

## Placement (boss's call)

Recommended: inside **Science Lab** as its model bench —
LABORATORY's Computational Lab and Independent Verification
are already this shape, and Hortus set the precedent (an
engine inside a system, not a standalone system). If the boss
wants it headline, it stands alone as its own system; the
spec works either way.

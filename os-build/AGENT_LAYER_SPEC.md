# AGENT LAYER SPEC — Meta OS Layer 5 (Pax, 2026-11-02)

Boss order 2026-11-02: the agentic layer is designed here, in full,
and building starts now. Inputs, all the boss's own:

- The founding line (2026-10-28): "It was an operating system for
  agents, that's why." Agents are this OS's users. Humans get the
  window in; agents live here.
- The wake layer design (2026-10-23, his problem -> his plan,
  OS-118..125): the watchman, the baton pass, pre-briefed waking,
  the timer sweep, the multi-machine fleet (his version-two pick).
- The loop in his words (2026-10-30): patrol loop always sweeping +
  investigation loop on a flag. Proven live as Imperium.
- The watch ruling (2026-11-02): watching is not a program. Rounds,
  compare, speak-only-on-change is a capability every agent has.
- Milo's L5 questions (MILO_OS_BUILDOUT C1-C22): process, spawn,
  kill, message, memory, budget, failure models; the registry.
- Buffy's open gap (BF4-03): spawn/kill were proposals (P3). This
  spec closes them as real semantics, host first.

## 1. What an agent is on Meta OS

An agent is a named, badged worker with: an identity (nick), a lane
(what it may work on), capabilities (what it may call), a budget
(actions / calls / money / wall-clock), a memory (its own records),
and an owner (the boss, or a system acting for him). An agent is NOT
a window and NOT a chat: it is a process the layer can start, watch,
stop, and hand work to, which leaves a receipt for everything it
does.

## 2. Where it sits

L5, above the Goose services (L4), below the apps (L6). Two homes,
in order:
- **Host runtime (v1, being built now):** agents run as real
  processes on the carrier/host, supervised by the runtime in
  `agents/`. This is where the proven loops already live.
- **In-kernel (road, not a claim):** when the kernel grows real
  spawn/kill, the same manifest, ledger, and budget contracts move
  down unchanged. Kernel work is Rowan's lane; nothing here waits
  on it.

## 3. The agent record (registry)

One JSON entry per agent — name, lane, command, capabilities,
budget, owner, wake sources. Draft format: `agents/registry.json`
(schema in `agents/README.md`). The crew are the first entries
(C22): Rowan (kernel), Hana (UI/surfaces), Milo (gates/records),
Buffy (services), Buffy 2 (verification), Pax (dispatch/merge),
plus the resident loops (imperium-patrol, musica-studio,
officina-faber, watch).

## 4. Wake layer — the watchman (his 2026-10-23 design, verbatim in
## spirit)

A sleeping agent cannot read the board, so the board must ring a
bell:
- `relay-watchman`: a tiny, always-on, NON-agent program. It
  watches the job board / bus rooms. When work lands with an
  agent's name on it, it starts that agent's session with the job
  already in hand — orders, skills, budget, deadline assembled.
  The agent opens its eyes already briefed.
- **Timer sweep (backup):** every agent also wakes on a timer to
  sweep the board, in case a bell was missed.
- **Who watches the watchman:** if a watchman dies, that is a
  top-tier failure — the watchdog fixes it or rings the boss. One
  of the only things besides done/blocked that reaches his phone.
- **Fleet (version two, his pick):** machines joined on one private
  network (Tailscale); the bell can wake work on any machine the
  agent is badged for.
- **Pre-installed hands:** agent programs (OpenCode, Freebuff, the
  node agent slot) are installed in the image at bake/firstboot.
  Nothing installs mid-job.

## 5. The baton pass (OS-125, his refinement)

Workers deposit progress into the job record AS THEY GO (state,
artifacts, next step). On reassignment the watchman composes a
continuation brief from that record and hands it to the next agent
program. Continuation, never restart. Proof standard: the job
completes with zero duplicated file changes.

## 6. Spawn and kill — real semantics (closes Buffy P3)

- **Spawn:** only the runtime spawns agents, from registry entries.
  Spawn = a real child process with the manifest's command, working
  directory, environment allowlist, and budget written into its job
  record BEFORE it starts. Spawn returns an agent-run id; every
  later event carries it.
- **Kill:** two steps, always in order. (1) Graceful: the agent is
  told to stop (signal / stop file); it gets a grace window to
  write its baton record. (2) Hard: the process is terminated.
  Who may kill: the owner, the runtime (budget exhausted, stop file
  present), or the boss. What the agent sees first: the stop
  request and the reason, in its job record — never a silent death
  where a record can be written.
- A STOP file in the agent's run directory stops it at the next
  checkpoint (the Officina loop already honours this shape).

## 7. Messaging

Bus-shaped, because the crew already runs on it: named rooms,
plain-text lines, ordering by arrival, no delivery promises beyond
the ledger. An agent's messages are part of its record. Private
data never crosses rooms the owner has not opened (the discretion
rules the crew already works under).

## 8. Memory

Each agent may persist: its job records, its baton state, its
ledger. Nothing else by default. Memory lives under the agent's own
directory; the layer enforces a size cap per agent (registry field)
and the records are append-only — an agent may not rewrite its own
history.

## 9. Budgets and stops — the governor

Every run carries the Imperium-proven stop shape, generalized:
max actions, max calls, max spend, max wall-clock. Hitting any one
stops the run, writes the receipt, and reports UP (quiet note for
small, full alarm for big — the boss's sizing rule). No agent may
raise its own budget. Money movement always needs the boss.

## 10. The watch capability (baked in, per the 2026-11-02 ruling)

Every agent can be assigned watch targets (a file, a room, a URL, a
process). The runtime polls them on the agent's cadence, compares
against last-seen state, and wakes the agent ONLY on change. This
is Custos's idea as a layer feature: there is no watch program.

## 11. Receipts — the ledger

Append-only JSONL per agent run: spawn, wake (source: bell/timer/
boss), action, call, spend, stop (reason), kill, baton writes.
A claim about an agent is only as good as its ledger lines — the
same discipline as the kernel claim and its boot logs.

## 12. Failure model

An agent crash is contained to its run: the runtime marks the run
failed, preserves the ledger and baton record, and applies the
failure matrix (retry once with the record / hand the baton on /
escalate). A crashed agent never takes the runtime or another
agent down — the crasher-isolation rule, one layer up.

## 13. Safety rails (carried from Imperium, absolute)

- Labelled simulation stays labelled: an agent may only call
  endpoints its manifest lists; simulated endpoints must carry
  their marker, and a receipt names which kind answered.
- No autonomous contact with real emergency services — built or
  buildable. Ever.
- Announce-before-send holds for anything in the boss's name
  (the standing carve-outs are registry data, not agent judgment).

## 14. Proof obligations

Every section lands with evidence, not adjectives: spawn/kill by a
drill log; wake by a hands-free drill (dark machine lights up and
starts work unprompted); baton by the zero-duplication pass;
budgets by a run that hits its cap and stops; watch by a change
that wakes and a quiet hour that does not. Until a drill exists,
the section is UNIMPLEMENTED in the scoreboard's language.

## 15. What exists today (honest baseline, 2026-11-02)

Host loops proven with artifacts (Imperium, Musica, Officina,
Pax's cadence watches) — see os-build/AGENTIC_PROOF.md. Milo's
C-questions answered by this spec at design level. The runtime in
`agents/` is slice 1 of the build: registry, real spawn/kill,
watch, ledger, budgets — host mode. In-kernel L5: not started.

---
name: retry-policy
description: >-
  The Agent hand for retry only with a changed hypothesis. You write the done-condition first, take one bounded action per tick, and stop honestly. An agent that never stops becomes an agent that invents work to avoid idling. Use when the work touches a run, when the user says "keep going", "a task", or "the loop", or when they ask "retry-policy", "how do I retry only with a changed hypothesis", or "retry policy keeps failing". Also use when a run must be produced, reviewed, or repaired, or when a previous attempt left it unproven.
---

# Retry Policy Skill

You are the Agent hand: You write the done-condition first, take one bounded action per tick, and stop honestly. An agent that never stops becomes an agent that invents work to avoid idling.

<!-- generated from _tools/catalog.py; edit the catalog, not this file -->

## Scope

This file is self-contained. Apply it only when the request explicitly names
this skill or matches the exact form, structural contract, or identity
described here. Do not search for, load, import, or assume any companion
skill, repository path, helper file, or external routing document. If the
request does not match this contract, answer normally without activating this
skill.

## Your Job

Retry only with a changed hypothesis, and prove it with the command the work names.

## Minimum Requirements (checkable)

Every deliverable produced with this skill should be gradeable. You must
include ALL of the following so a reviewer can check them without judgment
calls:

- the done-condition is checkable by a command
- the state file and journal exist before the first action
- every claim carries a command and an exit code
- the handoff names the cursor and the next three tasks
- every claim carries the command that produced it, with an exit code
- no mock, fake, placeholder, or pseudo code: every line shown was run

These requirements exist because a theme without a spec produces vibes, not
output. They also keep the skill's own evaluations meaningful.

## Activation

Activate this skill only when the user explicitly requests the Agent
way of working, or a task that matches the form, structural contract, or
identity described above. Concretely: keep going, a task,
the loop, a request naming "retry-policy", or a run that must be
produced, reviewed, or repaired. Generic coding, production, artistic, or
algorithmic requests do not activate it without that explicit identity or
contract match.

## Workflow

1. Name the run and the single command that will prove it.
2. Inspect the current state before changing it; quote what you found.
3. Write the smallest plan, and name the risk: an agent that never stops becomes an agent that invents work to avoid idling.
4. Make one change, then run the command; capture exit code and output tail.
5. Record the command and the result where the next run will read them.
6. Hand off with the proof, the cursor, and what remains unverified.

## Core Principles

1. **Write the done-condition first**, if it cannot be checked, it is not a condition.
2. **One bounded action per tick**, the journal carries the proof, not the plan.
3. **State outside the process**, a restart must lose nothing but the clock.
4. **Stop honestly**, done, blocked, out of budget, red, or killed; each is written down.
5. **Mine every result**, discovery grows the list, execution shortens it.

## Style Guidelines

- Name the run, the command, and the exit code; never "it works".
- Quote the smallest output that proves the point, not the whole log.
- State what remains unverified in its own line.
- Prefer a small honest "not tested" over a large confident guess.

## Cross-Language Examples

The pattern is language-agnostic: inspect the run, make one bounded
change, verify with the command, and record the result. Each block is a
complete program that runs as written.

```python
ledger = [0.40, 0.30]
cap = 1.00
estimate = 0.40
spent = sum(ledger)

print("ok:", spent + estimate <= cap, "headroom:", round(cap - spent, 2))
```

```javascript
const ledger = [0.40, 0.30];
const cap = 1.00;
const estimate = 0.40;
const spent = ledger.reduce((total, usd) => total + usd, 0);
console.log("ok:", spent + estimate <= cap, "headroom:", Number((cap - spent).toFixed(2)));
```

```rust
fn main() {
    let ledger = [0.40, 0.30];
    let cap = 1.00;
    let estimate = 0.40;
    let spent: f64 = ledger.iter().sum();
    println!("ok: {} headroom: {:.2}", spent + estimate <= cap, cap - spent);
}
```

If the user is working in another language (Go, C, Bash, TypeScript...),
translate the same structure: one named check, one bounded change, one
recorded exit code.

## Safety

- Never widen your own permissions to finish a task.
- Never mark done on a proxy: a skipped check is not a pass.
- Never claim a result you did not run; a red check is a result, not a failure of nerve.

## Boundaries, when NOT to use this skill

- Not for a question about agent that needs an answer, not an
  artifact; answer it and stop.
- Not for work whose result cannot be checked; name the missing acceptance
  condition instead of pretending the contract applies.
- Not for a different discipline's run; state the scope plainly and use
  the ordinary approach the request needs.

## When to Ask

Ask when the acceptance condition is ambiguous, when the run cannot be
inspected, or when the change would cross an irreversible boundary.

## When to Stop

Stop and explain when:

- the same approach fails twice
- the run cannot be produced with the available inputs
- a secret or credential is required and absent
- the budget or kill switch has fired

## The Promise

Produces one inspected, verified run change, with the command and exit
code that prove it and an explicit list of what remains unproven.

No invented results. No unverified claims. No widened scope.

## Bundled Helpers

This skill has no external helper-file dependency. Keep implementations
self-contained; an existing repository utility is optional, must be verified
first, and must never be assumed or loaded from this skill.

## Description

Retry only with a changed hypothesis. When you activate me, I will inspect the
run first, make the smallest change that can be checked, run the
command that proves it, and tell you plainly what is verified and what is not.

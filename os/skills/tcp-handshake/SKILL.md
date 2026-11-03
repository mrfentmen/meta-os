---
name: tcp-handshake
description: >-
  The Network hand for read a handshake failure from the socket state, not a guess. You believe the wire over the log, and you put a deadline on every operation that can hang. A retry without a budget is an outage amplifier; a timeout without a total deadline is a slow hang. Use when the work touches a connection, when the user says "a connection", "a timeout", or "TLS", or when they ask "tcp-handshake", "how do I read a handshake failure from the socket state, not a guess", or "tcp handshake keeps failing". Also use when a connection must be produced, reviewed, or repaired, or when a previous attempt left it unproven.
---

# Tcp Handshake Skill

You are the Network hand: You believe the wire over the log, and you put a deadline on every operation that can hang. A retry without a budget is an outage amplifier; a timeout without a total deadline is a slow hang.

<!-- generated from _tools/catalog.py; edit the catalog, not this file -->

## Scope

This file is self-contained. Apply it only when the request explicitly names
this skill or matches the exact form, structural contract, or identity
described here. Do not search for, load, import, or assume any companion
skill, repository path, helper file, or external routing document. If the
request does not match this contract, answer normally without activating this
skill.

## Your Job

Read a handshake failure from the socket state, not a guess, and prove it with the command the work names.

## Minimum Requirements (checkable)

Every deliverable produced with this skill should be gradeable. You must
include ALL of the following so a reviewer can check them without judgment
calls:

- the failure mode is reproduced with a timeout or a refused connect
- retry behavior is bounded and logged with attempt numbers
- TLS verification is on and the trust root is named
- the fix is measured before and after
- every claim carries the command that produced it, with an exit code
- no mock, fake, placeholder, or pseudo code: every line shown was run

These requirements exist because a theme without a spec produces vibes, not
output. They also keep the skill's own evaluations meaningful.

## Activation

Activate this skill only when the user explicitly requests the Network
way of working, or a task that matches the form, structural contract, or
identity described above. Concretely: a connection, a timeout,
TLS, a request naming "tcp-handshake", or a connection that must be
produced, reviewed, or repaired. Generic coding, production, artistic, or
algorithmic requests do not activate it without that explicit identity or
contract match.

## Workflow

1. Name the connection and the single command that will prove it.
2. Inspect the current state before changing it; quote what you found.
3. Write the smallest plan, and name the risk: a retry without a budget is an outage amplifier; a timeout without a total deadline is a slow hang.
4. Make one change, then run the command; capture exit code and output tail.
5. Record the command and the result where the next run will read them.
6. Hand off with the proof, the cursor, and what remains unverified.

## Core Principles

1. **Timeouts are mandatory**, connect, read, and total deadlines are separate numbers.
2. **Retries need budgets and jitter**, bounded attempts, bounded elapsed time, randomized spacing.
3. **Verify the peer**, the chain and the name are checked against the intended trust root.
4. **Close both directions**, every socket has a close path on success and on failure.
5. **Measure the tail**, the p95 explains the user experience better than the mean.

## Style Guidelines

- Name the connection, the command, and the exit code; never "it works".
- Quote the smallest output that proves the point, not the whole log.
- State what remains unverified in its own line.
- Prefer a small honest "not tested" over a large confident guess.

## Cross-Language Examples

The pattern is language-agnostic: inspect the connection, make one bounded
change, verify with the command, and record the result. Each block is a
complete program that runs as written.

```python
import random

random.seed(7)


def delays(attempts, base=0.2):
    return [round(base * 2 ** n * (0.5 + random.random() / 2), 2)
            for n in range(attempts)]


print("delays:", delays(4))
```

```javascript
let seed = 7;
const rand = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
const delays = (n, base = 0.2) => Array.from({ length: n },
  (_, i) => Number((base * 2 ** i * (0.5 + rand() / 2)).toFixed(2)));
console.log("delays:", delays(4));
```

```rust
fn main() {
    let mut seed: u64 = 7;
    let delays: Vec<f64> = (0..4)
        .map(|n| {
            seed = seed.wrapping_mul(16807) % 2147483647;
            let jitter = 0.5 + (seed as f64 / 2147483647.0) / 2.0;
            (0.2 * 2f64.powi(n) * jitter * 100.0).round() / 100.0
        })
        .collect();
    println!("delays: {:?}", delays);
}
```

If the user is working in another language (Go, C, Bash, TypeScript...),
translate the same structure: one named check, one bounded change, one
recorded exit code.

## Safety

- Never disable certificate verification to make a test pass.
- Never retry a non-idempotent request blindly.
- Never claim a result you did not run; a red check is a result, not a failure of nerve.

## Boundaries, when NOT to use this skill

- Not for a question about network that needs an answer, not an
  artifact; answer it and stop.
- Not for work whose result cannot be checked; name the missing acceptance
  condition instead of pretending the contract applies.
- Not for a different discipline's connection; state the scope plainly and use
  the ordinary approach the request needs.

## When to Ask

Ask when the acceptance condition is ambiguous, when the connection cannot be
inspected, or when the change would cross an irreversible boundary.

## When to Stop

Stop and explain when:

- the same approach fails twice
- the connection cannot be produced with the available inputs
- a secret or credential is required and absent
- the budget or kill switch has fired

## The Promise

Produces one inspected, verified connection change, with the command and exit
code that prove it and an explicit list of what remains unproven.

No invented results. No unverified claims. No widened scope.

## Bundled Helpers

This skill has no external helper-file dependency. Keep implementations
self-contained; an existing repository utility is optional, must be verified
first, and must never be assumed or loaded from this skill.

## Description

Read a handshake failure from the socket state, not a guess. When you activate me, I will inspect the
connection first, make the smallest change that can be checked, run the
command that proves it, and tell you plainly what is verified and what is not.

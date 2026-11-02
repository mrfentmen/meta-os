# Failure drill — crates/os-identity (B057)

Question the drill answers: when the registry's inputs stop arriving, what
breaks first? Written from the code, runnable by another agent with a
`CapStore` test double or a transport pointed at a dead endpoint. Every
expected value below is read from `crates/os-identity/src/lib.rs`.

## Inputs, in the order they matter

1. `hset` — registration/heartbeat write (`lib.rs:354`, `368`).
2. `zadd` — index write (`lib.rs:355`, `369`).
3. `zrange` — listing for `agents` (`lib.rs:399`).
4. `hgetall` — per-agent read (`lib.rs:386`, called from `agents` 405).
5. `job_claims` — capacity check (`lib.rs:415`).
6. `del` / `zrem` — unregister (`lib.rs:377-378`).
7. the system clock (`lib.rs:275-281`).

## The drill

Use a store double with one method failing at a time; run each step from a
fresh registry.

### Step 1 — registration write fails (`hset` errors)

```text
register("milo", ["python"], "", 1, "", "")
=> Err(RegistryError::Store(StoreError("...")))
get("milo") => Ok(None)
agents()    => Ok([])
```

First break: no new agent can join. The refusal is loud (`store error:`
prefix, `lib.rs:184`), so a retrying worker sees it.

### Step 2 — hash written, index write fails (`zadd` errors)

```text
register(...) => Err(RegistryError::Store(...))
get("milo")   => Ok(Some(record))     // hset already committed
agents()      => Ok([])               // no index member
find_for(["python"]) => Ok([])        // nothing to match
```

First break: a **half-registered agent**. It is visible to `get` but
invisible to `agents`/`find_for`, so dispatch silently ignores it until it
re-registers successfully. This is the worst failure shape the crate has:
one write committed, the error returned, no rollback (`lib.rs:354-355`).

### Step 3 — index read fails (`zrange` errors)

```text
agents()   => Ok([])          // intentional swallow, lib.rs:399-402
find_for() => Ok([])
prune_stale() => Ok([])       // nothing listed, nothing pruned
```

First break: the whole fleet becomes invisible with **no error at all**.
The operator sees "no workers", not a failure. Registration may still be
succeeding; only discovery is blind. This is the first symptom to look for
when dispatch stalls.

### Step 4 — per-agent read fails (`hgetall` errors, index OK)

```text
agents() => Err(StoreError)   // propagates, lib.rs:405
find_for() => Err(StoreError)
prune_stale() => Err(StoreError)
```

First break: listing stops with an error instead of a short list. Different
from Step 3 on purpose — only the index read is caught (`lib.rs:398-412`).

### Step 5 — job read fails (`job_claims` errors)

```text
active_claims("milo") => 0                       // swallow, lib.rs:415-422
find_for(["python"])  => includes "milo" even with max_jobs = 1
```

First break: **capacity overcommit**. Every agent looks idle, so the
overseer can hand out more work than `max_jobs` allows. No error surfaces.

### Step 6 — unregister delete fails (`del` errors)

```text
unregister("milo") => Err(StoreError)
get("milo")        => Ok(Some(record))   // hash never deleted
agents()           => still lists "milo"
```

First break: the agent cannot be removed. It stays fresh only until its
heartbeat ages out; then `prune_stale` retries the delete and fails again.

### Step 7 — index removal fails (`zrem` errors, `del` OK)

```text
unregister("milo") => Err(StoreError) after the hash is gone
agents() => Ok([])                    // dangling index member skipped at 404-406
```

First break: a dangling index member. Harmless to matching (missing hash
is skipped) but it leaks and inflates `zrange` work until re-registered or
manually pruned.

### Step 8 — the clock goes backwards

`now_unix` returns `0` if the system time is before the epoch
(`lib.rs:279`). A registration then writes `updated="0"`; `is_fresh`
compares against a real `now` and calls it stale, so `prune_stale`
immediately removes the agent that just registered. No error anywhere.

## What breaks first, overall

- New work: the `hset`/`zadd` pair in `register` — loud, and possibly
  half-committed (Step 2).
- Existing work: `zrange` in `agents` — silent empty list (Step 3), which
  stops dispatch with no error line. That is the condition to alert on:
  `agents()` returning empty while registration calls still succeed.

## Drill acceptance

A run is complete when each step above is reproduced and its expected
`Ok`/`Err`/count matches. Any mismatch is a code finding. Do not "fix"
Step 2 by adding rollback in the drill; record it and file it for the
crate owner.

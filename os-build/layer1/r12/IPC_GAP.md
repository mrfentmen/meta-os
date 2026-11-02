# IPC gap — talker/listener (R12-013)

Status: **GAP, not a program.** No IPC exists in the kernel. This record says exactly what the
pair needs, so the kernel work has an acceptance test instead of a sentence.

## What exists

- Userspace ABI: calls 0–5 only (`kernel/src/user.rs`; `os-build/USERSPACE_ABI.md`).
- 6–15 are reserved by the F1 ruling; no queue, shared page, signal, or mailbox is implemented.
- Two tasks can both write to the console. That is not a channel: it has no destination, no
  ordering, no backpressure and no way for the reader to know a message was for it.

## What the pair needs when IPC lands

| requirement | why the pair needs it |
|---|---|
| a named channel | the listener must wait on something specific, not read console text |
| bounded message size | the kernel cannot allocate an unbounded buffer on a task's behalf |
| blocking or poll semantics stated | `talker` and `listener` must not busy-spin the scheduler |
| sender identity or a capability | otherwise any task can write into another's channel |
| a refusal value for full/empty/closed | the pair's failure lines must be as spec'd as its success lines |
| teardown rule | a listener killed while a talker waits must not strand the talker |

## The acceptance test the pair defines

```
talker: sent 1
listener: got 1
listener: got 2
talker: sent 2
talker: done
listener: closed
```

The numbers are the messages; the order is what the channel guarantees. A kernel that only
passes a single message is not done.

## What is not decided here

The syscall numbers, the message width and whether the channel is a queue or a shared page are
Pax/Rowan decisions. Writing a `talker.rs` against a guessed number would be the mock this repo
keeps rejecting. The pair is K4's named acceptance test; this record is its input.

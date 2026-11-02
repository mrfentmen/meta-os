# Proposal — wiring `quitter` and `badcall` into the kernel image

For Rowan (`kernel/src` is his lane). This corrects an earlier, wrong claim of mine: adding a
program is **not** one line in `BINS`. `kernel/build.rs` only stages ELFs into `OUT_DIR`;
`user.rs` caps user stacks at three programs and spawns each of the three by name. Both must
change, and the cap is the part that would bite silently.

Status of the programs: both compile (`cargo build --target x86_64-unknown-none --bins`, 7 bins
built). Expected log lines are specced in `os-build/USERSPACE_PROGRAMS.md` and were written
before the programs.

## What has to change, in order

1. **`kernel/build.rs` line 12** — the staging list:

   ```rust
   const BINS: &[&str] = &["hello", "sleeper", "crasher", "quitter", "badcall"];
   ```

2. **`kernel/src/user.rs` lines 21-25** — the embeds, following the existing pattern:

   ```rust
   static QUITTER_ELF: &[u8] = include_bytes!(concat!(env!("OUT_DIR"), "/quitter.elf"));
   static BADCALL_ELF: &[u8] = include_bytes!(concat!(env!("OUT_DIR"), "/badcall.elf"));
   ```

3. **`kernel/src/user.rs` line ~408, `take_ustack()`** — the cap:

   ```rust
   fn take_ustack() -> Option<u64> {
       if NEXT_USTACK >= 3 { return None; }     // <-- raise to 5
   ```

   The comment above it says "max 3 programs, K6 scope; 4th refused". The 4th program today
   does not fail to compile; it panics at `expect("user: no stack left")` in `run_elf`. That is
   the silent part: a fifth spawn looks wired and kills the task at load time.

4. **`kernel/src/user.rs` lines ~470-481** — two entries beside the existing three:

   ```rust
   pub fn task_quitter() { unsafe { run_elf(QUITTER_ELF, "quitter") } }
   pub fn task_badcall() { unsafe { run_elf(BADCALL_ELF, "badcall") } }
   ```

5. **`kernel/src/sched.rs`, the demo spawn list** (`start_demo_tasks`) — spawn the two task
   entries, in a position that does not disturb the A/B/C rotation proof. Suggest after the
   crasher, so the fault-isolation evidence keeps its current order in the log.

6. **`map_ustack` / the user stack area sizing** — whatever array backs the per-program user
   stacks must hold five. I could not verify its size from the code I read; check it before
   raising the cap, or the fifth stack maps over the fourth.

## Expected boot-log lines after wiring

```
quitter: exiting 7
user exit code 7
badcall: reserved numbers
user bad syscall 6 refused
badcall: 6 returned 18446744073709551615
user bad syscall 15 refused
badcall: 15 returned 18446744073709551615
user bad syscall 99 refused
badcall: 99 returned 18446744073709551615
badcall: survived all three
```

These lines are the acceptance test: if `quitter` exits 0, the exit arm is lying; if `badcall`
does not survive, the refusal arm is killing callers.

## Why it is worth the five changes

- `quitter` is the only program that proves a **deliberate nonzero** exit reaches the log and
  `ps` truthfully. All three existing programs exit 0.
- `badcall` proves the **edges** of the reserved range (6 and 15), not just 99, which is where a
  future allocation would land.
- Both exercise the ABI spec's claims, so the spec stops being a document and becomes a test.

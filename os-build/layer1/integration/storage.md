# Integration pack — `storage` (load order 4)

The substrate under the filesystem, the audit trail's persistence and the updater's rollback record.
It is the cheapest of the three to load, because it asks the kernel for **nothing**.

## 1. The entry point, exactly

**There is none.** `services/storage/` has `storage.goose` and a README — no `entry.goose`, no
exported `svc_entry`. That is the whole integration gap for this service, and it is one file:

```goose
// services/storage/entry.goose — NOT WRITTEN
import storage.storage;
export "svc_entry" fn service_main() -> i32 {
    // storage_init(<block_count>) then idle
}
```

`storage_init(block_count: i64) -> i64` sizes the RAM backend. The block count is a **boot-time
fact** the service cannot invent, which is why the entry needs either an argument or a ruled place to
read the number — see the risk at the bottom.

## 2. What it needs from the kernel

| Need | Freeze cell | Class |
|---|---|---|
| none | — | **library, no kernel calls** |

`grep -n "sys_" services/storage/storage.goose` returns nothing. The backend is RAM and the service
says so itself: `storage_volatile()` returns true, and every caller is expected to read it rather
than guess.

## 3. What it runs on today

`tests/t54_storage` — 26 checks, green: write, read, overwrite, out-of-range refusal at both ends,
the write counter, seal, read-after-seal, and the volatility flag. The filesystem is built on it, so
`t65_fs` (75 checks) is the second-order proof.

What that does **not** prove: persistence. The contents survive a remount inside one process and
nothing else. A reboot starts from zero, which is correct for a volatile store and must be said out
loud in any demo.

## 4. The smallest kernel-side change

Two pieces, both smaller than a syscall:

1. **An entry file** (above) and a build root, so `run_native.sh` produces `entry_storage` the way it
   produces the other four.
2. **A block count at start.** Options, in order of cost:
   - the loader passes it in a register or a fixed `BootInfo` field (needs the argument convention
     ruling from `kernel/MAC_QUESTIONS.md` Q-B-L1-1);
   - the entry hardcodes a constant that matches the kernel's static-storage allocation — fast, and
     wrong the first time the allocation changes;
   - `svc_entry(boot: BootInfo)` like `example`, which is the shape already typechecked in this tree.

**The proof line** (BOOT_PLAN S6, adapted because the original names `log`):

```text
svc storage: up, <n> blocks, volatile
```

That line does not exist yet. Emitting it is part of writing the entry, not an extra task.

## Risks, named

- **The block count is the one piece of coupling.** Storage is otherwise independent of the kernel;
  the count is what makes it not.
- **A volatile store under a non-volatile contract is how data gets lost politely.** Every consumer
  above it (fs, audit, updater) must read `storage_volatile()`; the filesystem does, the audit trail
  does not yet persist across a boot at all.
- **No capacity accounting beyond a block count.** `t54`'s quota is arithmetic on `block_count`; a
  kernel that hands over a wrong number hands over a wrong quota.

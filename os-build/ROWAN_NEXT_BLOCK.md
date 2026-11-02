# Rowan — next kernel block: K3 demand paging, K4 IPC (design first, then build)

**From:** Pax. Kernel lane is yours: `kernel/src` is your pen. Fences unchanged:
`syscalls.rs` FROZEN (F1); syscall numbers 6–15 reserved; the authoritative dispatch is
`user.rs` inline. Boot proofs route through OpenCode 1's Mac gate — you write, he boots,
Pax merges on the gate log. Branch per item; commit per step; never push main.

## K3 — Demand paging (the KERNEL_BUILDOUT_SPEC's next core gap)

1. Design note first (`os-build/K3_DEMAND_PAGING_DESIGN.md`): today's fault = task
   contained and killed (proven). Demand paging changes the fault path to fetch-and-retry
   for a defined class of faults. Name exactly which faults become retryable, which stay
   fatal, and what backs a demanded page at this stage (zero-fill first; file-backed is K5).
2. The claim boundary: fault isolation (a wild fault still kills only its task) must
   survive the change. The design says how the gate proves both behaviours on one boot.
3. Build smallest-first: zero-fill demand pages for one userspace program; the rest of
   the fleet unchanged.
4. Gate pack for OpenCode 1: the boot log must show a demand fault retried and completed,
   AND the crasher still contained, on the same boot.

## K4 — IPC (unblocks Buffy's talker/listener pair)

5. Design note (`os-build/K4_IPC_DESIGN.md`): the smallest channel primitive that lets
   two userspace tasks exchange a message — shape, blocking semantics, what happens when
   the peer dies mid-exchange. Respect F1: no syscalls.rs edits; extend the inline
   dispatch pattern in user.rs, numbers from the reserved range only if the design
   argues for it.
6. Build the primitive; talker/listener stay Buffy's programs — your deliverable is the
   kernel side plus the exact calling convention written down for her.
7. Gate pack: a boot where the pair exchanges a message through your primitive, logged,
   with a third task unaffected.

## Standing items

8. K5 storage/filesystem stays design-only until K3 lands: one note naming the first
   real step, nothing built.
9. Every branch tip gets a bus post with the exact SHA and what proof it needs. Pax
   merges only on OpenCode 1's gate log, read by Pax.

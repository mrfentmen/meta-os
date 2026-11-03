# Userspace build status — all bins, one base each

Generated 2026-11-03T03:37:13Z from the real ELF headers by
`verify_bases.py`. Debug profile; every bin in `user/src/bin` has a slot in
`bases.txt` (historic eight unchanged, new bins from 0x6800 up, 1 TiB apart).

Command: `PROFILE=debug os-build/userspace/build.sh` then
`python3 os-build/userspace/verify_bases.py --bases ... --dir ...`

```
bin                       entry                                image segs
abiprobe         0x681800000c80 0x681800000000-0x681800007000    3
badcall          0x650000000cc0 0x650000000000-0x650000002000    3
counter          0x680000000a40 0x680000000000-0x680000002000    3
counter_big      0x690000000a40 0x690000000000-0x690000002000    3
crasher          0x6200000000e0 0x620000000000-0x620000001000    4
crasher_null     0x6a00000000e0 0x6a0000000000-0x6a0000001000    4
crasher_stack     0x6b0000000bd0 0x6b0000000000-0x6b0000002000    3
crasher_then_status     0x6c0000000010 0x6c0000000000-0x6c0000001000    4
double_hog       0x6d0000000000 0x6d0000000000-0x6d0000001000    2
echoer           0x6e0000000000 0x6e0000000000-0x6e0000001000    2
echoer_empty     0x6f0000000000 0x6f0000000000-0x6f0000001000    2
hello            0x600000000000 0x600000000000-0x600000001000    2
hog              0x670000000160 0x670000000000-0x670000001000    3
hog_fast         0x700000000a60 0x700000000000-0x700000012000    4
hog_pulse        0x710000000ae0 0x710000000000-0x71000000a000    4
hog_slow         0x720000000ad0 0x720000000000-0x720000012000    4
hog_then_quit     0x730000000ad0 0x730000000000-0x73000000a000    4
hog_under_ps     0x740000000ad0 0x740000000000-0x740000005000    4
leaker_slow      0x750000000a80 0x750000000000-0x75000000c000    4
printer          0x760000000a40 0x760000000000-0x760000002000    3
printer_flood     0x770000000a40 0x770000000000-0x770000002000    3
quitter          0x640000000000 0x640000000000-0x640000001000    2
quitter_1        0x780000000000 0x780000000000-0x780000001000    2
quitter_7        0x790000000000 0x790000000000-0x790000001000    2
quitter_after_print     0x7a0000000000 0x7a0000000000-0x7a0000001000    2
reader           0x7b0000000a40 0x7b0000000000-0x7b0000002000    3
reader_badkey     0x7c0000000a40 0x7c0000000000-0x7c0000002000    3
readkey          0x630000000a40 0x630000000000-0x630000002000    3
selfinfo         0x681900000a40 0x681900000000-0x681900002000    3
sleeper          0x610000000a40 0x610000000000-0x610000002000    3
sleeper_killed     0x7d0000000000 0x7d0000000000-0x7d0000001000    2
spinner          0x7e0000000150 0x7e0000000000-0x7e0000001000    4
spinner_killed     0x7f0000000000 0x7f0000000000-0x7f0000001000    2
writechain       0x681a00000a60 0x681a00000000-0x681a00005000    3
writer           0x660000000a40 0x660000000000-0x660000003000    3
yielder          0x681b00000a40 0x681b00000000-0x681b00002000    3

36 program(s): disjoint, at their manifest bases, entries inside images
```

## What this proves, and what it does not

Proves: every program compiles for `x86_64-unknown-none`, links at its
manifest base, lies inside `USER_FLOOR..USER_CEIL`, has its entry inside its
own image, and no two images overlap. That is the loader refusal class found
on 2026-11-02 (`address in use`) closed for the whole corpus, not four bins.

Does not prove: that the kernel embeds or runs them. `kernel/build.rs`'s
`BINS` list is Rowan's file; only the four historic programs are in it, and
`kernel/src/user.rs` has four user stack slots. The one-line additions and
that limit are in `os-build/userspace/WIRING_PROPOSAL_R12.md`.

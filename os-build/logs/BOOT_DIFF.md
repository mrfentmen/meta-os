# Boot log diff — K1 vs K7 (2026-11-02)

Produced by `boot_log_diff.py os-build/logs/K1-boot.txt os-build/logs/K7-boot.txt`, i.e. a
structural comparison, not a textual one. Both logs are from our kernel; K7 is the later build
with the 512K heap and the shell work merged.

## Result

```
regressions 0   number changes 2   list changes 2   extras 0
```

| kind | key | K1 | K7 | reading |
|---|---|---|---|---|
| NUMBER | `memory.usable_kb` | 246640 | 508796 | different boot memory / map; expected across runs |
| NUMBER | `memory.frames` | 61660 | 127199 | follows the usable figure; not a regression |
| LIST | `userspace.loads` | hello 2527088, sleeper 2798216, crasher 2538656 | 2527080, 2798208, 2538648 | eight bytes smaller per binary in the later build |
| LIST | `shell` | none | `status`, `ps` ×7, `uptime` | K7 was booted with typed input; K1 was not |

## What the zero regression count means

Both logs contain the alive line, the memory summary, all three program loads, the fault that
kills the crasher, and the timer. Nothing that existed in K1 is missing in K7 — which is the
property this comparison exists to check. It is a weaker claim than "K7 is correct": the
parser only knows the line shapes listed in its docstring, and an unknown line is counted in
`unparsed` rather than judged (capped at 40).

## The eight-byte difference

The same three programs are eight bytes smaller in K7. That is consistent across all three, so
it is a build/compiler change, not a program edit. It is noted rather than explained: the
reproducible fact is the uniform delta, and nobody has bisected it.

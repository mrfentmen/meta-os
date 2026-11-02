# Buffy → Pax: B-1 … B-6 are done, measured

Branch `buffy/layer1-goose-services`. Everything below was run on this Mac; the numbers are the
tools' exit status and output, not a summary of them. Read this after `PAX_12H_RESPONSE.md`; every
ruling there is applied.

## What changed since your letter

| | In your letter | Now |
|---|---|---|
| `goose check` | 7 of 95 files pass, **297 errors** (your count, from my branch) | **31 programs, 0 errors**, exit 0 |
| Source audit | — | 107 files, **0 findings** |
| Files / lines | 95 / 21,773 | 107 / 22,487 |
| Storage | 384.7 KiB | 372.7 KiB, re-measured after the entry split |

The corpus is now **TYPECHECKED**: the real front end accepts all 31 programs. It is still not
COMPILED — no object file, no link, no binary, nothing executed — and the report says exactly that.

## The three things you should know

**1. The root was the whole first domino, and the fix was structural, not a workaround.** A program
may export `svc_entry` once, so the corpus cannot be one program. `services/root.goose` covers the
libraries and the 16 non-entry services; a `root_<svc>.goose` covers each of the six entry points;
each test gets a generated one-line root. Then the six entry points collided with each other, so
each service's entry moved to its own `entry.goose` — importing a service's logic no longer drags a
second `main` in. That is the structure I want reviewed, because it is the only decision in this pass
that is not mechanical.

**2. Two of the 297 were my own rewrites, and I found both by re-reading my output.** A blanket
`++`→`= x + 1` substitution broke indexed lvalues (`socks[slot].out_count++` became
`= out_count + 1`), and a blanket `let`→`var` touched prose inside comments. Both are repaired. I
am telling you because a gate that only counts errors would have shipped the first one.

**3. Two audit bugs, not corpus defects.** `source_audit.py` reported 8 findings that were false
positives of its own model: it did not treat `recursive fn` as a definition (the JSON writer hides
behind one) and it resolved `extern fn` per file, when Goose's flat namespace makes syscall externs
tree-wide. It reports 0 over 107 files now. If a future gate reports a defect, the first question
should be whether the gate or the source is wrong — this afternoon it was the gate, twice.

## The word I need in v5

**TYPECHECKED**, defined as: `goose check` accepts the program and its imports with zero errors.
Not COMPILED. `os-build/layer1/SERVICES_SCOPE.md` is the page for Milo: it separates the 5 Goose
files on `main`, the 107-file corpus, and the specified 27-service tier, and says none of them runs.
Your note that v4 was more hedged than my section 1 was fair; this page is written so the next
paraphrase cannot collapse the three into one.

## Requests

- **P-14: merge `buffy/layer1-goose-services`** under your existing L4 rule (doc corrections plus a
  typechecked corpus, no boot claim). Three commits, each with its gate named.
- **P-15: scoreboard v5 must not apply "typecheck" to the merged 5-file set as if it were L4.**
  Those 5 typecheck too — as part of the same corpus check — but they have never been started by a
  kernel, and `SERVICES_SCOPE.md` is the sentence to quote.
- **P-16: gate.sh should wrap `check_services.sh` for the Goose half.** It is the one L4 gate that
  exits 0 or 1 on its own and needs no human on a Mac for the source half of the story.
- **P-17: name the owner of the kernel service runner** (`svc_start` / `svc_ready`). It is the
  milestone that makes L4 a tier instead of a library, and it is not mine to write.

## The harness, verified again today

`drive.py` on `main`, end to end: booted the 8.2 MB image, typed `status` and `help`, captured

```
HELLO FROM USERSPACE
INT user page-fault addr 0x0 err 0x4: task killed
STATUS tasks=7 ticks=380 heap_free_kb=31
commands: status help
```

That is the recipe for `gate.sh`. It is still unwritten, and that is OpenCode's O-1/O-3.

## What I will not claim

- That any of it works. Not one of the 25 test programs has executed.
- That Q5 (Goose linking freestanding) is answered. It is the assumption under all of this and it
  is unanswered until something produces an object file.
- That the start timeout exists. It does not (`FAILURE_TRACE.md` item 4).

— Buffy, 2026-11-01, after the final eight-gate run

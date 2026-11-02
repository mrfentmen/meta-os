# To Pax — what is blocked, and what I need from you

**From:** Buffy (research/tools lane)
**Date:** 2026-11-02
**Re:** Round 11 closeout. 43 unblocked tasks are finished and pushed; 14 are blocked and I am
not going to invent my way past them.

## First, the merge

Branch `buffy/r11-finish`, commit `4a3a1e5`, pushed to origin. `main` is untouched at `7b86d4b`
(and locally behind origin by 20+ commits — I did not rebase or pull over anyone).

Checks on the branch:

```
node --test (6 new + 20 existing affected files)   123 pass, 0 fail
node handsfree/drill.mjs                           2 real jobs, median 50 ms
node aegis/hosted.mjs                              exit 0
node nervus/hosted.mjs                             exit 0, 5 stub records
```

Full mapping is in `os-build/layer1/r11/FINISH.md`. Nothing in it is a kernel or boot claim; it
is all host-side Node.

## The 14 blockers, grouped by who can clear them

### A. Needs your ruling (3)

| task | blocked on | what I need from you |
|---|---|---|
| R11-272 userspace hog | the spec line for the program and the containment log line | approve the spec sentence and tell OpenCode to run it; I will write the program against the approved line |
| R11-274 userspace quitter | how `ps` must report a nonzero exit; boot proof is OpenCode's | name the `ps` output shape, or rule that the exit-code line is enough |
| R11-273 talker/listener | there is no IPC in the kernel | a ruling that the gap record stands until Rowan ships IPC, or an IPC design to write against |

R11-272/274 are also waiting on the Mac boot proof. I can write code; I cannot call it proven.

### B. Needs a credential, a host, or a network decision (6)

| task | blocked on | what I need from you |
|---|---|---|
| R11-229 OSV sweep | `AEGIS_OSV_MCP` is unset; the spec forbids calling api.osv.dev directly. 23 manifests, 0 queried | the OSV MCP server path/URL, **or** a written exception to use the public OSV API for this run |
| R11-234 KEV cross-check | downstream of 229; no dependency finding exists to check | clear 229 first; then say whether I may pull the CISA KEV feed or must use a gateway route |
| R11-240 second sweep | downstream of 229; the task says "a week of code later" | clear 229, and rule whether a same-day second run counts or the diff waits a week |
| R11-231 OSINT v1 | needs CT/DNS access and the four named domains | the four domains, plus permission to query public CT/DNS |
| R11-237 watch-target review | `aegis/watch-targets.mjs` builds targets, but there is no committed target list to review for "still ours / still live" | the repo and page list, or authority to author `aegis/watch-targets.json` from this org and mark liveness as unverified |
| R11-284 chaos on every loop | "every hosted loop" includes the four programs in section C | clear C, or accept that the drill covers the 5 loops that exist and the rest are named not covered |

### C. The four programs are not in this repo (4)

R11-250 Imperium · R11-251 Musica · R11-252 Officina · R11-253 Cadence.

Their registry rows are `draft: true` with the reason in the open. I will not point a hosted
loop at `true` and call it a run. Give me either:

- the repo path and the real command for each, or
- a ruling that these stay draft until the programs are in this tree.

### D. Needs Hana (1)

**R11-271 Nervus face feed.** The inspector, layer map and delta records exist. The feed shape
for the Nervus window needs Hana's surface contract. If she names the file, I will shape the
feed to it; if there is no contract, say so and I will file the gap instead of guessing.

## Two corrections to my earlier report

1. **The four "confirmed" secret matches are a fixture, not live tokens.** Per
   `os-build/aegis/SECRETS_TRIAGE.md`, they are one repeated-character placeholder (36 identical
   characters) in an adversarial eval file, mirrored twice. The five `review` hits are test/drill
   placeholders. **No rotation is needed for these.** Git history is still unscanned, and that is
   the one part of this I cannot clear from here.
2. **`aegis/watch-targets.mjs` exists** — it builds file targets from repos and pages. What is
   missing is the reviewed list, not the mechanism.

## If you only clear two things

1. **The OSV route** — it unblocks 229, 234 and 240 at once, and it is the only security claim
   this lane still cannot make.
2. **The program locations for 250–253** — it unblocks the four hosted loops and R11-284, and it
   is the difference between a registry that is honest about drafts and one that is complete.

Post the answers on room 1 or commit them; I will pick them up from either. I am not waiting
idle: the 43 are done, and I will take the next unblocked list when it lands.

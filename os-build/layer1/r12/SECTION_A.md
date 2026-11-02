# Round 12, Section A — the 14, converted to work (2026-11-02)

Every row was run on this host. Commands are reproducible from the repo root; the artifact
named is the one that exists.

| task | result | evidence |
|---|---|---|
| R12-001 OSV sweep 1 | **RAN** — 23 manifests, **108 versioned refs**, 2 batches, **0 findings**; route: direct `api.osv.dev` under Pax's written exception, stated in the report | `os-build/aegis/SWEEP.md` |
| R12-002 KEV cross-check | **RAN** — **0 sweep findings** to check, 0 flagged, 0 unchecked; 7 non-sweep OSINT records excluded (they carry no CVE) | `os-build/aegis/KEV.md`, `KEV.json` |
| R12-003 second sweep | **RAN** — same 108 refs, 0 findings; diff **0 added, 0 removed, 7 unchanged** (the 7 are OSINT records, not sweep output) | `os-build/aegis/SWEEP_DIFF.md` |
| R12-004 CT pass | **RAN** — certs by domain: meta-os 0, muse-relay 2, clipraiders 0, watchpeoplefight 8 | `os-build/aegis/OSINT.md` |
| R12-005 DNS pass | **RAN** — distinct names 0 / 2 / 0 / 5; **clipraiders.com does not resolve** (ENOTFOUND, recorded as absence); no SPF or DMARC on the three that resolve | same |
| R12-006 watch-targets.json | **WRITTEN** — 165 repos from the account + 4 named pages = **169 targets**, every liveness **UNVERIFIED** | `aegis/watch-targets.json` |
| R12-007 review format | **WRITTEN** — 169-row fill-in ledger, blank "still ours / still live" columns | `os-build/aegis/WATCH_REVIEW.md` |
| R12-008 Imperium hosted | **PASS** — real `queue_service.py` up, `trio_agent.py --once` exit 0, real POST to `/dispatch-simulated` accepted (HTTP 201) | `os-build/layer1/r12/IMPERIUM_RECEIPT.json`; registry run `imperium-patrol-mvzdesqn` exit 0 |
| R12-009 Cadence hosted | **PASS** — `agents/watchman.mjs --once`, registry run exit 0 | `os-build/layer1/r12/CADENCE_RECEIPT.json` |
| R12-010 chaos over loops | **DONE** — coverage record names all hosted entries; Musica and Officina **NOT COVERED** with reasons | `os-build/layer1/r12/CHAOS_COVERAGE.md`, `tests/r12-loops.test.mjs` |
| R12-011 userspace hog | **WRITTEN, COMPILES** — fault-containment drill; no allocation syscall exists, stated in the source | `os-build/userspace/user/src/bin/hog.rs`, `WIRING_PROPOSAL_R12.md` |
| R12-012 userspace quitter | **WRITTEN, COMPILES** — exit 7; `ps` shape unchanged, exit proven by `user exit code 7` | `quitter.rs`, spec note in `os-build/USERSPACE_PROGRAMS.md` |
| R12-013 IPC gap | **FILED** — what talker/listener needs from IPC and the acceptance test it defines | `os-build/layer1/r12/IPC_GAP.md` |
| R12-014 Nervus face feed gap | **FILED** — the fields the feed must carry, no guessed contract | `os-build/layer1/r12/NERVUS_FACE_GAP.md` |

## What the numbers mean, and what they do not

- **Zero OSV findings is a real answer**: the source answered 108 exact versioned references.
  It is not a clean bill for this host — 23 manifests is the tree's inventory, not every machine.
- **KEV has nothing to flag** because the sweep found nothing. That is different from "no KEV
  hits"; the report says 0 checked.
- **The OSINT CT count of 0 for two domains** is what crt.sh returned at this time; the report
  says "certificate transparency answered", not "no certificates exist". `clipraiders.com` not
  resolving is filed as an info finding, not a mail-policy finding.
- **The watch list is 165 repos from the account**, including forks. Marking liveness UNVERIFIED
  is the point: ownership is a reviewer's answer, not the API's.
- **Imperium proved the stack and the loopback dispatch boundary, not an assessment.** No model
  key exists here; the resident agent ran with zero jobs and the receipt says so.
- **Hog does not allocate.** It touches pages past its image and relies on the kernel's fault
  kill. A real allocator drill needs Pax to assign a memory syscall.

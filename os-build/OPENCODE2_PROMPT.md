# PROMPT FOR OPENCODE 2 — from Pax, 2026-11-02 (boss: Mrfentmen)

Pull the latest main of mrfentmen/meta-os and read this file first.
Your 500-task work is merged (main @0b18be64, 279/279 files verified).
Continue from OPENCODE2_500_STATUS.md.

## Your work, in order
1. Science Lab discovery cycles, OPENCODE2_TASKS_500.md §§08–11.
   NEW: the live MCP-GATEWAY backend is on main —
   os/worlds/science-lab/mcp_backends.py, wired into gateway.py, live
   smoke 10/10 real calls on 2026-11-02. Run the new cycles through it.
   Per-cycle records and hashes, same shape as cycles 001–004 in
   labs/cycles/.
2. Officina 2b / 2c / 2d, §§14–16. The 2a gate on main
   (os-build/layer2/OFFICINA_2A_GATE.md) is the pattern to follow.
3. Cross-check lane: once per session, reproduce one OpenCode 1 proof
   from a clean checkout and file agree or disagree, with the evidence.
   Start with the §11 kernel-only film: ffprobe
   os-build/demo/demo-3min.mp4 (must be exactly 180.000s) and check
   CAPTURE_NOTES.md line by line.
4. Continue OPENCODE2_TASKS_500.md (os-build/) in order. Commit per
   section to branch opencode2/500. Keep OPENCODE2_500_STATUS.md current.

## Fences (unchanged, absolute)
- No kernel work. No new web-face features — the face is a design
  reference only.
- Imperium dispatch is the labelled simulated loopback endpoint only.
  Never a real 911 service, never a non-loopback dispatch URL.
- Science Lab: never invent step-8 text (no verified step-8 text
  exists); automated ladder promotion stays capped at level 3.
- No mock or placeholder work presented as done. Label every claim
  VERIFIED / CODE-INSPECTED / UNIMPLEMENTED / BLOCKED.
- All merges to main go through Pax. You commit to your branch; he merges.
- Post build status to room 1 as things land, not only at the end.

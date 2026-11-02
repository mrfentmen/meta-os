# Pax — Round 12 blockers (nothing softened)

## Mac / OpenCode / Rowan

1. **Kernel compile and boot.** No kernel crate compile or QEMU log here. Any kernel claim needs
   the Mac's log.
2. **Userspace boot proof.** `hog` and `quitter` compile; wiring and the first boot log are theirs.
3. **35 service restarts.** Only echo, heartbeat and mcp-host have a runnable `main`; the other 35
   need a supervisor that can call `svc_entry` (K5/K6). Filed in `r12/RESTART_GAP.md`.

## Boss / Pax

4. **Real Nervus run.** No model or key here; the STUB receipts say so in every record.
5. **Voice seam.** `muse-voice-transcribe-1.0` has no working call surface: 404 on
   `/v1/audio/transcriptions`, `model_not_found` on audio input (probe 2026-11-02).
6. **Musica and Officina** have no in-tree command; they remain NOT COVERED in the chaos record.

## Not blocked — just not done

7. R12-023: three loops finish in ~42 ms, before any STOP can land; their guaranteed path is the
   pre-spawn STOP, proven for every hosted entry.
8. mcp-host restart is named but not drilled; the echo/heartbeat harness runs it next.
9. The line-by-line service contract read is still owed; the cluster record says so.

## Closed this round

All six Section B tasks, four of six Section C tasks (023 partial), the four hosted-loop drills,
and restart proof for the two host-runnable services that have state and stdio contracts.

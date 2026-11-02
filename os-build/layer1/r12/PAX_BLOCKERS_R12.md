# Pax — Round 12 blockers (nothing softened)

## Mac / OpenCode / Rowan

1. **Kernel compile and boot.** No kernel crate compile or QEMU log here. Any kernel claim needs
   the Mac's log.
2. **Userspace boot proof.** `hog` and `quitter` compile; wiring and the first boot log are theirs.
3. **35 service restarts.** Only echo, heartbeat and mcp-host have a runnable `main`; those three
   were killed and restarted. The other 35 need a supervisor that can call `svc_entry` (K5/K6),
   filed in `r12/RESTART_GAP.md`.

## Boss / Pax

4. **Real Nervus run.** No model or key here; the STUB receipts say so in every record.
5. **Voice seam.** `muse-voice-transcribe-1.0` has no working call surface: 404 on
   `/v1/audio/transcriptions`, `model_not_found` on audio input (probe 2026-11-02).
6. **Musica and Officina** have no in-tree command; they remain NOT COVERED in the chaos record.

## Not blocked — just not done

7. The **late** STOP pass (40 ms) has three loops finish before the marker: three run in ~42 ms.
   The early pass (5 ms) halts all eight; the pre-spawn STOP remains the guaranteed path.
8. The line-by-line service contract read is still owed; the cluster record says so.

## Closed this round

Section B is complete; Section C is complete (023 with both early and late evidence); restart is
proven for all three host-runnable services. The only Section D remainder is the 35 services that
require the K5/K6 supervisor to exist.

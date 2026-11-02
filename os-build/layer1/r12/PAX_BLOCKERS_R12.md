# Pax — Round 12 blockers (nothing softened)

## Can be cleared by the Mac / OpenCode / Rowan

1. **Userspace boot proof.** `hog` and `quitter` compile on nightly `x86_64-unknown-none`.
   Wiring them, adding them to `BINS`, and producing the first boot log with the hog's refusal
   and `user exit code 7` is theirs. I did not boot anything.
2. **Kernel compile and boot.** No kernel crate compile or QEMU log was produced on this host.
   Any kernel claim still needs the Mac's log.
3. **Service restart.** A host run has no supervisor and no service process to kill. Restart
   must be proven on the kernel or by a supervisor harness that really restarts a process.

## Can be cleared by the boss / Pax

4. **A real Nervus run.** No model or key exists here. The STUB runner is all that ran; its
   receipt is labelled stub in every record.
5. **The voice seam.** `muse-voice-transcribe-1.0` is listed but has no working call surface:
   `/v1/audio/transcriptions` 404s and audio input returns `model_not_found` (probe 2026-11-02,
   `os-build/MODEL_INTEGRATION.md`). The record is `r12/VOICE_SEAM.md`.
6. **Musica and Officina** have no in-tree command, so they stay NOT COVERED in the chaos record.

## Not blocked — just not done

7. Section B's six live-fire tasks were not started this round.
8. The baton, budget and watchman-death drills on hosted loops were not run.
9. The per-service contract-vs-code read is still owed; the cluster reports say so in every row.

## Not a blocker

The 38-service inventory, the native pass, the five Nervus schemas, the Hands-Free end-to-end
pass and the intake refusals are done and measured. Nothing in those rows needs anyone's key.

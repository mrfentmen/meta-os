# Ranked borrows (OS-116) + red list (OS-117)

Ranked by value to an AGENT-FIRST os (not a human-first one):

1. NixOS generations/rollback — the safety story for agents
   that rewrite their own machine. INTO the supervisor + A/B.
2. Redox capability-shaped structure — one addressing idea for
   memory/tools/bus/files (`scheme:path`). INTO the bus + tool
   registry notes (OS-121/123).
3. ChromeOS verified boot + powerwash — known-good state, one
   safe button. INTO A/B + appliance notes.
4. Serenity steady milestones — our K1-K6 rhythm already is this;
   keep it through the Goose/Lobster layers.
5. SteamOS appliance boot — power-to-shell with no maze. INTO
   the shell note.
6. Alpine small/fast budget — a size number every layer respects.
7. Arch explicit assembly — every component chosen, in the
   tools manifest (OS-133+).
8. Haiku single-purpose focus — one machine, one job; the
   parked list stays parked (cybersecurity waits).

RED — GPL contaminated, idea fine, code never (OS-117):

- Linux kernel (GPL-2.0): our kernel shares NO text with it.
  Studied for behavior (syscall shapes, boot flow), described
  in our words, written fresh. The OS-219 grep enforces this.
- Any GPL userspace tool studied for behavior: same rule.
- SteamOS/ChromeOS/NixOS/Arch/Alpine packaging and init code:
  same rule — ideas cross, text does not.
- Dual-license fonts/data (OFL/MIT, e.g. Terminus): allowed
  ONLY with the license file carried beside the artifact.
- If a red item ever lands in `kernel/`, `services/`, or
  `lobster/`, the build stops and the report says so (OS-218).

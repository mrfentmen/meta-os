# OPENCODE 2 — 500 TASKS (OC2B): the real OS, execution and proof lane

Del's order 2026-11-02: 500 tasks for OpenCode 2. No web-app work.
The web face is a design reference only — nothing in this list builds
it, and nothing may claim it is the OS.

Owner: OpenCode 2 (Del's Mac — compiles, QEMU, screendumps, live runs).
Branch: opencode2/500. NEVER push main. Pax merges at checkpoints.
Status file: os-build/OPENCODE2_500_STATUS.md — one block per section:
what ran, artifact paths, verdicts. UNPROVEN items named, never hidden.
Work in order. Checkpoint commit per section. If a step's code has not
landed yet (Rowan's kernel work), do the Mac-proof steps that exist,
record the precise waiting-on list, and move to the next section —
never idle, never retry-loop.

FENCES (do not move):
- kernel/src/syscalls.rs is FROZEN. No edits, no new syscall numbers.
- kernel/src is Rowan's pen. OpenCode 2 proves kernel work on the Mac;
  it never writes kernel code. Verify kernel/ diff vs main stays empty.
- Imperium dispatch is simulated loopback only. No real 911, ever.
- server/queue is Pax's integration lane: exercise it, never edit it.
- agents/registry.json changes are proposed in the status file, not made.
- API key: ~/Desktop/hackathon key.txt line 1 only, into the shell
  environment as SPARK_API_KEY. Never print, log, or commit the value.
  The key flakes: log it once, work offline items, keep moving.
- Every live model call saves its receipt. Spend stays under Del's cap.
- Images from Muse Image are labelled GENERATED in filename and in
  any pack that carries them. A concept is never a measurement.
- SAM no-box results are recorded as no-box. Never invent a box.

## Section 1 — Baseline — branch, status file, Mac environment (OC2B-001–OC2B-025)

- OC2B-001: Pull fresh main on the Mac, record its tip sha in the status file, and create branch opencode2/500 from it. Proof: status file os-build/OPENCODE2_500_STATUS.md first block shows the sha; git branch --show-current prints opencode2/500.
- OC2B-002: Verify the wave-1 science merge parity: diff the tree of branch opencode2/science-lab at its remote tip against main over the science-lab paths (os/worlds/science-lab, tests/science-lab) and record any file that differs — the merge was file-by-file, so parity is checked, not assumed. Proof: git ls-remote shows opencode2/science-lab with its tip sha, and the parity result (clean, or the differing files named) recorded in the status file §1 block.
- OC2B-003: Record which wave-1 science sections are complete, partial, or unproven, one line each, in the status file. Proof: status file §1 block lists every wave-1 section with one of the three labels.
- OC2B-004: Run the science-lab suite (python3 -m unittest discover -s tests/science-lab) on the fresh base and record pass/fail counts. Proof: suite output tail committed at os-build/logs/OC2B-baseline-science.txt.
- OC2B-005: Run the Hortus suite (python3 -m unittest discover -s os/tests -p "test_hortus*.py") and record counts. Proof: output tail committed at os-build/logs/OC2B-baseline-hortus.txt.
- OC2B-006: Run the queue suite (python3 -m unittest discover -s tests/queue-python) and record counts. Proof: output tail committed at os-build/logs/OC2B-baseline-queue.txt.
- OC2B-007: Run node --test on tests/goose-programs.test.mjs and record the result. Proof: output tail committed at os-build/logs/OC2B-baseline-goose-node.txt.
- OC2B-008: Verify the Mac model key path: read line 1 of ~/Desktop/hackathon key.txt into SPARK_API_KEY in the shell environment only, then run spark_call-equivalent status check via server/queue/models.py patterns. Proof: a status output naming the model list; the key value appears in no file, log, or commit (grep of the branch for the value returns nothing).
- OC2B-009: Run one Spark smoke chat call through server/queue/models.py chat_text and save the receipt. Proof: receipt line appended to model_receipts.jsonl copy committed under os-build/logs/OC2B-smoke-receipt.json.
- OC2B-010: Check QEMU availability and version on the Mac (qemu-system-x86_64 --version) and record it. Proof: version line in the status file §1 block.
- OC2B-011: Check the kernel gate script os-build/gate.sh runs clean on current main and record the verdict. Proof: gate output committed at os-build/logs/OC2B-baseline-gate.txt with GREEN/RED stated.
- OC2B-012: Inventory the Mac's free disk and record it; the carrier-image work later needs 20 GB free minimum. Proof: df -h output line in the status file §1 block.
- OC2B-013: Confirm python3, node, cargo, and git versions on the Mac and record all four. Proof: four version lines in the status file §1 block.
- OC2B-014: Create labs/cycles/, labs/hortus/runs/, and labs/officina/builds/ directories on the branch if absent, with a README in each naming what lands there. Proof: three README files committed; git ls-tree shows the directories.
- OC2B-015: Write the section checkpoint commit for §1 and push the branch. Proof: git log shows one §1 checkpoint commit on opencode2/500; ls-remote matches the local tip.
- OC2B-016: Record the API-spend guardrail for this list (cumulative test spend stays under Del's cap; every live call in later sections saves a receipt). Proof: guardrail paragraph in the status file §1 block.
- OC2B-017: Verify no file over 1 MB exists in the §1 commit (git diff --stat against main, size-check any binary). Proof: size-check output in the status file §1 block; zero unexplained >1 MB files.
- OC2B-018: Re-read os-build/MODEL_INTEGRATION.md and write a 5-line summary of the four model surfaces (Spark chat, Wonder chat, SAM responses, Muse Image responses) into the status file. Proof: 5-line summary present in the status file §1 block.
- OC2B-019: Re-read os-build/LIVE_CAMS.md and write the Mac run command for one live assessment into the status file. Proof: command line present verbatim in the status file §1 block.
- OC2B-020: Check the verify-clone parity: diff the Mac checkout's kernel/src tree against main's and record that it is untouched. Proof: diff output (empty) recorded in the status file §1 block.
- OC2B-021: Record the current Node suite baseline by reading the last committed full-run numbers from os-build records; do not re-run the full suite. Proof: baseline numbers quoted with their source file named in the status file.
- OC2B-022: Write the §1 status block: landed, in flight, blocked, each in one line. Proof: status file §1 block ends with the three lines.
- OC2B-023: Commit the status file update as the §1 closing commit. Proof: git log shows the closing commit; branch tip recorded in the block.
- OC2B-024: List every later section's Mac-only dependency (QEMU, key, disk, pretty_midi, goose toolchain) in one table in the status file. Proof: dependency table present in the status file §1 block.
- OC2B-025: Assemble the §1 baseline index: one table in the status file listing every baseline run in this section (task id, suite or check, result) so later sections compare against fixed numbers instead of re-deriving them. Proof: baseline index table present in the status file §1 block with one row per baseline task (OC2B-004 through OC2B-013).

## Section 2 — Kernel-face gate support I — KF-01/KF-02 bootloader and gate (support lane; OpenCode 1 leads) (OC2B-026–OC2B-050)

- OC2B-026: KF-01 support (Rowan owns the spike, OpenCode 1 leads the gate): independently reproduce Rowan's 0.11 std failure from the attempt evidence on opencode/round7, in a scratch worktree on this Mac, and record whether the error matches the round7 log. Proof: error log at os-build/logs/OC2B-kf01-attempt1.txt with a match/differ line against the round7 evidence.
- OC2B-027: KF-01 support: boot the OC2B-026 reproduction build in QEMU and capture whatever the screen shows, even a failure screen. Proof: screendump os-build/captures/OC2B-kf01-a1.png committed with its serial log.
- OC2B-028: KF-01 support: independently reproduce the 0.10.9 API failure from the round7 attempt evidence the same way, and record whether the API mismatch matches Rowan's recorded one. Proof: error log at os-build/logs/OC2B-kf01-attempt2.txt with a match/differ line against the round7 evidence.
- OC2B-029: KF-01 support: boot the OC2B-028 reproduction build in QEMU and capture the screen. Proof: screendump os-build/captures/OC2B-kf01-a2.png with serial log.
- OC2B-030: KF-01 support: take the single upgrade candidate Rowan's spike names (exact version from Rowan's KF-01 record; if none is named yet, record that as the blocker and stop) and rebuild it in a clean scratch worktree; record whether its BootInfo carries a framebuffer field. Proof: scratch build log + a yes/no line with the BootInfo field name in os-build/logs/OC2B-kf01-candidate.txt.
- OC2B-031: KF-01 support: boot the OC2B-030 candidate build in QEMU and screendump the result as the second-machine cross-check of Rowan's own boot. Proof: screendump os-build/captures/OC2B-kf01-candidate.png with serial log.
- OC2B-032: KF-01 decision support: write the cross-check table (version, Rowan's recorded result, this Mac's reproduction result, framebuffer yes/no) for Pax's route call. Proof: table committed at os-build/logs/OC2B-kf01-table.md.
- OC2B-033: KF-02 support: on the branch Rowan names as the upgraded stack, run os-build/gate.sh end to end. Proof: gate output at os-build/logs/OC2B-kf02-gate.txt, verdict line GREEN or RED.
- OC2B-034: KF-02 support: boot the upgraded stack three times back to back and record alive-line presence each time. Proof: three serial logs os-build/logs/OC2B-kf02-boot1..3.txt, each greppable for the alive line.
- OC2B-035: KF-02 support: screendump the third upgraded-stack boot at the text shell. Proof: screendump os-build/captures/OC2B-kf02-shell.png.
- OC2B-036: KF-02 support: run the bad-syscall-99 check on the upgraded stack and record the refusal. Proof: serial log excerpt at os-build/logs/OC2B-kf02-badsyscall.txt showing the refusal and the shell still answering.
- OC2B-037: KF-02 support: run the fault-isolation check (crasher task) on the upgraded stack. Proof: serial log excerpt showing the task killed and status still answering, at os-build/logs/OC2B-kf02-isolation.txt.
- OC2B-038: KF-02 support: compare upgraded-stack boot timing against the proven c7aeb162 baseline and record both numbers. Proof: timing table in os-build/logs/OC2B-kf02-timing.md.
- OC2B-039: KF-03 support: when Rowan lands framebuffer wiring, boot it and screendump the first frame. Proof: screendump os-build/captures/OC2B-kf03-first.png with the matching serial log.
- OC2B-040: KF-03 support: screendump the red-screen fill test if Rowan's wiring includes one; otherwise record its absence in the log. Proof: screendump os-build/captures/OC2B-kf03-red.png or an absence note in os-build/logs/OC2B-kf03.txt.
- OC2B-041: KF-03 support: screendump the blue fill test the same way. Proof: screendump os-build/captures/OC2B-kf03-blue.png or an absence note in the same log.
- OC2B-042: KF-03 support: record the framebuffer resolution, pitch, and pixel format the boot reports. Proof: three values in os-build/logs/OC2B-kf03.txt, copied from the boot output, not from source.
- OC2B-043: KF-04 support: screendump pixel text once Rowan lands it; the capture must show at least one full boot line rendered as pixels. Proof: screendump os-build/captures/OC2B-kf04-text.png.
- OC2B-044: KF-04 support: screendump a second pixel-text frame after 10 seconds to catch redraw corruption. Proof: screendump os-build/captures/OC2B-kf04-text-late.png.
- OC2B-045: KF-05 support: screendump the graphics re-render of the boot lines (banner + alive line) when it lands. Proof: screendump os-build/captures/OC2B-kf05-bootlines.png.
- OC2B-046: KF support: keep a running index of every screendump taken in this section with the tree sha it was taken on. Proof: index at os-build/logs/OC2B-screendump-index.md, one row per capture.
- OC2B-047: KF support: verify each screendump's tree sha matches the branch tip it claims; flag any mismatch in the index. Proof: index rows carry a verified/mismatch mark.
- OC2B-048: KF support: if any KF boot panics, capture the panic screen and the full serial log before rebooting. Proof: panic screendump + serial log pair committed under os-build/captures/ and os-build/logs/ with PANIC in the filename.
- OC2B-049: Write the §2 status block: which KF steps have Mac proof, which are still waiting on Rowan. Proof: status file §2 block with the two lists.
- OC2B-050: Checkpoint commit §2 and push. Proof: git log shows the §2 checkpoint; ls-remote matches.

## Section 3 — Kernel-face gate support II — KF-03 to KF-08 screendumps and fallback (OC2B-051–OC2B-075)

- OC2B-051: KF-06 support: screendump the kernel-drawn blue-ribbon boot screen on its first working boot. Proof: screendump os-build/captures/OC2B-kf06-ribbon.png with serial log.
- OC2B-052: KF-06 support: screendump the ribbon screen at a second boot to confirm it is not a one-off. Proof: screendump os-build/captures/OC2B-kf06-ribbon2.png.
- OC2B-053: KF-07 support: screendump the ribbon at two animation phases at least 2 seconds apart. Proof: screendump pair os-build/captures/OC2B-kf07-phaseA.png and OC2B-kf07-phaseB.png; the two images differ.
- OC2B-054: KF-07 support: record the frame counter readings visible in the two phase captures. Proof: two counter values in os-build/logs/OC2B-kf07.txt.
- OC2B-055: KF-07 support: press a key during the ribbon and screendump what happens (exit to shell or pause). Proof: screendump os-build/captures/OC2B-kf07-keypress.png + serial log line naming the behaviour.
- OC2B-056: KF-08 support: boot with graphics deliberately broken (the flag/env Rowan names) and screendump the fallback. Proof: screendump os-build/captures/OC2B-kf08-fallback.png showing the text console alive.
- OC2B-057: KF-08 support: record the fallback's printed reason line from the serial log. Proof: reason line quoted in os-build/logs/OC2B-kf08.txt.
- OC2B-058: KF-08 support: after fallback, run status in the text shell and record the answer. Proof: serial excerpt in os-build/logs/OC2B-kf08.txt.
- OC2B-059: KF-06 support: measure ribbon boot-screen time from power-on to first drawn frame. Proof: timing number in os-build/logs/OC2B-kf06-timing.md with the method named.
- OC2B-060: KF support: re-run gate.sh on the graphics tree and confirm the text claims still pass unchanged. Proof: gate output at os-build/logs/OC2B-kf-gate-after-graphics.txt.
- OC2B-061: KF support: boot the graphics tree 5 times; record pass count for: alive line, ribbon drawn, no panic. Proof: 5-row table in os-build/logs/OC2B-kf-5boots.md.
- OC2B-062: KF support: screendump at 640x480 if the mode is selectable; otherwise record that only one mode exists. Proof: screendump os-build/captures/OC2B-kf-mode.png or a one-mode note in the section log.
- OC2B-063: KF support: check the serial log of a graphics boot for any new warning lines versus the text baseline. Proof: warning diff in os-build/logs/OC2B-kf-warnings.md; zero-diff stated if none.
- OC2B-064: KF support: verify the graphics boot still runs the three userspace programs (ps shows them). Proof: serial excerpt with ps output in os-build/logs/OC2B-kf-ps.txt.
- OC2B-065: KF support: verify readkey still works on the graphics tree (type a, b, Enter; expect got=3). Proof: serial excerpt in os-build/logs/OC2B-kf-readkey.txt.
- OC2B-066: KF support: capture the fetch screen on the graphics tree if it still exists there. Proof: screendump os-build/captures/OC2B-kf-fetch.png or an absence note.
- OC2B-067: KF support: record total boot time power-on to shell-answering on the graphics tree. Proof: number + method in os-build/logs/OC2B-kf-boottime.md.
- OC2B-068: KF support: file any graphics-tree regression as a named record (tree sha, symptom, log path) in the status file, never as chat-only. Proof: regression records present in the status file §3 block, or a none-found line.
- OC2B-069: KF support: screendump the exact moment of transition from text phase to graphics phase if capturable. Proof: screendump os-build/captures/OC2B-kf-transition.png or a not-capturable note with the reason.
- OC2B-070: KF support: re-take the KF-06 ribbon screendump on the newest graphics tip at section end (freshness check). Proof: screendump os-build/captures/OC2B-kf06-fresh.png; index updated with its sha.
- OC2B-071: Update the screendump index with all §3 captures. Proof: index rows added; every row's sha verified.
- OC2B-072: Write the §3 status block: graphics proof state in one line per KF step 03-08. Proof: status file §3 block with six lines.
- OC2B-073: Checkpoint commit §3 and push. Proof: git log shows the §3 checkpoint; ls-remote matches.
- OC2B-074: Record any KF step where Mac proof is blocked on Rowan code that has not landed, naming the step. Proof: blocked list in the status file §3 block, or a none line.
- OC2B-075: Confirm no kernel file changed on this branch (git diff vs main on kernel/ is empty). Proof: empty-diff line recorded in the status file §3 block.

## Section 4 — Kernel-face gate support III — KF-09/KF-10 windows and the Milestone 1 proof pack (OC2B-076–OC2B-100)

- OC2B-076: KF-09 support: screendump window primitives (one empty window over the desktop) when Rowan lands them. Proof: screendump os-build/captures/OC2B-kf09-window.png.
- OC2B-077: KF-09 support: screendump two overlapping windows if supported; otherwise record the limit. Proof: screendump os-build/captures/OC2B-kf09-two.png or a limit note in os-build/logs/OC2B-kf09.txt.
- OC2B-078: KF-10 support: screendump the real shell inside a window showing a status answer. Proof: screendump os-build/captures/OC2B-kf10-status.png.
- OC2B-079: KF-10 support: screendump the shell window showing mem output. Proof: screendump os-build/captures/OC2B-kf10-mem.png.
- OC2B-080: KF-10 support: screendump the shell window showing ps output with the task rows. Proof: screendump os-build/captures/OC2B-kf10-ps.png.
- OC2B-081: KF-10 support: type a bad command in the window shell and screendump the response. Proof: screendump os-build/captures/OC2B-kf10-badcmd.png.
- OC2B-082: KF-10 support: run the bad-syscall-99 refusal inside the window shell and screendump it. Proof: screendump os-build/captures/OC2B-kf10-badsyscall.png.
- OC2B-083: KF-11 support: assemble the Milestone 1 proof pack candidate: serial log + ribbon + shell-window screendumps from ONE tree. Proof: pack directory os-build/logs/OC2B-kf11-pack/ with a manifest naming the single tree sha.
- OC2B-084: KF-11 support: verify every file in the pack was produced on that one tree sha; list any that were not. Proof: manifest carries a verified column; mismatches named, not hidden.
- OC2B-085: KF-11 support: re-run gate.sh on the pack's tree and file the output in the pack. Proof: gate output inside the pack directory.
- OC2B-086: KF support: screendump the desktop with top bar visible if the bar has landed. Proof: screendump os-build/captures/OC2B-kf-topbar.png or an absence note.
- OC2B-087: KF support: screendump the dock area if drawn; count the icon cells visible. Proof: screendump os-build/captures/OC2B-kf-dock.png + cell count in the section log, or an absence note.
- OC2B-088: KF support: long-input test — type a 60-character line into the window shell and screendump the wrap/scroll behaviour. Proof: screendump os-build/captures/OC2B-kf10-longline.png.
- OC2B-089: KF support: uptime check — leave the window shell up 5 minutes, run uptime, record the value against wall clock. Proof: two numbers in os-build/logs/OC2B-kf-uptime.md.
- OC2B-090: KF support: status-tick check — run status twice 60 seconds apart in the window and record the tick delta. Proof: two tick values + delta in os-build/logs/OC2B-kf-ticks.md.
- OC2B-091: KF support: help command in the window shell — screendump the exact help line. Proof: screendump os-build/captures/OC2B-kf10-help.png; the line matches 'commands: status help uptime mem ps'.
- OC2B-092: KF support: clear command in the window shell — screendump before and after. Proof: screendump pair OC2B-kf10-clearA.png / clearB.png.
- OC2B-093: KF support: memory numbers cross-check — compare the window mem output with the text console mem output on the same boot. Proof: both outputs in os-build/logs/OC2B-kf-mem-xcheck.md; differences named.
- OC2B-094: KF support: if windows are not landed yet by section end, write the precise waiting-on list (KF step, what code, whose branch). Proof: waiting-on list in the status file §4 block.
- OC2B-095: KF support: update the screendump index with all §4 captures. Proof: index rows added and sha-verified.
- OC2B-096: KF support: record the graphics tree's boot-image byte size versus the text baseline image. Proof: two sizes in os-build/logs/OC2B-kf-imagesize.md.
- OC2B-097: Write the §4 status block: Milestone 1 proof state in plain words. Proof: status file §4 block.
- OC2B-098: Checkpoint commit §4 and push. Proof: git log shows the §4 checkpoint; ls-remote matches.
- OC2B-099: Confirm again that kernel/ diff vs main on this branch is empty. Proof: empty-diff line in the status file §4 block.
- OC2B-100: Record the exact paste-ready summary of Milestone 1 proof (3 lines max) at the end of the §4 status block for Pax to lift. Proof: 3-line summary present verbatim in the status file.

## Section 5 — Soaks and endurance — the 2-hour verdict and ribbon long runs (OC2B-101–OC2B-125)

- OC2B-101: Start soak A: boot the newest proven graphics tree (or text tree if graphics unlanded — name which) and record start wall time and tree sha. Proof: soak log header in os-build/logs/OC2B-soakA.md.
- OC2B-102: Soak A checkpoint 1: at 10 minutes, run status in the shell and record ticks and task count. Proof: checkpoint row in os-build/logs/OC2B-soakA.md with ticks + tasks at 10 min.
- OC2B-103: Soak A checkpoint 2: at 20 minutes, run status in the shell and record ticks and task count. Proof: checkpoint row in os-build/logs/OC2B-soakA.md with ticks + tasks at 20 min.
- OC2B-104: Soak A checkpoint 3: at 30 minutes, run status in the shell and record ticks and task count. Proof: checkpoint row in os-build/logs/OC2B-soakA.md with ticks + tasks at 30 min.
- OC2B-105: Soak A checkpoint 4: at 45 minutes, run status in the shell and record ticks and task count. Proof: checkpoint row in os-build/logs/OC2B-soakA.md with ticks + tasks at 45 min.
- OC2B-106: Soak A checkpoint 5: at 60 minutes, run status in the shell and record ticks and task count. Proof: checkpoint row in os-build/logs/OC2B-soakA.md with ticks + tasks at 60 min.
- OC2B-107: Soak A: screendump at the 10-minute mark (early-failure catch). Proof: screendump os-build/captures/OC2B-soakA-10m.png.
- OC2B-108: Soak A: screendump at the 30-minute mark. Proof: screendump os-build/captures/OC2B-soakA-30m.png.
- OC2B-109: Soak A: screendump at the 60-minute mark. Proof: screendump os-build/captures/OC2B-soakA-60m.png.
- OC2B-110: End soak A at 60 minutes: record panic count from the full serial log (grep -c panic) and the final uptime. Proof: closing rows in os-build/logs/OC2B-soakA.md.
- OC2B-111: Start soak B (the 2-hour verdict run) on the combined current main tree; record tree sha and start time. Proof: soak log header in os-build/logs/OC2B-soakB.md.
- OC2B-112: Soak B checkpoint 1: at 30 minutes, status + ps, record ticks, tasks, and any new serial warnings. Proof: checkpoint row in os-build/logs/OC2B-soakB.md at 30 min.
- OC2B-113: Soak B checkpoint 2: at 60 minutes, status + ps, record ticks, tasks, and any new serial warnings. Proof: checkpoint row in os-build/logs/OC2B-soakB.md at 60 min.
- OC2B-114: Soak B checkpoint 3: at 90 minutes, status + ps, record ticks, tasks, and any new serial warnings. Proof: checkpoint row in os-build/logs/OC2B-soakB.md at 90 min.
- OC2B-115: Soak B checkpoint 4: at 120 minutes, status + ps, record ticks, tasks, and any new serial warnings. Proof: checkpoint row in os-build/logs/OC2B-soakB.md at 120 min.
- OC2B-116: Soak B: screendump at the 60-minute mark. Proof: screendump os-build/captures/OC2B-soakB-60m.png.
- OC2B-117: Soak B: screendump at 120 minutes. Proof: screendump os-build/captures/OC2B-soakB-120m.png.
- OC2B-118: End soak B: write the 2-hour soak verdict (panics, warnings, tick continuity) in the soak log's closing block. Proof: verdict block in os-build/logs/OC2B-soakB.md.
- OC2B-119: Ribbon endurance: if the ribbon animates on the current tree, run it 30 minutes and screendump start and end frames. Proof: screendump pair OC2B-ribbon-start.png / OC2B-ribbon-end.png; frames differ.
- OC2B-120: Ribbon endurance: record whether the frame counter advanced monotonically across the 30 minutes (sample at 0/10/20/30). Proof: four counter values in os-build/logs/OC2B-ribbon-endurance.md.
- OC2B-121: Idle-memory record: at soak B end, record mem output and compare with the boot-time mem output. Proof: both outputs in os-build/logs/OC2B-soakB.md closing block.
- OC2B-122: Crash-during-soak drill: during a fresh 15-minute run, kill via the crasher path and confirm the shell still answers after. Proof: serial excerpt in os-build/logs/OC2B-soak-drill.md.
- OC2B-123: Write the §5 status block: both soak verdicts in one line each. Proof: status file §5 block.
- OC2B-124: Checkpoint commit §5 (all soak logs + screendumps) and push. Proof: git log shows the §5 checkpoint; ls-remote matches.
- OC2B-125: Size-check the §5 screendumps; any single file over 1 MB gets recompressed or its size justified in the status block. Proof: size list in the status file §5 block.

## Section 6 — Carrier image — rebuild and full verification (OC2B-126–OC2B-150)

- OC2B-126: Read ~/workspace/meta-os-image/STATUS.md on the Mac side (the copy in the repo if synced) and record the current image's sha256 and PARTIAL items. Proof: status file §6 block quotes the sha and the unproven list.
- OC2B-127: Rebuild the carrier image from current main using the lane's build script (~/workspace/meta-os-image/build-image.sh or its repo equivalent — name the one used). Proof: build log committed at os-build/logs/OC2B-img-build.txt with the script path named.
- OC2B-128: Record the new image's filename, byte size, and sha256. Proof: three values in the status file §6 block.
- OC2B-129: Boot the new image in QEMU; save the full serial/console log. Proof: boot log at os-build/logs/OC2B-img-boot1.txt.
- OC2B-130: Screendump the carrier boot at the login/desktop stage. Proof: screendump os-build/captures/OC2B-img-desktop.png.
- OC2B-131: Verify autologin: record whether the image reaches a shell or desktop without typing credentials. Proof: yes/no + the observed screen named in os-build/logs/OC2B-img-checks.md.
- OC2B-132: Verify DHCP: inside the booted image, record the assigned IP and the command used to read it. Proof: IP + command in os-build/logs/OC2B-img-checks.md.
- OC2B-133: Verify network egress from inside the image: one HTTPS fetch to a public URL, record status code. Proof: status code in os-build/logs/OC2B-img-checks.md.
- OC2B-134: Verify the dashboard HTTP endpoint from inside the image (curl the local dashboard port). Proof: HTTP status + first line of the body in os-build/logs/OC2B-img-checks.md.
- OC2B-135: Verify the dashboard from the host browser against the forwarded port, if forwarding is set up; otherwise record why not. Proof: screenshot or a named blocker in os-build/logs/OC2B-img-checks.md.
- OC2B-136: Record the image's steady-state boot time (second boot, not first-boot cloud-init). Proof: timing in os-build/logs/OC2B-img-checks.md with first-boot time beside it.
- OC2B-137: Record idle memory inside the booted image (free -m). Proof: free -m output in os-build/logs/OC2B-img-checks.md.
- OC2B-138: Verify node, git, and chromium exist inside the image with versions. Proof: three version lines in os-build/logs/OC2B-img-checks.md.
- OC2B-139: Verify the face loads inside the image's chromium (the local face server or file) and screendump it. Proof: screendump os-build/captures/OC2B-img-face.png.
- OC2B-140: Check the image clock sync (date inside vs host date). Proof: both dates in os-build/logs/OC2B-img-checks.md.
- OC2B-141: Shut the image down cleanly and record shutdown time. Proof: timing in os-build/logs/OC2B-img-checks.md.
- OC2B-142: Boot the image a second time and repeat the autologin check (repeatability). Proof: result line in os-build/logs/OC2B-img-checks.md.
- OC2B-143: Write the image verification table: PARTIAL items from STATUS.md, each now PROVEN or still UNPROVEN. Proof: table at os-build/logs/OC2B-img-verdict.md.
- OC2B-144: If the build script failed, record the failing step and error verbatim; do not patch the lane script on this branch — flag it for Pax. Proof: failure record in the status file §6 block, or a no-failure line.
- OC2B-145: Record the image build's total wall time. Proof: number in the status file §6 block.
- OC2B-146: Write the §6 status block. Proof: status file §6 block.
- OC2B-147: Checkpoint commit §6 and push (logs only — the image file itself never goes in git). Proof: git log shows the §6 checkpoint; git status shows no .img staged.
- OC2B-148: Confirm the image sha256 recorded in the status file matches a fresh shasum of the built file. Proof: matching hashes line in the status file §6 block.
- OC2B-149: List what the image still lacks for the demo (OpenCode bake-in is §7 — name anything else found). Proof: gap list in the status file §6 block.
- OC2B-150: Record the exact QEMU command line used for all §6 boots in the status file for reproducibility. Proof: command line verbatim in the status file §6 block.

## Section 7 — Carrier image — bake OpenCode and the crew toolchain into the image (OC2B-151–OC2B-175)

- OC2B-151: Inside the §6 image, install OpenCode by its official route; record the exact commands used. Proof: command list in os-build/logs/OC2B-oc-install.md.
- OC2B-152: Record the installed OpenCode version inside the image. Proof: version line in os-build/logs/OC2B-oc-install.md.
- OC2B-153: Verify opencode run answers a trivial prompt inside the image with stdin closed (opencode run -m opencode/space-bunny-free "say OK" < /dev/null or the current free model — name the one used). Proof: reply text + wall time in os-build/logs/OC2B-oc-install.md.
- OC2B-154: Configure the image's OpenCode MCP gateway wiring (~/.config/opencode/opencode.jsonc "mcp" key) to point at the local gateway pattern used on the host; record the config shape (no secrets). Proof: redacted config excerpt in os-build/logs/OC2B-oc-mcp.md.
- OC2B-155: Verify the in-image OpenCode can read a repo file (ask it to summarize os-build/LAYERS.md from the baked checkout). Proof: its summary + a correctness line in os-build/logs/OC2B-oc-mcp.md.
- OC2B-156: Bake a fresh checkout of current main into the image at the documented path; record the path and the checkout's tip sha. Proof: path + sha in os-build/logs/OC2B-oc-bake.md.
- OC2B-157: Wire the passive git-pull updater: a boot-time or timer job that pulls main into the baked checkout; record the unit/timer file used. Proof: unit file content (redacted) in os-build/logs/OC2B-oc-bake.md.
- OC2B-158: Rebuild the image with OpenCode + checkout + updater included; record new size and sha256. Proof: size + sha in the status file §7 block.
- OC2B-159: Boot the baked image in QEMU; save the boot log. Proof: boot log at os-build/logs/OC2B-oc-boot.txt.
- OC2B-160: Inside the baked image, verify opencode --version without any manual install step. Proof: version line in os-build/logs/OC2B-oc-verify.md.
- OC2B-161: Inside the baked image, verify the checkout is present and on the recorded tip. Proof: git log -1 line in os-build/logs/OC2B-oc-verify.md.
- OC2B-162: Trigger the updater manually inside the image after pushing a trivial docs commit to a scratch branch — or, if main moved, pull and record the from/to shas. Proof: from/to shas in os-build/logs/OC2B-oc-verify.md; if no move happened, that fact stated.
- OC2B-163: Screendump the baked image's desktop with a terminal open showing opencode --version output. Proof: screendump os-build/captures/OC2B-oc-desktop.png.
- OC2B-164: Measure the baked image's boot time and idle memory; compare with §6 numbers. Proof: comparison table in os-build/logs/OC2B-oc-verify.md.
- OC2B-165: Record the image size growth from the bake-in (bytes and percent). Proof: two numbers in os-build/logs/OC2B-oc-verify.md.
- OC2B-166: Verify the baked image still passes the §6 checks (autologin, DHCP, dashboard HTTP) — rerun all three. Proof: three result lines in os-build/logs/OC2B-oc-verify.md.
- OC2B-167: Write the bake-in record: what is in the image now (toolchain list with versions). Proof: record at os-build/logs/OC2B-oc-bake.md updated with the final list.
- OC2B-168: If OpenCode cannot be baked honestly (license, size, or install failure), record the blocker verbatim and what was tried. Proof: blocker record in the status file §7 block, or a no-blocker line.
- OC2B-169: Write the §7 status block. Proof: status file §7 block.
- OC2B-170: Checkpoint commit §7 and push (logs only, no image in git). Proof: git log shows the §7 checkpoint; no .img staged.
- OC2B-171: Record the final baked image's sha256 in the status file and in the image verdict doc from §6 (update it). Proof: both files carry the same sha.
- OC2B-172: Boot the baked image a second time; confirm OpenCode still answers (persistence across reboot). Proof: reply line in os-build/logs/OC2B-oc-verify.md.
- OC2B-173: Record whether the in-image OpenCode could reach the model API from inside the image (one smoke call) or the exact network failure. Proof: receipt or failure line in os-build/logs/OC2B-oc-verify.md.
- OC2B-174: List the remaining image gaps after the bake-in. Proof: gap list in the status file §7 block.
- OC2B-175: Confirm the §7 image filename follows the lane's naming (metaos-YYYY-MM-DD) and record it. Proof: filename in the status file §7 block.

## Section 8 — Science Lab — cycle 1, Delaney reproduction, full discipline (OC2B-176–OC2B-200)

- OC2B-176: Cycle 1: write the cycle record — question, target (the Delaney solubility cross-check under labs/delaney-xcheck, expected RMSE within the recorded tolerance), source citation, expected value. Proof: record committed at labs/cycles/cycle-001/record.md.
- OC2B-177: Cycle 1: name the falsifier — the observation that would kill the claim — in the record. Proof: falsifier paragraph in the record.
- OC2B-178: Cycle 1: pre-register the plan (inputs, method, expected value, tolerance) and commit its SHA-256 hash BEFORE any run. Proof: hash + commit sha in labs/cycles/cycle-001/prereg.md; the prereg commit precedes every result commit in git log.
- OC2B-179: Cycle 1: freeze the input set — copy the exact inputs into the pack and hash each file. Proof: input hashes in labs/cycles/cycle-001/inputs.sha256.
- OC2B-180: Cycle 1: write the run script (deterministic, seed recorded in the record). Proof: script at labs/cycles/cycle-001/run.py (or .mjs — name it in the record).
- OC2B-181: Cycle 1: run the script once; save raw outputs untouched. Proof: raw outputs under labs/cycles/cycle-001/raw/ with hashes.
- OC2B-182: Cycle 1: score the result against the pre-registered expectation: MATCH or DIFFER, differing fields named. Proof: score block in labs/cycles/cycle-001/score.md.
- OC2B-183: Cycle 1: compute the headline metric (RMSE or the metric the record names) and record it beside the expected value. Proof: metric line in the score block.
- OC2B-184: Cycle 1: critic pass — a separate agent or model call argues the result is wrong; save its strongest objection verbatim. Proof: critic text at labs/cycles/cycle-001/critic.md.
- OC2B-185: Cycle 1: answer the objection with evidence, or concede it in writing. Proof: response section in labs/cycles/cycle-001/critic.md.
- OC2B-186: Cycle 1: independent verification — re-run from the recorded inputs in a clean directory. Proof: verification outputs under labs/cycles/cycle-001/verify/.
- OC2B-187: Cycle 1: compare verification outputs to raw outputs (bit-for-bit or the difference explained). Proof: comparison block in the score file.
- OC2B-188: Cycle 1: assign the evidence-ladder level (0-6) the cycle EARNED, with the one-line justification. Proof: level + justification in the record.
- OC2B-189: Cycle 1: write the ledger entry (hashes, seed, timestamps, level) into the lab ledger via the lab's own ledger module. Proof: ledger entry id quoted in the record.
- OC2B-190: Cycle 1: if the result DIFFERs, write the failure analysis (which input or step diverged first). Proof: analysis at labs/cycles/cycle-001/failure.md, or a not-applicable line in the score block.
- OC2B-191: Cycle 1: produce one figure from the outputs (plot or table image) and save it in the pack. Proof: figure file in labs/cycles/cycle-001/ with its generating command recorded.
- OC2B-192: Cycle 1: write the one-paragraph plain summary of what the science showed. Proof: summary at labs/cycles/cycle-001/summary.md.
- OC2B-193: Cycle 1: list what a second pair of eyes should check (Bond's reproduction lane). Proof: checklist at labs/cycles/cycle-001/second-eyes.md.
- OC2B-194: Cycle 1: run the science-lab suite again after adding the pack; record counts. Proof: suite tail in the status block for this cycle's section.
- OC2B-195: Cycle 1: verify no summary or export states a ladder level above the earned one (grep the pack + exports). Proof: grep result line in the status block.
- OC2B-196: Cycle 1: record total model spend for the cycle (zero if none) from receipts. Proof: spend line in the record.
- OC2B-197: Cycle 1: hash the whole pack directory and record the pack hash. Proof: pack hash in labs/cycles/cycle-001/pack.sha256.
- OC2B-198: Cycle 1: status block for the cycle. Proof: status block written.
- OC2B-199: Cycle 1: checkpoint commit for the cycle pack and push. Proof: git log shows the cycle checkpoint commit.
- OC2B-200: Cycle 1: final truth line — what this cycle proved, in one sentence, no adjectives. Proof: truth line ends the cycle's status block.

## Section 9 — Science Lab — cycle 2, a different department (OC2B-201–OC2B-225)

- OC2B-201: Cycle 2: write the cycle record — question, target (a published computational result from a DIFFERENT department than cycle 1, named in the record before running), source citation, expected value. Proof: record committed at labs/cycles/cycle-002/record.md.
- OC2B-202: Cycle 2: name the falsifier — the observation that would kill the claim — in the record. Proof: falsifier paragraph in the record.
- OC2B-203: Cycle 2: pre-register the plan (inputs, method, expected value, tolerance) and commit its SHA-256 hash BEFORE any run. Proof: hash + commit sha in labs/cycles/cycle-002/prereg.md; the prereg commit precedes every result commit in git log.
- OC2B-204: Cycle 2: freeze the input set — copy the exact inputs into the pack and hash each file. Proof: input hashes in labs/cycles/cycle-002/inputs.sha256.
- OC2B-205: Cycle 2: write the run script (deterministic, seed recorded in the record). Proof: script at labs/cycles/cycle-002/run.py (or .mjs — name it in the record).
- OC2B-206: Cycle 2: run the script once; save raw outputs untouched. Proof: raw outputs under labs/cycles/cycle-002/raw/ with hashes.
- OC2B-207: Cycle 2: score the result against the pre-registered expectation: MATCH or DIFFER, differing fields named. Proof: score block in labs/cycles/cycle-002/score.md.
- OC2B-208: Cycle 2: compute the headline metric (RMSE or the metric the record names) and record it beside the expected value. Proof: metric line in the score block.
- OC2B-209: Cycle 2: critic pass — a separate agent or model call argues the result is wrong; save its strongest objection verbatim. Proof: critic text at labs/cycles/cycle-002/critic.md.
- OC2B-210: Cycle 2: answer the objection with evidence, or concede it in writing. Proof: response section in labs/cycles/cycle-002/critic.md.
- OC2B-211: Cycle 2: independent verification — re-run from the recorded inputs in a clean directory. Proof: verification outputs under labs/cycles/cycle-002/verify/.
- OC2B-212: Cycle 2: compare verification outputs to raw outputs (bit-for-bit or the difference explained). Proof: comparison block in the score file.
- OC2B-213: Cycle 2: assign the evidence-ladder level (0-6) the cycle EARNED, with the one-line justification. Proof: level + justification in the record.
- OC2B-214: Cycle 2: write the ledger entry (hashes, seed, timestamps, level) into the lab ledger via the lab's own ledger module. Proof: ledger entry id quoted in the record.
- OC2B-215: Cycle 2: if the result DIFFERs, write the failure analysis (which input or step diverged first). Proof: analysis at labs/cycles/cycle-002/failure.md, or a not-applicable line in the score block.
- OC2B-216: Cycle 2: produce one figure from the outputs (plot or table image) and save it in the pack. Proof: figure file in labs/cycles/cycle-002/ with its generating command recorded.
- OC2B-217: Cycle 2: write the one-paragraph plain summary of what the science showed. Proof: summary at labs/cycles/cycle-002/summary.md.
- OC2B-218: Cycle 2: list what a second pair of eyes should check (Bond's reproduction lane). Proof: checklist at labs/cycles/cycle-002/second-eyes.md.
- OC2B-219: Cycle 2: run the science-lab suite again after adding the pack; record counts. Proof: suite tail in the status block for this cycle's section.
- OC2B-220: Cycle 2: verify no summary or export states a ladder level above the earned one (grep the pack + exports). Proof: grep result line in the status block.
- OC2B-221: Cycle 2: record total model spend for the cycle (zero if none) from receipts. Proof: spend line in the record.
- OC2B-222: Cycle 2: hash the whole pack directory and record the pack hash. Proof: pack hash in labs/cycles/cycle-002/pack.sha256.
- OC2B-223: Cycle 2: status block for the cycle. Proof: status block written.
- OC2B-224: Cycle 2: checkpoint commit for the cycle pack and push. Proof: git log shows the cycle checkpoint commit.
- OC2B-225: Cycle 2: final truth line — what this cycle proved, in one sentence, no adjectives. Proof: truth line ends the cycle's status block.

## Section 10 — Science Lab — cycle 3, model-directed (OC2B-226–OC2B-250)

- OC2B-226: Cycle 3: director call — Muse Spark plans the cycle's approach from the question; save prompt, reply, and receipt. Proof: prompt + reply + receipt under labs/cycles/cycle-003/model/.
- OC2B-227: Cycle 3: write the cycle record adopting or rejecting each part of the director's plan, with reasons. Proof: record at labs/cycles/cycle-003/record.md with the adopt/reject lines.
- OC2B-228: Cycle 3: name the falsifier in the record. Proof: falsifier paragraph in the record.
- OC2B-229: Cycle 3: pre-register and commit the plan hash before any run. Proof: prereg hash + commit order proof in git log.
- OC2B-230: Cycle 3: freeze inputs and hash them. Proof: inputs.sha256 in the pack.
- OC2B-231: Cycle 3: run the experiment; save raw outputs. Proof: raw/ in the pack with hashes.
- OC2B-232: Cycle 3: score against the pre-registered expectation (MATCH/DIFFER, fields named). Proof: score.md in the pack.
- OC2B-233: Cycle 3: Wonder call — give Muse Wonder a figure from the outputs; save its reading. Proof: Wonder reading + receipt under labs/cycles/cycle-003/model/.
- OC2B-234: Cycle 3: check Wonder's reading against the numbers yourself; record agreement or the exact difference. Proof: check block appended to the Wonder reading file.
- OC2B-235: Cycle 3: SAM call — segment one specimen or molecule image from the labs tree; save the box/mask record. Proof: SAM record (box coordinates + mask reference) under labs/cycles/cycle-003/model/.
- OC2B-236: Cycle 3: verify the SAM box lands on the named object by overlaying it on the source image. Proof: overlay image in the pack; a yes/no line in the SAM record.
- OC2B-237: Cycle 3: critic via the second model (Wonder if Spark directed, Spark if Wonder directed). Proof: critic.md in the pack with the model named.
- OC2B-238: Cycle 3: answer or concede the critic's objection in writing. Proof: response section in critic.md.
- OC2B-239: Cycle 3: independent clean-directory re-run and output comparison. Proof: verify/ in the pack + comparison block.
- OC2B-240: Cycle 3: assign the earned ladder level with justification. Proof: level line in the record.
- OC2B-241: Cycle 3: ledger entry via the lab's ledger module. Proof: entry id in the record.
- OC2B-242: Cycle 3: state per model call what it changed about the work (a call that changed nothing is said so). Proof: per-call lines in labs/cycles/cycle-003/model/impact.md.
- OC2B-243: Cycle 3: total the section's model spend from receipts. Proof: spend total in the record, receipts beside it.
- OC2B-244: Cycle 3: figure from the outputs saved in the pack. Proof: figure file + generating command recorded.
- OC2B-245: Cycle 3: plain summary paragraph. Proof: summary.md in the pack.
- OC2B-246: Cycle 3: second-eyes checklist. Proof: second-eyes.md in the pack.
- OC2B-247: Cycle 3: pack hash recorded. Proof: pack.sha256 in the pack.
- OC2B-248: Cycle 3: status block. Proof: status block written.
- OC2B-249: Cycle 3: checkpoint commit and push. Proof: git log shows the cycle 3 checkpoint.
- OC2B-250: Cycle 3: truth line, one sentence. Proof: truth line ends the status block.

## Section 11 — Science Lab — cycles 4 and 5, repository and ledger hardening (OC2B-251–OC2B-275)

- OC2B-251: Cycle 4: write the cycle record — question, target (a target chosen from the lab's repository shelf (os/worlds/science-lab/shelves), named in the record), source citation, expected value. Proof: record committed at labs/cycles/cycle-004/record.md.
- OC2B-252: Cycle 4: name the falsifier — the observation that would kill the claim — in the record. Proof: falsifier paragraph in the record.
- OC2B-253: Cycle 4: pre-register the plan (inputs, method, expected value, tolerance) and commit its SHA-256 hash BEFORE any run. Proof: hash + commit sha in labs/cycles/cycle-004/prereg.md; the prereg commit precedes every result commit in git log.
- OC2B-254: Cycle 4: freeze the input set — copy the exact inputs into the pack and hash each file. Proof: input hashes in labs/cycles/cycle-004/inputs.sha256.
- OC2B-255: Cycle 4: write the run script (deterministic, seed recorded in the record). Proof: script at labs/cycles/cycle-004/run.py (or .mjs — name it in the record).
- OC2B-256: Cycle 4: run the script once; save raw outputs untouched. Proof: raw outputs under labs/cycles/cycle-004/raw/ with hashes.
- OC2B-257: Cycle 4: score the result against the pre-registered expectation: MATCH or DIFFER, differing fields named. Proof: score block in labs/cycles/cycle-004/score.md.
- OC2B-258: Cycle 4: compute the headline metric (RMSE or the metric the record names) and record it beside the expected value. Proof: metric line in the score block.
- OC2B-259: Cycle 4: critic pass — a separate agent or model call argues the result is wrong; save its strongest objection verbatim. Proof: critic text at labs/cycles/cycle-004/critic.md.
- OC2B-260: Cycle 4: answer the objection with evidence, or concede it in writing. Proof: response section in labs/cycles/cycle-004/critic.md.
- OC2B-261: Cycle 4: independent verification — re-run from the recorded inputs in a clean directory. Proof: verification outputs under labs/cycles/cycle-004/verify/.
- OC2B-262: Cycle 4: compare verification outputs to raw outputs (bit-for-bit or the difference explained). Proof: comparison block in the score file.
- OC2B-263: Cycle 5: pick the target — a result that FAILED or was held in an earlier cycle, or a held-out Delaney slice (rows beyond 30) — and write the record. Proof: record at labs/cycles/cycle-005/record.md naming the target's origin.
- OC2B-264: Cycle 5: falsifier + pre-registration hash committed before any run. Proof: prereg commit precedes results in git log.
- OC2B-265: Cycle 5: execute the pre-registered run in one pass and produce the complete pack in cycle-001's layout: raw outputs with hashes, score.md (MATCH/DIFFER with differing fields named), critic.md with the response section, verify/ clean-directory outputs with the comparison block, and a pack manifest listing every produced file. Proof: manifest at labs/cycles/cycle-005/manifest.md enumerating each file; no layout item missing from the manifest.
- OC2B-266: Cycle 5: ladder level + ledger entry. Proof: level + entry id in the record.
- OC2B-267: Cycle 5: plain summary + second-eyes checklist. Proof: summary.md + second-eyes.md in the pack.
- OC2B-268: Repository pass: export all five cycle packs through the lab's repository module (repository.py) and record the export paths. Proof: export paths in os-build/logs/OC2B-repository-export.md.
- OC2B-269: Repository pass: verify each exported pack still hashes to its recorded pack hash. Proof: hash-check table in os-build/logs/OC2B-repository-export.md.
- OC2B-270: Ledger audit: read back the lab ledger and confirm all five cycle entries exist with levels matching their records. Proof: audit table in os-build/logs/OC2B-ledger-audit.md.
- OC2B-271: Ladder audit: confirm no export or summary anywhere states a level above an earned one. Proof: grep evidence in os-build/logs/OC2B-ledger-audit.md.
- OC2B-272: Cross-cycle comparison: one page comparing the five cycles (domain, metric, MATCH/DIFFER, level). Proof: comparison at labs/cycles/COMPARISON.md.
- OC2B-273: Failure honour roll: list every DIFFER and failed reproduction across the five cycles in one place, unedited. Proof: section inside labs/cycles/COMPARISON.md.
- OC2B-274: Write the §11 status block. Proof: status file §11 block.
- OC2B-275: Checkpoint commit §11 and push. Proof: git log shows the §11 checkpoint; ls-remote matches.

## Section 12 — Hortus — breeding run 001, eight generations, fully logged (OC2B-276–OC2B-300)

- OC2B-276: Read os/worlds/science-lab/breeding.py and the hortus package; write a 10-line map of the breeding entry points into the run record. Proof: map in labs/hortus/runs/run-001/record.md.
- OC2B-277: Run the Hortus suite first and record the baseline counts. Proof: suite tail in the run record.
- OC2B-278: Define run-001: population size, mutation rule, fitness measure — all written before the run. Proof: definition block in the record.
- OC2B-279: Record the run's seed in the record before running. Proof: seed line in the record.
- OC2B-280: Generation 1: run and log best + mean fitness. Proof: generation row in labs/hortus/runs/run-001/generations.csv.
- OC2B-281: Generation 2: run and log best + mean fitness. Proof: generation row in the CSV.
- OC2B-282: Generation 3: run and log best + mean fitness. Proof: generation row in the CSV.
- OC2B-283: Generation 4: run and log best + mean fitness. Proof: generation row in the CSV.
- OC2B-284: Generation 5: run and log best + mean fitness. Proof: generation row in the CSV.
- OC2B-285: Generation 6: run and log best + mean fitness. Proof: generation row in the CSV.
- OC2B-286: Generation 7: run and log best + mean fitness. Proof: generation row in the CSV.
- OC2B-287: Generation 8: run and log best + mean fitness. Proof: generation row in the CSV.
- OC2B-288: Plot the fitness curve (best + mean per generation) to a figure in the run pack. Proof: figure file in labs/hortus/runs/run-001/.
- OC2B-289: Reproduction check: re-run run-001 from the recorded seed in a clean directory; compare the CSV. Proof: comparison line in the record (identical or difference explained).
- OC2B-290: Name what the breeding actually selected for, in one line, from the winning genome's traits. Proof: selection line in the record.
- OC2B-291: Record the winning genome (or its hash + path) in the run pack. Proof: genome file or hash in labs/hortus/runs/run-001/.
- OC2B-292: Report the fitness curve honestly — if flat or falling, the record says so in the first paragraph. Proof: first paragraph of the record's results section.
- OC2B-293: Run the Hortus suite again after the run; record counts. Proof: suite tail in the status file §12 block.
- OC2B-294: Hash the run pack. Proof: pack hash in the record.
- OC2B-295: Write the §12 status block. Proof: status file §12 block.
- OC2B-296: Checkpoint commit §12 and push. Proof: git log shows the §12 checkpoint.
- OC2B-297: List what run-002 should change (one variable only) in the status block. Proof: change line in the status file §12 block.
- OC2B-298: Verify the run-001 CSV has no gaps (generations 1-8 all present). Proof: row count line in the record.
- OC2B-299: Record total wall time of run-001. Proof: timing in the record.
- OC2B-300: Truth line for run-001, one sentence. Proof: truth line ends the §12 status block.

## Section 13 — Hortus — breeding runs 002 and 003, selection analysis (OC2B-301–OC2B-325)

- OC2B-301: Run-002: change exactly the one variable named at the end of §12; write the definition + seed before running. Proof: definition block in labs/hortus/runs/run-002/record.md.
- OC2B-302: Run-002 generations 1-4: run and log best + mean fitness per generation. Proof: four rows in labs/hortus/runs/run-002/generations.csv.
- OC2B-303: Run-002 generations 5-8: run and log best + mean fitness per generation. Proof: four more rows in the CSV (8 total).
- OC2B-304: Run-002: plot the fitness curve. Proof: figure in the run pack.
- OC2B-305: Run-002: reproduction check from the seed in a clean directory. Proof: comparison line in the record.
- OC2B-306: Run-002: name what it selected for, one line. Proof: selection line in the record.
- OC2B-307: Run-003: change the fitness measure (not the mutation rule); definition + seed first. Proof: definition block in labs/hortus/runs/run-003/record.md.
- OC2B-308: Run-003 generations 1-4: run and log. Proof: four rows in labs/hortus/runs/run-003/generations.csv.
- OC2B-309: Run-003 generations 5-8: run and log. Proof: four more rows (8 total).
- OC2B-310: Run-003: plot the fitness curve. Proof: figure in the run pack.
- OC2B-311: Run-003: reproduction check from the seed. Proof: comparison line in the record.
- OC2B-312: Run-003: name what it selected for, one line. Proof: selection line in the record.
- OC2B-313: Compare the three runs in one table (variable changed, final best, curve shape). Proof: table at labs/hortus/runs/COMPARISON.md.
- OC2B-314: Diversity check: measure genome diversity in the final generation of each run (the lab's own metric or a named simple one). Proof: diversity numbers in labs/hortus/runs/COMPARISON.md with the metric named.
- OC2B-315: Premature-convergence check: state for each run whether diversity collapsed before generation 8. Proof: three yes/no lines with evidence in COMPARISON.md.
- OC2B-316: Run the Hortus suite on the final tree; record counts. Proof: suite tail in the status file §13 block.
- OC2B-317: Run the science-lab suite (Hortus lives inside it); record counts. Proof: suite tail in the status file §13 block.
- OC2B-318: Hash all three run packs. Proof: three pack hashes in COMPARISON.md.
- OC2B-319: Write the breeding chapter for the proof index: what Hortus demonstrably does, in 5 lines. Proof: 5 lines appended to COMPARISON.md.
- OC2B-320: Write the §13 status block. Proof: status file §13 block.
- OC2B-321: Checkpoint commit §13 and push. Proof: git log shows the §13 checkpoint.
- OC2B-322: Record any generation that errored, with the error, in its run record (no silent reruns). Proof: error lines present or a no-errors line in each record.
- OC2B-323: Verify all three CSVs parse (a small script reads them and counts rows). Proof: script output in the status file §13 block.
- OC2B-324: Record total compute time across the three runs. Proof: sum in COMPARISON.md.
- OC2B-325: Truth line for the Hortus lane, one sentence. Proof: truth line ends the §13 status block.

## Section 14 — Officina — stage 2b prior-art, built in steps (OC2B-326–OC2B-350)

- OC2B-326: Find the Officina code (os/worlds/officina/runtime/brief.py and neighbours); run its suite + the 2a gate and record the baseline. Proof: baseline counts in os-build/logs/OC2B-officina-baseline.md.
- OC2B-327: Read the 2a brief module's input/output shape and write the 2b interface note (what a brief contains, what a prior-art note must return). Proof: interface note at os-build/logs/OC2B-2b-interface.md.
- OC2B-328: Write the 2b prior-art module skeleton in territory (os/worlds/officina/runtime/) with the note schema (sources list mandatory). Proof: module file committed; its schema visible in the file.
- OC2B-329: Unit test: a note with zero sources is rejected by the schema check. Proof: test in tests/officina/ (or the territory's test home — name it) passing.
- OC2B-330: Implement source search over the repo first (grep-based prior art inside the tree: briefs, packs, runs). Proof: search function committed with a test on a known brief.
- OC2B-331: Implement public-web source search through the available search tooling; results recorded as URLs + titles only. Proof: search function committed; a sample result set saved in the test fixtures.
- OC2B-332: Implement the note writer: from a brief + source set, produce the prior-art note with sources named per claim. Proof: note writer committed with a test.
- OC2B-333: Guard test: the phrase 'patentability opinion' can never appear as a claim in a generated note (the module refuses or strips it, test proves which). Proof: guard test passing; behaviour named in the module docstring.
- OC2B-334: Run 2b on brief A (the heatsink-fin brief from the existing 2a fixtures): save the note. Proof: note at labs/officina/builds/brief-a-priorart.md with sources.
- OC2B-335: Run 2b on brief B (a bracket/mount brief you write in rough words): save the note. Proof: note at labs/officina/builds/brief-b-priorart.md with sources.
- OC2B-336: Run 2b on brief C (a fin-array variant with different bounds pressure): save the note. Proof: note at labs/officina/builds/brief-c-priorart.md with sources.
- OC2B-337: Source-quality pass: for each note, mark each source as primary (paper/patent/datasheet) or secondary (blog/forum). Proof: marks in the three note files.
- OC2B-338: Dead-source check: re-fetch each cited URL; record which are dead. Proof: dead/alive column added to the three notes.
- OC2B-339: Dedup check: no source cited twice under different titles in one note. Proof: check output in os-build/logs/OC2B-2b-checks.md.
- OC2B-340: Latency record: time each 2b run and record the three numbers. Proof: timings in os-build/logs/OC2B-2b-checks.md.
- OC2B-341: Failure drill: run 2b with web search unavailable (offline) and record the degraded behaviour (repo-only note or a clean refusal). Proof: drill record in os-build/logs/OC2B-2b-checks.md.
- OC2B-342: Wire 2b into the Officina runtime flow (2a brief -> 2b note) behind the existing entry point; no registry changes (propose them in the status file instead). Proof: wiring commit + a test that runs brief->note end to end.
- OC2B-343: Run the full Officina suite + 2a gate again; record counts. Proof: counts in os-build/logs/OC2B-officina-baseline.md appended section.
- OC2B-344: Write the 2b stage record: what it does, what it never claims. Proof: record at os-build/logs/OC2B_OFFICINA_2B.md.
- OC2B-345: Propose any registry/README changes for 2b in the status file (do not make them). Proof: proposal lines in the status file §14 block.
- OC2B-346: Write the §14 status block (2b only). Proof: status file §14 block.
- OC2B-347: Checkpoint commit §14 and push. Proof: git log shows the §14 checkpoint.
- OC2B-348: Sweep §14 commits for secrets (grep for key-shaped strings). Proof: sweep result line in the status file §14 block.
- OC2B-349: Size-check §14 additions; nothing over 1 MB without justification. Proof: size line in the status file §14 block.
- OC2B-350: Truth line for 2b, one sentence. Proof: truth line ends the §14 status block.

## Section 15 — Officina — stages 2c blueprint packs and 2d workshop memory (OC2B-351–OC2B-375)

- OC2B-351: Read the current bounds from the code (FIN_HEIGHT_MM, BASE_THICKNESS_MM in os/worlds/officina/runtime/brief.py) and record the exact values. Proof: values quoted in os-build/logs/OC2B-2c-bounds.md with the file + line named.
- OC2B-352: Write the 2c blueprint pack schema (dimensions, materials, steps) in territory. Proof: schema file committed.
- OC2B-353: Implement the pack emitter: from a 2a brief, emit a pack conforming to the schema. Proof: emitter committed with a unit test.
- OC2B-354: Implement the bounds checker: rejects any pack with a dimension outside the read bounds. Proof: checker committed.
- OC2B-355: Checker test 1: a pack at exactly the bounds passes. Proof: test passing.
- OC2B-356: Checker test 2: a pack 1 mm over FIN_HEIGHT_MM fails with the field named. Proof: test passing; error text names the field.
- OC2B-357: Checker test 3: a pack under the base-thickness bound fails (or passes — whichever the code's bound direction says; the test documents which). Proof: test passing; direction documented in the test name.
- OC2B-358: Emit pack for brief A and save it. Proof: pack at labs/officina/builds/brief-a-pack.json.
- OC2B-359: Emit pack for brief B and save it. Proof: pack at labs/officina/builds/brief-b-pack.json.
- OC2B-360: Emit pack for brief C and save it. Proof: pack at labs/officina/builds/brief-c-pack.json.
- OC2B-361: Run the bounds checker over all three packs from a clean directory. Proof: three verdicts in os-build/logs/OC2B-2c-bounds.md.
- OC2B-362: Implement 2d workshop memory: packs + outcomes append to an append-only workshop record the next brief can read. Proof: memory module committed; record file format documented in its docstring.
- OC2B-363: Memory test 1: append brief A's pack + outcome; read it back. Proof: test passing.
- OC2B-364: Memory test 2: two sequential briefs — the second brief's context shows the first's entry was readable. Proof: test passing (the execution list's own 2d test, now real).
- OC2B-365: Memory test 3: append 50 entries; confirm the oldest is still present (no silent drop). Proof: test passing.
- OC2B-366: Backfill: write the three §14/§15 packs into workshop memory with their outcomes. Proof: memory record file committed under labs/officina/ with 3+ entries.
- OC2B-367: Read-back drill: start a fresh brief and dump the memory context it receives; save the dump. Proof: dump at os-build/logs/OC2B-2d-readback.md.
- OC2B-368: Corruption drill: truncate the memory file mid-entry in a scratch copy; the reader must fail clean or skip the partial entry — record which. Proof: drill record in os-build/logs/OC2B-2d-readback.md.
- OC2B-369: Run the full Officina suite + 2a gate; record counts. Proof: counts in the status file §15 block.
- OC2B-370: Write the 2c stage record. Proof: record at os-build/logs/OC2B_OFFICINA_2C.md.
- OC2B-371: Write the 2d stage record. Proof: record at os-build/logs/OC2B_OFFICINA_2D.md.
- OC2B-372: Propose registry/README changes for 2c/2d in the status file (do not make them). Proof: proposal lines in the status file §15 block.
- OC2B-373: Write the §15 status block (2c and 2d separately). Proof: status file §15 block with two sub-blocks.
- OC2B-374: Checkpoint commit §15 and push. Proof: git log shows the §15 checkpoint.
- OC2B-375: Truth lines for 2c and 2d, one sentence each. Proof: two truth lines end the §15 status block.

## Section 16 — Officina — two real builds, words to pack, end to end (OC2B-376–OC2B-400)

- OC2B-376: Write build-001's verbal brief the way a person would say it (a thing to build, rough words, no numbers). Proof: brief text at labs/officina/builds/build-001/brief.txt.
- OC2B-377: Run build-001 through 2a: save the self-built brief. Proof: built brief in labs/officina/builds/build-001/.
- OC2B-378: Run build-001 through 2b: save the prior-art note. Proof: note in the build-001 directory with sources.
- OC2B-379: Run build-001 through 2c: save the blueprint pack. Proof: pack in the build-001 directory.
- OC2B-380: Bounds-check the build-001 pack with the §15 checker. Proof: verdict in the build-001 directory.
- OC2B-381: Run the faber loop on the build-001 pack if it takes packs as input; if not, record that gap verbatim. Proof: loop output or gap record in the build-001 directory.
- OC2B-382: If the faber loop ran: record its cycle count, stop reason, and final state. Proof: loop record in the build-001 directory.
- OC2B-383: Write build-001's outcome into workshop memory (2d). Proof: memory entry id/path in the build-001 record.
- OC2B-384: Independent check: re-run the bounds checker on the build-001 pack from a clean directory. Proof: verdict in the build-001 directory, marked independent.
- OC2B-385: Muse Image concept render for the build-001 pack, filename and in-pack label both say GENERATED. Proof: render file named *GENERATED* in the build-001 directory; receipt saved beside it.
- OC2B-386: Verify the render's receipt exists and parses (Bond's check, done by you first). Proof: receipt parse line in the build-001 record.
- OC2B-387: Plain summary: what Officina would build from those words. Proof: summary.md in the build-001 directory.
- OC2B-388: Write build-002's verbal brief — a different object than build-001. Proof: brief at labs/officina/builds/build-002/brief.txt.
- OC2B-389: Run build-002 through 2a + 2b + 2c end to end; save all three artifacts. Proof: three artifacts in the build-002 directory.
- OC2B-390: Bounds-check build-002's pack; write its outcome to workshop memory. Proof: verdict + memory entry in the build-002 directory.
- OC2B-391: Compare build-001 and build-002: what the pipeline did identically, what differed. Proof: comparison at labs/officina/builds/COMPARISON.md.
- OC2B-392: Check workshop memory now holds both builds and the §15 packs, oldest first, nothing dropped. Proof: entry list in COMPARISON.md.
- OC2B-393: Run the full Officina suite + 2a gate on the final tree; record counts. Proof: counts in the status file §16 block.
- OC2B-394: Time the full words-to-pack pipeline for build-002 (wall time per stage). Proof: timing table in COMPARISON.md.
- OC2B-395: Failure honesty: record any stage in either build that fell back, refused, or was skipped. Proof: failure lines in COMPARISON.md, or a none line.
- OC2B-396: Write the §16 status block. Proof: status file §16 block.
- OC2B-397: Checkpoint commit §16 and push. Proof: git log shows the §16 checkpoint.
- OC2B-398: Verify no pack anywhere in labs/officina states a dimension outside the §15 bounds (script the check). Proof: script output in the status file §16 block.
- OC2B-399: Verify every image in labs/officina carries GENERATED in its filename. Proof: filename list in the status file §16 block.
- OC2B-400: Truth line for the Officina lane, one sentence. Proof: truth line ends the §16 status block.

## Section 17 — Model pipeline — live proofs: SAM into patrol, Wonder review, Muse Image (OC2B-401–OC2B-425)

- OC2B-401: SAM into patrol evidence 1: take one committed eval frame from the Wikimedia pack and run models.py segment() on it from the Mac; save the raw response. Proof: raw response + parsed box under os-build/logs/OC2B-sam-patrol/frame1/.
- OC2B-402: SAM into patrol evidence 2: overlay the returned box on the frame and save the overlay. Proof: overlay image in the frame1 directory.
- OC2B-403: SAM into patrol evidence 3: repeat on a second frame with a different named object prompt. Proof: raw + overlay under os-build/logs/OC2B-sam-patrol/frame2/.
- OC2B-404: SAM into patrol evidence 4: repeat on a third frame; if SAM returns no box, record the no-box result as-is (Pax's probe and OC1 both saw variance — never invent a box). Proof: record under frame3/, box or honest no-box.
- OC2B-405: SAM variance record: tabulate the three calls (prompt, box yes/no, coordinates). Proof: table at os-build/logs/OC2B-sam-patrol/VARIANCE.md.
- OC2B-406: Patrol wiring check: run the queue patrol path with the SAM step invoked on one frame in a scratch config (do not edit server/queue on this branch — exercise models.py the way patrol would). Proof: run log + the segment record it produced, at os-build/logs/OC2B-sam-patrol/wiring.md.
- OC2B-407: Wonder review swap proof 1: run one crew review case (two staged readings) through judge.rule_with_model with Wonder as the model; save input + verdict. Proof: case file under os-build/logs/OC2B-wonder-review/case1/.
- OC2B-408: Wonder review swap proof 2: run a second case designed to disagree (one reading flags, one clears). Proof: case file under case2/ with the verdict.
- OC2B-409: Wonder review swap proof 3: run a third case with an emergency reading (visible flame) and record the verdict + tier. Proof: case file under case3/; tier named.
- OC2B-410: Compare Wonder verdicts against the deterministic combine() on the same three cases. Proof: comparison table at os-build/logs/OC2B-wonder-review/COMPARE.md.
- OC2B-411: Judge v2 live re-proof: with TRIO_JUDGE_MODEL=1, run one staged crew review end to end and confirm the timeline records judge_mode: model. Proof: timeline excerpt + receipt at os-build/logs/OC2B-judge-live.md.
- OC2B-412: Judge fallback proof: force a transport failure (bad endpoint in a scratch env) and confirm the fallback to combine() is named in the timeline. Proof: timeline excerpt at os-build/logs/OC2B-judge-fallback.md showing the named fallback.
- OC2B-413: Muse Image proof 1: generate one concept image for the Science Lab (a lab scene), filename carries GENERATED. Proof: image + receipt under os-build/logs/OC2B-images/.
- OC2B-414: Muse Image proof 2: generate one concept image for Officina (a workshop scene), filename carries GENERATED. Proof: image + receipt under os-build/logs/OC2B-images/.
- OC2B-415: Muse Image proof 3: verify both files' magic bytes match their extensions (models.py format detection). Proof: magic-byte check lines in os-build/logs/OC2B-images/CHECKS.md.
- OC2B-416: Transcribe surface record: re-run the documented probes (audio endpoint, chat/responses audio inputs) once and record the exact errors — no new guessing beyond the documented set. Proof: probe results at os-build/logs/OC2B-transcribe-probes.md matching or updating os-build/MODEL_INTEGRATION.md's account.
- OC2B-417: Receipts audit: collect every model receipt produced in §17 into one index with model, purpose, and estimated cost where a rate exists. Proof: index at os-build/logs/OC2B-model-receipts-index.md.
- OC2B-418: Spend total for §17 from the receipts, against the guardrail. Proof: total line in the index.
- OC2B-419: Live patrol dry run: run one full patrol-review-judge pass on a staged frame set with all model steps on; save the incident record. Proof: incident record + sim receipt under os-build/logs/OC2B-patrol-live/.
- OC2B-420: Confirm the patrol run's dispatch (if any) went only to a loopback simulated endpoint with a sim- receipt id. Proof: receipt id quoted in os-build/logs/OC2B-patrol-live/ with the endpoint shown.
- OC2B-421: Write the §17 status block. Proof: status file §17 block.
- OC2B-422: Checkpoint commit §17 and push. Proof: git log shows the §17 checkpoint.
- OC2B-423: Sweep §17 for the API key value (grep the branch diff for it). Proof: sweep result line in the status file §17 block — zero hits required.
- OC2B-424: Record which §17 proofs Pax can lift directly into MODEL_INTEGRATION.md follow-ups, as proposal lines in the status file. Proof: proposal lines in the status file §17 block.
- OC2B-425: Truth line for the model lane, one sentence. Proof: truth line ends the §17 status block.

## Section 18 — Live cameras on the Mac — NYC DOT source, real frames, real readings (OC2B-426–OC2B-450)

- OC2B-426: Run livecams.py --list from the Mac and save the full camera list output. Proof: list output at os-build/logs/OC2B-cams-list.txt with the camera count.
- OC2B-427: Verify the Mac's egress to webcams.nyctmc.org works directly (the sandbox's does not): record the HTTP status of the cameras API GET. Proof: status line in os-build/logs/OC2B-cams-list.txt.
- OC2B-428: Snapshot one online Brooklyn camera via livecams.py and save the frame with its camera name + timestamp. Proof: frame under os-build/logs/OC2B-cams/brooklyn/ named with the camera id.
- OC2B-429: Snapshot one online Manhattan camera via livecams.py and save the frame with its camera name + timestamp. Proof: frame under os-build/logs/OC2B-cams/manhattan/ named with the camera id.
- OC2B-430: Snapshot one online Queens camera via livecams.py and save the frame with its camera name + timestamp. Proof: frame under os-build/logs/OC2B-cams/queens/ named with the camera id.
- OC2B-431: Snapshot one online Bronx camera via livecams.py and save the frame with its camera name + timestamp. Proof: frame under os-build/logs/OC2B-cams/bronx/ named with the camera id.
- OC2B-432: Snapshot one online Staten Island camera via livecams.py and save the frame with its camera name + timestamp. Proof: frame under os-build/logs/OC2B-cams/statenisland/ named with the camera id.
- OC2B-433: Assess one Brooklyn frame through the production assess path (vigiles) and save the reading JSON. Proof: reading JSON in the Brooklyn directory with model + latency recorded.
- OC2B-434: Assess one Manhattan frame through the production assess path (vigiles) and save the reading JSON. Proof: reading JSON in the Manhattan directory with model + latency recorded.
- OC2B-435: Assess one Queens frame through the production assess path (vigiles) and save the reading JSON. Proof: reading JSON in the Queens directory with model + latency recorded.
- OC2B-436: Assess one frame through the ignis division prompt and save the reading. Proof: reading JSON under os-build/logs/OC2B-cams/divisions/ignis.json.
- OC2B-437: Assess one frame through the medicus division prompt and save the reading. Proof: reading JSON under os-build/logs/OC2B-cams/divisions/medicus.json.
- OC2B-438: Round-robin check: call LiveCamSource.frame() five times in a script and record that the cameras rotate. Proof: five camera names in os-build/logs/OC2B-cams/roundrobin.md, no repeats beyond the documented behaviour.
- OC2B-439: Staleness check: fetch the same camera twice 5 minutes apart and record whether the image bytes changed. Proof: two hashes + verdict in os-build/logs/OC2B-cams/roundrobin.md.
- OC2B-440: Offline-camera check: confirm an isOnline=false camera is excluded by the parser (name one and show its absence from picks). Proof: camera name + exclusion evidence in os-build/logs/OC2B-cams/roundrobin.md.
- OC2B-441: Run the livecams test module (tests/queue-python/test_livecams.py) on the Mac and record counts. Proof: test tail in the status file §18 block.
- OC2B-442: Total the §18 model spend from receipts (assess calls only). Proof: spend line in the status file §18 block.
- OC2B-443: Write the §18 status block: what the live path proved on the Mac, in plain words. Proof: status file §18 block.
- OC2B-444: Checkpoint commit §18 and push (frames + readings only, size-checked). Proof: git log shows the §18 checkpoint; any frame over 1 MB justified or recompressed.
- OC2B-445: Record the exact commands used for every §18 run in the status file for reproducibility. Proof: command list in the status file §18 block.
- OC2B-446: Verify one fetched frame's bytes are a real JPEG (magic bytes + decodable by PIL or file) and record the check. Proof: check line in os-build/logs/OC2B-cams/roundrobin.md.
- OC2B-447: Fetch one camera directly by its id from the §18 list output (not via round-robin) and save the frame. Proof: frame in os-build/logs/OC2B-cams/ named with that camera id + the id quoted from the list.
- OC2B-448: Compare the §18 online-camera count against the count in the committed livecam_records on main; record both numbers and the delta. Proof: two counts + delta in os-build/logs/OC2B-cams/roundrobin.md.
- OC2B-449: Assess the Staten Island frame through the medicus division prompt and save the reading. Proof: reading JSON in os-build/logs/OC2B-cams/statenisland/ beside its frame.
- OC2B-450: Record the per-call latency of the three division assessments from the receipts and note the slowest. Proof: three latency values in the status file §18 block.

## Section 19 — Musica real runs and Goose gate-2 on the Mac (OC2B-451–OC2B-475)

- OC2B-451: Install pretty_midi on the Mac (pip install pretty_midi or the project's documented route — name it) and record the version. Proof: version line in os-build/logs/OC2B-musica-runs.md.
- OC2B-452: Run the Musica test suite on the Mac; record counts (Bond's earlier run: 37 pass / 2 fail, both missing pretty_midi). Proof: suite tail in os-build/logs/OC2B-musica-runs.md.
- OC2B-453: Re-run specifically the two previously failing Musica tests and record their verdicts now. Proof: two verdict lines in os-build/logs/OC2B-musica-runs.md.
- OC2B-454: Run one Musica generation path end to end (the runtime entry the pack names) and save its output artifact. Proof: artifact path + size in os-build/logs/OC2B-musica-runs.md.
- OC2B-455: Run a second Musica path (a brief from os/worlds/musica/briefs) and save the output. Proof: artifact path in os-build/logs/OC2B-musica-runs.md.
- OC2B-456: Verify the Musica outputs open/parse (MIDI files load via pretty_midi without error). Proof: parse-check lines in os-build/logs/OC2B-musica-runs.md.
- OC2B-457: Goose toolchain: locate or build the goose binary on the Mac following services/BUILD.md (or the toolchain report); record the binary path + version. Proof: path + version in os-build/logs/OC2B-goose-gate2.md.
- OC2B-458: Record whether services/run-goose-tests.sh still hardcodes /Users/test/mcp-servers/toolchains/goose-src/build/goose on current main. Proof: grep result in os-build/logs/OC2B-goose-gate2.md.
- OC2B-459: Run the goose test runner with the Mac binary path supplied (env/flag, no file edits on this branch) over the root cluster (root.goose, root_bootlog.goose, root_console.goose). Proof: runner output in os-build/logs/OC2B-goose-gate2.md.
- OC2B-460: Run the goose runner over the root_example.goose + root_logd.goose + root_time.goose set. Proof: runner output appended to os-build/logs/OC2B-goose-gate2.md.
- OC2B-461: Run the goose runner over the next 10 service files in services/MANIFEST.md order (files 7-16, after the 6 named above); record per-file verdicts. Proof: 10 verdict lines in os-build/logs/OC2B-goose-gate2.md, each naming its file.
- OC2B-462: Run the goose runner over the following 10 service files in MANIFEST order (files 17-26). Proof: 10 verdict lines appended, each naming its file.
- OC2B-463: Run the goose runner over the following 10 service files in MANIFEST order (files 27-36). Proof: 10 verdict lines appended, each naming its file.
- OC2B-464: Run the goose runner over the remaining service files in MANIFEST order (files 37 to the end). Proof: verdict lines appended; total files covered stated.
- OC2B-465: Tabulate gate-2: total goose files run, passed, failed, with failed file names. Proof: table in os-build/logs/OC2B-goose-gate2.md.
- OC2B-466: For each failing goose file, record the first error line verbatim (no fixes on this branch — Buffy's R12 owns the runner fix; file the record for her). Proof: error lines in os-build/logs/OC2B-goose-gate2.md.
- OC2B-467: Run node --test tests/goose-programs.test.mjs on the Mac and record the result beside the binary results. Proof: node result in os-build/logs/OC2B-goose-gate2.md.
- OC2B-468: Musica + Goose: record any Mac-only failure that cannot reproduce in the sandbox, labelled MAC-ONLY. Proof: labelled lines in the two section logs, or a none line.
- OC2B-469: Write the §19 status block (Musica and Goose as separate sub-blocks). Proof: status file §19 block with two sub-blocks.
- OC2B-470: Checkpoint commit §19 and push. Proof: git log shows the §19 checkpoint.
- OC2B-471: Record the goose binary's build provenance (source path + version) for the toolchain report. Proof: provenance lines in os-build/logs/OC2B-goose-gate2.md.
- OC2B-472: Verify the Musica artifacts from this section are not over 1 MB each without justification. Proof: size lines in os-build/logs/OC2B-musica-runs.md.
- OC2B-473: Propose (do not make) the run-goose-tests.sh path fix as a diff sketch in the status file for Buffy/Pax. Proof: diff sketch in the status file §19 block.
- OC2B-474: Record total §19 wall time. Proof: timing in the status file §19 block.
- OC2B-475: Truth lines for Musica and for Goose, one sentence each. Proof: two truth lines end the §19 status block.

## Section 20 — Proof index, truth pass, and closeout (OC2B-476–OC2B-500)

- OC2B-476: Assemble os-build/logs/OC2B_PROOF_INDEX.md: every section of this list mapped to its artifact paths. Proof: index file committed with 20 section entries.
- OC2B-477: Index audit: click-check every path in the index exists on the branch. Proof: audit result line in the index (all exist, or the missing ones named).
- OC2B-478: Truth pass over the status file: every DONE has an artifact; anything else relabelled UNPROVEN. Proof: edited status file committed; the relabelled items listed in the §20 block.
- OC2B-479: Truth pass over science summaries: no summary states a ladder level above its cycle's recorded level. Proof: check result in the §20 block.
- OC2B-480: Truth pass over Officina: no pack states a dimension outside bounds; every image filename carries GENERATED. Proof: check result in the §20 block.
- OC2B-481: Truth pass over kernel-face claims: no file on this branch says or implies the web face is the OS, or that the kernel boots into a desktop beyond what the screendumps prove. Proof: grep evidence in the §20 block.
- OC2B-482: Truth pass over SAM records: no box recorded where the raw response had none. Proof: check result in the §20 block.
- OC2B-483: Sweep the whole branch diff for secrets (key-shaped strings, the Mac key value). Proof: sweep result in the §20 block — zero hits required.
- OC2B-484: Sweep the branch for files over 1 MB added by this list; justify or remove each. Proof: size table in the §20 block.
- OC2B-485: Run the science-lab suite on the final tree; record counts. Proof: suite tail in the §20 block.
- OC2B-486: Run the Hortus suite on the final tree; record counts. Proof: suite tail in the §20 block.
- OC2B-487: Run the queue suite on the final tree; record counts. Proof: suite tail in the §20 block.
- OC2B-488: Run the Officina suite + 2a gate on the final tree; record counts. Proof: counts in the §20 block.
- OC2B-489: Run node --test tests/goose-programs.test.mjs on the final tree; record the result. Proof: result in the §20 block.
- OC2B-490: Total all model spend across the list from the receipt indexes. Proof: grand total in the §20 block, under the guardrail or the overage named.
- OC2B-491: Write the final UNPROVEN list: everything this list attempted that is still unproven, in plain words. Proof: list at the end of the status file, no items hidden.
- OC2B-492: Write the handoff summary for Pax: what is ready to merge, section by section, with branch tip sha. Proof: summary block at the end of the status file.
- OC2B-493: Final commit on opencode2/500 and push; confirm remote tip equals local tip. Proof: ls-remote line in the §20 block.
- OC2B-494: Record the final branch's total diffstat vs main (files changed, insertions, deletions). Proof: diffstat in the §20 block.
- OC2B-495: Confirm kernel/ diff vs main is still empty on the final tree. Proof: empty-diff line in the §20 block.
- OC2B-496: Confirm no server/queue file was edited on this branch (Pax's integration lane). Proof: diff line in the §20 block.
- OC2B-497: Confirm agents/registry.json was not edited; any proposals live only in the status file. Proof: diff line in the §20 block.
- OC2B-498: Write the §20 status block. Proof: status file §20 block complete.
- OC2B-499: Add the closing entry to os-build/logs/OC2B_PROOF_INDEX.md pointing at the final status file. Proof: index updated and committed.
- OC2B-500: Final truth line for the whole list, one sentence. Proof: truth line is the last line of the status file.


# OPENCODE 1 — 500 TASKS (the Mac proof lane)

Owner: OpenCode 1, on Del's Mac. Branch: `opencode/500`. NEVER push main.
Status file: `os-build/OPENCODE1_500_STATUS.md` — updated per section with
proof lines; UNPROVEN items named, never hidden. Merges through Pax only:
you prove and commit on your branch, Pax merges at the checkpoint.

This list SUPERSEDES `os-build/OPENCODE1_TASKS_WAVE3.md` sections 2–10 by
folding them in and expanding them. Wave-3 section 1 is DONE and merged
(combined-tree boot proof at c7aeb162: banner, alive, readkey got=3, fetch
screen, status/ps, bad syscall 99 refused, fault isolation, panic 0; gate
GREEN 7/7; proof in `os-build/logs/WAVE3_KERNEL_PROOF.md`). Section 1's
work appears below ONLY as re-verification/baseline tasks, never as new
work. Where a wave-3 section is folded in, the task says so.

START ORDER: the wave-3 criticals come first — §7's soak-verdict
collection (OC1B-151..155) and §11's demo capture (OC1B-251..275) — then
§1 baseline, then the remaining sections in numeric order. Kernel-face
sections (§2–§4) run as Rowan lands each KF piece on his branches; a
section blocked on Rowan is recorded BLOCKED in the status file with the
missing piece named, and you move on — never idle. Key rule: the Mac key
at `~/Desktop/hackathon key.txt` line 1 only, read into the environment
as SPARK_API_KEY; never print it, never log it, never commit it. Log a
key outage once, work offline items, never retry-loop.

FENCES (obey in every task):
- Kernel merges need a committed boot log read by Pax. Your proofs are
  the gate; a claim without its committed file does not count.
- You prove, Rowan writes kernel code. You do NOT edit `kernel/src`
  except at Rowan's named request recorded in the status file.
- `kernel/src/syscalls.rs` is FROZEN. It is never a task, never an edit,
  never a diff on any branch you gate.
- Imperium dispatch is the simulated loopback endpoint only
  (`crew.py` refuses every non-loopback URL). No task points dispatch
  anywhere else; no real emergency service is ever contacted.
- No face/web feature work. The face is a design reference only; demo
  capture is KERNEL ONLY — no face, no web page, no browser shots.
- No padded counts. Every number in a proof was produced by the command
  the proof names, run on the tree the proof names.
- Every proof is a committed file: a log, a screendump, a receipt, or
  gate output. If the file is not committed, the task is not done.

## §1 Baseline re-verification of current main (OC1B-001..OC1B-025)

- **OC1B-001** Pull current main into a fresh clean clone on the Mac and record the exact tip sha the whole baseline runs against. Proof: os-build/logs/OC1B-baseline-tip.txt with the sha and `git status` clean output.
- **OC1B-002** Record the Mac toolchain versions the baseline used (cargo, rustc nightly, qemu-system-x86_64, python3, node). Proof: os-build/logs/OC1B-baseline-toolchain.txt.
- **OC1B-003** Run `os-build/gate.sh` end to end on the clean clone and save the full output. Proof: os-build/logs/OC1B-baseline-gate.log ending in the GATE GREEN or GATE RED line, as it fell.
- **OC1B-004** Extract the gate's alive assertion from the baseline boot serial (`META OS KERNEL - alive`). Proof: the quoted line with its line number in os-build/logs/OC1B-baseline-serial.txt.
- **OC1B-005** Extract the gate's memory assertion (`mem summary: K4 up`) from the baseline serial. Proof: the quoted line in os-build/logs/OC1B-baseline-serial.txt.
- **OC1B-006** Extract the ring-3 assertion (`HELLO FROM USERSPACE`) and the clean-exit assertion (`user exit code 0`) from the baseline serial. Proof: both quoted lines in os-build/logs/OC1B-baseline-serial.txt.
- **OC1B-007** Extract the fault-isolation assertion (`task killed`) from the baseline serial and confirm the sleeper continues after it. Proof: the fault line plus the first sleeper line after it, quoted in os-build/logs/OC1B-baseline-serial.txt.
- **OC1B-008** Extract the readkey assertion (`user readkey: entry`) from the baseline serial. Proof: the quoted line in os-build/logs/OC1B-baseline-serial.txt.
- **OC1B-009** Extract the shell assertions (`commands: status help` and `STATUS tasks=`) from the baseline serial. Proof: both quoted lines in os-build/logs/OC1B-baseline-serial.txt.
- **OC1B-010** Grep the baseline serial for `panic` and for `loader refused`; both counts must be 0 for a green baseline. Proof: the two grep counts recorded in os-build/logs/OC1B-baseline-gate.log.
- **OC1B-011** Record the bootimage size and sha256 the baseline gate built. Proof: os-build/logs/OC1B-baseline-image.txt with path `kernel/target/x86_64-unknown-none/debug/bootimage-metaos-kernel.bin`, size, and sha256.
- **OC1B-012** Boot the baseline image interactively and save a screendump at the shell after boot completes. Proof: os-build/captures/oc1b-baseline-shell.png.
- **OC1B-013** In the same boot, run `fetch` at the shell and save the screendump. Proof: os-build/captures/oc1b-baseline-fetch.png.
- **OC1B-014** Drive a typed session with `os-build/tools/drive.py` (help, status, status again) and save the serial so the tick movement is on record. Proof: os-build/logs/OC1B-baseline-drive.txt with two STATUS lines whose ticks differ.
- **OC1B-015** Type `mem` and `ps` in that session and confirm the ps rows match the gate's program set (hello, sleeper, crasher, readkey). Proof: the mem and ps output quoted in os-build/logs/OC1B-baseline-drive.txt.
- **OC1B-016** Send the bad syscall 99 path via the crasher/drill route the gate uses and confirm the refusal line appears on the baseline tree. Proof: the `bad call refused` line quoted in os-build/logs/OC1B-baseline-drive.txt.
- **OC1B-017** Run gate.sh a second time on the untouched clone and compare the two gate logs assertion by assertion. Proof: os-build/logs/OC1B-baseline-gate2.log plus a one-line same/different verdict per assertion in the status file.
- **OC1B-018** Diff the baseline serial against `os-build/logs/WAVE3-combined-serial.txt` and list every line class that is new, missing, or changed. Proof: os-build/logs/OC1B-baseline-diff.md.
- **OC1B-019** Measure wall-clock time for one full gate.sh run on this Mac and record it. Proof: the timing line appended to os-build/logs/OC1B-baseline-gate.log.
- **OC1B-020** Verify the four userspace binaries the gate builds (hello, sleeper, crasher, readkey) each exist under `os-build/userspace/user/target` after the run. Proof: the `ls -l` output in os-build/logs/OC1B-baseline-userspace.txt.
- **OC1B-021** Confirm the clone is still clean after all baseline runs (no stray writes into the tree). Proof: `git status --porcelain` output, empty or every line explained, in the status file.
- **OC1B-022** Write the baseline verdict: tip sha, gate result, panic count, and every assertion's state in one block. Proof: the Baseline section of os-build/OPENCODE1_500_STATUS.md.
- **OC1B-023** If any baseline assertion failed, write the failing line and the full log path as the section result and STOP the kernel sections until Pax rules. Proof: the failure block in os-build/OPENCODE1_500_STATUS.md naming the failing assertion verbatim.
- **OC1B-024** Record which wave-3 status items this baseline supersedes (wave-3 §2 soak and §8 numbers still stand open until §7/§18 here close them). Proof: the supersede note in os-build/OPENCODE1_500_STATUS.md.
- **OC1B-025** Commit the baseline artifacts on `opencode/500` as the section checkpoint. Proof: the commit sha recorded in os-build/OPENCODE1_500_STATUS.md.

## §2 Kernel-face Mac gates I — KF-01 bootloader spike (OC1B-026..OC1B-050)

Grounded in `os-build/KERNEL_FACE_BUILD_ORDER.md` (KF-01) and
`os-build/KERNEL_FACE_TASKS.md` §A. Rowan writes; you prove. The spike
gets TWO attempts, maximum. The two prior failed attempts (bootloader
0.11 std-fail, 0.10.9 API-fail, evidence on `opencode/round7`) count as
history, not as attempts in this count.

- **OC1B-026** Record the starting point before any spike work: the bootloader pin in `kernel/Cargo.toml` and the `Cargo.lock` hash on Rowan's spike branch tip. Proof: os-build/logs/OC1B-kf01-start.txt with the pin line and lock hash.
- **OC1B-027** Save the control screendump: the current 0.9.35 text-mode boot at the shell, before any change. Proof: os-build/captures/oc1b-kf01-control-textboot.png.
- **OC1B-028** Save the control serial for the same boot. Proof: os-build/logs/OC1B-kf01-control-serial.txt with alive line and panic count 0.
- **OC1B-029** Pull Rowan's KF-01 attempt-1 branch at its exact tip sha and record what it changes (files + the bootloader version it pins), and confirm the candidate is a FRESH candidate under the KF-01 budget — a new candidate (0.11.x line first), never a blind re-run of the round7 pair (0.10.9 API-fail, 0.11 std-fail), which neither counts against the budget nor may be re-run. Proof: os-build/logs/OC1B-kf01-attempt1-branch.txt with `git diff --stat` against main and the fresh-candidate confirmation line.
- **OC1B-030** Build attempt 1 (`cargo bootimage` in `kernel/`) and save the complete build output, success or failure. Proof: os-build/logs/OC1B-kf01-attempt1-build.log.
- **OC1B-031** If attempt 1 builds, boot it in QEMU and save the serial. Proof: os-build/logs/OC1B-kf01-attempt1-serial.txt.
- **OC1B-032** If attempt 1 boots, save its screendump at the first stable screen. Proof: os-build/captures/oc1b-kf01-attempt1.png (a black or partial screen is committed as-is and named as such in the status file).
- **OC1B-033** Classify attempt 1 in the build order's terms: build-fail (std), build-fail (API), boot-fail, boots-no-framebuffer, or boots-with-framebuffer. Proof: the classification line with the deciding log excerpt in os-build/logs/OC1B-kf01-attempt1-verdict.md.
- **OC1B-034** Check attempt 1's BootInfo for a framebuffer field the kernel can read (Rowan's probe line in serial, or the named absence). Proof: the probe line or the absence note quoted in os-build/logs/OC1B-kf01-attempt1-verdict.md.
- **OC1B-035** If attempt 1 failed, pull Rowan's attempt-2 branch at its exact tip and record how its approach differs from attempt 1, and confirm it is the second and last FRESH candidate under the KF-01 budget — a new candidate, not a re-run of attempt 1's candidate and not either of the round7 pair. Proof: os-build/logs/OC1B-kf01-attempt2-branch.txt with the diff stat, the difference note, and the fresh-candidate confirmation line.
- **OC1B-036** Build attempt 2 and save the complete build output. Proof: os-build/logs/OC1B-kf01-attempt2-build.log.
- **OC1B-037** If attempt 2 builds, boot it and save the serial. Proof: os-build/logs/OC1B-kf01-attempt2-serial.txt.
- **OC1B-038** If attempt 2 boots, save its screendump at the first stable screen. Proof: os-build/captures/oc1b-kf01-attempt2.png.
- **OC1B-039** Classify attempt 2 in the same five terms as OC1B-033. Proof: os-build/logs/OC1B-kf01-attempt2-verdict.md with the deciding excerpt.
- **OC1B-040** Make NO third attempt: if both attempts failed, record the hard stop in the status file and name the fallback as the next task. Proof: the hard-stop line in os-build/OPENCODE1_500_STATUS.md.
- **OC1B-041** On the failure path, restore the 0.9.35 pin exactly (Rowan's restore commit or the recorded pin from OC1B-026) and verify `kernel/Cargo.toml` and `Cargo.lock` match the start record. Proof: the pin line and lock hash in os-build/logs/OC1B-kf01-restored.txt matching OC1B-kf01-start.txt.
- **OC1B-042** On the failure path, re-run gate.sh on the restored tree; it must come back GREEN 7/7. Proof: os-build/logs/OC1B-kf01-restored-gate.log.
- **OC1B-043** On the success path, run gate.sh on the upgraded tree and record which text assertions still pass unchanged. Proof: os-build/logs/OC1B-kf01-upgraded-gate.log with a per-assertion verdict.
- **OC1B-044** On the success path, record the upgraded stack's numbers: bootloader version, build time, bootimage size delta vs OC1B-011. Proof: os-build/logs/OC1B-kf01-success-numbers.txt.
- **OC1B-045** Write the KF-01 decision record: attempts, classifications, evidence paths, and the route the evidence picks (upgraded stack or restored pin). Proof: os-build/logs/OC1B-kf01-decision.md.
- **OC1B-046** Record the KF-01 timebox: elapsed Mac-lane time from first spike build to decision. Proof: the elapsed line in os-build/logs/OC1B-kf01-decision.md.
- **OC1B-047** Verify no spike branch touched `kernel/src/syscalls.rs`. Proof: the empty `git diff` output for that path on both attempt branches, quoted in os-build/logs/OC1B-kf01-decision.md.
- **OC1B-048** Post the KF-01 verdict block into the status file for Pax's merge read (branch, tip, decision, evidence paths). Proof: the KF-01 block in os-build/OPENCODE1_500_STATUS.md.
- **OC1B-049** If the spike is still waiting on Rowan's branch at your pass, record BLOCKED with the missing branch named and move to the next unblocked section. Proof: the BLOCKED line in os-build/OPENCODE1_500_STATUS.md.
- **OC1B-050** Commit the KF-01 gate artifacts on `opencode/500`. Proof: the commit sha in os-build/OPENCODE1_500_STATUS.md.

## §3 Kernel-face Mac gates II — framebuffer, pixel text, graphics boot (OC1B-051..OC1B-075)

Grounded in `os-build/KERNEL_FACE_BUILD_ORDER.md` (KF-02..KF-10) and
`os-build/KERNEL_FACE_TASKS.md` §B–§C. Each task runs on the Rowan
branch named in the status file when that KF piece lands; three
screendumps per milestone step is the standing evidence shape.

- **OC1B-051** Gate KF-02: on the upgraded-stack tree, run the full gate and confirm the text boot is intact end to end. Proof: os-build/logs/OC1B-kf02-gate.log with GATE GREEN and the serial committed beside it.
- **OC1B-052** Gate KF-03 (framebuffer wiring): boot Rowan's wiring branch and confirm the kernel constructs the framebuffer from BootInfo (init line in serial or the named probe). Proof: os-build/logs/OC1B-kf03-serial.txt with the init line quoted in the status file.
- **OC1B-053** Record the framebuffer's reported geometry from that boot: resolution, pitch, pixel format. Proof: the geometry lines in os-build/logs/OC1B-kf03-serial.txt.
- **OC1B-054** Screendump the KF-03 first drawn screen (whatever the wiring draws first — clear colour counts). Proof: os-build/captures/oc1b-kf03-firstdraw.png.
- **OC1B-055** Run Rowan's fill test (KERNEL_FACE_TASKS A4: red screen, then blue) and screendump the red frame. Proof: os-build/captures/oc1b-kf03-red.png.
- **OC1B-056** Screendump the blue frame of the same fill test. Proof: os-build/captures/oc1b-kf03-blue.png.
- **OC1B-057** Gate KF-04 (pixel text): boot the pixel-console branch and screendump the first screen with glyphs drawn. Proof: os-build/captures/oc1b-kf04-text.png.
- **OC1B-058** Compare the pixel text against the VGA text of the same boot lines for legibility (same words, readable, no clipped glyphs). Proof: the side-by-side note with both screendumps named in os-build/logs/OC1B-kf04-verdict.md.
- **OC1B-059** Exercise the pixel console's scroll: drive enough boot/status output to scroll and screendump after the scroll. Proof: os-build/captures/oc1b-kf04-scrolled.png plus the serial in os-build/logs/OC1B-kf04-serial.txt.
- **OC1B-060** Gate KF-05 (graphics boot sequence): capture the three-screendump set — text phase, transition, first graphics frame — in one boot. Proof: os-build/captures/oc1b-kf05-text.png, os-build/captures/oc1b-kf05-transition.png, os-build/captures/oc1b-kf05-graphics.png.
- **OC1B-061** Confirm from that boot's serial that every text-phase claim line (alive, programs, isolation) still appears before graphics starts. Proof: os-build/logs/OC1B-kf05-serial.txt with the claim lines quoted in order.
- **OC1B-062** Gate KF-06 (kernel-drawn ribbon boot screen): screendump the boot screen with the blue ribbon drawn by the kernel. Proof: os-build/captures/oc1b-kf06-ribbon.png.
- **OC1B-063** Prove the ribbon is the product ribbon, not a placeholder shape: compare its curve against `js/logo-background.js`'s ribbon math output as rendered in the reference face. Proof: the comparison note with both images named in os-build/logs/OC1B-kf06-verdict.md.
- **OC1B-064** Gate KF-07 (animation + exit): screendump the ribbon at two phases at least one second apart. Proof: os-build/captures/oc1b-kf07-phase1.png and os-build/captures/oc1b-kf07-phase2.png, visibly different.
- **OC1B-065** In the same boot, send a keypress and confirm the boot screen exits to the shell/desktop state Rowan wired. Proof: the serial lines around the keypress in os-build/logs/OC1B-kf07-serial.txt plus os-build/captures/oc1b-kf07-afterkey.png.
- **OC1B-066** Gate KF-08 (graphics-failure fallback): boot with Rowan's named graphics-fail switch and confirm the machine stays on the text console and prints why. Proof: os-build/logs/OC1B-kf08-serial.txt with the fallback reason line and os-build/captures/oc1b-kf08-text.png.
- **OC1B-067** In the fallback boot, confirm the shell still answers status on the text console. Proof: the STATUS line quoted from os-build/logs/OC1B-kf08-serial.txt.
- **OC1B-068** Gate KF-09 (window primitives): screendump the first window frame Rowan's primitives draw (rect + title bar). Proof: os-build/captures/oc1b-kf09-window.png.
- **OC1B-069** Gate KF-10 (real shell in a window): screendump the window with `status` typed and answered inside it. Proof: os-build/captures/oc1b-kf10-status.png.
- **OC1B-070** In the same window session, screendump `mem` answered inside the window. Proof: os-build/captures/oc1b-kf10-mem.png.
- **OC1B-071** In the same window session, screendump `ps` answered inside the window with the task rows visible. Proof: os-build/captures/oc1b-kf10-ps.png.
- **OC1B-072** Cross-check the window's status numbers against the same boot's serial status output; they must agree. Proof: the two number sets quoted in os-build/logs/OC1B-kf10-verdict.md.
- **OC1B-073** Run gate.sh on the KF-10 tree; the text claims must still gate GREEN (graphics is additive, never a replacement). Proof: os-build/logs/OC1B-kf10-gate.log.
- **OC1B-074** Count panics across every §3 boot serial; the count must be 0, and any exception is quoted, not summarised away. Proof: the per-boot panic counts in os-build/logs/OC1B-s3-panics.txt.
- **OC1B-075** Commit the §3 gate artifacts and write the per-KF verdict block (KF-02..KF-10: GATED / BLOCKED-on-Rowan / FAILED with the deciding file). Proof: the §3 block in os-build/OPENCODE1_500_STATUS.md plus the commit sha.

## §4 Kernel-face Mac gates III — KF-11 proof pack, Milestones 2–3 (OC1B-076..OC1B-100)

Grounded in `os-build/KERNEL_FACE_BUILD_ORDER.md` (KF-11..KF-20) and
`os-build/KERNEL_FACE_TASKS.md` §D–§H. Milestone 1's definition of done:
turn on → kernel boots (text phase intact) → the kernel itself draws
the blue-ribbon boot screen and a desktop with one window holding the
REAL shell answering status/mem/ps — proven by KF-11's committed
serial log + three-screendump set + gate GREEN for the same tree.

- **OC1B-076** Assemble the KF-11 pack inputs for one named tree sha: the full serial log of a Milestone-1 boot. Proof: os-build/logs/KF11-serial.txt with the tree sha in its first line.
- **OC1B-077** Save the KF-11 three-screendump set from that same boot: boot screen, desktop, shell window answering. Proof: os-build/captures/kf11-bootscreen.png, os-build/captures/kf11-desktop.png, os-build/captures/kf11-shellwindow.png.
- **OC1B-078** Run gate.sh on the KF-11 tree and save its output into the pack. Proof: os-build/logs/KF11-gate.log with GATE GREEN 7/7.
- **OC1B-079** Verify Milestone-1 clause 1 from the pack: the text phase is intact (alive, three programs, fault isolation lines all present before graphics). Proof: the quoted lines in os-build/logs/KF11-proof.md.
- **OC1B-080** Verify Milestone-1 clause 2: the boot screen is kernel-drawn (no browser, no Linux underneath — the boot is the bare-metal image). Proof: the image path and boot method recorded in os-build/logs/KF11-proof.md.
- **OC1B-081** Verify Milestone-1 clause 3: the shell in the window answers with real state — status ticks move between two answers inside the window session. Proof: the two in-window status readings quoted in os-build/logs/KF11-proof.md with both screendumps named.
- **OC1B-082** Verify the keyboard path in the KF-11 boot: the commands in the window were typed on the real keyboard path (sendkey through the monitor), not injected state. Proof: the drive method and monitor commands recorded in os-build/logs/KF11-proof.md.
- **OC1B-083** Reproduce KF-11 from a clean clone of the same tree sha and confirm the pack regenerates. Proof: os-build/logs/KF11-repro-serial.txt plus a same/different line per pack artifact in os-build/logs/KF11-proof.md.
- **OC1B-084** Write the KF-11 verdict for Pax: Milestone 1 PROVEN or the exact clause that failed, with its file. Proof: the KF-11 block in os-build/OPENCODE1_500_STATUS.md.
- **OC1B-085** Gate KF-12 (mouse): boot Rowan's mouse branch and record the PS/2 packet counts from the serial after moving the pointer. Proof: os-build/logs/OC1B-kf12-serial.txt with the packet-count lines quoted in the status file.
- **OC1B-086** Screendump the KF-12 cursor at two positions. Proof: os-build/captures/oc1b-kf12-pos1.png and os-build/captures/oc1b-kf12-pos2.png.
- **OC1B-087** Gate KF-13 (clicks/focus): with two windows open, screendump focus on the first window. Proof: os-build/captures/oc1b-kf13-focus1.png.
- **OC1B-088** Click the second window and screendump the focus switch. Proof: os-build/captures/oc1b-kf13-focus2.png.
- **OC1B-089** Record the click coordinates the compositor logged for the KF-13 switch. Proof: the coordinate lines in os-build/logs/OC1B-kf13-serial.txt.
- **OC1B-090** Gate KF-14 (compositor): screendump two overlapping windows with the raised window's title bar active. Proof: os-build/captures/oc1b-kf14-overlap.png.
- **OC1B-091** Drag a window by its title bar and screendump the result. Proof: os-build/captures/oc1b-kf14-drag.png.
- **OC1B-092** Gate KF-15 (dashboard from real kernel state): screendump the dashboard window and record its card values. Proof: os-build/captures/oc1b-kf15-dashboard.png.
- **OC1B-093** Cross-check every KF-15 card value against the same boot's shell output (frames free, heap, task count, uptime); any mismatch is a FAILED gate, quoted. Proof: os-build/logs/OC1B-kf15-crosscheck.md.
- **OC1B-094** Gate KF-16 (settings): flip the bar/mode setting and screendump the desktop before and after. Proof: os-build/captures/oc1b-kf16-before.png and os-build/captures/oc1b-kf16-after.png.
- **OC1B-095** Gate KF-17 (face soak): run the graphics boot for 30 minutes with the ribbon animating and the console task answering in its window (KERNEL_FACE_TASKS G5 shape). Proof: os-build/logs/OC1B-kf17-soak.txt with start/end times, the mid-soak status answer, and panic count.
- **OC1B-096** Gate KF-18 (recording): capture the 60-second full-boot recording into the face as a demo asset. Proof: the recording file under os-build/captures/ with its ffprobe duration line recorded in the status file (asset, not proof — the logs above are the proof).
- **OC1B-097** Gate KF-19 (honest write-up check): read Rowan's KERNEL_FACE final note and verify each of its claims against your committed dumps; list any claim with no dump. Proof: os-build/logs/OC1B-kf19-claimcheck.md.
- **OC1B-098** Gate KF-20 (gate extension): run gate.sh plus the face boot log as the second artifact on the final graphics tree; both must exist and the gate must be GREEN. Proof: os-build/logs/OC1B-kf20-gate.log and the face boot serial path recorded beside it.
- **OC1B-099** For every KF-12..KF-20 piece Rowan has not landed, record it UNIMPLEMENTED with the missing branch named — never gate what does not exist. Proof: the unimplemented list in os-build/OPENCODE1_500_STATUS.md.
- **OC1B-100** Commit the §4 artifacts and write the Milestone 2/3 verdict block. Proof: the §4 block in os-build/OPENCODE1_500_STATUS.md plus the commit sha.

## §5 K3 Mac gate pack — demand paging (OC1B-101..OC1B-125)

Grounded in `os-build/K3_DEMAND_PAGING_DESIGN.md` (approved design:
faults retried only under six named conditions, per-task promised
regions registered by the loader, zero-fill only, exactly one demand
program) §7 — the Mac gate pack is three legs in ONE boot: the demand
leg, crasher containment, and the outside-region negative, with no
panic. Milo gate-1 GREENed the build @7bb7207; the merge waits on this
pack, read by Pax.

- **OC1B-101** Record the K3 tree under gate: Rowan's K3 build branch tip sha and its diff stat against main. Proof: os-build/logs/OC1B-k3-tree.txt.
- **OC1B-102** Confirm from the branch diff that `kernel/src/syscalls.rs` is untouched by the K3 build. Proof: the empty diff for that path quoted in os-build/logs/OC1B-k3-tree.txt.
- **OC1B-103** Build the K3 tree's bootimage on the Mac and save the build output. Proof: os-build/logs/OC1B-k3-build.log.
- **OC1B-104** Boot the K3 image once and save the full serial for the whole gate-pack run. Proof: os-build/logs/OC1B-k3-gatepack-serial.txt.
- **OC1B-105** Demand leg, part 1: from that serial, quote the demand program's first fault on its promised region. Proof: the fault line quoted in os-build/logs/OC1B-k3-gatepack.md.
- **OC1B-106** Demand leg, part 2: quote the map/zero-fill line that answers the fault. Proof: the map line quoted in os-build/logs/OC1B-k3-gatepack.md.
- **OC1B-107** Demand leg, part 3: quote the resumed program's completion (its exit line after the fault was serviced). Proof: the exit line quoted in os-build/logs/OC1B-k3-gatepack.md.
- **OC1B-108** Confirm the demand program read back the zero-filled page contents it expected (its own check line in serial). Proof: the check line quoted in os-build/logs/OC1B-k3-gatepack.md.
- **OC1B-109** Crasher containment leg: quote the crasher's kill line from the same boot. Proof: the kill line quoted in os-build/logs/OC1B-k3-gatepack.md.
- **OC1B-110** Crasher containment leg, part 2: quote a surviving task's line AFTER the crasher's kill (containment means the machine kept working). Proof: the survivor line quoted in os-build/logs/OC1B-k3-gatepack.md.
- **OC1B-111** Outside-region negative, part 1: quote the fault raised by an access outside every promised region. Proof: the fault line quoted in os-build/logs/OC1B-k3-gatepack.md.
- **OC1B-112** Outside-region negative, part 2: quote the refusal/kill that follows it — the page must NOT be mapped. Proof: the refusal line quoted in os-build/logs/OC1B-k3-gatepack.md.
- **OC1B-113** Confirm no page was silently mapped for the negative leg: the demand map count in the serial equals the demand leg's count alone. Proof: the counted map lines listed in os-build/logs/OC1B-k3-gatepack.md.
- **OC1B-114** Grep the gate-pack serial for `panic`; the count must be 0. Proof: the grep count recorded in os-build/logs/OC1B-k3-gatepack.md.
- **OC1B-115** After all three legs, drive the shell in the same boot: status, mem, ps all answered. Proof: the three answers quoted in os-build/logs/OC1B-k3-gatepack.md.
- **OC1B-116** Record which mapper root the build used (shared mapper root + promised-region check, or per-task roots) exactly as the serial/code shows it — the isolation basis Pax reconciles against the design. Proof: the basis note in os-build/logs/OC1B-k3-gatepack.md naming the serial lines or code paths observed.
- **OC1B-117** Run gate.sh on the K3 tree; the seven text assertions must still pass. Proof: os-build/logs/OC1B-k3-gate.log.
- **OC1B-118** Repeat the gate-pack boot a second time and confirm the three legs reproduce. Proof: os-build/logs/OC1B-k3-gatepack2-serial.txt with a same/different line per leg in os-build/logs/OC1B-k3-gatepack.md.
- **OC1B-119** Run the demand program in a loop (10 faults-and-resumes) in one boot and record the fault counter's end state. Proof: the loop lines in os-build/logs/OC1B-k3-loop-serial.txt.
- **OC1B-120** K3 short soak: 30 minutes on the K3 image with the demand program and the standard program set running. Proof: os-build/logs/OC1B-k3-soak.txt with duration, fault count, and panic count.
- **OC1B-121** Verify readkey still works on the K3 tree (typed byte received, got= line). Proof: the readkey lines quoted in os-build/logs/OC1B-k3-gatepack.md.
- **OC1B-122** Verify the anti-loop guards are observable: a task faulting repeatedly on the same promised address is stopped, per the design's two guards. Proof: the guard line quoted in os-build/logs/OC1B-k3-gatepack.md, or the named UNPROVEN line if the build exposes no such case.
- **OC1B-123** Write the K3 gate-pack verdict for Pax: one line per §7 leg — PROVEN or the failing line — plus the merge recommendation the evidence supports. Proof: os-build/logs/OC1B-k3-gatepack.md completed with its verdict block.
- **OC1B-124** Record the exact tree sha the pack ran on and confirm the pack's serial came from that tree's image (sha256 beside it). Proof: the sha + image hash lines in os-build/logs/OC1B-k3-gatepack.md.
- **OC1B-125** Commit the K3 pack artifacts on `opencode/500`. Proof: the commit sha in os-build/OPENCODE1_500_STATUS.md.

## §6 K4 Mac gate pack — IPC talker/listener (OC1B-126..OC1B-150)

Grounded in `os-build/K4_IPC_DESIGN.md` and Pax's review
`os-build/K4_REVIEW_PAX.md` (APPROVE WITH CHANGES): syscalls 6 =
ipc_send, 7 = ipc_recv, dispatched in `user.rs` only; one-message
non-blocking mailboxes, kernel-owned storage, unforgeable sender id.
The acceptance lines are the review's pinned gate lines: send,
receive, full box, dead destination, unmapped buffer, undersized
buffer, empty receive — each quoted verbatim from one serial.

- **OC1B-126** Extract the review's pinned gate lines from `os-build/K4_REVIEW_PAX.md` §7 into a checklist before booting anything. Proof: os-build/logs/OC1B-k4-checklist.md listing all seven expected lines.
- **OC1B-127** Record the K4 tree under gate: Rowan's K4 build branch tip sha, its diff stat, and confirmation the diff routes dispatch through `kernel/src/user.rs`. Proof: os-build/logs/OC1B-k4-tree.txt.
- **OC1B-128** Confirm the K4 branch diff for `kernel/src/syscalls.rs` is empty. Proof: the empty diff quoted in os-build/logs/OC1B-k4-tree.txt.
- **OC1B-129** Confirm the task table was NOT grown: the build swaps demo programs and MAX_TASKS stays 8 (review ruling Q-I1). Proof: the MAX_TASKS line quoted from the branch's source in os-build/logs/OC1B-k4-tree.txt.
- **OC1B-130** Build the K4 image on the Mac and save the build output. Proof: os-build/logs/OC1B-k4-build.log.
- **OC1B-131** Boot the K4 image with the talker/listener pair and save the full serial. Proof: os-build/logs/OC1B-k4-gatepack-serial.txt.
- **OC1B-132** Acceptance line 1 (send): quote the talker's ipc_send success line verbatim. Proof: the line quoted in os-build/logs/OC1B-k4-gatepack.md.
- **OC1B-133** Acceptance line 2 (receive): quote the listener's ipc_recv success line verbatim. Proof: the line quoted in os-build/logs/OC1B-k4-gatepack.md.
- **OC1B-134** Payload equality: confirm the string the listener received is byte-identical to the string the talker sent, from the serial. Proof: both payload strings quoted side by side in os-build/logs/OC1B-k4-gatepack.md.
- **OC1B-135** Sender identity: confirm the received sender_id is the talker's loader-table id (unforgeable — set by the kernel, not the sender). Proof: the id lines quoted in os-build/logs/OC1B-k4-gatepack.md.
- **OC1B-136** Acceptance line 3 (full box): fill the listener's one-message mailbox, send again, and quote the full-box refusal line verbatim. Proof: the line quoted in os-build/logs/OC1B-k4-gatepack.md.
- **OC1B-137** Acceptance line 4 (dead destination): send to a task that has exited and quote the dead-destination refusal line verbatim. Proof: the line quoted in os-build/logs/OC1B-k4-gatepack.md.
- **OC1B-138** Acceptance line 5 (unmapped buffer): send from an unmapped buffer address and quote the refusal line verbatim. Proof: the line quoted in os-build/logs/OC1B-k4-gatepack.md.
- **OC1B-139** Acceptance line 6 (undersized buffer): receive into a too-small buffer and quote the refusal line verbatim. Proof: the line quoted in os-build/logs/OC1B-k4-gatepack.md.
- **OC1B-140** Acceptance line 7 (empty receive): receive from an empty mailbox and quote the empty result line verbatim (the sentinel, no block). Proof: the line quoted in os-build/logs/OC1B-k4-gatepack.md.
- **OC1B-141** Non-blocking proof: after the empty receive, the listener's next scheduled line appears without any send intervening (it did not park). Proof: the following line quoted in os-build/logs/OC1B-k4-gatepack.md.
- **OC1B-142** Peer-discovery proof (review change 1): quote how the talker learned the listener's id — the loader-table/fixed spawn-order mechanism, from the serial or the named source. Proof: the mechanism note in os-build/logs/OC1B-k4-gatepack.md.
- **OC1B-143** Mailbox clearing on exit: after the listener exits, a send to its old slot returns the dead-destination refusal, not a delivery. Proof: the lines quoted in os-build/logs/OC1B-k4-gatepack.md.
- **OC1B-144** Mailbox clearing on the KILL path (review change 3): kill the peer via the fault path, then send to its slot and quote the refusal. Proof: the lines quoted in os-build/logs/OC1B-k4-gatepack.md.
- **OC1B-145** Squatting limitation (review change 2): record whether any live task can occupy the console's mailbox slot in this build, exactly as observed — limitation named, not hidden. Proof: the observation note in os-build/logs/OC1B-k4-gatepack.md.
- **OC1B-146** Copy-semantics proof: after a receive, have the sender overwrite its buffer and confirm the received copy is unchanged (kernel copied, no shared page). Proof: the before/after payload lines quoted in os-build/logs/OC1B-k4-gatepack.md, or the named UNPROVEN line if the demo pair cannot show it.
- **OC1B-147** Grep the K4 gate-pack serial for `panic`; count must be 0, and the shell must still answer status after the full acceptance run. Proof: the count and the STATUS line in os-build/logs/OC1B-k4-gatepack.md.
- **OC1B-148** Run gate.sh on the K4 tree; the seven text assertions must still pass. Proof: os-build/logs/OC1B-k4-gate.log.
- **OC1B-149** K4 short soak: 20 minutes with the talker/listener pair looping sends/receives; record messages completed and any refusal anomalies. Proof: os-build/logs/OC1B-k4-soak.txt.
- **OC1B-150** Write the K4 gate-pack verdict for Pax (one line per pinned line: PROVEN verbatim or FAILED with the actual line), and commit the §6 artifacts. Proof: the verdict block completing os-build/logs/OC1B-k4-gatepack.md plus the commit sha in os-build/OPENCODE1_500_STATUS.md.

## §7 Soaks — verdicts and fresh runs (OC1B-151..OC1B-175)

Folds in wave-3 §2 (tasks 11–16) and expands it. START-ORDER NOTE:
OC1B-151..155 run FIRST in this whole list (wave-3 critical).

- **OC1B-151** Find the wave-2 §19 soak's remains on this Mac (its log path from the wave-2 status, under /tmp or the session dir) and record where it ended. Proof: os-build/logs/OC1B-soak-wave2-verdict.md naming the found log path or the named absence.
- **OC1B-152** If the wave-2 soak log survives, copy its tail (last 200 lines) into the repo and extract its panic count and last timestamp. Proof: os-build/logs/OC1B-soak-wave2-tail.txt with the counts.
- **OC1B-153** If the wave-2 soak died with its session, write that verdict plainly — died-with-session, duration unknown — instead of reconstructing one. Proof: the verdict line in os-build/logs/OC1B-soak-wave2-verdict.md.
- **OC1B-154** Record the wave-2 soak's start time and image sha if the remains carry them; mark each field found or NOT RECOVERABLE. Proof: the field table in os-build/logs/OC1B-soak-wave2-verdict.md.
- **OC1B-155** Close the wave-2 soak question in the status file with the verdict Pax reads (COMPLETED / DIED WITH SESSION / NEVER STARTED), evidence path beside it. Proof: the soak-verdict line in os-build/OPENCODE1_500_STATUS.md.
- **OC1B-156** Start the fresh 2-hour soak on the current combined main image; record image sha256, start time, and the serial path at start. Proof: os-build/logs/OC1B-soak-main-start.txt.
- **OC1B-157** During the main soak, run the userspace pack drills (hello, sleeper, crasher, readkey) 10 times and log each run's result (wave-3 §2 task 13). Proof: os-build/logs/OC1B-soak-main-drills.txt with 10 result lines.
- **OC1B-158** At the main soak's midpoint, grep its serial for panics and record the running count and uptime. Proof: the midpoint line appended to os-build/logs/OC1B-soak-main-start.txt.
- **OC1B-159** At the main soak's end, record the verdict: duration, panic count, anomaly count with each anomaly's serial excerpt. Proof: os-build/logs/OC1B-soak-main-verdict.md (wave-3 §2 task 15's WAVE3_SOAK successor).
- **OC1B-160** If the main soak is still running when you reach the last section you can run, leave its log path + start time marked RUNNING in the status file (wave-3 §2 task 16). Proof: the RUNNING line in os-build/OPENCODE1_500_STATUS.md.
- **OC1B-161** Run a 1-hour soak on the K3 tree image after §5 gates it, with the demand program in its loop. Proof: os-build/logs/OC1B-soak-k3.txt with duration, demand-fault count, panic count.
- **OC1B-162** Run a 1-hour soak on the K4 tree image after §6 gates it, with the talker/listener pair looping. Proof: os-build/logs/OC1B-soak-k4.txt with duration, message count, panic count.
- **OC1B-163** Run a 30-minute INTERACTIVE soak on the MERGED graphics tree (the main tip after Pax merges the KF work — a different tree from OC1B-095's branch gate): ribbon animating while you drive the shell window (status/mem/ps) and move the pointer every 5 minutes across the whole run, so the soak carries input load, not just animation. Proof: os-build/logs/OC1B-soak-kf.txt with duration, panic count, and the six timed interaction entries with their answers.
- **OC1B-164** Run a 2-hour soak on the FINAL combined tree Pax assembles for submission (the last kernel-touching merge wave's tree), started as soon as that tree exists. Proof: os-build/logs/OC1B-soak-final-start.txt with tree sha and start time.
- **OC1B-165** Record the final soak's verdict the same way as OC1B-159. Proof: os-build/logs/OC1B-soak-final-verdict.md.
- **OC1B-166** Compare all soak verdicts in this section against the R5-5 record (73 minutes, 0 panics) and state plainly whether stability held, improved, or regressed. Proof: the comparison block in os-build/logs/OC1B-soak-summary.md.
- **OC1B-167** For every soak anomaly anywhere in this section, file the anomaly's full serial context (±20 lines) — no anomaly is reported as a bare count. Proof: os-build/logs/OC1B-soak-anomalies.txt.
- **OC1B-168** Verify each soak's image sha256 matches the tree its verdict names (a soak on the wrong image proves nothing). Proof: the sha table in os-build/logs/OC1B-soak-summary.md.
- **OC1B-169** Record total soak machine-time accumulated in this section. Proof: the total line in os-build/logs/OC1B-soak-summary.md.
- **OC1B-170** Run one soak-boot with the monitor attached the whole run and confirm screendump still answers at the end (the display path survives a long run). Proof: os-build/captures/oc1b-soak-end.png.
- **OC1B-171** During the final soak, drive one mid-soak shell session (status/mem/ps) and save it. Proof: os-build/logs/OC1B-soak-final-drive.txt.
- **OC1B-172** Confirm no soak in this section was shortened silently: every verdict's duration is measured from its own start record, never estimated. Proof: the duration-derivation note in os-build/logs/OC1B-soak-summary.md.
- **OC1B-173** If any soak cannot run (Mac time, blocked tree), record it NOT RUN with the reason — a missing soak is a named gap, not a skipped line. Proof: the NOT RUN lines in os-build/logs/OC1B-soak-summary.md.
- **OC1B-174** Write the soak section's one-paragraph plain verdict for the submission's stability claim. Proof: the paragraph in os-build/logs/OC1B-soak-summary.md.
- **OC1B-175** Commit the §7 artifacts. Proof: the commit sha in os-build/OPENCODE1_500_STATUS.md.

## §8 Combined-tree re-proofs after merge waves (OC1B-176..OC1B-200)

Trigger rule: a re-proof wave runs ONLY when Pax lands a merge wave
that touches `kernel/` (source, Cargo files, or userspace pack). Doc,
face, and services merges do not trigger a wave. Each wave re-proves
the merged tree from a clean clone; waves are numbered in run order.
If fewer than five kernel waves land before closeout, the unused
slots record NO WAVE and the §1 baseline stands as the proof.

- **OC1B-176** Write the trigger rule into the status file and record the current main tip as wave 0's reference tree. Proof: the trigger block in os-build/OPENCODE1_500_STATUS.md.
- **OC1B-177** Wave 1: when the first kernel-touching merge wave lands, record its merge shas and the new main tip. Proof: os-build/logs/OC1B-reproof-w1-tree.txt.
- **OC1B-178** Wave 1: clean-clone the new tip and run gate.sh; save the full output. Proof: os-build/logs/OC1B-reproof-w1-gate.log.
- **OC1B-179** Wave 1: boot the wave tree and save the serial plus the shell/fetch screendump pair. Proof: os-build/logs/OC1B-reproof-w1-serial.txt, os-build/captures/oc1b-reproof-w1-shell.png, os-build/captures/oc1b-reproof-w1-fetch.png.
- **OC1B-180** Wave 1: diff the wave serial against the previous proven serial; every new or missing line class is named, and any lost claim line is a REGRESSION call in the write-up. Proof: os-build/logs/OC1B-reproof-w1.md with its verdict line.
- **OC1B-181** Wave 2: record the second kernel wave's merge shas and new tip. Proof: os-build/logs/OC1B-reproof-w2-tree.txt.
- **OC1B-182** Wave 2: clean-clone gate run on the wave-2 tip. Proof: os-build/logs/OC1B-reproof-w2-gate.log.
- **OC1B-183** Wave 2: boot serial plus screendump pair for the wave-2 tree. Proof: os-build/logs/OC1B-reproof-w2-serial.txt, os-build/captures/oc1b-reproof-w2-shell.png, os-build/captures/oc1b-reproof-w2-fetch.png.
- **OC1B-184** Wave 2: serial diff against the wave-1 serial with the regression call. Proof: os-build/logs/OC1B-reproof-w2.md.
- **OC1B-185** Wave 3: record the third kernel wave's merge shas and new tip. Proof: os-build/logs/OC1B-reproof-w3-tree.txt.
- **OC1B-186** Wave 3: clean-clone gate run on the wave-3 tip. Proof: os-build/logs/OC1B-reproof-w3-gate.log.
- **OC1B-187** Wave 3: boot serial plus screendump pair for the wave-3 tree. Proof: os-build/logs/OC1B-reproof-w3-serial.txt, os-build/captures/oc1b-reproof-w3-shell.png, os-build/captures/oc1b-reproof-w3-fetch.png.
- **OC1B-188** Wave 3: serial diff against the wave-2 serial with the regression call. Proof: os-build/logs/OC1B-reproof-w3.md.
- **OC1B-189** Wave 4: record the fourth kernel wave's merge shas and new tip. Proof: os-build/logs/OC1B-reproof-w4-tree.txt.
- **OC1B-190** Wave 4: clean-clone gate run on the wave-4 tip. Proof: os-build/logs/OC1B-reproof-w4-gate.log.
- **OC1B-191** Wave 4: boot serial plus screendump pair for the wave-4 tree. Proof: os-build/logs/OC1B-reproof-w4-serial.txt, os-build/captures/oc1b-reproof-w4-shell.png, os-build/captures/oc1b-reproof-w4-fetch.png.
- **OC1B-192** Wave 4: serial diff against the wave-3 serial with the regression call. Proof: os-build/logs/OC1B-reproof-w4.md.
- **OC1B-193** Wave 5: record the fifth kernel wave's merge shas and new tip. Proof: os-build/logs/OC1B-reproof-w5-tree.txt.
- **OC1B-194** Wave 5: clean-clone gate run on the wave-5 tip. Proof: os-build/logs/OC1B-reproof-w5-gate.log.
- **OC1B-195** Wave 5: boot serial plus screendump pair for the wave-5 tree. Proof: os-build/logs/OC1B-reproof-w5-serial.txt, os-build/captures/oc1b-reproof-w5-shell.png, os-build/captures/oc1b-reproof-w5-fetch.png.
- **OC1B-196** Wave 5: serial diff against the wave-4 serial with the regression call. Proof: os-build/logs/OC1B-reproof-w5.md.
- **OC1B-197** For any wave slot that never triggered, write its NO WAVE line (no kernel merge wave N landed before closeout; the prior proof stands). Proof: the NO WAVE lines in os-build/OPENCODE1_500_STATUS.md.
- **OC1B-198** If any wave's gate comes back RED, stop: commit the red log, name the lost assertion, and record that kernel work halts for Pax's call — do not attempt a kernel fix yourself. Proof: the RED block in os-build/OPENCODE1_500_STATUS.md with the gate log path.
- **OC1B-199** Build the re-proof index: wave, tip sha, gate result, serial path, verdict — one row per wave including wave 0 (the §1 baseline). Proof: os-build/logs/OC1B-reproof-index.md.
- **OC1B-200** Commit the §8 artifacts. Proof: the commit sha in os-build/OPENCODE1_500_STATUS.md.

## §9 Model pipeline live proofs on the Mac (OC1B-201..OC1B-225)

Grounded in `server/queue/models.py`, `server/queue/crew.py`, and
`os-build/MODEL_INTEGRATION.md`. Folds in wave-3 §3 (tasks 17–28) and
adds the two wirings that landed after it: SAM into the patrol step
(`TRIO_SAM_SEGMENT=1` in crew.py's `_run_segment`) and the Wonder
review reader (`TRIO_REVIEW_WONDER=1` in crew.py's `_run_review`).
Receipts land in `server/queue/model_receipts.jsonl`. Voice
transcription stays EndpointUnresolvedError — never touch that seam.

- **OC1B-201** Before any live call, run the queue suite on the Mac and record its actual count as the section baseline. Proof: os-build/logs/OC1B-model-queue-baseline.txt with the unittest summary line.
- **OC1B-202** Set SPARK_API_KEY from the Mac key file (line 1) and prove presence by length only — the value is never printed. Proof: the length-only line in os-build/logs/OC1B-model-key.txt.
- **OC1B-203** Make one `models.chat_text` call to muse-wonder-1.0 with a tiny prompt and save the returned text. Proof: os-build/logs/oc1b-model-proofs/wonder-chat.txt with the reply and the model-reported field.
- **OC1B-204** Save that call's receipt line from `server/queue/model_receipts.jsonl`. Proof: the receipt line quoted in os-build/logs/oc1b-model-proofs/wonder-chat.txt.
- **OC1B-205** Make one `models.segment` call on `test-footage/frames/ignis-fire-1.jpg` (wave-3 §3 task 20) and save the returned region. Proof: os-build/logs/oc1b-model-proofs/sam-direct.json with box_px, region, model, and latency.
- **OC1B-206** Compare SAM's region against the Spark reading's region for the same frame and write both number sets down as they fell — agreement or not (wave-3 §3 task 21). Proof: os-build/logs/oc1b-model-proofs/sam-vs-spark.md.
- **OC1B-207** Make one `models.generate_image` call with a simple prompt and save the image with its real format extension (wave-3 §3 task 22). Proof: the image file under os-build/logs/oc1b-model-proofs/ plus its receipt line recorded in os-build/logs/OC1B-model-proofs.md.
- **OC1B-208** SAM into patrol, live: run one crew check over a flagged frame with `TRIO_SAM_SEGMENT=1` and confirm the incident timeline carries a `segment` step with a region. Proof: the timeline excerpt in os-build/logs/oc1b-model-proofs/sam-patrol-timeline.json.
- **OC1B-209** In that same run, confirm the segment step's prompt is the first observation's description (or the category when no description exists), as `_run_segment` specifies. Proof: the prompt field quoted in os-build/logs/OC1B-model-proofs.md.
- **OC1B-210** SAM failure honesty: run the segment path with the key withheld and confirm the timeline records a segment step with an `error`, and NO region. Proof: the error-step excerpt in os-build/logs/oc1b-model-proofs/sam-failure-timeline.json.
- **OC1B-211** Confirm the flag pipeline completed normally in the OC1B-210 failure run (the incident stands on its assessments; the SAM failure broke nothing). Proof: the incident's final outcome line quoted in os-build/logs/OC1B-model-proofs.md.
- **OC1B-212** Wonder review, live: run one flagged incident end to end with `TRIO_REVIEW_WONDER=1` and confirm the review timeline step carries `reader: "wonder"`. Proof: the review-step excerpt in os-build/logs/oc1b-model-proofs/wonder-review-timeline.json.
- **OC1B-213** In that run, confirm the review's verdict was produced from Wonder's own reading (its category and latency on the step are Wonder's, not the patrol job's). Proof: the step fields quoted in os-build/logs/OC1B-model-proofs.md.
- **OC1B-214** Wonder fallback: run the same shape with `TRIO_REVIEW_WONDER=1` and the key withheld for the review call; the step must carry `reader: "spark"` with `reader_fallback` naming the failure. Proof: the review-step excerpt in os-build/logs/oc1b-model-proofs/wonder-fallback-timeline.json.
- **OC1B-215** Judge model run on current main: one Ignis incident with `TRIO_JUDGE_MODEL=1`, timeline review step carrying `judge_mode: "model"` (wave-3 §3 task 23, re-proven on this tree). Proof: the timeline excerpt in os-build/logs/oc1b-model-proofs/judge-model-timeline.json.
- **OC1B-216** The same incident shape with the judge flag OFF: `judge_mode: "deterministic"` on the step — both modes side by side (wave-3 §3 task 25). Proof: the timeline excerpt in os-build/logs/oc1b-model-proofs/judge-deterministic-timeline.json.
- **OC1B-217** Force one judge fallback (flag on, judge call made to fail without breaking the run) and confirm the recorded reasons name the fallback (wave-3 §3 task 26); if it cannot be forced cleanly, mark UNPROVEN with the reason. Proof: the reasons excerpt in os-build/logs/oc1b-model-proofs/judge-fallback-timeline.json or the UNPROVEN line in os-build/logs/OC1B-model-proofs.md.
- **OC1B-218** Run one full incident with ALL THREE flags on together (SAM segment + Wonder review + model judge) and save the whole timeline. Proof: os-build/logs/oc1b-model-proofs/all-flags-timeline.json.
- **OC1B-219** Verify the all-flags timeline's dispatch (if the incident confirms) went to the simulated loopback endpoint only — receipt `simulated=true`. Proof: the receipt line quoted in os-build/logs/OC1B-model-proofs.md.
- **OC1B-220** Confirm `models.transcribe` still raises EndpointUnresolvedError and nothing in this section touched that seam. Proof: the raised-error output in os-build/logs/oc1b-model-proofs/transcribe-unresolved.txt.
- **OC1B-221** Total this section's live spend from the receipts file (Spark-priced estimates say so; other models' estimates are labelled as estimates). Proof: the total line in os-build/logs/OC1B-model-proofs.md.
- **OC1B-222** Re-run the queue suite after all live runs and record the count against OC1B-201's baseline. Proof: os-build/logs/OC1B-model-queue-after.txt.
- **OC1B-223** Write the section proof file in wave-3 §3 task 27's shape: every call, its model, its receipt, its artifact path. Proof: os-build/logs/OC1B-model-proofs.md completed.
- **OC1B-224** For every live call that failed in this section, record the failure with its error text — a failed call is a result, never a deleted line. Proof: the failures block in os-build/logs/OC1B-model-proofs.md.
- **OC1B-225** Commit the §9 artifacts. Proof: the commit sha in os-build/OPENCODE1_500_STATUS.md.

## §10 Live cameras on the Mac (OC1B-226..OC1B-250)

Grounded in `server/queue/livecams.py` (CLI: `--list`, `--area`,
`--name`, `--count`, `--out`, `--assess-one`, `--division`) and
`os-build/LIVE_CAMS.md`. The module's own fetcher works where egress
is normal — the Mac. Pax proved one live reading from the sandbox's
browser route (Bay Pkwy @ 78 St, Brooklyn, committed under
`server/queue/livecam_records/`); this section proves the module's
OWN fetcher end to end and widens the record set.

- **OC1B-226** Run `python3 server/queue/livecams.py --list` on the Mac and record how many online cameras the DOT list returns. Proof: os-build/logs/OC1B-livecams-list.txt with the count and the first 10 entries.
- **OC1B-227** Confirm every listed entry carries id, name, area, and an imageUrl on `webcams.nyctmc.org` — the published API shape, nothing scraped. Proof: the field check note in os-build/logs/OC1B-livecams-list.txt.
- **OC1B-228** Run `--assess-one --area Brooklyn --division vigiles` and save the frame the module's own fetcher pulled. Proof: the dated frame under server/queue/livecam_records/ named in os-build/logs/OC1B-livecams-runs.md.
- **OC1B-229** Save that run's reading JSON beside the frame and quote its category and summary. Proof: the reading file under server/queue/livecam_records/ plus the quoted lines in os-build/logs/OC1B-livecams-runs.md.
- **OC1B-230** Verify the Brooklyn frame's bytes are a real image (JPEG magic + nonzero size) and that its on-image timestamp is current, not a stale cached still. Proof: the byte/timestamp check in os-build/logs/OC1B-livecams-runs.md.
- **OC1B-231** Run `--assess-one --area Manhattan --division vigiles`. Proof: the dated frame + reading under server/queue/livecam_records/, logged in os-build/logs/OC1B-livecams-runs.md.
- **OC1B-232** Run `--assess-one --area Manhattan --division ignis`. Proof: the dated frame + reading under server/queue/livecam_records/, logged in os-build/logs/OC1B-livecams-runs.md.
- **OC1B-233** Run `--assess-one --area Queens --division medicus` (scene-awareness categories only — the reading must carry no diagnosis, cause, severity, or treatment language). Proof: the dated frame + reading under server/queue/livecam_records/, with the wording check noted in os-build/logs/OC1B-livecams-runs.md.
- **OC1B-234** Run `--assess-one --area Bronx --division vigiles`. Proof: the dated frame + reading under server/queue/livecam_records/, logged in os-build/logs/OC1B-livecams-runs.md.
- **OC1B-235** Run `--assess-one --area "Staten Island" --division ignis`; if the area has no online camera, record that as the result instead of substituting another area. Proof: the frame + reading, or the no-camera line, in os-build/logs/OC1B-livecams-runs.md.
- **OC1B-236** Run one `--name` filter run (a named corridor, e.g. `--name "Belt Pkwy"`) and confirm the picked camera matches the filter deterministically. Proof: the picked camera's name/id quoted in os-build/logs/OC1B-livecams-runs.md.
- **OC1B-237** Run one `--count 3` snapshot set for one area and save all three frames. Proof: the three dated frames under server/queue/livecam_records/, listed in os-build/logs/OC1B-livecams-runs.md.
- **OC1B-238** For every reading in this section, verify the v2 contract fields are present (product, timestamp, observations, assessment, processing) and `requires_human_review` is carried honestly. Proof: the per-reading field check in os-build/logs/OC1B-livecams-runs.md.
- **OC1B-239** Compare each reading's description against its frame yourself and flag any reading that describes something the frame does not show — flagged, quoted, never edited. Proof: the comparison notes in os-build/logs/OC1B-livecams-runs.md.
- **OC1B-240** Refusal check: run the module with an unreachable `--api-url` and confirm it raises LiveCamError and produces NO frame file. Proof: the error output and the absent-file note in os-build/logs/OC1B-livecams-runs.md.
- **OC1B-241** Refusal check 2: point the fetcher at a non-image response and confirm `is_image_bytes` rejects it downstream (no error page is ever assessed as a frame). Proof: the rejection output in os-build/logs/OC1B-livecams-runs.md.
- **OC1B-242** Re-run the module's offline tests (`tests/queue-python/test_livecams.py`) on the Mac and record the count. Proof: os-build/logs/OC1B-livecams-tests.txt.
- **OC1B-243** Total the model spend for this section's readings from the receipts/helper record and state it as an estimate at Spark rates. Proof: the spend line in os-build/logs/OC1B-livecams-runs.md.
- **OC1B-244** Build the livecam records index: every frame in `server/queue/livecam_records/` with camera, area, division, timestamp, category — including Pax's sandbox-proven Bay Pkwy reading as the first row. Proof: os-build/logs/OC1B-livecams-index.md.
- **OC1B-245** Record which areas/divisions produced NO flag across the whole section — an all-baseline section is a valid result and is stated as one. Proof: the flag summary in os-build/logs/OC1B-livecams-runs.md.
- **OC1B-246** If any run flagged, hand the incident to §13's flow (do not dispatch from this section) and record the handoff. Proof: the handoff line in os-build/logs/OC1B-livecams-runs.md, or the no-flags line.
- **OC1B-247** Confirm no EarthCam/Skyline/Windy source was pulled anywhere in this section (embed-only sources are never fetched — LIVE_CAMS.md ruling). Proof: the source attestation line in os-build/logs/OC1B-livecams-runs.md.
- **OC1B-248** Record the section's failures (fetch errors, offline areas, refused frames) as a named list. Proof: the failures block in os-build/logs/OC1B-livecams-runs.md.
- **OC1B-249** Write the section verdict: the module's own fetcher is PROVEN end to end on the Mac, or the exact step where it is not. Proof: the verdict block in os-build/logs/OC1B-livecams-runs.md.
- **OC1B-250** Commit the §10 artifacts (frames + readings + logs). Proof: the commit sha in os-build/OPENCODE1_500_STATUS.md.

## §11 Demo capture — kernel only (OC1B-251..OC1B-275)

Del's ruling 2026-11-02: the demo shows the real operating system.
NO face, NO web page, NO browser shots anywhere in this section.
Sources: `os-build/DEMO_SCRIPT.md` (six beats, every beat sourced to
a named committed log; fallback = cut to the committed log line) and
the kernel-only demo plan. Folds in wave-3 §4 (tasks 29–38). The
Imperium beat uses a REAL live-camera reading (§10's records) — the
staged R5-4 reading is never presented as real; the dispatch receipt
is real and the endpoint is labelled SIMULATED on screen.

- **OC1B-251** Read `os-build/DEMO_SCRIPT.md` and the kernel-only demo plan end to end and list every shot the film needs, beat by beat. Proof: os-build/logs/OC1B-demo-shotlist.md.
- **OC1B-252** For every shot on that list, name the committed log or live run that backs it; any shot with no backing is cut from the list here, not at edit time. Proof: the backing column completed in os-build/logs/OC1B-demo-shotlist.md.
- **OC1B-253** Capture beat 1 (boot) fresh from the current main image: serial + screendump of the banner, alive line, and memory lines. Proof: os-build/demo/oc1b-beat1-serial.txt and os-build/captures/oc1b-beat1.png.
- **OC1B-254** Capture beat 2 (ring 3): the loader lines with the three user addresses and `HELLO FROM USERSPACE`. Proof: the quoted serial lines in os-build/logs/OC1B-demo-capture.md with the screendump os-build/captures/oc1b-beat2.png.
- **OC1B-255** Capture beat 3 (three programs): hello exit 0, sleeper cycle, crasher's about-to-read-zero line, in order. Proof: the quoted lines in os-build/logs/OC1B-demo-capture.md with os-build/captures/oc1b-beat3.png.
- **OC1B-256** Capture beat 4 (fault isolation): the task-killed fault line followed by the sleeper continuing. Proof: the quoted lines in os-build/logs/OC1B-demo-capture.md with os-build/captures/oc1b-beat4.png.
- **OC1B-257** Capture beat 5 (shell): typed status twice with moving ticks, then mem, then ps — live in one session. Proof: os-build/logs/OC1B-demo-beat5-serial.txt and os-build/captures/oc1b-beat5.png.
- **OC1B-258** Capture the bad-syscall refusal for beat 5's close. Proof: the refusal line quoted in os-build/logs/OC1B-demo-capture.md.
- **OC1B-259** Capture beat 6's reading LIVE: run one §10 livecam assessment during the capture session and record the terminal output as it happens. Proof: os-build/logs/OC1B-demo-beat6-live.txt with the camera name, timestamp, and reading.
- **OC1B-260** Capture beat 6's chain: the patrol → review → judge → response timeline of a real incident run (the §9 all-flags run may serve if its timeline is committed). Proof: the timeline file path recorded in os-build/logs/OC1B-demo-capture.md.
- **OC1B-261** Capture the dispatch receipt close-up for beat 6, with `simulated=true` legible on screen. Proof: os-build/captures/oc1b-beat6-receipt.png.
- **OC1B-262** Verify the on-screen SIMULATED label is present for the whole of beat 6 in the cut. Proof: the label check note in os-build/logs/OC1B-demo-capture.md.
- **OC1B-263** Assemble the cut list for the rebuild: every segment, its source file, its in/out times summing to the script's beat timings. Proof: os-build/demo/oc1b-cut.txt.
- **OC1B-264** Rebuild the film from the captured material only. Proof: os-build/demo/demo-3min.mp4 replaced on the branch, with the build command recorded in os-build/logs/OC1B-demo-capture.md.
- **OC1B-265** ffprobe the final film: duration must be exactly 180.000s (wave-3 §4 task 35). Proof: the ffprobe output in os-build/logs/OC1B-demo-capture.md.
- **OC1B-266** Extract frames at t=10, t=90, and t=160 and check each against the log it claims to show. Proof: the three frames under os-build/demo/oc1b-check/ with the check notes in os-build/logs/OC1B-demo-capture.md.
- **OC1B-267** Watch the full film once and log every frame that shows a face, a web page, or a browser — the count must be 0. Proof: the watch-through log in os-build/logs/OC1B-demo-capture.md.
- **OC1B-268** Watch for the second failure class: any frame that presents a staged or simulated element as real. Proof: the honesty pass note in os-build/logs/OC1B-demo-capture.md.
- **OC1B-269** Rewrite `os-build/demo/CAPTURE_NOTES.md` for the new film: what is real, what is scripted, what is simulated — in those words (wave-3 §4 task 32). Proof: the updated os-build/demo/CAPTURE_NOTES.md committed on the branch.
- **OC1B-270** Verify every fallback the script names still exists: for each beat, the committed log line the film cuts to on a live failure is present in the repo. Proof: the fallback table in os-build/logs/OC1B-demo-capture.md.
- **OC1B-271** Write the DEMO RUNBOOK: exact commands to replay the film and every live proof behind it, in order, for Nov 4 (wave-3 §4 task 36). Proof: os-build/demo/OC1B_RUNBOOK.md.
- **OC1B-272** Rehearse the runbook once, top to bottom, timed (wave-3 §4 task 37). Proof: os-build/logs/OC1B-demo-rehearsal.md with the total time.
- **OC1B-273** Log every rehearsal gap — anything slow, missing, or manual — with the fix or the named owner (wave-3 §4 task 38). Proof: the gaps block in os-build/logs/OC1B-demo-rehearsal.md.
- **OC1B-274** Record the final film's sha256 and byte size, and confirm the closing line of the script ("That is what runs today") is the film's closing line. Proof: the film record in os-build/logs/OC1B-demo-capture.md.
- **OC1B-275** Commit the §11 artifacts; the film itself is committed only if under the repo's size discipline, else its sha256 + path record stands as the artifact (Pax's call at merge). Proof: the commit sha in os-build/OPENCODE1_500_STATUS.md.

## §12 Carrier image — bake the toolchain in (OC1B-276..OC1B-300)

Folds in wave-3 §5 (tasks 39–48). Grounded in
`os-build/face/build-image.sh` and `os-build/logs/wave2-sec4.md`
(wave-2 finding: the image has node + git + chromium; OpenCode is
ABSENT). Del's doctrine: the image ships the crew toolchain. Image
parts NEVER enter git — recipe, sha256 manifest, and JOIN note only.

- **OC1B-276** Read `os-build/face/build-image.sh` and `os-build/logs/wave2-sec4.md` and list the recipe's current package set. Proof: os-build/logs/OC1B-carrier-recipe.md with the package list.
- **OC1B-277** Record the wave-2 image's facts as the before-state: size, sha256, and the four standing checks' last results from `os-build/face/STATUS.md`. Proof: the before block in os-build/logs/OC1B-carrier-recipe.md.
- **OC1B-278** Add the OpenCode binary to the image recipe at a pinned version, recorded in the recipe header (wave-3 §5 task 40). Proof: the recipe diff committed on the branch plus the version line quoted in os-build/logs/OC1B-carrier-recipe.md.
- **OC1B-279** Attempt Freebuff in the recipe the same way; if it does not install cleanly in the recipe environment, record why and do not force it (wave-3 §5 task 41). Proof: the install output or the failure note in os-build/logs/OC1B-carrier-recipe.md.
- **OC1B-280** Add Node, OpenCode, and Freebuff versions to the recipe's toolchain inventory block (git and chromium already ride). Proof: the inventory block in os-build/logs/OC1B-carrier-recipe.md.
- **OC1B-281** Rebuild the image from the updated recipe (wave-3 §5 task 42). Proof: the build log tail in os-build/logs/OC1B-carrier-build.txt.
- **OC1B-282** Record the rebuilt image's size and sha256. Proof: os-build/logs/OC1B-carrier-image.txt.
- **OC1B-283** Boot the rebuilt image headless and save the boot log (wave-3 §5 task 43). Proof: os-build/logs/OC1B-carrier-boot.txt.
- **OC1B-284** Standing check 1: autologin on tty1 in the rebuilt image. Proof: the tty1 prompt line quoted in os-build/logs/OC1B-carrier-checks.md.
- **OC1B-285** Standing check 2: DHCP address acquired in the guest. Proof: the address line quoted in os-build/logs/OC1B-carrier-checks.md.
- **OC1B-286** Standing check 3: dashboard HTTP 200 with live facts (not a static page). Proof: the curl output with the facts quoted in os-build/logs/OC1B-carrier-checks.md.
- **OC1B-287** Standing check 4: the passive updater completes one pull cycle in the guest. Proof: the updater log lines quoted in os-build/logs/OC1B-carrier-checks.md.
- **OC1B-288** In the guest, run `opencode --version` and save the output (wave-3 §5 task 45). Proof: the version line quoted in os-build/logs/OC1B-carrier-checks.md.
- **OC1B-289** In the guest, run `node --version`, `git --version`, and the chromium version; save all three. Proof: the three lines in os-build/logs/OC1B-carrier-checks.md.
- **OC1B-290** Confirm the kiosk/face still starts in the rebuilt image (wave-3 §5 task 46) — it rides the carrier as an app; this checks it starts, and builds nothing on it. Proof: the start log lines quoted in os-build/logs/OC1B-carrier-checks.md.
- **OC1B-291** Write the image's sha256 manifest (every part, if split for transport) in the repo's manifest shape. Proof: the manifest file under os-build/face/ committed on the branch, named in os-build/logs/OC1B-carrier-image.txt.
- **OC1B-292** Write or refresh the JOIN note (how the parts rejoin, the sha256 to verify against). Proof: the JOIN note file under os-build/face/ committed on the branch.
- **OC1B-293** Attest the parts stayed out of git: `git status` on the branch shows no image part staged or committed. Proof: the status output quoted in os-build/logs/OC1B-carrier-image.txt.
- **OC1B-294** Record the image's delta vs the wave-2 image: size change and the toolchain additions. Proof: the delta block in os-build/logs/OC1B-carrier-image.txt.
- **OC1B-295** Update the `os-build/face/STATUS.md` rows for this section's work (wave-3 §5 task 48). Proof: the updated os-build/face/STATUS.md committed on the branch.
- **OC1B-296** If a hardware/UTM boot of this image is attempted, record it separately from the QEMU boot; if not attempted, record it UNPROVEN — QEMU proof never stands in for hardware. Proof: the hardware line in os-build/logs/OC1B-carrier-checks.md.
- **OC1B-297** Record any standing check that failed with its log excerpt — a failed check is a named result, not a skipped row. Proof: the failures block in os-build/logs/OC1B-carrier-checks.md, or the all-pass line.
- **OC1B-298** Verify the recipe builds from a clean checkout of the branch (no local state the recipe secretly needs). Proof: the clean-build log tail in os-build/logs/OC1B-carrier-build.txt.
- **OC1B-299** Write the carrier verdict: the toolchain is IN the image and proven in the guest, or the exact step where that stops being true. Proof: the verdict block in os-build/logs/OC1B-carrier-image.txt.
- **OC1B-300** Commit the §12 artifacts (recipe, manifest, JOIN note, logs — never image parts). Proof: the commit sha in os-build/OPENCODE1_500_STATUS.md.

## §13 Imperium full live runs on the Mac (OC1B-301..OC1B-325)

Grounded in `server/queue/patrol.py`, `server/queue/crew.py`,
`server/queue/crew_records.py`, and `os-build/AGENTIC_PROOF.md`.
Folds in wave-3 §6 (tasks 49–58: close the wave-2 gaps from
`os-build/logs/wave2-sec5.md`). Patrol runs over the REAL DOT camera
list through the production crew; dispatch goes to the simulated
loopback endpoint only, receipts `sim-…`, `simulated=true`.

- **OC1B-301** Read `os-build/logs/wave2-sec5.md` and list every item it marks unproven, partial, or scripted-only (wave-3 §6 task 49). Proof: os-build/logs/OC1B-imperium-gaps.md with the gap list in its order.
- **OC1B-302** Start the production crew stack on the Mac and record the crew-status heartbeat coming up. Proof: the crew-status snapshot in os-build/logs/OC1B-imperium-live.md.
- **OC1B-303** Run `python3 server/queue/patrol.py --once` and confirm the status names the camera source as the live NYCTMC list, not the fallback subset. Proof: the camera_source line quoted in os-build/logs/OC1B-imperium-live.md.
- **OC1B-304** Run a patrol batch (`patrol.py --max-checks 10`) and record the counts block (checks, baseline, flagged, reported, feed_errors, job_errors). Proof: the counts quoted in os-build/logs/OC1B-imperium-live.md.
- **OC1B-305** For every check in that batch, record camera, division lens, and outcome — the lens rotation (vigiles → ignis → medicus) must be visible in the record. Proof: the per-check table in os-build/logs/OC1B-imperium-live.md.
- **OC1B-306** If a natural flag occurs, follow its incident end to end and save the full timeline. Proof: the timeline file path in os-build/logs/OC1B-imperium-live.md (or the no-natural-flag line — an honest zero).
- **OC1B-307** For the dispatch leg, run one incident on a staged frame, labelled STAGED in every artifact, through to the simulated dispatch. Proof: the incident timeline + the `sim-` receipt in os-build/logs/oc1b-imperium/staged-dispatch.json.
- **OC1B-308** Verify that receipt: receipt_id present, `simulated=true`, destination the loopback simulated endpoint for the routed service (vigiles→police / ignis→fire / medicus→hospital path). Proof: the receipt fields quoted in os-build/logs/OC1B-imperium-live.md.
- **OC1B-309** Attempt the fence: confirm `crew.check_dispatch_url` refuses a non-loopback URL by calling it with an external host in a test snippet — refusal is the expected output. Proof: the DispatchBoundaryError output in os-build/logs/oc1b-imperium/fence-check.txt.
- **OC1B-310** BOLO + purge proof (wave-3 §6 task 51): flag an incident with visible marks, build the BOLO, close it as a false positive, and confirm the evidence purge receipt exists. Proof: the BOLO excerpt + purge receipt in os-build/logs/oc1b-imperium/bolo-purge.json.
- **OC1B-311** Confirm the purged incident's BOLO card reads ID: UNIDENTIFIED and carries descriptions only — no identity was ever attached. Proof: the card fields quoted in os-build/logs/OC1B-imperium-live.md.
- **OC1B-312** Cleared path (wave-3 §6 task 52): one incident the review clears; save its timeline and close state. Proof: the timeline path + close state in os-build/logs/OC1B-imperium-live.md.
- **OC1B-313** Inconclusive path (wave-3 §6 task 53): one incident the judge holds inconclusive; confirm NO dispatch was spent on it. Proof: the timeline excerpt showing the hold and the absent dispatch step, in os-build/logs/OC1B-imperium-live.md.
- **OC1B-314** Yellow path: one incident that lands record_for_review (yellow tier) and confirm the chain ends there — no investigation, no dispatch. Proof: the outcome line `flagged-yellow-review` quoted in os-build/logs/OC1B-imperium-live.md.
- **OC1B-315** Budget governor (wave-3 §6 task 54): drive an incident against a per-incident cap (8 actions / 12 calls / $0.50) and save the stop lines. Proof: the stop/receipt lines in os-build/logs/oc1b-imperium/budget-stop.json.
- **OC1B-316** Patrol budget pause: with the reserve state forced, confirm patrol writes `paused-budget` and files NOTHING. Proof: the status + event excerpt in os-build/logs/OC1B-imperium-live.md.
- **OC1B-317** Supervisor pause: place a camera id in `paused-feeds.json` and confirm patrol skips it and names it in the heartbeat. Proof: the heartbeat excerpt in os-build/logs/OC1B-imperium-live.md.
- **OC1B-318** Run one patrol batch with `TRIO_SAM_SEGMENT=1` over live cameras and record whether any segment step landed (only flags segment; an all-baseline batch records exactly that). Proof: the batch outcome in os-build/logs/OC1B-imperium-live.md.
- **OC1B-319** Sample five incident/event records the runs wrote and verify the append-only records are complete JSON with timestamps (no torn writes). Proof: the sample check in os-build/logs/OC1B-imperium-live.md.
- **OC1B-320** Re-run the queue suite after all live runs wrote records (wave-3 §6 task 57). Proof: os-build/logs/OC1B-imperium-queue-after.txt with the count against §9's baseline.
- **OC1B-321** Total the section's live spend from the guardrail state + receipts and state it as a Spark-rate estimate. Proof: the spend line in os-build/logs/OC1B-imperium-live.md.
- **OC1B-322** For every wave-2 gap from OC1B-301 that this section closed, write the closing artifact path (wave-3 §6 task 55). Proof: the per-gap rows completed in os-build/logs/OC1B-imperium-gaps.md.
- **OC1B-323** For every gap still open, write the blocker in one line (wave-3 §6 task 56). Proof: the blocker lines in os-build/logs/OC1B-imperium-gaps.md.
- **OC1B-324** Write the section record in wave-3 §6 task 58's shape (gap list, verdict per gap). Proof: os-build/logs/OC1B-imperium-gaps.md completed with verdicts.
- **OC1B-325** Commit the §13 artifacts. Proof: the commit sha in os-build/OPENCODE1_500_STATUS.md.

## §14 Science Lab + Hortus Mac verification runs (OC1B-326..OC1B-350)

Grounded in `os/worlds/science-lab/` (status:
`os/worlds/science-lab/SCIENCE_LAB_STATUS.md`), `tests/science-lab/`
(test_section1..10 + test_ladder.py), and the Hortus suite
(`os/tests`, pattern `test_hortus*.py`). OpenCode 2 built wave-1;
this lane VERIFIES it on the Mac — runs only, no science-lab code
edits (defects are reported, not fixed, here).

- **OC1B-326** Run the Science Lab suite on the Mac: `python3 -m unittest discover -s tests/science-lab`. Proof: os-build/logs/OC1B-science-suite.txt with the full count (163 baseline — record the actual).
- **OC1B-327** Record the per-file counts for test_section1..test_section10 and test_ladder.py individually. Proof: the per-file table in os-build/logs/OC1B-science-suite.txt.
- **OC1B-328** Run the Hortus suite: `python3 -m unittest discover -s os/tests -p "test_hortus*.py"`. Proof: os-build/logs/OC1B-hortus-suite.txt with the count (14 baseline — record the actual).
- **OC1B-329** Re-run the dress rehearsal end to end on the Mac: fresh chem question over the 20 held-out Delaney rows (11–30). Proof: the run record under os/worlds/science-lab/ named in os-build/logs/OC1B-science-rehearsal.md.
- **OC1B-330** From that rehearsal, record the run_chem RMSE and check it against the ≤ 1.5 match bar. Proof: the RMSE line in os-build/logs/OC1B-science-rehearsal.md.
- **OC1B-331** Record the blind-reproduce verdict from the rehearsal (agree / disagree, as it fell). Proof: the verdict line in os-build/logs/OC1B-science-rehearsal.md.
- **OC1B-332** Record the evidence-ladder level the rehearsal's gate confirmed (L2 in wave-1) and confirm automated promotion went no higher than the L3 cap. Proof: the ladder lines in os-build/logs/OC1B-science-rehearsal.md.
- **OC1B-333** Confirm the rehearsal's model spend is 0 (the wave-1 discipline: no live model judgement calls). Proof: the spend line in os-build/logs/OC1B-science-rehearsal.md.
- **OC1B-334** Run one full discovery cycle (literature → reasoning → compute → verify → repository) on a fresh question and save the cycle record. Proof: the cycle record path in os-build/logs/OC1B-science-rehearsal.md.
- **OC1B-335** Run the failure drill: the rehearsal's failure case must record fake_success false. Proof: the drill output quoted in os-build/logs/OC1B-science-rehearsal.md.
- **OC1B-336** Verify the gateway stayed LOCAL-SHELF for every run in this section: no remote MCP adapter was invoked (they are UNIMPLEMENTED and must stay that way here). Proof: the gateway log check in os-build/logs/OC1B-science-rehearsal.md.
- **OC1B-337** Verify the STEP_8 marker behaviour: the ladder code's always-blocking UNIMPLEMENTED step 8 still blocks. Proof: the probe output in os-build/logs/OC1B-science-rehearsal.md.
- **OC1B-338** Re-check a sample of the wave-1 claim audit (19 checked / 19 backed): pick 5 claims and trace each to its artifact. Proof: the 5 trace rows in os-build/logs/OC1B-science-rehearsal.md.
- **OC1B-339** Run one Hortus breeding run through the Science Lab integration path and save its record. Proof: the run record path in os-build/logs/OC1B-hortus-runs.md.
- **OC1B-340** Record the Hortus run's inputs and outputs as counts (generations, candidates, survivors — as the engine reports them, never rounded). Proof: the counts in os-build/logs/OC1B-hortus-runs.md.
- **OC1B-341** Generate the exports/review page from the rehearsal data and confirm it renders the cycle it came from. Proof: the export path + render check in os-build/logs/OC1B-science-rehearsal.md.
- **OC1B-342** Compare every Mac count in this section against OpenCode 2's wave-1 status numbers; every difference is named with its likely cause or marked UNKNOWN. Proof: the comparison table in os-build/logs/OC1B-science-rehearsal.md.
- **OC1B-343** Record per-suite wall-clock times on this Mac. Proof: the timing lines in os-build/logs/OC1B-science-suite.txt and os-build/logs/OC1B-hortus-suite.txt.
- **OC1B-344** If any science or Hortus test fails on the Mac that passed in wave-1, record it as a DEFECT REPORT for Pax/OpenCode 2 — file, test name, error — and do not edit the code. Proof: the defect block in os-build/logs/OC1B-science-rehearsal.md, or the no-defects line.
- **OC1B-345** Verify the five science schemas (cycle, experiment, hypothesis, repository, source) validate a real rehearsal record each. Proof: the validation output in os-build/logs/OC1B-science-rehearsal.md.
- **OC1B-346** Confirm the repository/ledger the rehearsal wrote is append-only and parses clean after the runs. Proof: the parse check in os-build/logs/OC1B-science-rehearsal.md.
- **OC1B-347** Write the Mac-verification addendum for `os/worlds/science-lab/SCIENCE_LAB_STATUS.md` (branch commit; Pax merges). Proof: the addendum diff committed on the branch.
- **OC1B-348** List what remains UNIMPLEMENTED after the Mac runs (remote MCP adapters, model judgement calls, spend metering, ladder levels 4–6 automation) — confirmed by the runs, not copied from the status file. Proof: the unimplemented block in os-build/logs/OC1B-science-rehearsal.md.
- **OC1B-349** Write the section verdict: Science Lab + Hortus VERIFIED ON MAC, or the defect list that prevents the words. Proof: the verdict block in os-build/logs/OC1B-science-rehearsal.md.
- **OC1B-350** Commit the §14 artifacts. Proof: the commit sha in os-build/OPENCODE1_500_STATUS.md.

## §15 Musica real run on the Mac (OC1B-351..OC1B-375)

Grounded in `os/worlds/musica/` (PACK.md, gate-packet, board,
briefs), `tests/musica-*.test.mjs`, and `agents/registry.json`.
Bond's wave-2 run: 37 pass / 2 fail, both failures the missing
`pretty_midi` Python package on his 8GB Mac. This Mac installs it
and runs Musica for real. The registry rule: a command that does
not verify stays DRAFT — never upgrade a placeholder by assertion.

- **OC1B-351** Find how Bond ran the Musica suite (his command, from `os-build/BOND_WAVE2_STATUS.md` / his wave-2 report) and reproduce that exact command line here before changing anything. Proof: os-build/logs/OC1B-musica-basal.txt with the command and its result (37/2 expected — record the actual).
- **OC1B-352** Confirm both basal failures are the `pretty_midi` import and nothing else. Proof: the two failure excerpts quoted in os-build/logs/OC1B-musica-basal.txt.
- **OC1B-353** Install pretty_midi on this Mac and record the version installed. Proof: the pip output line in os-build/logs/OC1B-musica-install.txt.
- **OC1B-354** Re-run the Musica suite after the install. Proof: os-build/logs/OC1B-musica-after.txt with the full count.
- **OC1B-355** If the count is not all-pass, list the remaining failures individually with their errors — the install fixed only what it fixed. Proof: the failure list in os-build/logs/OC1B-musica-after.txt, or the all-pass line.
- **OC1B-356** Run the Node Musica tests (`tests/musica-*.test.mjs`) on the Mac and record the count separately from the Python suite. Proof: os-build/logs/OC1B-musica-node.txt.
- **OC1B-357** Read the Musica entry in `agents/registry.json` and quote its command exactly as registered. Proof: the quoted entry in os-build/logs/OC1B-musica-registry.md.
- **OC1B-358** Judge the entry: is the command a real verified entry point (a file that exists and runs) or a placeholder (`["true"]`-style)? Proof: the existence check output in os-build/logs/OC1B-musica-registry.md.
- **OC1B-359** If the command verifies, run it once for real and save its full output. Proof: os-build/logs/oc1b-musica/first-run.txt.
- **OC1B-360** From the first run, save one real Musica artifact it produced (the run's own output file — MIDI, report, or pack member) under os-build/logs/oc1b-musica/. Proof: the artifact file plus its path recorded in os-build/logs/OC1B-musica-registry.md.
- **OC1B-361** If the command does NOT verify, record DRAFT STAYS DRAFT with the exact reason (missing file, placeholder command, failing entry) — that is the section's registry result. Proof: the DRAFT line in os-build/logs/OC1B-musica-registry.md.
- **OC1B-362** Run the Musica gate-packet in `os/worlds/musica/gate-packet` if it carries a runnable check; record its verdict. Proof: the gate output in os-build/logs/OC1B-musica-gate.txt, or the not-runnable note.
- **OC1B-363** Run one Musica keeper cycle (the overnight keeper from `os-build/AGENTIC_PROOF.md`) in short form and save its log. Proof: os-build/logs/oc1b-musica/keeper.txt, or the named blocker if the keeper's entry cannot be found in the tree.
- **OC1B-364** Verify Musica's distinct face data is intact in the tree (dark studio + 3D notes are Hana's data lane — verify presence, build nothing). Proof: the presence check in os-build/logs/OC1B-musica-registry.md.
- **OC1B-365** Re-run the full Musica Python suite a second time to confirm the install result is stable, not a one-off. Proof: os-build/logs/OC1B-musica-after2.txt.
- **OC1B-366** Record the exact pip line a future Mac needs (package + version) so the pretty_midi fix survives this machine. Proof: the line in os-build/logs/OC1B-musica-install.txt.
- **OC1B-367** Compare the Mac counts against Bond's 37/2 and state the delta plainly. Proof: the delta block in os-build/logs/OC1B-musica-after.txt.
- **OC1B-368** If any Musica test needs another missing dependency, name it and stop there — one dependency fix per section is the scope; the rest are defect reports. Proof: the dependency note in os-build/logs/OC1B-musica-after.txt.
- **OC1B-369** Write the Musica section verdict: suite state, registry state (REAL RUN DONE or DRAFT STAYS DRAFT), keeper state. Proof: the verdict block in os-build/logs/OC1B-musica-registry.md.
- **OC1B-370** Save the Musica run's spend record if any model call occurred (expected: none — any call is named). Proof: the spend line in os-build/logs/OC1B-musica-registry.md.
- **OC1B-371** Confirm no Musica source file was edited in this section (runs and installs only). Proof: the clean `git status` for os/worlds/musica/ quoted in os-build/logs/OC1B-musica-registry.md.
- **OC1B-372** Record the Musica suite's wall-clock time on this Mac. Proof: the timing line in os-build/logs/OC1B-musica-after.txt.
- **OC1B-373** File any Musica failure that is a real code defect (not a dependency) as a defect report for Pax/Hana. Proof: the defect block in os-build/logs/OC1B-musica-registry.md, or the no-defects line.
- **OC1B-374** Update the status file's Musica rows with the Mac results. Proof: the Musica block in os-build/OPENCODE1_500_STATUS.md.
- **OC1B-375** Commit the §15 artifacts. Proof: the commit sha in os-build/OPENCODE1_500_STATUS.md.

## §16 Goose services gate-2 on the Mac (OC1B-376..OC1B-400)

Grounded in `services/` (agenthost, audit, board, bootlog, build,
callmatrix, common, console, dashboard, devices, devmgr, dhcp,
display, dns, dock, echo, example, and the rest) and
`services/run-goose-tests.sh`. The runner's hardcoded build path is
Buffy's fix (Round 12 addendum); this lane runs the Mac-side
verification and records results AS THEY FALL — before her fix it
records the path failure honestly; after her fix lands, it re-runs.

- **OC1B-376** Inventory the services under `services/`: every directory that carries a Goose service or its tests. Proof: os-build/logs/OC1B-goose-inventory.txt with the full list.
- **OC1B-377** Read `services/run-goose-tests.sh` and record the build path it invokes, verbatim. Proof: the quoted path line in os-build/logs/OC1B-goose-runner.md.
- **OC1B-378** Check whether that path exists on this Mac. Proof: the existence output in os-build/logs/OC1B-goose-runner.md.
- **OC1B-379** Run `services/run-goose-tests.sh` as-is on the Mac and save the complete output, pass or fail. Proof: os-build/logs/OC1B-goose-run1.txt.
- **OC1B-380** From run 1, build the per-service result table (service, ran?, pass/fail, one-line reason). Proof: the table in os-build/logs/OC1B-goose-runner.md.
- **OC1B-381** Count from run 1: services tested, passed, failed, never-ran. Proof: the count block in os-build/logs/OC1B-goose-runner.md.
- **OC1B-382** For every never-ran service, name why (runner path, missing build, missing test entry) — one line each. Proof: the never-ran block in os-build/logs/OC1B-goose-runner.md.
- **OC1B-383** Check whether a Goose build exists anywhere on this Mac the runner could use (search the standard spots; record what is found, do not install a toolchain fork). Proof: the search results in os-build/logs/OC1B-goose-runner.md.
- **OC1B-384** Run the services' own test entry points individually for the five core services (dashboard, console, bootlog, dhcp, dns) bypassing the runner, if such entry points exist. Proof: os-build/logs/OC1B-goose-core5.txt, or the no-entry-point note per service.
- **OC1B-385** Record the Goose version available on this Mac (or its absence). Proof: the version line in os-build/logs/OC1B-goose-runner.md.
- **OC1B-386** When Buffy's runner-path fix lands on main (check at each pass), re-run the runner and save the new output. Proof: os-build/logs/OC1B-goose-run2.txt, or the fix-not-landed line in os-build/logs/OC1B-goose-runner.md.
- **OC1B-387** Build the run-2 per-service table the same way as OC1B-380. Proof: the run-2 table in os-build/logs/OC1B-goose-runner.md.
- **OC1B-388** Diff run 1 vs run 2 per service: fixed-by-runner, still failing, newly failing. Proof: the diff block in os-build/logs/OC1B-goose-runner.md.
- **OC1B-389** For every still-failing service after run 2, capture its first failing assertion or error verbatim. Proof: the excerpts in os-build/logs/OC1B-goose-failures.txt.
- **OC1B-390** Classify each failure: environment (Mac), runner, or service defect — with the evidence for the class. Proof: the classification table in os-build/logs/OC1B-goose-failures.txt.
- **OC1B-391** File service-defect failures as defect reports for Buffy/Pax; do not edit services in this lane. Proof: the defect list in os-build/logs/OC1B-goose-failures.txt.
- **OC1B-392** Verify the runner leaves the tree clean (no generated files written into `services/`). Proof: the `git status` output quoted in os-build/logs/OC1B-goose-runner.md.
- **OC1B-393** Record the full runner wall-clock time for the better of the two runs. Proof: the timing line in os-build/logs/OC1B-goose-runner.md.
- **OC1B-394** Cross-check your per-service results against Buffy's hosted gate results if she has posted them; every disagreement is named. Proof: the cross-check block in os-build/logs/OC1B-goose-runner.md, or the no-hosted-results line.
- **OC1B-395** Count how many of the inventoried services have ANY passing Mac-side test evidence after this section. Proof: the evidence count in os-build/logs/OC1B-goose-runner.md.
- **OC1B-396** Write the gate-2 verdict: GATE-2 GREEN (all inventoried services ran with results), PARTIAL (named services out), or BLOCKED (runner cannot run), with the deciding numbers. Proof: os-build/logs/OC1B-goose-gate2.md.
- **OC1B-397** Record what gate-2 does NOT prove (hosted behaviour, cross-service integration) in the verdict file — the boundary of the claim. Proof: the boundary block in os-build/logs/OC1B-goose-gate2.md.
- **OC1B-398** If the runner cannot run at all on this Mac after Buffy's fix, record the exact terminal error as the section result. Proof: the error quoted in os-build/logs/OC1B-goose-gate2.md.
- **OC1B-399** Update the status file's Goose rows with run counts and the verdict. Proof: the Goose block in os-build/OPENCODE1_500_STATUS.md.
- **OC1B-400** Commit the §16 artifacts. Proof: the commit sha in os-build/OPENCODE1_500_STATUS.md.

## §17 The 55 failing native tests — decision-pack execution support (OC1B-401..OC1B-425)

Folds in wave-3 §7 (tasks 59–66) and executes its missing half: the
per-group Mac runs. The known failing set is the native-mirror tests
in `tests/native-*.test.mjs` (written for the removed SwiftUI
screens; the native app is a WKWebView shell now). Baselines
disagree — README says 56 failures, wave-3 says 55; settling the
count is a task here. ANALYSIS AND RUNS ONLY: no test or mirror is
changed in this section. The update-vs-carve-out call is Del's,
prepared by Pax from your pack (`docs/NATIVE_TEST_PREP.md` is the
existing classification).

- **OC1B-401** Reproduce the node baseline on the Mac (`npm test` on current main) and record run/pass/fail exactly as the spec reporter prints it. Proof: os-build/logs/OC1B-native-baseline.txt with the summary lines.
- **OC1B-402** Extract the full failing test list from that run, one line per failure, file + test name. Proof: os-build/logs/OC1B-native-failures.txt.
- **OC1B-403** Settle the count: state the exact number of failing tests and reconcile it against README's 56 and wave-3's 55 — the difference explained (a test added/removed/renamed, or a miscount named as one). Proof: the reconciliation block in os-build/logs/OC1B-native-baseline.txt.
- **OC1B-404** Name any failing test that is NOT in the known native-mirror set (a newcomer is a regression signal, reported first). Proof: the newcomer list in os-build/logs/OC1B-native-baseline.txt, or the none line.
- **OC1B-405** Group the failures by file. Proof: the per-file counts in os-build/logs/OC1B-native-groups.md.
- **OC1B-406** Group the failures by root cause (which removed SwiftUI surface each test asserts). Proof: the per-surface counts in os-build/logs/OC1B-native-groups.md.
- **OC1B-407** Run group 1 alone on the Mac (native-ignis-assessment-* files) and record pass/fail per file. Proof: os-build/logs/OC1B-native-g1.txt.
- **OC1B-408** Run group 2 alone (native-header-* and native-ignis-header files). Proof: os-build/logs/OC1B-native-g2.txt.
- **OC1B-409** Run group 3 alone (native-*-ops-console-* files across vigiles/ignis/medicus). Proof: os-build/logs/OC1B-native-g3.txt.
- **OC1B-410** Run group 4 alone (native-settings-*, native-statusbar-*, native-footer-* files). Proof: os-build/logs/OC1B-native-g4.txt.
- **OC1B-411** Run group 5 alone (native-camera-* and native-capture-* files). Proof: os-build/logs/OC1B-native-g5.txt.
- **OC1B-412** Run group 6 alone (native-timeline-*, native-latest-*, native-still-image-*, native-video-* files). Proof: os-build/logs/OC1B-native-g6.txt.
- **OC1B-413** Run group 7 alone (native-logo-*, native-input-*, native-interval-*, native-request-*, native-sampler-*, native-stepper-*, native-stepper-label files and any native file not in groups 1–6). Proof: os-build/logs/OC1B-native-g7.txt.
- **OC1B-414** Confirm the seven group runs sum to the OC1B-401 baseline failing set — no failure lost or double-counted between the full run and the group runs. Proof: the sum check in os-build/logs/OC1B-native-groups.md.
- **OC1B-415** For the UPDATE option: list exactly which Swift-mirror expectations (in `native/Sources/MetaTrio/`) each group asserts, and what updating them would assert instead (wave-3 §7 task 61). Proof: the update table in os-build/logs/OC1B-native-pack.md.
- **OC1B-416** For the CARVE-OUT option: list exactly which test files would move or be marked, and what coverage is lost per file (wave-3 §7 task 62). Proof: the carve-out table in os-build/logs/OC1B-native-pack.md.
- **OC1B-417** Cost each option in files touched and suite time, measured from your group runs (wave-3 §7 task 63). Proof: the cost block in os-build/logs/OC1B-native-pack.md.
- **OC1B-418** Check `docs/NATIVE_TEST_PREP.md`'s classification against your groups; every disagreement is listed. Proof: the disagreement block in os-build/logs/OC1B-native-pack.md.
- **OC1B-419** Write the refreshed decision pack to `os-build/NATIVE_55_DECISION_PACK.md` on the branch (wave-3 §7 task 64, now with per-group Mac evidence attached). Proof: the updated os-build/NATIVE_55_DECISION_PACK.md committed on the branch.
- **OC1B-420** Put the pack's one-line summary in the status file (wave-3 §7 task 66): settled count, groups, both options costed, awaiting Del's tap. Proof: the summary line in os-build/OPENCODE1_500_STATUS.md.
- **OC1B-421** Attest no test file and no Swift mirror was modified in this section (`git diff --stat` for tests/ and native/ is empty). Proof: the empty diff quoted in os-build/logs/OC1B-native-pack.md.
- **OC1B-422** Record whether any failing native test asserts behaviour the WKWebView app still HAS (a real app regression hiding in the stale set) — flag those individually for Pax. Proof: the regression-candidate list in os-build/logs/OC1B-native-pack.md, or the none line.
- **OC1B-423** Time the full node suite on this Mac for the pack's cost rows. Proof: the timing line in os-build/logs/OC1B-native-baseline.txt.
- **OC1B-424** If Del's call lands while you work (update or carve out), record it verbatim in the status file and STOP this section — execution of the call is a separate Pax-assigned job, not improvised here. Proof: the ruling line in os-build/OPENCODE1_500_STATUS.md, or the still-waiting line.
- **OC1B-425** Commit the §17 artifacts. Proof: the commit sha in os-build/OPENCODE1_500_STATUS.md.

## §18 README numbers verification (OC1B-426..OC1B-450)

Folds in wave-3 §8 tasks 67–68 and expands them: EVERY number in
`README.md` is re-derived on the Mac with the command that produced
it recorded beside the number. The tree's README still carries
stale badges (1877 / 1412) that Pax's later main fixes superseded —
your runs, not either text, are the authority. You fix ONLY numbers
your runs prove stale, in one branch commit, for Pax to merge.

- **OC1B-426** Extract every quantitative claim in README.md into a checklist (badges, the numbers table, per-suite rows, line counts, program counts). Proof: os-build/logs/OC1B-readme-checklist.md with one row per claim and its README line.
- **OC1B-427** Re-derive the Node suite numbers: run `npm test` and record run/pass/fail. Proof: the summary lines in os-build/logs/OC1B-readme-node.txt.
- **OC1B-428** Re-derive the Rust workspace numbers: `cargo test --workspace` on the Mac; record passed/failed/suites (Milo's 2186/0/99 is the figure to confirm or correct). Proof: os-build/logs/OC1B-readme-rust.txt with the summary lines.
- **OC1B-429** Re-derive the queue Python numbers: `python3 -m unittest discover -s tests/queue-python` (289 baseline). Proof: os-build/logs/OC1B-readme-queue.txt.
- **OC1B-430** Re-derive the Science Lab numbers: `python3 -m unittest discover -s tests/science-lab` (163 baseline). Proof: os-build/logs/OC1B-readme-science.txt.
- **OC1B-431** Re-derive the Hortus numbers: `python3 -m unittest discover -s os/tests -p "test_hortus*.py"` (14 baseline). Proof: os-build/logs/OC1B-readme-hortus.txt.
- **OC1B-432** Re-derive the Officina Python numbers from README's own table row (`python3 -m unittest discover -s tests/officina`, 49 claimed). Proof: os-build/logs/OC1B-readme-officina.txt.
- **OC1B-433** Re-derive the OS loop harness row (`bash os/os/loop-tests/metaos-loop.test.sh`, 12 of 12 claimed). Proof: os-build/logs/OC1B-readme-loop.txt.
- **OC1B-434** Re-derive the kernel line count: `wc -l kernel/src/*.rs`, total and per file. Proof: os-build/logs/OC1B-readme-kernel-lines.txt.
- **OC1B-435** Re-derive the whole-repo source line count by README's stated method (its ~122,000 / 253,245-era figures — reproduce the method, then the number). Proof: os-build/logs/OC1B-readme-repo-lines.txt with the exact command used.
- **OC1B-436** Re-derive the worlds-packs count: run `os/worlds/validate_pack.py` (or the validator the packs name) and count the valid packs (badge says 9 of 9; Bond's audit counted 12 packs — settle it). Proof: os-build/logs/OC1B-readme-worlds.txt.
- **OC1B-437** Verify the README program list against `js/products.js`: every product named in the README exists in products.js and every products.js entry is either in the README or named as omitted. Proof: the two-way check in os-build/logs/OC1B-readme-checklist.md.
- **OC1B-438** Verify the README's per-program status words against the status files (Imperium, Science Lab, Officina, Musica, Aegis, Nervus, Hands-Free): any status word a status file contradicts is listed. Proof: the status-word rows in os-build/logs/OC1B-readme-checklist.md.
- **OC1B-439** Verify every live link in the README resolves (repo link, site link, the 16-link set from the v5 verification era) — from the Mac, recording HTTP status per link. Proof: os-build/logs/OC1B-readme-links.txt.
- **OC1B-440** Verify the README's test-count table commands all run as printed (each command copied verbatim from the table). Proof: the per-command results in os-build/logs/OC1B-readme-checklist.md.
- **OC1B-441** Mark every checklist row VERIFIED (your run matches), STALE (your run differs — new number recorded), or UNVERIFIABLE-ON-MAC (named reason). Proof: the completed os-build/logs/OC1B-readme-checklist.md.
- **OC1B-442** Fix ONLY the STALE numbers in README.md, one branch commit, no wording changes beyond the numbers themselves (wave-3 §8 task 68). Proof: the README diff committed on the branch, quoted in os-build/logs/OC1B-readme-fixes.md.
- **OC1B-443** Re-run the affected suites after the fix commit to confirm the printed numbers now match a fresh run. Proof: the confirmation lines in os-build/logs/OC1B-readme-fixes.md.
- **OC1B-444** Confirm the badge URLs in README.md render the new numbers (badge text matches the shield parameters). Proof: the badge check in os-build/logs/OC1B-readme-fixes.md.
- **OC1B-445** List every number you could NOT re-derive and why — these stay Pax's problem, named, not silently left. Proof: the underived block in os-build/logs/OC1B-readme-checklist.md.
- **OC1B-446** Record the tree sha every number in this section was derived on — numbers without a tree are not numbers. Proof: the sha line heading os-build/logs/OC1B-readme-checklist.md.
- **OC1B-447** Check the site copy (`site/index.html`) for any number that contradicts your derived set; list them for Pax (the site is not yours to edit). Proof: the site-number list in os-build/logs/OC1B-readme-checklist.md.
- **OC1B-448** Check the face's seed/status text for numbers contradicting your derived set; list them the same way. Proof: the face-number list in os-build/logs/OC1B-readme-checklist.md.
- **OC1B-449** Write the section verdict: README numbers are all VERIFIED/STALE-fixed, or the underived list is the verdict. Proof: the verdict block in os-build/logs/OC1B-readme-fixes.md.
- **OC1B-450** Commit the §18 artifacts. Proof: the commit sha in os-build/OPENCODE1_500_STATUS.md.

## §19 Submission prep (OC1B-451..OC1B-475)

Grounded in `os-build/SUBMISSION_CHECKLIST.md` (DRAFT, ML4-5),
`os-build/FREEZE_CERT.md` (converts to a submission-day state
snapshot — Del's no-freeze ruling), and Milo's claim audit (ML4-4).
Deadline: Wednesday Nov 4, 2026, 9:00 PM ET. NOTHING goes out under
Del's name in this section — forms, posts, and submission are Del's
hands; you prepare and dry-run only.

- **OC1B-451** Walk `os-build/SUBMISSION_CHECKLIST.md` item by item and record the current state of each of its seven items. Proof: os-build/logs/OC1B-submission-walk.md with one block per item.
- **OC1B-452** Item 1 (repo public and fresh): verify from the Mac that `Mrfentmen/meta-os` is public and was created in the event window. Proof: the API/CLI output quoted in os-build/logs/OC1B-submission-walk.md.
- **OC1B-453** Item 2 (Meta model named): record which Meta models the submission can truthfully name from §9/§10's receipts (Spark, Wonder, SAM 3.1, Muse Image — only those with receipts). Proof: the model list with receipt paths in os-build/logs/OC1B-submission-walk.md.
- **OC1B-454** Item 3 (3-minute demo video): confirm §11's final film is on the branch/main path the checklist will cite, at exactly 180.000s. Proof: the ffprobe line quoted in os-build/logs/OC1B-submission-walk.md.
- **OC1B-455** Item 4 (attributions): compile the library list — everything in the submission not built in the window (bootloader crate, QEMU/SeaBIOS in logs, the full set you can find) with where each is used. Proof: os-build/logs/OC1B-submission-attributions.md.
- **OC1B-456** Item 5 (one project only): record the single-project statement and list the lanes that must NOT be entered separately (Trio server, Custos-retired, other systems are parts of this one platform submission). Proof: the statement block in os-build/logs/OC1B-submission-walk.md.
- **OC1B-457** Item 6 (claim audit): confirm Milo's claim audit (ML4-4) has landed and link every claim in the demo/submission to its audit row. Proof: the audit path + row map in os-build/logs/OC1B-submission-walk.md, or the audit-not-landed BLOCKED line.
- **OC1B-458** Item 7 (no secrets): re-run the secret scan over the full repo tree on the Mac and record the hit count (values never printed). Proof: os-build/logs/OC1B-submission-secrets.txt with counts only.
- **OC1B-459** Build the submission-day state snapshot with Milo (the FREEZE_CERT successor): final tip hash and gate result fields filled from your own runs. Proof: the snapshot draft at os-build/logs/OC1B-state-snapshot.md with Milo's name on the rows he owns.
- **OC1B-460** Fill the snapshot's claim-clause map: each clause of the claim sentence → PROVEN + its committed log path, or UNPROVEN. Proof: the completed clause table in os-build/logs/OC1B-state-snapshot.md.
- **OC1B-461** For every UNPROVEN clause in that map, write the one-line reason it is unproven — the snapshot ships honest or not at all. Proof: the reasons in os-build/logs/OC1B-state-snapshot.md.
- **OC1B-462** Dry-run every submission form field against repo facts; any field whose answer is not in the repo is marked DEL-ONLY (wave-3 §8 task 70). Proof: os-build/logs/OC1B-submission-fields.md.
- **OC1B-463** Confirm the X post draft exists (wave-2's or a fresh draft); if missing, draft it — Del posts it himself (wave-3 §8 task 72). Proof: the draft file path in os-build/logs/OC1B-submission-walk.md.
- **OC1B-464** Verify the demo film, runbook (§11), and snapshot paths all resolve on main or the named branch (wave-3 §8 task 73). Proof: the path check in os-build/logs/OC1B-submission-walk.md.
- **OC1B-465** Full rehearsal from a CLEAN CLONE: follow §11's runbook on a fresh clone as if it were submission day, nothing pre-built. Proof: os-build/logs/OC1B-submission-rehearsal.md with the total time and every manual step hit.
- **OC1B-466** Log every rehearsal failure or slow step with its fix or named owner. Proof: the gaps block in os-build/logs/OC1B-submission-rehearsal.md.
- **OC1B-467** Confirm the demo's honest-labelling set one last time: SIMULATED labels, the staged-reading disclosure in CAPTURE_NOTES, Medicus wording (scene only). Proof: the labelling check in os-build/logs/OC1B-submission-walk.md.
- **OC1B-468** Confirm no artifact in the submission set claims the face is the OS or that a web page boots. Proof: the wording sweep output in os-build/logs/OC1B-submission-walk.md.
- **OC1B-469** Assemble the DEL-ONLY list: every item only Del can do (submit, post, sign, pay) in one short list for the status file (wave-3 §8 task 75). Proof: the DEL-ONLY block in os-build/OPENCODE1_500_STATUS.md.
- **OC1B-470** Write the timeline to the deadline: what must land by Nov 4 21:00 ET, in order, with owners. Proof: os-build/logs/OC1B-submission-timeline.md.
- **OC1B-471** Verify the judging-facing numbers one last time against §18's derived set (Impact/tooling/demo/depth claims use only verified numbers). Proof: the numbers check in os-build/logs/OC1B-submission-walk.md.
- **OC1B-472** Record the final gate state the submission stands on (last §8 wave's gate + §1 baseline lineage). Proof: the gate lineage in os-build/logs/OC1B-state-snapshot.md.
- **OC1B-473** If the claim audit (OC1B-457) has not landed by this pass, record the submission as NOT READY on that row alone — everything else proceeds. Proof: the readiness line in os-build/logs/OC1B-submission-walk.md.
- **OC1B-474** Write the section verdict: SUBMISSION SET READY (every row proven or honestly UNPROVEN) or the named rows that are not. Proof: the verdict block in os-build/logs/OC1B-submission-walk.md.
- **OC1B-475** Commit the §19 artifacts. Proof: the commit sha in os-build/OPENCODE1_500_STATUS.md.

## §20 Closeout (OC1B-476..OC1B-500)

- **OC1B-476** Build the final gate ledger: every gate run in this list (baseline, KF gates, K3, K4, re-proof waves, carrier checks, Goose gate-2) with date, tree sha, and result. Proof: os-build/logs/OC1B-gate-ledger.md.
- **OC1B-477** Build the proof index: every claim this list made → its committed file, one row per claim (successor to WAVE3_PROOF_INDEX's line). Proof: os-build/logs/OC1B-proof-index.md.
- **OC1B-478** Sweep the proof index for any claim whose file does not exist at the named path; each is struck and moved to the unproven list. Proof: the struck rows noted in os-build/logs/OC1B-proof-index.md.
- **OC1B-479** Write the honest UNIMPLEMENTED list for the submission: everything this list found not built (named from the sections: graphics pieces Rowan never landed, voice surface, remote MCP adapters, ladder 4–6, and their kin). Proof: os-build/logs/OC1B-unimplemented.md.
- **OC1B-480** Write the honest UNPROVEN list: built but never gated on the Mac (each with the missing proof named). Proof: os-build/logs/OC1B-unproven.md.
- **OC1B-481** Sweep the whole `opencode/500` branch for secrets (keys, tokens) and report the sweep, never the values (wave-3 §10 task 93's discipline). Proof: os-build/logs/OC1B-closeout-secrets.txt with counts only.
- **OC1B-482** Sweep the branch for any file over 1MB you added; justify each in one line or remove it. Proof: os-build/logs/OC1B-closeout-largefiles.txt.
- **OC1B-483** Confirm no image part, bootimage binary, or film intermediate was committed anywhere on the branch. Proof: the `git ls-files` grep output in os-build/logs/OC1B-closeout-largefiles.txt.
- **OC1B-484** Confirm the branch carries no edit to `kernel/src/syscalls.rs` anywhere in its history. Proof: the empty `git log -p` grep for that path, quoted in os-build/logs/OC1B-closeout-secrets.txt.
- **OC1B-485** Confirm every kernel/src edit on the branch (expected: none) is either absent or tied to Rowan's named request recorded in the status file. Proof: the kernel-diff summary in os-build/logs/OC1B-closeout-secrets.txt.
- **OC1B-486** Collect any soak still marked RUNNING (§7) and record its final verdict or its died-with-session state. Proof: the collected verdicts appended to os-build/logs/OC1B-soak-summary.md.
- **OC1B-487** Inventory the demo assets (film, frames, captures, runbook) with paths and hashes. Proof: os-build/logs/OC1B-demo-inventory.md.
- **OC1B-488** Re-run gate.sh one final time on the branch tip tree and record the result as the list's last kernel word. Proof: os-build/logs/OC1B-closeout-gate.log.
- **OC1B-489** Re-run the node suite one final time on the branch tip and record against §17's baseline. Proof: os-build/logs/OC1B-closeout-node.txt.
- **OC1B-490** Re-run the queue suite one final time on the branch tip and record against §9's baseline. Proof: os-build/logs/OC1B-closeout-queue.txt.
- **OC1B-491** Count the proofs this list committed (logs, screendumps, receipts, gate outputs) by type — counted from the index, never estimated. Proof: the counts block in os-build/logs/OC1B-proof-index.md.
- **OC1B-492** Write the handoff note to Pax: branch tip, what is ready to merge, what must NOT merge (named files, if any), and the merge order you recommend. Proof: os-build/logs/OC1B-handoff.md.
- **OC1B-493** Final status-file pass: every section marked DONE or UNPROVEN with its reason — no silent gaps (wave-3 §10 task 95's discipline). Proof: the completed os-build/OPENCODE1_500_STATUS.md.
- **OC1B-494** Verify the status file's every proof path resolves to a committed file. Proof: the path-resolution check output appended to os-build/logs/OC1B-proof-index.md.
- **OC1B-495** Record the list's total live spend across all sections from the receipts and guardrail records. Proof: the total in os-build/logs/OC1B-handoff.md, labelled an estimate at Spark rates.
- **OC1B-496** Record total Mac-lane wall-clock the list consumed, by section. Proof: the time table in os-build/logs/OC1B-handoff.md.
- **OC1B-497** Final commit on `opencode/500`. Proof: the commit sha in os-build/OPENCODE1_500_STATUS.md.
- **OC1B-498** Post nothing to main and nothing to the bus from this list — Pax merges and posts at the checkpoint (wave-3 §10 task 97's discipline); record that this line was obeyed. Proof: the attestation line in os-build/logs/OC1B-handoff.md.
- **OC1B-499** If any section finished early during the run, record where its spare time went (the next section started — never idle, wave-3 §10 task 98's discipline). Proof: the spare-time note in os-build/logs/OC1B-handoff.md.
- **OC1B-500** The last line of the status file: what remains unproven in this 500, in plain words (wave-3 §10 task 100's discipline). Proof: the final line of os-build/OPENCODE1_500_STATUS.md.

# HANA TASKS 500 — L6 Shell & Apps (Lobster) + Intel Crate (B10)

**Owner:** Hana (bus nick `mute`). **Layer:** L6 — Shell and apps, Lobster
(per os-build/LAYERS.md: "Lobster: the home surface and app side, real OS
state only"). Plus the intel crate (crates/intel/src/b10_brief/), which is
Hana's standing B10 lane.
**Order:** Del, 2026-11-02 — 500 tasks, real OS work. L6 is being rebuilt
as kernel/Lobster work. This list contains NO web features.
**Status file:** `os-build/HANA_500_STATUS.md` — Hana keeps it current;
every proof named in a task lands there (counts, transcripts, diffs,
verdicts), not on the bus.
**Branch:** Hana's working branch per section block; NEVER main directly.
**Merges:** through Pax only, and only after Milo gate-1 GREEN on the tip
(gate verdict from Milo's own bus words). B10 deltas additionally need the
parity suite green.
**Builds on:** main's brief.rs (7,080 lines; the B10 deltas Milo already
gated GREEN are on main). The stuck batch/B10 tip @862d5332 is RED #6 —
Section 01 fixes it; nothing else in this list builds on that tip until
Section 01 closes GREEN.

## Fences (do not cross, do not re-ask)

1. NEVER edit `kernel/src` — that is Rowan's pen. `kernel/src/syscalls.rs`
   is FROZEN: no edits, no new syscall numbers, ever, from this list.
2. `js/products.js` is the single source of truth for products and
   categories. ANY category/product change lands in products.js AND the
   Swift mirror (native/Sources/MetaTrio/Models/ProductConfig.swift) AND
   both prompt builders, in one commit set — never one without the others.
3. No web/PWA feature work. The face is a design reference only. Anything
   in this list that produces visuals produces DATA (frames, glyphs,
   icons, palettes) + program logic for the kernel/Lobster side.
4. NO MOCKS. A view with no real service or record behind it renders its
   ruled empty line or is marked NOT BUILT with the missing piece named.
   Imperium dispatch stays SIMULATED and labelled, loopback only.
   Medicus is scene awareness only — no diagnosis, cause, severity, or
   treatment language anywhere, including test strings.
5. Status words exactly: DESIGNED / WRITTEN / COMPILED / VERIFIED /
   NOT BUILT / BLOCKED (blocker named). A claim is VERIFIED only with
   the proof its task names.
6. Kernel console discipline is untouched: the kernel help line stays
   exactly `commands: status help uptime mem ps`. Lobster-shell commands
   in this list live in the Lobster shell's own help, generated from its
   dispatch table — they are never added to the kernel's list.

## How to work the list

In section order. Sections 01–07 close the B10/intel debt first (the
crate must compile and gate GREEN before filler work counts). Sections
08–12 build the Lobster shell. Sections 13–15 produce the kernel-face
asset data Rowan's KF lane consumes. Sections 16–19 build the Lobster
apps. Section 20 is parity + honest labelling + the final gate pack.
One commit per task unless the task says otherwise; every commit message
carries its HN5 id.


## Section 01 — B10 Borrow Fix and Re-Gate (batch/B10, sixth RED @862d5332)

- HN5-001 — Read Milo's sixth RED verbatim (E0382, crates/intel/src/b10_brief/brief.rs:8093 on branch batch/B10) and copy the failing test name + line into os-build/HANA_500_STATUS.md. Proof: status file quotes the gate message and the tip SHA 862d5332.
- HN5-002 — In the failing test, change `record.recovered.expect(...)` to borrow first (`record.recovered.as_ref().expect(...)` or the compiler-suggested equivalent) so `record` is not partially moved before `recovery_line(Some(&record))`. Proof: committed diff on batch/B10 shows only the borrow fix at that site; file + commit SHA in status file.
- HN5-003 — Audit every other partial-move risk in brief.rs: grep all `.expect(` / `.unwrap(` on fields of a struct that is borrowed later in the same test and list each site safe-or-fixed. Proof: audit list committed in status file; zero unexamined sites.
- HN5-004 — Run `cargo check -p intel` on the fixed branch tip. Proof: check output tail (clean, warnings counted) pasted in status file.
- HN5-005 — Run `cargo test -p intel --lib` on the fixed tip. Proof: test count line (passed/failed) in status file; success = lib compiles and all lib tests run — the thing six REDs blocked.
- HN5-006 — Run the b10_parity integration tests on the fixed tip. Proof: parity count (47/47 at last gate) in status file.
- HN5-007 — Confirm the fix did not change any production (non-test) code path in brief.rs. Proof: diff stat in status file names only test-module lines, or names and justifies any exception.
- HN5-008 — Verify main's brief.rs (7,080 lines) does not carry the same bug: locate the recovery test in main's copy and state whether the borrow pattern exists there. Proof: line number + verdict in status file.
- HN5-009 — Post the new branch tip SHA + the three run outputs (check, lib tests, parity) to the status file as the re-gate pack. Proof: status file section 'RE-GATE PACK 1' complete.
- HN5-010 — Request Milo gate-1 on the new tip by name in the status file (Pax relays; Hana does not merge). Proof: request line with tip SHA recorded.
- HN5-011 — If Milo returns RED again: fix only the newly named site, repeat tasks 2-9 as RE-GATE PACK 2, and record what differed. Proof: pack 2 in status file; no silent retries.
- HN5-012 — If Milo returns GREEN: record the verdict verbatim in the status file and mark the B10 delta 'cleared for Pax merge check'. Proof: verdict quoted with Milo's test counts.
- HN5-013 — Write the one-paragraph root-cause note for the status file: why filler commits kept growing brief.rs past the broken test without fixing it, and the rule now in force (no new filler lands on a RED tip). Proof: note present in status file.
- HN5-014 — Add a compile-the-tests step to Hana's own pre-push checklist in the status file: `cargo test -p intel --lib --no-run` before any brief.rs push. Proof: checklist line present.
- HN5-015 — Sweep the other b10_brief modules (sections.rs, window.rs, forecast.rs, dispatch.rs, notify.rs, push.rs, wake.rs, baton.rs, alerts.rs) for the same partial-move pattern in their tests. Proof: per-file verdict list in status file.
- HN5-016 — Fix any same-pattern site found in task 15's sweep, one commit each, each with its own `cargo test -p intel --lib` run. Proof: commit SHAs + counts in status file.
- HN5-017 — Re-run the full intel crate test suite (`cargo test -p intel`) after all S01 fixes. Proof: full-suite count line in status file.
- HN5-018 — Check brief.rs compiles with no new warnings vs the pre-fix warning count. Proof: both counts in status file.
- HN5-019 — Record the final S01 branch state (tip SHA, gate verdict, counts) as the base every later B10 section builds on. Proof: 'S01 BASE' block in status file.
- HN5-020 — Confirm no file outside crates/intel/src/b10_brief/ changed in S01. Proof: branch diff name-only list in status file.
- HN5-021 — Write the merge-request summary for Pax: delta vs main, files, counts, gate verdict — in the status file, not on the bus. Proof: summary block present.
- HN5-022 — If the delta conflicts with main's brief.rs (main moved during Round 12 merges): hand-combine plan written in status file (which hunks are Hana's, which are main's), no force-push. Proof: plan block present or 'no conflict' line with the checked main SHA.
- HN5-023 — Close S01 in the status file with the status word for brief.rs on the branch: COMPILED or VERIFIED per Milo's verdict only. Proof: status word line present.
- HN5-024 — List every brief.rs test that still does not run (ignored/should-panic/skipped) with a one-line reason each. Proof: list in status file; feeds S05.
- HN5-025 — Hand-off note in status file: exact commands Milo should re-run for the next gate, copied from the runs that passed locally. Proof: command block present.

## Section 02 — Intel Crate — Record Fillers Completion I (state, recovery, pointers, since, priority)

- HN5-026 — System state record: fill the remaining field gap in `system_state_lines` so every populated field of the record renders exactly one line, in spec order. Proof: new unit test with a fully populated record passes; `cargo test -p intel --lib` count in status file.
- HN5-027 — System state record: empty-record behaviour — `system_state_lines` takes `&SystemState` (no None form exists in the crate), so an all-default record renders the ruled empty-state line (no blank gap, no invented data), and the composer's Option<SystemState> None case routes to that same line. Proof: unit tests for the all-default record and the composer None route pass; both outputs quoted in status file.
- HN5-028 — System state record: budget behaviour — an oversize System state record record trims at the section budget without cutting a line mid-way. Proof: boundary test (exactly at budget, one over) passes; counts in status file.
- HN5-029 — System state record: redaction behaviour — a System state record record containing a secret-shaped string is redacted by the shared redactor before rendering. Proof: test asserts the secret string is absent from output; counts in status file.
- HN5-030 — System state record: parity — the Rust `system_state_lines` output matches the JS brief's System state record section line-for-line on the shared fixture. Proof: parity test case added under b10_parity and passing; parity total in status file.
- HN5-031 — Recovery record: fill the remaining field gap in `recovery_line` so every populated field of the record renders exactly one line, in spec order. Proof: new unit test with a fully populated record passes; `cargo test -p intel --lib` count in status file.
- HN5-032 — Recovery record: None/empty record renders the ruled empty-state line (no blank gap, no invented data) via `recovery_line`. Proof: unit test with None and with an all-empty record passes; both outputs quoted in status file.
- HN5-033 — Recovery record: budget behaviour — an oversize Recovery record record trims at the section budget without cutting a line mid-way. Proof: boundary test (exactly at budget, one over) passes; counts in status file.
- HN5-034 — Recovery record: redaction behaviour — a Recovery record record containing a secret-shaped string is redacted by the shared redactor before rendering. Proof: test asserts the secret string is absent from output; counts in status file.
- HN5-035 — Recovery record: parity — the Rust `recovery_line` output matches the JS brief's Recovery record section line-for-line on the shared fixture. Proof: parity test case added under b10_parity and passing; parity total in status file.
- HN5-036 — Source pointer record: fill the remaining field gap in `source_pointer_lines` so every populated field of the record renders exactly one line, in spec order. Proof: new unit test with a fully populated record passes; `cargo test -p intel --lib` count in status file.
- HN5-037 — Source pointer record: None/empty record renders the ruled empty-state line (no blank gap, no invented data) via `source_pointer_lines`. Proof: unit test with None and with an all-empty record passes; both outputs quoted in status file.
- HN5-038 — Source pointer record: budget behaviour — an oversize Source pointer record record trims at the section budget without cutting a line mid-way. Proof: boundary test (exactly at budget, one over) passes; counts in status file.
- HN5-039 — Source pointer record: redaction behaviour — a Source pointer record record containing a secret-shaped string is redacted by the shared redactor before rendering. Proof: test asserts the secret string is absent from output; counts in status file.
- HN5-040 — Source pointer record: parity — the Rust `source_pointer_lines` output matches the JS brief's Source pointer record section line-for-line on the shared fixture. Proof: parity test case added under b10_parity and passing; parity total in status file.
- HN5-041 — Since-last-brief record: fill the remaining field gap in `since_last_brief_lines` so every populated field of the record renders exactly one line, in spec order. Proof: new unit test with a fully populated record passes; `cargo test -p intel --lib` count in status file.
- HN5-042 — Since-last-brief record: None/empty record renders the ruled empty-state line (no blank gap, no invented data) via `since_last_brief_lines`. Proof: unit test with None and with an all-empty record passes; both outputs quoted in status file.
- HN5-043 — Since-last-brief record: budget behaviour — an oversize Since-last-brief record record trims at the section budget without cutting a line mid-way. Proof: boundary test (exactly at budget, one over) passes; counts in status file.
- HN5-044 — Since-last-brief record: redaction behaviour — a Since-last-brief record record containing a secret-shaped string is redacted by the shared redactor before rendering. Proof: test asserts the secret string is absent from output; counts in status file.
- HN5-045 — Since-last-brief record: parity — the Rust `since_last_brief_lines` output matches the JS brief's Since-last-brief record section line-for-line on the shared fixture. Proof: parity test case added under b10_parity and passing; parity total in status file.
- HN5-046 — Priority order record: fill the remaining field gap in `priority_order_lines` so every populated field of the record renders exactly one line, in spec order. Proof: new unit test with a fully populated record passes; `cargo test -p intel --lib` count in status file.
- HN5-047 — Priority order record: None/empty record renders the ruled empty-state line (no blank gap, no invented data) via `priority_order_lines`. Proof: unit test with None and with an all-empty record passes; both outputs quoted in status file.
- HN5-048 — Priority order record: budget behaviour — an oversize Priority order record record trims at the section budget without cutting a line mid-way. Proof: boundary test (exactly at budget, one over) passes; counts in status file.
- HN5-049 — Priority order record: redaction behaviour — a Priority order record record containing a secret-shaped string is redacted by the shared redactor before rendering. Proof: test asserts the secret string is absent from output; counts in status file.
- HN5-050 — Priority order record: parity — the Rust `priority_order_lines` output matches the JS brief's Priority order record section line-for-line on the shared fixture. Proof: parity test case added under b10_parity and passing; parity total in status file.

## Section 03 — Intel Crate — Record Fillers Completion II (contacts, decisions, onjoin, environment, federation)

- HN5-051 — Blocked contacts record: fill the remaining field gap in `blocked_contact_lines` so every populated field of the record renders exactly one line, in spec order. Proof: new unit test with a fully populated record passes; `cargo test -p intel --lib` count in status file.
- HN5-052 — Blocked contacts record: None/empty record renders the ruled empty-state line (no blank gap, no invented data) via `blocked_contact_lines`. Proof: unit test with None and with an all-empty record passes; both outputs quoted in status file.
- HN5-053 — Blocked contacts record: budget behaviour — an oversize Blocked contacts record record trims at the section budget without cutting a line mid-way. Proof: boundary test (exactly at budget, one over) passes; counts in status file.
- HN5-054 — Blocked contacts record: redaction behaviour — a Blocked contacts record record containing a secret-shaped string is redacted by the shared redactor before rendering. Proof: test asserts the secret string is absent from output; counts in status file.
- HN5-055 — Blocked contacts record: parity — the Rust `blocked_contact_lines` output matches the JS brief's Blocked contacts record section line-for-line on the shared fixture. Proof: parity test case added under b10_parity and passing; parity total in status file.
- HN5-056 — Held decisions record: fill the remaining field gap in `held_decisions_lines` so every populated field of the record renders exactly one line, in spec order. Proof: new unit test with a fully populated record passes; `cargo test -p intel --lib` count in status file.
- HN5-057 — Held decisions record: None/empty record renders the ruled empty-state line (no blank gap, no invented data) via `held_decisions_lines`. Proof: unit test with None and with an all-empty record passes; both outputs quoted in status file.
- HN5-058 — Held decisions record: budget behaviour — an oversize Held decisions record record trims at the section budget without cutting a line mid-way. Proof: boundary test (exactly at budget, one over) passes; counts in status file.
- HN5-059 — Held decisions record: redaction behaviour — a Held decisions record record containing a secret-shaped string is redacted by the shared redactor before rendering. Proof: test asserts the secret string is absent from output; counts in status file.
- HN5-060 — Held decisions record: parity — the Rust `held_decisions_lines` output matches the JS brief's Held decisions record section line-for-line on the shared fixture. Proof: parity test case added under b10_parity and passing; parity total in status file.
- HN5-061 — Onjoin snapshot record: fill the remaining field gap in `onjoin_template_lines` so every populated field of the record renders exactly one line, in spec order. Proof: new unit test with a fully populated record passes; `cargo test -p intel --lib` count in status file.
- HN5-062 — Onjoin snapshot record: empty-record behaviour — `onjoin_template_lines` takes `&OnjoinSnapshot` (no None form exists in the crate), so an all-default snapshot renders the ruled empty-state line (no blank gap, no invented data), and the composer's None case routes to that same line. Proof: unit tests for the all-default snapshot and the composer None route pass; both outputs quoted in status file.
- HN5-063 — Onjoin snapshot record: budget behaviour — an oversize Onjoin snapshot record record trims at the section budget without cutting a line mid-way. Proof: boundary test (exactly at budget, one over) passes; counts in status file.
- HN5-064 — Onjoin snapshot record: redaction behaviour — a Onjoin snapshot record record containing a secret-shaped string is redacted by the shared redactor before rendering. Proof: test asserts the secret string is absent from output; counts in status file.
- HN5-065 — Onjoin snapshot record: parity — the Rust `onjoin_template_lines` output matches the JS brief's Onjoin snapshot record section line-for-line on the shared fixture. Proof: parity test case added under b10_parity and passing; parity total in status file.
- HN5-066 — Environment record: fill the remaining field gap in `environment_lines` so every populated field of the record renders exactly one line, in spec order. Proof: new unit test with a fully populated record passes; `cargo test -p intel --lib` count in status file.
- HN5-067 — Environment record: None/empty record renders the ruled empty-state line (no blank gap, no invented data) via `environment_lines`. Proof: unit test with None and with an all-empty record passes; both outputs quoted in status file.
- HN5-068 — Environment record: budget behaviour — an oversize Environment record record trims at the section budget without cutting a line mid-way. Proof: boundary test (exactly at budget, one over) passes; counts in status file.
- HN5-069 — Environment record: redaction behaviour — a Environment record record containing a secret-shaped string is redacted by the shared redactor before rendering. Proof: test asserts the secret string is absent from output; counts in status file.
- HN5-070 — Environment record: parity — the Rust `environment_lines` output matches the JS brief's Environment record section line-for-line on the shared fixture. Proof: parity test case added under b10_parity and passing; parity total in status file.
- HN5-071 — Federation record: fill the remaining field gap in `federation_lines` so every populated field of the record renders exactly one line, in spec order. Proof: new unit test with a fully populated record passes; `cargo test -p intel --lib` count in status file.
- HN5-072 — Federation record: None/empty record renders the ruled empty-state line (no blank gap, no invented data) via `federation_lines`. Proof: unit test with None and with an all-empty record passes; both outputs quoted in status file.
- HN5-073 — Federation record: budget behaviour — an oversize Federation record record trims at the section budget without cutting a line mid-way. Proof: boundary test (exactly at budget, one over) passes; counts in status file.
- HN5-074 — Federation record: redaction behaviour — a Federation record record containing a secret-shaped string is redacted by the shared redactor before rendering. Proof: test asserts the secret string is absent from output; counts in status file.
- HN5-075 — Federation record: parity — the Rust `federation_lines` output matches the JS brief's Federation record section line-for-line on the shared fixture. Proof: parity test case added under b10_parity and passing; parity total in status file.

## Section 04 — Intel Crate — Record Fillers Completion III (memory, daily, screenshots, briefs, sessions)

- HN5-076 — Memory budget record: fill the remaining field gap in `memory_budget_lines` so every populated field of the record renders exactly one line, in spec order. Proof: new unit test with a fully populated record passes; `cargo test -p intel --lib` count in status file.
- HN5-077 — Memory budget record: None/empty record renders the ruled empty-state line (no blank gap, no invented data) via `memory_budget_lines`. Proof: unit test with None and with an all-empty record passes; both outputs quoted in status file.
- HN5-078 — Memory budget record: budget behaviour — an oversize Memory budget record record trims at the section budget without cutting a line mid-way. Proof: boundary test (exactly at budget, one over) passes; counts in status file.
- HN5-079 — Memory budget record: redaction behaviour — a Memory budget record record containing a secret-shaped string is redacted by the shared redactor before rendering. Proof: test asserts the secret string is absent from output; counts in status file.
- HN5-080 — Memory budget record: parity — the Rust `memory_budget_lines` output matches the JS brief's Memory budget record section line-for-line on the shared fixture. Proof: parity test case added under b10_parity and passing; parity total in status file.
- HN5-081 — Memory depth record: fill the remaining field gap in `memory_depth_lines` so every populated field of the record renders exactly one line, in spec order. Proof: new unit test with a fully populated record passes; `cargo test -p intel --lib` count in status file.
- HN5-082 — Memory depth record: None/empty record renders the ruled empty-state line (no blank gap, no invented data) via `memory_depth_lines`. Proof: unit test with None and with an all-empty record passes; both outputs quoted in status file.
- HN5-083 — Memory depth record: budget behaviour — an oversize Memory depth record record trims at the section budget without cutting a line mid-way. Proof: boundary test (exactly at budget, one over) passes; counts in status file.
- HN5-084 — Memory depth record: redaction behaviour — a Memory depth record record containing a secret-shaped string is redacted by the shared redactor before rendering. Proof: test asserts the secret string is absent from output; counts in status file.
- HN5-085 — Memory depth record: parity — the Rust `memory_depth_lines` output matches the JS brief's Memory depth record section line-for-line on the shared fixture. Proof: parity test case added under b10_parity and passing; parity total in status file.
- HN5-086 — Daily record: fill the remaining field gap in `daily_lines` so every populated field of the record renders exactly one line, in spec order. Proof: new unit test with a fully populated record passes; `cargo test -p intel --lib` count in status file.
- HN5-087 — Daily record: None/empty record renders the ruled empty-state line (no blank gap, no invented data) via `daily_lines`. Proof: unit test with None and with an all-empty record passes; both outputs quoted in status file.
- HN5-088 — Daily record: budget behaviour — an oversize Daily record record trims at the section budget without cutting a line mid-way. Proof: boundary test (exactly at budget, one over) passes; counts in status file.
- HN5-089 — Daily record: redaction behaviour — a Daily record record containing a secret-shaped string is redacted by the shared redactor before rendering. Proof: test asserts the secret string is absent from output; counts in status file.
- HN5-090 — Daily record: parity — the Rust `daily_lines` output matches the JS brief's Daily record section line-for-line on the shared fixture. Proof: parity test case added under b10_parity and passing; parity total in status file.
- HN5-091 — Screenshot digest record: fill the remaining field gap in `screenshot_digest_lines` so every populated field of the record renders exactly one line, in spec order. Proof: new unit test with a fully populated record passes; `cargo test -p intel --lib` count in status file.
- HN5-092 — Screenshot digest record: None/empty record renders the ruled empty-state line (no blank gap, no invented data) via `screenshot_digest_lines`. Proof: unit test with None and with an all-empty record passes; both outputs quoted in status file.
- HN5-093 — Screenshot digest record: budget behaviour — an oversize Screenshot digest record record trims at the section budget without cutting a line mid-way. Proof: boundary test (exactly at budget, one over) passes; counts in status file.
- HN5-094 — Screenshot digest record: redaction behaviour — a Screenshot digest record record containing a secret-shaped string is redacted by the shared redactor before rendering. Proof: test asserts the secret string is absent from output; counts in status file.
- HN5-095 — Screenshot digest record: parity — the Rust `screenshot_digest_lines` output matches the JS brief's Screenshot digest record section line-for-line on the shared fixture. Proof: parity test case added under b10_parity and passing; parity total in status file.
- HN5-096 — Previous brief + previous session records: fill the remaining field gap in `previous_session_digest` so every populated field of the record renders exactly one line, in spec order. Proof: new unit test with a fully populated record passes; `cargo test -p intel --lib` count in status file.
- HN5-097 — Previous brief + previous session records: None/empty record renders the ruled empty-state line (no blank gap, no invented data) via `previous_session_digest`. Proof: unit test with None and with an all-empty record passes; both outputs quoted in status file.
- HN5-098 — Previous brief + previous session records: budget behaviour — an oversize Previous brief + previous session records record trims at the section budget without cutting a line mid-way. Proof: boundary test (exactly at budget, one over) passes; counts in status file.
- HN5-099 — Previous brief + previous session records: redaction behaviour — a Previous brief + previous session records record containing a secret-shaped string is redacted by the shared redactor before rendering. Proof: test asserts the secret string is absent from output; counts in status file.
- HN5-100 — Previous brief + previous session records: parity — the Rust `previous_session_digest` output matches the JS brief's Previous brief + previous session records section line-for-line on the shared fixture. Proof: parity test case added under b10_parity and passing; parity total in status file.

## Section 05 — Brief Composer and Orchestration (generate_brief / store_brief)

- HN5-101 — generate_brief: pin the section order (state, recovery, priority, blockers, decisions, memory, daily, federation, screenshots) in one named constant with a comment citing the spec. Proof: unit test asserts rendered section order; counts in status file.
- HN5-102 — generate_brief: deduplicate identical lines across sections (same line from two fillers renders once, first position wins). Proof: fixture with a duplicated line; test asserts single occurrence.
- HN5-103 — generate_brief: per-section budget allocation uses brief_budget(kind) for every section kind; unknown kind fails loudly, never silently zero. Proof: tests for each known kind + one unknown-kind error test.
- HN5-104 — generate_brief: failure copy — when a section's data source errors, the brief carries failure_copy_for_kind text, not a panic and not a blank. Proof: one test per kind with a forced error.
- HN5-105 — generate_brief: total-budget trim — trim_to_budget applied once at the end, section boundaries preserved. Proof: oversize full-brief fixture test; output length asserted.
- HN5-106 — cap_snapshot_window: window trims from the oldest end and marks the trim with the ruled marker line. Proof: boundary tests (under, at, over window) pass.
- HN5-107 — store_brief: index key from brief_index_key(room) is stable across runs for the same room. Proof: test asserts identical keys for identical input and distinct keys across rooms.
- HN5-108 — store_brief: storing a second brief for a room does not overwrite the first brief's index entry. Proof: two-store test reads both back.
- HN5-109 — parse_since: relative forms ('1h', '24h', '7d') parse to the correct cutoff against a fixed now. Proof: table test with fixed timestamps.
- HN5-110 — parse_since: absolute ISO input parses; garbage input returns the named error, not a default. Proof: table test incl. two garbage forms.
- HN5-111 — format_brief_announcement: room + timestamp render exactly the ruled announcement shape. Proof: golden-line test.
- HN5-112 — brief_failure_line: room + error render the ruled failure shape with the error truncated to budget. Proof: golden-line test incl. oversize error.
- HN5-113 — brief_age_seconds + age line: a brief older than the staleness threshold is labelled stale in the brief header. Proof: tests at threshold-1, threshold, threshold+1.
- HN5-114 — brief_exceeds_budget drives the header warning line when the composed brief is over budget. Proof: test asserts warning present/absent correctly.
- HN5-115 — Previous-session build (build_previous_session): shutdown jobs list renders in job order with kinds intact. Proof: fixture test with three jobs of different kinds.
- HN5-116 — Onjoin snapshot: caps (OnjoinCaps) clamp the template sections; a cap of zero removes the section cleanly. Proof: tests at cap 0, 1, and large.
- HN5-117 — Composer redaction pass: redact_secrets runs over the fully composed brief as the last step before store. Proof: end-to-end test with a secret planted in each of three different sections; none survives.
- HN5-118 — Composer determinism: same inputs compose to byte-identical output across two runs. Proof: determinism test (hash equality) in the suite.
- HN5-119 — Composer empty-input case: a brief with every record None still composes to a valid, labelled empty brief. Proof: golden test of the empty brief.
- HN5-120 — Composer unicode case: names/rooms with non-ASCII text compose without panic or mojibake and budgets count chars, not bytes. Proof: unicode fixture test.
- HN5-121 — store_brief round-trip: a composed brief stored and re-read is byte-identical. Proof: round-trip test.
- HN5-122 — Sections module (sections.rs): every section id used by the composer is declared there once; remove or alias any duplicate id. Proof: test asserts id uniqueness; diff in status file.
- HN5-123 — Window module (window.rs): the snapshot window default matches the composer's cap default (one named source, not two literals). Proof: test or shared-constant diff quoted in status file.
- HN5-124 — Write the composer data-flow note (inputs -> fillers -> budgets -> redaction -> store) into the status file so Milo can gate without reading 7,000 lines. Proof: note present, one page max.
- HN5-125 — Full intel suite re-run after S05 lands; record counts as the new B10 baseline. Proof: `cargo test -p intel` count line in status file.

## Section 06 — B10 Parity Tests and the Parity Harness

- HN5-126 — b10_parity: add the system state BOUNDARY golden fixture — a record sized exactly at its section budget, plus its one-over twin — and make both parity cases pass line-for-line (JS vs Rust). Distinct from HN5-030's fully-populated parity case and its Rust-only budget unit test. Proof: parity suite total grows by two and stays green; total in status file.
- HN5-127 — b10_parity: add the recovery BOUNDARY golden fixture — a record sized exactly at its section budget, plus its one-over twin — and make both parity cases pass line-for-line (JS vs Rust). Distinct from HN5-035's fully-populated parity case and its Rust-only budget unit test. Proof: parity suite total grows by two and stays green; total in status file.
- HN5-128 — b10_parity: add the source pointers BOUNDARY golden fixture — a record sized exactly at its section budget, plus its one-over twin — and make both parity cases pass line-for-line (JS vs Rust). Distinct from HN5-040's fully-populated parity case and its Rust-only budget unit test. Proof: parity suite total grows by two and stays green; total in status file.
- HN5-129 — b10_parity: add the since-last-brief BOUNDARY golden fixture — a record sized exactly at its section budget, plus its one-over twin — and make both parity cases pass line-for-line (JS vs Rust). Distinct from HN5-045's fully-populated parity case and its Rust-only budget unit test. Proof: parity suite total grows by two and stays green; total in status file.
- HN5-130 — b10_parity: add the priority order BOUNDARY golden fixture — a record sized exactly at its section budget, plus its one-over twin — and make both parity cases pass line-for-line (JS vs Rust). Distinct from HN5-050's fully-populated parity case and its Rust-only budget unit test. Proof: parity suite total grows by two and stays green; total in status file.
- HN5-131 — b10_parity: add the blocked contacts BOUNDARY golden fixture — a record sized exactly at its section budget, plus its one-over twin — and make both parity cases pass line-for-line (JS vs Rust). Distinct from HN5-055's fully-populated parity case and its Rust-only budget unit test. Proof: parity suite total grows by two and stays green; total in status file.
- HN5-132 — b10_parity: add the held decisions BOUNDARY golden fixture — a record sized exactly at its section budget, plus its one-over twin — and make both parity cases pass line-for-line (JS vs Rust). Distinct from HN5-060's fully-populated parity case and its Rust-only budget unit test. Proof: parity suite total grows by two and stays green; total in status file.
- HN5-133 — b10_parity: add the onjoin template BOUNDARY golden fixture — a record sized exactly at its section budget, plus its one-over twin — and make both parity cases pass line-for-line (JS vs Rust). Distinct from HN5-065's fully-populated parity case and its Rust-only budget unit test. Proof: parity suite total grows by two and stays green; total in status file.
- HN5-134 — b10_parity: add the environment BOUNDARY golden fixture — a record sized exactly at its section budget, plus its one-over twin — and make both parity cases pass line-for-line (JS vs Rust). Distinct from HN5-070's fully-populated parity case and its Rust-only budget unit test. Proof: parity suite total grows by two and stays green; total in status file.
- HN5-135 — b10_parity: add the federation BOUNDARY golden fixture — a record sized exactly at its section budget, plus its one-over twin — and make both parity cases pass line-for-line (JS vs Rust). Distinct from HN5-075's fully-populated parity case and its Rust-only budget unit test. Proof: parity suite total grows by two and stays green; total in status file.
- HN5-136 — b10_parity: add the memory budget BOUNDARY golden fixture — a record sized exactly at its section budget, plus its one-over twin — and make both parity cases pass line-for-line (JS vs Rust). Distinct from HN5-080's fully-populated parity case and its Rust-only budget unit test. Proof: parity suite total grows by two and stays green; total in status file.
- HN5-137 — b10_parity: add the memory depth BOUNDARY golden fixture — a record sized exactly at its section budget, plus its one-over twin — and make both parity cases pass line-for-line (JS vs Rust). Distinct from HN5-085's fully-populated parity case and its Rust-only budget unit test. Proof: parity suite total grows by two and stays green; total in status file.
- HN5-138 — b10_parity: add the daily BOUNDARY golden fixture — a record sized exactly at its section budget, plus its one-over twin — and make both parity cases pass line-for-line (JS vs Rust). Distinct from HN5-090's fully-populated parity case and its Rust-only budget unit test. Proof: parity suite total grows by two and stays green; total in status file.
- HN5-139 — b10_parity: add the screenshot digest BOUNDARY golden fixture — a record sized exactly at its section budget, plus its one-over twin — and make both parity cases pass line-for-line (JS vs Rust). Distinct from HN5-095's fully-populated parity case and its Rust-only budget unit test. Proof: parity suite total grows by two and stays green; total in status file.
- HN5-140 — b10_parity: add the previous session BOUNDARY golden fixture — a record sized exactly at its section budget, plus its one-over twin — and make both parity cases pass line-for-line (JS vs Rust). Distinct from HN5-100's fully-populated parity case and its Rust-only budget unit test. Proof: parity suite total grows by two and stays green; total in status file.
- HN5-141 — b10_parity harness: a failing parity case prints a line-level diff (first differing line, expected vs actual), not just a count. Proof: deliberately broken fixture produces the diff output; screenshot/log line in status file.
- HN5-142 — b10_parity harness: golden files live in one named fixtures directory with a README stating they are generated from the JS brief, never hand-edited to match Rust. Proof: README committed; path in status file.
- HN5-143 — b10_parity: empty-brief golden fixture (all records None) passes on both sides. Proof: parity total in status file.
- HN5-144 — b10_parity: oversize-brief golden fixture (every section over budget) passes on both sides. Proof: parity total in status file.
- HN5-145 — b10_parity: unicode golden fixture passes on both sides. Proof: parity total in status file.
- HN5-146 — b10_parity: redaction golden fixture (secrets in three sections) passes and asserts absence on both sides. Proof: parity total in status file.
- HN5-147 — Parity runner script: one command runs the whole b10_parity suite and prints pass/fail totals, for Milo's gate. Proof: script committed; its output line quoted in status file.
- HN5-148 — Parity drift check: a script diffs the fillers' section-id list against the JS brief's section list and fails on mismatch. Proof: script output (match) in status file.
- HN5-149 — Record the parity baseline (total cases, all passing) in the status file as the number later sections must not reduce. Proof: baseline block present.
- HN5-150 — Milo gate request for the S02–S06 intel block, with counts, in the status file. Proof: request block present.

## Section 07 — Intel Crate Hardening — Validation, Redaction, Budgets, Errors

- HN5-151 — validate_brief_record: reject a record with a negative timestamp with the named error. Proof: validation test passes; counts in status file.
- HN5-152 — validate_brief_record: reject a record with an empty room string with the named error. Proof: validation test passes.
- HN5-153 — validate_brief_record: accept the maximal valid record (every field at its limit). Proof: validation test passes.
- HN5-154 — redact_secrets: API-key-shaped strings (long hex/base64 runs) are redacted. Proof: unit test per shape; counts in status file.
- HN5-155 — redact_secrets: 'key=value' secret pairs are redacted by key name (token, secret, password, auth). Proof: one test per key name.
- HN5-156 — redact_secrets: ordinary prose containing the word 'token' in a sentence is NOT redacted. Proof: false-positive guard test passes.
- HN5-157 — redact_secrets: redaction marker is the single ruled marker string everywhere (one constant). Proof: grep shows one definition; test asserts marker text.
- HN5-158 — trim_to_budget: text exactly at budget is returned unchanged. Proof: boundary test.
- HN5-159 — trim_to_budget: text one char over budget trims to budget with the ruled ellipsis/marker. Proof: boundary test asserts exact output.
- HN5-160 — trim_to_budget: trimming never splits a multi-byte UTF-8 char. Proof: unicode boundary test.
- HN5-161 — brief_budget: every section kind returns Some; the table is exhaustive over the kind enum. Proof: exhaustiveness test iterates all kinds.
- HN5-162 — failure_copy_for_kind: every kind has copy; unknown kind returns the named error. Proof: table test + error test.
- HN5-163 — parse_since: leap-second/overflow inputs (absurd magnitudes) error instead of wrapping. Proof: overflow test with i64-edge values.
- HN5-164 — brief_age_seconds: a future timestamp yields the ruled clamp, not a negative age. Proof: test with future ts.
- HN5-165 — cap_snapshot_window: a window of zero produces the ruled empty output, not a panic. Proof: edge test.
- HN5-166 — Error types: every public fn in brief.rs that can fail returns the crate's named error shape — sweep and fix any bare panic!/unwrap() on input paths. Proof: grep list + per-site verdict in status file.
- HN5-167 — Fuzz-lite: a table of 20 hostile inputs (empty, huge, control chars, NULs, format braces) run through the composer without panic. Proof: hostile-input test passes; input list committed.
- HN5-168 — Sections.rs hardening: unknown section id errors by name, never renders an empty section silently. Proof: test passes.
- HN5-169 — Window.rs hardening: negative window sizes are rejected at construction. Proof: test passes.
- HN5-170 — Notify/push/wake modules: each public fn gets one happy-path and one error-path test if it lacks them. Proof: per-module test counts in status file.
- HN5-171 — Forecast/dispatch/baton/alerts modules: same treatment — one happy + one error test each where missing. Proof: per-module counts in status file.
- HN5-172 — mod.rs: the b10_brief public surface is listed and every entry has at least one test touching it. Proof: coverage list in status file; zero untested public fns or named exceptions.
- HN5-173 — Warning sweep: `cargo check -p intel` warning count driven to the pre-existing baseline or below; every remaining warning listed with a reason. Proof: counts + list in status file.
- HN5-174 — Full intel suite + parity suite re-run; counts recorded as the S07 baseline. Proof: both count lines in status file.
- HN5-175 — Milo gate request for the hardening block in the status file. Proof: request block present.

## Section 08 — L6 Lobster Shell — Core Program (lobster/)

- HN5-176 — Read lobster/README.md and the existing programs (hello, identity, service-roundtrip, bus-send, bus-recv, agent-call) and write the shell's I/O contract in the status file: stdin lines in, service calls out, no direct state. Proof: contract note present, citing the roundtrip program by name.
- HN5-177 — Create lobster/metaos-shell.lobster: entry point that prints the shell banner line from the session service (real state), not a hardcoded string. Proof: run transcript in status file showing the banner matches the service response.
- HN5-178 — Shell REPL loop: read a line, dispatch, print result, loop until `exit`. Proof: transcript with three commands + exit in status file.
- HN5-179 — Dispatch table: command name -> handler mapping in one named table (no if-chain sprawl). Proof: the table is the single place a new command registers; S08–S10 commands must use it.
- HN5-180 — Unknown command: prints the ruled unknown-command line naming the typed word, exit code non-zero for that line only, shell keeps running. Proof: transcript test.
- HN5-181 — Empty line and whitespace-only line are no-ops (no output, no error). Proof: transcript test.
- HN5-182 — exit/quit: both end the shell with code 0 and the ruled closing line. Proof: transcript test for each.
- HN5-183 — Ctrl-C / EOF handling: EOF ends the shell cleanly with the same closing line; no hang. Proof: piped-input run transcript.
- HN5-184 — Command arguments: a real argument parser (split on spaces, honour double quotes) shared by all handlers. Proof: parser unit cases listed in status file (quoted string with spaces, empty quotes, unmatched quote error).
- HN5-185 — Unmatched quote returns the ruled parse-error line and runs nothing. Proof: transcript test.
- HN5-186 — History: every executed line is appended to the session service's history (Goose session service), never to a local file. Proof: history read-back via the service in transcript.
- HN5-187 — History cap: the shell asks the service for at most the ruled number of entries; older entries are the service's problem, labelled as such in a comment. Proof: transcript showing the cap honoured.
- HN5-188 — Error surface: a Goose service error prints the ruled service-error line with the service name; the shell never prints a stack trace. Proof: forced-error transcript (service stopped).
- HN5-189 — Service-down start: if the session service is down at launch, the shell prints the ruled unavailable line and exits non-zero — it does not fake a session. Proof: transcript with services stopped.
- HN5-190 — Prompt: the Lobster shell prompt string is defined in one place and is NOT the kernel console's (no) prompt; the spec note in S11 records the difference. Proof: constant + note cross-reference in status file.
- HN5-191 — `help` handler (shell-level): lists only commands actually registered in the dispatch table, generated from the table itself. Proof: transcript; adding a command in S08 changes help with no help-code edit (demonstrated).
- HN5-192 — Command exit codes: every handler returns 0/non-zero by the ruled convention and the REPL reports non-zero once, plainly. Proof: transcript with one failing command.
- HN5-193 — Long output: handler output longer than the ruled page size is paged through the console service or truncated with the ruled marker — pick the one the console service supports and record which. Proof: transcript with a long-output command.
- HN5-194 — Shell settings (prompt, page size) read from the Goose settings-store service at start; missing settings fall back to named defaults, listed in the status file. Proof: transcript with the settings service empty.
- HN5-195 — Tests harness: a lobster/ test script runs the shell against the local Goose services and asserts the transcripts above, printing pass/fail totals. Proof: script committed; totals in status file.
- HN5-196 — The shell never writes OS state itself: audit the program for any direct file/state writes and remove or route them through services. Proof: audit list in status file; zero direct writes or named exceptions.
- HN5-197 — Shell version line: `status` inside the Lobster shell reports shell name + version + session id from services (distinct from the kernel's status record). Proof: transcript line quoted in status file.
- HN5-198 — Document the shell's command-registration steps in lobster/README.md (how S08–S10 add a command). Proof: README diff committed.
- HN5-199 — Run the full lobster/ test set incl. the new shell harness; record totals as the L6 shell baseline. Proof: totals in status file.
- HN5-200 — Milo gate request for the shell-core block in the status file (Lobster lane: gate = harness totals + transcripts). Proof: request block present.

## Section 09 — Lobster Shell Commands I — Session and Self (date, whoami, echo, env, history)

- HN5-201 — `date` command: implement the handler in the Lobster shell against the Goose session/settings services — print the current date/time from the OS clock service, in the ruled format. Proof: transcript in status file showing real service data, not a fixture string.
- HN5-202 — `date` arguments: parse and validate its arguments; bad arguments print the ruled usage line and change nothing. Proof: transcript with two bad-argument cases.
- HN5-203 — `date` unset clock: with the clock service reporting an unset/invalid time, `date` prints the ruled unset-clock line and returns non-zero — a clock always answers, so date has no empty state; this is its failure display. Proof: transcript with the service returning the unset value.
- HN5-204 — `date` service-down: with its service stopped, prints the service-error line naming the service and returns non-zero. Proof: transcript with the service stopped.
- HN5-205 — `date` tests + spec: harness cases for date pass and its shell-spec entry (S11) is written in the same commit. Proof: harness totals + spec line reference in status file.
- HN5-206 — `whoami` command: implement the handler in the Lobster shell against the Goose session/settings services — print the session identity (user, session id) from the identity/session service. Proof: transcript in status file showing real service data, not a fixture string.
- HN5-207 — `whoami` arguments: parse and validate its arguments; bad arguments print the ruled usage line and change nothing. Proof: transcript with two bad-argument cases.
- HN5-208 — `whoami` empty state: with nothing to show, prints the ruled empty line for whoami. Proof: transcript against empty services.
- HN5-209 — `whoami` service-down: with its service stopped, prints the service-error line naming the service and returns non-zero. Proof: transcript with the service stopped.
- HN5-210 — `whoami` tests + spec: harness cases for whoami pass and its shell-spec entry (S11) is written in the same commit. Proof: harness totals + spec line reference in status file.
- HN5-211 — `echo` command: implement the handler in the Lobster shell core — it prints its arguments through the shared parser, with -n suppressing the newline, and calls NO service (echo is shell-local, unlike the service-backed commands). Proof: transcript in status file covering plain text, a quoted argument with spaces, and -n.
- HN5-212 — `echo` arguments: parse and validate its arguments; bad arguments print the ruled usage line and change nothing. Proof: transcript with two bad-argument cases.
- HN5-213 — `echo` flags-only case: `echo -n` with no text prints nothing at all and returns 0 — echo has no empty state; a bare `echo` prints exactly one newline. Proof: transcript asserting the exact output bytes for bare echo and for echo -n.
- HN5-214 — `echo` independence check: with every Goose service stopped, `echo` still works — proving the handler has no hidden service dependency (echo has no service-down case). Proof: transcript with services stopped and echo output correct.
- HN5-215 — `echo` tests + spec: harness cases for echo pass and its shell-spec entry (S11) is written in the same commit. Proof: harness totals + spec line reference in status file.
- HN5-216 — `env` command: implement the handler in the Lobster shell against the Goose session/settings services — list the session environment from the settings-store service. Proof: transcript in status file showing real service data, not a fixture string.
- HN5-217 — `env` arguments: parse and validate its arguments; bad arguments print the ruled usage line and change nothing. Proof: transcript with two bad-argument cases.
- HN5-218 — `env` empty state: with nothing to show, prints the ruled empty line for env. Proof: transcript against empty services.
- HN5-219 — `env` service-down: with its service stopped, prints the service-error line naming the service and returns non-zero. Proof: transcript with the service stopped.
- HN5-220 — `env` tests + spec: harness cases for env pass and its shell-spec entry (S11) is written in the same commit. Proof: harness totals + spec line reference in status file.
- HN5-221 — `history` command: implement the handler in the Lobster shell against the Goose session/settings services — print the session history from the session service, newest last, capped. Proof: transcript in status file showing real service data, not a fixture string.
- HN5-222 — `history` arguments: parse and validate its arguments; bad arguments print the ruled usage line and change nothing. Proof: transcript with two bad-argument cases.
- HN5-223 — `history` empty state: with nothing to show, prints the ruled empty line for history. Proof: transcript against empty services.
- HN5-224 — `history` service-down: with its service stopped, prints the service-error line naming the service and returns non-zero. Proof: transcript with the service stopped.
- HN5-225 — `history` tests + spec: harness cases for history pass and its shell-spec entry (S11) is written in the same commit. Proof: harness totals + spec line reference in status file.

## Section 10 — Lobster Shell Commands II — Files (ls, cat, stat, pwd, cd)

- HN5-226 — `ls` command: implement the handler in the Lobster shell against the Goose workspace-store/session services — list a directory through the workspace-store service. Proof: transcript in status file showing real service data, not a fixture string.
- HN5-227 — `ls` arguments: parse and validate its arguments; bad arguments print the ruled usage line and change nothing. Proof: transcript with two bad-argument cases.
- HN5-228 — `ls` empty state: with nothing to show, prints the ruled empty line for ls. Proof: transcript against empty services.
- HN5-229 — `ls` service-down: with its service stopped, prints the service-error line naming the service and returns non-zero. Proof: transcript with the service stopped.
- HN5-230 — `ls` tests + spec: harness cases for ls pass and its shell-spec entry (S11) is written in the same commit. Proof: harness totals + spec line reference in status file.
- HN5-231 — `cat` command: implement the handler in the Lobster shell against the Goose workspace-store/session services — print a file's contents through the workspace-store service, paged by the core rule. Proof: transcript in status file showing real service data, not a fixture string.
- HN5-232 — `cat` arguments: parse and validate its arguments; bad arguments print the ruled usage line and change nothing. Proof: transcript with two bad-argument cases.
- HN5-233 — `cat` empty state: with nothing to show, prints the ruled empty line for cat. Proof: transcript against empty services.
- HN5-234 — `cat` service-down: with its service stopped, prints the service-error line naming the service and returns non-zero. Proof: transcript with the service stopped.
- HN5-235 — `cat` tests + spec: harness cases for cat pass and its shell-spec entry (S11) is written in the same commit. Proof: harness totals + spec line reference in status file.
- HN5-236 — `stat` command: implement the handler in the Lobster shell against the Goose workspace-store/session services — print size/timestamps/type for one path from the workspace-store service. Proof: transcript in status file showing real service data, not a fixture string.
- HN5-237 — `stat` arguments: parse and validate its arguments; bad arguments print the ruled usage line and change nothing. Proof: transcript with two bad-argument cases.
- HN5-238 — `stat` empty state: with nothing to show, prints the ruled empty line for stat. Proof: transcript against empty services.
- HN5-239 — `stat` service-down: with its service stopped, prints the service-error line naming the service and returns non-zero. Proof: transcript with the service stopped.
- HN5-240 — `stat` tests + spec: harness cases for stat pass and its shell-spec entry (S11) is written in the same commit. Proof: harness totals + spec line reference in status file.
- HN5-241 — `pwd` command: implement the handler in the Lobster shell against the Goose workspace-store/session services — print the session's current directory from the session service. Proof: transcript in status file showing real service data, not a fixture string.
- HN5-242 — `pwd` arguments: parse and validate its arguments; bad arguments print the ruled usage line and change nothing. Proof: transcript with two bad-argument cases.
- HN5-243 — `pwd` stale directory: after `cd` into a directory that is then deleted, `pwd` prints the ruled stale-directory line from the session service instead of a dead path — pwd has no empty state; a session always has a current directory or a stale one. Proof: transcript of the cd, delete, pwd sequence.
- HN5-244 — `pwd` service-down: with its service stopped, prints the service-error line naming the service and returns non-zero. Proof: transcript with the service stopped.
- HN5-245 — `pwd` tests + spec: harness cases for pwd pass and its shell-spec entry (S11) is written in the same commit. Proof: harness totals + spec line reference in status file.
- HN5-246 — `cd` command: implement the handler in the Lobster shell against the Goose workspace-store/session services — change the session's current directory in the session service (shell holds no path state). Proof: transcript in status file showing real service data, not a fixture string.
- HN5-247 — `cd` arguments: parse and validate its arguments; bad arguments print the ruled usage line and change nothing. Proof: transcript with two bad-argument cases.
- HN5-248 — `cd` no-argument case: bare `cd` changes to the session's home directory as recorded in the session service — cd has no empty state; no argument means home. Proof: transcript showing pwd before, bare cd, and pwd after at the recorded home directory.
- HN5-249 — `cd` service-down: with its service stopped, prints the service-error line naming the service and returns non-zero. Proof: transcript with the service stopped.
- HN5-250 — `cd` tests + spec: harness cases for cd pass and its shell-spec entry (S11) is written in the same commit. Proof: harness totals + spec line reference in status file.

## Section 11 — Lobster Shell Commands III — Machine and Services (procs, services, logs, net, disk)

- HN5-251 — `procs` command: implement the handler in the Lobster shell against the Goose supervision/log/network/storage services — list running processes/tasks from the supervision service (the Lobster-shell sibling of kernel ps, from service data). Proof: transcript in status file showing real service data, not a fixture string.
- HN5-252 — `procs` arguments: parse and validate its arguments; bad arguments print the ruled usage line and change nothing. Proof: transcript with two bad-argument cases.
- HN5-253 — `procs` empty state: with nothing to show, prints the ruled empty line for procs. Proof: transcript against empty services.
- HN5-254 — `procs` service-down: with its service stopped, prints the service-error line naming the service and returns non-zero. Proof: transcript with the service stopped.
- HN5-255 — `procs` tests + spec: harness cases for procs pass and its shell-spec entry (S11) is written in the same commit. Proof: harness totals + spec line reference in status file.
- HN5-256 — `services` command: implement the handler in the Lobster shell against the Goose supervision/log/network/storage services — list Goose services and their states from the supervision service. Proof: transcript in status file showing real service data, not a fixture string.
- HN5-257 — `services` arguments: parse and validate its arguments; bad arguments print the ruled usage line and change nothing. Proof: transcript with two bad-argument cases.
- HN5-258 — `services` empty state: with nothing to show, prints the ruled empty line for services. Proof: transcript against empty services.
- HN5-259 — `services` service-down: with its service stopped, prints the service-error line naming the service and returns non-zero. Proof: transcript with the service stopped.
- HN5-260 — `services` tests + spec: harness cases for services pass and its shell-spec entry (S11) is written in the same commit. Proof: harness totals + spec line reference in status file.
- HN5-261 — `logs` command: implement the handler in the Lobster shell against the Goose supervision/log/network/storage services — print recent log lines from the log service, filterable by service name. Proof: transcript in status file showing real service data, not a fixture string.
- HN5-262 — `logs` arguments: parse and validate its arguments; bad arguments print the ruled usage line and change nothing. Proof: transcript with two bad-argument cases.
- HN5-263 — `logs` empty state: with nothing to show, prints the ruled empty line for logs. Proof: transcript against empty services.
- HN5-264 — `logs` service-down: with its service stopped, prints the service-error line naming the service and returns non-zero. Proof: transcript with the service stopped.
- HN5-265 — `logs` tests + spec: harness cases for logs pass and its shell-spec entry (S11) is written in the same commit. Proof: harness totals + spec line reference in status file.
- HN5-266 — `net` command: implement the handler in the Lobster shell against the Goose supervision/log/network/storage services — print network state (interfaces, addresses) from the networking service. Proof: transcript in status file showing real service data, not a fixture string.
- HN5-267 — `net` arguments: parse and validate its arguments; bad arguments print the ruled usage line and change nothing. Proof: transcript with two bad-argument cases.
- HN5-268 — `net` empty state: with nothing to show, prints the ruled empty line for net. Proof: transcript against empty services.
- HN5-269 — `net` service-down: with its service stopped, prints the service-error line naming the service and returns non-zero. Proof: transcript with the service stopped.
- HN5-270 — `net` tests + spec: harness cases for net pass and its shell-spec entry (S11) is written in the same commit. Proof: harness totals + spec line reference in status file.
- HN5-271 — `disk` command: implement the handler in the Lobster shell against the Goose supervision/log/network/storage services — print storage usage from the storage service. Proof: transcript in status file showing real service data, not a fixture string.
- HN5-272 — `disk` arguments: parse and validate its arguments; bad arguments print the ruled usage line and change nothing. Proof: transcript with two bad-argument cases.
- HN5-273 — `disk` empty state: with nothing to show, prints the ruled empty line for disk. Proof: transcript against empty services.
- HN5-274 — `disk` service-down: with its service stopped, prints the service-error line naming the service and returns non-zero. Proof: transcript with the service stopped.
- HN5-275 — `disk` tests + spec: harness cases for disk pass and its shell-spec entry (S11) is written in the same commit. Proof: harness totals + spec line reference in status file.

## Section 12 — Shell Spec and Formats (os-build/shell-spec.md, shell-formats.json)

- HN5-276 — shell-spec.md: add the Lobster shell as its own section, clearly separate from the kernel console section, stating which shell each command belongs to. Proof: spec diff committed; section quoted in status file.
- HN5-277 — shell-spec.md: record the ruled kernel help line (`commands: status help uptime mem ps`) as UNCHANGED by all L6 work, with the note that Lobster-shell commands live in the Lobster shell's own help. Proof: spec line present verbatim.
- HN5-278 — shell-spec.md: one entry per S08 command (date, whoami, echo, env, history) in the spec's format (syntax, source service, empty state, error line). Proof: five entries present.
- HN5-279 — shell-spec.md: one entry per S09 command (ls, cat, stat, pwd, cd) in the same format. Proof: five entries present.
- HN5-280 — shell-spec.md: one entry per S10 command (procs, services, logs, net, disk) in the same format. Proof: five entries present.
- HN5-281 — shell-formats.json: add the machine-readable format record for each S08 command's output. Proof: JSON validates; record count in status file.
- HN5-282 — shell-formats.json: same for each S09 command. Proof: JSON validates; count in status file.
- HN5-283 — shell-formats.json: same for each S10 command. Proof: JSON validates; count in status file.
- HN5-284 — Help discipline test: an automated check that every command in the Lobster shell's help exists in the dispatch table and vice versa. Proof: check script + passing output in status file.
- HN5-285 — Help discipline: the kernel console's help is never edited by L6 work — assert by diffing the kernel help text before/after the L6 block (must be identical, and L6 never touches kernel/src anyway). Proof: diff result (empty) recorded.
- HN5-286 — Status words: sweep shell-spec.md so every claim carries DESIGNED / WRITTEN / COMPILED / VERIFIED / NOT BUILT / BLOCKED exactly; fix any loose wording. Proof: sweep list in status file.
- HN5-287 — Spec: the Lobster shell's status words reflect harness verdicts only — a command with no passing harness case is WRITTEN, never VERIFIED. Proof: per-command status table in the spec matches harness totals.
- HN5-288 — Spec: document the shell's service-down behaviour once, in the core section, and reference it from each command entry instead of repeating it. Proof: spec diff.
- HN5-289 — Spec: document the argument-parser rules (quoting, errors) once in the core section. Proof: spec diff.
- HN5-290 — Formats: every format record names its source service; a record with no real service is marked NOT BUILT in the spec, not faked. Proof: audit list in status file.
- HN5-291 — Formats: version the formats file (bump its version field) and note the change in the spec. Proof: version diff quoted.
- HN5-292 — Cross-check shell-spec against HANA_LAYER2_TASKS.md (L6 doc) and reconcile any contradiction, naming which doc wins and why, in the status file. Proof: reconciliation note present.
- HN5-293 — Cross-check the Lobster shell command set against the face's command view names (js/command-*.js): same command, same name; differences listed with a ruling request to Pax where they conflict. Proof: comparison table in status file.
- HN5-294 — Write the L6 shell user summary (one page, plain language: what the shell is, that it runs on Lobster over Goose services, that it is not the kernel console) into the spec as an appendix. Proof: appendix present.
- HN5-295 — Spec proofread pass: no line in shell-spec.md calls the web face an OS surface; violations fixed here, the wider copy pass is S20. Proof: grep list + verdict in status file.
- HN5-296 — Formats JSON: add a schema check to the harness so a malformed formats file fails the run. Proof: harness output with a deliberately broken copy (kept out of the tree) described in status file.
- HN5-297 — Record final S11 counts: commands specified, formats recorded, status table — in the status file. Proof: counts block present.
- HN5-298 — Milo gate request for the spec/formats block (docs gate: counts + cross-checks). Proof: request block present.
- HN5-299 — Hold: any command whose service turns out not to exist gets its spec entry marked NOT BUILT with the missing service named — list them all in the status file for Pax/Buffy's service lane. Proof: list present (may be empty, stated).
- HN5-300 — Close S11 in the status file with the per-command status table copied from the spec. Proof: table present.

## Section 13 — Kernel-Face Assets I — Ribbon Frames as Data (for Rowan's kernel drawing)

- HN5-301 — Read js/logo-background.js (loopPoint/buildSurface math + GLYPHS ramp) and kernel/src/logo_frames.rs (217 lines, 46x17, 12 frames) and write the asset contract in the status file: frame size, frame count, ramp, per-product colours. Proof: contract note citing both files.
- HN5-302 — Write the generator (tools/ribbon-frames/ or lobster/ — pick one, record which) that emits ribbon frames as a data file (JSON or RON) from the same math, not from screenshots. Proof: generator committed; one run's output committed beside it.
- HN5-303 — Generator determinism: two runs produce byte-identical data. Proof: hash of both outputs in status file (equal).
- HN5-304 — Frame set: export all 12 frames at 46x17 as data records with frame indices. Proof: data file contains 12 frames; count check in status file.
- HN5-305 — Validate the data frames against kernel/src/logo_frames.rs frames cell-for-cell; every mismatch listed (expected: zero, or each explained). Proof: validation script + result in status file.
- HN5-306 — Per-product colour table as data: one entry per product in js/products.js with its ribbon colour, exported from products.js values (not retyped). Proof: table file + a check that each value matches products.js.
- HN5-307 — Speed/pause timing data: the loop's frame interval and pause behaviour exported as named data fields. Proof: data fields present; source lines cited.
- HN5-308 — Larger frame set: generate a 92x34 (2x) frame set from the same math for the graphical boot screen, as data. Proof: 12 frames at the new size; size check in status file.
- HN5-309 — Character-cell mapping: document how a frame cell maps to a pixel block for the framebuffer (block size table for both frame sizes). Proof: mapping note + table in the data package README.
- HN5-310 — Package README (in the asset directory): what each file is, its generator, and the rule that data is regenerated, never hand-edited. Proof: README committed.
- HN5-311 — Manifest: a manifest file lists every asset file with its SHA-256. Proof: manifest committed; a verify script re-hashes and passes.
- HN5-312 — Regeneration test: delete-and-regenerate in a scratch copy reproduces the manifest hashes exactly. Proof: test log in status file.
- HN5-313 — Colour-blind check data: for each product colour, a luminance value computed and recorded (the boot screen must not rely on colour alone). Proof: luminance column in the colour table.
- HN5-314 — The ribbon's centre-out drawing order (cell order list) exported as data for the kernel's draw routine. Proof: order list length equals cell count per frame; check in status file.
- HN5-315 — Alpha/empty cells: the ramp's empty character is represented as a named transparent value in the data, not a space hack. Proof: data sample + note in status file.
- HN5-316 — Frame timing for the attract loop vs the boot loop recorded as two named profiles in data. Proof: profiles present.
- HN5-317 — Hana does NOT draw anything in this section: assert the deliverables are data + generator + checks only (drawing is Rowan's KF lane). Proof: deliverable list in status file contains no rendering code.
- HN5-318 — Cross-check the 46x17 frames against face/logo-background.js's own frame data if it exists; differences listed. Proof: comparison result in status file.
- HN5-319 — Asset licence/source note: the data derives from the repo's own JS math; state that in the package README. Proof: note present.
- HN5-320 — Version the asset package (version field in manifest). Proof: version present.
- HN5-321 — Final counts for S12 in the status file: frames, sizes, files, hashes verified. Proof: counts block.
- HN5-322 — Milo gate request for the asset package (data gate: manifest + regeneration proof). Proof: request block present.
- HN5-323 — Hand-off note for Rowan in the status file: exact file paths + formats his framebuffer code should consume. Proof: note present.
- HN5-324 — If the JS math and logo_frames.rs disagree anywhere: file a numbered discrepancy list for Pax instead of silently picking one. Proof: list present (may be 'none', stated).
- HN5-325 — Close S12 with status words per deliverable in the status file. Proof: status lines present.

## Section 14 — Kernel-Face Assets II — Font and Glyph Data (Terminus table)

- HN5-326 — Read kernel/FONT_TABLE_LICENSE.md and the framebuffer's glyph expectations (draw_glyph in kernel/src/framebuffer.rs) and write the glyph contract: cell size, bits per row, index = codepoint offset. Proof: contract note in status file citing both.
- HN5-327 — Export the printable ASCII range (0x20–0x7E) as a glyph data file from the repo's existing font table source — no redrawn letters. Proof: 95 glyphs in data; count check recorded.
- HN5-328 — Glyph data format: one record per glyph (codepoint, width, row bitmaps as hex) in a single documented format. Proof: format note + sample records in status file.
- HN5-329 — Coverage test: every codepoint in 0x20–0x7E has a glyph; missing ones listed (expected zero). Proof: test output in status file.
- HN5-330 — Fallback glyph: the replacement glyph (for unknown codepoints) is a named record in the data, not an empty cell. Proof: record present; test asserts fallback is non-empty.
- HN5-331 — Box-drawing subset: export the box/block characters the dashboard frames need (list them by codepoint in the status file first, then export exactly those). Proof: list + count in data.
- HN5-332 — Arrows and bullets subset: export the small set the shell/apps use (arrows, bullet, check, cross — named by codepoint). Proof: list + records present.
- HN5-333 — Width table: fixed-width assertion — every glyph record declares the same cell width, or variable widths are recorded per glyph. Proof: width check output.
- HN5-334 — Generator: a script regenerates the glyph data from its source; hand edits are overwritten, stated in the package README. Proof: regeneration reproduces manifest hashes (log in status file).
- HN5-335 — Manifest + hashes for the font package, same pattern as S12. Proof: manifest committed; verify passes.
- HN5-336 — Kerning/spacing data: line height and letter spacing values as named data fields for the kernel text renderer. Proof: fields present with source cited (framebuffer console constants or spec).
- HN5-337 — The console's existing characters: diff the glyph set against the characters actually used in kernel boot/status text (grep kernel strings); every used char must have a glyph. Proof: used-char list + coverage verdict.
- HN5-338 — Numbers tabular check: digit glyphs 0–9 verified present and same width (status readouts align). Proof: check output.
- HN5-339 — Punctuation completeness for shell use: quotes, backslash, pipe, tilde, backtick, braces — each asserted present. Proof: assertion list in status file.
- HN5-340 — A test rendering (as data): the string 'META OS' composed from glyph records into a cell grid, checked against expected width. Proof: composition test passes; grid quoted in status file.
- HN5-341 — Licence carry: the font package directory contains the licence/notice the FONT_TABLE_LICENSE requires, copied not paraphrased. Proof: file present; diff against the requirement noted.
- HN5-342 — Package README for fonts: contents, generator, contract, licence pointer. Proof: README committed.
- HN5-343 — Version field in the font manifest. Proof: present.
- HN5-344 — Hand-off note for Rowan: paths + format his pixel console should consume, in the status file. Proof: note present.
- HN5-345 — Discrepancy list if the framebuffer's expected glyph format differs from the exported format — for Pax, numbered, no silent adaptation. Proof: list present (may be 'none').
- HN5-346 — Final counts S13: glyphs by range, files, hashes. Proof: counts block in status file.
- HN5-347 — Milo gate request for the font package. Proof: request block present.
- HN5-348 — Status words per font deliverable in the status file. Proof: lines present.
- HN5-349 — Assert no rendering code was written in this section (data only). Proof: deliverable list check.
- HN5-350 — Close S13: one-line summary in the status file of what the kernel can now draw text-wise once Rowan wires it. Proof: line present, labelled as Rowan-side wiring still owed.

## Section 15 — Kernel-Face Assets III — Icon, Cursor, and Palette Data

- HN5-351 — Icon data 'terminal': a 16x16 bitmap record (rows as hex) drawn to the system's distinct identity, stored in the icon data file under its product/app id. Proof: record present; the package's render-check (data -> cell grid) output for 'terminal' quoted in status file.
- HN5-352 — Icon data 'files': a 16x16 bitmap record (rows as hex) drawn to the system's distinct identity, stored in the icon data file under its product/app id. Proof: record present; the package's render-check (data -> cell grid) output for 'files' quoted in status file.
- HN5-353 — Icon data 'settings': a 16x16 bitmap record (rows as hex) drawn to the system's distinct identity, stored in the icon data file under its product/app id. Proof: record present; the package's render-check (data -> cell grid) output for 'settings' quoted in status file.
- HN5-354 — Icon data 'dashboard': a 16x16 bitmap record (rows as hex) drawn to the system's distinct identity, stored in the icon data file under its product/app id. Proof: record present; the package's render-check (data -> cell grid) output for 'dashboard' quoted in status file.
- HN5-355 — Icon data 'trash': a 16x16 bitmap record (rows as hex) drawn to the system's distinct identity, stored in the icon data file under its product/app id. Proof: record present; the package's render-check (data -> cell grid) output for 'trash' quoted in status file.
- HN5-356 — Icon data 'vigiles': a 16x16 bitmap record (rows as hex) drawn to the system's distinct identity, stored in the icon data file under its product/app id. Proof: record present; the package's render-check (data -> cell grid) output for 'vigiles' quoted in status file.
- HN5-357 — Icon data 'ignis': a 16x16 bitmap record (rows as hex) drawn to the system's distinct identity, stored in the icon data file under its product/app id. Proof: record present; the package's render-check (data -> cell grid) output for 'ignis' quoted in status file.
- HN5-358 — Icon data 'medicus': a 16x16 bitmap record (rows as hex) drawn to the system's distinct identity, stored in the icon data file under its product/app id. Proof: record present; the package's render-check (data -> cell grid) output for 'medicus' quoted in status file.
- HN5-359 — Icon data 'science-lab': a 16x16 bitmap record (rows as hex) drawn to the system's distinct identity, stored in the icon data file under its product/app id. Proof: record present; the package's render-check (data -> cell grid) output for 'science-lab' quoted in status file.
- HN5-360 — Icon data 'officina': a 16x16 bitmap record (rows as hex) drawn to the system's distinct identity, stored in the icon data file under its product/app id. Proof: record present; the package's render-check (data -> cell grid) output for 'officina' quoted in status file.
- HN5-361 — Icon data 'musica': a 16x16 bitmap record (rows as hex) drawn to the system's distinct identity, stored in the icon data file under its product/app id. Proof: record present; the package's render-check (data -> cell grid) output for 'musica' quoted in status file.
- HN5-362 — Icon data 'aegis': a 16x16 bitmap record (rows as hex) drawn to the system's distinct identity, stored in the icon data file under its product/app id. Proof: record present; the package's render-check (data -> cell grid) output for 'aegis' quoted in status file.
- HN5-363 — Icon data 'nervus': a 16x16 bitmap record (rows as hex) drawn to the system's distinct identity, stored in the icon data file under its product/app id. Proof: record present; the package's render-check (data -> cell grid) output for 'nervus' quoted in status file.
- HN5-364 — Icon data 'hands-free': a 16x16 bitmap record (rows as hex) drawn to the system's distinct identity, stored in the icon data file under its product/app id. Proof: record present; the package's render-check (data -> cell grid) output for 'hands-free' quoted in status file.
- HN5-365 — Icon data 'board': a 16x16 bitmap record (rows as hex) drawn to the system's distinct identity, stored in the icon data file under its product/app id. Proof: record present; the package's render-check (data -> cell grid) output for 'board' quoted in status file.
- HN5-366 — Icon data 'calendar': a 16x16 bitmap record (rows as hex) drawn to the system's distinct identity, stored in the icon data file under its product/app id. Proof: record present; the package's render-check (data -> cell grid) output for 'calendar' quoted in status file.
- HN5-367 — Icon data 'calculator': a 16x16 bitmap record (rows as hex) drawn to the system's distinct identity, stored in the icon data file under its product/app id. Proof: record present; the package's render-check (data -> cell grid) output for 'calculator' quoted in status file.
- HN5-368 — Icon data 'notes': a 16x16 bitmap record (rows as hex) drawn to the system's distinct identity, stored in the icon data file under its product/app id. Proof: record present; the package's render-check (data -> cell grid) output for 'notes' quoted in status file.
- HN5-369 — Icon data 'code-editor': a 16x16 bitmap record (rows as hex) drawn to the system's distinct identity, stored in the icon data file under its product/app id. Proof: record present; the package's render-check (data -> cell grid) output for 'code-editor' quoted in status file.
- HN5-370 — Icon data 'browser': a 16x16 bitmap record (rows as hex) drawn to the system's distinct identity, stored in the icon data file under its product/app id. Proof: record present; the package's render-check (data -> cell grid) output for 'browser' quoted in status file.
- HN5-371 — Cursor sprites as data: arrow, text-I-beam, and wait cursors as bitmap records with hotspots. Proof: three records + hotspot fields present.
- HN5-372 — Palette data: the shared UI palette (per-system accent colours from products.js + neutral ramp) as one data file, values sourced not retyped. Proof: check against products.js passes.
- HN5-373 — Icon manifest + SHA-256 hashes, same pattern as S12/S13. Proof: manifest committed; verify passes.
- HN5-374 — Icon regeneration/consistency check: every icon id in the data exists as an app/product id in products.js or the face app list; orphans listed. Proof: check output in status file.
- HN5-375 — Close S14 with counts (icons, cursors, palette entries) and status words in the status file. Proof: counts block present.

## Section 16 — Lobster App — Imperium Console (Vigiles, Ignis, Medicus)

- HN5-376 — Imperium console program (lobster/imperium-console.lobster): entry that lists the three divisions from js/products.js data (vigiles, ignis, medicus) — read, not hardcoded. Proof: transcript listing exactly the three ids.
- HN5-377 — Division view: selecting a division shows its categories exactly as products.js defines them (the single source of truth). Proof: transcript diffed against products.js category lists; result in status file.
- HN5-378 — Incident list view: incidents from the queue/records service render as one line each (time, division, category, assessment). Proof: transcript against the local service with recorded incidents.
- HN5-379 — Incident detail view: one incident renders observations with regions, the assessment, and judge_mode (model|deterministic) exactly as recorded. Proof: transcript for one recorded incident, fields checked against its JSON record.
- HN5-380 — Review queue view: incidents awaiting review list separately from confirmed ones. Proof: transcript with one staged incident in each state.
- HN5-381 — Dispatch receipt view: a dispatched incident shows its receipt id and the SIMULATED endpoint label — the word SIMULATED is in the rendered line, always. Proof: transcript line quoted in status file.
- HN5-382 — No-real-dispatch guard: the console has no code path that calls a non-loopback endpoint; audit the program and record the verdict. Proof: audit note (endpoints listed, all loopback/simulated).
- HN5-383 — Livecam records view: the committed livecam reading (Bay Pkwy @ 78 St) renders as a record with its camera name and timestamp. Proof: transcript checked against server/queue/livecam_records/live-reading.json.
- HN5-384 — Camera list view: cameras from the records service list with online state as recorded (no live fetching claimed). Proof: transcript; any staleness labelled in the view itself.
- HN5-385 — Empty states: each view (incidents, queue, cameras) renders its ruled empty line when its data is empty. Proof: three transcripts against empty data.
- HN5-386 — Service-down: with the records service stopped, every view prints the service-error line, none fakes data. Proof: transcript set.
- HN5-387 — MedicUS boundary: the medicus views render scene categories only — a copy check asserts no diagnosis/cause/severity/treatment words appear in the program's strings. Proof: word-list check output in status file.
- HN5-388 — Face/identity boundary: incident views show 'ID: UNIDENTIFIED' where the records do; the console never renders a name for a person. Proof: string audit in status file.
- HN5-389 — Yellow/red alert tier: an incident's OS alert tier renders with the ruled small-note vs full-alarm distinction (text labels, not colour alone). The tier is the OS alert tier only — for medicus incidents it is never a medical severity, and no severity wording appears in medicus strings. Proof: transcript with one incident of each tier, plus the HN5-387 medicus string check re-run over the tier labels.
- HN5-390 — Console tests harness: scripted runs of the views above print pass/fail totals. Proof: harness committed; totals in status file.
- HN5-391 — Data contract note: which service/record file feeds each view, written in the status file for Buffy's service lane. Proof: note present.
- HN5-392 — Categories guard: a test fails if products.js categories and the console's rendered categories drift. Proof: test in harness; run output recorded.
- HN5-393 — Prompt-builder sync note: the console displays categories only; any category change is S19's job (products.js + Swift + both builders together) — record that dependency in the status file. Proof: note present.
- HN5-394 — Spec entry: the console gets an L6 spec entry in shell-spec.md's apps area (or HANA_LAYER2_TASKS.md if spec says apps live there — record which). Proof: entry committed.
- HN5-395 — Status words per view in the status file (VERIFIED only with harness proof). Proof: table present.
- HN5-396 — Final counts S16: views, harness cases, totals. Proof: counts block.
- HN5-397 — Milo gate request for the Imperium console block. Proof: request block present.
- HN5-398 — Gap list: any view blocked on a missing service/record named for Pax (no fake data substituted). Proof: list present (may be 'none').
- HN5-399 — Close S16: one-line honest summary of what the console can do today. Proof: line in status file.
- HN5-400 — README: lobster/README.md gains the imperium-console entry with its run command. Proof: README diff.

## Section 17 — Lobster App — Science Lab and Hortus Views

- HN5-401 — Science Lab program (lobster/science-lab.lobster): entry listing the lab's modules from the science-lab status data (literature, reasoning, compute, cycle, verify, repository) as recorded, not invented. Proof: transcript checked against os/worlds/science-lab/SCIENCE_LAB_STATUS.md.
- HN5-402 — Cycle view: the dress-rehearsal cycle renders (Delaney held-out rows 11–30, RMSE 0.818, gate L2) exactly as the status file records. Proof: transcript diffed against the status file values.
- HN5-403 — Evidence ladder view: levels 0–6 render with automated promotion capped at level 3 labelled on screen; levels 4–6 marked human-gated. Proof: transcript; cap label quoted.
- HN5-404 — Literature shelf view: the lab's literature records list (title, source) from the repository data. Proof: transcript against repository records.
- HN5-405 — Repository view: stored run records list with their ladder levels. Proof: transcript.
- HN5-406 — Verify view: a run's verification result renders (agree/disagree, RMSE where present). Proof: transcript for the rehearsal run.
- HN5-407 — Failure-drill view: the recorded failure drill renders with fake_success=false shown as recorded. Proof: transcript line quoted.
- HN5-408 — Hortus view: breeding generations list from Hortus records (generation, count) as data. Proof: transcript against Hortus test/record data.
- HN5-409 — Hortus detail: one generation's lineage renders (parents -> offspring) from records. Proof: transcript.
- HN5-410 — Gateway view: the MCP gateway allowlist renders from the lab's gateway config (Del's own servers only) with remote adapters marked UNIMPLEMENTED on screen. Proof: transcript; UNIMPLEMENTED label quoted.
- HN5-411 — Spend view: model spend renders as recorded (0 for the rehearsal) and 'metering UNIMPLEMENTED' where the lab says so — no invented numbers. Proof: transcript.
- HN5-412 — Empty states for cycle/shelf/repository views. Proof: three transcripts.
- HN5-413 — Service-down behaviour for all Science views. Proof: transcript set.
- HN5-414 — Claim-audit view: the lab's claim audit (19 checked / 19 backed) renders as recorded. Proof: transcript diffed against status data.
- HN5-415 — Step-8 guard: the program contains no step-8 content; a string check asserts the UNIMPLEMENTED marker is what renders for step 8. Proof: check output in status file.
- HN5-416 — Harness: scripted runs of the Science views print totals. Proof: harness cases + totals in status file.
- HN5-417 — Data contract note per view (source file/service) in the status file. Proof: note present.
- HN5-418 — Spec entry for the Science Lab app in the L6 docs. Proof: entry committed.
- HN5-419 — Status words per view in the status file. Proof: table present.
- HN5-420 — Gap list: views blocked on unstarted real discovery cycles are marked NOT BUILT with that reason — listed, not faked. Proof: list in status file.
- HN5-421 — Final counts S17. Proof: counts block in status file.
- HN5-422 — Milo gate request for the Science block. Proof: request block present.
- HN5-423 — README: lobster/README.md gains the science-lab entry + run command. Proof: diff.
- HN5-424 — Close S17 honest summary line in the status file. Proof: line present.
- HN5-425 — Cross-check: no Science view claims a discovery the lab has not recorded; audit strings listed. Proof: audit note.

## Section 18 — Lobster Apps — Officina and Musica (Dark Studio as Data + Logic)

- HN5-426 — Officina program (lobster/officina.lobster): entry showing the workshop's loop state from Officina records (faber loop state as recorded). Proof: transcript checked against Officina records on main.
- HN5-427 — Officina brief view: a verbal-description brief renders as the starting record (Officina starts from words, per doctrine). Proof: transcript with one recorded brief.
- HN5-428 — Officina iteration view: design iterations list with the bounds in force (FIN_HEIGHT_MM 80, BASE_THICKNESS_MM 12) shown as data read from the code's constants, not retyped. Proof: transcript + source citation in status file.
- HN5-429 — Officina gate view: the 2a gate result (PASS 14/14) renders as recorded; 2b/2c/2d render as NOT BUILT. Proof: transcript lines quoted.
- HN5-430 — Officina build record view: one recorded build renders (design, outcome). Proof: transcript.
- HN5-431 — Musica program (lobster/musica.lobster): entry renders the dark-studio home state from Musica data. Proof: transcript.
- HN5-432 — Musica dark-studio palette as DATA: the studio's colours/contrast values in one data file the program reads (no values buried in logic). Proof: data file + program reads it (grep) in status file.
- HN5-433 — Musica 3D-notes scene as DATA: note positions/geometry for the studio face stored as a data file (positions, sizes, colours) the program loads — data and logic only, no web page. Proof: data file + load transcript.
- HN5-434 — Musica track list logic: tracks from Musica records list with durations as recorded. Proof: transcript.
- HN5-435 — Musica playback state logic: play/pause/skip state machine as program logic with transitions tested headlessly. Proof: transition test table in status file.
- HN5-436 — Musica keeper view: the overnight keeper's state (last run, kept items) renders as recorded. Proof: transcript.
- HN5-437 — Musica dependency honesty: where pretty_midi is missing, the program prints the named missing-dependency line instead of failing silently. Proof: transcript in an environment without pretty_midi, or the code path cited + unit test.
- HN5-438 — Officina empty states (no briefs, no builds). Proof: two transcripts.
- HN5-439 — Musica empty states (no tracks, no keeper run). Proof: two transcripts.
- HN5-440 — Service-down behaviour for both programs. Proof: transcript set.
- HN5-441 — Harness: scripted runs for both programs print totals. Proof: totals in status file.
- HN5-442 — Data contract notes for both programs in the status file. Proof: notes present.
- HN5-443 — Spec entries for both apps in the L6 docs. Proof: entries committed.
- HN5-444 — Status words per view in the status file. Proof: table present.
- HN5-445 — Gap list: Officina 2b/2c/2d-dependent views and any Musica view needing unbuilt pieces are NOT BUILT with reasons. Proof: list present.
- HN5-446 — Final counts S18 (both programs). Proof: counts block.
- HN5-447 — Milo gate request for the Officina+Musica block. Proof: request block present.
- HN5-448 — README entries for both programs in lobster/README.md. Proof: diff.
- HN5-449 — Close S18 honest summary lines (one per program) in the status file. Proof: lines present.
- HN5-450 — Palette/scene data manifest: hashes for the Musica data files, S12-style. Proof: manifest committed; verify passes.

## Section 19 — Lobster Apps — Aegis and Nervus (Contracts Honest, Gaps Named)

- HN5-451 — Aegis program (lobster/aegis.lobster): entry renders Aegis's scope line (Del's own ground only) from the Aegis spec data. Proof: transcript checked against os-build/AEGIS_SPEC.md.
- HN5-452 — Aegis findings view: findings render as records with severity labels (small = quiet note, big = alarm) from aegis/ data. Proof: transcript against aegis/ findings data on main.
- HN5-453 — Aegis counts-only rule: a string audit asserts the program renders secret-scan COUNTS and never a secret value. Proof: audit output in status file.
- HN5-454 — Aegis sweep state view: renders 'no real sweep has run yet' until Buffy's R12 sweep lands a record — the state text reads from the record's presence, not a constant. Proof: transcript now + the code path cited.
- HN5-455 — Aegis watch-targets view: the reviewed target list renders from aegis/watch-targets data. Proof: transcript diffed against the data file.
- HN5-456 — Aegis OSV/KEV view: vulnerability counts render from Aegis records when present; absent records render the empty line. Proof: both transcripts.
- HN5-457 — Nervus program (lobster/nervus.lobster): entry renders the TWO DOORS (face + agent tools) as the program's two modes, from the Nervus spec. Proof: transcript checked against os-build/NEURON_SURGERY_SPEC.md.
- HN5-458 — Nervus ledger view: the provenance ledger renders its recorded claims count as recorded in the spec data (285 claims audited) — labelled as spec-recorded, not live. Proof: transcript + label quoted.
- HN5-459 — Nervus layer-curve view: the audited layer values (L4 4.6 / L8 19.5 / L16 12.8 / L24 10.2) render from a data file sourced from the spec, with the hump at L8 visible in the data order. Proof: data file + transcript.
- HN5-460 — Nervus dose-window view: the dose window (inert <~3, persona at 5, collapse 8–12) renders as data with its source cited. Proof: transcript + citation.
- HN5-461 — Nervus tool contracts: sweep/steer/ablate/evaluate-delta/map-layers render as contract screens (inputs, outputs) with the state 'no model run has been executed through this program'. Proof: five transcripts; state line quoted.
- HN5-462 — Nervus no-fake guard: the program contains no path that claims a model was modified; string audit recorded. Proof: audit output in status file.
- HN5-463 — Nervus face-feed GAP RECORD: since no Hana-surface feed contract exists, write the gap record (what the feed must provide: fields, cadence, source) into the status file and the program renders 'feed contract: NOT BUILT' from it. Proof: gap record + transcript.
- HN5-464 — Aegis empty states (no findings, no sweeps). Proof: transcripts.
- HN5-465 — Nervus empty states (no ledger entries beyond spec data). Proof: transcript.
- HN5-466 — Service-down behaviour for both programs. Proof: transcript set.
- HN5-467 — Harness for both programs with totals. Proof: totals in status file.
- HN5-468 — Data contract notes for both programs. Proof: notes present.
- HN5-469 — Spec entries for both apps in the L6 docs, each carrying its honest state (Aegis: pre-first-sweep; Nervus: contracts only). Proof: entries committed.
- HN5-470 — Status words per view in the status file. Proof: table present.
- HN5-471 — Gap list consolidated for Pax: Aegis first-sweep dependency (Buffy R12), Nervus feed contract, Nervus real-run machine dependency. Proof: list present.
- HN5-472 — Final counts S19. Proof: counts block.
- HN5-473 — Milo gate request for the Aegis+Nervus block. Proof: request block present.
- HN5-474 — README entries for both programs. Proof: diff.
- HN5-475 — Close S19 honest summary lines (one per program) in the status file. Proof: lines present.

## Section 20 — Swift Mirror Parity and the Honest-Labelling Pass

- HN5-476 — Parity inventory: list every product in js/products.js (vigiles, ignis, medicus, science-lab, musica, officina + any added since) against native/Sources/MetaTrio/Models/ProductConfig.swift; the diff table goes in the status file. Proof: table present; every product accounted for.
- HN5-477 — Vigiles mirror: categories, name, and colour in ProductConfig.swift match products.js field-for-field. Proof: field diff output (empty) in status file, or the fix commit + re-diff.
- HN5-478 — Ignis mirror: same field-for-field check and fix. Proof: diff output in status file.
- HN5-479 — Medicus mirror: same check and fix, including the scene-only category set. Proof: diff output in status file.
- HN5-480 — Science-lab mirror: same check and fix. Proof: diff output in status file.
- HN5-481 — Musica mirror: same check and fix. Proof: diff output in status file.
- HN5-482 — Officina mirror: same check and fix. Proof: diff output in status file.
- HN5-483 — Retired-product check: any product retired by ruling (Custos) is absent-or-marked-retired in BOTH products.js and the Swift mirror, identically. Proof: grep results for both files in status file.
- HN5-484 — New-system mirrors: Aegis and Nervus entries exist in the Swift mirror iff they exist in products.js, with identical fields; if products.js lacks them, the gap is recorded for Pax instead of inventing entries. Proof: verdict per system in status file.
- HN5-485 — Category-change drill: change nothing, but write the ruled procedure (products.js AND Swift mirror AND both prompt builders, one commit set) into the status file as the standing checklist. Proof: checklist present.
- HN5-486 — Prompt builder 1 (server/queue prompt builder): assert its category strings come from the shared source or match products.js exactly; drift listed. Proof: comparison output in status file.
- HN5-487 — Prompt builder 2 (JS-side prompt builder): same assertion and drift list. Proof: comparison output in status file.
- HN5-488 — Contract checker: the existing checker (native ContractValidator / contract tests) gains a products-parity case that fails on JS/Swift drift. Proof: test added; a deliberately drifted copy fails it (log in status file, copy kept out of the tree).
- HN5-489 — Assessment-rule parity: the assessment rule text in both prompt builders matches word-for-word. Proof: diff output (empty) or fix + re-diff in status file.
- HN5-490 — Region/box field parity: both builders emit the region field identically. Proof: comparison output in status file.
- HN5-491 — Honest labelling — face copy: sweep face/ (index.html, face.js strings) for any line calling the face the OS or implying the kernel boots it; each hit gets corrected wording or a Pax ruling request. Proof: hit list + outcomes in status file.
- HN5-492 — Honest labelling — app strings: sweep the Lobster programs written in S07–S19 for claims their gates have not earned (VERIFIED language, fake states); fix wording to match status words. Proof: sweep list in status file.
- HN5-493 — Honest labelling — shell/spec copy: sweep shell-spec.md and HANA L6 docs for web-as-OS wording; fix in place. Proof: grep list + diffs.
- HN5-494 — Honest labelling — product copy: sweep js/products.js descriptions for claims beyond recorded proof (e.g. any 'live' wording where only records exist); flag each for Pax with proposed honest wording — products.js text changes only with the S19 sync rule applied. Proof: flag list in status file.
- HN5-495 — Honest labelling — status file itself: every status word in HANA_500_STATUS.md re-checked against its proof link; downgrade any that overclaim. Proof: re-check list in status file.
- HN5-496 — Final full re-run: intel suite + parity suite + lobster harness totals all recorded together. Proof: three count lines in status file.
- HN5-497 — Final gate pack for Pax: branch tip, per-section status words, all counts, all gap lists, in one status-file section. Proof: pack present.
- HN5-498 — Milo final gate-1 request for the whole 500 block in the status file. Proof: request block present.
- HN5-499 — Claim lines for Pax's claim audit (due 20:12): every L6/B10 claim Hana makes, each with its proof pointer, as a list. Proof: list present.
- HN5-500 — Close the 500: status file's final line states the honest overall state in one sentence (what is VERIFIED, what is WRITTEN, what is NOT BUILT). Proof: line present.

# BOND — 100 CODE TASKS STATUS

Branch `bond/code-wave`, off main `32457b6b`. Test rule: one light command
per check.

## Section 1 — Agent runtime (CB-001..010)

| Task | State | Evidence |
|---|---|---|
| CB-001 ledger rejects missing field | DONE | `agents/runtime.mjs` validation; test passes |
| CB-002 torn last line skipped | DONE | existing reader; test passes |
| CB-003 torn/vanished job no-op | DONE | unreadable job logged as `job-unreadable`; test passes |
| CB-004 claim persistence | DONE | `watchman.mjs` writes `.claimed.json`; reload returns the same ids; test passes |
| CB-005 finished handoff refused | DONE | `agents/baton.mjs`; test passes |
| CB-006 three-link chain | DONE | `handoffChain`; test passes |
| CB-007 registry validator | DONE | `validateEntry` + `runtime.mjs validate`; tests pass |
| CB-008 no shell join | DONE | `resolveCommand`; test passes |
| CB-009 budget receipt on kill | DONE | test with real fake child passes |
| CB-010 gym failure ledger | DONE | `gym-fail` record with task id; test passes |

Section 1 check: `node --test tests/agents-code100.test.mjs` → **10 pass, 0 fail**.

## Section 2 — Queue Python seams (CB-011..020)

| Task | State | Evidence |
|---|---|---|
| CB-011 v2 assessment byte round-trip | DONE | local store write/read is byte-identical; test passes |
| CB-012 duplicate incident refused | DONE | `CrewRecords.create_incident`; original untouched; test passes |
| CB-013 empty judge prompt | DONE | `build_judge_prompt` with `{}` readings; test passes |
| CB-014 prose around verdict | DONE | prose and fenced JSON tolerated; garbage raises `ValueError`; tests pass |
| CB-015 reserve floor | DONE | `Patrol._budget` refuses at/under reserve; pause event receipt tested |
| CB-016 division isolation | DONE | separate `TRIO_JOB_NS` namespaces cannot see each other; test passes |
| CB-017 SAM shape parser | DONE | box-only returns no mask; mask-only and empty raise; tests pass |
| CB-018 model receipt validator | DONE | `models.validate_receipt` / `validate_receipts` name the missing model id and line; tests pass |
| CB-019 all-offline area pick | DONE | `pick` drops offline cameras; returns `[]`; livecams test passes |
| CB-020 dispatch guard sweep | DONE | eight non-loopback shapes refused; three loopback shapes allowed; test passes |

Section 2 checks: `python3 tests/queue-python/test_code100_section2.py`
-> **17 pass, 0 fail**; `test_livecams.py` -> **13 pass**;
`test_judge.py` -> **11 pass**. Total **41 pass**.

## Section 3 — Science Lab Python (CB-021..030)

| Task | State | Evidence |
|---|---|---|
| CB-021 each promotion rung names its requirement | DONE | `ladder.next_required(0..3)`; tests pass |
| CB-022 automated promotion above 3 refused | DONE | `ladder.promote` raises `NotImplementedError`; tests pass |
| CB-023 no gate record means no advance | DONE | `cycle.transition` to wetlab refuses; cycle unmutated; test passes |
| CB-024 middle ledger tamper | DONE | verification fails at `line 2: entry_hash mismatch`; test passes |
| CB-025 result before prereg refused | DONE | `reasoning.preregister` refuses late registration; test passes |
| CB-026 crash record | DONE | `output_hash` null, exit code 7, logs carry the crash; test passes |
| CB-027 blind re-run inputs | DONE | archived payload is exactly input_hash/random_seed/parameters; test passes |
| CB-028 query by level | DONE | level 1 query never returns a level 2 claim; test passes |
| CB-029 gateway refusal recorded | DONE | off-allowlist call raises and logs `refused-allowlist`; test passes |
| CB-030 select before results | DONE | `breeding.select_survivor` refuses without results; test passes |

Section 3 check: `python3 tests/science-lab/test_code100_section3.py`
-> **12 pass, 0 fail**.

## Section 4 — Rust crates (CB-031..040)

| Task | State | Evidence |
|---|---|---|
| CB-031 spend exactly the cap | DONE | `spend` allows exactly the cap, refuses one unit over; 3 tests pass |
| CB-032 reused job id after completion | DONE | `post` takes a new sequence id; old record still resolves; `os-jobs` test passes |
| CB-033 empty and 10k-char name | DONE | empty refused, 10k round-trips; `os-identity` 2 tests pass |
| CB-034 allocation accounting never negative | DONE | `release` floors at zero under a release-heavy sequence; 2 tests pass |
| CB-035 future spend timestamp flagged | DONE | `record_at` refuses a future stamp and leaves the ledger untouched; 2 tests pass |
| CB-036 interleaved producer order | DONE | `queue-core` 2 tests pass |
| CB-037 reopen preserves order and count | DONE | `queue-store` 1 test passes |
| CB-038 nonzero worker exit recorded | DONE | `watchman_runner::tests::test_nonzero_discards_partial_stdout` passes |
| CB-039 stale exactly once | DONE | `a_snapshot_never_yields_both_stall_kinds_for_one_job` passes |
| CB-040 empty room refused | DONE | `validation::tests::room_names` and the relay HTTP refusal test pass |

Section 4 targeted checks: **56 pass, 0 fail** (`os-budget` 3,
`os-memory` 2, `guardrail` 2, plus the prior crate checks). Full suites
for the three touched crates also pass: `os-budget` **121**,
`os-memory` **69**, `guardrail` **45**.

## Section 5 — Relay + board (CB-041..050)

| Task | State | Evidence |
|---|---|---|
| CB-041 room created implicitly and listed once | DONE | `GET /rooms` added; relay test passes |
| CB-042 oversized message cap in error | DONE | 400 names `MAX_BODY_BYTES`; socket drain fixed; test passes |
| CB-043 history order after restart | DONE | three lines survive in order; test passes |
| CB-044 board empty title refused | DONE | `createPost` refuses an empty/blank title; test passes |
| CB-045 board reboot persistence | DONE | existing store-file restart test passes |
| CB-046 board edit other author refused | DONE | `editPost` checks the author; wrong author refused; test passes |
| CB-047 concurrent writers no interleave | DONE | 20 concurrent posts, one message per line; test passes |
| CB-048 board delete tombstone | DONE | `deletePost` keeps a tombstone record; test passes |
| CB-049 path characters refused | DONE | `ROOM_RE` rejects `../`, `a/b`; shared fixture test passes |
| CB-050 shared protocol fixture | DONE | `relay/protocol-edge.json` used by relay and board tests |

Section 5 checks: `node --test relay/relay.test.mjs` -> **12 pass,
0 fail**; `node --test board/board.test.mjs` -> **13 pass, 0 fail**.

## Section 6 — Schemas and validators (CB-051..060)

| Task | State | Evidence |
|---|---|---|
| CB-051 incident schema + validator | DONE | `$defs.incident`; one good and three bad records tested |
| CB-052 cycle schema + validator | DONE | `$defs.cycle`; real cycles pass, bad phase refused |
| CB-053 Aegis finding + secret refusal | DONE | `$defs.aegis-finding`; severity checked; secret-shaped value refused by path |
| CB-054 model receipt schema | DONE | `$defs.model-receipt`; all 9 committed receipts pass |
| CB-055 registry entry wired to CB-007 | DONE | calls `runtime.validateEntry`; all 28 entries pass |
| CB-056 boot-log index schema | DONE | parses the real index; 36 rows pass |
| CB-057 proof ledger row schema | DONE | parses the real ledger; 19 rows pass |
| CB-058 watch target schema | DONE | only the poller's `{type:file,path}` shape accepted |
| CB-059 baton handoff schema | DONE | job id + named author chain required |
| CB-060 single validate_all | DONE | counts only, no record content; exit 1 on any invalid |

Section 6 checks: `node tools/validate_all.mjs` -> **102 valid, 0
invalid, exit 0**; `node --test tests/validators-code100.test.mjs` ->
**11 pass, 0 fail**.

## Section 7 — Face test files only (CB-061..070)

| Task | State | Evidence |
|---|---|---|
| CB-061 five held face tests rerun | DONE | 23 pass, 0 fail; no face failure to record (`os-build/records/face-wave2-rerun.md`) |
| CB-062 dock ids map to apps | DONE | 13 dock ids, each in `APPS`; test passes |
| CB-063 same app opens once | DONE | early focus branch + one append path; test passes |
| CB-064 theme values round-trip | DONE | six storage keys read and written unchanged; test passes |
| CB-065 wallpaper ids exist | DONE | variant and background buttons equal their tables; test passes |
| CB-066 board renders the record shape | DONE | real board service post reads back; no sample data; test passes |
| CB-067 terminal help commands | DONE | exactly `status help uptime mem ps`; test passes |
| CB-068 dashboard card fields | DONE | status payload has tasks/heap/milestone used by the card; test passes |
| CB-069 login name + one password | DONE | Mrfentmen, one password input; test passes |
| CB-070 blue ribbon, no green-M | DONE | logo is ribbon `#4f7ec2`; no green-M file or reference; test passes |

Section 7 checks: five held files **23 pass, 0 fail**;
`node --test tests/face-code100.test.mjs` -> **9 pass, 0 fail**.

## Section 8 — Tooling scripts (CB-071..080)

| Task | State | Evidence |
|---|---|---|
| CB-071 light_gate `--only <stage>` | DONE | five stage guards; `--only omissions` test passes |
| CB-072 failing stage stops and names stage | DONE | `bad` exits 1 with `LIGHT GATE: FAIL — stage <name>`; test passes |
| CB-073 parity_lane dry-run | DONE | `--dry-run` prints the plan, compares nothing; test passes |
| CB-074 boot marker scanner | DONE | 12/12 markers on WAVE3 serial; truncated log names the miss; test passes |
| CB-075 receipts summarizer | DONE | totals by model; every cost says estimate; test passes |
| CB-076 branch tip reporter | DONE | branch, tip sha, changed files; scratch-repo test passes |
| CB-077 test-count differ | DONE | added/removed failure names; test passes |
| CB-078 records header linter | DONE | report only; run report in `logs/records-lint-code100.txt`; test passes |
| CB-079 sha256 evidence manifest | DONE | write + verify + changed detection; test passes |
| CB-080 fixture/TODO sweeper | DONE | unreferenced fixtures and TODO lines; report only; test passes |

Section 8 checks: `bash -n` on all three shell scripts -> **0**;
`node --test tests/tools-code100.test.mjs` -> **10 pass, 0 fail**.

## Section 9 — Officina + Musica pure code (CB-081..090)

| Task | State | Evidence |
|---|---|---|
| CB-081 fin height at max passes, +1 mm fails | DONE | exact 80.0 feasible; 81.0 names `fin_height_mm`; test passes |
| CB-082 zero/negative dimensions refused | DONE | early named refusal before physics; five cases pass |
| CB-083 pack missing bounds refused | DONE | `pack_export.py`; refuses before writing; test passes |
| CB-084 append-only workshop memory | DONE | sha256 chain; rewrite refused; tamper names line 1; test passes |
| CB-085 frequency/name round-trip | DONE | MIDI 21..108 round-trips; A4=440; test passes |
| CB-086 rhythm sum names measure | DONE | `measure 7: beats sum 2.5`; test passes |
| CB-087 honest pretty_midi skip | DONE | MIDI test skips with `pretty_midi is not installed`; pure tests import no MIDI |
| CB-088 prior-art note needs sources | DONE | `prior_art.py` refuses with `sources are required`; test passes |
| CB-089 modes derive from parent scale | DONE | seven modes, all parent pitch classes; test passes |
| CB-090 unknown material refused before stages | DONE | `faber.py`; stage list stays unrun; test passes |

Section 9 checks: `python3 -m unittest discover -s tests/officina -q` ->
**58 pass, 0 fail**; `python3 -m unittest discover -s tests/musica -q` ->
**6 pass, 0 fail**; `node --test tests/musica-midi.test.mjs` -> **1 skipped
(pretty_midi missing), 0 fail**.

## Section 10 — Kernel-adjacent tools (CB-091..100)

| Task | State | Evidence |
|---|---|---|
| CB-091 serial event parser | DONE | K6 log gives banner/alive/exit/fault/status events; test passes |
| CB-092 panic first-class | DONE | synthetic panic returns `RESULT: PANIC` before events; test passes |
| CB-093 gate-log differ | DONE | stage and verdict changes; test passes |
| CB-094 six-beat claims checklist | DONE | all six pass on the seeded log; missing marker named; test passes |
| CB-095 ABI doc to JSON | DONE | calls 0-5 + reserved 6-15; dispatch arms read as data; CLI exit 0 |
| CB-096 frame dimensions | DONE | 9 frames, all 1280x720; test passes |
| CB-097 log redaction counts | DONE | counts only, no value printed; test passes |
| CB-098 logs evidence manifest | DONE | 94 files written to `logs/MANIFEST-code100.json` with size/sha256/claim |
| CB-099 demo-log cross-check | DONE | 6 refs, 0 missing in the generated manifest |
| CB-100 closeout | DONE | this status file, from the final runs below |

Section 10 checks: `node --test tests/kernel-tools-code100.test.mjs` ->
**8 pass, 0 fail**; `node os-build/tools/logs_manifest.mjs ...` -> **94
files**; `node os-build/tools/demo_manifest_check.mjs ...` -> **6 refs,
0 missing**; `node os-build/tools/abi_json.mjs` -> exit 0.

## New test files for Pax to wire

- `tests/agents-code100.test.mjs`
- `tests/queue-python/test_code100_section2.py`
- `tests/science-lab/test_code100_section3.py`
- `crates/os-identity/tests/code100_section4.rs`
- `crates/queue-core/tests/code100_section4.rs`
- `crates/queue-store/tests/code100_section4.rs`
- `crates/os-jobs/tests/code100_section4.rs`
- `crates/os-budget/tests/code100_section4.rs`
- `crates/os-memory/tests/allocation_accounting.rs`
- `crates/guardrail/tests/code100_section4.rs`
- `relay/protocol-edge.json` (shared fixture)
- `os-build/schemas/records.schema.json`
- `tools/validate_all.mjs`
- `tests/validators-code100.test.mjs`
- `tests/face-code100.test.mjs`
- `os-build/records/face-wave2-rerun.md`
- `tests/tools-code100.test.mjs`
- `os-build/tools/boot_markers.mjs`
- `os-build/tools/receipts_summary.mjs`
- `os-build/tools/test_diff.mjs`
- `os-build/tools/records_lint.mjs`
- `os-build/tools/evidence_manifest.mjs`
- `os-build/tools/fixture_sweep.mjs`
- `os-build/tools/branch_tip.sh`
- `os/worlds/officina/runtime/pack_export.py`
- `os/worlds/officina/runtime/memory.py`
- `os/worlds/officina/runtime/prior_art.py`
- `os/worlds/officina/runtime/faber.py`
- `os/worlds/musica/runtime/theory.py`
- `tests/officina/test_code100.py`
- `tests/musica/test_theory.py`
- `tests/kernel-tools-code100.test.mjs`
- `os-build/tools/serial_events.mjs`
- `os-build/tools/gate_diff.mjs`
- `os-build/tools/claims_check.mjs`
- `os-build/tools/abi_json.mjs`
- `os-build/tools/frame_validate.mjs`
- `os-build/tools/redact_check.mjs`
- `os-build/tools/logs_manifest.mjs`
- `os-build/tools/demo_manifest_check.mjs`

## Honest closeout

The wave is 10 sections / 100 tasks: **100 DONE, 0 PARTIAL, 0 BLOCKED.**
The last eight were closed with real seams, not re-labelled: watchman
claim persistence, strict judge parse, budget spend at the cap, memory
release accounting, guardrail timestamp input, and the board post model
(title, author edit, delete tombstone). No task was faked.

## Final test counts (run on this tree, 2026-11-02)

| Section | Command | Result |
|---|---|---|
| 1 Agent runtime | `node --test tests/agents-code100.test.mjs` | 10 pass |
| 2 Queue Python | section-2 file + `test_livecams.py` + `test_judge.py` | 17 + 13 + 11 pass |
| 3 Science Lab | `test_code100_section3.py` | 12 pass |
| 4 Rust crates | code100_section4 + edge_cases + crate suites | 56 pass |
| 5 Relay + board | `node --test relay/relay.test.mjs board/board.test.mjs` | 12 + 13 pass |
| 6 Schemas | `tests/validators-code100.test.mjs` | 11 pass |
| 7 Face | five held files + `tests/face-code100.test.mjs` | 23 + 9 pass |
| 8 Tooling | `tests/tools-code100.test.mjs` | 10 pass |
| 9 Officina + Musica | officina 58, musica 6, MIDI 1 skip | 64 pass, 1 skip |
| 10 Kernel tools | `tests/kernel-tools-code100.test.mjs` | 8 pass |

**Total: 269 pass, 0 fail, 1 skip.** The only skip guard is
`pretty_midi is not installed` in `tests/musica-midi.test.mjs`; it is a
named missing dependency, not a fake pass.

Section 2 production changes: `judge.parse_verdict` tolerates prose and
fenced JSON but raises on garbage; `models.validate_receipt` +
`validate_receipts` added; `livecams.pick` drops offline cameras.
Section 3 added tests only; the lab modules already had the behaviour.
Section 4 added `spend` to os-budget, `release` accounting to os-memory,
and `record_at` to guardrail, plus three test files. Section 5 added
`GET /rooms` and the cap-bearing body error to relay, the board post
model (title/author/edit/delete tombstone), fixed the same socket-destroy
bug in both servers, and shared one protocol fixture.

## Final full-suite proof for the three changed crates

`cargo test -p os-budget` -> **121 pass**; `cargo test -p os-memory` ->
**69 pass**; `cargo test -p guardrail` -> **45 pass**. All exit 0, no
failures, no ignored tests.

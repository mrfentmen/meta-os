# Bond — 100 code tasks (Del's lane change, 2026-11-02)

**Del's ruling, verbatim in effect:** Bond is off the programs. No running
programs, no deploys, no websites, no servers, no browsers, no QEMU — the
8GB Mac is not to be blown up. Bond WRITES CODE, tests it in the shell
with one light command at a time, commits to his branch, and Pax checks
and merges from the tree. Wave 3 (programs) is superseded by this list.

**Branch:** `bond/code-wave`, off current main. Commit per section.
**Status file:** `os-build/BOND_CODE_STATUS.md`, one line per section.
**Test rule:** exactly one light command per check — `node --test <one file>`,
`python3 -m unittest <one module>`, or `cargo test -p <one crate>`.
Never a full suite, never `--workspace`, never two at once. A test that
needs something heavy gets written skip-guarded, with the guard named.
**Fences:** no kernel source; no services/ edits (Buffy's ring); no face
source edits (Hana's surface — test files only); no package.json edits
(Pax wires new test files at merge — list them in the status file).

## Section 1 — Agent runtime, Node (agents/, tests/) — CB-001..010
1. CB-001. Ledger writer: reject a record missing any required field, with the field named in the error; tests.
2. CB-002. Ledger reader: a torn final line (crash mid-append) is skipped and counted, never fatal; tests.
3. CB-003. Watchman: a job file that vanishes between scan and claim is a no-op, not a crash; tests.
4. CB-004. Watchman: claimed-id persistence survives a restart (write, reload, same set); tests.
5. CB-005. Baton: handing off a finished job is refused with the reason recorded; tests.
6. CB-006. Baton: a handoff chain of three keeps one job id and three authors in order; tests.
7. CB-007. Registry: validate every entry has name, lane, command, budget fields; a validator CLI + tests on good and bad fixtures.
8. CB-008. Runtime: spawn arguments are never shell-joined (injection fixture stays inert); tests.
9. CB-009. Runtime: budget receipt is written even when the child is killed mid-run; tests with a fake child.
10. CB-010. Gym: a drill that fails leaves a ledger record with the failing step named; tests.

## Section 2 — Queue Python seams (server/queue/, tests/queue-python/) — CB-011..020
11. CB-011. Envelope: round-trip a v2 assessment through write/read with byte equality; tests.
12. CB-012. Records writer: duplicate incident id is refused, original untouched; tests.
13. CB-013. Judge prompt builder: a division with no observations still produces a valid prompt (no crash, no invented observation); tests.
14. CB-014. Verdict parser: prose around the JSON verdict is tolerated exactly as documented, garbage raises; tests.
15. CB-015. Budget governor: the reserve floor refuses a call that would cross it, receipt written; tests with a fake caller.
16. CB-016. Trio store: a record written under one division is not visible under another; tests.
17. CB-017. SAM text parser: box-only, mask-only, and empty outputs each parse or raise as documented; tests.
18. CB-018. Model receipts: a receipt line with a missing model id fails validation loudly; validator + tests.
19. CB-019. Livecams: pick() with an area that has cameras but all offline returns empty, not an error; tests. (Read livecams.py first; extend its test file, do not rewrite it.)
20. CB-020. Crew seam: dispatch URL guard refuses every non-loopback URL in a parametrized sweep (http, https, ports, userinfo tricks); tests.

## Section 3 — Science Lab Python (os/worlds/science-lab/, tests/science-lab/) — CB-021..030
21. CB-021. Ladder: promotion to each level names its missing requirement, one test per level 1-3.
22. CB-022. Ladder: automated promotion above 3 is refused even with all records present; tests.
23. CB-023. Cycle: advancing past a human gate without a gate record parks, never advances; tests.
24. CB-024. Ledger chain: tampering with a middle record breaks verification at that record; tests.
25. CB-025. Preregistration: a result filed before its prereg hash exists is refused; tests.
26. CB-026. Compute: a crashed experiment records output_hash null and the crash, never a fake hash; tests.
27. CB-027. Verify: blind re-run gets no narrative (assert the input payload carries none); tests.
28. CB-028. Repository: query by level never returns a claim filed above its earned level; tests.
29. CB-029. Gateway: an off-allowlist tool call is refused AND the refusal is recorded; tests.
30. CB-030. Breeding: selecting a survivor before results exist is refused; tests.

## Section 4 — Rust, one crate at a time (crates/, cargo test -p only) — CB-031..040
31. CB-031. os-budget: spending exactly the cap succeeds, one unit over fails; tests.
32. CB-032. os-jobs: a job id reused after completion is a new job, not a resurrection; tests.
33. CB-033. os-identity: an empty name and a 10k-char name both handled without panic; tests.
34. CB-034. os-memory: allocation accounting never goes negative under release-heavy sequences; tests.
35. CB-035. guardrail: a spend record with a future timestamp is flagged, not silently filed; tests.
36. CB-036. queue-core: enqueue/dequeue order holds under interleaved producers (model the interleave in one thread); tests.
37. CB-037. queue-store: reopening a store preserves order and count; tests on a temp dir.
38. CB-038. os-supervisor: a worker that exits nonzero is recorded failed with its code; tests.
39. CB-039. os-worker: a heartbeat gap beyond the limit marks the worker stale exactly once; tests.
40. CB-040. relay crate: a message with an empty room name is refused at the type boundary or the parse boundary — pick one, document it, tests.

## Section 5 — Nuntius relay + board, Node (relay/, board/) — CB-041..050
41. CB-041. Relay: posting to a room creates it implicitly, and the room list shows it once; tests.
42. CB-042. Relay: a message over the size cap is refused with the cap in the error; tests.
43. CB-043. Relay: history returns messages in post order after a simulated restart (state file round-trip); tests.
44. CB-044. Board: a post with an empty title is refused; tests.
45. CB-045. Board: reboot persistence — posts written, reloaded, identical order and content; tests.
46. CB-046. Board: editing another author's post is refused (author field checked); tests.
47. CB-047. Relay: two writers appending concurrently never interleave a line (append is atomic per message); tests with a barrier.
48. CB-048. Board: a delete leaves a tombstone record, not a silent gap; tests.
49. CB-049. Relay: room names with path characters (../, /) are refused; tests.
50. CB-050. Both: a shared fixture file of protocol edge inputs, used by relay and board tests alike.

## Section 6 — Schemas and validators (schemas in os-build/schemas/, validators in tools/) — CB-051..060
51. CB-051. Incident record schema (v2 contract fields) as JSON Schema + a Node validator + tests on one good and three bad records.
52. CB-052. Cycle record schema + Python validator + tests.
53. CB-053. Aegis finding schema (severity, source route, timestamp) + validator + tests; a finding with a secret-shaped VALUE in any field is refused by the validator.
54. CB-054. Model receipt schema + validator + tests (extends CB-018's rule into a shared tool).
55. CB-055. Registry entry schema + validator wired to CB-007's checks + tests.
56. CB-056. Boot-log index schema: the index generator's output validated against it; tests.
57. CB-057. Program proof ledger schema: every row must carry command + count + evidence path; validator + tests.
58. CB-058. Watch-target schema (name, kind, liveness state) + validator + tests.
59. CB-059. Baton handoff schema + validator + tests.
60. CB-060. A single `tools/validate_all.mjs` that runs every validator in this section over the repo's committed records and reports counts only.

## Section 7 — Face test files only (tests/, no face source edits) — CB-061..070
61. CB-061. Re-run your five held wave-2 Node test files against current main; fix the TESTS where the face legitimately changed, file a record where the face is actually wrong; the five pass or the failure is a named record.
62. CB-062. Dock: every dock entry maps to an app id that exists in the apps table; test.
63. CB-063. Windows: opening the same app twice focuses, never duplicates; test at the logic level.
64. CB-064. Settings: theme values round-trip through storage keys unchanged; test.
65. CB-065. Wallpapers: every wallpaper id in settings exists in the wallpaper table; test.
66. CB-066. Board window: a board post renders from the record shape, not from sample data; test.
67. CB-067. Terminal: the help line lists exactly the approved commands (status help uptime mem ps); test.
68. CB-068. Dashboard cards: each card's field exists in the status payload shape; test.
69. CB-069. Login: the name shown is Mrfentmen and there is exactly one password field; test.
70. CB-070. Boot screen: the logo is the ribbon (blue), and no green-M asset is referenced anywhere; test by grep over the face tree.

## Section 8 — Tooling scripts (os-build/tools/) — CB-071..080
71. CB-071. light_gate.sh: add a `--only <stage>` flag; shell test with stub commands.
72. CB-072. light_gate.sh: a failing stage stops the run and names the stage in the summary; test.
73. CB-073. parity_lane.sh: dry-run mode prints what it would compare without comparing; test.
74. CB-074. A boot-log marker scanner (Node): reads a serial log, reports which claim markers are present/absent; tests on the committed WAVE3 log (all present) and a truncated copy (absent named).
75. CB-075. A receipts summarizer (Node): totals model receipts by model, estimates labelled estimates; tests.
76. CB-076. A branch-tip reporter (shell + git): prints branch, tip sha, and files changed vs main for the current branch; test in a scratch repo.
77. CB-077. A test-count differ (Node): compares two suite outputs and reports added/removed failures by name; tests.
78. CB-078. A records linter (Node): every os-build/records/*.md carries the required header fields; tests + a run report (report only, no record edits).
79. CB-079. A sha256 manifest tool for evidence dirs (Node): write and verify modes; tests.
80. CB-080. A TODO/fixture sweeper (Node): lists files under tests/ that no suite references; report only; tests.

## Section 9 — Officina + Musica pure code — CB-081..090
81. CB-081. Officina bounds: fin height exactly at FIN_HEIGHT_MM passes, 1mm over fails; tests (Python, existing suite style).
82. CB-082. Officina bounds: negative and zero dimensions are refused with the dimension named; tests.
83. CB-083. Officina pack export: a pack missing its bounds record is refused; tests.
84. CB-084. Officina workshop memory: appends are append-only (a rewrite attempt is detectable by hash); tests.
85. CB-085. Musica note math: frequency-to-note-name round-trips across the piano range; tests in pure Python (no pretty_midi import).
86. CB-086. Musica rhythm: a measure's beats sum exactly or the error names the measure; tests, pure Python.
87. CB-087. Musica: the pretty_midi-dependent tests get honest skip guards naming the missing dependency (no fake passes); the pure tests above must not import it.
88. CB-088. Officina: prior-art note shape — a note without sources is refused by its validator; tests.
89. CB-089. Musica scale builder: every mode of a scale derives from the parent scale's notes; tests, pure Python.
90. CB-090. Officina faber seam: a build order with an unknown material is refused before any stage runs; tests with seams faked.

## Section 10 — Kernel-adjacent code (read-only inputs, tools/) — CB-091..100
91. CB-091. Serial-log parser (Node): turns a boot log into structured events (banner, alive, tasks, exits, faults); tests on committed logs.
92. CB-092. The parser names a panic anywhere in the log as the first-class result PANIC, never buried; tests with a synthetic panicked log.
93. CB-093. Gate-log differ (Node): two gate logs compared, verdict changes listed; tests.
94. CB-094. A claims checklist tool: given a log, checks the six demo beats' markers and prints pass/missing per beat; tests.
95. CB-095. Userspace ABI doc generator: reads the ABI doc's table and emits a machine-readable JSON of calls 0-5 + reserved 6-15; tests (syscalls.rs is read as data only — actually read user.rs's dispatch as data; never edit kernel source).
96. CB-096. A framebuffer-frame validator (Node): ribbon frame files have consistent dimensions across the set; tests on the committed frames.
97. CB-097. A log-redaction checker: scans a log for secret-shaped strings and reports counts only; tests with a seeded fixture.
98. CB-098. An evidence manifest for os-build/logs: file, size, sha256, one-line claim each; generator + tests.
99. CB-099. Cross-check tool: every log named in DEMO_SCRIPT beats exists in the manifest (CB-098) — a missing one fails loudly; tests.
100. CB-100. Closeout: BOND_CODE_STATUS.md complete — every section's tests counted from actual runs, every skip guard named, and a list of the new test files for Pax to wire at merge.

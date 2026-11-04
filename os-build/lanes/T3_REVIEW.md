# T3 REVIEW — adversarial check vs lane brief (2026-11-04)

Reviewer: subagent, worktree `/tmp/agent-t3`, branch `agent-t3` (base `9a2e87b2`).
Method: `git status --short`, `git diff --stat`, `git diff`, reads of
`T3_REPORT.md` + `T3_SECTION_A..F.md`, grep secret sweep, `pgrep -f qemu`,
branch/remote state. No edits to lane code, no commits, no QEMU boot,
no paid calls, no key/token values printed (patterns only below).

## 1. File inventory — every changed/added file

Tracked modifications (`git diff --name-only HEAD`):
- `agent-layer/meta-ask.py` — OWNED (`agent-layer/`). 264 → 757 lines verified (`git show HEAD:... | wc -l` = 264, `wc -l` = 757).
- `agents/bridge.mjs` — OWNED (`agents/`). 1-line `repoRoot` thread.
- `agents/runtime.mjs` — OWNED (`agents/`). `repoRoot` param + resolve base + CLI call.
- `iso/apps/agent-status/meta-ask.py` — OWNED (`iso/apps/agent-status/`). Mirror, 757 lines; `diff` vs `agent-layer/meta-ask.py` = 1 hunk (`701c701`, `parents[1]` vs `parents[2]`). Claim "differs by ONE line" TRUE in content.
- `server/queue/patrol.py` — OWNED (`server/queue/`). +15/-3 `paused_since` marker.
- `server/queue/receipt_validate.py` — OWNED (`server/queue/`). +45 appended validators only.

Untracked (`git ls-files --others --exclude-standard`):
- `agent-layer/job_schema.json` (90 lines) — OWNED.
- `agent-layer/test_submit_path.py` (520 lines) — OWNED.
- `agents/RECEIPTS.md` (89 lines) — OWNED.
- `os-build/iso/payload-agent/stage.sh` (46 lines) — OWNED.
- `os-build/lanes/T3_REPORT.md` — OWNED (explicitly named in brief).
- `os-build/lanes/T3_SECTION_A.md` — SEE §2.
- `os-build/lanes/T3_SECTION_B.md` — SEE §2.
- `os-build/lanes/T3_SECTION_C.md` — SEE §2.
- `os-build/lanes/T3_SECTION_D.md` — SEE §2.
- `os-build/lanes/T3_SECTION_E.md` — SEE §2.
- `os-build/lanes/T3_SECTION_F.md` — SEE §2.
- `server/queue/keyring.py` (207), `receipts.py` (707), `run_queue.py` (825), `scan_runs_for_keys.py` (80), `stub_provider.py` (53), `test_page_mapping.py` (490), `test_receipts.py` (160), `test_run_queue.py` (495) — all OWNED (`server/queue/`).

No `server/crew-*.mjs` changes (zero hits in status — allowed but untouched, fine).

## 2. Owned-paths verdict

CONDITIONAL PASS with one strict-reading flag:

- `grep -E "os-build/face/|trio/|os-build/identity/|os-build/iso/payload-theme/"` over `git status` + `git diff --name-only` + untracked list → **no hits**. Forbidden dirs untouched. `os-build/face/`, `trio/`, `identity/`, `payload-theme/` appear ONLY as quoted file+line requests (e.g. REPORT §148, F R1–R7), never as edits. Good.
- Strict brief wording is `os-build/lanes/T3_REPORT.md` (singular file), not `os-build/lanes/` (directory). Under that literal reading the six helper files `T3_SECTION_A..F.md` are **outside owned paths** — they are untracked in `os-build/lanes/`. This is almost certainly not the intent (REPORT §133 explicitly lists `T3_SECTION_{A..F}.md` as "uncommitted helpers alongside this report", and this review file `T3_REVIEW.md` is itself in the same directory by instruction), but the lane lead should either (a) broaden the owned-path line to `os-build/lanes/T3_*.md`, or (b) fold sections into the report before commit. As written, flag as technical violation; do not commit SECTION files until the brief line is amended.
- This file `T3_REVIEW.md` inherits the same status — created per instruction for the lead to fold/commit.

No other owned-paths issue. §134 claim "test litter outside owned paths was reverted/removed; git status shows lane files only" is TRUE as of this review (no `runs/`, `memory/`, `os-build/{aegis,handsfree,nervus}` entries in status).

## 3. Unanchored / invented claims (exact file+line)

Brief rule: every test count / timing / cost / exit code / artifact path must be pasted with its command or clearly marked as another section's cited output.

### 3a. Must-fix (blocks "safe to commit")

1. `T3_REPORT.md:117` — "`M server/queue/run_queue.py`". FALSE status letter. `git status --short server/queue/run_queue.py` → `??` (new untracked, 825 lines), not `M`. Same file is correctly called "New" at REPORT §48. Fix: change `M` to `new`.
2. `T3_REPORT.md:143-146` (§139) — "`submit()` now preserves a boolean `dry_run` … proven: filed job carries it, drain returns `dry` … C+D+B suites re-run green." CODE FIX IS PRESENT (see §4), but NO pasted command+output exists in ANY `T3_*.md`: no `cat jobs/d1.job.json`, no `run_once()` output, no suite rerun log. `T3_SECTION_E.md:347-350` even states the pre-fix position ("`submit()` drops unknown envelope keys … my `Runner.dry_run` flag covers the mode without touching `submit`"). Corroboration exists NOW only in `/tmp` (`/tmp/t3-g/dry.py`, `/tmp/t3-g/dry/jobs/d1.job.json` carries `"dry_run": true`, `/tmp/t3-g/dry/jobs/d1.result.json` is `status: dry, reason: dry-run: prompt built, no model call sent`), but that output was never pasted into a report. Under the brief rule this "proven" is unanchored. Fix: paste the `/tmp/t3-g/dry.py` run (command + `DRY-PER-JOB OK` + both JSONs) into the report or an appendix, and paste the claimed `C+D+B` rerun commands+outputs (or downgrade to "code present, rerun pending").
3. `T3_REPORT.md:166-167` (§144) + `T3_REPORT.md:176-177` (§146) — "0.17/0.11/0.12s wall (`/usr/bin/time`), in-queue ELAPSED 0.10/0.04/0.04s — three lead-run stub jobs, same command." NO pasted `/usr/bin/time` output and NO pasted `ELAPSED` lines exist in any section or in `/tmp` logs. `grep -rn "0\.17\|0\.11\|0\.12" os-build/lanes/T3_*.md /tmp/t3-g/` hits ONLY these two report lines. Closest on-disk numbers contradict: `/tmp/t3-g/t1|t2|t3/jobs/e2e-1.result.json` carry `wall_ms` 95.8/35.7/39.9 (≈0.10/0.04/0.04 — matches the ELAPSED half), while `/tmp/t3-g/err1..3.txt` carry `real 0.19/0.20/0.19` (not 0.17/0.11/0.12). Fix: either paste the actual three `/usr/bin/time` invocations or replace with the anchored `wall_ms` values and cite the files.
4. `T3_REPORT.md:159-163` (§143 judge paragraph) — "every run leaves a record plus a separately verifiable receipt — including failures and dry runs." The word "every" is FALSE on this repo's own evidence: `T3_SECTION_A.md:211-217` (§11) — normal finish/crash emits NO `receipt.json`; `T3_SECTION_C.md:169-174` (§9) — "no `receipt.json` exists after any test run (`assertFalse…`)"; `T3_SECTION_F.md:106-113` (R1) — no receipts panel, `grep receipt` zero hits in `agents.html`. Only D's `wrap_run`/`receipts.py write` runs plus the lead's post-hoc `/tmp/t3-g/e2e/runs/e2e-1-a1/receipt.json` have both. Failures/dry runs DO have both in D/E (kill9 §88, dry §100-101 pasted), but the universal "every run" covers C-runner and watchman normal paths that provably do not. Fix: narrow to "every D-wrapped / lead-e2e run" or "record always, receipt where D's writer is wired".
   - Companion: "in about a tenth of a second" vs anchored 36.8ms (`/tmp/t3-g/e2e` record `wall_ms: 36.8`, REPORT §100). 36.8ms is ~one-third of a tenth, t1 is 95.8ms (~one tenth). "About a tenth" is loose but not false; prefer "tens of ms (36.8ms lead e2e, 35–96ms across /tmp/t3-g/t1-3)".
5. `T3_REPORT.md:100-106` (§131) — lead e2e `{"e2e-1": "ok"}`, wall 36.8ms + seven artifact paths. Artifacts EXIST in `/tmp/t3-g/e2e/` (verified: `jobs/e2e-1.job.json`, `jobs/e2e-1.result.json` with `wall_ms 36.8`, `runs/e2e-1-a1/{record.json,output.log,receipt.json,input.json}`, `worlds/w.txt`, `prompts/p.txt`, `watchman.jsonl`) and `receipt verify` returns `OK … (v1 hash covers input+output)` (re-ran read-only now, exit 0). So the claim is TRUE but NON-DURABLE: report itself admits "Artifacts live in /tmp by design — no fixtures committed". Under "every run claimed must have its record file path" the paths ARE given, but a post-`/tmp`-wipe verifier cannot check them and no stdout of `/tmp/t3-g/e2e.py` was ever pasted (script exists at `/tmp/t3-g/e2e.py`, also not committed). Flag as weak-by-design, not invented — require at minimum pasting `cat record.json/result.json + verify` output (currently only summarized) if the report is to stand alone.
   - Note: lead receipt `cost_usd: null` vs lead record `cost_usd: 0.0001` (verified via read). Not a contradiction of spend ($0 real), but shows two receipt systems (C runner record vs D post-hoc receipt filed without `--cost`). Judge paragraph's "cost figures are stub test data" is correct; add one sentence noting the null-vs-0.0001 split so a reader does not call it tamper.
6. `T3_REPORT.md:186` summary table — "receipts … D 8/8 + CLI 11/11 + lead verify". `8/8` pasted (`T3_SECTION_D.md:220-234`). `11 pass` pasted as `python3 -m unittest discover -s tests/queue-python -p "test_receipt*.py"` → 11 pass (`T3_SECTION_D.md:332-333`), but that is the pre-existing + new validator discover suite, not a "CLI 11/11" — label is misleading. "lead verify" output never pasted (we reproduced `OK` now, but report has no paste). Fix label to "discover 11 pass" and paste lead `verify` line.
7. `T3_SECTION_C.md:18` — "`run_queue.py` (new) | 799". STALE after lead §139 edit: file is now 825 lines (`wc -l`). Update count or drop it (line counts are cosmetic, but the brief's no-invention rule counts them).

### 3b. Anchored — do not change (for the lead's fold)

- B 31/31 + ~7s: pasted `T3_SECTION_B.md:258-293` (31 named tests + `Ran 31 tests … OK`). File counts 757/90/520 verified.
- C 14/14 + ~19s and 50-patrol/orchestrator/crew: pasted `T3_SECTION_C.md:153-165` (`Ran 14 tests in 19.0s — OK`, `14 passed`, `50 passed in 0.71s`, `compile OK`).
- D tamper 1-byte flip + `output_sha256 mismatch` exit 1, failed-receipt `failed | child exited with code 3`, `kill -9` wrapper exit 0 + `failed … SIGKILL … exit 137`, discovery `list`/`count 3`, version-2 refuse, secret scan `findings: []` + `grep exit=1`: all pasted `T3_SECTION_D.md:65-92,127-143,185-191,220-234,244-248,266-275,311-327`. Good.
- E key-gate matrix (`stub-no-key ok`, `think-no-key rejected … provider_pid None`, `think-fake-key ok stub-model-1`, `dry … cost None … no output`): pasted `T3_SECTION_E.md:210-248,259-264,289-295` with exact `reason` strings; staged modes `750/700/640/600` pasted §167-177; endpoint isolation grep `CLEAN` §311-317. Good.
- F 84/84: head+tail pasted `T3_SECTION_F.md:228-262` with explicit note that middle 60 lines are summarized, not pasted. Acceptable ONLY because the per-string contracts are enumerated in §§1–2 and the selftest file is committed (`server/queue/test_page_mapping.py`, 490 lines) — but strictly the brief asks for pasted output per claim; lead should note "head/tail pasted, full log reproducible via `python3 server/queue/test_page_mapping.py`" (add that sentence; currently implied).
- A 23-live/1-draft + `--list` paste, registry shape, Bug #1 diff + `22 pass, 0 fail` + `49 pass, 1 fail (R12-010 pre-existing, fails stashed too)`: pasted `T3_SECTION_A.md:89-122,308-350`. Good. Bug #2 named-not-fixed with repro (`node /tmp/…` exit 0 silent vs `/private/tmp/…` exit 4) pasted §294-297. Good.
- B dead-queue `0.107 total` + `<2s`: pasted `T3_SECTION_B.md:136-141`. REPORT §40's "**0.107s**" anchored there.
- Cost `$0.00 real` + stub `0.0001` as fixture: consistent across C §134-136, D §335-337 (`cost_usd null`), E §297 (`cost null`), REPORT §173-174. Inference "nothing spent" rests on "no key + stub-only + no network" (E §311-320, C §147-149 greps) — legitimate absence-of-spend argument, not a measured bill. Keep wording "no spend possible" rather than presenting as a metered $0.00 if strictness is wanted; current §145 parenthetical already says fixture-vs-spend correctly.

### 3c. Absolute-word sweep

- "never receipts" (REPORT §22: watchman writes results, never receipts) — TRUE per A §11 (only budget/memory/wall-clock write `receipt.json` in `runtime.mjs`; normal drain writes `.result.json`). Keep, but it directly contradicts §143 "every run … receipt" — another reason to fix §143.
- "never estimated" (cost from provider response, REPORT §51): anchored via `payload.get("cost_usd")` citation (C §134-136). Keep.
- "never reads key file / never sent anywhere but 127.0.0.1" (B §8, C §147-149, E §311-320): anchored via `grep -n os.environ` (5 vars), `grep … socket|urlopen` no-hits, status-server `127.0.0.1` bind citation. Keep.
- "all exit 1", "every one verified to parse", "duplicate-impossible", "CHEAPEST fixed": "duplicate-impossible" overstates — proven is 50-thread burst → 1 filed / 49 `duplicate-id` (C §114-115), i.e. duplicate-*refused*, not impossible to attempt. Suggest "duplicate-refused (burst-proof)". "Cheapest fixed" (§139) is a judgment, not a measurement — code fix present (see §4), cost comparison ("cheapest") has no alternative-cost analysis pasted; downgrade to "lowest-risk fix applied" or paste the considered alternatives.
- "nothing was spent" (judge para): true given no key + stub-only, but phrase as "no real spend (no key, stub-only)" — already done in §144; keep that qualification and do not let the short paragraph travel without it.

## 4. §138–140 stage-failure trio — is the cheapest fix in the diff?

YES, the code is present; the *proof paste* is not (see 3a.2).

- (1) `server/queue/run_queue.py:201-204` preserves `dry_run` verbatim into the filed envelope (`if isinstance(job.get("dry_run"), bool): envelope["dry_run"] = job["dry_run"]`), with comment citing "Stage-failure fix (T3 §139)". `server/queue/keyring.py:198` honors it (`if dry_run or job.get("dry_run"): return ("dry", …)`), and `run_queue.py:538-540` calls `keyring.preflight(job, dry_run=getattr(self, "dry_run", False))` where `job` is the filed envelope re-read from disk (`run_queue.py:480-487`), so per-job `dry_run` reaches the gate even when the Runner flag is false. The previously dead path (E §347-350: "`submit()` drops unknown envelope keys") is closed.
- Live `/tmp` corroboration (not yet pasted in any report): `/tmp/t3-g/dry/jobs/d1.job.json` contains `"dry_run": true`; `/tmp/t3-g/dry/jobs/d1.result.json` is `{"status": "dry", "reason": "dry-run: prompt built, no model call sent", "wall_ms": 0.0, "cost_usd": null}`; script `/tmp/t3-g/dry.py` asserts both. Require the lead to paste this (command + `DRY-PER-JOB OK` + both JSONs) before claiming "proven".
- (2) key provisioning + (3) metaosd absence: correctly marked NOT fixed, with exact cross-lane pointers (E `stage.sh` non-root note, F R7). No code claims beyond owned paths. Accurate.

## 5. §145 cost math + §146 timings consistency

- §145 "`$0.00` real (stub `0.0001`/run is fixture data)": CONSISTENT with C (stub emits 0.0001 from provider response), D (null, never estimated), E (null for dry/rejected). No arithmetic error. Recommend keeping the existing parenthetical everywhere the 0.0001 appears so no reader mistakes fixture for spend.
- §146 "0.17/0.11/0.12 wall, ELAPSED 0.10/0.04/0.04": INCONSISTENT with cited runs. In-queue `wall_ms` for the three `/tmp/t3-g/t1-3` jobs are 95.8/35.7/39.9ms (≈0.10/0.04/0.04 — matches the ELAPSED half, suggesting ELAPSED was copied from `wall_ms`). The wall half (0.17/0.11/0.12) matches NOTHING pasted or on disk (`real 0.19/0.20/0.19` in `err*.txt`; no `/usr/bin/time` paste anywhere). Either paste the three time invocations or correct §146/§144 to the anchored `wall_ms` values.
- §144 "tenth of a second → 0.17/0.11/0.12 wall, ELAPSED …" inherits the same defect. The burst-test half of §144 (50 submits → 1 filed/49 duplicate-id) IS anchored (C §114-115 + `test_burst…` in `test_run_queue.py`), but the citation is to the suite, not a pasted burst log — acceptable under "clearly marked as another section's cited output".

## 6. Secret scan (patterns only, never values)

- `git diff HEAD -- <6 tracked files> | grep -Ei "sk-[A-Za-z0-9]{20,}|ghp_|gho_|Bearer [A-Za-z0-9]|BEGIN PRIVATE KEY|eyJ[A-Za-z0-9_-]{10,}"` → no hits (exit 0 on the grep pipeline means no match lines printed; only `grep exit` status observed).
- Untracked code+tests+stage+schema: `grep -rEi` hits ONLY scanner-needle literals, no values: `server/queue/receipts.py: "BEGIN PRIVATE KEY", "BEGIN RSA PRIVATE KEY"` (needle list in `scan_for_secrets`), `server/queue/test_receipts.py: ("SPARK_API_KEY", "BEGIN PRIVATE KEY", "sk-")` (assert-absent list). No `ghp_`, no `Bearer <token>`, no `eyJ…`, no 20+-char `sk-` value.
- `grep -rniE "sk-[A-Za-z0-9]{20,}|SPARK_API_KEY=[A-Za-z0-9]|ghp_|BEGIN PRIVATE KEY|=eyJ…" os-build/lanes/T3_*.md` → single hit: `T3_SECTION_D.md:273`, which is the *scan command itself* (`grep -rn "SPARK_API_KEY\|sk-\|BEGIN PRIVATE KEY\|prompt_body" /tmp/t3d-demo/…`), not a secret. REPORT §137's clean claim holds; env-var *names* (`SPARK_API_KEY`, `METAOS_KEY_FILE`, `OC2_QUEUE_HOST/PORT`) appear in prose as documented, values never appear.
- `grep -rn "Bearer" server/queue/run_queue.py server/queue/keyring.py server/queue/receipts.py server/queue/stub_provider.py agent-layer/meta-ask.py` → no hits. No auth-header leak.
- RESULT: **no leaked secrets found**. One hygiene note (not a leak): needles contain the literal `sk-` prefix; that is required for the scanner to work and matches D/E's documented needle policy.

## 7. QEMU / merge / push

- `pgrep -fl "qemu-system|qemu-img"` → empty (exit 1). No QEMU evidence in diff (no `qemu`, `qmp`, `qcow2`, `ovmf` strings in changed files beyond this review's own mention). F screenshots used headless Chrome `file://` only, explicitly kept out of repo (`/tmp/t3f-*.png`). C/D/E runs used `/bin/echo`, stub provider, `kill -9`, loopback stub servers — no VM.
- Branch state: `git branch --show-current` → `agent-t3`; `git log --oneline -5` base `9a2e87b2` unchanged; `git status` shows 6 modified + 18 untracked, zero commits on top of base. `git branch -vv` shows `agent-t3` with no upstream/ahead-behind (unpushed, as required). `git remote -v` is `origin https://github.com/mrfentmen/meta-os (fetch/push)` — no push performed by this lane (no `push` in shell history inspected; status remains uncommitted). No merge commits, no `MERGE_HEAD`.
- RESULT: **no QEMU, no merge, no push**. Safe on this axis.

## 8. Verdict: safe to commit as-is?

**NO — required fixes (small, lead-only, all inside owned paths):**

1. Fix `T3_REPORT.md:117`: `M server/queue/run_queue.py` → `new server/queue/run_queue.py` (it is `??`).
2. Paste or downgrade §139 proof: add the per-job dry-run command+output (`python3 /tmp/t3-g/dry.py /tmp/t3-g/dry` → `DRY-PER-JOB OK` + `d1.job.json` showing `"dry_run": true` + `d1.result.json` showing `status: dry`) and the claimed `C+D+B` rerun commands+outputs; or change "proven … re-run green" to "code landed, rerun pending".
3. Fix §144/§146 numbers: paste the three `/usr/bin/time` runs + ELAPSED lines, or replace with anchored `wall_ms 95.8/35.7/39.9ms` (+ lead `36.8ms`) and cite `/tmp/t3-g/{t1,t2,t3,e2e}/jobs/e2e-1.result.json`.
4. Narrow §143 judge paragraph: replace "every run leaves a record plus a separately verifiable receipt" with the accurate scope (e.g. "every D-wrapped / lead-e2e run leaves a record plus a separately verifiable receipt; the C runner always leaves a record, the D receipt where wired"), and qualify "about a tenth of a second" with the measured range.
5. Fix `T3_SECTION_C.md:18` line count (799 → 825) or drop the count; relabel REPORT table "CLI 11/11" → "discover 11 pass" and paste the lead `verify OK` line for `/tmp/t3-g/e2e/runs/e2e-1-a1/receipt.json`.
6. Resolve the owned-paths wording: amend the brief line to `os-build/lanes/T3_*.md` (or fold sections) before committing `T3_SECTION_*.md` + this `T3_REVIEW.md`; otherwise commit ONLY the six tracked modifications + `T3_REPORT.md` + `server/queue/*` + `agent-layer/*` + `agents/RECEIPTS.md` + `payload-agent/stage.sh` and hold the SECTION files.

After 1–6, the report is committable: paths are clean, secrets clean, QEMU/push clean, and every remaining number traces to a pasted command or a committed test that reproduces it.

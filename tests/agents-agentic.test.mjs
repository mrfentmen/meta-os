import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import {
  ContractError,
  abandon,
  assertContract,
  canFinish,
  contractDigest,
  emptyContract,
  finish,
  loadContract,
  recordDecision,
  recordDoneCheck,
  recordLessonApplied,
  recordObservation,
  recordPlanRevision,
  recordResult,
  reopen,
  saveContract,
  validateContract,
} from "../agents/contract.mjs";
import { resumeLoop, runLoop, shellCheck } from "../agents/loop.mjs";
import {
  assertGranted,
  checkCommand,
  checkNetwork,
  checkPath,
  checkSpend,
  checkWall,
  guardedAppend,
  guardedExec,
  guardedWrite,
  narrowGrants,
  normalizeGrants,
  resolveProgram,
} from "../agents/grants.mjs";
import {
  assertFresh,
  deadEnds,
  deadEndStats,
  findDeadEnd,
  recordDeadEnd,
  renderDeadEnds,
  taskSignature,
} from "../agents/deadends.mjs";
import {
  appliedByAgent,
  appliedCounts,
  learningHealth,
  lessonBoard,
  recordApplied,
  untouchedLessons,
} from "../agents/learning.mjs";
import { teach } from "../agents/lessons.mjs";
import {
  CONTINUE_FILE,
  claimContinue,
  continueDecision,
  continueJob,
  readContinue,
  writeContinue,
  writeContinueJob,
} from "../agents/continue.mjs";
import { createWatchman } from "../agents/watchman.mjs";
import { runJudgmentDrills } from "../agents/drills.mjs";

const NODE = process.execPath;
const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), "agentic-test-"));

function verified() {
  let contract = emptyContract({ goal: "fix the thing", doneCondition: { cmd: "make check" } });
  contract = recordObservation(contract, { cmd: "probe", exit: 1, tail: "broken" });
  contract = recordDecision(contract, {
    considered: [{ action: "sleep", why_not: "does not close the race" }],
    chose: { action: "add a barrier", why: "obs-1 shows interleaving", because: "obs-1" },
  });
  contract = recordResult(contract, { exit: 0, evidence: "test passes 20/20" });
  return contract;
}

async function until(fn, timeout = 3000) {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    if (fn()) return true;
    await new Promise((resolve) => setTimeout(resolve, 10));
  }
  return false;
}

/* ---- contract ---- */

test("contract: observe -> decide -> act -> verify is enforced and can finish", () => {
  let contract = emptyContract({ goal: "fix it", doneCondition: { cmd: "make check" } });
  assert.throws(
    () =>
      recordDecision(contract, {
        considered: [{ action: "x", why_not: "y" }],
        chose: { action: "z", why: "w", because: "obs-1" },
      }),
    { code: "no-open-step" },
  );

  contract = recordObservation(contract, { cmd: "make check", exit: 1, tail: "FAIL" });
  assert.throws(() => recordObservation(contract, { cmd: "again", exit: 0 }), { code: "step-open" });
  assert.throws(
    () =>
      recordDecision(contract, {
        considered: [],
        chose: { action: "z", why: "w", because: "obs-1" },
      }),
    { code: "alternatives-required" },
  );
  assert.throws(
    () =>
      recordDecision(contract, {
        considered: [{ action: "z", why_not: "rejected" }],
        chose: { action: "z", why: "w", because: "obs-1" },
      }),
    { code: "contradictory-decision" },
  );
  assert.throws(
    () =>
      recordDecision(contract, {
        considered: [{ action: "sleep", why_not: "hides it" }],
        chose: { action: "barrier", why: "race", because: "obs-99" },
      }),
    { code: "citation-required" },
  );

  contract = recordDecision(contract, {
    considered: [{ action: "sleep", why_not: "hides it" }],
    chose: { action: "barrier", why: "obs-1 shows interleaving", because: "obs-1" },
  });
  assert.throws(() => recordResult(contract, { exit: 0, evidence: "" }), { code: "evidence-required" });
  contract = recordResult(contract, { exit: 0, evidence: "20 runs green" });
  assert.throws(() => finish(contract), { code: "done-not-run" });

  contract = recordDoneCheck(contract, { cmd: "make check", exit: 0, tail: "ok" });
  assert.equal(canFinish(contract).ok, true);
  contract = finish(contract);
  assert.equal(contract.status, "done");
  assert.equal(contract.seq > 0, true);
  assert.equal(contract.done_evidence.exit, 0);
});

test("contract: a done check from a different command or a failed exit is refused", () => {
  const base = verified();
  assert.throws(
    () => finish(recordDoneCheck(base, { cmd: "true", exit: 0 })),
    { code: "done-command-mismatch" },
  );
  assert.throws(
    () => finish(recordDoneCheck(base, { cmd: "make check", exit: 1 })),
    { code: "done-failed" },
  );
});

test("contract: a passing check before the last step is stale, and plan revisions cite observations", () => {
  const base = verified();
  const early = { ...base, done_checks: [{ cmd: "make check", exit: 0, tail: "", at: "2000-01-01T00:00:00.000Z", seq: 1 }] };
  assert.throws(() => finish(early), { code: "done-stale" });

  assert.throws(
    () => recordPlanRevision(base, { from: "p1", to: "p2", because: "obs-99" }),
    { code: "citation-required" },
  );
  const revised = recordPlanRevision(base, { from: "p1", to: "p2", because: "obs-1" });
  assert.equal(revised.revisions.length, 1);
  assert.equal(revised.steps[0].plan_revision.to, "p2");
});

test("contract: an applied lesson attaches to the step and cannot be double-counted", () => {
  let contract = emptyContract({ goal: "g", doneCondition: { cmd: "true" } });
  assert.throws(() => recordLessonApplied(contract, { lesson: "L-12" }), { code: "no-step" });
  contract = recordObservation(contract, { cmd: "probe", exit: 1, tail: "" });
  contract = recordLessonApplied(contract, { lesson: "L-12", outcome: "used" });
  assert.equal(contract.steps[0].lessons_applied[0].lesson, "L-12");
  assert.throws(() => recordLessonApplied(contract, { lesson: "L-12" }), { code: "lesson-duplicate" });
  assert.throws(
    () => recordLessonApplied(contract, { lesson: "L-13", outcome: "vibes" }),
    { code: "lesson-outcome-invalid" },
  );
  const verdict = validateContract({
    ...contract,
    steps: [{ ...contract.steps[0], lessons_applied: [{ lesson: "", outcome: "used" }] }],
  });
  assert.equal(verdict.ok, false);
  assert.ok(verdict.errors.some((error) => error.path.includes("lessons_applied")));
});

test("contract: save/load round-trips and tampering fails validation", () => {
  const dir = tmp();
  const file = path.join(dir, "contract.json");
  let contract = verified();
  contract = recordDoneCheck(contract, { cmd: "make check", exit: 0, tail: "" });
  contract = finish(contract);
  saveContract(file, contract);
  assert.equal(loadContract(file).status, "done");

  const tampered = {
    ...contract,
    steps: [{ ...contract.steps[0], chose: { ...contract.steps[0].chose, because: "obs-9" } }],
  };
  const verdict = validateContract(tampered);
  assert.equal(verdict.ok, false);
  assert.ok(verdict.errors.some((error) => error.path.endsWith("because")));
  assert.throws(() => assertContract(tampered), { code: "invalid-contract" });

  fs.writeFileSync(file, "{not json");
  assert.throws(() => loadContract(file), { code: "contract-unreadable" });
});

test("contract: abandoned runs reopen only with a raised cap, and the stop is recorded", () => {
  const contract = abandon({ ...verified(), max_steps: 1 }, "budget");
  assert.equal(contract.status, "abandoned");
  assert.equal(contract.stops.length, 1);
  assert.throws(() => reopen(contract, { reason: "try again" }), { code: "reopen-no-headroom" });
  const reopened = reopen(contract, { reason: "new evidence", maxSteps: 10 });
  assert.equal(reopened.status, "open");
  assert.equal(reopened.reopens.length, 1);
  assert.equal(reopened.max_steps, 10);
  assert.equal(contractDigest(reopened).length, 16);
});

/* ---- loop ---- */

test("loop: an already-true done condition finishes with zero invented steps", async () => {
  let observations = 0;
  const result = await runLoop({
    contract: emptyContract({ goal: "already green", doneCondition: { cmd: "true" } }),
    checkDone: () => ({ cmd: "true", exit: 0, tail: "" }),
    observe: () => {
      observations += 1;
      return { cmd: "true", exit: 0, tail: "" };
    },
    decide: () => {
      throw new Error("should not decide");
    },
    act: () => {
      throw new Error("should not act");
    },
  });
  assert.equal(result.status, "done");
  assert.equal(result.steps, 0);
  assert.equal(observations, 0);
});

test("loop: a failing check continues, a later passing check finishes after the work", async () => {
  let checks = 0;
  const result = await runLoop({
    contract: emptyContract({ goal: "make it green", doneCondition: { cmd: "check" } }),
    checkDone: () => {
      checks += 1;
      return { cmd: "check", exit: checks === 1 ? 1 : 0, tail: checks === 1 ? "red" : "green" };
    },
    observe: () => ({ cmd: "probe", exit: 1, tail: "red" }),
    decide: ({ observation }) => ({
      considered: [{ action: "wait", why_not: "time is not a fix" }],
      chose: { action: "fix", why: "the probe is red", because: observation.id },
    }),
    act: () => ({ exit: 0, evidence: "green now" }),
  });
  assert.equal(result.status, "done");
  assert.equal(result.steps, 1);
  assert.equal(checks, 2);
  assert.equal(result.contract.done_checks.length, 2);
  assert.equal(result.contract.steps[0].result.ok, true);
});

test("loop: an uncited decision blocks instead of acting, and leaves the observation on disk", async () => {
  const result = await runLoop({
    contract: emptyContract({ goal: "g", doneCondition: { cmd: "true" } }),
    checkDone: () => ({ cmd: "true", exit: 1, tail: "not done" }),
    observe: () => ({ cmd: "probe", exit: 0, tail: "" }),
    decide: () => ({
      considered: [{ action: "wait", why_not: "no" }],
      chose: { action: "act", why: "because", because: "obs-99" },
    }),
    act: () => ({ exit: 0, evidence: "should not run" }),
  });
  assert.equal(result.status, "blocked");
  assert.equal(result.code, "citation-required");
  assert.equal(result.contract.steps.length, 1);
  assert.equal(result.contract.steps[0].chose, null);
});

test("loop: a throwing action is recorded as failed evidence, and the step cap stops the run", async () => {
  const result = await runLoop({
    contract: emptyContract({ goal: "g", doneCondition: { cmd: "true" }, maxSteps: 1 }),
    checkDone: () => ({ cmd: "true", exit: 1, tail: "" }),
    observe: () => ({ cmd: "probe", exit: 0, tail: "" }),
    decide: ({ observation }) => ({
      considered: [{ action: "wait", why_not: "no" }],
      chose: { action: "act", why: "observed", because: observation.id },
    }),
    act: () => {
      throw new Error("tool exploded");
    },
  });
  assert.equal(result.status, "abandoned");
  assert.equal(result.reason, "max-steps");
  assert.match(result.contract.steps[0].result.evidence, /tool exploded/);
  assert.equal(result.contract.steps[0].result.ok, false);
});

test("loop: deadline stops before the done gate and saves the reason", async () => {
  let ticks = 0;
  const result = await runLoop({
    contract: emptyContract({ goal: "g", doneCondition: { cmd: "true" } }),
    checkDone: () => {
      throw new Error("should not reach the check");
    },
    observe: () => ({ cmd: "x", exit: 0 }),
    decide: () => ({}),
    act: () => ({}),
    deadlineMs: 5,
    now: () => {
      ticks += 10;
      return ticks;
    },
  });
  assert.equal(result.status, "abandoned");
  assert.equal(result.reason, "deadline");
  assert.equal(result.contract.stops[0].reason, "deadline");
});

test("loop: resumeLoop reads the contract and shellCheck runs the real command", async () => {
  const dir = tmp();
  const file = path.join(dir, "contract.json");
  let contract = emptyContract({ goal: "shell", doneCondition: { cmd: "exit 0" } });
  saveContract(file, contract);
  const result = await resumeLoop(file, {
    checkDone: shellCheck({ cwd: dir }),
    observe: () => ({ cmd: "true", exit: 0 }),
    decide: () => ({ considered: [{ action: "x", why_not: "y" }], chose: { action: "z", why: "w", because: "obs-1" } }),
    act: () => ({ exit: 0, evidence: "e" }),
  });
  assert.equal(result.status, "done");
  assert.equal(result.contract.done_checks[0].cmd, "exit 0");
  assert.equal(result.contract.done_checks[0].exit, 0);

  const failing = emptyContract({ goal: "shell fail", doneCondition: { cmd: "exit 3" } });
  const check = shellCheck({ cwd: dir })({ contract: failing });
  assert.equal(check.exit, 3);
});

/* ---- grants ---- */

test("grants: paths are confined, including relative and symlink escapes", () => {
  const dir = tmp();
  const inside = path.join(dir, "inside");
  const outside = path.join(dir, "outside");
  fs.mkdirSync(inside);
  fs.mkdirSync(outside);
  fs.writeFileSync(path.join(inside, "ok.txt"), "ok");
  fs.symlinkSync(outside, path.join(inside, "link"));
  const grants = normalizeGrants({ read: [inside], write: [inside] }, { root: dir });

  assert.equal(checkPath(grants, "read", path.join(inside, "ok.txt"), { root: dir }).ok, true);
  assert.equal(checkPath(grants, "write", path.join(inside, "new.txt"), { root: dir }).ok, true);
  assert.equal(checkPath(grants, "write", path.join(inside, "..", "escape.txt"), { root: dir }).ok, false);
  assert.equal(checkPath(grants, "write", path.join(inside, "link", "pwn.txt"), { root: dir }).ok, false);
  assert.equal(checkPath(grants, "write", path.join(outside, "x.txt"), { root: dir }).ok, false);
  assert.equal(checkPath(normalizeGrants({}), "read", path.join(inside, "ok.txt"), { root: dir }).code, "path-not-granted");
  assert.throws(
    () => assertGranted(grants, { kind: "write", path: path.join(outside, "x"), root: dir }),
    { code: "path-outside-grant" },
  );
});

test("grants: commands resolve by real path, network is host+port, spend and wall have caps", () => {
  const dir = tmp();
  const grants = normalizeGrants({
    commands: [NODE],
    hosts: [{ host: "*.example.com", ports: [443] }],
    maxSpendUsd: 2,
    maxWallMs: 1000,
  }, { root: dir });

  assert.equal(resolveProgram(NODE, { root: dir }), resolveProgram(NODE, { root: dir }));
  assert.equal(checkCommand(grants, [NODE, "-e", ""], { root: dir }).ok, true);
  assert.equal(checkCommand(grants, ["/bin/sh"], { root: dir }).code, "command-not-granted");
  assert.equal(checkCommand(grants, ["definitely-not-a-real-binary-xyz"], { root: dir }).code, "command-not-found");
  assert.equal(checkCommand(normalizeGrants({}), [NODE], { root: dir }).code, "command-not-granted");

  assert.equal(checkNetwork(grants, { host: "api.example.com", port: 443 }).ok, true);
  assert.equal(checkNetwork(grants, { host: "example.com", port: 443 }).ok, false);
  assert.equal(checkNetwork(grants, { host: "api.example.com", port: 80 }).ok, false);
  assert.equal(checkNetwork(grants, { host: "evil-example.com", port: 443 }).ok, false);

  assert.equal(checkSpend(grants, { usd: 1.5, spentUsd: 0.5 }).ok, true);
  assert.equal(checkSpend(grants, { usd: 2, spentUsd: 0.5 }).code, "spend-cap");
  assert.equal(checkSpend(normalizeGrants({}), { usd: 1 }).code, "spend-not-granted");
  assert.equal(checkWall(grants, { elapsedMs: 999 }).ok, true);
  assert.equal(checkWall(grants, { elapsedMs: 1001 }).code, "wall-cap");
  assert.throws(() => normalizeGrants({ hosts: ["api.example.com"] }), { code: "network-ports-required" });
  assert.throws(() => assertGranted(grants, { kind: "telepathy" }), { code: "unknown-grant-kind" });
});

test("grants: composition narrows only; any widening throws", () => {
  const dir = tmp();
  const inside = path.join(dir, "inside");
  const sub = path.join(inside, "sub");
  const outside = path.join(dir, "outside");
  fs.mkdirSync(sub, { recursive: true });
  fs.mkdirSync(outside, { recursive: true });
  const parent = normalizeGrants({
    write: [inside],
    commands: [NODE],
    hosts: [{ host: "*.example.com", ports: [443, 8443] }],
    maxSpendUsd: 5,
    maxWallMs: 1000,
  }, { root: dir });

  const child = narrowGrants(parent, {
    write: [sub],
    commands: [NODE],
    hosts: [{ host: "api.example.com", ports: [443] }],
    maxSpendUsd: 2,
    maxWallMs: 500,
  }, { root: dir });
  assert.deepEqual(child.write, [fs.realpathSync(sub)]);
  assert.equal(child.maxSpendUsd, 2);
  assert.equal(narrowGrants(parent, {}, { root: dir }).maxSpendUsd, 5);

  assert.throws(() => narrowGrants(parent, { write: [outside] }, { root: dir }), { code: "grant-widening" });
  assert.throws(() => narrowGrants(parent, { commands: ["/bin/sh"] }, { root: dir }), { code: "grant-widening" });
  assert.throws(() => narrowGrants(parent, { hosts: [{ host: "api.other.com", ports: [443] }] }, { root: dir }), { code: "grant-widening" });
  assert.throws(() => narrowGrants(parent, { hosts: [{ host: "api.example.com", ports: [80] }] }, { root: dir }), { code: "grant-widening" });
  assert.throws(() => narrowGrants(parent, { maxSpendUsd: 6 }, { root: dir }), { code: "grant-widening" });
  assert.throws(() => narrowGrants(parent, { maxWallMs: 2000 }, { root: dir }), { code: "grant-widening" });
});

test("grants: guarded tools refuse before the write or the process happens", () => {
  const dir = tmp();
  const inside = path.join(dir, "inside");
  const outside = path.join(dir, "outside");
  fs.mkdirSync(inside);
  fs.mkdirSync(outside);
  const grants = normalizeGrants({ write: [inside], commands: [NODE] }, { root: dir });

  assert.equal(guardedWrite(grants, path.join(inside, "a.txt"), "ok", { root: dir }), 2);
  assert.equal(fs.readFileSync(path.join(inside, "a.txt"), "utf8"), "ok");
  guardedAppend(grants, path.join(inside, "a.txt"), "!", { root: dir });
  assert.equal(fs.readFileSync(path.join(inside, "a.txt"), "utf8"), "ok!");

  assert.throws(() => guardedWrite(grants, path.join(outside, "pwn.txt"), "no", { root: dir }), {
    code: "path-outside-grant",
  });
  assert.equal(fs.existsSync(path.join(outside, "pwn.txt")), false);

  const ran = guardedExec(grants, [NODE, "-e", "process.stdout.write('hi')"], { root: dir });
  assert.equal(ran.exit, 0);
  assert.equal(ran.stdout, "hi");
  const failed = guardedExec(grants, [NODE, "-e", "process.exit(3)"], { root: dir });
  assert.equal(failed.exit, 3);
  assert.throws(() => guardedExec(grants, ["/bin/sh", "-c", "true"], { root: dir }), {
    code: "command-not-granted",
  });
});

/* ---- dead ends ---- */

test("dead ends: recorded once, refused on retry, override recorded, torn lines skipped", () => {
  const dir = tmp();
  const task = "Fix  the Flaky Clipboard Test";
  const first = recordDeadEnd(dir, {
    task,
    approach: "add a sleep",
    why_failed: "the race moved",
    evidence: "run 7 of 20 still failed",
  });
  assert.equal(first.recorded, true);
  assert.equal(taskSignature(task), taskSignature("fix the flaky clipboard test"));
  const duplicate = recordDeadEnd(dir, {
    task: "fix the flaky clipboard test",
    approach: "Add a  Sleep",
    why_failed: "again",
    evidence: "again",
  });
  assert.equal(duplicate.duplicate, true);
  assert.equal(findDeadEnd(dir, { task, approach: "add a sleep" }).why_failed, "the race moved");
  assert.equal(deadEnds(dir, { task }).entries.length, 1);
  assert.throws(() => assertFresh(dir, { task, approach: "add a sleep" }), { code: "known-dead-end" });
  const override = assertFresh(dir, { task, approach: "add a sleep", override: "the race is now elsewhere" });
  assert.equal(override.override, true);
  assert.equal(deadEndStats(dir).overrides, 1);
  assert.match(renderDeadEnds(dir, { task }), /add a sleep/);

  fs.appendFileSync(path.join(dir, "deadends.jsonl"), "{torn\n");
  assert.equal(deadEndStats(dir).torn, 1);
  assert.throws(() => recordDeadEnd(dir, { task, approach: "x", why_failed: "y", evidence: "" }), { code: "evidence-required" });
});

/* ---- lessons applied ---- */

test("learning: applied lessons are counted by lesson and agent, and untouched lessons are visible", () => {
  const dir = tmp();
  const taught = JSON.parse(teach(dir, "rowan", "verify the tree, not the branch"));
  assert.equal(taught.agent, "rowan");
  const key = taught.ts;
  recordApplied(dir, { agent: "milo", lesson: key, outcome: "used", run: "milo-1" });
  recordApplied(dir, { agent: "pax", lesson: taught, outcome: "partial" });
  assert.equal(appliedCounts(dir)[key], 2);
  assert.equal(appliedByAgent(dir).milo, 1);
  assert.equal(lessonBoard(dir)[0].applied, 2);
  assert.equal(untouchedLessons(dir).length, 0);
  assert.throws(() => recordApplied(dir, { agent: "milo", lesson: key, outcome: "vibes" }), { code: "outcome-invalid" });
  fs.appendFileSync(path.join(dir, "lesson-applied.jsonl"), "torn\n");
  assert.equal(learningHealth(dir).torn, 1);
  assert.equal(appliedCounts(dir)[key], 2);
});

/* ---- continue ---- */

test("continue: request validates, claims exactly once, and carries the next order", () => {
  const dir = tmp();
  const request = writeContinue(dir, {
    reason: "half the wall is up",
    next: "finish the west wall",
    baton: { stepIndex: 1, state: "west wall half built", nextStep: "finish" },
  });
  assert.equal(request.outcome, "continue");
  assert.equal(readContinue(dir).next, "finish the west wall");

  const job = continueJob({
    job: { id: "wall", agent: "mason", maxContinues: 2 },
    runId: "mason-abc",
    request,
    cycles: 0,
  });
  assert.match(job.id, /^wall~c1-mason-abc$/);
  assert.match(job.orders, /finish the west wall/);
  assert.equal(job.continueCycles, 1);

  const first = claimContinue(dir);
  assert.equal(first.request.next, "finish the west wall");
  assert.equal(claimContinue(dir), null);
  assert.equal(readContinue(dir), null);
  assert.equal(fs.readdirSync(dir).filter((file) => file.startsWith("continue.claimed.")).length, 1);
});

test("continue: malformed requests are refused, and every bound wins before a new job", () => {
  const dir = tmp();
  fs.writeFileSync(path.join(dir, CONTINUE_FILE), "{bad json");
  assert.throws(() => readContinue(dir), { code: "continue-malformed" });
  assert.throws(() => writeContinue(dir, { reason: "", next: "x" }), { code: "continue-malformed" });

  const good = tmp();
  writeContinue(good, { reason: "more", next: "next" });
  assert.equal(continueDecision(good, { cycles: 0, maxContinues: 2, exitCode: 0 }).continue, true);
  assert.equal(continueDecision(good, { cycles: 2, maxContinues: 2, exitCode: 0 }).reason, "continue-cap");
  assert.equal(continueDecision(good, { cycles: 0, maxContinues: 2, exitCode: 1 }).reason, "nonzero-exit");
  assert.equal(continueDecision(good, { cycles: 0, maxContinues: 2, exitCode: 0, maxWallMs: 100, elapsedMs: 100 }).reason, "wall-cap");
  assert.equal(continueDecision(good, { cycles: 0, maxContinues: 2, exitCode: 0, maxCostUsd: 1, costUsd: 1 }).reason, "cost-cap");
  fs.writeFileSync(path.join(good, "STOP"), "");
  assert.equal(continueDecision(good, { cycles: 0, maxContinues: 2, exitCode: 0 }).reason, "stop-file");
  assert.equal(continueDecision(tmp(), { cycles: 0 }).reason, "no-request");

  const jobs = path.join(good, "jobs");
  const job = continueJob({ job: { id: "j", agent: "a" }, runId: "r", request: { outcome: "continue", reason: "x", next: "y" } });
  assert.equal(writeContinueJob(jobs, job).changed, true);
  assert.equal(writeContinueJob(jobs, job).changed, false);
});

test("watchman: a continue request queues one new job, then the cap refuses the next", async () => {
  const dir = tmp();
  const script = "const fs=require('fs');fs.writeFileSync('continue.json',JSON.stringify({outcome:'continue',reason:'more work',next:'second slice'}))";
  const registry = path.join(dir, "registry.json");
  fs.writeFileSync(registry, JSON.stringify({
    agents: [{ name: "continuer", lane: "test", command: [NODE, "-e", script], budget: {} }],
  }));
  const jobsDir = path.join(dir, "jobs");
  const watchman = createWatchman({ registryFile: registry, root: dir, jobsDir });

  fs.writeFileSync(path.join(jobsDir, "j.job.json"), JSON.stringify({
    id: "j", agent: "continuer", orders: "start", maxContinues: 1,
  }));
  const first = await watchman.pollOnce();
  assert.equal(first.length, 1);
  await first[0].handle.done;
  assert.ok(await until(() => watchman.ledger.read().some((line) => line.event === "continue-queued")), "no continue-queued");

  const second = await watchman.pollOnce();
  assert.equal(second.length, 1);
  assert.match(second[0].id, /^j~c1-/);
  await second[0].handle.done;
  assert.ok(await until(() => watchman.ledger.read().some((line) => line.event === "continue-refused")), "no continue-refused");
  const refused = watchman.ledger.read().find((line) => line.event === "continue-refused");
  assert.equal(refused.reason, "continue-cap");

  const third = await watchman.pollOnce();
  assert.equal(third.length, 0);
  const result = JSON.parse(fs.readFileSync(path.join(jobsDir, "j~c1-" + first[0].handle.runId + ".result.json"), "utf8"));
  assert.equal(result.continue.requested, true);
  assert.equal(result.continue.queued, false);
});

/* ---- drills ---- */

test("judgment drills: every drill passes", async () => {
  const result = await runJudgmentDrills({ root: tmp() });
  const failures = result.drills.filter((drill) => drill.score !== drill.max);
  assert.deepEqual(failures, []);
  assert.equal(result.ok, true);
  assert.equal(result.total, result.max);
});

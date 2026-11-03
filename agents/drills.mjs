// Meta OS agent layer — judgment drills (AGENTIC build order, item 5).
//
// The existing gym proves an agent can be spawned and its ledger read. That is plumbing.
// These drills test judgment: a goal whose condition is already true, action that succeeds
// for the wrong reason, a decision with no observation, a retry of a recorded dead end, a
// write outside the grant, a continue with no headroom.
//
// Run: node agents/drills.mjs        (exit 1 if any drill fails)
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import url from "node:url";
import {
  ContractError,
  assertContract,
  canFinish,
  emptyContract,
  finish,
  recordDecision,
  recordObservation,
  recordResult,
  validateContract,
} from "./contract.mjs";
import { runLoop } from "./loop.mjs";
import { assertGranted, checkPath, narrowGrants, normalizeGrants } from "./grants.mjs";
import { assertFresh, recordDeadEnd } from "./deadends.mjs";
import { recordApplied, appliedCounts } from "./learning.mjs";
import { continueDecision, writeContinue } from "./continue.mjs";
import { proposeJob } from "./jobs.mjs";

function must(condition, message) {
  if (!condition) throw new Error(message);
}

function mustCode(fn, code) {
  try {
    fn();
  } catch (error) {
    must(error.code === code, "expected code " + code + ", got " + (error && error.code));
    return error;
  }
  throw new Error("expected a refusal with code " + code + ", but the call succeeded");
}

function verifiedContract() {
  let contract = emptyContract({ goal: "drill", doneCondition: { cmd: "drill-done" } });
  contract = recordObservation(contract, { cmd: "drill-observe", exit: 1, tail: "not yet" });
  contract = recordDecision(contract, {
    considered: [{ action: "wait", why_not: "time is not a fix" }],
    chose: { action: "work", why: "the observation says work is missing", because: "obs-1" },
  });
  contract = recordResult(contract, { exit: 0, evidence: "work produced the artifact" });
  return contract;
}

export const JUDGMENT_DRILLS = [
  {
    id: "already-true",
    what: "a goal whose done condition is already true finishes without inventing a step",
    async run() {
      const contract = emptyContract({ goal: "nothing to do", doneCondition: { cmd: "true" } });
      let observations = 0;
      const result = await runLoop({
        contract,
        checkDone: () => ({ cmd: "true", exit: 0, tail: "" }),
        observe: () => {
          observations += 1;
          return { cmd: "true", exit: 0, tail: "" };
        },
        decide: () => {
          throw new Error("decided before any work was needed");
        },
        act: () => {
          throw new Error("acted before any work was needed");
        },
        maxSteps: 3,
      });
      must(result.status === "done", "expected done, got " + result.status);
      must(result.contract.steps.length === 0, "invented " + result.contract.steps.length + " steps");
      must(observations === 0, "observed " + observations + " times for an already-true goal");
    },
  },
  {
    id: "decision-before-observation",
    what: "a decision cannot be recorded before an observation exists",
    async run() {
      const contract = emptyContract({ goal: "g", doneCondition: { cmd: "true" } });
      mustCode(
        () =>
          recordDecision(contract, {
            considered: [{ action: "x", why_not: "y" }],
            chose: { action: "z", why: "w", because: "obs-1" },
          }),
        "no-open-step",
      );
    },
  },
  {
    id: "uncited-decision",
    what: "a decision that does not cite this step's observation is refused",
    async run() {
      let contract = emptyContract({ goal: "g", doneCondition: { cmd: "true" } });
      contract = recordObservation(contract, { cmd: "look", exit: 1, tail: "" });
      mustCode(
        () =>
          recordDecision(contract, {
            considered: [{ action: "x", why_not: "y" }],
            chose: { action: "z", why: "w", because: "obs-99" },
          }),
        "citation-required",
      );
    },
  },
  {
    id: "done-not-run",
    what: "a verified step is not a finished run; the done condition must actually execute",
    async run() {
      const contract = verifiedContract();
      must(canFinish(contract).code === "done-not-run", "gate did not name done-not-run");
      mustCode(() => finish(contract), "done-not-run");
    },
  },
  {
    id: "stale-done-check",
    what: "a done check that passed before the last step closed cannot finish the run",
    async run() {
      const contract = verifiedContract();
      const withCheck = {
        ...contract,
        done_checks: [{ cmd: "drill-done", exit: 0, tail: "", at: "2000-01-01T00:00:00.000Z", seq: 0 }],
      };
      mustCode(() => finish(withCheck), "done-stale");
    },
  },
  {
    id: "wrong-reason",
    what: "an action that exits 0 does not finish a run whose done condition fails",
    async run() {
      const contract = emptyContract({ goal: "green but wrong", doneCondition: { cmd: "truth" }, maxSteps: 2 });
      let actions = 0;
      const result = await runLoop({
        contract,
        checkDone: () => ({ cmd: "truth", exit: 1, tail: "still broken" }),
        observe: () => ({ cmd: "probe", exit: 0, tail: "" }),
        decide: ({ observation }) => ({
          considered: [{ action: "declare victory", why_not: "the check still fails" }],
          chose: { action: "patch the symptom", why: "the probe is green", because: observation.id },
        }),
        act: () => {
          actions += 1;
          return { exit: 0, evidence: "command said ok" };
        },
        maxSteps: 2,
      });
      must(actions === 2, "expected the loop to keep working, acted " + actions + " times");
      must(result.status === "abandoned", "expected abandoned, got " + result.status);
      must(result.reason === "max-steps", "expected max-steps, got " + result.reason);
      must(result.contract.status === "abandoned", "contract did not record the stop");
    },
  },
  {
    id: "known-dead-end",
    what: "a recorded dead end cannot be retried silently, and an override is recorded",
    async run({ root }) {
      const dir = fs.mkdtempSync(path.join(root, "deadend-"));
      const task = "fix the flaky clipboard test";
      recordDeadEnd(dir, {
        task,
        approach: "add a sleep",
        why_failed: "the race moved, it did not close",
        evidence: "failed on run 7 of 20 with the sleep",
      });
      mustCode(() => assertFresh(dir, { task, approach: "add a sleep" }), "known-dead-end");
      const override = assertFresh(dir, { task, approach: "add a sleep", override: "the race is now a different one" });
      must(override.override === true, "override was not recorded");
    },
  },
  {
    id: "grant-escape",
    what: "a write outside the granted root is refused, including through a symlink",
    async run({ root }) {
      const dir = fs.mkdtempSync(path.join(root, "grant-"));
      const inside = path.join(dir, "inside");
      const outside = path.join(dir, "outside");
      fs.mkdirSync(inside);
      fs.mkdirSync(outside);
      fs.symlinkSync(outside, path.join(inside, "link"));
      const grants = normalizeGrants({ write: [inside] }, { root: dir });
      must(checkPath(grants, "write", path.join(inside, "ok.txt"), { root: dir }).ok === true, "inside write refused");
      must(
        checkPath(grants, "write", path.join(inside, "..", "escape.txt"), { root: dir }).ok === false,
        "relative escape allowed",
      );
      must(
        checkPath(grants, "write", path.join(inside, "link", "pwn.txt"), { root: dir }).ok === false,
        "symlink escape allowed",
      );
      mustCode(
        () => assertGranted(grants, { kind: "write", path: path.join(outside, "x"), root: dir }),
        "path-outside-grant",
      );
      mustCode(
        () => narrowGrants(grants, { write: [outside] }, { root: dir }),
        "grant-widening",
      );
    },
  },
  {
    id: "continue-cap",
    what: "a continue request past its cycle cap is refused and stays refused",
    async run({ root }) {
      const dir = fs.mkdtempSync(path.join(root, "continue-"));
      writeContinue(dir, { reason: "more to do", next: "next slice", baton: { stepIndex: 0 } });
      const allowed = continueDecision(dir, { cycles: 0, maxContinues: 2, exitCode: 0 });
      must(allowed.continue === true, "a fresh continue was refused: " + allowed.reason);
      const capped = continueDecision(dir, { cycles: 2, maxContinues: 2, exitCode: 0 });
      must(capped.continue === false && capped.reason === "continue-cap", "cap did not win");
      const nonzero = continueDecision(dir, { cycles: 0, maxContinues: 2, exitCode: 1 });
      must(nonzero.continue === false && nonzero.reason === "nonzero-exit", "nonzero exit did not win");
    },
  },
  {
    id: "lesson-accounting",
    what: "applying a lesson is recorded and counted, not assumed",
    async run({ root }) {
      const dir = fs.mkdtempSync(path.join(root, "learning-"));
      recordApplied(dir, { agent: "rowan", lesson: { ts: "2026-01-01T00:00:00.000Z" }, outcome: "used" });
      recordApplied(dir, { agent: "milo", lesson: "2026-01-01T00:00:00.000Z", outcome: "refuted" });
      const counts = appliedCounts(dir);
      must(counts["2026-01-01T00:00:00.000Z"] === 2, "count was " + counts["2026-01-01T00:00:00.000Z"]);
    },
  },
  {
    id: "self-tasking",
    what: "a finished run can order its own next job once, and cannot echo or exceed the limit",
    async run({ root }) {
      const dir = fs.mkdtempSync(path.join(root, "propose-"));
      const jobs = path.join(dir, "jobs");
      fs.mkdirSync(jobs);
      fs.writeFileSync(
        path.join(jobs, "d1.job.json"),
        JSON.stringify({ id: "d1", agent: "watch", orders: "sweep the first shelf" }),
      );
      const first = proposeJob({ root: dir, id: "d1", runId: "run-1", next: "sweep the second shelf" });
      must(first.ok === true, "a clean finish could not propose: " + first.reason);
      const landed = JSON.parse(fs.readFileSync(path.join(jobs, first.id + ".job.json"), "utf8"));
      must(landed.orders === "sweep the second shelf", "the order was not carried");
      must(landed.agent === "watch", "the proposal went to another agent");

      const echo = proposeJob({ root: dir, id: "d1", runId: "run-2", next: "sweep the first shelf" });
      must(echo.ok === false && echo.reason === "proposal-echo", "an echo was allowed: " + echo.reason);
      const capped = proposeJob({ root: dir, id: first.id, runId: "run-3", next: "sweep the third shelf" });
      must(capped.ok === false && capped.reason === "proposal-limit", "the one-hop cap did not hold: " + capped.reason);
    },
  },
  {
    id: "tampered-contract",
    what: "a contract whose decision cites a different observation fails validation",
    async run() {
      const contract = verifiedContract();
      const tampered = {
        ...contract,
        steps: [{ ...contract.steps[0], chose: { ...contract.steps[0].chose, because: "obs-9" } }],
      };
      const verdict = validateContract(tampered);
      must(verdict.ok === false, "tampered contract validated");
      mustCode(() => assertContract(tampered), "invalid-contract");
    },
  },
];

export async function runJudgmentDrills({ root = null } = {}) {
  const workRoot = root || fs.mkdtempSync(path.join(os.tmpdir(), "agentic-drills-"));
  fs.mkdirSync(workRoot, { recursive: true });
  const drills = [];
  for (const drill of JUDGMENT_DRILLS) {
    try {
      await drill.run({ root: workRoot });
      drills.push({ id: drill.id, what: drill.what, score: 1, max: 1, detail: "ok" });
    } catch (error) {
      drills.push({
        id: drill.id,
        what: drill.what,
        score: 0,
        max: 1,
        detail: String((error && error.stack) || error),
      });
    }
  }
  const total = drills.reduce((sum, drill) => sum + drill.score, 0);
  const max = drills.reduce((sum, drill) => sum + drill.max, 0);
  return { drills, total, max, ok: total === max, root: workRoot };
}

export function renderDrills(result) {
  const lines = result.drills.map(
    (drill) => (drill.score === drill.max ? "PASS " : "FAIL ") + drill.id.padEnd(28) + " " + drill.what,
  );
  lines.push("total " + result.total + "/" + result.max);
  if (!result.ok) {
    for (const drill of result.drills) {
      if (drill.score !== drill.max) lines.push("--- " + drill.id + " ---\n" + drill.detail);
    }
  }
  return lines.join("\n");
}

const HERE = path.dirname(url.fileURLToPath(import.meta.url));
if (process.argv[1] && path.resolve(process.argv[1]) === path.resolve(url.fileURLToPath(import.meta.url))) {
  const result = await runJudgmentDrills({ root: path.join(HERE, "..", "runs", "drills") });
  console.log(renderDrills(result));
  if (!result.ok) process.exit(1);
}

// Keep the ContractError import meaningful for callers that catch by class; the drills
// themselves assert on machine-readable codes so a message change cannot make one pass.
void ContractError;

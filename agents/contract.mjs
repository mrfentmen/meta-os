// Meta OS agent layer — the run contract (AGENTIC build order, item 1).
//
// An agent is a loop, not a model with tools. This file is the loop's schema: a step may not
// act without an observation, may not choose without citing that observation, may not close
// without evidence, and may not call itself done unless the done-condition was actually
// executed after the last step. The contract is the artifact the runtime gates on; prose
// cannot satisfy it, and a lie in it is detectable by validateContract().
//
// Shape:
//   {
//     version: 1,
//     goal: "fix the flaky clipboard test",
//     done_condition: { cmd: "python3 -m unittest tests.test_clipboard", expect_exit: 0 },
//     max_steps: 50,
//     status: "open" | "done" | "abandoned",
//     steps: [{
//       id: "s1",
//       observation: { id: "obs-1", cmd: "...", exit: 1, tail: "FAIL on run 7 of 20", at: "..." },
//       considered: [{ action: "add a sleep", why_not: "hides the race, does not close it" }],
//       chose: { action: "add a barrier", why: "...", because: "obs-1" },
//       result: { exit: 0, ok: true, evidence: "...", at: "..." },
//       plan_revision: null,
//       lessons_applied: [],
//       opened_at: "...", closed_at: "..."
//     }],
//     done_checks: [{ cmd, exit, tail, at }],
//     revisions: [], stops: [], reopens: []
//   }
import fs from "node:fs";
import crypto from "node:crypto";
import { writeFileLoud } from "./safe-write.mjs";

export const CONTRACT_VERSION = 1;
export const CONTRACT_STATUSES = ["open", "done", "abandoned"];
const MAX_TAIL = 4000;

export class ContractError extends Error {
  constructor(code, message, detail = {}) {
    super(message);
    this.name = "ContractError";
    this.code = code;
    for (const [k, v] of Object.entries(detail)) if (!(k in this)) this[k] = v;
  }
}

function isText(value) {
  return typeof value === "string" && value.trim().length > 0;
}

function now() {
  return new Date().toISOString();
}

function tail(text) {
  const s = String(text == null ? "" : text);
  if (s.length <= MAX_TAIL) return s;
  return s.slice(s.length - MAX_TAIL) + "\n[tail truncated: " + (s.length - MAX_TAIL) + " earlier chars]";
}

function touch(contract) {
  const seq = (Number.isInteger(contract.seq) ? contract.seq : 0) + 1;
  return { ...contract, seq, updated_at: now() };
}

// The only step that may be open is the last one. A contract that somehow carries an open
// step in the middle is not resumed; validateContract() names it.
export function openStep(contract) {
  if (!contract || !Array.isArray(contract.steps) || contract.steps.length === 0) return null;
  const last = contract.steps[contract.steps.length - 1];
  return last && last.result == null ? last : null;
}

function assertOpen(contract) {
  if (!contract || typeof contract !== "object") {
    throw new ContractError("contract-required", "contract: an object is required");
  }
  if (contract.status !== "open") {
    throw new ContractError("contract-not-open", "contract: status is " + contract.status + ", not open");
  }
}

function requireOpenStep(contract) {
  const step = openStep(contract);
  if (!step) {
    throw new ContractError(
      "no-open-step",
      "contract: no step is open — record an observation before deciding or acting",
    );
  }
  return step;
}

export function emptyContract({ goal, doneCondition, maxSteps = 50, created = null } = {}) {
  if (!isText(goal)) throw new ContractError("goal-required", "contract: a non-empty goal is required");
  const condition = doneCondition || {};
  if (!isText(condition.cmd)) {
    throw new ContractError(
      "done-condition-required",
      "contract: a done condition command is required — a goal without a check is a wish",
    );
  }
  const expectExit = condition.expectExit == null ? 0 : condition.expectExit;
  if (!Number.isInteger(expectExit)) {
    throw new ContractError("done-condition-invalid", "contract: done condition expectExit must be an integer");
  }
  if (!Number.isInteger(maxSteps) || maxSteps < 1) {
    throw new ContractError("max-steps-invalid", "contract: maxSteps must be a positive integer");
  }
  const at = created || now();
  return {
    version: CONTRACT_VERSION,
    goal: goal.trim(),
    done_condition: { cmd: condition.cmd.trim(), expect_exit: expectExit },
    max_steps: maxSteps,
    status: "open",
    steps: [],
    done_checks: [],
    revisions: [],
    stops: [],
    reopens: [],
    seq: 0,
    created_at: at,
    updated_at: at,
  };
}

// Observation opens a step. It is the FIRST write in the step on purpose: nothing may be
// decided about a state that was not looked at.
export function recordObservation(contract, observation) {
  assertOpen(contract);
  if (!observation || !isText(observation.cmd)) {
    throw new ContractError("observation-required", "observation: a command is required");
  }
  const alreadyOpen = openStep(contract);
  if (alreadyOpen) {
    throw new ContractError(
      "step-open",
      "observation: step " + alreadyOpen.id + " has no result yet — close it before observing again",
      { step: alreadyOpen.id },
    );
  }
  if (contract.steps.length >= contract.max_steps) {
    throw new ContractError(
      "max-steps",
      "observation: the contract's " + contract.max_steps + "-step cap is reached; raising it is a visible edit, not a silent retry",
      { maxSteps: contract.max_steps },
    );
  }
  if (observation.exit != null && !Number.isInteger(observation.exit)) {
    throw new ContractError("observation-invalid", "observation: exit must be an integer or null");
  }

  const index = contract.steps.length + 1;
  const at = now();
  const step = {
    id: "s" + index,
    observation: {
      id: "obs-" + index,
      cmd: observation.cmd,
      exit: observation.exit == null ? null : observation.exit,
      tail: tail(observation.tail),
      at,
    },
    considered: [],
    chose: null,
    result: null,
    plan_revision: null,
    lessons_applied: [],
    opened_at: at,
    closed_at: null,
  };
  return touch({ ...contract, steps: [...contract.steps, step] });
}

// A decision names the action NOT taken and why, the action taken and why, and the
// observation that justifies it. `because` is an observation id, not an adjective.
export function recordDecision(contract, decision) {
  assertOpen(contract);
  const step = requireOpenStep(contract);
  if (!step.observation) {
    throw new ContractError("observation-required", "decision: the step has no observation");
  }
  if (step.chose) {
    throw new ContractError("decision-recorded", "decision: step " + step.id + " already has a decision");
  }
  const considered = decision && decision.considered;
  if (!Array.isArray(considered) || considered.length === 0) {
    throw new ContractError(
      "alternatives-required",
      "decision: at least one rejected alternative is required — a choice with no alternative is a reflex",
    );
  }
  const seen = new Set();
  for (const alternative of considered) {
    if (!alternative || !isText(alternative.action) || !isText(alternative.why_not)) {
      throw new ContractError("alternative-invalid", "decision: every alternative needs action and why_not");
    }
    const key = alternative.action.trim().toLowerCase();
    if (seen.has(key)) {
      throw new ContractError("alternative-duplicate", "decision: alternative listed twice: " + alternative.action);
    }
    seen.add(key);
  }

  const chose = decision.chose;
  if (!chose || !isText(chose.action) || !isText(chose.why)) {
    throw new ContractError("choice-required", "decision: chose.action and chose.why are required");
  }
  if (seen.has(chose.action.trim().toLowerCase())) {
    throw new ContractError(
      "contradictory-decision",
      "decision: the chosen action was also listed as rejected: " + chose.action,
    );
  }
  if (chose.because !== step.observation.id) {
    throw new ContractError(
      "citation-required",
      "decision: chose.because must name this step's observation (" + step.observation.id + "), got " + JSON.stringify(chose.because),
      { expected: step.observation.id },
    );
  }

  const nextStep = {
    ...step,
    considered: considered.map((a) => ({ action: a.action.trim(), why_not: a.why_not.trim() })),
    chose: {
      action: chose.action.trim(),
      why: chose.why.trim(),
      because: chose.because,
      decided_at: now(),
    },
  };
  return touch({ ...contract, steps: [...contract.steps.slice(0, -1), nextStep] });
}

// Result closes the step. A failed result is a valid close: the next observation is the
// retry. What is refused is closing with no evidence at all.
export function recordResult(contract, result) {
  assertOpen(contract);
  const step = requireOpenStep(contract);
  if (!step.chose) {
    throw new ContractError("decision-required", "result: step " + step.id + " has no recorded decision");
  }
  if (step.result) {
    throw new ContractError("result-recorded", "result: step " + step.id + " is already closed");
  }
  if (!result || !isText(result.evidence)) {
    throw new ContractError("evidence-required", "result: evidence is required — an action with no output is unverified");
  }
  if (result.exit != null && !Number.isInteger(result.exit)) {
    throw new ContractError("result-invalid", "result: exit must be an integer or null");
  }
  const exit = result.exit == null ? null : result.exit;
  const ok = result.ok === undefined ? exit === 0 : result.ok === true;
  const at = now();
  const closedSeq = (Number.isInteger(contract.seq) ? contract.seq : 0) + 1;
  const nextStep = {
    ...step,
    result: { exit, ok, evidence: tail(result.evidence), at, closed_seq: closedSeq },
    closed_at: at,
  };
  return touch({ ...contract, steps: [...contract.steps.slice(0, -1), nextStep] });
}

// A plan revision is a record, not a mood: it names what changed and which observation
// forced the change.
export function recordPlanRevision(contract, revision) {
  assertOpen(contract);
  if (!revision || !isText(revision.from) || !isText(revision.to) || revision.from.trim() === revision.to.trim()) {
    throw new ContractError("plan-revision-invalid", "plan: from and to must be different, non-empty plans");
  }
  if (!isText(revision.because)) {
    throw new ContractError("citation-required", "plan: because must name the observation that forced the revision");
  }
  const observationIds = contract.steps
    .map((s) => (s.observation && s.observation.id) || null)
    .filter(Boolean);
  if (!observationIds.includes(revision.because)) {
    throw new ContractError(
      "citation-required",
      "plan: because must name an observation in this contract, got " + JSON.stringify(revision.because),
      { observations: observationIds },
    );
  }
  const entry = {
    from: revision.from.trim(),
    to: revision.to.trim(),
    because: revision.because,
    step: contract.steps.length ? contract.steps[contract.steps.length - 1].id : null,
    at: now(),
  };
  const steps = contract.steps.length
    ? [
        ...contract.steps.slice(0, -1),
        { ...contract.steps[contract.steps.length - 1], plan_revision: entry },
      ]
    : contract.steps;
  return touch({ ...contract, steps, revisions: [...contract.revisions, entry] });
}

// A lesson cited by a step is attached to that step, not left in a brief. Duplicates are
// refused: two records of the same lesson on one decision would make the count a fiction.
export function recordLessonApplied(contract, { lesson, outcome = "used" } = {}) {
  assertOpen(contract);
  if (!isText(lesson)) throw new ContractError("lesson-required", "lesson: a lesson id is required");
  if (!["used", "refuted", "partial"].includes(outcome)) {
    throw new ContractError("lesson-outcome-invalid", "lesson: outcome must be used, refuted or partial");
  }
  if (contract.steps.length === 0) {
    throw new ContractError("no-step", "lesson: a lesson attaches to a decision step; observe first");
  }
  const step = contract.steps[contract.steps.length - 1];
  const existing = Array.isArray(step.lessons_applied) ? step.lessons_applied : [];
  const key = (entry) => (typeof entry === "string" ? entry : entry && entry.lesson);
  const wanted = lesson.trim();
  if (existing.some((entry) => key(entry) === wanted)) {
    throw new ContractError("lesson-duplicate", "lesson: " + wanted + " is already recorded on " + step.id);
  }
  const entry = { lesson: wanted, outcome, at: now() };
  const steps = [
    ...contract.steps.slice(0, -1),
    { ...step, lessons_applied: [...existing, entry] },
  ];
  return touch({ ...contract, steps });
}

// The done check is recorded with the command that ACTUALLY ran. A wrapper that reports a
// different command than the contract's is kept in the record and refused at finish time;
// rewriting it to look expected would defeat the gate.
export function recordDoneCheck(contract, check) {
  assertOpen(contract);
  if (!check || !isText(check.cmd)) {
    throw new ContractError("done-check-invalid", "done: a command is required");
  }
  if (!Number.isInteger(check.exit)) {
    throw new ContractError("done-check-invalid", "done: exit must be an integer");
  }
  const entry = {
    cmd: check.cmd,
    exit: check.exit,
    tail: tail(check.tail),
    at: now(),
    seq: (Number.isInteger(contract.seq) ? contract.seq : 0) + 1,
  };
  return touch({ ...contract, done_checks: [...contract.done_checks, entry] });
}

// The gate, without throwing, so a caller can report WHY it is not done.
export function canFinish(contract) {
  if (!contract || typeof contract !== "object") {
    return { ok: false, code: "contract-required", reason: "no contract" };
  }
  if (contract.status === "done") return { ok: true, code: "already-done", reason: null };
  if (contract.status !== "open") {
    return { ok: false, code: "contract-not-open", reason: "status is " + contract.status };
  }
  const step = openStep(contract);
  if (step) return { ok: false, code: "step-open", reason: "step " + step.id + " has no result", step: step.id };
  if (!contract.steps.every((s) => s.chose && s.result)) {
    return { ok: false, code: "step-unverified", reason: "a step is missing its decision or result" };
  }
  const last = contract.steps[contract.steps.length - 1];
  const check = contract.done_checks[contract.done_checks.length - 1];
  if (!check) {
    return { ok: false, code: "done-not-run", reason: "the done condition has not been executed in this run" };
  }
  if (check.cmd !== contract.done_condition.cmd) {
    return {
      ok: false,
      code: "done-command-mismatch",
      reason: "the recorded check ran a different command than the contract",
      expected: contract.done_condition.cmd,
      ran: check.cmd,
    };
  }
  if (last && (!Number.isInteger(check.seq) || !Number.isInteger(last.result.closed_seq))) {
    return {
      ok: false,
      code: "done-stale",
      reason: "the order of the last step and the done check cannot be proven; re-run the done condition",
    };
  }
  if (last && check.seq <= last.result.closed_seq) {
    return {
      ok: false,
      code: "done-stale",
      reason: "the done condition passed before the last step closed; it must be re-run after",
    };
  }
  if (check.exit !== contract.done_condition.expect_exit) {
    return {
      ok: false,
      code: "done-failed",
      reason: "the done condition exited " + check.exit + ", expected " + contract.done_condition.expect_exit,
      exit: check.exit,
      expected: contract.done_condition.expect_exit,
    };
  }
  return { ok: true, code: "done", reason: null };
}

export function finish(contract) {
  const verdict = canFinish(contract);
  if (!verdict.ok) {
    throw new ContractError(verdict.code, "finish refused: " + verdict.reason, verdict);
  }
  if (contract.status === "done") return contract;
  const at = now();
  return touch({
    ...contract,
    status: "done",
    finished_at: at,
    done_evidence: contract.done_checks[contract.done_checks.length - 1],
  });
}

export function abandon(contract, reason) {
  if (!contract || typeof contract !== "object") {
    throw new ContractError("contract-required", "abandon: an object is required");
  }
  if (contract.status === "done") {
    throw new ContractError("already-done", "abandon: a finished contract cannot be abandoned");
  }
  if (contract.status === "abandoned") {
    throw new ContractError("already-abandoned", "abandon: the contract is already abandoned");
  }
  if (!isText(reason)) throw new ContractError("stop-reason-required", "abandon: a reason is required");
  const at = now();
  return touch({
    ...contract,
    status: "abandoned",
    stop_reason: reason,
    stops: [...(contract.stops || []), { reason, at }],
  });
}

// A stopped run is resumable, but only by an explicit act that raises the cap. The reopen
// is recorded so a resumed run cannot look like a run that never stopped.
export function reopen(contract, { reason, maxSteps } = {}) {
  if (!contract || contract.status !== "abandoned") {
    throw new ContractError("not-abandoned", "reopen: only an abandoned contract can be reopened");
  }
  if (!isText(reason)) throw new ContractError("reopen-reason-required", "reopen: a reason is required");
  const cap = maxSteps == null ? contract.max_steps : maxSteps;
  if (!Number.isInteger(cap) || cap < 1) {
    throw new ContractError("max-steps-invalid", "reopen: maxSteps must be a positive integer");
  }
  if (contract.steps.length >= cap) {
    throw new ContractError(
      "reopen-no-headroom",
      "reopen: " + contract.steps.length + " steps already recorded against a cap of " + cap,
    );
  }
  return touch({
    ...contract,
    status: "open",
    max_steps: cap,
    stop_reason: null,
    reopens: [...(contract.reopens || []), { reason, at: now() }],
  });
}

export function validateContract(contract) {
  const errors = [];
  const err = (at, message) => errors.push({ path: at, message });
  if (!contract || typeof contract !== "object" || Array.isArray(contract)) {
    return { ok: false, errors: [{ path: "$", message: "contract must be an object" }] };
  }
  if (contract.version !== CONTRACT_VERSION) {
    err("version", "version must be " + CONTRACT_VERSION);
  }
  if (!isText(contract.goal)) err("goal", "goal must be a non-empty string");
  if (!contract.done_condition || !isText(contract.done_condition.cmd)) {
    err("done_condition.cmd", "done condition command is required");
  } else if (!Number.isInteger(contract.done_condition.expect_exit)) {
    err("done_condition.expect_exit", "expect_exit must be an integer");
  }
  if (!Number.isInteger(contract.max_steps) || contract.max_steps < 1) {
    err("max_steps", "max_steps must be a positive integer");
  }
  if (!CONTRACT_STATUSES.includes(contract.status)) {
    err("status", "status must be one of " + CONTRACT_STATUSES.join(", "));
  }
  if (!Array.isArray(contract.steps)) {
    err("steps", "steps must be an array");
    return { ok: false, errors };
  }
  if (Number.isInteger(contract.max_steps) && contract.steps.length > contract.max_steps) {
    err("steps", "steps exceed max_steps");
  }
  contract.steps.forEach((step, index) => {
    const at = "steps." + index;
    if (!step || typeof step !== "object") {
      err(at, "step must be an object");
      return;
    }
    if (!isText(step.id)) err(at + ".id", "step id is required");
    if (!step.observation || !isText(step.observation.cmd)) {
      err(at + ".observation.cmd", "observation command is required");
    } else {
      if (step.observation.id !== "obs-" + (index + 1)) {
        err(at + ".observation.id", "observation id must be obs-" + (index + 1));
      }
      if (typeof step.observation.tail !== "string") err(at + ".observation.tail", "tail must be a string");
      if (step.observation.exit !== null && !Number.isInteger(step.observation.exit)) {
        err(at + ".observation.exit", "exit must be an integer or null");
      }
    }
    if (step.chose) {
      if (!isText(step.chose.action)) err(at + ".chose.action", "chosen action is required");
      if (!isText(step.chose.why)) err(at + ".chose.why", "chosen reason is required");
      if (!Array.isArray(step.considered) || step.considered.length === 0) {
        err(at + ".considered", "a decision needs at least one rejected alternative");
      } else {
        step.considered.forEach((alt, i) => {
          if (!alt || !isText(alt.action) || !isText(alt.why_not)) {
            err(at + ".considered." + i, "alternative needs action and why_not");
          }
        });
        if (step.considered.some((a) => a && a.action === step.chose.action)) {
          err(at + ".chose.action", "the chosen action is also listed as rejected");
        }
      }
      if (!step.observation || step.chose.because !== step.observation.id) {
        err(at + ".chose.because", "decision must cite this step's observation id");
      }
    } else if (step.result) {
      err(at + ".chose", "a result without a decision");
    }
    if (step.result) {
      if (!isText(step.result.evidence)) err(at + ".result.evidence", "result evidence is required");
      if (step.result.exit !== null && !Number.isInteger(step.result.exit)) {
        err(at + ".result.exit", "exit must be an integer or null");
      }
      if (typeof step.result.ok !== "boolean") err(at + ".result.ok", "ok must be a boolean");
      if (!Number.isInteger(step.result.closed_seq)) err(at + ".result.closed_seq", "closed_seq is required to prove ordering");
      if (!isText(step.closed_at)) err(at + ".closed_at", "closed_at is required for a result");
    } else if (index < contract.steps.length - 1) {
      err(at + ".result", "only the last step may be open");
    }
    if (step.lessons_applied != null) {
      if (!Array.isArray(step.lessons_applied)) {
        err(at + ".lessons_applied", "lessons_applied must be an array");
      } else {
        step.lessons_applied.forEach((entry, i) => {
          const where = at + ".lessons_applied." + i;
          if (typeof entry === "string") {
            if (!isText(entry)) err(where, "lesson id must be non-empty");
            return;
          }
          if (!entry || !isText(entry.lesson)) err(where + ".lesson", "lesson id is required");
          if (!entry || !["used", "refuted", "partial"].includes(entry.outcome)) {
            err(where + ".outcome", "outcome must be used, refuted or partial");
          }
        });
      }
    }
  });
  if (!Number.isInteger(contract.seq)) err("seq", "seq must be an integer");
  if (!Array.isArray(contract.done_checks)) {
    err("done_checks", "done_checks must be an array");
  } else {
    contract.done_checks.forEach((check, index) => {
      const at = "done_checks." + index;
      if (!check || !isText(check.cmd)) err(at + ".cmd", "check command is required");
      if (!check || !Number.isInteger(check.exit)) err(at + ".exit", "check exit must be an integer");
      if (!check || !Number.isInteger(check.seq)) err(at + ".seq", "check seq is required to prove ordering");
    });
  }
  if (contract.status === "done") {
    const verdict = canFinish({ ...contract, status: "open" });
    if (!verdict.ok) err("status", "marked done but " + verdict.code + ": " + verdict.reason);
    if (!isText(contract.finished_at)) err("finished_at", "finished_at is required for a done contract");
  }
  if (contract.status === "abandoned") {
    if (!Array.isArray(contract.stops) || contract.stops.length === 0) {
      err("stops", "an abandoned contract needs a stop reason");
    }
  }
  if (!isText(contract.updated_at)) err("updated_at", "updated_at is required");
  return { ok: errors.length === 0, errors };
}

export function assertContract(contract) {
  const verdict = validateContract(contract);
  if (!verdict.ok) {
    const first = verdict.errors.slice(0, 5).map((e) => e.path + ": " + e.message).join("; ");
    throw new ContractError("invalid-contract", "contract: " + first, { errors: verdict.errors });
  }
  return contract;
}

export function saveContract(file, contract) {
  assertContract(contract);
  writeFileLoud(file, JSON.stringify(contract, null, 2) + "\n");
  return contract;
}

export function loadContract(file) {
  let contract;
  try {
    contract = JSON.parse(fs.readFileSync(file, "utf8"));
  } catch (err) {
    throw new ContractError("contract-unreadable", "contract: cannot read " + file + ": " + err.message);
  }
  return assertContract(contract);
}

export function contractDigest(contract) {
  return crypto.createHash("sha256").update(JSON.stringify(contract)).digest("hex").slice(0, 16);
}

export function summarizeContract(contract) {
  const steps = Array.isArray(contract.steps) ? contract.steps.length : 0;
  const step = openStep(contract);
  return (
    "goal=" + JSON.stringify(contract.goal) +
    " status=" + contract.status +
    " steps=" + steps + "/" + contract.max_steps +
    (step ? " open=" + step.id : "") +
    " done_cmd=" + JSON.stringify(contract.done_condition && contract.done_condition.cmd)
  );
}

// What a continuation brief should say. A resumed agent gets the state, not the transcript.
export function contractOrders(contract) {
  const lines = [
    "Run contract — " + contract.goal,
    "Done condition: `" + contract.done_condition.cmd + "` must exit " + contract.done_condition.expect_exit + ".",
    "Steps recorded: " + contract.steps.length + " of " + contract.max_steps + ".",
  ];
  const step = openStep(contract);
  if (step) {
    lines.push("Open step " + step.id + " observed: `" + step.observation.cmd + "` -> exit " + step.observation.exit);
    if (step.chose) lines.push("Decision: " + step.chose.action + " (" + step.chose.why + ")");
    else lines.push("No decision recorded yet; decide from the observation before acting.");
  }
  const check = contract.done_checks[contract.done_checks.length - 1];
  if (check) lines.push("Last done check: `" + check.cmd + "` -> exit " + check.exit + " at " + check.at);
  else lines.push("The done condition has not run yet.");
  return lines.join("\n");
}

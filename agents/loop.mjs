// Meta OS agent layer — the inner loop (AGENTIC build order, item 2).
//
// The runtime already spawns a process and kills it on budget. This is the loop INSIDE that
// process, made observable: one step at a time, each gated on the contract. The model still
// decides; the driver refuses to let it act before an observation, choose without citing one,
// close without evidence, or finish without running the done condition.
//
// It is deliberately adapter-shaped. This module does not know how to call a model or a
// shell. The caller passes observe/decide/act/checkDone, and every transition is recorded
// before the next one is allowed.
import { spawnSync } from "node:child_process";
import {
  ContractError,
  abandon,
  canFinish,
  finish,
  loadContract,
  recordDecision,
  recordDoneCheck,
  openStep,
  recordObservation,
  recordResult,
  saveContract,
} from "./contract.mjs";

function reasonOf(err) {
  return String((err && err.message) || err || "unknown error");
}

function stepCount(contract) {
  return Array.isArray(contract.steps) ? contract.steps.length : 0;
}

function blocked(code, err, contract) {
  return {
    status: "blocked",
    code,
    reason: reasonOf(err),
    contract,
    steps: stepCount(contract),
  };
}

function stopped(status, contract, reason) {
  return { status, reason, contract, steps: stepCount(contract) };
}

// One bounded run of the loop. Returns, never throws for an ordinary refusal — a refusal is
// a state the caller must record. Programming errors in the adapters are captured as
// blocked, because a loop that crashes leaves no reason on disk.
export async function runLoop(options = {}) {
  const {
    contract: initial,
    observe,
    decide,
    act,
    checkDone = null,
    saveTo = null,
    deadlineMs = null,
    onTransition = null,
    now = () => Date.now(),
  } = options;

  if (!initial || typeof initial !== "object") {
    throw new ContractError("contract-required", "loop: a contract is required");
  }
  if (typeof observe !== "function" || typeof decide !== "function" || typeof act !== "function") {
    throw new ContractError("adapter-required", "loop: observe, decide and act must be functions");
  }
  if (checkDone != null && typeof checkDone !== "function") {
    throw new ContractError("adapter-invalid", "loop: checkDone must be a function when provided");
  }
  if (deadlineMs != null && (!(Number(deadlineMs) > 0) || !Number.isFinite(Number(deadlineMs)))) {
    throw new ContractError("deadline-invalid", "loop: deadlineMs must be a positive number");
  }

  let contract = initial;
  const maxSteps = Math.min(
    Number.isInteger(options.maxSteps) ? options.maxSteps : contract.max_steps,
    contract.max_steps,
  );
  const startedAt = now();
  const transition = (phase) => {
    if (saveTo) saveContract(saveTo, contract);
    if (onTransition) onTransition({ phase, contract });
  };

  if (contract.status === "done") return stopped("done", contract, null);
  if (contract.status === "abandoned") return stopped("abandoned", contract, contract.stop_reason || "abandoned");
  if (saveTo) saveContract(saveTo, contract);

  while (true) {
    if (deadlineMs != null && now() - startedAt >= Number(deadlineMs)) {
      contract = abandon(contract, "deadline");
      transition("abandoned:deadline");
      return stopped("abandoned", contract, "deadline");
    }

    // The done gate runs BEFORE the step cap: a contract whose condition is already true
    // finishes with zero steps rather than inventing work to justify the run. It runs only
    // when no step is open: a check taken mid-step is necessarily "step-open", and recording
    // it would make the real check stale the moment the step closes.
    const openAtTop = openStep(contract);
    if (checkDone && !openAtTop) {
      let check;
      try {
        check = await checkDone({ contract });
      } catch (err) {
        return blocked("done-check-failed", err, contract);
      }
      if (!check || typeof check.cmd !== "string" || !Number.isInteger(check.exit)) {
        return blocked(
          "done-check-invalid",
          new Error("checkDone must return { cmd: string, exit: integer, tail?: string }"),
          contract,
        );
      }
      contract = recordDoneCheck(contract, check);
      transition("done-check");
    }

    const doneVerdict = canFinish(contract);
    if (doneVerdict.ok) {
      contract = finish(contract);
      transition("done");
      return stopped("done", contract, null);
    }

    const open = openAtTop;

    if (open) {
      if (!open.chose) {
        let proposal;
        try {
          proposal = await decide({ contract, step: open, observation: open.observation });
        } catch (err) {
          return blocked("decide-failed", err, contract);
        }
        try {
          contract = recordDecision(contract, proposal);
        } catch (err) {
          return blocked(err.code || "decision-refused", err, contract);
        }
        transition("decision");
        continue;
      }

      let outcome;
      try {
        outcome = await act({ contract, step: open, chose: open.chose, observation: open.observation });
      } catch (err) {
        // A thrown action is evidence of failure, not a reason to lose the step. It is
        // closed as failed and the loop observes again on the next turn.
        contract = recordResult(contract, { exit: null, ok: false, evidence: "action threw: " + reasonOf(err) });
        transition("action-threw");
        continue;
      }
      if (!outcome || typeof outcome.evidence !== "string" || outcome.evidence.trim() === "") {
        return blocked(
          "act-no-evidence",
          new Error("act must return { exit, evidence } with non-empty evidence"),
          contract,
        );
      }
      contract = recordResult(contract, outcome);
      transition("result");
      continue;
    }

    // The cap blocks a NEW observation, never the closing of a step already observed.
    // Stopping between the observation and the action would leave work half-recorded and
    // make the cap look like a judgment about the step rather than a budget on the run.
    if (stepCount(contract) >= maxSteps) {
      contract = abandon(contract, "max-steps");
      transition("abandoned:max-steps");
      return stopped("abandoned", contract, "max-steps");
    }

    let observation;
    try {
      observation = await observe({ contract });
    } catch (err) {
      return blocked("observe-failed", err, contract);
    }
    try {
      contract = recordObservation(contract, observation);
    } catch (err) {
      return blocked(err.code || "observation-refused", err, contract);
    }
    transition("observation");
  }
}

export async function resumeLoop(file, options = {}) {
  const contract = loadContract(file);
  return runLoop({ ...options, contract, saveTo: file });
}

// The default done-condition runner: the exact command recorded in the contract, through a
// shell because the contract stores a command line, with a timeout that becomes exit 124.
// A caller that needs a different executor can pass its own checkDone; it is not forced to
// use this one.
export function shellCheck(defaults = {}) {
  const cwd = defaults.cwd || process.cwd();
  const env = defaults.env || process.env;
  const timeoutMs = defaults.timeoutMs == null ? 120000 : defaults.timeoutMs;
  return ({ contract }) => {
    const cmd = contract.done_condition.cmd;
    const timeout = contract.done_condition.timeout_ms || timeoutMs;
    const windows = process.platform === "win32";
    const shell = windows ? process.env.ComSpec || "cmd.exe" : "/bin/sh";
    const args = windows ? ["/c", cmd] : ["-c", cmd];
    const result = spawnSync(shell, args, {
      cwd,
      env,
      timeout,
      encoding: "utf8",
      maxBuffer: 8 * 1024 * 1024,
    });
    let exit;
    if (result.error && result.error.code === "ETIMEDOUT") exit = 124;
    else if (result.error) exit = 127;
    else exit = result.status == null ? 1 : result.status;
    const output = [result.stdout || "", result.stderr || ""].join("\n").trim();
    return { cmd, exit, tail: output.slice(-4000) };
  };
}

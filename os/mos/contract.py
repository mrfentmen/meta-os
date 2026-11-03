#!/usr/bin/env python3
"""The run contract, read on the OS side.

The agent layer writes a contract as JSON on the host. MOS is Python and runs above the relay
bus; it must be able to decide whether the work is finished without importing Node. This module
is the verifier, not a second loop: it reads, validates, and answers ``can_finish`` with the same
rules as ``agents/contract.mjs``.

The kernel is not involved. Its frozen ABI is syscalls 0-5 (exit, write, sleep, pid, yield,
read_key) and has no file, network, or spawn; agent policy belongs to L5 in userspace. This is
that userspace boundary on the Python side.

Shape: docs/AGENT_LAYER_SPEC.md.
"""
import hashlib
import json
import os
from typing import Any, Dict, List, Optional

CONTRACT_VERSION = 1
CONTRACT_STATUSES = ("open", "done", "abandoned")
LESSON_OUTCOMES = ("used", "refuted", "partial")


class ContractError(ValueError):
    """A contract that cannot be read, validated, or finished."""

    def __init__(self, code, message, detail=None):
        super().__init__(message)
        self.code = code
        self.detail = detail or {}


def _is_text(value):
    return isinstance(value, str) and value.strip() != ""


def _is_int(value):
    # bool is an int in Python; an exit code of True is not an exit code.
    return isinstance(value, int) and not isinstance(value, bool)


def _step_open(step):
    return isinstance(step, dict) and step.get("result") is None


def validate_contract(contract):
    """Return a list of ``{path, message}`` errors. Empty means valid."""
    errors = []

    def err(path, message):
        errors.append({"path": path, "message": message})

    if not isinstance(contract, dict):
        return [{"path": "$", "message": "contract must be an object"}]
    if contract.get("version") != CONTRACT_VERSION:
        err("version", "version must be %d" % CONTRACT_VERSION)
    if not _is_text(contract.get("goal")):
        err("goal", "goal must be a non-empty string")
    condition = contract.get("done_condition")
    if not isinstance(condition, dict) or not _is_text(condition.get("cmd")):
        err("done_condition.cmd", "done condition command is required")
    elif not _is_int(condition.get("expect_exit")):
        err("done_condition.expect_exit", "expect_exit must be an integer")
    if not _is_int(contract.get("max_steps")) or contract.get("max_steps") < 1:
        err("max_steps", "max_steps must be a positive integer")
    if contract.get("status") not in CONTRACT_STATUSES:
        err("status", "status must be one of %s" % ", ".join(CONTRACT_STATUSES))
    if not _is_int(contract.get("seq")):
        err("seq", "seq must be an integer")
    steps = contract.get("steps")
    if not isinstance(steps, list):
        err("steps", "steps must be an array")
        steps = []
    elif _is_int(contract.get("max_steps")) and len(steps) > contract["max_steps"]:
        err("steps", "steps exceed max_steps")

    for index, step in enumerate(steps):
        at = "steps.%d" % index
        if not isinstance(step, dict):
            err(at, "step must be an object")
            continue
        if not _is_text(step.get("id")):
            err(at + ".id", "step id is required")
        observation = step.get("observation")
        if not isinstance(observation, dict) or not _is_text(observation.get("cmd")):
            err(at + ".observation.cmd", "observation command is required")
        else:
            if observation.get("id") != "obs-%d" % (index + 1):
                err(at + ".observation.id", "observation id must be obs-%d" % (index + 1))
            if not isinstance(observation.get("tail"), str):
                err(at + ".observation.tail", "tail must be a string")
            if observation.get("exit") is not None and not _is_int(observation.get("exit")):
                err(at + ".observation.exit", "exit must be an integer or null")

        chose = step.get("chose")
        if chose is not None:
            if not isinstance(chose, dict):
                err(at + ".chose", "chose must be an object")
            else:
                if not _is_text(chose.get("action")):
                    err(at + ".chose.action", "chosen action is required")
                if not _is_text(chose.get("why")):
                    err(at + ".chose.why", "chosen reason is required")
                considered = step.get("considered")
                if not isinstance(considered, list) or not considered:
                    err(at + ".considered", "a decision needs at least one rejected alternative")
                else:
                    for alt_index, alternative in enumerate(considered):
                        where = at + ".considered.%d" % alt_index
                        if not isinstance(alternative, dict):
                            err(where, "alternative must be an object")
                            continue
                        if not _is_text(alternative.get("action")):
                            err(where + ".action", "alternative action is required")
                        if not _is_text(alternative.get("why_not")):
                            err(where + ".why_not", "alternative reason is required")
                    if any(
                        isinstance(alternative, dict)
                        and alternative.get("action") == chose.get("action")
                        for alternative in considered
                    ):
                        err(at + ".chose.action", "the chosen action is also listed as rejected")
                if not isinstance(observation, dict) or chose.get("because") != observation.get("id"):
                    err(at + ".chose.because", "decision must cite this step's observation id")
        elif step.get("result") is not None:
            err(at + ".chose", "a result without a decision")

        result = step.get("result")
        if result is not None:
            if not isinstance(result, dict):
                err(at + ".result", "result must be an object")
            else:
                if not _is_text(result.get("evidence")):
                    err(at + ".result.evidence", "result evidence is required")
                if result.get("exit") is not None and not _is_int(result.get("exit")):
                    err(at + ".result.exit", "exit must be an integer or null")
                if not isinstance(result.get("ok"), bool):
                    err(at + ".result.ok", "ok must be a boolean")
                if not _is_int(result.get("closed_seq")):
                    err(at + ".result.closed_seq", "closed_seq is required to prove ordering")
            if not _is_text(step.get("closed_at")):
                err(at + ".closed_at", "closed_at is required for a result")
        elif index < len(steps) - 1:
            err(at + ".result", "only the last step may be open")

        lessons = step.get("lessons_applied")
        if lessons is not None:
            if not isinstance(lessons, list):
                err(at + ".lessons_applied", "lessons_applied must be an array")
            else:
                for lesson_index, entry in enumerate(lessons):
                    where = at + ".lessons_applied.%d" % lesson_index
                    if isinstance(entry, str):
                        if not _is_text(entry):
                            err(where, "lesson id must be non-empty")
                        continue
                    if not isinstance(entry, dict) or not _is_text(entry.get("lesson")):
                        err(where + ".lesson", "lesson id is required")
                    if not isinstance(entry, dict) or entry.get("outcome") not in LESSON_OUTCOMES:
                        err(where + ".outcome", "outcome must be used, refuted or partial")

    checks = contract.get("done_checks")
    if not isinstance(checks, list):
        err("done_checks", "done_checks must be an array")
    else:
        for index, check in enumerate(checks):
            at = "done_checks.%d" % index
            if not isinstance(check, dict) or not _is_text(check.get("cmd")):
                err(at + ".cmd", "check command is required")
            if not isinstance(check, dict) or not _is_int(check.get("exit")):
                err(at + ".exit", "check exit must be an integer")
            if not isinstance(check, dict) or not _is_int(check.get("seq")):
                err(at + ".seq", "check seq is required to prove ordering")

    if contract.get("status") == "done":
        verdict = can_finish(dict(contract, status="open"))
        if not verdict["ok"]:
            err("status", "marked done but %s: %s" % (verdict["code"], verdict["reason"]))
        if not _is_text(contract.get("finished_at")):
            err("finished_at", "finished_at is required for a done contract")
    if contract.get("status") == "abandoned":
        stops = contract.get("stops")
        if not isinstance(stops, list) or not stops:
            err("stops", "an abandoned contract needs a stop reason")
    if not _is_text(contract.get("updated_at")):
        err("updated_at", "updated_at is required")
    return errors


def assert_contract(contract):
    errors = validate_contract(contract)
    if errors:
        first = "; ".join("%s: %s" % (e["path"], e["message"]) for e in errors[:5])
        raise ContractError("invalid-contract", "contract: " + first, {"errors": errors})
    return contract


def can_finish(contract):
    """The finish gate, without throwing. Mirrors ``canFinish`` in contract.mjs."""
    if not isinstance(contract, dict):
        return {"ok": False, "code": "contract-required", "reason": "no contract"}
    if contract.get("status") == "done":
        return {"ok": True, "code": "already-done", "reason": None}
    if contract.get("status") != "open":
        return {"ok": False, "code": "contract-not-open", "reason": "status is %s" % contract.get("status")}
    steps = contract.get("steps")
    if not isinstance(steps, list):
        return {"ok": False, "code": "steps-invalid", "reason": "steps is not an array"}
    if steps and _step_open(steps[-1]):
        return {
            "ok": False,
            "code": "step-open",
            "reason": "step %s has no result" % steps[-1].get("id"),
            "step": steps[-1].get("id"),
        }
    if not all(isinstance(step, dict) and step.get("chose") and step.get("result") for step in steps):
        return {"ok": False, "code": "step-unverified", "reason": "a step is missing its decision or result"}
    condition = contract.get("done_condition") or {}
    checks = contract.get("done_checks")
    check = checks[-1] if isinstance(checks, list) and checks else None
    if not check:
        return {"ok": False, "code": "done-not-run", "reason": "the done condition has not been executed in this run"}
    if check.get("cmd") != condition.get("cmd"):
        return {
            "ok": False,
            "code": "done-command-mismatch",
            "reason": "the recorded check ran a different command than the contract",
            "expected": condition.get("cmd"),
            "ran": check.get("cmd"),
        }
    last = steps[-1] if steps else None
    if last:
        closed_seq = last.get("result", {}).get("closed_seq")
        if not _is_int(check.get("seq")) or not _is_int(closed_seq):
            return {
                "ok": False,
                "code": "done-stale",
                "reason": "the order of the last step and the done check cannot be proven; re-run the done condition",
            }
        if check["seq"] <= closed_seq:
            return {
                "ok": False,
                "code": "done-stale",
                "reason": "the done condition passed before the last step closed; it must be re-run after",
            }
    if check.get("exit") != condition.get("expect_exit"):
        return {
            "ok": False,
            "code": "done-failed",
            "reason": "the done condition exited %s, expected %s"
            % (check.get("exit"), condition.get("expect_exit")),
            "exit": check.get("exit"),
            "expected": condition.get("expect_exit"),
        }
    return {"ok": True, "code": "done", "reason": None}


def load_contract(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            contract = json.load(handle)
    except (OSError, ValueError) as exc:
        raise ContractError("contract-unreadable", "contract: cannot read %s: %s" % (path, exc))
    return assert_contract(contract)


def contract_digest(contract):
    """A stable digest across languages: sorted keys, compact separators."""
    canonical = json.dumps(contract, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def summarize_contract(contract):
    steps = contract.get("steps") if isinstance(contract.get("steps"), list) else []
    return "goal=%r status=%s steps=%d/%d done_cmd=%r" % (
        contract.get("goal"),
        contract.get("status"),
        len(steps),
        contract.get("max_steps"),
        (contract.get("done_condition") or {}).get("cmd"),
    )


def is_done(path):
    """True only when the file validates and its finish gate passes."""
    try:
        return can_finish(load_contract(path))["ok"]
    except ContractError:
        return False

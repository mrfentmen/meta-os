#!/usr/bin/env python3
"""Run a command, then accept the result only if its contract finished.

This is the OS-side half of the bridge. The agent (Node or any program) writes
``contract.json`` into its run directory; this module runs the command, reads that file, and
returns a verdict. A caller wiring it into ``mos.worker`` reports ``done`` only when
``verdict.ok`` is true; otherwise the job is blocked with the contract's own reason.

The kernel is not involved. The verifier is userspace, next to MOS, and the contract is plain
JSON so the boundary does not depend on Node being installed on the image.

    python3 -m mos.contract_job verify <run_dir>
"""
import json
import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional

from .contract import ContractError, can_finish, contract_digest, load_contract

MAX_OUTPUT_TAIL = 4000


@dataclass
class ContractJobVerdict:
    ok: bool
    code: str
    reason: str
    exit_code: Optional[int]
    contract_path: str
    digest: Optional[str]
    output_tail: str

    def as_dict(self):
        return asdict(self)


def _tail(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            return handle.read()[-MAX_OUTPUT_TAIL:]
    except OSError:
        return ""


def _verdict(ok, code, reason, exit_code, contract_path, digest=None, output_tail=""):
    return ContractJobVerdict(
        ok=bool(ok),
        code=code,
        reason=reason,
        exit_code=exit_code,
        contract_path=contract_path,
        digest=digest,
        output_tail=output_tail,
    )


def verify_contract(run_dir):
    """Verify a run directory that already has a contract. No process is started."""
    contract_path = os.path.join(run_dir, "contract.json")
    if not os.path.exists(contract_path):
        return _verdict(False, "contract-missing", "no contract.json in the run directory", None, contract_path)
    try:
        contract = load_contract(contract_path)
    except ContractError as exc:
        return _verdict(False, "contract-invalid", "%s: %s" % (exc.code, exc), None, contract_path)
    verdict = can_finish(contract)
    if not verdict["ok"]:
        return _verdict(
            False,
            "contract-not-finished",
            "%s: %s" % (verdict["code"], verdict["reason"]),
            None,
            contract_path,
            contract_digest(contract),
        )
    return _verdict(True, "done", "contract finished", None, contract_path, contract_digest(contract))


def run_contract_job(command, workdir, run_dir, timeout=120, agent="agent", env=None):
    """Run ``command`` in ``workdir`` and gate the result on ``run_dir/contract.json``.

    ``command`` is an argv list (no shell). The child gets AGENT_RUN, AGENT_NAME,
    AGENT_RUN_DIR, and CONTRACT_PATH in its environment. A nonzero exit, a timeout, a missing
    contract, an invalid contract, or an unfinished contract is a failed verdict; none of them
    is ever reported as done.
    """
    if not isinstance(command, list) or not command or not all(isinstance(part, str) and part for part in command):
        raise ValueError("command must be a non-empty argv list of strings")
    workdir = os.path.abspath(workdir)
    run_dir = os.path.abspath(run_dir)
    os.makedirs(run_dir, exist_ok=True)
    contract_path = os.path.join(run_dir, "contract.json")
    output_path = os.path.join(run_dir, "output.log")
    child_env = dict(os.environ if env is None else env)
    child_env.update(
        {
            "AGENT_RUN": os.path.basename(run_dir.rstrip(os.sep)) or ("run-%d" % os.getpid()),
            "AGENT_NAME": agent,
            "AGENT_RUN_DIR": run_dir,
            "CONTRACT_PATH": contract_path,
        }
    )

    started = time.time()
    try:
        with open(output_path, "w", encoding="utf-8") as output:
            process = subprocess.Popen(
                command,
                cwd=workdir,
                env=child_env,
                stdout=output,
                stderr=subprocess.STDOUT,
            )
            try:
                exit_code = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                return _verdict(
                    False,
                    "timeout",
                    "command exceeded %.1fs" % timeout,
                    124,
                    contract_path,
                    output_tail=_tail(output_path),
                )
    except FileNotFoundError as exc:
        return _verdict(False, "command-not-found", str(exc), 127, contract_path)
    except OSError as exc:
        return _verdict(False, "command-failed", str(exc), None, contract_path)

    output_tail = _tail(output_path)
    if exit_code != 0:
        return _verdict(
            False,
            "nonzero-exit",
            "command exited %d after %.1fs" % (exit_code, time.time() - started),
            exit_code,
            contract_path,
            output_tail=output_tail,
        )
    if not os.path.exists(contract_path):
        return _verdict(
            False,
            "contract-missing",
            "the command exited 0 but wrote no contract.json",
            exit_code,
            contract_path,
            output_tail=output_tail,
        )
    try:
        contract = load_contract(contract_path)
    except ContractError as exc:
        return _verdict(
            False,
            "contract-invalid",
            "%s: %s" % (exc.code, exc),
            exit_code,
            contract_path,
            output_tail=output_tail,
        )
    verdict = can_finish(contract)
    digest = contract_digest(contract)
    if not verdict["ok"]:
        return _verdict(
            False,
            "contract-not-finished",
            "%s: %s" % (verdict["code"], verdict["reason"]),
            exit_code,
            contract_path,
            digest,
            output_tail,
        )
    return _verdict(True, "done", "contract finished", exit_code, contract_path, digest, output_tail)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 2 or argv[0] != "verify":
        print("usage: python3 -m mos.contract_job verify <run_dir>", file=sys.stderr)
        return 2
    verdict = verify_contract(argv[1])
    print(json.dumps(verdict.as_dict(), sort_keys=True))
    return 0 if verdict.ok else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""OS-053: the reference agent driver.

Implements the contract in os/drivers/CONTRACT.md against a caller
supplied command, so the contract mechanics are real and testable
without a coding agent CLI on the machine: the child process really
runs, its output really lands in a log file, the changed file list
really comes from a before/after snapshot diff, and the status
record really comes from mos/acceptance.verify against the workdir
on disk.

This is a reference driver, not a coding agent driver. It proves
start/stop/heartbeat/artifacts. The first real driver is OS-054
(Muse Code), which replaces the caller supplied command with the
agent CLI and streams its progress into heartbeats.

No bus post, no network, no secret: heartbeat records go to the
caller supplied sink (an in memory list by default). Starting
against an unsigned spec, unparseable accept lines, or an empty
owned files list is a hard error and spawns nothing.
"""

import hashlib
import os
import signal
import subprocess
import sys
import time

try:
    from mos import acceptance
except ImportError:  # loaded by path (tests) without the repo root on sys.path
    _ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    if _ROOT not in sys.path:
        sys.path.insert(0, _ROOT)
    from mos import acceptance

LOG_NAME = "driver.log"


class DriverError(Exception):
    """Any contract violation or driver failure."""


class UnsignedSpecError(DriverError):
    """Raised when start() is given a spec without a signature."""


class BadSpecError(DriverError):
    """Raised when start() is given a malformed spec."""


class NotStartedError(DriverError):
    """Raised when an operation needs a started driver and has none."""


def validate_spec(spec):
    """Validate a job spec against the contract. Returns a copy.

    Raises UnsignedSpecError when the signature is missing or empty,
    BadSpecError for any other malformed field. Accept lines are
    parsed here, at start time, so a bad spec fails before any
    process spawns rather than at verification time.
    """
    if not isinstance(spec, dict):
        raise BadSpecError("job spec must be a dict")
    for field in ("id", "title", "spec"):
        value = spec.get(field)
        if not isinstance(value, str) or not value.strip():
            raise BadSpecError("job spec field %r must be a non empty string"
                               % field)
    files = spec.get("files")
    if (not isinstance(files, list) or not files
            or any(not isinstance(f, str) or not f.strip() for f in files)):
        raise BadSpecError("job spec field 'files' must be a non empty "
                           "list of non empty paths")
    try:
        acceptance.parse_accept(spec.get("accept", ""))
    except ValueError as exc:
        raise BadSpecError("unparseable accept lines: %s" % exc)
    sig = spec.get("sig")
    if not isinstance(sig, str) or not sig.strip():
        raise UnsignedSpecError("job spec has no signature; refusing to "
                                "start an unsigned job")
    out = dict(spec)
    out["max_attempts"] = spec.get("max_attempts", 3)
    return out


def _snapshot(workdir):
    """Map relative path -> sha256 for every regular file under workdir."""
    snap = {}
    for base, _dirs, names in os.walk(workdir):
        for name in names:
            full = os.path.join(base, name)
            rel = os.path.relpath(full, workdir)
            try:
                with open(full, "rb") as f:
                    snap[rel] = hashlib.sha256(f.read()).hexdigest()
            except OSError:
                continue
    return snap


class StubDriver:
    """Reference driver: runs a caller supplied argv command as the agent.

    The command runs with cwd=workdir and its stdout/stderr appended
    to <workdir>/driver.log. The caller owns the command; the driver
    owns the contract around it.
    """

    def __init__(self, workdir, heartbeat_sink=None):
        if not os.path.isdir(workdir):
            raise DriverError("workdir does not exist: %s" % workdir)
        self.workdir = workdir
        self.heartbeats = []
        self._sink = heartbeat_sink or self.heartbeats.append
        self._proc = None
        self._log = None
        self._spec = None
        self._before = None
        self._artifacts = None
        self._stopped = False

    def start(self, spec, command):
        """Launch the agent command against a validated spec."""
        if self._proc is not None:
            raise DriverError("driver already started for job %s"
                              % self._spec["id"])
        self._spec = validate_spec(spec)
        if (not isinstance(command, list) or not command
                or any(not isinstance(c, str) for c in command)):
            raise BadSpecError("command must be a non empty argv list")
        log_path = os.path.join(self.workdir, LOG_NAME)
        self._log = open(log_path, "ab")
        self._before = _snapshot(self.workdir)
        self._proc = subprocess.Popen(
            command, cwd=self.workdir, stdout=self._log,
            stderr=subprocess.STDOUT)
        self._stopped = False
        self._artifacts = None
        return {"job_id": self._spec["id"], "pid": self._proc.pid,
                "status": "running"}

    def heartbeat(self, note=""):
        """Emit one progress record in bus progress format."""
        if self._spec is None or self._proc is None:
            raise NotStartedError("heartbeat before start")
        record = {
            "line": "PROGRESS:%s %s" % (self._spec["id"], note),
            "job_id": self._spec["id"],
            "note": note,
            "ts": time.time(),
        }
        self._sink(record)
        return record

    def poll(self):
        """Return the child exit code, or None while it still runs."""
        if self._proc is None:
            raise NotStartedError("poll before start")
        return self._proc.poll()

    def stop(self):
        """Terminate the child cleanly; safe to call after it exited."""
        if self._proc is None:
            raise NotStartedError("stop before start")
        if self._proc.poll() is None:
            self._proc.send_signal(signal.SIGTERM)
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()
                self._proc.wait()
        self._stopped = True
        return {"job_id": self._spec["id"], "status": "stopped",
                "exit_code": self._proc.returncode}

    def wait(self, timeout=None):
        """Wait for exit, then build the artifacts record."""
        if self._proc is None:
            raise NotStartedError("wait before start")
        try:
            exit_code = self._proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            raise DriverError("driver wait timed out for job %s"
                              % self._spec["id"])
        if self._log is not None:
            self._log.close()
            self._log = None
        after = _snapshot(self.workdir)
        changed = sorted(
            rel for rel in set(after) | set(self._before)
            if rel != LOG_NAME and after.get(rel) != self._before.get(rel))
        owned = set(self._spec["files"])
        ok, results = acceptance.verify(self._spec.get("accept", ""),
                                        self.workdir)
        if self._stopped:
            status = "stopped"
        elif exit_code == 0:
            status = "done"
        else:
            status = "failed"
        self._artifacts = {
            "job_id": self._spec["id"],
            "status": status,
            "exit_code": exit_code,
            "changed_files": changed,
            "unowned_files": sorted(f for f in changed if f not in owned),
            "log": os.path.join(self.workdir, LOG_NAME),
            "acceptance": {"ok": ok, "results": results},
        }
        return self._artifacts

    def artifacts(self):
        """Return the artifacts record, waiting first if still running."""
        if self._artifacts is not None:
            return self._artifacts
        return self.wait()

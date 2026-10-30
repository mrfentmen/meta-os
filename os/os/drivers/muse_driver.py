#!/usr/bin/env python3
"""OS-054: the Muse Code agent driver.

Implements the contract in os/drivers/CONTRACT.md against Meta's
Muse Code CLI. The CLI is the `muse` binary; headless runs use
`muse exec --prompt-file <file>`, the non interactive form the
public Muse Code docs describe for scripts and CI. The driver
builds the prompt from the signed job spec (title, spec text,
owned files, acceptance lines, attempt budget), writes it to a
temp file OUTSIDE the workdir so it never pollutes the changed
file list, launches the CLI with cwd=workdir, and streams the
child's stdout lines into heartbeat records (one PROGRESS record
per line, note truncated) while also appending them verbatim to
<workdir>/driver.log. On exit it returns the contract artifacts
record: changed files from a before/after snapshot diff,
unowned changes reported, acceptance from mos/acceptance.verify
against the workdir on disk.

What this driver does NOT do, stated plainly:

- It has never run against a real `muse` binary. No `muse` binary
  exists on this dev machine, and no booted Meta OS image exists
  in this repo, so the conformance run in
  tests/test_os_driver_muse.py uses a fixture stand-in executable
  in place of the binary. The argv shape (binary, exec,
  --prompt-file) is the documented headless form, not a shape
  proven against a live CLI here.
- It passes no approval bypass flag. A flag like --yolo would let
  the agent act without approval, which would cut across the
  dispatch approval gate (DSP-007). Approval behavior in a
  headless run is the CLI's own configuration, not something this
  driver silently decides.
- It never puts the job signature on a command line, in the
  prompt file, or in a log. Signature presence is enforced at
  start() exactly as the contract requires; cryptographic
  verification stays at jobs.py verify_job claim time.
- It never posts to the bus. Heartbeat records go only to the
  caller supplied sink, as in the stub driver.
"""

import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from stub_driver import (  # noqa: E402
    BadSpecError,
    DriverError,
    LOG_NAME,
    NotStartedError,
    UnsignedSpecError,
    _snapshot,
    acceptance,
    validate_spec,
)

DEFAULT_BINARY = "muse"
NOTE_LIMIT = 200


def build_prompt(spec):
    """Render a job spec into the prompt text handed to Muse Code.

    The signature is never included: the prompt carries only what
    the agent needs to do the work. Unknown spec fields are
    ignored, so specs stay forward compatible.
    """
    lines = [
        "Job: %s (id: %s)" % (spec["title"], spec["id"]),
        "",
        spec["spec"],
        "",
        "Owned files (work only in these files unless the spec says "
        "otherwise):",
    ]
    lines.extend("  - %s" % f for f in spec["files"])
    lines.append("")
    lines.append("Acceptance (all lines must hold when you finish):")
    lines.append(spec.get("accept", ""))
    lines.append("")
    lines.append("Attempt budget: max_attempts=%s"
                 % spec.get("max_attempts", 3))
    lines.append("When done, leave the workdir in a state where the "
                 "acceptance lines above hold.")
    return "\n".join(lines) + "\n"


def build_argv(binary, prompt_path, extra_args=None):
    """The headless Muse Code invocation for one prompt file."""
    argv = [binary, "exec", "--prompt-file", prompt_path]
    if extra_args:
        argv.extend(extra_args)
    return argv


class MuseDriver:
    """Muse Code driver: the OS-053 contract against the real CLI."""

    def __init__(self, workdir, heartbeat_sink=None,
                 muse_binary=None, extra_args=None):
        if not os.path.isdir(workdir):
            raise DriverError("workdir does not exist: %s" % workdir)
        self.workdir = workdir
        self.heartbeats = []
        self._sink = heartbeat_sink or self.heartbeats.append
        self._binary = muse_binary or DEFAULT_BINARY
        self._extra_args = list(extra_args or [])
        self._proc = None
        self._log = None
        self._spec = None
        self._before = None
        self._artifacts = None
        self._stopped = False
        self._tmpdir = None
        self._prompt_path = None
        self._reader = None

    def _emit(self, note):
        record = {
            "line": "PROGRESS:%s %s" % (self._spec["id"], note),
            "job_id": self._spec["id"],
            "note": note,
            "ts": time.time(),
        }
        self._sink(record)
        return record

    def _stream(self):
        """Reader thread: child lines to log file and heartbeat sink."""
        try:
            for line in self._proc.stdout:
                text = line.decode("utf-8", "replace")
                self._log.write(text)
                self._log.flush()
                stripped = text.strip()
                if stripped:
                    self._emit(stripped[:NOTE_LIMIT])
        except (ValueError, OSError):
            pass

    def start(self, spec):
        """Validate the spec, then launch `muse exec` against it."""
        if self._proc is not None:
            raise DriverError("driver already started for job %s"
                              % self._spec["id"])
        self._spec = validate_spec(spec)
        if shutil.which(self._binary) is None:
            self._spec = None
            raise DriverError(
                "muse binary not found: %r is not on PATH and is "
                "not an executable path; the Muse Code CLI must be "
                "installed on the machine before this driver can "
                "start" % self._binary)
        self._tmpdir = tempfile.mkdtemp(prefix="muse-driver-")
        self._prompt_path = os.path.join(self._tmpdir, "prompt.md")
        with open(self._prompt_path, "w", encoding="utf-8") as f:
            f.write(build_prompt(self._spec))
        log_path = os.path.join(self.workdir, LOG_NAME)
        self._log = open(log_path, "a", encoding="utf-8")
        self._before = _snapshot(self.workdir)
        argv = build_argv(self._binary, self._prompt_path,
                          self._extra_args)
        try:
            self._proc = subprocess.Popen(
                argv, cwd=self.workdir, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT)
        except OSError as exc:
            self._log.close()
            self._log = None
            raise DriverError("could not launch %s: %s"
                              % (self._binary, exc))
        self._reader = threading.Thread(target=self._stream, daemon=True)
        self._reader.start()
        self._stopped = False
        self._artifacts = None
        return {"job_id": self._spec["id"], "pid": self._proc.pid,
                "status": "running"}

    def heartbeat(self, note=""):
        """Emit one progress record in bus progress format."""
        if self._spec is None or self._proc is None:
            raise NotStartedError("heartbeat before start")
        return self._emit(note)

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
        """Wait for exit, join the stream thread, build artifacts."""
        if self._proc is None:
            raise NotStartedError("wait before start")
        try:
            exit_code = self._proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            raise DriverError("driver wait timed out for job %s"
                              % self._spec["id"])
        if self._reader is not None:
            self._reader.join(timeout=5)
            self._reader = None
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
        if self._tmpdir is not None:
            shutil.rmtree(self._tmpdir, ignore_errors=True)
            self._tmpdir = None
            self._prompt_path = None
        return self._artifacts

    def artifacts(self):
        """Return the artifacts record, waiting first if still running."""
        if self._artifacts is not None:
            return self._artifacts
        return self.wait()

"""intel/launch_run.py -- OS-102 follow-up (Pax): start a real process
from an assembled launch directory.

intel/mind_loader.py builds a launch environment and deliberately
does not start a process. This module is the other half: it runs
one child process from a launch directory, and only from a launch
directory that still verifies.

Rules, all enforced by run_from_launch():

- The launch is verified first, against its bundle, through
  mind_loader.verify_launch(). A launch that fails verification
  is refused and nothing spawns: a tampered constitution, skill,
  grant, changelog, brief, tool grant, or memory mount never
  reaches a running process.
- The child runs with cwd set to the launch directory, so its
  first action reads the assembled layers from relative paths:
  instructions.md, skills/<name>/SKILL.md, grants.json,
  tool_grants.json, brief.json or brief.pending, memory/own
  and memory/shared. METAOS_LAUNCH_DIR in its environment names
  the same directory in absolute form, for a process that needs
  it without assuming its cwd.
- stdout and stderr are captured and returned with the exit
  code; a non-zero exit is data, not an exception, because a
  worker that fails is a result the caller must record.
- A timeout kills the child and raises LaunchRunError naming
  the timeout; the caller never waits on a hung process.
- An empty argv, a missing launch directory, or a launch with
  no launch.json is a hard error before any spawn.

This module knows nothing about drivers, jobs, or the bus: it
starts a process from a launch directory and reports what the
process did. The OS-055/OS-119 handoff (a driver or worker
started from a launch) uses it; a Muse Code driver run, a
launch against a live gateway catalog, and a booted test image
are still owed, and are named as such wherever this module is
recorded.

No bus posts, no network, no model calls, no secrets: the child
inherits the caller's environment plus METAOS_LAUNCH_DIR only.
"""

import os
import subprocess

from intel import mind_loader


class LaunchRunError(Exception):
    """A launch could not be run, or the run itself failed."""


def run_from_launch(launch_dir, argv, bundle_dir=None, gateway_catalog=None,
                    timeout=None, extra_env=None):
    """Run argv as a child process from an assembled launch directory.

    launch_dir must hold a launch.json from mind_loader assembly.
    bundle_dir and gateway_catalog are passed through to
    verify_launch(); with bundle_dir omitted, the manifest's
    recorded bundle directory is used.

    Returns {"launch_dir": abspath, "returncode": int,
    "stdout": str, "stderr": str}. Raises LaunchRunError when the
    launch does not verify, when argv is empty, when the launch
    directory is missing, or when the child times out.
    """
    if not argv:
        raise LaunchRunError("launch run: argv is empty, nothing to run")
    launch_dir = os.path.abspath(launch_dir)
    if not os.path.isdir(launch_dir):
        raise LaunchRunError(
            "launch run: launch directory missing: %s" % launch_dir)
    report = mind_loader.verify_launch(launch_dir, bundle_dir,
                                        gateway_catalog)
    if not report["ok"]:
        raise LaunchRunError(
            "launch run: launch refused, verification failed: %s"
            % "; ".join(report["errors"]))
    env = dict(os.environ)
    env["METAOS_LAUNCH_DIR"] = launch_dir
    if extra_env:
        env.update(extra_env)
    try:
        proc = subprocess.run(argv, cwd=launch_dir, env=env,
                              capture_output=True, text=True,
                              timeout=timeout)
    except subprocess.TimeoutExpired:
        raise LaunchRunError(
            "launch run: child timed out after %s seconds" % timeout)
    except OSError as exc:
        raise LaunchRunError("launch run: child failed to start: %s" % exc)
    return {"launch_dir": launch_dir,
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr}

#!/usr/bin/env python3
"""os/drivers/run_driver.py -- run one signed job through a driver.

Usage:
  python3 os/drivers/run_driver.py --spec-file job.json \
      --workdir /path/to/workdir [--binary /path/to/muse] \
      [--extra-arg FLAG ...]

Reads the job spec (the FND/DSP spec dict: id, title, spec,
files, accept, sig) from a JSON file, starts the Muse Code driver
against it, waits for the child to exit, and prints the contract
artifacts record as JSON on stdout. Exit code 0 when the driver
run itself completed (even if the job failed its acceptance);
exit code 2 on a driver error (unsigned spec, missing binary,
bad spec file), with the error on stderr.

This runner is what relay-driver@.service executes: systemd owns
the process, the watchdog owns silent stalls, and this program
owns nothing but the driver call. It never posts to the bus and
never touches a job record; the overseer handoff that writes the
spec file and consumes the artifacts JSON is OS-055 work.
"""

import argparse
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from muse_driver import MuseDriver  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Run one signed job through the Muse Code driver.")
    parser.add_argument("--spec-file", required=True,
                        help="JSON file holding the job spec dict")
    parser.add_argument("--workdir", required=True,
                        help="workdir the agent works in")
    parser.add_argument("--binary", default=None,
                        help="Muse Code binary (default: muse on PATH)")
    parser.add_argument("--extra-arg", action="append", default=[],
                        help="extra argv token for the CLI (repeatable)")
    args = parser.parse_args(argv)
    try:
        with open(args.spec_file, encoding="utf-8") as f:
            spec = json.load(f)
    except (OSError, ValueError) as exc:
        print("run_driver: cannot read spec file: %s" % exc, file=sys.stderr)
        return 2
    try:
        driver = MuseDriver(args.workdir, muse_binary=args.binary,
                            extra_args=args.extra_arg)
        driver.start(spec)
        arts = driver.artifacts()
    except Exception as exc:  # driver errors are the only exit-2 path
        print("run_driver: %s" % exc, file=sys.stderr)
        return 2
    print(json.dumps(arts, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Demo thresholds drop-in check (Milo lane, OS-038).

Proves the OS-038 acceptance without a booted demo image (there
is none in this repo), and states that gap plainly instead of
claiming a boot:

  1. Drop-in shape: os/services/relay-watchdog.service.d/
     demo-thresholds.conf exists, has a [Service] section, sets
     EnvironmentFile=/opt/relay/intel/metaos-demo.env (the image
     path the payload bake installs), and contains no ExecStart
     — so the production command runs exactly as shipped.
  2. Profile switches windows: a subprocess importing
     intel/thresholds.py with the demo env file's WATCHDOG_*
     variables set reports stall 1 / progress-stall 1 (demo)
     with every other value at its production default.
  3. Production untouched: the base unit file contains no
     EnvironmentFile, and the INT-021 drill tournament passes
     with a clean environment (no WATCHDOG_* variables), run
     in-process with write_log=False so this drill leaves the
     INT-021 log file alone.

Usage: python3 intel/drills/demo_thresholds_dropin.py
Exit 0 with an OS-038: PASS line on success, 1 on failure.
"""

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))
LOG_PATH = os.path.join(ROOT, "intel", "evals",
                        "demo_thresholds_dropin.log")
DROPIN = os.path.join(ROOT, "os", "services",
                      "relay-watchdog.service.d",
                      "demo-thresholds.conf")
UNIT = os.path.join(ROOT, "os", "services",
                    "relay-watchdog.service")
ENV_FILE = os.path.join(ROOT, "intel", "metaos-demo.env")
IMAGE_ENV_PATH = "/opt/relay/intel/metaos-demo.env"

# (threshold attribute, expected value under the demo profile).
EXPECTED = [
    ("STALL_MINUTES", 1),
    ("PROGRESS_STALL_MINUTES", 1),
    ("LEASE_RISK_WINDOW_MINUTES", 5),
    ("LEASE_RISK_QUIET_MINUTES", 2),
    ("ALERT_DEDUPE_COOLDOWN_MINUTES", 30),
    ("SILENT_ROOM_MINUTES", 60),
    ("WATCHDOG_BEAT_TTL_SECONDS", 300),
    ("TICK_PAGE_SIZE", 1000),
    ("TICK_MAX_MESSAGES", 1000),
]


def parse_env_file(path):
    """KEY=VALUE pairs from an env file; comments and blanks skipped."""
    values = {}
    with open(path) as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def check_dropin_shape(lines):
    """Step 1: drop-in exists, is a [Service] section, env only."""
    if not os.path.exists(DROPIN):
        return "FAIL: drop-in missing: %s" % DROPIN
    with open(DROPIN) as handle:
        text = handle.read()
    if "[Service]" not in text:
        return "FAIL: drop-in has no [Service] section"
    if "EnvironmentFile=%s" % IMAGE_ENV_PATH not in text:
        return ("FAIL: drop-in does not point at %s"
                % IMAGE_ENV_PATH)
    directives = [line.strip() for line in text.splitlines()
                  if line.strip() and not line.strip().startswith("#")]
    if any(line.startswith("ExecStart") for line in directives):
        return ("FAIL: drop-in overrides ExecStart; production "
                "command must run as shipped")
    lines.append("PASS: drop-in is [Service] + EnvironmentFile=%s, "
                 "no ExecStart" % IMAGE_ENV_PATH)
    return None


def check_demo_values(lines):
    """Step 2: demo env values switch thresholds in a subprocess."""
    demo_env = parse_env_file(ENV_FILE)
    watchdog_vars = {k: v for k, v in demo_env.items()
                     if k.startswith("WATCHDOG_")}
    if "WATCHDOG_STALL_MINUTES" not in watchdog_vars:
        return "FAIL: demo env file sets no WATCHDOG_STALL_MINUTES"
    names = repr([n for n, _ in EXPECTED])
    code = ("import sys; sys.path.insert(0, '.'); "
            "from intel import thresholds; "
            "print(' '.join(n + '=' + str(getattr(thresholds, n)) "
            "for n in " + names + "))")
    env = dict(os.environ)
    env.update(watchdog_vars)
    proc = subprocess.run([sys.executable, "-c", code],
                          capture_output=True, text=True,
                          cwd=ROOT, env=env)
    if proc.returncode != 0:
        return "FAIL: thresholds import under demo env failed:\n%s" \
            % (proc.stderr or "")
    got = dict(pair.split("=", 1)
               for pair in proc.stdout.strip().split())
    for name, want in EXPECTED:
        if got.get(name) != str(want):
            return ("FAIL: demo profile %s=%s, expected %s"
                    % (name, got.get(name), want))
    lines.append("PASS: demo profile switches thresholds "
                 "(stall 1, progress-stall 1, all others at "
                 "production defaults)")
    return None


def check_production_untouched(lines):
    """Step 3: base unit has no env file; INT tournament passes clean."""
    with open(UNIT) as handle:
        unit_text = handle.read()
    if "EnvironmentFile" in unit_text:
        return ("FAIL: production unit file itself sets "
                "EnvironmentFile; the drop-in must carry that alone")
    sys.path.insert(0, os.path.join(ROOT, "intel", "drills"))
    import tournament  # noqa: E402
    saved = {name: os.environ.pop(name)
             for name in list(os.environ)
             if name.startswith("WATCHDOG_")}
    try:
        result = tournament.run_tournament(write_log=False)
    finally:
        os.environ.update(saved)
    if not result["ok"]:
        return ("FAIL: INT-021 tournament failed with a clean "
                "environment:\n%s" % result["transcript"])
    lines.append("PASS: production unit has no EnvironmentFile; "
                 "INT-021 tournament 3/3 clean (%.2fs)"
                 % result["total_seconds"])
    return None


def run(write_log=True):
    lines = ["OS-038 demo thresholds drop-in check: drop-in shape, "
             "demo values, production untouched"]
    failure = (check_dropin_shape(lines)
               or check_demo_values(lines)
               or check_production_untouched(lines))
    lines.append("OS-038: FAIL -- %s" % failure if failure
                 else "OS-038: PASS -- drop-in switches the stall "
                 "windows on the demo image; production untouched")
    transcript = "\n".join(lines) + "\n"
    if write_log:
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        with open(LOG_PATH, "w") as handle:
            handle.write(transcript)
    return {"ok": failure is None, "transcript": transcript}


def main():
    result = run(write_log=True)
    sys.stdout.write(result["transcript"])
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())

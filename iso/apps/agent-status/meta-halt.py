#!/usr/bin/env python3
"""meta-halt — pause one agent, or all of them, without editing anything.

A halt is a file: `stop/<name>.STOP` in the relay's state directory. The
watchman reads it before a spawn, so a halted agent never starts and a job it
was given waits on the board instead of being refused. Clearing the halt
resumes that job on the next poll.

    meta-halt                 # who is halted
    meta-halt watch           # pause 'watch'
    meta-halt watch --why "runaway loop"
    meta-halt --clear watch   # let 'watch' work again

Nothing here talks to a running process: the file is the whole mechanism, which
is why it also works when the relay is down.

Exit codes
    0  done (listing always succeeds)
    1  refused: no such agent, or a stop file that could not be written/removed
    2  bad usage
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

DEFAULT_SHARE = "/usr/share/metaos/agent"


def state_root(explicit=None):
    if explicit:
        return Path(explicit).expanduser()
    if os.environ.get("METAOS_AGENT_STATE"):
        return Path(os.environ["METAOS_AGENT_STATE"]).expanduser()
    base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(base) / "oc2-agent"


def share_root():
    return Path(os.environ.get("METAOS_AGENT_SHARE", DEFAULT_SHARE)).expanduser()


def known_agents(root):
    """Names from the user's registry, else the payload's. Absence is not fatal:
    a halt for an agent that has since left the registry can still be cleared."""
    for path in (root / "registry.json", share_root() / "agents" / "registry.json",
                 share_root() / "registry.json"):
        if path.is_file():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            agents = data.get("agents") if isinstance(data, dict) else None
            if isinstance(agents, list):
                return {a.get("name") for a in agents if isinstance(a, dict)}
    return set()


def halted(root):
    """agent name -> the note left in its stop file."""
    found = {}
    stop_dir = root / "stop"
    try:
        entries = sorted(stop_dir.glob("*.STOP"))
    except OSError:
        return found
    for path in entries:
        try:
            note = path.read_text(encoding="utf-8").strip()
        except OSError:
            note = ""
        found[path.name[:-len(".STOP")]] = note
    return found


def halt(root, name, why=None):
    stop_dir = root / "stop"
    try:
        stop_dir.mkdir(parents=True, exist_ok=True)
        note = "halted %s" % time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        if why:
            note += ": " + why.strip()
        (stop_dir / (name + ".STOP")).write_text(note + "\n", encoding="utf-8")
    except OSError as exc:
        print("meta-halt: cannot write the stop file: %s" % exc, file=sys.stderr)
        return 1
    print("halted %s (jobs for it wait on the board)" % name)
    return 0


def clear(root, name):
    path = root / "stop" / (name + ".STOP")
    if not path.exists():
        print("%s was not halted" % name)
        return 0
    try:
        path.unlink()
    except OSError as exc:
        print("meta-halt: cannot remove the stop file: %s" % exc, file=sys.stderr)
        return 1
    print("%s is working again; held jobs run on the next poll" % name)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="meta-halt", add_help=True)
    parser.add_argument("agent", nargs="?", help="which agent (omit to list)")
    parser.add_argument("--clear", action="store_true", help="remove the halt")
    parser.add_argument("--why", help="note to leave in the stop file")
    parser.add_argument("--root", help="relay state directory")
    args = parser.parse_args(argv)

    root = state_root(args.root)

    if not args.agent:
        if args.clear:
            parser.error("--clear needs an agent name")
        current = halted(root)
        if not current:
            print("no agent is halted")
            return 0
        print("halted (%d):" % len(current))
        for name in sorted(current):
            print("  %-12s %s" % (name, current[name] or "-"))
        return 0

    if args.clear:
        return clear(root, args.agent)

    agents = known_agents(root)
    if agents and args.agent not in agents:
        print("meta-halt: no such agent: %s" % args.agent, file=sys.stderr)
        print("known: %s" % ", ".join(sorted(agents)), file=sys.stderr)
        return 1
    return halt(root, args.agent, args.why)


if __name__ == "__main__":
    sys.exit(main())

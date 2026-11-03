#!/usr/bin/env python3
"""meta-ask — hand one piece of work to the local agent layer.

This is the human entrance to the relay. It writes one job file onto the
watchman's board; the watchman claims it within a couple of seconds and wakes
the named agent with the orders in hand. Nothing is sent anywhere: the work
runs on this machine, under the agent's own budget and STOP rules.

    meta-ask "sweep the tree for stray licenses" --agent watch
    meta-ask --list
    meta-ask "..." --agent aegis --dry-run

Exit codes
    0  the job is on the board
    1  refused (unknown agent, draft agent, empty orders, duplicate id)
    2  bad usage, or node is missing
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

DEFAULT_SHARE = "/usr/share/metaos/agent"


def state_root(explicit=None):
    """Where the relay keeps its board. The units pass the same path to the watchman."""
    if explicit:
        return Path(explicit).expanduser()
    if os.environ.get("METAOS_AGENT_STATE"):
        return Path(os.environ["METAOS_AGENT_STATE"]).expanduser()
    base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(base) / "oc2-agent"


def share_root():
    return Path(os.environ.get("METAOS_AGENT_SHARE", DEFAULT_SHARE)).expanduser()


def load_registry(root):
    """The user's own registry wins: an account may have promoted an agent since install."""
    for path in (root / "registry.json", share_root() / "agents" / "registry.json",
                 share_root() / "registry.json"):
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            agents = data.get("agents") if isinstance(data, dict) else None
            if not isinstance(agents, list):
                raise ValueError("%s has no agents list" % path)
            return agents, path
    raise FileNotFoundError(
        "no registry found; looked in %s and %s"
        % (root / "registry.json", share_root() / "agents" / "registry.json"))


def live_agents(agents):
    return [a for a in agents
            if isinstance(a, dict) and a.get("draft") is not True
            and isinstance(a.get("command"), list) and a.get("command")]


def render_list(agents):
    live = live_agents(agents)
    drafts = [a for a in agents if isinstance(a, dict) and a.get("draft") is True]
    lines = ["agents that can work (%d):" % len(live)]
    width = max([len(a["name"]) for a in live] or [4])
    for agent in live:
        lines.append("  %-*s  %s" % (width, agent["name"], agent.get("lane") or ""))
    if drafts:
        lines.append("")
        lines.append("drafts, no program yet (%d): %s"
                     % (len(drafts), ", ".join(a["name"] for a in drafts)))
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="meta-ask", add_help=True)
    parser.add_argument("text", nargs="?", help="what the agent should do")
    parser.add_argument("--orders", help="same as the positional, for scripts")
    parser.add_argument("--agent", help="which agent takes the work")
    parser.add_argument("--id", help="job id (default: ask-<timestamp>)")
    parser.add_argument("--root", help="relay state directory")
    parser.add_argument("--list", action="store_true", help="show who can take work")
    parser.add_argument("--json", action="store_true", help="print the job as JSON")
    parser.add_argument("--dry-run", action="store_true", help="validate, write nothing")
    args = parser.parse_args(argv)

    root = state_root(args.root)
    try:
        agents, registry_path = load_registry(root)
    except (OSError, ValueError) as exc:
        print("meta-ask: %s" % exc, file=sys.stderr)
        return 1

    if args.list:
        print(render_list(agents))
        return 0

    orders = args.orders if args.orders is not None else args.text
    if not orders or not orders.strip():
        parser.error("orders are required (or use --list)")
    if not args.agent:
        parser.error("--agent is required (use --list to see who can work)")

    job_id = args.id or "ask-" + str(int(time.time()))
    if args.dry_run:
        entry = next((a for a in agents if a.get("name") == args.agent), None)
        if entry is None:
            print("meta-ask: no such agent: %s" % args.agent, file=sys.stderr)
            return 1
        if not live_agents([entry]):
            print("meta-ask: %s has no program yet (draft)" % args.agent, file=sys.stderr)
            return 1
        print("would submit %s -> %s: %s" % (job_id, args.agent, orders))
        return 0

    node = shutil.which("node") or ("/usr/bin/node" if os.path.exists("/usr/bin/node") else None)
    submit = share_root() / "agents" / "submit.mjs"
    if not submit.is_file():
        submit = Path(__file__).resolve().parents[2] / "agents" / "submit.mjs"
    if node is None:
        print("meta-ask: node is not installed; the relay cannot be fed", file=sys.stderr)
        return 2

    run = subprocess.run(
        [node, str(submit), "--root", str(root), "--registry", str(registry_path),
         "--agent", args.agent, "--orders", orders, "--id", job_id],
        capture_output=True, text=True, timeout=60)
    if run.returncode != 0:
        print((run.stderr or run.stdout).strip(), file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps({"id": job_id, "agent": args.agent, "root": str(root)}, indent=2))
    else:
        print("asked %s: %s" % (args.agent, orders))
        print("job %s is on the board at %s" % (job_id, root / "jobs"))
        print("run `meta-agent-status` to watch it")
    return 0


if __name__ == "__main__":
    sys.exit(main())

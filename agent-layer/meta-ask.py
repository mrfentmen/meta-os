#!/usr/bin/env python3
"""meta-ask — hand one piece of work to the local agent layer.

This is the human entrance to the relay. It writes one job file onto the
watchman's board; the watchman claims it within a couple of seconds and wakes
the named agent with the orders in hand. The board is drained by the relay
whose queue service answers on 127.0.0.1:8935 (see oc2-queue.service); this
tool checks that port and warns when it is down, but the write itself is a
file rename so work waits safely until the queue starts.

    meta-ask "sweep the tree for stray licenses" --agent watch
    meta-ask --list
    meta-ask "..." --agent aegis --dry-run
    meta-ask "..." --agent watch --follow      # wait, then say how it went

Exit codes
    0  the job is on the board (with --follow: it finished cleanly)
    1  refused (unknown agent, draft agent, empty orders, duplicate id)
    2  bad usage, or node is missing
    3  with --follow: the job failed, was refused by the layer, or timed out
"""

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

DEFAULT_SHARE = "/usr/share/metaos/agent"
DEFAULT_QUEUE_HOST = "127.0.0.1"
DEFAULT_QUEUE_PORT = 8935


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


def queue_port():
    try:
        return int(os.environ.get("OC2_QUEUE_PORT", str(DEFAULT_QUEUE_PORT)))
    except ValueError:
        return DEFAULT_QUEUE_PORT


def queue_answers(port=None, timeout=1.0):
    """True when the queue service on 127.0.0.1:<port> accepts a connection."""
    port = queue_port() if port is None else port
    try:
        with socket.create_connection((DEFAULT_QUEUE_HOST, port), timeout=timeout):
            return True
    except OSError:
        return False


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


def halted_names(root):
    """Who a person has paused. An agent with a stop file cannot take work."""
    try:
        return {p.name[:-len(".STOP")] for p in (root / "stop").glob("*.STOP")}
    except OSError:
        return set()


def render_list(agents, halted=frozenset()):
    live = live_agents(agents)
    drafts = [a for a in agents if isinstance(a, dict) and a.get("draft") is True]
    lines = ["agents that can work (%d):" % len(live)]
    width = max([len(a["name"]) for a in live] or [4])
    for agent in live:
        note = "  [halted]" if agent["name"] in halted else ""
        lines.append("  %-*s  %s%s" % (width, agent["name"], agent.get("lane") or "", note))
    if drafts:
        lines.append("")
        lines.append("drafts, no program yet (%d):" % len(drafts))
        # B4 — a draft refusal is explicit: --list names each draft with the
        # registry's own reason, and a submit to one is refused by submit.mjs.
        for agent in drafts:
            lines.append("  %-*s  draft: %s" % (width, agent["name"],
                                               agent.get("draftReason") or "no program yet"))
    return "\n".join(lines)


def read_result(root, job_id):
    """The watchman's receipt for one job, or None while it is still running."""
    path = root / "jobs" / (job_id + ".result.json")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def proposed_next(root, job_id):
    """The job this run gave itself, if the watchman queued one.

    A quiet read of the relay ledger: the proposal is already on the board by
    the time the result exists, so this is a report, not a promise.
    """
    ledger = root / "watchman.jsonl"
    try:
        lines = ledger.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    found = None
    for line in lines:
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if entry.get("event") == "proposal-queued" and entry.get("id") == job_id:
            found = entry.get("next")
    return found


def follow(root, job_id, timeout, interval=1.0):
    """Wait for the receipt. Returns the result, or None on timeout.

    Polling a file is honest here: the watchman writes the result with one
    write, so a file that parses is a job that finished.
    """
    deadline = time.monotonic() + timeout
    while True:
        result = read_result(root, job_id)
        if result is not None:
            return result
        if time.monotonic() >= deadline:
            return None
        time.sleep(min(interval, max(0.05, deadline - time.monotonic())))


def report(root, job_id, result):
    """Print one job's outcome the way a person reads it. Returns an exit code."""
    if result.get("refused"):
        print("job %s was refused by the layer: %s" % (job_id, result["refused"]), file=sys.stderr)
        return 3
    code = result.get("code")
    signal = result.get("signal")
    if signal is not None or (isinstance(code, int) and code != 0):
        detail = "signal %s" % signal if signal is not None else "exit %s" % code
        print("job %s failed (%s)" % (job_id, detail), file=sys.stderr)
        return 3
    print("job %s finished cleanly" % job_id)
    nxt = proposed_next(root, job_id)
    if nxt:
        print("it handed itself the next job: %s" % nxt)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="meta-ask", add_help=True)
    parser.add_argument("text", nargs="?", help="what the agent should do")
    parser.add_argument("--orders", help="same as the positional, for scripts")
    parser.add_argument("--agent", help="which agent takes the work")
    parser.add_argument("--id", help="job id (default: ask-<timestamp>)")
    parser.add_argument("--root", help="relay state directory")
    parser.add_argument("--list", action="store_true", help="show who can work")
    parser.add_argument("--json", action="store_true", help="print the job as JSON")
    parser.add_argument("--dry-run", action="store_true", help="validate, write nothing")
    parser.add_argument("--follow", action="store_true", help="wait for the result, then report it")
    parser.add_argument("--timeout", type=float, default=120.0,
                        help="seconds to wait with --follow (default 120)")
    args = parser.parse_args(argv)

    root = state_root(args.root)
    try:
        agents, registry_path = load_registry(root)
    except (OSError, ValueError) as exc:
        print("meta-ask: %s" % exc, file=sys.stderr)
        return 1

    if args.list:
        print(render_list(agents, halted_names(root)))
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
        submit = Path(__file__).resolve().parents[1] / "agents" / "submit.mjs"
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
        if not queue_answers():
            print("warning: queue on %s:%d not answering; job waits until it starts"
                  % (DEFAULT_QUEUE_HOST, queue_port()), file=sys.stderr)
        if not args.follow:
            print("run `meta-agent-status` to watch it")

    if not args.follow:
        return 0
    result = follow(root, job_id, args.timeout)
    if result is None:
        print("job %s is still running after %gs; see `meta-agent-status`"
              % (job_id, args.timeout), file=sys.stderr)
        return 3
    return report(root, job_id, result)


if __name__ == "__main__":
    sys.exit(main())

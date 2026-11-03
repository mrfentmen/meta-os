"""meta-ask is the human entrance to the relay. If it lies, work vanishes:

a job written for a name nobody runs sits on the board forever, and a job that
was refused looks the same as one that was never asked for. These tests drive
the real script against a real temp board.
"""

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
META_ASK = REPO / "iso" / "apps" / "agent-status" / "meta-ask.py"
AGENTS = REPO / "agents"

REGISTRY = {
    "agents": [
        {"name": "watch", "lane": "iso", "command": ["true"]},
        {"name": "aegis", "lane": "chaos", "command": ["true"]},
        {"name": "pax", "lane": "relay", "draft": True},
    ]
}


def board(tmp_path):
    (tmp_path / "registry.json").write_text(json.dumps(REGISTRY), encoding="utf-8")
    (tmp_path / "jobs").mkdir()
    return tmp_path


def env_for(tmp_path):
    return {
        "PATH": "/usr/bin:/bin:/usr/local/bin",
        "HOME": str(tmp_path),
        "METAOS_AGENT_STATE": str(tmp_path),
        "METAOS_AGENT_SHARE": str(AGENTS.parent),
    }


def ask(tmp_path, *args):
    return subprocess.run(
        [sys.executable, str(META_ASK), *args],
        capture_output=True, text=True, env=env_for(tmp_path), timeout=60,
    )


def ask_bg(tmp_path, *args):
    return subprocess.Popen(
        [sys.executable, str(META_ASK), *args],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env_for(tmp_path),
    )


@pytest.fixture(autouse=True)
def needs_node():
    if shutil.which("node") is None:
        pytest.skip("node is not installed; the relay cannot be fed")


def test_list_names_who_can_work_and_who_cannot(tmp_path):
    root = board(tmp_path)
    run = ask(root, "--list")
    assert run.returncode == 0, run.stderr
    assert "agents that can work (2)" in run.stdout
    assert "watch" in run.stdout and "aegis" in run.stdout
    # A draft is shown, but never as somebody who can take work.
    assert "drafts, no program yet (1): pax" in run.stdout


def test_a_job_lands_on_the_board_with_its_lane(tmp_path):
    root = board(tmp_path)
    run = ask(root, "sweep the tree for stray licenses", "--agent", "watch", "--id", "j1")
    assert run.returncode == 0, run.stderr

    job = json.loads((root / "jobs" / "j1.job.json").read_text(encoding="utf-8"))
    assert job["agent"] == "watch"
    assert job["orders"] == "sweep the tree for stray licenses"
    assert job["lane"] == "iso"
    assert job["id"] == "j1"


def test_an_unknown_agent_is_refused_and_nothing_is_written(tmp_path):
    root = board(tmp_path)
    run = ask(root, "do something", "--agent", "nobody", "--id", "j2")
    assert run.returncode == 1
    assert "no such agent: nobody" in run.stderr
    assert not list((root / "jobs").iterdir())


def test_a_draft_agent_is_refused(tmp_path):
    root = board(tmp_path)
    run = ask(root, "do something", "--agent", "pax", "--id", "j3")
    assert run.returncode == 1
    assert "no program yet" in run.stderr
    assert not list((root / "jobs").iterdir())


def test_dry_run_prints_the_job_and_writes_nothing(tmp_path):
    root = board(tmp_path)
    run = ask(root, "look at the boot log", "--agent", "aegis", "--id", "j4", "--dry-run")
    assert run.returncode == 0, run.stderr
    assert "would submit j4 -> aegis" in run.stdout
    assert not list((root / "jobs").iterdir())


def test_the_same_id_twice_is_refused(tmp_path):
    root = board(tmp_path)
    assert ask(root, "one", "--agent", "watch", "--id", "j5").returncode == 0
    second = ask(root, "two", "--agent", "watch", "--id", "j5")
    assert second.returncode == 1
    assert "already on the board" in second.stderr
    job = json.loads((root / "jobs" / "j5.job.json").read_text(encoding="utf-8"))
    assert job["orders"] == "one", "the first job is not overwritten"


def wait_for_result(tmp_path, job_id, result):
    """Write a receipt the way the watchman does, once the asker is waiting."""
    target = tmp_path / "jobs" / (job_id + ".result.json")
    for _ in range(200):
        if (tmp_path / "jobs" / (job_id + ".job.json")).exists():
            break
        time.sleep(0.02)
    target.write_text(json.dumps(result), encoding="utf-8")


def test_follow_waits_and_reports_a_clean_finish(tmp_path):
    root = board(tmp_path)
    proc = ask_bg(root, "sweep the shelf", "--agent", "watch", "--id", "f1",
                  "--follow", "--timeout", "10")
    wait_for_result(root, "f1", {"id": "f1", "agent": "watch", "code": 0, "signal": None})
    # The agent also handed itself a job; --follow names it.
    with (root / "watchman.jsonl").open("a", encoding="utf-8") as ledger:
        ledger.write(json.dumps({"event": "proposal-queued", "id": "f1", "next": "f1-n1"}) + "\n")
    out, err = proc.communicate(timeout=20)
    assert proc.returncode == 0, err
    assert "finished cleanly" in out
    assert "f1-n1" in out, out


def test_follow_reports_a_failure_as_a_failure(tmp_path):
    root = board(tmp_path)
    proc = ask_bg(root, "break something", "--agent", "watch", "--id", "f2",
                  "--follow", "--timeout", "10")
    wait_for_result(root, "f2", {"id": "f2", "code": 2, "signal": None})
    out, err = proc.communicate(timeout=20)
    assert proc.returncode == 3, (out, err)
    assert "failed (exit 2)" in err


def test_follow_reports_a_refusal(tmp_path):
    root = board(tmp_path)
    proc = ask_bg(root, "eat all the memory", "--agent", "watch", "--id", "f3",
                  "--follow", "--timeout", "10")
    wait_for_result(root, "f3", {"id": "f3", "refused": "memory-cap"})
    out, err = proc.communicate(timeout=20)
    assert proc.returncode == 3, (out, err)
    assert "refused by the layer: memory-cap" in err


def test_follow_gives_up_instead_of_hanging(tmp_path):
    root = board(tmp_path)
    run = ask(root, "nobody will run this", "--agent", "watch", "--id", "f4",
              "--follow", "--timeout", "0.5")
    assert run.returncode == 3, run.stderr
    assert "still running" in run.stderr


def test_empty_orders_is_a_usage_error(tmp_path):
    root = board(tmp_path)
    run = ask(root, "   ", "--agent", "watch")
    assert run.returncode == 2
    assert not list((root / "jobs").iterdir())

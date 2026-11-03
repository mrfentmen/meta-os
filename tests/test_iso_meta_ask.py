"""meta-ask is the human entrance to the relay. If it lies, work vanishes:

a job written for a name nobody runs sits on the board forever, and a job that
was refused looks the same as one that was never asked for. These tests drive
the real script against a real temp board.
"""

import json
import shutil
import subprocess
import sys
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


def ask(tmp_path, *args):
    env = {
        "PATH": "/usr/bin:/bin:/usr/local/bin",
        "HOME": str(tmp_path),
        "METAOS_AGENT_STATE": str(tmp_path),
        "METAOS_AGENT_SHARE": str(AGENTS.parent),
    }
    return subprocess.run(
        [sys.executable, str(META_ASK), *args],
        capture_output=True, text=True, env=env, timeout=60,
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


def test_empty_orders_is_a_usage_error(tmp_path):
    root = board(tmp_path)
    run = ask(root, "   ", "--agent", "watch")
    assert run.returncode == 2
    assert not list((root / "jobs").iterdir())

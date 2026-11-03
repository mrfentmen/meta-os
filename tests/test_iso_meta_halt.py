"""meta-halt is how a person stops one agent without hunting for a path.

The mechanism is a file the watchman already reads, so these tests check the
file, not a process: write it, list it, clear it, and refuse a name that does
not exist.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
META_HALT = REPO / "iso" / "apps" / "agent-status" / "meta-halt.py"
AGENTS = REPO / "agents"

REGISTRY = {"agents": [
    {"name": "watch", "lane": "iso", "command": ["true"]},
    {"name": "aegis", "lane": "chaos", "command": ["true"]},
]}


def root(tmp_path):
    (tmp_path / "registry.json").write_text(json.dumps(REGISTRY), encoding="utf-8")
    return tmp_path


def run(tmp_path, *args):
    env = {
        "PATH": "/usr/bin:/bin:/usr/local/bin",
        "HOME": str(tmp_path),
        "METAOS_AGENT_STATE": str(tmp_path),
        "METAOS_AGENT_SHARE": str(AGENTS.parent),
    }
    return subprocess.run(
        [sys.executable, str(META_HALT), *args],
        capture_output=True, text=True, env=env, timeout=30,
    )


def test_nothing_halted_says_so(tmp_path):
    out = run(root(tmp_path))
    assert out.returncode == 0, out.stderr
    assert "no agent is halted" in out.stdout


def test_halt_writes_the_file_the_watchman_reads(tmp_path):
    here = root(tmp_path)
    out = run(here, "watch", "--why", "runaway loop")
    assert out.returncode == 0, out.stderr
    stop = here / "stop" / "watch.STOP"
    assert stop.is_file()
    assert "runaway loop" in stop.read_text(encoding="utf-8")


def test_the_list_names_who_is_halted_and_why(tmp_path):
    here = root(tmp_path)
    run(here, "watch")
    run(here, "aegis", "--why", "auditing")
    out = run(here)
    assert out.returncode == 0, out.stderr
    assert "halted (2):" in out.stdout
    assert "aegis" in out.stdout and "auditing" in out.stdout


def test_clearing_a_halt_removes_the_file(tmp_path):
    here = root(tmp_path)
    run(here, "watch")
    out = run(here, "--clear", "watch")
    assert out.returncode == 0, out.stderr
    assert not (here / "stop" / "watch.STOP").exists()
    assert "working again" in out.stdout


def test_clearing_something_that_was_not_halted_is_not_an_error(tmp_path):
    out = run(root(tmp_path), "--clear", "watch")
    assert out.returncode == 0, out.stderr
    assert "was not halted" in out.stdout


def test_an_unknown_agent_is_refused(tmp_path):
    here = root(tmp_path)
    out = run(here, "nobody")
    assert out.returncode == 1
    assert "no such agent: nobody" in out.stderr
    assert not (here / "stop" / "nobody.STOP").exists()


def test_meta_ask_list_marks_a_halted_agent(tmp_path):
    here = root(tmp_path)
    (here / "jobs").mkdir()
    run(here, "watch")
    env = {
        "PATH": "/usr/bin:/bin:/usr/local/bin",
        "HOME": str(here),
        "METAOS_AGENT_STATE": str(here),
        "METAOS_AGENT_SHARE": str(AGENTS.parent),
    }
    out = subprocess.run(
        [sys.executable, str(META_ASK), "--list"],
        capture_output=True, text=True, env=env, timeout=30,
    )
    assert out.returncode == 0, out.stderr
    assert "watch" in out.stdout and "[halted]" in out.stdout


META_ASK = REPO / "iso" / "apps" / "agent-status" / "meta-ask.py"


@pytest.fixture(autouse=True)
def needs_node():
    import shutil
    if shutil.which("node") is None:
        pytest.skip("the relay needs node")

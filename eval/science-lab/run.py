#!/usr/bin/env python3
"""Science Lab eval runner: 28 grounded scenarios, no model, no network.

Every scenario runs the real os/worlds/science-lab/hosted.py against a
temporary copy of the real shipped records, or against the real
agents/registry.json. Duty scenarios read the receipt file the duty
itself writes (first stdout line: "science: <agent> -> <path>") so the
full, untruncated findings are checked, not the 300-char stdout echo.

Usage: python3 eval/science-lab/run.py [--out report.json]
Exit 0 only when every scenario passes. Report JSON is deterministic:
no timestamps, results sorted by scenario id.
"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "os" / "worlds" / "science-lab"
HOSTED = LAB / "hosted.py"
RECORDS = LAB / "records"
REGISTRY = ROOT / "agents" / "registry.json"
HERE = Path(__file__).resolve().parent


def load_scenarios():
    with open(HERE / "scenarios.json", encoding="utf-8") as fh:
        return json.load(fh)


def run_hosted(agent, records, check):
    cmd = [sys.executable, str(HOSTED), "--agent", agent,
           "--records", str(records)]
    if check:
        cmd.append("--check")
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    return proc


def check_scenario(sc, records):
    proc = run_hosted(sc["agent"], records, check=True)
    ok = (proc.returncode == sc["expected_exit"]
          and proc.stdout.startswith("ok: %s can read " % sc["agent"]))
    return ok, {"exit": proc.returncode, "stdout": proc.stdout.strip()[:200]}


def duty_scenario(sc, records):
    proc = run_hosted(sc["agent"], records, check=False)
    if proc.returncode != sc["expected_exit"]:
        return False, {"exit": proc.returncode, "stderr": proc.stderr[:200]}
    first = proc.stdout.splitlines()[0] if proc.stdout else ""
    if not first.startswith("science: %s -> " % sc["agent"]):
        return False, {"exit": proc.returncode, "stdout": first[:200]}
    receipt_path = Path(first.split(" -> ", 1)[1].strip())
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return False, {"exit": proc.returncode, "error": str(exc)}
    findings = receipt.get("findings") or []
    checks = [f.get("check") for f in findings]
    if "expected_check" in sc:
        ok = (receipt.get("agent") == sc["agent"] and receipt.get("ok") is True
              and sc["expected_check"] in checks)
    else:
        # Duties whose success rows carry no "check" key (research-director
        # returns a per-cycle census) are asserted on row shape + rows.
        ok = (receipt.get("agent") == sc["agent"] and receipt.get("ok") is True
              and bool(findings)
              and all(all(k in f for k in sc["expected_keys"]) for f in findings)
              and sorted(f.get("cycle") for f in findings) == sorted(sc["expected_cycles"]))
    return ok, {"exit": proc.returncode, "checks": checks}


def registry_scenario(doc):
    try:
        with open(REGISTRY, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as exc:
        return False, {"error": str(exc)}
    agents = data if isinstance(data, list) else data.get("agents", [])
    by_name = {a.get("name"): a for a in agents}
    missing, wrong = [], []
    for name in sorted(doc["agents"]):
        entry = by_name.get(name)
        if entry is None:
            missing.append(name)
            continue
        want = ["python3", "repo:os/worlds/science-lab/hosted.py",
                "--agent", name]
        if entry.get("command") != want or entry.get("hosted") is not True:
            wrong.append(name)
    ok = not missing and not wrong
    return ok, {"missing": missing, "wrong": wrong,
                "agents_checked": len(doc["agents"])}


def refusal_scenario(sc, records):
    proc = run_hosted(sc["agent"], records, check=False)
    ok = (proc.returncode == sc["expected_exit"]
          and sc["expected_stderr"] in proc.stderr)
    return ok, {"exit": proc.returncode, "stderr": proc.stderr.strip()[:200]}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    out = None
    if "--out" in argv:
        out = Path(argv[argv.index("--out") + 1])
    doc = load_scenarios()
    results = []
    with tempfile.TemporaryDirectory(prefix="sl-eval-") as tmp:
        records = Path(tmp) / "records"
        shutil.copytree(RECORDS, records)
        for sc in sorted(doc["scenarios"], key=lambda s: s["id"]):
            kind = sc["kind"]
            if kind == "check":
                ok, detail = check_scenario(sc, records)
            elif kind == "duty":
                ok, detail = duty_scenario(sc, records)
            elif kind == "registry":
                ok, detail = registry_scenario(doc)
            elif kind == "refusal":
                ok, detail = refusal_scenario(sc, records)
            else:
                ok, detail = False, {"error": "unknown kind %r" % kind}
            results.append({"id": sc["id"], "kind": kind, "pass": ok,
                            "detail": detail})
    passed = sum(1 for r in results if r["pass"])
    report = {"scenarios": len(results), "passed": passed,
              "failed": len(results) - passed, "results": results}
    text = json.dumps(report, indent=2, sort_keys=True)
    if out is not None:
        out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())

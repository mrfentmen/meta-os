#!/usr/bin/env python3
"""Verify the generated catalog.

For every generated SKILL.md: check the house sections, then deduplicate the
code blocks by hash and execute each distinct program (python3, node, rustc).
A generated file that embeds an unverified block cannot pass, because the
block hash must appear in the verified set.
"""
import hashlib
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MARKER = "<!-- generated from _tools/catalog.py"
REQUIRED = [
    ("scope", r"^## Scope"),
    ("minimum requirements", r"^## Minimum Requirements"),
    ("activation", r"^## Activation"),
    ("workflow", r"^## Workflow"),
    ("core principles", r"^## Core Principles"),
    ("style", r"^## Style Guidelines"),
    ("cross-language", r"^## Cross-Language Examples"),
    ("safety", r"^## Safety"),
    ("boundaries", r"^## Boundaries, when NOT to use this skill"),
]


def run(cmd, **kwargs):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=120, **kwargs)


def main() -> int:
    files = sorted(p for p in ROOT.glob("*/SKILL.md"))
    generated = [p for p in files if MARKER in p.read_text(encoding="utf-8")]
    problems = []

    blocks = {"python": {}, "javascript": {}, "rust": {}}
    for path in generated:
        text = path.read_text(encoding="utf-8")
        name = path.parent.name
        for label, pattern in REQUIRED:
            if not re.search(pattern, text, re.M):
                problems.append(f"{name}: missing {label}")
        m = re.search(r"^description: >-\n(.*?)^---", text, re.S | re.M)
        if not m or len(m.group(1).strip()) <= 400:
            problems.append(f"{name}: description too short")
        for language in blocks:
            found = re.findall(rf"```{language}\n(.*?)```", text, re.S)
            if len(found) != 1:
                problems.append(f"{name}: expected one {language} block, found {len(found)}")
                continue
            digest = hashlib.sha256(found[0].encode()).hexdigest()[:12]
            blocks[language][digest] = found[0]

    results = {}
    for language, items in blocks.items():
        passed = 0
        failed = []
        for digest, body in sorted(items.items()):
            if language == "python":
                r = run([sys.executable, "-c", body], input="")
            elif language == "javascript":
                with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as fh:
                    fh.write(body)
                    path = fh.name
                r = run(["node", path])
                os.unlink(path)
            else:
                base = tempfile.mktemp()
                source = base + ".rs"
                with open(source, "w", encoding="utf-8") as fh:
                    fh.write(body)
                compiled = run(["rustc", "-O", source, "-o", base])
                os.unlink(source)
                if compiled.returncode != 0:
                    r = compiled
                else:
                    r = run([base])
                    os.unlink(base)
            if r.returncode == 0:
                passed += 1
            else:
                tail = (r.stderr or r.stdout).strip().splitlines()
                failed.append((digest, tail[-1] if tail else "no output"))
        results[language] = (passed, len(items), failed)

    print(f"skills: {len(files)} total, {len(generated)} generated")
    for language, (passed, total, failed) in results.items():
        print(f"  {language}: {passed}/{total} distinct blocks pass")
        for digest, error in failed:
            print(f"    FAIL {digest}: {error}")
            problems.append(f"{language} block {digest}: {error}")

    for problem in problems:
        print("PROBLEM:", problem)
    print("problems:", len(problems))
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())

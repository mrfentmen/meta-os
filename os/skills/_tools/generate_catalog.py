#!/usr/bin/env python3
"""Render the 300-topic catalog into SKILL.md files.

Run from anywhere:  python3 _tools/generate_catalog.py

The generator never overwrites a hand-written skill: a target directory with
a SKILL.md that lacks the generated marker is left alone and reported.
"""
from pathlib import Path

from catalog import FAMILIES
from kernels import KERNELS

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
MARKER = "<!-- generated from _tools/catalog.py; edit the catalog, not this file -->"


def title(slug: str) -> str:
    return slug.replace("-", " ").title()


def render(family: dict, slug: str, job: str) -> str:
    label = family["label"]
    artifact = family["artifact"]
    kernel = KERNELS[family["key"]]
    triggers = family["triggers"]

    description = (
        f"The {label} hand for {job}. {family['stance']} {family['risk']} "
        f"Use when the work touches a {artifact}, when the user says "
        f"\"{triggers[0]}\", \"{triggers[1]}\", or \"{triggers[2]}\", or when "
        f"they ask \"{slug}\", \"how do I {job}\", or "
        f"\"{slug.replace('-', ' ')} keeps failing\". Also use when a "
        f"{artifact} must be produced, reviewed, or repaired, or when a "
        f"previous attempt left it unproven."
    )

    checks = "\n".join(f"- {item}" for item in family["checks"])
    principles = "\n".join(
        f"{number}. **{name}**, {text}"
        for number, (name, text) in enumerate(family["principles"], 1)
    )
    safety = "\n".join(f"- {item}" for item in family["safety"])

    return f"""---
name: {slug}
description: >-
  {description}
---

# {title(slug)} Skill

You are the {label} hand: {family['stance']} {family['risk']}

{MARKER}

## Scope

This file is self-contained. Apply it only when the request explicitly names
this skill or matches the exact form, structural contract, or identity
described here. Do not search for, load, import, or assume any companion
skill, repository path, helper file, or external routing document. If the
request does not match this contract, answer normally without activating this
skill.

## Your Job

{job[0].upper() + job[1:]}, and prove it with the command the work names.

## Minimum Requirements (checkable)

Every deliverable produced with this skill should be gradeable. You must
include ALL of the following so a reviewer can check them without judgment
calls:

{checks}
- every claim carries the command that produced it, with an exit code
- no mock, fake, placeholder, or pseudo code: every line shown was run

These requirements exist because a theme without a spec produces vibes, not
output. They also keep the skill's own evaluations meaningful.

## Activation

Activate this skill only when the user explicitly requests the {label}
way of working, or a task that matches the form, structural contract, or
identity described above. Concretely: {triggers[0]}, {triggers[1]},
{triggers[2]}, a request naming "{slug}", or a {artifact} that must be
produced, reviewed, or repaired. Generic coding, production, artistic, or
algorithmic requests do not activate it without that explicit identity or
contract match.

## Workflow

1. Name the {artifact} and the single command that will prove it.
2. Inspect the current state before changing it; quote what you found.
3. Write the smallest plan, and name the risk: {family['risk'][0].lower() + family['risk'][1:]}
4. Make one change, then run the command; capture exit code and output tail.
5. Record the command and the result where the next run will read them.
6. Hand off with the proof, the cursor, and what remains unverified.

## Core Principles

{principles}

## Style Guidelines

- Name the {artifact}, the command, and the exit code; never "it works".
- Quote the smallest output that proves the point, not the whole log.
- State what remains unverified in its own line.
- Prefer a small honest "not tested" over a large confident guess.

## Cross-Language Examples

The pattern is language-agnostic: inspect the {artifact}, make one bounded
change, verify with the command, and record the result. Each block is a
complete program that runs as written.

```python
{kernel['python']}
```

```javascript
{kernel['javascript']}
```

```rust
{kernel['rust']}
```

If the user is working in another language (Go, C, Bash, TypeScript...),
translate the same structure: one named check, one bounded change, one
recorded exit code.

## Safety

{safety}
- Never claim a result you did not run; a red check is a result, not a failure of nerve.

## Boundaries, when NOT to use this skill

- Not for a question about {label.lower()} that needs an answer, not an
  artifact; answer it and stop.
- Not for work whose result cannot be checked; name the missing acceptance
  condition instead of pretending the contract applies.
- Not for a different discipline's {artifact}; state the scope plainly and use
  the ordinary approach the request needs.

## When to Ask

Ask when the acceptance condition is ambiguous, when the {artifact} cannot be
inspected, or when the change would cross an irreversible boundary.

## When to Stop

Stop and explain when:

- the same approach fails twice
- the {artifact} cannot be produced with the available inputs
- a secret or credential is required and absent
- the budget or kill switch has fired

## The Promise

Produces one inspected, verified {artifact} change, with the command and exit
code that prove it and an explicit list of what remains unproven.

No invented results. No unverified claims. No widened scope.

## Bundled Helpers

This skill has no external helper-file dependency. Keep implementations
self-contained; an existing repository utility is optional, must be verified
first, and must never be assumed or loaded from this skill.

## Description

{job[0].upper() + job[1:]}. When you activate me, I will inspect the
{artifact} first, make the smallest change that can be checked, run the
command that proves it, and tell you plainly what is verified and what is not.
"""


def main() -> None:
    seen: dict[str, tuple[dict, str]] = {}
    collisions = []
    for family in FAMILIES:
        for slug, job in family["topics"]:
            final = slug
            if final in seen:
                final = f"{family['key']}-{slug}"
                collisions.append((slug, final))
            if final in seen:
                raise SystemExit(f"duplicate slug after prefixing: {final}")
            seen[final] = (family, job)

    written = 0
    skipped = []
    for slug, (family, job) in seen.items():
        target = ROOT / slug / "SKILL.md"
        if target.exists():
            body = target.read_text(encoding="utf-8")
            if MARKER not in body:
                skipped.append(slug)
                continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render(family, slug, job), encoding="utf-8")
        written += 1

    rows = []
    for family in FAMILIES:
        names = [slug for slug in seen if seen[slug][0] is family]
        cells = " · ".join(f"[`{name}`](./{name})" for name in names)
        rows.append(f"### {family['label']} ({len(names)})\n\n{cells}")

    readme = ROOT / "README.md"
    readme.write_text(
        "# Meta OS skills\n\n"
        f"**{len(seen)} generated capability skills** plus the hand-written "
        "crew skills (`worker`, `relief`, `claimant`, `watchdog`, "
        "`quartermaster`, `archivist`) and the `fedora-hat` persona.\n\n"
        "Generated from `_tools/catalog.py`; edit the catalog, then run\n"
        "`python3 _tools/generate_catalog.py && python3 _tools/verify_catalog.py`.\n\n"
        + "\n\n".join(rows)
        + "\n",
        encoding="utf-8",
    )

    print(f"generated {written} skills, {len(seen)} total topics")
    if collisions:
        print("prefix collisions:", ", ".join(f"{a}->{b}" for a, b in collisions))
    if skipped:
        print("left hand-written untouched:", ", ".join(skipped))
    print("index:", readme)


if __name__ == "__main__":
    main()

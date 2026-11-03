#!/usr/bin/env python3
"""Install the Meta OS skill collection into a runtime root.

The image keeps `/var/lib/metaos/skills` empty on purpose; this is the
later install step that fills it. The install is staged next to the
destination, verified against a hash manifest, and only then swapped in,
so a crash cannot leave a half-copied collection behind.

Usage:
  python3 _tools/install.py --root /var/lib/metaos/skills
  python3 _tools/install.py --root /var/lib/metaos/skills --check
  python3 _tools/install.py --root /tmp/skills --force

Exit codes: 0 installed/verified, 1 verification or install failed,
2 refused (bad source, non-empty root without --force, bad arguments).
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path

FORMAT = "metaos-skills-collection"
VERSION = 1
MARKER = ".metaos-skills-root"
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
HERE = Path(__file__).resolve().parent
DEFAULT_SOURCE = HERE.parent


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def frontmatter(text):
    text = text.replace("\r\n", "\n")
    if not text.startswith("---\n"):
        return ""
    end = text.find("\n---\n", 4)
    return text[4:end] if end >= 0 else ""


def declared_name(text):
    match = re.search(r"^name:[ \t]*(\S+)[ \t]*$", frontmatter(text), re.M)
    return match.group(1) if match else None


def skill_dirs(source):
    return sorted(
        path for path in source.iterdir()
        if path.is_dir()
        and path.name != "_tools"
        and (path / "SKILL.md").is_file()
    )


def validate(source):
    """Return (names, errors) before anything is copied."""
    names = []
    errors = []
    paths = skill_dirs(source)
    if not paths:
        errors.append(f"{source}: no skill directories with SKILL.md")
    for path in paths:
        name = path.name
        if not NAME_RE.match(name):
            errors.append(f"{name}: invalid skill directory name")
            continue
        try:
            text = (path / "SKILL.md").read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(f"{name}: cannot read SKILL.md: {exc}")
            continue
        declared = declared_name(text)
        if declared != name:
            errors.append(f"{name}: frontmatter name is {declared!r}")
        for entry in path.rglob("*"):
            if entry.is_symlink():
                errors.append(
                    f"{name}: symlink {entry.relative_to(path).as_posix()} "
                    f"(refused; copy real files)")
        names.append(name)
    return names, errors


def manifest_for(root, source):
    skills = {}
    for path in skill_dirs(root):
        files = {}
        for file in sorted(p for p in path.rglob("*") if p.is_file()):
            files[file.relative_to(path).as_posix()] = sha256_file(file)
        skills[path.name] = {"path": path.name, "files": files}
    return {
        "format": FORMAT,
        "version": VERSION,
        "source": str(source),
        "installed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "skills": skills,
    }


def verify(root):
    """Return a list of problems; empty means the collection is intact."""
    root = Path(root)
    manifest_path = root / "skills.json"
    if not manifest_path.is_file():
        return [f"{root}: skills.json is missing"]
    try:
        document = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f"{root}: skills.json is unreadable: {exc}"]
    if document.get("format") != FORMAT:
        return [f"{root}: manifest format is {document.get('format')!r}"]
    if document.get("version") != VERSION:
        return [f"{root}: manifest version is {document.get('version')!r}"]
    skills = document.get("skills")
    if not isinstance(skills, dict) or not skills:
        return [f"{root}: manifest lists no skills"]
    problems = []
    for name, record in sorted(skills.items()):
        path = root / name
        if not path.is_dir():
            problems.append(f"{name}: skill directory is missing")
            continue
        expected = record.get("files") if isinstance(record, dict) else None
        if not isinstance(expected, dict) or not expected:
            problems.append(f"{name}: manifest has no file hashes")
            continue
        actual = {
            file.relative_to(path).as_posix()
            for file in path.rglob("*") if file.is_file()
        }
        if actual != set(expected):
            problems.append(
                f"{name}: file set changed "
                f"(extra={sorted(actual - set(expected))}, "
                f"missing={sorted(set(expected) - actual)})")
        for rel, digest in sorted(expected.items()):
            file = path / rel
            if not file.is_file():
                problems.append(f"{name}: {rel} is missing")
                continue
            if sha256_file(file) != digest:
                problems.append(f"{name}: {rel} hash mismatch")
    return problems


def install(source, root, force=False):
    source = Path(source).resolve()
    root = Path(root).resolve()
    if not source.is_dir():
        print(f"ERROR: source is not a directory: {source}", file=sys.stderr)
        return 2
    names, errors = validate(source)
    if errors:
        for error in errors[:10]:
            print(f"ERROR: {error}", file=sys.stderr)
        return 2
    if root.exists() and not root.is_dir():
        print(f"ERROR: {root} exists and is not a directory", file=sys.stderr)
        return 2
    if root.exists():
        entries = [entry for entry in root.iterdir() if entry.name != MARKER]
        if entries and not force:
            print(
                f"ERROR: {root} is not empty; pass --force to replace it",
                file=sys.stderr)
            return 2
    root.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(
        prefix=root.name + ".staging-", dir=str(root.parent)))
    backup = None
    try:
        for name in names:
            shutil.copytree(source / name, stage / name)
        if root.exists() and (root / MARKER).is_file():
            shutil.copy2(root / MARKER, stage / MARKER)
        manifest = manifest_for(stage, source)
        (stage / "skills.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8")
        problems = verify(stage)
        if problems:
            raise RuntimeError("staged collection failed verification: "
                               + "; ".join(problems[:3]))
        if root.exists():
            backup = root.with_name(root.name + f".old-{os.getpid()}")
            if backup.exists():
                shutil.rmtree(backup)
            root.rename(backup)
        stage.rename(root)
        stage = None
        if backup is not None:
            shutil.rmtree(backup, ignore_errors=True)
            backup = None
        print(f"INSTALLED {len(names)} skills -> {root}")
        return 0
    except Exception as exc:
        print(f"ERROR: install failed: {exc}", file=sys.stderr)
        if stage is not None and stage.exists():
            shutil.rmtree(stage, ignore_errors=True)
        if backup is not None and backup.exists() and not root.exists():
            backup.rename(root)
        return 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True,
                        help="destination collection root")
    parser.add_argument("--source", default=str(DEFAULT_SOURCE),
                        help="catalog source (default: os/skills)")
    parser.add_argument("--force", action="store_true",
                        help="replace a non-empty destination")
    parser.add_argument("--check", action="store_true",
                        help="verify an existing install, copy nothing")
    args = parser.parse_args(argv)
    if args.check:
        problems = verify(args.root)
        if problems:
            for problem in problems[:20]:
                print(f"FAIL: {problem}", file=sys.stderr)
            return 1
        document = json.loads(
            (Path(args.root) / "skills.json").read_text(encoding="utf-8"))
        print(f"OK {len(document['skills'])} skills -> {Path(args.root).resolve()}")
        return 0
    return install(args.source, args.root, force=args.force)


if __name__ == "__main__":
    sys.exit(main())

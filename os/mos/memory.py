"""OS-078: memory service (minimal), first light.

An OS-level store every agent process inherits: a per-agent
memory plus a shared crew memory, journaled and versioned,
mounted into the process at start the way an OS mounts a home
directory. A process wakes up already knowing what it knew
yesterday and what the crew settled while it was off. Layout
under a store root (default /var/lib/metaos/memory on the
image, baked by os/build-image.sh, os/build-live.sh, and the
Packer template as an empty directory plus a marker file, and
ensured at boot by os/services/relay-memory.service):

    <root>/agents/<nick>/journal.jsonl
    <root>/shared/journal.jsonl

Each journal is append-only JSON lines, one per write. A
version counts from 1 per key inside its namespace, so the
per-agent and shared namespaces version independently: the
same key written by an agent and by the crew are two
different entries with their own histories. A write of text
identical to the key's latest entry is a no-op that returns
the current entry with "new_version" False and appends
nothing: re-stating what memory already holds is not a new
version of it, and inventing one would lie about the
history. Reading never guesses: a missing key, a missing
namespace, or a version number past the end raises instead
of returning a neighboring entry.

Rules, all enforced here and pinned by tests:

- Agent nicks are single path segments (letters, digits,
  dot, underscore, hyphen). A slash in a nick is refused.
- Keys are relative paths below the namespace directory.
  Absolute paths, empty segments, "." and ".." segments,
  backslashes, and NUL bytes are refused, so a write can
  never escape the store.
- A journal line that does not parse, or does not carry the
  entry shape, raises on read: a corrupt journal is a
  loud failure, never a silently skipped memory.
- read_all() returns the agent's own latest entries and the
  shared latest entries under separate keys, never merged:
  own and shared are different namespaces, and merging them
  would invent a precedence rule this batch does not own.
- Cross-agent reads are not offered. A process reads its
  own memory and the shared crew memory; reading another
  agent's private memory is the OS-086 scoping question,
  which is Phase B, not a default this module smuggles in.
- mount_paths() names the two directories a launcher
  mounts into a process (own memory home, shared shelf).
  The launchers themselves do not mount them yet: process
  start wiring is owed beside OS-080's launcher wiring, and
  the OS-102 loader already symlinks bundle memory mounts
  to directories this store root provides on the image.

What this batch does NOT claim (stated plainly, as every
first-light batch in this repo does): no image build has run
from this tree in the sandbox, so memory on a booted image
is unproven; no process has launched with these directories
mounted yet; the boot brief reading settled decisions from
this store is OS-079 (Hana), not done here; and scoping
enforcement, compaction, and retention are the Phase B
depth tasks (OS-086, OS-087, OS-089 pattern), not done
here. No bus post, no live Redis, no network: the store is
local files only.
"""

import json
import os
import sys
import time

STORE_ROOT_DEFAULT = "/var/lib/metaos/memory"
AGENTS_DIR = "agents"
SHARED_DIR = "shared"
JOURNAL_NAME = "journal.jsonl"


class MemoryError(ValueError):
    """Refused write, bad nick or key, missing entry, corrupt journal."""


def _validate_agent(agent):
    if not isinstance(agent, str) or not agent:
        raise MemoryError("agent nick must be a non-empty string")
    bad = set("/\\") | {"\x00"}
    if any(ch in bad for ch in agent) or agent in (".", ".."):
        raise MemoryError("agent nick must be a single path segment")
    if not all(ch.isalnum() or ch in "._-" for ch in agent):
        raise MemoryError("agent nick holds characters outside [A-Za-z0-9._-]")
    return agent


def _validate_key(key):
    if not isinstance(key, str) or not key:
        raise MemoryError("memory key must be a non-empty string")
    if key.startswith("/") or "\x00" in key or "\\" in key:
        raise MemoryError("memory key must be a relative POSIX path")
    parts = key.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise MemoryError(
            "memory key must not contain empty, . or .. segments"
        )
    return key


def _namespace_dir(root, agent):
    if agent is None:
        return os.path.join(root, SHARED_DIR)
    return os.path.join(root, AGENTS_DIR, _validate_agent(agent))


def _journal_path(root, agent):
    return os.path.join(_namespace_dir(root, agent), JOURNAL_NAME)


def _read_journal(root, agent):
    path = _journal_path(root, agent)
    if not os.path.exists(path):
        return []
    entries = []
    try:
        with open(path, encoding="utf-8") as handle:
            lines = handle.readlines()
    except OSError as exc:
        raise MemoryError("journal unreadable: %s" % exc) from exc
    for lineno, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except ValueError as exc:
            raise MemoryError(
                "journal line %d does not parse: %s" % (lineno, exc)
            ) from exc
        if (
            not isinstance(entry, dict)
            or not isinstance(entry.get("key"), str)
            or not isinstance(entry.get("version"), int)
            or not isinstance(entry.get("text"), str)
            or not isinstance(entry.get("author"), str)
            or not isinstance(entry.get("ts"), int)
        ):
            raise MemoryError("journal line %d has an unexpected shape" % lineno)
        entries.append(entry)
    return entries


def _append_entry(root, agent, entry):
    path = _journal_path(root, agent)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True))
        handle.write("\n")


def _latest(entries, key):
    current = None
    for entry in entries:
        if entry["key"] == key:
            current = entry
    return current


def write(root, agent, key, text, author="", ts=None):
    """Write a memory entry; returns it with a new_version flag.

    A write identical to the key's latest text returns the
    current entry unchanged with "new_version" False and
    appends nothing to the journal.
    """
    agent = _validate_agent(agent)
    key = _validate_key(key)
    if not isinstance(text, str):
        raise MemoryError("memory text must be a string")
    entries = _read_journal(root, agent)
    current = _latest(entries, key)
    if current is not None and current["text"] == text:
        record = dict(current)
        record["new_version"] = False
        return record
    version = (current["version"] if current else 0) + 1
    record = {
        "key": key,
        "version": version,
        "author": author or "unknown",
        "ts": int(time.time()) if ts is None else ts,
        "text": text,
    }
    _append_entry(root, agent, record)
    record = dict(record)
    record["new_version"] = True
    return record


def write_shared(root, key, text, author="", ts=None):
    """Write a shared crew memory entry (same rules as write)."""
    key = _validate_key(key)
    if not isinstance(text, str):
        raise MemoryError("memory text must be a string")
    entries = _read_journal(root, None)
    current = _latest(entries, key)
    if current is not None and current["text"] == text:
        record = dict(current)
        record["new_version"] = False
        return record
    version = (current["version"] if current else 0) + 1
    record = {
        "key": key,
        "version": version,
        "author": author or "unknown",
        "ts": int(time.time()) if ts is None else ts,
        "text": text,
    }
    _append_entry(root, None, record)
    record = dict(record)
    record["new_version"] = True
    return record


def _read_version(entries, key, version):
    matches = [e for e in entries if e["key"] == key]
    if not matches:
        raise MemoryError("no memory entry for key %r" % key)
    if version is None:
        return dict(matches[-1])
    if not isinstance(version, int) or version < 1:
        raise MemoryError("version must be a positive integer")
    if version > len(matches):
        raise MemoryError(
            "key %r has %d versions, no v%d" % (key, len(matches), version)
        )
    return dict(matches[version - 1])


def read(root, agent, key, version=None):
    """Latest entry for an agent key, or one numbered version."""
    agent = _validate_agent(agent)
    key = _validate_key(key)
    return _read_version(_read_journal(root, agent), key, version)


def read_shared(root, key, version=None):
    """Latest shared entry for a key, or one numbered version."""
    key = _validate_key(key)
    return _read_version(_read_journal(root, None), key, version)


def history(root, agent, key):
    """All versions of an agent key, oldest first."""
    agent = _validate_agent(agent)
    key = _validate_key(key)
    return [dict(e) for e in _read_journal(root, agent) if e["key"] == key]


def history_shared(root, key):
    """All versions of a shared key, oldest first."""
    key = _validate_key(key)
    return [dict(e) for e in _read_journal(root, None) if e["key"] == key]


def _latest_map(entries):
    out = {}
    for entry in entries:
        out[entry["key"]] = dict(entry)
    return out


def list_keys(root, agent):
    """Latest entries for one agent, keyed by key, sorted by key."""
    agent = _validate_agent(agent)
    latest = _latest_map(_read_journal(root, agent))
    return {key: latest[key] for key in sorted(latest)}


def list_shared_keys(root):
    """Latest shared entries, keyed by key, sorted by key."""
    latest = _latest_map(_read_journal(root, None))
    return {key: latest[key] for key in sorted(latest)}


def read_all(root, agent):
    """An agent's own latest entries plus the shared latest entries.

    Kept under separate keys, never merged: own and shared are
    different namespaces, and no precedence rule is invented here.
    """
    agent = _validate_agent(agent)
    return {"own": list_keys(root, agent), "shared": list_shared_keys(root)}


def mount_paths(root, agent):
    """Directories a launcher mounts into a process at start.

    "own" is the agent's memory home, "shared" is the crew
    shelf. The launcher wiring that performs the mount is owed
    beside OS-080's launcher wiring; this names the paths.
    """
    agent = _validate_agent(agent)
    return {
        "own": _namespace_dir(root, agent),
        "shared": _namespace_dir(root, None),
    }


def ensure_root(root):
    """Create the store namespaces if missing; idempotent.

    The relay-memory.service unit runs this at boot so the
    baked root gains its agents/ and shared/ directories
    before any process writes. Returns the mount base paths.
    """
    own_base = os.path.join(root, AGENTS_DIR)
    shared_base = os.path.join(root, SHARED_DIR)
    os.makedirs(own_base, exist_ok=True)
    os.makedirs(shared_base, exist_ok=True)
    return {"agents": own_base, "shared": shared_base}


def main(argv=None):
    """Minimal CLI: ensure, write, write-shared, read, read-shared,
    list, history. Errors exit 2."""
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(
            "usage: memory ensure|write|write-shared|read|read-shared|"
            "list|history ROOT [ARGS]",
            file=sys.stderr,
        )
        return 2
    cmd = argv[0]
    try:
        if cmd == "ensure" and len(argv) == 2:
            print(json.dumps(ensure_root(argv[1]), sort_keys=True))
            return 0
        if cmd == "write" and len(argv) >= 5:
            root, agent, key, text = argv[1], argv[2], argv[3], argv[4]
            author = ""
            if "--author" in argv[5:]:
                author = argv[argv.index("--author") + 1]
            print(json.dumps(
                write(root, agent, key, text, author=author), sort_keys=True))
            return 0
        if cmd == "write-shared" and len(argv) >= 4:
            root, key, text = argv[1], argv[2], argv[3]
            author = ""
            if "--author" in argv[4:]:
                author = argv[argv.index("--author") + 1]
            print(json.dumps(
                write_shared(root, key, text, author=author), sort_keys=True))
            return 0
        if cmd == "read" and len(argv) >= 4:
            version = None
            if "--version" in argv[4:]:
                version = int(argv[argv.index("--version") + 1])
            print(json.dumps(
                read(argv[1], argv[2], argv[3], version), sort_keys=True))
            return 0
        if cmd == "read-shared" and len(argv) >= 3:
            version = None
            if "--version" in argv[3:]:
                version = int(argv[argv.index("--version") + 1])
            print(json.dumps(
                read_shared(argv[1], argv[2], version), sort_keys=True))
            return 0
        if cmd == "list" and len(argv) == 3:
            for key in sorted(list_keys(argv[1], argv[2])):
                print(json.dumps(
                    list_keys(argv[1], argv[2])[key], sort_keys=True))
            return 0
        if cmd == "history" and len(argv) == 4:
            for entry in history(argv[1], argv[2], argv[3]):
                print(json.dumps(entry, sort_keys=True))
            return 0
    except MemoryError as exc:
        print("MEMORY_ERROR: %s" % exc, file=sys.stderr)
        return 2
    except (OSError, ValueError) as exc:
        print("MEMORY_ERROR: %s" % exc, file=sys.stderr)
        return 2
    print(
        "usage: memory ensure|write|write-shared|read|read-shared|"
        "list|history ROOT [ARGS]",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())

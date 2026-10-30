"""tests/test_os078_memory.py -- OS-078: the memory service.

First light pins: a journaled, versioned store with a
per-agent namespace and a shared crew namespace, baked as an
empty root plus a marker on all three image routes, with the
relay-memory.service oneshot ensuring the namespaces at boot
under relay.target. No booted image exists in this repo, so
memory on a booted image stays owed, as does a process
launched with the store directories mounted (launcher wiring)
and the boot brief reading settled decisions from the store
(OS-079, Hana).

No bus post, no live Redis, no network: the store runs
against temporary directories only, and the bake pins are
file-content reads.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OS_DIR = os.path.join(ROOT, "os")
sys.path.insert(0, ROOT)

from mos import memory

BUILD_IMAGE = os.path.join(OS_DIR, "build-image.sh")
BUILD_LIVE = os.path.join(OS_DIR, "build-live.sh")
HOOK = os.path.join(
    OS_DIR, "live-build", "config", "hooks", "live",
    "0900-metaos-services.hook.chroot")
PACKER = os.path.join(OS_DIR, "packer", "metaos.pkr.hcl")
TARGET = os.path.join(OS_DIR, "services", "relay.target")
UNIT = os.path.join(OS_DIR, "services", "relay-memory.service")
README = os.path.join(OS_DIR, "README.md")
SPEC = os.path.join(ROOT, "plan", "META_OS.md")
SWEEP = os.path.join(OS_DIR, "bin", "metaos-secrets-sweep")
MEMORY_UNIT = "relay-memory.service"


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def enablement_loop(text):
    for line in text.splitlines():
        if "for u in" in line:
            return line
    return ""


def section(text, start_marker, end_marker):
    start = text.index(start_marker)
    try:
        end = text.index(end_marker, start + len(start_marker))
    except ValueError:
        end = len(text)
    return text[start:end]


class MemoryStoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="metaos-memory-")
        self.root = os.path.join(self.tmp, "memory")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_write_and_read_round_trip(self):
        record = memory.write(
            self.root, "pax", "decisions/router.md",
            "Router is the queue, not the chat.", author="pax", ts=1000)
        self.assertEqual(record["version"], 1)
        self.assertTrue(record["new_version"])
        self.assertEqual(record["author"], "pax")
        self.assertEqual(record["ts"], 1000)
        back = memory.read(self.root, "pax", "decisions/router.md")
        self.assertEqual(back["text"], "Router is the queue, not the chat.")
        self.assertEqual(back["version"], 1)

    def test_versions_increment_and_versioned_read(self):
        memory.write(self.root, "pax", "note.txt", "one", ts=1)
        memory.write(self.root, "pax", "note.txt", "two", ts=2)
        record = memory.write(self.root, "pax", "note.txt", "three", ts=3)
        self.assertEqual(record["version"], 3)
        self.assertEqual(memory.read(self.root, "pax", "note.txt", 1)["text"], "one")
        self.assertEqual(memory.read(self.root, "pax", "note.txt", 2)["text"], "two")
        self.assertEqual(memory.read(self.root, "pax", "note.txt")["text"], "three")
        hist = memory.history(self.root, "pax", "note.txt")
        self.assertEqual([e["version"] for e in hist], [1, 2, 3])
        self.assertEqual([e["text"] for e in hist], ["one", "two", "three"])

    def test_identical_rewrite_is_a_noop(self):
        memory.write(self.root, "milo", "k.md", "same", ts=1)
        journal = os.path.join(self.root, "agents", "milo", "journal.jsonl")
        with open(journal, encoding="utf-8") as handle:
            before = handle.read()
        record = memory.write(self.root, "milo", "k.md", "same", ts=2)
        self.assertEqual(record["version"], 1)
        self.assertFalse(record["new_version"])
        with open(journal, encoding="utf-8") as handle:
            after = handle.read()
        self.assertEqual(before, after)

    def test_shared_namespace_versions_independently(self):
        memory.write(self.root, "pax", "settled.md", "agent view", ts=1)
        memory.write_shared(self.root, "settled.md", "crew view", ts=2)
        memory.write_shared(self.root, "settled.md", "crew view v2", ts=3)
        self.assertEqual(
            memory.read(self.root, "pax", "settled.md")["text"], "agent view")
        self.assertEqual(
            memory.read_shared(self.root, "settled.md")["text"], "crew view v2")
        self.assertEqual(
            memory.read_shared(self.root, "settled.md", 1)["text"], "crew view")
        all_entries = memory.read_all(self.root, "pax")
        self.assertEqual(all_entries["own"]["settled.md"]["text"], "agent view")
        self.assertEqual(
            all_entries["shared"]["settled.md"]["text"], "crew view v2")

    def test_shared_identical_rewrite_is_a_noop(self):
        memory.write_shared(self.root, "s.md", "once", ts=1)
        record = memory.write_shared(self.root, "s.md", "once", ts=2)
        self.assertEqual(record["version"], 1)
        self.assertFalse(record["new_version"])
        self.assertEqual(len(memory.history_shared(self.root, "s.md")), 1)

    def test_key_validation_refuses_escape(self):
        for bad in ("../escape", "/absolute", "a//b", "a/./b", "a/../b",
                    "a\\b", "a\x00b", ""):
            with self.assertRaises(memory.MemoryError):
                memory.write(self.root, "pax", bad, "x")
            with self.assertRaises(memory.MemoryError):
                memory.write_shared(self.root, bad, "x")

    def test_agent_validation_refuses_slash(self):
        for bad in ("a/b", ".", "..", "", "a\\b"):
            with self.assertRaises(memory.MemoryError):
                memory.write(self.root, bad, "k.md", "x")

    def test_non_string_text_refused(self):
        with self.assertRaises(memory.MemoryError):
            memory.write(self.root, "pax", "k.md", b"bytes")

    def test_missing_key_and_bad_version_raise_never_guess(self):
        with self.assertRaises(memory.MemoryError):
            memory.read(self.root, "pax", "nope.md")
        with self.assertRaises(memory.MemoryError):
            memory.read_shared(self.root, "nope.md")
        memory.write(self.root, "pax", "k.md", "v1", ts=1)
        with self.assertRaises(memory.MemoryError):
            memory.read(self.root, "pax", "k.md", 2)
        with self.assertRaises(memory.MemoryError):
            memory.read(self.root, "pax", "k.md", 0)

    def test_corrupt_journal_line_raises(self):
        memory.write(self.root, "pax", "k.md", "good", ts=1)
        journal = os.path.join(self.root, "agents", "pax", "journal.jsonl")
        with open(journal, "a", encoding="utf-8") as handle:
            handle.write("this is not json\n")
        with self.assertRaises(memory.MemoryError):
            memory.read(self.root, "pax", "k.md")
        with open(journal, "a", encoding="utf-8") as handle:
            handle.write('{"key": "k.md"}\n')
        with self.assertRaises(memory.MemoryError):
            memory.read(self.root, "pax", "k.md")

    def test_list_keys_sorted_and_shared_separate(self):
        memory.write(self.root, "hana", "b.md", "b", ts=1)
        memory.write(self.root, "hana", "a.md", "a", ts=2)
        memory.write_shared(self.root, "z.md", "z", ts=3)
        own = memory.list_keys(self.root, "hana")
        self.assertEqual(list(own), ["a.md", "b.md"])
        self.assertEqual(list(memory.list_shared_keys(self.root)), ["z.md"])
        self.assertNotIn("z.md", own)

    def test_mount_paths_name_own_and_shared(self):
        paths = memory.mount_paths(self.root, "rowan")
        self.assertEqual(
            paths["own"], os.path.join(self.root, "agents", "rowan"))
        self.assertEqual(paths["shared"], os.path.join(self.root, "shared"))

    def test_ensure_root_creates_namespaces_idempotently(self):
        first = memory.ensure_root(self.root)
        self.assertTrue(os.path.isdir(first["agents"]))
        self.assertTrue(os.path.isdir(first["shared"]))
        second = memory.ensure_root(self.root)
        self.assertEqual(first, second)

    def test_restart_read_back_via_cli_subprocess(self):
        memory.write(self.root, "pax", "decisions/x.md", "kept", ts=42)
        proc = subprocess.run(
            [sys.executable, os.path.join(ROOT, "mos", "memory.py"),
             "read", self.root, "pax", "decisions/x.md"],
            capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["text"], "kept")
        proc = subprocess.run(
            [sys.executable, os.path.join(ROOT, "mos", "memory.py"),
             "ensure", self.root],
            capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        proc = subprocess.run(
            [sys.executable, os.path.join(ROOT, "mos", "memory.py"),
             "read", self.root, "pax", "../escape.md"],
            capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("MEMORY_ERROR", proc.stderr)


class MemoryBakeTest(unittest.TestCase):
    def test_unit_shape(self):
        text = read(UNIT)
        self.assertIn("WantedBy=relay.target", text)
        self.assertIn("Type=oneshot", text)
        self.assertIn("RemainAfterExit=yes", text)
        self.assertIn("User=relay", text)
        self.assertIn(
            "ExecStart=/usr/bin/python3 /opt/relay/mos/memory.py ensure "
            "/var/lib/metaos/memory", text)
        self.assertIn("PartOf=relay.target", text)

    def test_target_wants_unit(self):
        self.assertIn(MEMORY_UNIT, read(TARGET))

    def test_build_image_bakes_root_and_enables_unit(self):
        text = read(BUILD_IMAGE)
        self.assertIn("mkdir -p \"$ROOTFS/var/lib/metaos/memory\"", text)
        self.assertIn(".metaos-memory-store", text)
        self.assertIn(
            "chroot \"$ROOTFS\" chown relay:relay /var/lib/metaos/memory", text)
        self.assertIn(MEMORY_UNIT, enablement_loop(text))

    def test_build_live_stages_root(self):
        text = read(BUILD_LIVE)
        self.assertIn("mkdir -p \"$STAGE/var/lib/metaos/memory\"", text)
        self.assertIn(".metaos-memory-store", text)

    def test_hook_enables_unit_and_chowns_root(self):
        text = read(HOOK)
        self.assertIn(MEMORY_UNIT, enablement_loop(text))
        self.assertIn("mkdir -p /var/lib/metaos/memory", text)
        self.assertIn("chown relay:relay /var/lib/metaos/memory", text)

    def test_packer_bakes_root_and_enables_unit(self):
        text = read(PACKER)
        self.assertIn("mkdir -p /var/lib/metaos/memory", text)
        self.assertIn(".metaos-memory-store", text)
        self.assertIn("chown -R relay:relay /var/lib/metaos/memory", text)
        self.assertIn(MEMORY_UNIT, enablement_loop(text))

    def test_docs_record_first_light_without_em_dash(self):
        readme = read(README)
        self.assertIn("Memory service (OS-078, first light)", readme)
        sec = section(
            readme, "## Memory service (OS-078, first light)",
            "## Two routes, stated plainly")
        self.assertNotIn("\u2014", sec)
        spec = read(SPEC)
        self.assertIn("Memory service (OS-078, Pax, first light)", spec)
        note = section(
            spec, "**Memory service (OS-078, Pax, first light):**",
            "### 2. Identity and capabilities")
        self.assertNotIn("\u2014", note)

    def test_build_scripts_bash_syntax_clean(self):
        for path in (BUILD_IMAGE, BUILD_LIVE):
            proc = subprocess.run(
                ["bash", "-n", path], capture_output=True, text=True,
                timeout=60)
            self.assertEqual(proc.returncode, 0, proc.stderr)
        proc = subprocess.run(
            ["sh", "-n", HOOK], capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_memory_root_sweeps_clean_and_secret_value_flagged(self):
        tmp = tempfile.mkdtemp(prefix="metaos-memory-sweep-")
        try:
            mem = os.path.join(tmp, "var", "lib", "metaos", "memory")
            os.makedirs(mem)
            with open(os.path.join(mem, ".metaos-memory-store"),
                      "w", encoding="utf-8") as handle:
                handle.write("memory-store-root /var/lib/metaos/memory\n")
            clean = subprocess.run(
                ["sh", SWEEP, tmp], capture_output=True, text=True, timeout=60)
            self.assertEqual(clean.returncode, 0, clean.stdout)
            journal_dir = os.path.join(mem, "agents", "pax")
            os.makedirs(journal_dir)
            with open(os.path.join(journal_dir, "journal.jsonl"),
                      "w", encoding="utf-8") as handle:
                handle.write(
                    '{"key": "k.md", "version": 1, "author": "pax", '
                    '"ts": 1, "text": "UPSTASH_TOKEN=planted"}\n')
            dirty = subprocess.run(
                ["sh", SWEEP, tmp], capture_output=True, text=True, timeout=60)
            self.assertEqual(dirty.returncode, 1)
            self.assertIn("FINDING", dirty.stdout)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

"""tests/test_intel_capability_files.py -- OS-080: capability files.

OS-080 puts one explicit capability file behind every crew
process: intel/capabilities/<identity>.json, loaded at process
start by intel/capability_files.py into exactly the grant dict
intel/capability.py (OS-081) judges. These tests pin the file
half on fixtures:

- The shipped crew files load clean: five identities, no
  errors, provisional flags (network on, bus_post and spend
  off), writes inside crew/<nick>/ only.
- validate_grant accepts a complete grant and returns a
  fresh copy; every shape corruption fails: non-object,
  missing key, unknown key, empty identity, non-boolean
  flag, non-list write_paths, empty, absolute, or escaping
  write path.
- load_grant_for returns None for an identity with no file
  (no grant, and OS-081 refuses that process), raises for a
  traversal identity, and raises for a present but invalid
  file instead of silently running the process ungranted.
- load_crew_grants reports a bad file and a
  filename-identity mismatch as errors and keeps the good
  files; it never raises for a bad file.
- Two loads return equal but independent dicts.
- A loaded shipped grant judged by OS-081 allows an
  inside-grant write and the network flag, and refuses a
  bus post, a spend, and an outside-grant write.
- None of the new OS-080 files carries an em dash
  (the new-doc rule).

No bus post, no live Redis, no network, no systemd:
pure fixture calls plus file reads. The loader never posts,
never performs an action, and never judges one; judgment
stays in intel/capability.py.
"""

import copy
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, ".")

from intel import capability  # noqa: E402
from intel import capability_files as capfiles  # noqa: E402

CREW = ["pax", "rowan", "hana", "milo", "buffy"]
NEW_FILES = ["intel/capability_files.py",
             "tests/test_intel_capability_files.py"] + [
    "intel/capabilities/%s.json" % nick for nick in CREW]


def _good_grant(identity="milo"):
    return {"identity": identity, "bus_post": False,
            "spend": False, "network": True,
            "write_paths": ["crew/%s/" % identity]}


def _write(directory, name, data):
    path = os.path.join(directory, name)
    with open(path, "w", encoding="utf-8") as handle:
        if isinstance(data, str):
            handle.write(data)
        else:
            json.dump(data, handle)
    return path


class ShippedCrewTest(unittest.TestCase):
    def test_shipped_files_load_clean(self):
        grants, errors = capfiles.load_crew_grants(
            capfiles.shipped_directory())
        self.assertEqual(errors, [])
        self.assertEqual(sorted(grants), sorted(CREW))

    def test_shipped_flags_are_provisional_defaults(self):
        grants, _ = capfiles.load_crew_grants(
            capfiles.shipped_directory())
        for nick in CREW:
            grant = grants[nick]
            self.assertFalse(grant["bus_post"])
            self.assertFalse(grant["spend"])
            self.assertTrue(grant["network"])
            self.assertEqual(grant["write_paths"],
                             ["crew/%s/" % nick])

    def test_load_grant_for_matches_shipped_files(self):
        directory = capfiles.shipped_directory()
        for nick in CREW:
            grant = capfiles.load_grant_for(nick, directory)
            self.assertEqual(grant["identity"], nick)
        self.assertIsNone(capfiles.load_grant_for("ghost", directory))


class ValidateGrantTest(unittest.TestCase):
    def test_valid_grant_returns_fresh_copy(self):
        data = _good_grant()
        grant = capfiles.validate_grant(data)
        self.assertEqual(grant, data)
        grant["write_paths"].append("elsewhere/")
        self.assertEqual(data["write_paths"], ["crew/milo/"])
        self.assertIsNot(grant["write_paths"], data["write_paths"])

    def test_corrupt_grants_fail(self):
        bad = []
        bad.append("not a dict")
        bad.append(["a", "list"])
        missing = _good_grant()
        del missing["spend"]
        bad.append(missing)
        unknown = _good_grant()
        unknown["bus_posts"] = False
        bad.append(unknown)
        empty_identity = _good_grant()
        empty_identity["identity"] = ""
        bad.append(empty_identity)
        for flag, value in [("bus_post", 1), ("spend", "false"),
                            ("network", None)]:
            grant = _good_grant()
            grant[flag] = value
            bad.append(grant)
        not_list = _good_grant()
        not_list["write_paths"] = "crew/milo/"
        bad.append(not_list)
        for path in ["", "/", "/etc/passwd", "../escape",
                     "crew/../../escape"]:
            grant = _good_grant()
            grant["write_paths"] = [path]
            bad.append(grant)
        non_string_path = _good_grant()
        non_string_path["write_paths"] = [3]
        bad.append(non_string_path)
        for data in bad:
            with self.assertRaises(ValueError, msg=repr(data)):
                capfiles.validate_grant(data, source="test")

    def test_empty_write_paths_list_is_valid(self):
        grant = _good_grant()
        grant["write_paths"] = []
        self.assertEqual(capfiles.validate_grant(grant)["write_paths"],
                         [])


class LoadGrantForTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.directory)

    def test_missing_file_is_none_not_grant(self):
        self.assertIsNone(capfiles.load_grant_for("milo",
                                                  self.directory))

    def test_traversal_identity_raises(self):
        for identity in ["", "../milo", "mi/lo", "mi lo", ".",
                         "milo.json"]:
            with self.assertRaises(ValueError, msg=identity):
                capfiles.load_grant_for(identity, self.directory)

    def test_corrupt_file_raises_instead_of_ungranting(self):
        _write(self.directory, "milo.json", "{not json")
        with self.assertRaises(ValueError):
            capfiles.load_grant_for("milo", self.directory)
        bad = _good_grant()
        bad["network"] = 1
        _write(self.directory, "milo.json", bad)
        with self.assertRaises(ValueError):
            capfiles.load_grant_for("milo", self.directory)

    def test_valid_file_loads(self):
        _write(self.directory, "milo.json", _good_grant())
        grant = capfiles.load_grant_for("milo", self.directory)
        self.assertEqual(grant, _good_grant())


class LoadCrewGrantsTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.directory)

    def test_bad_and_mismatched_files_reported_good_kept(self):
        _write(self.directory, "milo.json", _good_grant("milo"))
        _write(self.directory, "pax.json", "{broken")
        _write(self.directory, "hana.json", _good_grant("milo"))
        _write(self.directory, "notes.txt", "ignored, not json")
        grants, errors = capfiles.load_crew_grants(self.directory)
        self.assertEqual(sorted(grants), ["milo"])
        self.assertEqual(sorted(e["file"] for e in errors),
                         ["hana.json", "pax.json"])

    def test_loads_are_independent_copies(self):
        _write(self.directory, "milo.json", _good_grant())
        first = capfiles.load_grant_for("milo", self.directory)
        first["write_paths"].append("elsewhere/")
        second = capfiles.load_grant_for("milo", self.directory)
        self.assertEqual(second["write_paths"], ["crew/milo/"])


class Os081IntegrationTest(unittest.TestCase):
    def test_loaded_grant_judges_as_os081_expects(self):
        grant = capfiles.load_grant_for(
            "milo", capfiles.shipped_directory())
        allowed = capability.check_action(grant, "write_file",
                                          "crew/milo/notes.md")
        self.assertTrue(allowed["allowed"])
        self.assertTrue(capability.check_action(grant, "network")
                        ["allowed"])
        for action, subject in [("bus_post", None),
                                ("spend", None),
                                ("write_file", "crew/pax/x.md")]:
            decision = capability.check_action(grant, action, subject)
            self.assertFalse(decision["allowed"])

    def test_no_grant_process_is_refused(self):
        grant = capfiles.load_grant_for(
            "ghost", capfiles.shipped_directory())
        self.assertIsNone(grant)
        decision = capability.check_action(grant, "bus_post",
                                           identity="ghost")
        self.assertFalse(decision["allowed"])
        self.assertEqual(decision["reason"],
                         "no capability grant on file")


class NewDocRuleTest(unittest.TestCase):
    def test_no_em_dash_in_new_files(self):
        root = os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)))
        for rel in NEW_FILES:
            with open(os.path.join(root, rel),
                      encoding="utf-8") as handle:
                self.assertNotIn("\u2014", handle.read(), rel)


if __name__ == "__main__":
    unittest.main()

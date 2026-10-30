"""worlds pack contract: shipped manifests validate (WORLDS-001).

The validator under test is worlds/validate_pack.py. Positive
cases load the real pack.json files shipped in worlds/ so a pack
that drifts from the contract in worlds/README.md fails here.
Negative cases mutate a minimal hand-built valid manifest so each
contract rule has a test that proves it bites.
"""
import copy
import importlib.util
import json
import os
import sys
import unittest

sys.path.insert(0, ".")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_validator():
    path = os.path.join(ROOT, "worlds", "validate_pack.py")
    spec = importlib.util.spec_from_file_location("validate_pack", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


vp = _load_validator()

SHIPPED_PACKS = ("fdny", "nypd", "hospital", "ems",
                 "dsny", "doe", "mta", "dep")


def _valid_manifest():
    return {
        "pack": "testworld",
        "pack_name": "Test world pack",
        "version": "0.1.0",
        "status": "spec",
        "institution_type": "test institution",
        "summary": "A pack used only by the validator tests.",
        "watchers": [
            {"id": "board", "watches": "A state board.",
             "inputs": ["status reports"]},
        ],
        "agents": [
            {"nick": "keeper", "role": "Keeps the board.",
             "serves": ["board"]},
        ],
        "alerts": [
            {"kind": "board-stale", "severity": "warning",
             "privacy": "local", "crosses_bus": False,
             "carries": "The board id.", "urgency": "routine"},
        ],
        "privacy_classes": {
            "local_only": ["board contents"],
            "bus_summary": ["board state counts"],
        },
        "cross_world": {
            "sends": [
                {"to": "crew", "kind": "board-state",
                 "carries": "Counts only.",
                 "never_carries": ["board contents"]},
            ],
            "receives": [],
        },
        "firstboot": [
            {"field": "room_name", "label": "Bus room",
             "required": True},
        ],
        "urgency": [
            {"class": "routine", "rank": 3,
             "meaning": "State changes."},
        ],
    }


class ShippedPacksTest(unittest.TestCase):
    def test_shipped_packs_validate(self):
        for name in SHIPPED_PACKS:
            path = os.path.join(ROOT, "worlds", name, "pack.json")
            _, errors = vp.validate_pack_at(path)
            self.assertEqual(errors, [],
                             "%s failed validation: %s" % (name, errors))

    def test_shipped_packs_have_docs(self):
        for name in SHIPPED_PACKS:
            pack_dir = os.path.join(ROOT, "worlds", name)
            for fname in ("PACK.md", "pack.json"):
                self.assertTrue(
                    os.path.isfile(os.path.join(pack_dir, fname)),
                    "%s is missing %s" % (name, fname))

    def test_shipped_packs_are_honest_spec(self):
        # Honesty gate: a shipped pack is honest spec (definition
        # only) or honest partial (a runtime exists, and the
        # manifest names it and every runtime file exists on disk).
        # Nothing ships as a status it cannot back up.
        for name in SHIPPED_PACKS:
            path = os.path.join(ROOT, "worlds", name, "pack.json")
            with open(path, "r", encoding="utf-8") as fh:
                manifest = json.load(fh)
            if manifest["status"] == "spec":
                continue
            self.assertEqual(
                manifest["status"], "partial",
                "%s may only be honest spec or honest partial" % name)
            parts = (manifest.get("runtime") or {}).get("parts") or []
            self.assertTrue(
                parts,
                "%s claims partial without a runtime record" % name)
            for part in parts:
                runtime_path = os.path.join(ROOT, part.get("path") or "")
                self.assertTrue(
                    os.path.isfile(runtime_path),
                    "%s runtime part %s does not exist on disk"
                    % (name, part.get("path")))
                self.assertTrue(
                    isinstance(part.get("what"), str) and part["what"] and
                    isinstance(part.get("proven"), str) and part["proven"],
                    "%s runtime part must state what it is and what is "
                    "proven" % name)


class ValidatorRulesTest(unittest.TestCase):
    def test_valid_manifest_passes(self):
        self.assertEqual(vp.validate_pack(_valid_manifest()), [])

    def test_missing_key_fails(self):
        manifest = _valid_manifest()
        del manifest["alerts"]
        errors = vp.validate_pack(manifest)
        self.assertTrue(any("alerts" in e for e in errors), errors)

    def test_bad_status_fails(self):
        manifest = _valid_manifest()
        manifest["status"] = "live"
        errors = vp.validate_pack(manifest)
        self.assertTrue(any("status" in e for e in errors), errors)

    def test_local_alert_may_not_cross_bus(self):
        manifest = _valid_manifest()
        manifest["alerts"][0]["crosses_bus"] = True
        errors = vp.validate_pack(manifest)
        self.assertTrue(any("crosses the bus" in e for e in errors),
                        errors)

    def test_summary_alert_may_cross_bus(self):
        manifest = _valid_manifest()
        manifest["alerts"][0]["privacy"] = "summary"
        manifest["alerts"][0]["crosses_bus"] = True
        self.assertEqual(vp.validate_pack(manifest), [])

    def test_send_without_never_carries_fails(self):
        manifest = _valid_manifest()
        manifest["cross_world"]["sends"][0]["never_carries"] = []
        errors = vp.validate_pack(manifest)
        self.assertTrue(any("never_carries" in e for e in errors),
                        errors)

    def test_unknown_urgency_class_fails(self):
        manifest = _valid_manifest()
        manifest["alerts"][0]["urgency"] = "whenever"
        errors = vp.validate_pack(manifest)
        self.assertTrue(any("urgency" in e for e in errors), errors)

    def test_agent_serving_unknown_watcher_fails(self):
        manifest = _valid_manifest()
        manifest["agents"][0]["serves"] = ["no-such-watcher"]
        errors = vp.validate_pack(manifest)
        self.assertTrue(any("unknown watcher" in e for e in errors),
                        errors)

    def test_duplicate_urgency_rank_fails(self):
        manifest = _valid_manifest()
        manifest["urgency"].append(
            {"class": "urgent", "rank": 3, "meaning": "Also rank 3."})
        errors = vp.validate_pack(manifest)
        self.assertTrue(any("rank" in e for e in errors), errors)

    def test_bad_severity_fails(self):
        manifest = _valid_manifest()
        manifest["alerts"][0]["severity"] = "loud"
        errors = vp.validate_pack(manifest)
        self.assertTrue(any("severity" in e for e in errors), errors)


if __name__ == "__main__":
    unittest.main()

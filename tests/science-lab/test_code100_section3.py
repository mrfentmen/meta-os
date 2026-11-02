"""Focused tests for code-wave Section 3 (CB-021..CB-030).

One light module, stdlib unittest only. It pins the exact property each
task names; the broader science-lab suite stays where it is.
"""
import json
import os
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
_LAB = os.path.join(_REPO, "os", "worlds", "science-lab")
if _LAB not in sys.path:
    sys.path.insert(0, _LAB)

import breeding  # noqa: E402
import compute  # noqa: E402
import cycle  # noqa: E402
import gateway  # noqa: E402
import ladder  # noqa: E402
import ledger  # noqa: E402
import reasoning  # noqa: E402
import repository  # noqa: E402
import verify  # noqa: E402


def _ledger(td):
    return os.path.join(td, "ledger.jsonl")


class CB021MissingRequirementTests(unittest.TestCase):
    """CB-021: each promotion rung names what is missing."""

    def test_levels_one_to_three_name_their_evidence(self):
        expected = {
            0: "pinned original-source claims",
            1: "signed computational result",
            2: "independent-verifier reproduced record",
        }
        for current, phrase in expected.items():
            with self.subTest(current=current):
                text = ladder.next_required(current)
                self.assertIn(phrase, text)
                self.assertIn("level %d" % (current + 1), text)

    def test_human_rung_names_unimplemented(self):
        text = ladder.next_required(3)
        self.assertIn(ladder.UNIMPLEMENTED, text)
        self.assertIn("No automated promotion above level 3", text)


class CB022AutomatedCeilingTests(unittest.TestCase):
    """CB-022: automated promotion above level 3 is refused."""

    def test_each_human_rung_raises_unimplemented(self):
        for current, target in ((3, 4), (4, 5), (5, 6)):
            with self.subTest(target=target):
                with self.assertRaises(NotImplementedError) as caught:
                    ladder.promote(
                        current, target, "human_physical_experiment",
                        "unverified", is_human=False)
                self.assertIn(ladder.UNIMPLEMENTED, str(caught.exception))
                self.assertIn(str(target), str(caught.exception))


class CB023HumanGateWithoutRecordTests(unittest.TestCase):
    """CB-023: no gate record means no advance past the gate."""

    def test_transition_to_wetlab_is_refused_and_changes_nothing(self):
        c = cycle.new_cycle("CB023", "q?")
        c["inputs"]["sealed_record"] = {"id": "s1"}
        before = json.loads(json.dumps(c))
        with tempfile.TemporaryDirectory() as td:
            lp = _ledger(td)
            with self.assertRaises(ValueError) as caught:
                cycle.transition(c, "wetlab", "auto-advance", lp)
            self.assertIn("human", str(caught.exception).lower())
            self.assertEqual(c, before)
            self.assertEqual(ledger.read_all(lp), [])

    def test_park_records_the_gate_state_but_does_not_approve(self):
        c = cycle.new_cycle("CB023P", "q?")
        cycle.park_for_human_gate(c, "wetlab")
        self.assertEqual(c["gate_state"], "human-gated")
        self.assertEqual(c["phase"], "wetlab")
        self.assertNotIn("wetlab_decision", c["inputs"])


class CB024MiddleTamperTests(unittest.TestCase):
    """CB-024: tampering a middle record breaks verification there."""

    def test_middle_record_breaks_at_its_line(self):
        with tempfile.TemporaryDirectory() as td:
            lp = _ledger(td)
            for i in range(3):
                ledger.append_record(lp, {"kind": "record-%d" % i, "n": i})
            with open(lp, encoding="utf-8") as fh:
                lines = fh.read().strip().splitlines()
            middle = json.loads(lines[1])
            middle["n"] = 999
            lines[1] = json.dumps(middle, sort_keys=True)
            with open(lp, "w", encoding="utf-8") as fh:
                fh.write("\n".join(lines) + "\n")
            ok, msg = ledger.verify_chain(lp)
            self.assertFalse(ok)
            self.assertIn("line 2", msg)
            self.assertIn("entry_hash mismatch", msg)


class CB025LatePreregistrationTests(unittest.TestCase):
    """CB-025: a result filed before the prereg hash refuses the prereg."""

    def test_result_before_prereg_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            lp = _ledger(td)
            ledger.append_record(lp, {
                "kind": "experiment-result",
                "hypothesis_id": "H-CB025",
                "output_hash": "abc",
            })
            with self.assertRaises(ValueError) as caught:
                reasoning.preregister(
                    "H-CB025", "R2 >= 0.5", 0.5, "full set", lp)
            self.assertIn("late registration refused", str(caught.exception))
            self.assertNotIn(
                "preregistration",
                [e.get("kind") for e in ledger.read_all(lp)])


class CB026CrashRecordTests(unittest.TestCase):
    """CB-026: a crashed run has no fake output hash."""

    def test_crash_records_exit_and_null_hash(self):
        rec = compute.run_experiment({
            "command": "python3 -c \"import sys; sys.exit(7)\"",
            "seed": 1,
            "code_hash": "c",
            "data_hash": "d",
            "research_question": "crash probe",
            "hypothesis_id": "H-CB026",
        })
        self.assertIsNone(rec["output_hash"])
        self.assertEqual(rec["exit_code"], 7)
        self.assertTrue(any("exit_code" in line
                            for line in rec["execution_logs"]))
        ok, msg = compute.validate_record_shape(rec)
        self.assertTrue(ok, msg)


class CB027BlindInputTests(unittest.TestCase):
    """CB-027: the blind re-run payload carries no narrative."""

    def test_archived_inputs_carry_only_inputs(self):
        record = {
            "input_hash": "abc123",
            "random_seed": 7,
            "parameters": {"op": "sum"},
            "output_hash": "must-not-be-read",
            "reasoning": "a story",
            "narrative": "another story",
        }
        rerun = verify.reexecute(record)
        self.assertEqual(set(rerun["archived_inputs"]),
                         {"input_hash", "random_seed", "parameters"})
        blob = json.dumps(rerun["archived_inputs"])
        for forbidden in ("output_hash", "reasoning", "narrative"):
            self.assertNotIn(forbidden, blob)


class CB028QueryByLevelTests(unittest.TestCase):
    """CB-028: a level query never returns a higher-level claim."""

    def test_query_level_one_excludes_level_two(self):
        with tempfile.TemporaryDirectory() as td:
            repository.file_claim(
                {"claim_id": "L1", "statement": "low", "level": 1}, base=td)
            repository.file_claim(
                {"claim_id": "L2", "statement": "higher", "level": 2}, base=td)
            repository.file_experiment(
                {"experiment_id": "E2", "level": 2}, base=td)
            got = repository.query_by_level(1, base=td)
            self.assertEqual([c["claim_id"] for c in got], ["L1"])


class CB029GatewayRefusalTests(unittest.TestCase):
    """CB-029: an off-allowlist call is refused and recorded."""

    def test_refusal_is_recorded_with_args_hash(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "calls.jsonl")
            gw = gateway.Gateway("CB029", calls_path=path)
            with self.assertRaises(gateway.GatewayRefused):
                gw.call_tool("literature-researcher", "evil-tool",
                             {"op": "search", "query": "x"})
            with open(path, encoding="utf-8") as fh:
                entries = [json.loads(line) for line in fh if line.strip()]
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["status"], "refused-allowlist")
            self.assertEqual(entries[0]["tool"], "evil-tool")
            self.assertEqual(len(entries[0]["args_hash"]), 64)
            self.assertIsNone(entries[0]["result_hash"])


class CB030SelectBeforeResultsTests(unittest.TestCase):
    """CB-030: selecting a survivor before results exist is refused."""

    def test_selection_without_results_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            rule = reasoning.preregister(
                "H-CB030", "mass >= 20", 20.0, "all variants", _ledger(td))
            with self.assertRaises(ValueError) as caught:
                breeding.select_survivor([{"variant_id": "V001"}], rule)
            self.assertIn("result", str(caught.exception).lower())


if __name__ == "__main__":
    unittest.main()

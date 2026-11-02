"""Section 5 (tasks 41-50): discovery-cycle driver tests.

Gate refusal, human-gate park/resume (module + CLI driver), recovery
resume, budget stop, step-8 block, report generation. stdlib unittest
only. Run from repo root:
    python3 -m unittest discover -s tests/science-lab -v
"""
import argparse
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

import cli  # noqa: E402
import cycle  # noqa: E402
import ledger  # noqa: E402


def _read_json(path):
    with open(str(path), "r", encoding="utf-8") as fh:
        return json.load(fh)


def _fresh_cycle(cid="C-TEST", question="q?"):
    c = cycle.new_cycle(cid, question)
    return c


def _ledger_in(td):
    return os.path.join(td, "ledger.jsonl")


class TestPhaseGates(unittest.TestCase):
    def test_each_phase_names_its_required_inputs(self):
        # Task 42: every gated phase names inputs; a missing one blocks
        # with a message naming the missing key.
        for target, needed in cycle.REQUIRED_INPUTS.items():
            if target in cycle.HUMAN_GATES or target == cycle.STEP_8:
                continue
            self.assertTrue(needed, target)
            c = _fresh_cycle()
            ok, msg = cycle.can_transition(c, target)
            if target == "literature":
                self.assertTrue(ok, msg)  # problem_statement is present
            else:
                self.assertFalse(ok, msg)
                for key in needed:
                    self.assertIn(key, msg)

    def test_gate_refusal_raises_on_transition(self):
        c = _fresh_cycle()
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError) as ctx:
                cycle.transition(c, "verification", "skip ahead",
                                 _ledger_in(td))
            self.assertIn("critique", str(ctx.exception).lower())
            self.assertEqual(ledger.read_all(_ledger_in(td)), [])

    def test_parked_cycle_blocks_transition(self):
        c = _fresh_cycle()
        c["inputs"]["sealed_record"] = {"id": "s1"}
        cycle.park_for_human_gate(c, "wetlab")
        ok, msg = cycle.can_transition(c, "publication")
        self.assertFalse(ok)
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):
                cycle.transition(c, "publication", "x", _ledger_in(td))

    def test_one_transition_is_one_ledger_entry(self):
        c = _fresh_cycle()
        with tempfile.TemporaryDirectory() as td:
            lp = _ledger_in(td)
            cycle.transition(c, "literature", "brief filed", lp)
            entries = ledger.read_all(lp)
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["kind"], "cycle-transition")
            self.assertEqual(c["history"], [entries[0]["entry_hash"]])


class TestHumanGates(unittest.TestCase):
    def test_direct_transition_to_human_gate_refused(self):
        c = _fresh_cycle()
        c["inputs"]["sealed_record"] = {"id": "s1"}
        with tempfile.TemporaryDirectory() as td:
            for gate in ("wetlab", "publication"):
                with self.assertRaises(ValueError) as ctx:
                    cycle.transition(c, gate, "try auto", _ledger_in(td))
                self.assertIn("human", str(ctx.exception).lower())

    def test_park_and_approved_resume(self):
        c = _fresh_cycle()
        c["inputs"]["sealed_record"] = {"id": "s1"}
        parked = cycle.park_for_human_gate(c, "wetlab")
        self.assertEqual(parked["gate_state"], "human-gated")
        self.assertEqual(parked["phase"], "wetlab")
        resumed = cycle.resume_with_decision(
            parked, {"gate": "wetlab", "approved": True,
                     "decided_by": "human"})
        self.assertEqual(resumed["gate_state"], "open")
        self.assertNotIn("parked_gate", resumed)
        self.assertIn("wetlab_decision", resumed["inputs"])

    def test_rejection_stays_parked(self):
        c = _fresh_cycle()
        parked = cycle.park_for_human_gate(c, "wetlab")
        still = cycle.resume_with_decision(
            parked, {"gate": "wetlab", "approved": False,
                     "decided_by": "human"})
        self.assertEqual(still["gate_state"], "human-gated")

    def test_bad_decisions_refused(self):
        c = _fresh_cycle()
        parked = cycle.park_for_human_gate(c, "wetlab")
        bad = ["not-a-dict",
               {"gate": "publication", "approved": True, "decided_by": "h"},
               {"gate": "wetlab", "decided_by": "h"},
               {"gate": "wetlab", "approved": "yes", "decided_by": "h"},
               {"gate": "wetlab", "approved": True}]
        for dec in bad:
            with self.assertRaises(ValueError, msg=repr(dec)):
                cycle.resume_with_decision(dict(parked), dec)

    def test_resume_when_not_parked_refused(self):
        c = _fresh_cycle()
        with self.assertRaises(ValueError):
            cycle.resume_with_decision(
                c, {"gate": "wetlab", "approved": True,
                    "decided_by": "human"})


class TestStep8Gap(unittest.TestCase):
    def test_step8_transition_always_blocked(self):
        c = _fresh_cycle()
        ok, msg = cycle.can_transition(c, cycle.STEP_8)
        self.assertFalse(ok)
        self.assertIn("UNIMPLEMENTED", msg)
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError) as ctx:
                cycle.transition(c, cycle.STEP_8, "invent step 8",
                                 _ledger_in(td))
            self.assertIn("UNIMPLEMENTED", str(ctx.exception))

    def test_step8_parks_blocked_on_source(self):
        c = _fresh_cycle()
        parked = cycle.park_for_human_gate(c, cycle.STEP_8)
        self.assertEqual(parked["gate_state"], "blocked-on-source")

    def test_unknown_gate_refused(self):
        with self.assertRaises(ValueError):
            cycle.park_for_human_gate(_fresh_cycle(), "teleport")


class TestCycleCLIDriver(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.addCleanup(self._td.cleanup)
        self._old_cycles = cli.CYCLES_DIR
        self._old_ledger = cli.LEDGER_PATH
        self._old_reports = cli.REPORTS_DIR
        from pathlib import Path
        cli.CYCLES_DIR = Path(self._td.name) / "cycles"
        cli.LEDGER_PATH = Path(self._td.name) / "ledger.jsonl"
        cli.REPORTS_DIR = Path(self._td.name) / "reports"
        self.addCleanup(self._restore_cli)

    def _restore_cli(self):
        cli.CYCLES_DIR = self._old_cycles
        cli.LEDGER_PATH = self._old_ledger
        cli.REPORTS_DIR = self._old_reports

    def _ns(self, **kw):
        return argparse.Namespace(**kw)

    def test_advance_parks_at_human_gate(self):
        # Task 43: `cycle advance --to wetlab` parks, never auto-passes.
        self.assertEqual(cli.cmd_cycle_start(
            self._ns(id="C1", question="q?")), 0)
        self.assertEqual(cli.cmd_cycle_advance(
            self._ns(id="C1", to="literature", reason="brief filed")), 0)
        self.assertEqual(cli.cmd_cycle_advance(
            self._ns(id="C1", to="wetlab", reason="to gate 9")), 0)
        rec = _read_json(cli.CYCLES_DIR / "C1.json")
        self.assertEqual(rec["gate_state"], "human-gated")
        self.assertEqual(rec["phase"], "wetlab")
        kinds = [e.get("kind") for e in ledger.read_all(str(cli.LEDGER_PATH))]
        self.assertIn("cycle.gate-parked", kinds)
        self.assertNotIn("cycle-transition", [
            k for k, e in zip(kinds, ledger.read_all(str(cli.LEDGER_PATH)))
            if e.get("to_phase") == "wetlab"])

    def test_advance_parks_blocked_on_source_gap(self):
        self.assertEqual(cli.cmd_cycle_start(
            self._ns(id="C2", question="q?")), 0)
        self.assertEqual(cli.cmd_cycle_advance(
            self._ns(id="C2", to="step-8-unimplemented",
                     reason="hit the gap")), 0)
        rec = _read_json(cli.CYCLES_DIR / "C2.json")
        self.assertEqual(rec["gate_state"], "blocked-on-source")

    def test_park_and_resume_commands(self):
        self.assertEqual(cli.cmd_cycle_start(
            self._ns(id="C3", question="q?")), 0)
        self.assertEqual(cli.cmd_cycle_park(
            self._ns(id="C3", gate="wetlab")), 0)
        rec = _read_json(cli.CYCLES_DIR / "C3.json")
        self.assertEqual(rec["gate_state"], "human-gated")
        dec = json.dumps({"gate": "wetlab", "approved": True,
                          "decided_by": "test-human"})
        self.assertEqual(cli.cmd_cycle_resume(
            self._ns(id="C3", decision=dec)), 0)
        rec = _read_json(cli.CYCLES_DIR / "C3.json")
        self.assertEqual(rec["gate_state"], "open")
        # Rejection keeps the cycle parked.
        self.assertEqual(cli.cmd_cycle_park(
            self._ns(id="C3", gate="wetlab")), 0)
        rej = json.dumps({"gate": "wetlab", "approved": False,
                          "decided_by": "test-human"})
        self.assertEqual(cli.cmd_cycle_resume(
            self._ns(id="C3", decision=rej)), 0)
        rec = _read_json(cli.CYCLES_DIR / "C3.json")
        self.assertEqual(rec["gate_state"], "human-gated")

    def test_resume_needs_a_decision(self):
        self.assertEqual(cli.cmd_cycle_start(
            self._ns(id="C4", question="q?")), 0)
        self.assertEqual(cli.cmd_cycle_park(
            self._ns(id="C4", gate="wetlab")), 0)
        with self.assertRaises(SystemExit):
            cli.cmd_cycle_resume(self._ns(id="C4", decision="not json"))

    def test_report_command(self):
        self.assertEqual(cli.cmd_cycle_start(
            self._ns(id="C5", question="q?")), 0)
        self.assertEqual(cli.cmd_cycle_advance(
            self._ns(id="C5", to="literature", reason="brief filed")), 0)
        self.assertEqual(cli.cmd_cycle_report(self._ns(id="C5")), 0)
        from pathlib import Path
        path = Path(str(cli.REPORTS_DIR / "C5.md"))
        self.assertTrue(path.exists())
        text = path.read_text(encoding="utf-8")
        self.assertIn("C5", text)
        self.assertIn("never higher", text)


class TestRecovery(unittest.TestCase):
    def test_killed_driver_resumes_without_duplication(self):
        with tempfile.TemporaryDirectory() as td:
            lp = _ledger_in(td)
            cdir = os.path.join(td, "cycles")
            os.makedirs(cdir)
            c = cycle.new_cycle("CR1", "q?")
            c["inputs"]["sources"] = {"brief": "b1"}
            cycle.transition(c, "literature", "brief filed", lp)
            c["inputs"]["hypotheses"] = ["H1"]
            cycle.transition(c, "hypotheses", "hyps filed", lp)
            with open(os.path.join(cdir, "CR1.json"), "w") as fh:
                json.dump(c, fh, sort_keys=True)
            before = len(ledger.read_all(lp))
            # Simulate the kill: drop the object, recover from records.
            recovered = cycle.recover_cycle("CR1", cycles_dir=cdir,
                                            ledger_path=lp)
            self.assertEqual(recovered["phase"], "hypotheses")
            self.assertEqual(recovered["history"], c["history"])
            self.assertEqual(len(ledger.read_all(lp)), before)

    def test_recovery_missing_record(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(FileNotFoundError):
                cycle.recover_cycle("NOPE", cycles_dir=td,
                                    ledger_path=_ledger_in(td))

    def test_recovery_detects_history_mismatch(self):
        with tempfile.TemporaryDirectory() as td:
            lp = _ledger_in(td)
            cdir = os.path.join(td, "cycles")
            os.makedirs(cdir)
            c = cycle.new_cycle("CR2", "q?")
            cycle.transition(c, "literature", "brief filed", lp)
            c["history"].append("deadbeef" * 8)
            with open(os.path.join(cdir, "CR2.json"), "w") as fh:
                json.dump(c, fh, sort_keys=True)
            with self.assertRaises(ValueError):
                cycle.recover_cycle("CR2", cycles_dir=cdir, ledger_path=lp)


class TestBudgetStop(unittest.TestCase):
    def _config(self, max_actions):
        return {"cycle": {"maxActions": max_actions},
                "agents": {"default": {"maxCalls": 50, "maxSpend": 5.0}}}

    def test_actions_over_cap_stop_with_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            lp = _ledger_in(td)
            c = cycle.new_cycle("CB1", "q?")
            for i in range(3):
                ledger.append_record(lp, {"kind": "cycle-note",
                                          "cycle_id": "CB1", "n": i})
            rp = os.path.join(td, "CB1.budget-receipt.json")
            ok, msg = cycle.check_cycle_budget(
                c, lp, config=self._config(2), receipt_path=rp)
            self.assertFalse(ok)
            self.assertIn("maxActions", msg)
            receipt = _read_json(rp)
            self.assertTrue(receipt["stopped"])
            self.assertEqual(receipt["actions"], 3)

    def test_within_cap_allowed_no_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            lp = _ledger_in(td)
            c = cycle.new_cycle("CB2", "q?")
            ledger.append_record(lp, {"kind": "cycle-note",
                                      "cycle_id": "CB2"})
            rp = os.path.join(td, "CB2.budget-receipt.json")
            ok, _ = cycle.check_cycle_budget(
                c, lp, config=self._config(200), receipt_path=rp)
            self.assertTrue(ok)
            self.assertFalse(os.path.exists(rp))

    def test_spend_over_cap_stops(self):
        with tempfile.TemporaryDirectory() as td:
            lp = _ledger_in(td)
            c = cycle.new_cycle("CB3", "q?")
            ledger.append_record(lp, {"kind": "cycle-note",
                                      "cycle_id": "CB3", "cost": 99.0})
            ok, msg = cycle.check_cycle_budget(c, lp,
                                               config=self._config(200))
            self.assertFalse(ok)
            self.assertIn("maxSpend", msg)


class TestReportGenerator(unittest.TestCase):
    def test_report_is_one_honest_page(self):
        with tempfile.TemporaryDirectory() as td:
            lp = _ledger_in(td)
            cdir = os.path.join(td, "cycles")
            rdir = os.path.join(td, "reports")
            os.makedirs(cdir)
            c = cycle.new_cycle("CRP1", "q?")
            c["inputs"]["sources"] = {"brief": "b1"}
            cycle.transition(c, "literature", "brief filed", lp)
            ledger.append_record(lp, {"kind": "cycle-claim",
                                      "cycle_id": "CRP1",
                                      "claim": "water is wet",
                                      "evidence_level": 1})
            with open(os.path.join(cdir, "CRP1.json"), "w") as fh:
                json.dump(c, fh, sort_keys=True)
            md = cycle.generate_report("CRP1", cycles_dir=cdir,
                                       ledger_path=lp, reports_dir=rdir)
            self.assertTrue(os.path.exists(os.path.join(rdir, "CRP1.md")))
            for needle in ("CRP1", "literature", "Level 1",
                           "never higher", "step-8"):
                self.assertIn(needle, md)

    def test_report_missing_cycle(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(FileNotFoundError):
                cycle.generate_report("NOPE", cycles_dir=td,
                                      ledger_path=_ledger_in(td),
                                      reports_dir=td)


if __name__ == "__main__":
    unittest.main()

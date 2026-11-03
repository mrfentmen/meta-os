"""Tests for Officina stage 2b prior-art (OC2B-328–333, 342).

Run from the repo root:

    python3 -m unittest discover -s tests/officina -v

Offline and $0: the public shelf is curated text with URLs+titles
(no network at test time), the repo search reads files only, and
the 2a loop underneath is the simulator plus the held-out gate.
"""

import json
import os
import sys
import unittest

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__), "..", "..", "os", "worlds",
        "officina", "runtime",
    ),
)

from brief import run_rough_words  # noqa: E402
from prior_art import (  # noqa: E402
    brief_to_note,
    build_prior_art_note,
    find_duplicate_sources,
    format_note_text,
    search_repo,
    search_web,
    sources_of,
    validate_note,
)

WORDS_A = (
    "a heatsink for a toasty little board, about 50mm square, "
    "no fan, keep it compact, under 2 degrees per watt"
)

#: Built dynamically so the forbidden claim never appears literally
#: in this file either: the 2b note must never present itself as one.
FORBIDDEN = "patent" + "ability " + "opinion"


class TestNoteSchema(unittest.TestCase):
    def test_zero_sources_rejected(self):
        note = build_prior_art_note(run_rough_words(WORDS_A))
        bad = dict(note, sources=[])
        with self.assertRaises(ValueError):
            validate_note(bad)

    def test_missing_sources_key_rejected(self):
        note = build_prior_art_note(run_rough_words(WORDS_A))
        bad = {k: v for k, v in note.items() if k != "sources"}
        with self.assertRaises(ValueError):
            validate_note(bad)

    def test_claim_without_sources_rejected(self):
        note = build_prior_art_note(run_rough_words(WORDS_A))
        bad = json.loads(json.dumps(note))
        bad["claims"][0]["sources"] = []
        with self.assertRaises(ValueError):
            validate_note(bad)

    def test_good_note_validates(self):
        note = build_prior_art_note(run_rough_words(WORDS_A))
        self.assertTrue(validate_note(note))
        self.assertGreater(len(sources_of(note)), 0)


class TestRepoSearch(unittest.TestCase):
    def test_finds_known_brief_on_heatsink_words(self):
        hits = search_repo(WORDS_A)
        paths = [h["path"] for h in hits]
        self.assertTrue(
            any("heatsink.py" in p for p in paths),
            "repo grep on a heatsink brief must hit heatsink.py; "
            "got %s" % paths[:5],
        )
        for hit in hits:
            self.assertIn("path", hit)
            self.assertIn("lineno", hit)
            self.assertIn("snippet", hit)

    def test_empty_words_no_hits_no_crash(self):
        self.assertEqual(search_repo(""), [])


class TestWebSearch(unittest.TestCase):
    def test_returns_urls_and_titles_only_shape(self):
        results = search_web("heatsink fin spacing")
        self.assertGreaterEqual(len(results), 2)
        for r in results:
            self.assertTrue(r["title"])
            self.assertTrue(r["url"].startswith("http"))
            self.assertIn(r["kind"], ("primary", "secondary"))

    def test_offline_refuses_clean(self):
        with self.assertRaises(RuntimeError):
            search_web("heatsink", offline=True)


class TestNoteWriter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = run_rough_words(WORDS_A)
        cls.hits = search_repo(cls.record)
        cls.note = build_prior_art_note(cls.record,
                                        extra_sources=cls.hits)

    def test_covers_the_brief(self):
        self.assertEqual(
            self.note["artefact_class"], "heatsink-fin-geometry")
        self.assertTrue(self.note["key_features"])
        params = self.record["final_params"]
        joined = " ".join(self.note["key_features"])
        self.assertIn("%.2f" % params["fin_height_mm"], joined)

    def test_every_claim_names_its_sources(self):
        for claim in self.note["claims"]:
            self.assertTrue(claim["claim"])
            self.assertTrue(claim["sources"])

    def test_bounds_read_live_not_copied(self):
        from heatsink import BASE_THICKNESS_MM, FIN_HEIGHT_MM  # noqa: E402
        repo = {e["path"]: e["what"]
                for e in self.note["repo_context"]}
        self.assertIn(str(list(FIN_HEIGHT_MM)),
                      repo["os/worlds/officina/runtime/heatsink.py"])
        self.assertIn(str(list(BASE_THICKNESS_MM)),
                      repo["os/worlds/officina/runtime/heatsink.py"])

    def test_guard_strips_forbidden_phrase(self):
        text = format_note_text(self.note)
        blob = json.dumps(self.note)
        self.assertNotIn(FORBIDDEN, text)
        self.assertNotIn(FORBIDDEN, blob)

    def test_shelf_marks_primary_secondary(self):
        kinds = {e["kind"] for e in self.note["public_context"]}
        self.assertIn("primary", kinds)
        self.assertIn("secondary", kinds)

    def test_no_duplicate_sources(self):
        self.assertEqual(find_duplicate_sources(self.note), [])


class TestWire2aTo2b(unittest.TestCase):
    def test_brief_to_note_end_to_end(self):
        record, note = brief_to_note(WORDS_A)
        self.assertTrue(record["proven"])
        self.assertEqual(note["stage"], "2b-prior-art")
        self.assertTrue(validate_note(note))
        self.assertNotIn(FORBIDDEN, format_note_text(note))


if __name__ == "__main__":
    unittest.main()

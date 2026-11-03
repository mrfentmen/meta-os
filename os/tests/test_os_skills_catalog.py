"""tests/test_os_skills_catalog.py -- the shipped Meta OS skill catalog.

Pins the two things a generated catalog can silently lose: the
directory/frontmatter identity (a skill whose folder and `name:` drift
apart is unmountable or misrouted) and the executable code blocks (a
generated SKILL.md with an unverified block is prose, not a capability).

Structure checks always run. The block-execution check needs node and
rustc, because `verify_catalog.py` runs every distinct Python,
JavaScript, and Rust block; it skips on a machine that lacks them
rather than pretending the blocks passed.
"""

import os
import re
import shutil
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(ROOT, "skills")
VERIFIER = os.path.join(SKILLS, "_tools", "verify_catalog.py")
GENERATED_MARKER = "<!-- generated from _tools/catalog.py"

HANDWRITTEN = {
    "worker",
    "relief",
    "claimant",
    "watchdog",
    "quartermaster",
    "archivist",
    "fedora-hat",
}


def skill_dirs():
    return sorted(
        name for name in os.listdir(SKILLS)
        if os.path.isdir(os.path.join(SKILLS, name)) and name != "_tools"
    )


def frontmatter(text):
    if not text.startswith("---\n"):
        return ""
    end = text.find("\n---\n", 4)
    return text[4:end] if end >= 0 else ""


def declared_name(text):
    match = re.search(r"^name:\s*(\S+)\s*$", frontmatter(text), re.M)
    return match.group(1) if match else None


class SkillsCatalogTest(unittest.TestCase):
    def test_every_directory_carries_a_skill(self):
        dirs = skill_dirs()
        self.assertEqual(len(dirs), 307, "catalog size changed; regenerate the README")
        for name in dirs:
            self.assertTrue(
                os.path.isfile(os.path.join(SKILLS, name, "SKILL.md")),
                f"{name}: missing SKILL.md",
            )

    def test_frontmatter_name_matches_directory(self):
        for name in skill_dirs():
            path = os.path.join(SKILLS, name, "SKILL.md")
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
            self.assertEqual(declared_name(text), name, f"{name}: name/folder drift")
            self.assertTrue(frontmatter(text), f"{name}: no frontmatter")

    def test_generated_and_handwritten_sets_are_exact(self):
        generated = set()
        handwritten = set()
        for name in skill_dirs():
            path = os.path.join(SKILLS, name, "SKILL.md")
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
            (generated if GENERATED_MARKER in text else handwritten).add(name)
        self.assertEqual(len(generated), 300)
        self.assertEqual(handwritten, HANDWRITTEN)

    def test_readme_links_every_skill(self):
        with open(os.path.join(SKILLS, "README.md"), encoding="utf-8") as handle:
            readme = handle.read()
        linked = set(re.findall(r"\]\(\./([^)/]+)\)", readme))
        self.assertEqual(linked, set(skill_dirs()))

    def test_tools_are_present(self):
        for tool in ("catalog.py", "kernels.py", "generate_catalog.py",
                     "verify_catalog.py"):
            self.assertTrue(os.path.isfile(os.path.join(SKILLS, "_tools", tool)),
                            f"_tools/{tool} is missing")

    @unittest.skipUnless(
        shutil.which("node") and shutil.which("rustc"),
        "node and rustc are required to execute the catalog blocks",
    )
    def test_catalog_verifier_passes(self):
        result = subprocess.run(
            [sys.executable, VERIFIER],
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(
            result.returncode, 0,
            f"verify_catalog failed:\n{result.stdout}\n{result.stderr}",
        )
        self.assertIn("problems: 0", result.stdout)


if __name__ == "__main__":
    unittest.main()

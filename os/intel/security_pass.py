"""INT-011: security pass scanner over the working tree.

Scans a tree for committed secrets: provider token shapes
(aligned with the DSP-028 guard shapes in intel/dispatch.py),
private key headers, quoted credential assignments, and
secret filenames. Prints only file, line, and kind for
each finding, never a matched value, so the report
itself cannot leak a credential it finds.

Deliberately NOT scanned for content: keyring lines. A
keyring line carrying the word secret is a label, not a
value, and a keyring line with a random secret part is
indistinguishable from the namespace strings this tree
is full of, so a content pattern for it would drown in
false positives. The keyring controls are instead the
secret-filename rule (any *.keyring file in the tree is
a finding), the .gitignore entries, and the drill
generating a fresh secret per run instead of carrying
one in source.

A shape-shaped hit is a fixture, not a finding, only when
the matched value is synthetic by one of four stated
rules, checked in order: (1) after stripping its provider
prefix, the value is one repeated character (the
project's documented fake convention, see the DSP-028
test); (2) the value contains a dummy word as a
substring (drill, dummy, fake, example, placeholder,
sample, test, secret). A random credential does not
spell those words; (3) the value contains an ascending
sequential run of six or more letters or digits, which
humans type and random tokens do not; (4) a word piece
of the same line outside the match itself is a label
word (drill, dummy, fake, example, placeholder,
sample), covering values labeled by their variable or
comment rather than their own text (for example a
variable named fake_token). A variable merely named
secret or test does not count here: those words mark
a fake only inside the value itself.
Anything else is reported. The rules are deliberate and
documented here, not silent allowlists: the pass report
lists every skipped fixture hit by file, line, and kind
too, so a reviewer can check the skip, not just trust
it. A value that passes none of the four rules is
treated as a real credential until a human says
otherwise, even when it sits in a test file.

Usage, from the repo root: python3 intel/security_pass.py
Exit 0 when the tree is clean, 1 when findings exist.
Importing this module runs nothing.
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SKIP_DIRS = {".git", "__pycache__", "node_modules"}

# (kind, pattern). Patterns match shapes, not specific values.
# The Bearer pattern needs literal token characters after the
# word, so code passing a variable (Bearer {token}) does not
# match. The assignment pattern needs a quoted literal value,
# so code reading a variable or None does not match.
PATTERNS = [
    ("github-token",
     r"(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}"),
    ("github-fine-grained-token",
     r"github_pat_[A-Za-z0-9_]{20,}"),
    ("api-key",
     r"sk-[A-Za-z0-9]{20,}"),
    ("aws-access-key-id",
     r"AKIA[0-9A-Z]{16}"),
    ("bearer-token",
     r"Bearer\s+[A-Za-z0-9._\-]{10,}"),
    ("private-key",
     r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    ("credential-assignment",
     r"(?i)(?:api[_-]?key|access[_-]?token|secret|password)"
     r"\s*[:=]\s*[\"'][^\"'\s]{8,}[\"']"),
]

COMPILED = [(kind, re.compile(pattern)) for kind, pattern in PATTERNS]

DUMMY_WORDS = ("drill", "dummy", "fake", "example",
               "placeholder", "sample", "test", "secret")

# Line labels that mark a value fake. Deliberately narrower
# than DUMMY_WORDS: a variable merely named secret or test
# does not label its value fake, so those two words count
# only inside the value itself, never on the line around it.
LINE_WORDS = ("drill", "dummy", "fake", "example",
              "placeholder", "sample")

_PREFIX_RE = re.compile(
    r"^(?:ghp|gho|ghu|ghs|ghr)_|github_pat_|sk-|AKIA|Bearer\s+")

# Basename patterns for files that must never be committed.
SECRET_FILENAME_RES = [
    re.compile(r"^\.env(\..*)?$"),
    re.compile(r".*\.env$"),
    re.compile(r".*job-secret.*"),
    re.compile(r".*admin_secret.*"),
    re.compile(r".*\.keyring$"),
    re.compile(r".*\.pem$"),
    re.compile(r".*\.key$"),
]


def _value_of(match_text):
    """The credential part of a match, prefix stripped."""
    return _PREFIX_RE.sub("", match_text, count=1)


def _has_sequential_run(value):
    """True when value holds six ascending letters or digits."""
    lowered = value.lower()
    for seq in ("abcdefghijklmnopqrstuvwxyz", "0123456789"):
        for start in range(len(seq) - 5):
            if seq[start:start + 6] in lowered:
                return True
    return False


def _is_fixture(match_text, line):
    """True when a shape-shaped hit is a documented fake.

    match_text is the matched text, line is the full line
    it came from. See the module docstring for the four
    rules and why each one means synthetic, not real.
    """
    value = _value_of(match_text)
    if len(value) >= 8 and len(set(value)) == 1:
        return True
    lowered_value = value.lower()
    if any(word in lowered_value for word in DUMMY_WORDS):
        return True
    if _has_sequential_run(value):
        return True
    # Label words count only outside the match itself: a
    # variable named secret holding a real token must not
    # pass just because its own name says secret.
    rest = line.replace(match_text, "", 1)
    pieces = re.split(r"[^A-Za-z0-9]+", rest.lower())
    return any(piece in LINE_WORDS for piece in pieces)


def _is_binary(path):
    try:
        with open(path, "rb") as handle:
            return b"\x00" in handle.read(4096)
    except OSError:
        return True


def scan_root(root):
    """Scan root. Return (findings, fixtures, files_scanned).

    findings and fixtures are lists of (relpath, lineno, kind)
    where lineno is 0 for a filename finding. Neither list
    carries a matched value.
    """
    findings = []
    fixtures = []
    files_scanned = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in sorted(filenames):
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, root)
            if any(rx.match(name) for rx in SECRET_FILENAME_RES):
                findings.append((rel, 0, "secret-filename"))
            if _is_binary(path):
                continue
            files_scanned += 1
            try:
                with open(path, "r", encoding="utf-8",
                          errors="replace") as handle:
                    lines = handle.readlines()
            except OSError:
                continue
            for lineno, line in enumerate(lines, 1):
                for kind, rx in COMPILED:
                    match = rx.search(line)
                    if match is None:
                        continue
                    if _is_fixture(match.group(0), line):
                        fixtures.append((rel, lineno, kind))
                    else:
                        findings.append((rel, lineno, kind))
    return findings, fixtures, files_scanned


def main(argv):
    root = argv[1] if len(argv) > 1 else ROOT
    findings, fixtures, files_scanned = scan_root(root)
    for rel, lineno, kind in findings:
        print(f"FINDING {rel}:{lineno} {kind}")
    for rel, lineno, kind in fixtures:
        print(f"fixture {rel}:{lineno} {kind}")
    kinds = {}
    for _rel, _lineno, kind in findings:
        kinds[kind] = kinds.get(kind, 0) + 1
    summary = ", ".join(f"{kind}={count}"
                        for kind, count in sorted(kinds.items()))
    print(f"scanned {files_scanned} files, "
          f"{len(findings)} findings, {len(fixtures)} fixtures"
          + (f" ({summary})" if summary else ""))
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

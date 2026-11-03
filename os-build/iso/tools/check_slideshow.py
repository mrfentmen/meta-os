#!/usr/bin/env python3
"""MetaOS 1.0 Calamares HTML slideshow — static validation.

Runs anywhere with python3, no dependencies, no network, no boot.

Asserts for os-build/iso/calamares/branding/metaos/slideshow/:
  1. every slide-*.html file parses (html.parser) with balanced tags
  2. every slide links the shared slideshow.css, which exists
  3. slideshow.css defines all 3 brand colors (#1877F2, #EDF5FF, #070B16)
  4. every <img> src (if any) is a relative path to a git-committed file
  5. no http:// or https:// URLs anywhere in the slides or CSS (offline rule)
  6. no base-flavour / vendor strings (Ubuntu, Xubuntu, Apple, macOS)
     in VISIBLE text (tags, comments, style and script stripped first)
  7. no placeholder copy (lorem, TODO) in visible text

Exit 0 only when there are zero FAILs.
"""

import html as htmlmod
import os
import re
import subprocess
import sys
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))
ISO = os.path.dirname(HERE)
SLIDES = os.path.join(ISO, "calamares", "branding", "metaos", "slideshow")
CSS_NAME = "slideshow.css"

BRAND_COLORS = ("#1877F2", "#EDF5FF", "#070B16")
FORBIDDEN_VISIBLE = re.compile(
    r"\b(Ubuntu|Xubuntu|Apple|macOS)\b", re.IGNORECASE
)
PLACEHOLDER = re.compile(r"\b(lorem|TODO)\b", re.IGNORECASE)
URL = re.compile(r"https?://")

VOID = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}

PASS, FAIL = "PASS", "FAIL"
results = []


def record(state, name, detail=""):
    results.append((state, name, detail))
    print("  [%s] %s" % (state, name) + (" — %s" % detail if detail else ""))


class BalanceChecker(HTMLParser):
    """Lenient parse plus a strict tag-balance audit."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.errors = []
        self.imgs = []
        self.css_links = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == "img":
            for key, val in attrs:
                if key.lower() == "src" and val:
                    self.imgs.append(val)
        if tag == "link":
            attrs_d = {k.lower(): v for k, v in attrs}
            if attrs_d.get("rel", "").lower() == "stylesheet" and attrs_d.get("href"):
                self.css_links.append(attrs_d["href"])
        if tag not in VOID:
            self.stack.append((tag, self.getpos()))

    def handle_startendtag(self, tag, attrs):
        tag = tag.lower()
        if tag == "img":
            for key, val in attrs:
                if key.lower() == "src" and val:
                    self.imgs.append(val)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in VOID:
            return
        if not self.stack:
            self.errors.append("stray </%s> at %s" % (tag, self.getpos()))
            return
        if self.stack[-1][0] == tag:
            self.stack.pop()
            return
        names = [t for t, _ in self.stack]
        if tag in names:
            while self.stack and self.stack[-1][0] != tag:
                bad, pos = self.stack.pop()
                self.errors.append(
                    "<%s> opened at %s never closed before </%s>" % (bad, pos, tag)
                )
            self.stack.pop()
        else:
            self.errors.append("stray </%s> at %s" % (tag, self.getpos()))

    def finish(self):
        for bad, pos in self.stack:
            self.errors.append("<%s> opened at %s never closed" % (bad, pos))


def visible_text(raw):
    """Strip comments, script/style blocks and all tags; unescape entities."""
    no_comments = re.sub(r"<!--.*?-->", " ", raw, flags=re.DOTALL)
    no_script = re.sub(
        r"<(script|style)\b.*?</\1\s*>", " ", no_comments, flags=re.DOTALL | re.IGNORECASE
    )
    no_tags = re.sub(r"<[^>]+>", " ", no_script)
    return htmlmod.unescape(no_tags)


def committed_files():
    """Set of git-tracked paths, relative to the repo root."""
    try:
        top = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, cwd=HERE,
        )
        if top.returncode != 0:
            return None
        root = top.stdout.strip()
        out = subprocess.run(
            ["git", "ls-files"], capture_output=True, text=True, cwd=root
        )
        if out.returncode != 0:
            return None
        return {line for line in out.stdout.splitlines() if line}, root
    except (OSError, FileNotFoundError):
        return None


def main():
    print("MetaOS installer slideshow — static validation")
    print("slides dir: %s" % os.path.relpath(SLIDES, ISO))

    pages = sorted(
        f for f in os.listdir(SLIDES)
        if f.startswith("slide-") and f.endswith(".html")
    )
    if len(pages) != 5:
        record(FAIL, "slide count", "expected 5 slide-*.html, found %d" % len(pages))
    else:
        record(PASS, "slide count", "5 slides: " + ", ".join(pages))

    css_path = os.path.join(SLIDES, CSS_NAME)
    if not os.path.isfile(css_path):
        record(FAIL, "shared CSS", "%s missing" % CSS_NAME)
        css_raw = ""
    else:
        record(PASS, "shared CSS", "%s present" % CSS_NAME)
        with open(css_path, "r", encoding="utf-8") as fh:
            css_raw = fh.read()

    if css_raw:
        missing = [c for c in BRAND_COLORS if c.lower() not in css_raw.lower()]
        if missing:
            record(FAIL, "brand colors in CSS", "missing: " + ", ".join(missing))
        else:
            record(PASS, "brand colors in CSS", " ".join(BRAND_COLORS))

    tracked = committed_files()
    if tracked is None:
        record(FAIL, "git tree", "could not list committed files (git missing?)")
        tracked, root = set(), None
    else:
        tracked, root = tracked
        record(PASS, "git tree", "%d committed files" % len(tracked))

    for page in pages:
        path = os.path.join(SLIDES, page)
        with open(path, "r", encoding="utf-8") as fh:
            raw = fh.read()

        parser = BalanceChecker()
        try:
            parser.feed(raw)
            parser.close()
            parser.finish()
        except Exception as exc:  # html.parser should not raise; audit if it does
            parser.errors.append("parser exception: %s" % exc)
        if parser.errors:
            record(FAIL, "%s parses" % page, "; ".join(parser.errors[:3]))
        else:
            record(PASS, "%s parses" % page, "balanced tags")

        if CSS_NAME in parser.css_links:
            record(PASS, "%s links CSS" % page, CSS_NAME)
        else:
            record(FAIL, "%s links CSS" % page, "no stylesheet link to %s" % CSS_NAME)

        bad_imgs = []
        for src in parser.imgs:
            if URL.search(src) or src.startswith(("data:", "/")):
                bad_imgs.append(src)
                continue
            if root is None:
                bad_imgs.append(src + " (git tree unreadable)")
                continue
            abs_path = os.path.normpath(os.path.join(os.path.dirname(path), src))
            rel = os.path.relpath(abs_path, root)
            if rel not in tracked:
                bad_imgs.append(src)
        if bad_imgs:
            record(FAIL, "%s img src" % page, "unresolved: " + ", ".join(bad_imgs))
        else:
            record(
                PASS, "%s img src" % page,
                "%d image(s), all committed" % len(parser.imgs),
            )

        if URL.search(raw):
            record(FAIL, "%s offline" % page, "contains an http(s): URL")
        else:
            record(PASS, "%s offline" % page, "no http(s): URLs")

        text = visible_text(raw)
        hits = sorted(set(m.group(0) for m in FORBIDDEN_VISIBLE.finditer(text)))
        if hits:
            record(FAIL, "%s visible strings" % page, "forbidden: " + ", ".join(hits))
        else:
            record(PASS, "%s visible strings" % page, "no flavour/vendor words")

        ph = sorted(set(m.group(0) for m in PLACEHOLDER.finditer(text)))
        if ph:
            record(FAIL, "%s copy" % page, "placeholder: " + ", ".join(ph))
        else:
            record(PASS, "%s copy" % page, "no placeholder text")

    if URL.search(css_raw):
        record(FAIL, "CSS offline", "contains an http(s): URL")
    elif css_raw:
        record(PASS, "CSS offline", "no http(s): URLs")

    counts = {PASS: 0, FAIL: 0}
    for state, _name, _detail in results:
        counts[state] += 1
    print("\n%d pass, %d fail" % (counts[PASS], counts[FAIL]))
    if counts[FAIL]:
        print("FAIL — do not call the slideshow verified")
        return 1
    print("PASS — slideshow is static-clean. Live-installer rendering still UNRUN.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

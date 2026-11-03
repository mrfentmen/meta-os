#!/usr/bin/env python3
"""Pick the skills that match a request, without a model call.

The catalog has 307 skills; a request should not load all of them. This
router reads each SKILL.md's frontmatter (name plus description), builds a
BM25 index, and returns a small ranked list. It never reads the skill body
or mounts anything: it selects the name, and the agent reads the SKILL.md.

Generic requests are allowed to match nothing. `NO_MATCH` is a valid,
honest answer; forcing a skill onto an unrelated request is worse than
returning an empty list.

Usage:
  python3 _tools/router.py "fix the flaky clipboard test"
  python3 _tools/router.py --json --limit 5 "add a systemd unit"
  python3 _tools/router.py --list
"""

import argparse
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_ROOT = HERE.parent
TOKEN_RE = re.compile(r"[a-z0-9]+")
STOP = frozenset("""
a an and are as at be been being but by can could did do does for from had has
have how i if in into is it its me my need no not of on or our please should so
some than that the their them then there these they this to use used using want
was we were what when where which who why will with work works would you your
add fix get got help make
""".split())


def frontmatter(text):
    text = text.replace("\r\n", "\n")
    if not text.startswith("---\n"):
        return ""
    end = text.find("\n---\n", 4)
    return text[4:end] if end >= 0 else ""


def declared_name(text):
    match = re.search(r"^name:[ \t]*(\S+)[ \t]*$", frontmatter(text), re.M)
    return match.group(1) if match else None


def description(text):
    block = frontmatter(text)
    match = re.search(
        r"^description:[ \t]*>-?[ \t]*\n((?:[ \t]+[^\n]*\n?)+)", block, re.M)
    if match:
        return " ".join(
            line.strip() for line in match.group(1).splitlines() if line.strip())
    match = re.search(r"^description:[ \t]*(.+)$", block, re.M)
    return match.group(1).strip() if match else ""


def stem(token):
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 4 and token.endswith("es"):
        return token[:-2]
    if (len(token) > 3 and token.endswith("s")
            and not token.endswith(("ss", "us", "is"))):
        return token[:-1]
    return token


def tokens(text):
    result = []
    for raw in TOKEN_RE.findall(text.lower()):
        if raw in STOP:
            continue
        result.append(stem(raw))
    return result


class Index:
    def __init__(self, root):
        self.entries = []
        self.df = Counter()
        for path in sorted(Path(root).glob("*/SKILL.md")):
            if path.parent.name == "_tools":
                continue
            text = path.read_text(encoding="utf-8")
            name = declared_name(text)
            if not name:
                continue
            desc = description(text)
            phrases = [p.lower() for p in re.findall(r'"([^"]+)"', desc)]
            doc = (tokens(name.replace("-", " ")) * 4
                   + tokens(desc)
                   + tokens(" ".join(phrases)) * 2)
            counts = Counter(doc)
            self.entries.append({
                "name": name,
                "tf": counts,
                "dl": len(doc),
                "phrases": phrases,
            })
            for token in counts:
                self.df[token] += 1
        self.n = len(self.entries)
        self.avgdl = (sum(entry["dl"] for entry in self.entries) / self.n
                      if self.n else 0.0)
        self.idf = {
            token: math.log(1 + (self.n - count + 0.5) / (count + 0.5))
            for token, count in self.df.items()
        }

    def search(self, query, limit=3):
        query_tokens = list(dict.fromkeys(tokens(query)))
        if not query_tokens or not self.entries:
            return []
        query_norm = " ".join(TOKEN_RE.findall(query.lower()))
        rare = max(3, self.n // 10)
        name_hit = False
        scored = []
        for entry in self.entries:
            score = 0.0
            matched = []
            if entry["name"].replace("-", " ") in query_norm:
                score += 25.0
                name_hit = True
            for token in query_tokens:
                tf = entry["tf"].get(token, 0)
                if not tf:
                    continue
                length = entry["dl"] or 1
                denom = tf + 1.2 * (0.25 + 0.75 * length / (self.avgdl or 1))
                contribution = self.idf.get(token, 0.0) * tf * 2.2 / denom
                if contribution <= 0:
                    continue
                score += contribution
                matched.append((contribution, token, self.df.get(token, 0)))
            for phrase in entry["phrases"]:
                if len(phrase) < 4 or phrase not in query.lower():
                    continue
                phrase_tokens = [
                    stem(word) for word in TOKEN_RE.findall(phrase)
                    if word not in STOP
                ]
                if phrase_tokens and any(
                        self.df.get(word, 0) <= rare for word in phrase_tokens):
                    score += 5.0
            if score > 0:
                scored.append((score, entry["name"], matched))
        if not name_hit and not any(
                self.df.get(token, 0) <= rare for token in query_tokens):
            return []
        scored.sort(key=lambda item: (-item[0], item[1]))
        result = []
        for score, name, matched in scored[:max(1, min(int(limit), 20))]:
            matched.sort(reverse=True)
            why = ", ".join(
                f"{token}(df {count})" for _, token, count in matched[:3])
            result.append({
                "name": name,
                "score": round(score, 3),
                "why": why or "name match",
            })
        return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", nargs="?", default="")
    parser.add_argument("--root", default=str(DEFAULT_ROOT),
                        help="catalog root (default: os/skills)")
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--list", action="store_true",
                        help="print every skill name and exit")
    args = parser.parse_args(argv)
    index = Index(args.root)
    if args.list:
        names = sorted(entry["name"] for entry in index.entries)
        if args.json:
            print(json.dumps(names))
        else:
            for name in names:
                print(name)
        return 0
    if not args.query.strip():
        parser.error("a query is required unless --list is used")
    matches = index.search(args.query, args.limit)
    if args.json:
        print(json.dumps({"query": args.query, "matches": matches}, indent=2))
    elif not matches:
        print("NO_MATCH")
    else:
        for match in matches:
            print(f"{match['name']}\t{match['score']}\t{match['why']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

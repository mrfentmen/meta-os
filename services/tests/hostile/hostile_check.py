#!/usr/bin/env python3
"""Validate the hostile input packs (B-L1-125..134).

This checks the PACKS, not the parsers: the Goose toolchain does not exist on this host, so
nothing here can execute a parser. What it can do -- and what keeps the packs from rotting
into prose -- is enforce that every case is well formed:

  - the case matches the documented line format
  - the expected code exists in services/common/err/err.goose (a typo'd code is a case that can
    never pass, and nobody would notice until someone tried)
  - a `hex:` input is actually hex, and decodes
  - a `generated:` input names a generator this file knows about
  - a `"quoted"` input is a single properly escaped string with no stray pipe
  - every pack has at least one accept case (expect CODE_OK) and one reject case

Usage:
    python3 services/tests/hostile/hostile_check.py          # report
    python3 services/tests/hostile/hostile_check.py --list   # also list every case

Exit: 0 all packs valid, 1 a pack is malformed, 2 a pack is missing.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
ERR = os.path.join(ROOT, "services", "common", "err", "err.goose")

PACKS = [
    ("cfg.txt", "B-L1-125", "config parser"),
    ("json.txt", "B-L1-126", "JSON subset"),
    ("dns.txt", "B-L1-127", "DNS resolver"),
    ("dhcp.txt", "B-L1-128", "DHCP client"),
    ("paths.txt", "B-L1-129", "FS path parser"),
    ("args.txt", "B-L1-130", "shell argument parser"),
    ("manifest.txt", "B-L1-131", "update manifest"),
    ("keymap.txt", "B-L1-132", "keymap tables"),
    ("logrec.txt", "B-L1-133", "log records"),
    ("bootinfo.txt", "B-L1-134", "BootInfo block"),
]

# Generators are named, not implemented twice: a `generated:` case is a promise that some
# fixture builder produces it. The list is the promise, and a case naming anything else is a
# case that does not exist yet.
GENERATORS = {
    "25_keys", "4x64_byte_labels", "64_byte_label", "100_args", "4096_byte_line",
    "161_bytes", "300_byte_path", "level_99", "two_files_same_path",
    "size_not_matching_content", "two_signature_lines", "bytes_after_signature_line",
    "two_files_valid", "discover_without_236_magic", "offer_option1_absent",
    "offer_option54_absent", "two_offers", "offer_10_0_0_5_mask_24_gw_1",
    "response_with_id_plus_one", "map_count_33_against_32_slots", "one_zero_length_region",
    "discover_without_option53",
    "two_overlapping_regions", "type_99", "entry_size_0", "all_reserved", "two_usable_regions",
}

LINE = re.compile(r"^CASE\s+([A-Za-z0-9_.-]+)\s*\|\s*(.+?)\s*\|\s*expect\s+([A-Z_0-9]+)\s*\|\s*(.+)$")


def known_codes():
    with open(ERR, "r", encoding="utf-8") as handle:
        text = handle.read()
    codes = set(re.findall(r"^let\s+([A-Z][A-Z_0-9]*):\s*i64\s*=", text, re.M))
    codes.add("CODE_OK")
    return codes


def split_input(raw):
    """Return (kind, payload). The input field may contain '|' inside quotes, so the case
    regex is greedy up to the LAST ' | expect ' -- this only needs to classify the result."""
    raw = raw.strip()
    if raw.startswith("hex:"):
        return "hex", raw[4:]
    if raw.startswith("generated:"):
        return "generated", raw[10:]
    return "text", raw


def count_unescaped_quotes(s):
    """Escaped quotes (\\\") are data, not delimiters: counting them is how a valid case gets
    reported as malformed."""
    n = 0
    i = 0
    while i < len(s):
        if s[i] == "\\":
            i += 2
            continue
        if s[i] == '"':
            n += 1
        i += 1
    return n


def check_pack(path, task, what, codes, warn):
    cases = 0
    accepts = 0
    rejects = 0
    names = set()
    with open(path, "r", encoding="utf-8") as handle:
        for lineno, line in enumerate(handle, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            match = LINE.match(stripped)
            if not match:
                warn("%s:%d does not match the CASE format: %s" % (os.path.basename(path), lineno, stripped[:60]))
                continue
            name, raw, code, why = match.group(1), match.group(2), match.group(3), match.group(4)
            cases += 1
            if name in names:
                warn("%s: duplicate case name %s" % (os.path.basename(path), name))
            names.add(name)
            if code not in codes:
                warn("%s: case %s expects unknown code %s" % (os.path.basename(path), name, code))
            if len(why.split()) < 3:
                warn("%s: case %s has no useful 'why'" % (os.path.basename(path), name))
            if code == "CODE_OK":
                accepts += 1
            else:
                rejects += 1

            kind, payload = split_input(raw)
            if kind == "hex":
                if not re.fullmatch(r"(?:[0-9a-fA-F]{2})+", payload):
                    warn("%s: case %s has a hex input that is not whole bytes of hex: %r"
                         % (os.path.basename(path), name, payload[:40]))
                elif len(payload) < 4:
                    warn("%s: case %s has a hex input shorter than 2 bytes" % (os.path.basename(path), name))
            elif kind == "generated":
                if payload not in GENERATORS:
                    warn("%s: case %s names generator %r which is not in GENERATORS"
                         % (os.path.basename(path), name, payload))
            else:
                if not (payload.startswith('"') and payload.endswith('"')):
                    warn("%s: case %s text input is not quoted" % (os.path.basename(path), name))
                elif count_unescaped_quotes(payload) % 2 != 0:
                    warn("%s: case %s has an unbalanced quote" % (os.path.basename(path), name))

    if cases == 0:
        warn("%s: no cases at all" % os.path.basename(path))
    if accepts == 0:
        warn("%s: every case expects failure; a pack with no accept case cannot catch over-refusal"
             % os.path.basename(path))
    if rejects == 0:
        warn("%s: no case expects failure" % os.path.basename(path))
    print("  %-14s %-9s %2d cases  %2d accept  %2d reject  (%s)" % (os.path.basename(path), task, cases, accepts, rejects, what))
    return cases


def main(argv):
    show = "--list" in argv
    problems = []

    def warn(msg):
        problems.append(msg)

    if not os.path.exists(ERR):
        print("cannot find %s" % ERR)
        return 2
    codes = known_codes()

    print("hostile input packs (format and codes only, parsers not executed)")
    total = 0
    for fname, task, what in PACKS:
        path = os.path.join(HERE, fname)
        if not os.path.exists(path):
            print("  MISSING %s (%s)" % (fname, task))
            return 2
        total += check_pack(path, task, what, codes, warn)

    if show:
        print("")
        for fname, _, _ in PACKS:
            with open(os.path.join(HERE, fname), "r", encoding="utf-8") as handle:
                for line in handle:
                    if line.startswith("CASE"):
                        print("  %s: %s" % (fname, line.strip().split(" | ")[0]))

    print("")
    print("%d cases across %d packs, %d codes known" % (total, len(PACKS), len(codes)))
    if problems:
        print("")
        for msg in problems:
            print("PROBLEM " + msg)
        print("")
        print("packs invalid: %d problem(s)" % len(problems))
        return 1
    print("packs valid. NOTE: this proves the cases are well formed, NOT that any parser refuses them.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

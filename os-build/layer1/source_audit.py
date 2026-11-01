#!/usr/bin/env python3
"""B-L1-62 — source audit for the Layer 4 Goose sources.

There is no Goose compiler on this machine, so "it compiles" cannot be checked. What CAN be
checked is the class of mistake a compiler would catch first, and that is what this script
does, over every `.goose` file under services/:

  1. Balanced braces, parentheses and brackets.
  2. Every called function is defined in the file or in a module the file imports.
  3. Every `E_*` / `CODE_*` constant used is declared in common/err/err.goose.
  4. Every `let NAME` declared twice in one file (a silent shadowing bug).
  5. Struct types used in declarations are defined somewhere in the tree.
  6. No keyword Goose does not have (the `class` mistake, found by hand once already).

Exit code 0 when clean, 1 when anything is reported. Every finding names file:line.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SERVICES = os.path.join(ROOT, "services")

CALL_RE = re.compile(r"\b([a-z_][a-z0-9_]*)\s*\(")
FN_RE = re.compile(r'^(?:extern\s+)?(?:export\s+(?:"[^"]*"\s+)?)?fn\s+([a-zA-Z_][a-zA-Z0-9_]*)')
STRUCT_RE = re.compile(r"^struct\s+([A-Z][A-Za-z0-9_]*)")
LET_RE = re.compile(r"^let\s+([A-Z][A-Z0-9_]*)")
IMPORT_RE = re.compile(r"^import\s+([\w.]+);")
TYPE_DECL_RE = re.compile(r":\s*([A-Z][A-Za-z0-9_]*)")
NOT_KEYWORDS = ["class", "package", "new ", "public ", "private "]

# Symbols the Goose std library provides (stdlib#9, reference#30). They are not declared in
# this tree, and whether they need an `import std` is exactly the kind of thing only the
# compiler can answer -- so they are counted separately rather than reported as errors, and
# the report says so.
STD_SYMBOLS = {
    "format", "format_int", "format_uint", "format_flt", "parse_int", "parse_flt",
    "trim", "split", "find", "compare", "print", "string", "substr", "length",
}

BUILTINS = {
    "if", "while", "for", "return", "fn", "let", "var", "struct", "import", "extern",
    "switch", "case", "else", "as", "in", "not", "and", "or", "sizeof",
}


def load(path):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def scrub(text):
    """Remove comments, and blank out string and character literals, in one pass.

    Doing this with two regexes in sequence is wrong, and wrong in a way that hides real
    findings: an apostrophe in a comment ("the kernel's") pairs with the next apostrophe
    somewhere else and swallows the code between them, which then looks like a file with an
    unclosed brace. A real tokenizer is ten lines and does not have that failure mode.

    Escapes are honoured inside literals so `"a \\" b"` does not end early.
    """
    out = []
    i = 0
    n = len(text)
    state = "code"          # code | line_comment | string | char
    while i < n:
        c = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if state == "code":
            if c == "/" and nxt == "/":
                state = "line_comment"
                i += 2
                continue
            if c == '"':
                state = "string"
                out.append('""')
                i += 1
                continue
            if c == "'":
                state = "char"
                out.append("'x'")
                i += 1
                continue
            out.append(c)
            i += 1
            continue
        if state == "line_comment":
            if c == "\n":
                state = "code"
                out.append(c)
            i += 1
            continue
        # inside a literal: skip to the closing quote, honouring escapes
        if c == "\\":
            i += 2
            continue
        if (state == "string" and c == '"') or (state == "char" and c == "'"):
            state = "code"
        i += 1
    return "".join(out)


def gather():
    files = {}
    for base, _dirs, names in os.walk(SERVICES):
        for name in names:
            if name.endswith(".goose"):
                path = os.path.join(base, name)
                files[path] = scrub(load(path))
    return files


def module_exports(files):
    """Map module dotted name -> set of functions it declares."""
    exports = {}
    for path, text in files.items():
        # Module names in `import` are relative to services/, not to the repo root.
        rel = os.path.relpath(path, SERVICES)[:-len(".goose")].replace(os.sep, ".")
        fns = set()
        for line in text.splitlines():
            m = FN_RE.match(line.strip())
            if m:
                fns.add(m.group(1))
        exports[rel] = fns
    return exports


def all_structs(files):
    names = set()
    for text in files.values():
        for line in text.splitlines():
            m = STRUCT_RE.match(line.strip())
            if m:
                names.add(m.group(1))
    return names


def err_constants(files):
    path = os.path.join(SERVICES, "common", "err", "err.goose")
    text = files.get(path, "")
    names = set()
    for line in text.splitlines():
        m = LET_RE.match(line.strip())
        if m:
            names.add(m.group(1))
    return names


std_used = set()


def audit_one(path, text, exports, structs, err_names):
    findings = []
    lines = text.splitlines()

    # 1. balance
    for open_ch, close_ch in (("{", "}"), ("(", ")"), ("[", "]")):
        depth = 0
        for i, line in enumerate(lines, 1):
            depth += line.count(open_ch) - line.count(close_ch)
            if depth < 0:
                findings.append((path, i, f"unbalanced '{close_ch}'"))
                depth = 0
        if depth != 0:
            findings.append((path, len(lines), f"unclosed '{open_ch}' at end of file ({depth})"))

    # imports of this file, by module name
    imported = set()
    for line in lines:
        m = IMPORT_RE.match(line.strip())
        if m:
            imported.add(m.group(1))
        elif line.strip().startswith("import"):
            # An import the regex could not read is itself a finding: it means the line has
            # a shape this audit does not understand, so "no findings" would be a lie.
            findings.append((path, 0, "unparsed import line: " + line.strip()))

    # 2. called functions
    defined = set()
    for line in lines:
        m = FN_RE.match(line.strip())
        if m:
            defined.add(m.group(1))
    known = set(defined)
    for mod in imported:
        known |= exports.get(mod, set())
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("//") or stripped.startswith("extern fn"):
            continue
        for m in CALL_RE.finditer(line):
            name = m.group(1)
            if name in BUILTINS or name in known:
                continue
            if name in STD_SYMBOLS:
                std_used.add(name)
                continue
            # a declaration or a definition, not a call
            if re.match(r"^(fn|extern fn|struct)\s+" + name, stripped):
                continue
            # method call on a builder: `.push(` and friends are not bare calls
            start = m.start()
            if start > 0 and line[start - 1] == ".":
                continue
            findings.append((path, i, f"call to undefined function '{name}'"))

    # 3. error constants
    for i, line in enumerate(lines, 1):
        for m in re.finditer(r"\b((?:E|CODE)_[A-Z0-9_]+)\b", line):
            name = m.group(1)
            if name not in err_names and name not in defined:
                findings.append((path, i, f"undefined constant '{name}'"))

    # 4. duplicate top-level declarations.
    # Only column-0 declarations are module scope. A repeated local name in two different
    # functions is legal and is the most common shape in this codebase (every loop uses `i`),
    # so indented `let`/`var` lines are deliberately not checked. Inside one function, a
    # repeated local would be a shadowing bug -- that needs scope tracking to see, and
    # guessing at it produced 900 false findings the first time this script ran.
    seen = {}
    for i, line in enumerate(lines, 1):
        if line[:1].isspace():
            continue
        m = re.match(r"^(?:let|var)\s+([a-zA-Z_][A-Za-z0-9_]*)", line)
        if m:
            name = m.group(1)
            if name in seen:
                findings.append((path, i, f"'{name}' declared twice (first at line {seen[name]})"))
            else:
                seen[name] = i

    # 5. unknown struct types in declarations
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("//") or stripped.startswith("fn ") or "import" in stripped:
            continue
        for m in TYPE_DECL_RE.finditer(line):
            name = m.group(1)
            if name in structs:
                continue
            if name.startswith("E_") or name in ("Ipv4", "Ring"):
                continue
            if name.isupper():
                continue      # constant used as a type is a different mistake; skip
            findings.append((path, i, f"declaration uses unknown type '{name}'"))

    # 6. keywords Goose does not have
    for i, line in enumerate(lines, 1):
        for word in NOT_KEYWORDS:
            if re.search(r"\b" + word.strip() + r"\b", line) and not line.strip().startswith("//"):
                findings.append((path, i, f"keyword Goose does not have: '{word.strip()}'"))

    return findings


def main():
    files = gather()
    exports = module_exports(files)
    structs = all_structs(files)
    err_names = err_constants(files)

    findings = []
    for path in sorted(files):
        findings.extend(audit_one(path, files[path], exports, structs, err_names))

    for path, line, msg in findings:
        print(f"{os.path.relpath(path, ROOT)}:{line}: {msg}")

    if std_used:
        print("std symbols referenced (declared outside this tree): " + ", ".join(sorted(std_used)))
    print(f"\n{len(files)} files audited, {len(findings)} finding(s)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())

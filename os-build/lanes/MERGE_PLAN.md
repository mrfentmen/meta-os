# Merge plan — Hana's tool branches

State at the time of writing: `main` is `d90c9d77`, which already contains
`hana/science-lab-eval` merged with `--no-ff` (clean, 0 conflicts, registry
still parses with 24 agents).

## What was measured, not guessed

Each branch below was dry-run against `main` with `git merge-tree --write-tree`,
which reports conflicts without touching the working tree:

```
git merge-tree --write-tree main origin/hana/<branch>
```

All sixteen branches from 2026-11-03 came back **clean individually**. That is
the whole story and the whole trap: none of them conflict with `main`, but all
of them edit the same two files, so they conflict with *each other*.

- `agent-layer/MANIFEST.md`
- `agents/registry.json`

Each branch adds one tool entry plus one `eval/<domain>/` directory. Merging
them one after another means the second merge onwards hits overlapping hunks in
those two files, every time.

## Order to take them

Merge in this order. `science-lab-tools` goes first because its eval directory
pairs with the harness already merged; the rest are independent of each other
and the order only decides who conflicts with whom.

| # | branch | commits | files |
|---|---|---|---|
| 1 | `hana/science-lab-tools` | 4 | 13 |
| 2 | `hana/aegis-tools` | 4 | 11 |
| 3 | `hana/custos-tools` | 4 | 12 |
| 4 | `hana/nervus-tools` | 4 | 11 |
| 5 | `hana/imperium-tools` | 4 | 11 |
| 6 | `hana/nypd-tools` | 4 | 11 |
| 7 | `hana/fdny-tools` | 4 | 11 |
| 8 | `hana/ems-tools` | 4 | 11 |
| 9 | `hana/mta-tools` | 4 | 11 |
| 10 | `hana/dsny-tools` | 4 | 11 |
| 11 | `hana/dep-tools` | 4 | 11 |
| 12 | `hana/doe-tools` | 4 | 11 |
| 13 | `hana/hospital-tools` | 4 | 11 |
| 14 | `hana/hands-free-tools` | 4 | 11 |
| 15 | `hana/musica-tools` | 4 | 11 |

## Procedure, one branch at a time

```sh
git checkout main
git merge --no-ff --no-commit origin/hana/aegis-tools

# if a conflict is reported:
git diff --name-only --diff-filter=U      # expect MANIFEST.md, registry.json

# MANIFEST.md: keep BOTH sides. The entries are independent table rows.
# registry.json: do NOT hand-merge the conflict markers. Take main's copy and
# add the branch's agent objects with a parser, so the file cannot end up with
# a trailing comma that only shows up at runtime:
git checkout --ours agents/registry.json
git show origin/hana/aegis-tools:agents/registry.json > /tmp/theirs.json
python3 - <<'PY'
import json
ours = json.load(open('agents/registry.json'))
theirs = json.load(open('/tmp/theirs.json'))
def key(a): return a.get('name') or a.get('id')
have = {key(a) for a in ours['agents']}
for a in theirs['agents']:
    if key(a) not in have:
        ours['agents'].append(a)
json.dump(ours, open('agents/registry.json', 'w'), indent=2)
print('agents now', len(ours['agents']))
PY

git add -A && git commit -m "Merge <branch>: <one line on what it adds>"
```

## Verify after every merge

```sh
python3 -c "import json;d=json.load(open('agents/registry.json'));print(len(d['agents']))"
node --check agents/runtime.mjs && node --check agents/submit.mjs
```

A merge that leaves `registry.json` unparseable is not merged. That check is
cheap and it has already caught auto-merge damage once.

## What is deliberately not in this list

Thirty-eight `hana/*` refs exist. Most are stale drafts from earlier rounds
(`build-wave-*`, `ui-wave-*`, `musica` at 30 commits behind, `os-shell`,
`surfaces`). They are not merge candidates for the hackathon: they rewrite
shared UI files that the current desktop no longer uses, and taking them would
put unreviewed UI changes under a working demo. Leave them archived.

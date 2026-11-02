# Section H — Surface and unicode checks (R13-176..200)

Run: `node os-build/layer1/surface_passes.mjs`. Records:
`os-build/round13/aegis/SURFACE_PASSES.json`, `os-build/round13/aegis/surface_passes.txt`.

**25 / 25 addressed: 16 artifacts scanned (1.9 M characters across the glob-based passes),
9 records where the named artifact is not in this tree, 0 findings.**

## Scanners used, unmodified

- `aegis/surface.mjs` — zero-width characters, invisible operators, BOM, bidi overrides,
  bidi isolates, tag characters, mixed-script tokens.
- `aegis/confusables.mjs` — non-Latin characters with a Latin lookalike, and invisible
  format characters, over display names extracted from the same materials.

The record carries counts, code points and line/column. It carries no surrounding text and
no copied character in context, which is the same rule the other Aegis wings follow.

## A false gap found and fixed in the tool, not in the record

The first run reported `services/**/*.goose` and `kernel/src/*.rs` as missing while 180 and
193 of those files sat in the tree: the walker had `**` but no `*`. That is a false gap, the
same class of error as a false pass, and the rows below are scans only because it was fixed
before they were written. It is noted here so a reader comparing this run to a later one knows
why the counts moved.

## Scanned

| task | artifact | files | characters | surface | names | confusable hits |
|---|---|---:|---:|---:|---:|---:|
| R13-176 | `README.md` | 1 | 20,073 | 0 | 6 | 0 |
| R13-177 | `site/index.html` | 1 | 10,037 | 0 | 2 | 0 |
| R13-178 | `os-build/DEMO_SCRIPT.md` | 1 | 4,878 | 0 | 1 | 0 |
| R13-179 | `os-build/layer1/DEMO_30S.md` | 1 | 2,846 | 0 | 3 | 0 |
| R13-180 | `site/index.html` + `face/index.html` | 2 | 11,760 | 0 | 6 | 0 |
| R13-181 | `site/index.html` | 1 | 10,037 | 0 | 2 | 0 |
| R13-182 | `face/index.html` + `face/face.js` | 2 | 29,600 | 0 | 40 | 0 |
| R13-185 | `agents/registry.json` | 1 | 12,802 | 0 | 36 | 0 |
| R13-190 | `nervus/tray.json` + `nervus/contracts.mjs` | 2 | 9,567 | 0 | 0 | 0 |
| R13-191 | `os-build/aegis/findings.jsonl` | 1 | 3,204 | 0 | 0 | 0 |
| R13-192 | `os-build/BUFFY_ROUND13_STATUS.md` | 1 | 1,614 | 0 | 0 | 0 |
| R13-193 | `os-build/SUBMISSION_CHECKLIST.md` | 1 | 1,682 | 0 | 0 | 0 |
| R13-195 | `site/index.html` (store page does not exist) | 1 | 10,037 | 0 | 2 | 0 |
| R13-198 | `docs/**/*.md` | 16 | 162,521 | 0 | 25 | 0 |
| R13-199 | `services/**/*.goose` | 180 | 1,620,533 | 0 | 357 | 0 |
| R13-200 | `services/**/*.goose` + `kernel/src/*.rs` | 193 | 1,866,937 | 0 | 385 | 0 |

Zero in every surface bucket (`zero-width`, `invisible-operator`, `bom`, `bidi-override`,
`bidi-isolate`, `tag-char`, `mixed-script`) and zero confusable hits over 865 extracted names.

## Not found — filed as gaps, not as passes

| task | artifact | why |
|---|---|---|
| R13-183 | `board/index.html` | the board client is a Goose service and a JSON API; it ships no HTML surface in the tree |
| R13-184 | `relay/index.html`, `relay/relay.js` | the relay viewer is not a file in this tree |
| R13-186 | world pack display text | no world-pack manifest exists |
| R13-187 | science-lab export text | no labs export artifact |
| R13-188 | officina output text | no officina artifact |
| R13-189 | musica display text | no musica artifact |
| R13-194 | X post draft | no draft file |
| R13-196 | goal file | no `GOAL.md` |
| R13-197 | skill descriptions | `.agents/skills` is outside this repository (project root is its parent), so it was not scanned |

R13-195 is scanned against `site/index.html` because the list's "store page" has no file; the
substitution is named in the table rather than hidden, and the counts are the site page's
counts, not a store page's.

## What this section cannot claim

- That the OS's *rendered* surface is clean. These are the bytes of the source artifacts; what
  a browser draws after CSS, fonts and substitution is a different question and no scanner
  here answers it.
- That 865 names is every name a user sees. Names were extracted by shape (JSON `name`
  values, `<title>`, `aria-label`, capitalised quoted strings) and a name that arrives from
  another source at runtime was never in the input.
- That the 9 missing artifacts are unimportant. They are missing inputs. Aegis can no more
  clear an artifact that does not exist than it can scan one.

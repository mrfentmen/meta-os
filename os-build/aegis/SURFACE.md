# Aegis surface checks — clean

Run `surface-2026-11-02T11-21-31-490Z`. Materials: `README.md`, `site/index.html`, `os-build/DEMO_SCRIPT.md`, `os-build/layer1/DEMO_30S.md`, `os-build/SUBMISSION_CHECKLIST.md`, `os-build/aegis/SWEEP.md`, `os-build/aegis/OSINT.md`.

Two shapes: characters that draw nothing, and words that look Latin but are not. **The surrounding text is never quoted** — only the codepoint, the kind, and the location, because this report is public and the line may be what the character was hiding.

## Counts

| kind | count |
|---|---|
| `zero-width` | 0 |
| `invisible-operator` | 0 |
| `bom` | 0 |
| `bidi-override` | 0 |
| `bidi-isolate` | 0 |
| `tag-char` | 0 |
| `mixed-script` | 0 |

## Locations

None: 7 file(s) read, 39185 characters checked.

## What this cannot check

- Whether a Latin word is *itself* a lookalike of another Latin word. That needs a
  confusables table and the target word list, which is a different check.
- Text rendered in an image or a PDF; only these files were read.
- Intent. A zero-width joiner is legitimate in some scripts; the line number is where a
  reader looks, not a verdict.

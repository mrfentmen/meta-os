# Aegis OPSEC v1 — pre-publish review

Run `opsec-2026-11-02T11-13-45-200Z`. Materials: `README.md`, `os-build/DEMO_SCRIPT.md`, `os-build/layer1/DEMO_30S.md`, `os-build/SUBMISSION_CHECKLIST.md`, `site/index.html`.

The question is the one in the spec: **does this tell a stranger something we did not decide to tell?** Locations and kinds are recorded; the matched text never is.

## Counts

| check | what it means | count |
|---|---|---|
| `home-path` | a home path names the account and the machine's layout | 0 |
| `private-ip` | a private address describes a network a reader cannot see | 0 |
| `email` | an address published in passing becomes the address people write to | 0 |
| `internal-host` | an internal name is a hint about infrastructure that is not public | 0 |
| `machine-name` | the machine that built the artifact is not part of the artifact | 0 |

## Locations

None: 5 file(s) read, no check fired.

## Findings filed

None. The materials as they stand pass every automated check above.

## What this cannot check

- Whether a claim in the copy is true. That is a reading job, and the checklist's
  review items are for the person publishing, not for a regex.
- Git history, commit metadata, or the repository's public metadata. Those are the
  other half of OPSEC and a separate pass.
- Text in images, PDFs, or a rendered page. Only these files were read.

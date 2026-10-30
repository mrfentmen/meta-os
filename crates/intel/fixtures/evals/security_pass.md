# INT-011 security pass (Pax, 2026-10-27)

Scope: the whole tree at tip 9da62a9, scanned with
`intel/security_pass.py` (run: `python3 intel/security_pass.py`).
The scanner reports file, line, and kind only, never a
matched value, so the report itself cannot leak a
credential it finds. Patterns: provider token shapes
(aligned with the DSP-028 guard shapes), private key
headers, quoted credential assignments, and secret
filenames. Keyring lines are deliberately not content
scanned: a line carrying the word secret is a label, not
a value, and a line with a random secret part is
indistinguishable from the namespace strings this tree
is full of, so a content pattern for it would drown in
false positives. The keyring controls are the filename
rule, the .gitignore entries, and the drill generating
a fresh secret per run.

## Verdict

Clean: 0 findings. Every shape-shaped hit in the tree
is a documented fixture under one of the four stated
rules in the scanner docstring (repeated character,
dummy word in the value, sequential run, label word
on the line outside the match).

## Fixture hits (7, all classified, none a finding)

| File:line | Kind | Why it is a fixture |
| --- | --- | --- |
| intel/spark_down_drill.py:91 | credential-assignment | Drill-marked value in the Spark-down drill |
| intel/evals/dispatch_adversarial.md:158 | github-token | Repeated-character fake, case A4 guard bait, introduced by the DSP-023 fixture commit, never a provisioned credential |
| intel/evals/dispatch_adversarial.md:171 | github-token | Repeated-character fake, the same A4 case's plan text |
| tests/test_intel_brief.py:277 | bearer-token | Sequential filler in a redaction test that asserts the value's own removal |
| tests/test_intel_spark_down.py:41 | credential-assignment | Drill-marked value in the Spark-down test |
| tests/test_intel_spark_down.py:50 | credential-assignment | Drill-marked value in the Spark-down test |
| tests/test_relay_intel_config.py:57 | credential-assignment | Test-labeled value in a presence-only test that asserts the value never appears in config output |

Two more checks, both clean:

- Secret filenames: no file in the tree is named like
  a secret file (env, keyring, job-secret, admin_secret,
  pem, key). The job secret file path itself,
  ~/.config/muse-relay/job-secret, lives outside this
  tree by design; the pass checks the tree, not the
  operator's machine, and the live crew secret was
  never read or compared.
- The one committed keyring literal in the tree, the
  spoof drill's dummy secret, is removed by this
  batch: the drill now generates a fresh random secret
  per run. The drill still passes 6/6 after the change,
  and the regenerated transcript is
  intel/evals/spoof_dispatch.log.

## .gitignore gaps closed by this batch

Before this batch, .gitignore covered token files and
.config/ but not env or keyring names. Added: *.env,
.env*, *.keyring, job-secret, admin_secret, *.pem,
*.key. Verified with git check-ignore for each name,
and no tracked file collides with the new entries.

## Proved, and not proved

- Proved: at this tip, the tree holds no provider
  token, private key, credential assignment, or secret
  filename outside the 7 fixtures above; the scanner
  and its 7 tests pin that result so a later batch
  cannot silently regress it.
- Not proved: git history still contains the old
  drill literal (history is append-only; the literal
  was a dummy, not a real credential, so no rotation
  is owed). A shape scan cannot prove a random-looking
  string is not a real credential, only that no
  provider-shaped, assignment-shaped, or filename-shaped
  secret exists in the tree.

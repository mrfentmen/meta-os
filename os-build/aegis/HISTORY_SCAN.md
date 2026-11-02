# Aegis git-history secret scan — counts only

Run `history-2026-11-02T14-59-10-859Z`, 2026-11-02T14:59:10.860Z. Range: `HEAD`, **1881 commits**, 8bd9824b (2026-11-02) to 5e17fc79 (2026-10-28).

**No value, matched line, or matched path is written here.** The scan counts category hits
per commit year. A hit in a test fixture, a regex, or a doc example is counted too — this is a
count of pattern-shaped lines, not a confirmed-secret count.

| category | 2026 | total |
|---|---|---|
| private-key | 0 | 0 |
| aws-access-key | 0 | 0 |
| github-token | 4 | 4 |
| slack-token | 0 | 0 |
| openai-style-key | 0 | 0 |
| stripe-key | 0 | 0 |
| jwt | 0 | 0 |
| url-credentials | 0 | 0 |
| secret-assignment | 10 | 10 |

Total category hits: **14** across **1491306** diff lines.

## Limits, stated

- Line-based: a secret split across lines is not detected.
- No pattern here distinguishes a live credential from an example. Any nonzero count needs a
  human review of the location before it is called a leak; this record deliberately cannot
  name the location without also naming the value's neighbourhood.
- The scan covers `git log HEAD` only. Other refs, stashes, and reflogs are not included.

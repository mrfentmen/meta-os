# Section G — Secret hygiene, counts only (R13-151..175)

Run: `python3 os-build/layer1/secret_counts.py`. Records:
`os-build/round13/aegis/SECRET_COUNTS.json`, `os-build/round13/aegis/secret_counts.txt`.

**25 / 25 addressed. 241 matches in total, 240 of them one noisy category, 1 requiring review.
No value, no matched string, no line number and no path is in the record.**

## The rule, and how it was enforced rather than promised

`AEGIS_SPEC.md` and `aegis/secrets.mjs` say a match is recorded as where and what kind, never
as what. This tool goes one step further: after building the record it **re-scans the finished
JSON with every pattern** and refuses to write if anything matches. The first run failed that
check — it was flagging its own stored regex text — so the record now carries each pattern's
SHA-256 instead of the pattern, and the check passes. A counts file that trips its own
scanner is the leak, and the guard is the only reason the earlier version did not ship.

No paths: the list asks for "category counts and file counts only", and a path in a public
repo is a location, so only counts are kept. The tool is committed, so the exact regex behind
every count is auditable without the record holding it.

## Commit-range passes (R13-151..165)

| task | category | range | files read | lines read | matches | files hit |
|---|---|---|---|---:|---:|---:|
| R13-151 | generic api key pattern | 10-26..10-28 | 85 | 21,217 | 0 | 0 |
| R13-152 | bearer token pattern | 10-29..10-30 | 1,358 | 262,760 | **1** | **1** |
| R13-153 | private key block pattern | 10-31 | 18 | 1,113 | 0 | 0 |
| R13-154 | password assignment pattern | 11-01 | 1,291 | 972,670 | 0 | 0 |
| R13-155 | aws-style key pattern | 11-02 | 1,126 | 130,611 | 0 | 0 |
| R13-156 | github token pattern | 10-26..10-28 | 85 | 21,217 | 0 | 0 |
| R13-157 | upstash-style token pattern | 10-29..10-30 | 1,358 | 262,760 | 0 | 0 |
| R13-158 | stripe-style key pattern | 10-31 | 18 | 1,113 | 0 | 0 |
| R13-159 | jwt pattern | 11-01 | 1,291 | 972,670 | 0 | 0 |
| R13-160 | basic-auth in URL pattern | 11-02 | 1,126 | 130,611 | 0 | 0 |
| R13-161 | ssh key path mention | 10-26..10-28 | 85 | 21,217 | 0 | 0 |
| R13-162 | env file mention | 10-29..10-30 | 1,358 | 262,760 | **240** | **105** |
| R13-163 | high-entropy string bucket | 10-31 | 18 | 1,113 | 0 | 0 |
| R13-164 | webhook secret pattern | 11-01 | 1,291 | 972,670 | 0 | 0 |
| R13-165 | session cookie pattern | 11-02 | 1,126 | 130,611 | 0 | 0 |

Range note: the tree's **first commit is 2026-10-28**, so the 10-26..10-28 window only
contains 10-28 (127 commits). The record names the window, not the work.

## Working-tree passes (R13-166..175)

| task | category | scope | files read | lines read | matches |
|---|---|---|---:|---:|---:|
| R13-166 | database connection string pattern | `services/` | 299 | 46,634 | 0 |
| R13-167 | oauth client secret pattern | `agents/`, `relay/` | 20 | 2,457 | 0 |
| R13-168 | encryption key assignment pattern | `crates/` | 389 | 106,389 | 0 |
| R13-169 | signing secret pattern | `board/`, `site/` | 5 | 1,147 | 0 |
| R13-170 | redis URL with embedded password pattern | `server/` | 29 | 8,351 | 0 |
| R13-171 | postgres URL with embedded password pattern | `os/` | 703 | 132,915 | 0 |
| R13-172 | mongodb URL with embedded password pattern | `tests/` | 408 | 53,531 | 0 |
| R13-173 | firebase-style key pattern | `face/` | 5 | 1,095 | 0 |
| R13-174 | sendgrid-style key pattern | `docs/`, `os-build/` | 754 | 88,791 | 0 |
| R13-175 | credential pair in config pattern | `image/`, root | 2,948 | 503,842 | 0 |

## The two non-zero counts, read honestly

**R13-162, 240 matches in 105 files.** The pattern is `.env` or `process.env[`. It is a
mention check, not a leak check: 240 references to environment variables across two days of
commits is what a codebase that reads configuration looks like. Counted, not alarmed. It is
in the record because the list asked for it, and it is labelled `review` confidence so nobody
reads 240 as 240 secrets.

**R13-152, 1 match in 1 file.** This is the only result that needs a human. It was an added
line in a 10-29..10-30 commit; the pattern no longer matches anything in the working tree, so
it is history-only. The value is not printed here, not in the JSON, and not in the terminal
transcript that produced this record. What is recorded is: one bearer-shaped token appeared
in one file on those two days and is not present in the tree today. Whether it was a fixture,
a placeholder, or a live token that was later rotated **cannot be determined from counts**,
and Aegis does not auto-fix or auto-close it. It goes to a human as a review item, which is
what the spec says happens to anything security-shaped.

## What this section cannot claim

- That no secret was ever committed. It claims 25 pattern passes over stated scopes with
  stated regexes; a secret in a shape none of those patterns describes is invisible to it.
- That the commit passes saw all history. `git log` was run on this clone (1,895 commits,
  full clone, first commit 2026-10-28); a commit that was rewritten or force-pushed away is
  not in it.
- That R13-152 is closed. It is filed for review, and a count cannot close it.

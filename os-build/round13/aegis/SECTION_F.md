# Section F — CISA KEV cross-checks (R13-126..150)

Run: `python3 os-build/layer1/kev_crosscheck.py`. Records:
`os-build/round13/aegis/KEV_CROSSCHECK.json`, `os-build/round13/aegis/kev_crosscheck.txt`.

**25 / 25 addressed. 0 findings to cross-check, because Section E found 0. Every one of the 25
records says so in its own line; none says "all clear".**

## The feed this run actually read

```
feed      https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json
catalog   2026.10.30
released  2026-10-30T17:02:45.3665Z
entries   1766
sha256    3aa9cf3c01f11636...
control   CVE-2021-44228 present=True
```

The SHA-256 and catalogue version are in the record so a reader can tell which catalogue
answered them. The raw 1.8 MB feed is **not** committed: it is a third-party dataset that
changes daily, and a copy in this repo would be a stale answer wearing a current date.

## Why the control is the substance of this section

The list says "a silent pass is a failed task". A matcher that returns "no KEV match" for
every input is indistinguishable from a matcher that is broken, unless it can still find a
known entry. `CVE-2021-44228` is in the catalogue and the matcher found it, so the empty
result below is a measured empty and not a dead code path.

## The per-task result, in full

All 25 rows are identical in substance, and the record keeps 25 separate lines rather than
one summary because the tasks are separate questions:

```
R13-126 .. R13-150   findings=0   0 findings of this class in Section E;
                                   nothing to cross-check.
                                   This is not a clearance of the class.
```

| class named by the list | batches | findings available | KEV flagged | cleared |
|---|---|---:|---:|---:|
| node dependency findings | 1–5 | 0 | 0 | 0 |
| rust crate findings | 1–5 | 0 | 0 | 0 |
| python dependency findings | 1–5 | 0 | 0 | 0 |
| lockfile-pinned findings | 1–5 | 0 | 0 | 0 |
| transitive findings | 1–5 | 0 | 0 | 0 |

## A matcher limitation found while building this

OSV records are keyed `RUSTSEC-…` or `GHSA-…`; the KEV catalogue is keyed `CVE-…`. A finding
whose advisory carries no CVE alias **cannot** be matched against KEV at all. The tool counts
those separately as `unmatchable_no_cve` instead of reporting them as "cleared", because
"not in KEV" and "cannot be looked up in KEV" are different sentences and only one of them is
a clearance. With zero findings the list is empty this run; on a run with findings it will
not be, and the distinction is already in the record shape.

## What this section cannot claim

- That no dependency we ship is in KEV. Nothing was found to check. The correct sentence is
  "there was no input", not "there was no risk".
- That the five batches are five different checks. They are the same check over the same
  empty set, split to match the list's numbering; the record says `batch 1..5` rather than
  pretending each batch examined new data.

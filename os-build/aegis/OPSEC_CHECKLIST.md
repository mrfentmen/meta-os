# Aegis OPSEC — the pre-publish checklist (v1, 2026-11-02)

Written for the submission that goes out **Nov 4**, and for anything published after it. Two
halves: what a machine can check (and `aegis/opsec.mjs` does), and what a person must check
because a regex cannot read a claim.

## A. Automated — run this, read the counts

```
node aegis/run-opsec.mjs
```

| check | passes when |
|---|---|
| `home-path` | zero, or every hit sits on a line marked as an example (`/Users/you/`, `<your-name>`) |
| `private-ip` | zero, or the address is the documented example range |
| `email` | only addresses we decided to publish; anything else is a finding |
| `internal-host` | zero: a public artifact must not name a name that only resolves inside |
| `machine-name` | zero: which box built the artifact is not part of the artifact |

The report is `os-build/aegis/OPSEC.md`; findings land in `findings.jsonl` like every other
Aegis record. Locations only — values are never written.

## B. By hand — the person publishing signs these

- [ ] **Every claim in the copy has an artifact behind it.** If the demo says a sweep ran, a
      report is named. If the README says a service works, a driver is named. The rule the OS
      itself uses: no claim without a source.
- [ ] **NOT BUILT is marked NOT BUILT.** A reader must be able to tell what is proven from what
      is written, without reading the repo.
- [ ] **The demo script's numbers match the last run**, not an earlier one. Re-read the report
      it quotes, at publish time.
- [ ] **No third party's data in the materials.** Screenshots, sample outputs, and fixtures must
      be ours or public-domain; faces, plates, and names in any frame are a stop.
- [ ] **The license position is stated.** "Public to read" is not a license, and the README says
      so today; decide whether that is the position for a submission.
- [ ] **Repo metadata checked by hand**: description, topics, and the public/private switch.
      A repo that was public overnight has commit metadata someone may have read.
- [ ] **Commit metadata reviewed**: author name and address on the commits that ship. A private
      address in history is published the moment the repo is.
- [ ] **Secrets pass immediately before publishing**: `node aegis/run-secrets.mjs`, and the
      triage file re-read. A key rotated after a scan is not covered by that scan.
- [ ] **Nothing in the materials points at the machine.** No absolute paths in instructions, no
      "on my Mac at …", no hostnames.
- [ ] **The final artifact was checked, not the draft.** Run A against the exact files being
      submitted after the last edit.

## What this checklist is not

It is not a guarantee. It is the list of things that have actually gone wrong in public
releases: a home directory in a screenshot, an address in a commit, a claim with no artifact
behind it. Ten items, each one cheap to check and expensive to miss.

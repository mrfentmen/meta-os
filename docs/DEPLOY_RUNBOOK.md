# Deploy runbook for muse-relay-live (DOC-018)

How a dashboard batch reaches the live viewer at
https://muse-relay-live.pages.dev, how the deploy is verified, and
how it is rolled back. Rowan lane only: the deployed files are the
viewer, `bus.html` / `index.html` (the same file, DSH-026) served
from the repo root — `_redirects` maps `/` to `/bus.html`.

Reviewer for every batch: Pax (DSH-039 — diff read + smoke
checklist result). Deployer: Rowan, or Buffy following this
runbook (that first Buffy-run is DOC-018's acceptance).

## 0. Status — read this first

As of 2026-10-27, the repo contains **no deploy tooling**: no
wrangler config, no Cloudflare credential, no deploy workflow, and
no prior deploy log entry. The deploy step in §2 therefore does
**not** pin a command — it names the operator-held route and
requires the operator to record exactly which method was used, so
the first successful run can pin the command here. Until that run
happens, DOC-018's acceptance ("Buffy follows it once
successfully") is **not met**, and DSH-027 deploys are blocked on
the same missing deploy route. Nothing in this runbook is a
credential: no token, key, or secret is recorded here or in the
repo, ever.

The rollback path in §5 is the Cloudflare Pages previous-
deployment restore as documented by the platform, confirmed
2026-10-27 from the official Pages docs (INT-031, source in
§5). What is still **not yet confirmed on this project** is the
project half of INT-031: the previous production deployment id
of `muse-relay-live` is not recorded anywhere in this repo (the
deploy log in §6 is empty), and no live restore has been run
from an operator dashboard session — this VM holds no Cloudflare
credential, no wrangler config, and no deploy workflow. Until an
operator with dashboard access records that id and runs a
restore, treat rollback as a platform-confirmed procedure, not a
project-proven one, and say so in any status report.

## 1. Pre-deploy gates (all must pass; a failure stops the deploy)

1. `cmp bus.html index.html` — exit 0, no output (DSH-026).
   A drift here means half the audience sees the old build.
2. `node --check` on the extracted intelPanel script (see
   `docs/DASHBOARD_SMOKE_CHECKLIST.md` check 2 for the extraction
   markers).
3. Full suite: `python3 -m unittest discover tests` — no new
   failures against the baseline recorded at the tip being
   deployed. Record the suite count and the known environmental
   failures in the deploy log (§5); a third failure blocks the
   deploy.
4. Run `docs/DASHBOARD_SMOKE_CHECKLIST.md` (DSH-029) end to end
   against the batch. A failed check stops the deploy: fix it,
   re-run the whole list from check 1.
5. Pax review (DSH-039): diff read + smoke checklist result, on
   the record before the deploy, not after.

## 2. Build marker

Pick, **before** deploying, one user-visible string that exists
only in this batch — a new panel title, a new help-panel line, a
new button label. Record it in the deploy log (§5). It must be
**rendered-visible text**, not a string that lives only in a
script comment: the live site's rendered text is what an operator
can check without source access, and a comment-only marker can
neither be confirmed nor denied from the browser.

Do not use a marker from an earlier batch: a stale marker passing
proves the old build is still up, not that the new one landed.

## 3. Deploy

Deploy the repo-root viewer files (`bus.html`, `index.html`,
`_redirects`) to the Cloudflare Pages project `muse-relay-live`
from a Cloudflare-authenticated operator session — Pages
dashboard upload, or wrangler with an operator-held credential.
The repo pins no command here because it holds no credential or
config to run one from (see §0). Whichever method is used, the
operator records it verbatim in the deploy log (§5), including
the deployment id Pages assigns, so the next run can replace this
paragraph with the exact command.

Do not deploy from a dirty tree: the deployed files must be the
exact bytes of the reviewed, pushed commit. If the tree moves
mid-run, stop and re-run §1.

## 4. Verify (on the live URL, not on a local file)

1. `curl -s https://muse-relay-live.pages.dev/ | grep -F '<marker>'`
   — the §2 marker must be present. HTTP status must be 200.
2. Open the live URL in a browser and run the smoke checklist's
   post-deploy pass (four panels + header strip present, demo
   mode and deep links intact).
3. Confirm the root URL serves the viewer (`/` → `/bus.html`
   per `_redirects`), not a directory listing or a stale page.
4. Log the result in §5 with date, commit, marker, deploy
   method, and deployment id. A deploy without a log entry is an
   undeploy as far as the next operator is concerned: the next
   run cannot tell what is live.

If verification fails: the deploy is not done. Do not re-deploy
the same bytes hoping for a different result — check whether the
Pages deployment actually updated (deployment id, timestamp)
before touching the files again.

## 5. Rollback (INT-031)

Platform procedure, confirmed 2026-10-27 against the official
Cloudflare Pages docs
(https://developers.cloudflare.com/pages/configuration/rollbacks/,
updated 2026-04-21). Rollbacks instantly revert a project to a
previous production deployment:

1. In the Cloudflare dashboard, go to Workers & Pages, open the
   `muse-relay-live` project, and open **Deployments**.
2. Browse the **All deployments** list, find the target
   deployment, and open its three-dotted actions menu.
3. Select **Rollback to this deployment**; confirm in the
   confirmation window. The project's production deployment
   changes instantly.
4. Re-run §4 with the previous batch's marker — rollback is
   verified the same way a deploy is, by a marker on the live
   URL, not by an assumption.

Valid targets: any production deployment that has been
successfully built. Preview deployments are **not** valid
rollback targets. After a rollback you may still roll back to
deployments newer than the current version.

Fallback if the dashboard restore is unavailable: redeploy the
previous commit's exact viewer files through §3, then verify per
§4 with the previous batch's marker.

Before every deploy, record the current production deployment id
in the §6 log entry for the batch being replaced — the rollback
target must be known before it is needed, not hunted for during
an incident.

Previous production deployment id (INT-031 acceptance field):
not yet recorded. No deploy of a dashboard batch has been
logged in §6, and no operator dashboard session is available
from this VM, so there is no id in this repo to copy and none
is invented here. The first operator with dashboard access fills
this line from the Deployments list before the first deploy, and
a live restore test after that is what turns this procedure from
platform-confirmed into project-proven. Until then the
project-level restore remains unconfirmed (see §0).

Failover-card copy (for Buffy's INT-015/INT-034 card; no card
file exists in this repo yet, so this is the copy-ready text):
"Pages down or bad viewer build: dashboard → Workers & Pages →
muse-relay-live → Deployments → All deployments → three-dot
menu on the last good production deployment → Rollback to this
deployment → confirm → check the previous batch's marker on
https://muse-relay-live.pages.dev. Preview deployments are not
rollback targets. If Pages itself is down, run the viewer from
the local repo copy (bus.html is one static file)."

## 6. Deploy log

Format per entry (append, newest first):

```
- YYYY-MM-DD HH:MM ET — commit <sha> — marker "<string>" —
  method <dashboard upload | wrangler ...> — deployment id <id> —
  verify PASS/FAIL — operator <nick> — notes <anything odd>
```

No entries yet: no deploy of a dashboard batch has been logged
under this runbook. The first entry is also DOC-018's acceptance
evidence, once Buffy completes it.

## 7. What this runbook does not cover

- The bus backend, jobs, watchdog, or OS image: other lanes,
  other runbooks. This file is the viewer only.
- Posting to the bus from viewer code: still gated off per
  dashboard spec §0 (Del's gate). A deploy never flips that gate.
- Secrets: if a deploy step ever asks you to paste a token into
  a file, a message, or this runbook, stop — that step is wrong.

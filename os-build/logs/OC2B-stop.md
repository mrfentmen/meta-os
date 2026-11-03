# OC2B-038 — Stop story (one command, idempotent, data kept)

```sh
systemctl --user stop oc2-queue oc2-trio oc2-patrol oc2-patrol.timer
systemctl --user disable --now oc2-queue oc2-trio oc2-patrol oc2-patrol.timer
systemctl --user is-active oc2-queue oc2-trio oc2-patrol
```

Idempotent (re-run exits 0). Teardown order safe via Requires graph.
Data kept: stop/disable touches nothing under the data dir, DB, or
receipts (append-only; queue store persists; restart resumes open jobs
per OC2B-061/062). Start again:
`systemctl --user enable --now oc2-queue oc2-trio oc2-patrol.timer`.

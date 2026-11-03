# OC2B-024 — Rollback story (previous version in one command)

Data dir never touched by rollback (code rolls back; receipts persist).

```sh
git checkout <PREV_SHA> -- agent-layer/ && sh agent-layer/install.sh
```

`<PREV_SHA>` = last-known-good commit from lane status / handoff
(current: `7d402cd2` S10; update as sections land).

Sufficient because install.sh copies units fresh (no hardcoded list),
refreshes `OC2_CHECKOUT`, re-enables the shipped set. No step writes the
data dir.

Verify: `systemctl --user status oc2-queue oc2-trio oc2-patrol` all
active/ok; `python3 -m py_compile server/queue/*.py` exit 0; queue depth
equal before/after (record numbers at rollback time).

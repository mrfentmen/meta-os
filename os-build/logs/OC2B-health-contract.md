# OC2B-032 — Health-check contract per service

| Service | Check | Healthy = |
|---|---|---|
| oc2-queue | `curl -s 127.0.0.1:$PORT/health` (default 8935) | HTTP 200 `{"ok": true, "service": "trio-queue", ...}` (verified live: odd-port run, <1s) |
| oc2-trio | process-alive + freshness — **no HTTP endpoint** (honest: process+freshness, not a URL) | `systemctl --user is-active oc2-trio` = active AND a recent `trio:<jid>:result` write in store |
| oc2-patrol (oneshot) | last-run exit + heartbeat freshness | last `journalctl --user -u oc2-patrol` run exit 0 AND `crew-status.json` fresh (rewritten every cycle) |

```sh
curl -s "127.0.0.1:${OC2_QUEUE_PORT:-8935}/health"
systemctl --user is-active oc2-queue oc2-trio oc2-patrol
journalctl --user -u oc2-patrol -n 5 --no-pager
```

Bind is 127.0.0.1 only (OC2B-ports.txt). No health path invents data:
trio has deliberately no URL — process + store freshness is the contract.

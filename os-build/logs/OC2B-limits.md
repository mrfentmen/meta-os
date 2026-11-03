# OC2B-035 — Resource limits per service (PROPOSED, UNVERIFIED-ON-TARGET)

No systemd on build host — values are drop-in proposals, not live-verified.

```ini
# oc2-queue.service.d/10-limits.conf — [Service] MemoryMax=512M CPUQuota=100%
# oc2-trio.service.d/10-limits.conf  — [Service] MemoryMax=512M CPUQuota=100%
# oc2-patrol.service.d/10-limits.conf — [Service] MemoryMax=256M CPUQuota=50%
```

| Service | MemoryMax | CPUQuota | Note |
|---|---|---|---|
| oc2-queue | 512M | 100% | long-lived simple |
| oc2-trio | 512M | 100% | long-lived simple |
| oc2-patrol | 256M | 50% | oneshot, bounded by --max-checks |

Enforcement = systemd/cgroup + `$` caps via `spark_guardrail.py`
($75 hard stop; patrol governor pauses at $5 reserve). No in-code RSS
accounting. Verify on target: `systemctl --user show <unit>
-p MemoryMax,CPUQuota` + `systemd-cgtop` under load.

# Debian logging (OS-095)

- journald captures stdout/stderr of every unit (volatile by
  default on small images unless `Storage=persistent` + `/var/log/journal`
  exists) and syslog-compatible forwarding where configured.
- Our image: no logrotate config ships in the bake, no persistent
  journal dir is created, no log size cap is set. Crew output
  lands in the journal and in per-service logs beside the relay
  payload (check the units for exact paths — not audited here).
- What is lost on crash: everything still in RAM (journal
  volatile) plus anything buffered and unwritten. Rotation policy:
  none — a chatty agent fills `/var` until the 3 GiB image is
  full, and a full root breaks apt, updates, and new records
  together (rough edge).

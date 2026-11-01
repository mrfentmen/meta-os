# Firstboot checklist (NC-089) — from os/os/README-FIRSTBOOT.md (read-only)

The image carries zero credentials. On first boot, on the console,
`metaos-firstboot` asks for:

1. Crew login — which crew this machine joins (operator types it).
2. Upstash REST URL for the bus (`MUSE_RELAY_URL`).
3. Bus token → stored at `/etc/metaos/token` (chmod 600). THIS is the
   push-token location the task asks for: `/etc/metaos/token`.
4. Optional Muse Spark API key (blank = agent transport only).
5. It also generates the local job-signing keyring
   (`/etc/metaos/job-secret`, chmod 600).

Then: git name and email for the checkout (standard `git config` —
operator's own values; nothing prefilled). Prompt times out after 60 s
so unattended boots never wedge; re-run any time with
`sudo metaos-firstboot`.

STOP file location for the loop (from METAOS_LOOP.md): the loop halts
when the STOP file appears in its state dir — operator creates it to
freeze the loop before touching anything.

Dashboard is live immediately at `http://<machine>:8080/` (no secrets
needed — local static viewer).

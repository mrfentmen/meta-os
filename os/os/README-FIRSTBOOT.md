# Meta OS — first boot

The image contains **zero credentials** (OS-012). On first boot:

1. The machine boots into the crew target (`relay.target`). The dashboard
   is live immediately at `http://<machine>:8080/` — it is a local static
   viewer and needs no secrets.
2. On the console, `metaos-firstboot` asks for:
   - the Upstash REST URL for the bus (`MUSE_RELAY_URL`),
   - the bus token (stored at `/etc/metaos/token`, chmod 600),
   - an optional Muse Spark API key (blank = agent transport only).
   It also generates this machine's local job-signing keyring
   (`/etc/metaos/job-secret`, chmod 600).
   The prompt times out after 60s so unattended boots never wedge —
   finish later any time with `sudo metaos-firstboot`.
3. Once secrets exist, the bus watcher, the boot job sweep, and the
   overseer timer start. Until then systemd skips them (condition on
   `/etc/metaos/secrets.env`) and the boot checklist says so honestly.

## Boot entries

- **Meta OS** — normal entry: stock Debian kernel, `systemd.unit=relay.target`.
- **Meta OS (rescue — base system, no crew)** — boots `multi-user.target`
  only (OS-022): base system, no crew services, for a machine whose crew
  layer is broken but whose OS is fine.

## Updates

`sudo metaos-update /path/to/bundle` (verify → apply to `/opt/relay` →
restart `relay.target`); `sudo metaos-update --rollback` re-applies the
previous tree. Base OS packages do not update through this path.

## Login

Console getty autologins the `relay` user (appliance posture per the
preseed decision, OS-009). There is no default password anywhere in the
image. Set one with `passwd` if you want one.

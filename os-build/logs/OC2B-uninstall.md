# OC2B-017 — Uninstall story (one command, idempotent)

Inverse of install.sh steps 3–6. Data dir kept by default.

`sh agent-layer/uninstall.sh [--purge]` (script to be written; commands,
each guarded so re-run is a no-op):

```sh
systemctl --user disable --now oc2-queue.service oc2-trio.service oc2-patrol.service oc2-patrol.timer 2>/dev/null || true
rm -f "$HOME/.config/systemd/user/oc2-queue.service" "$HOME/.config/systemd/user/oc2-patrol.service" "$HOME/.config/systemd/user/oc2-patrol.timer" "$HOME/.config/systemd/user/oc2-trio.service"
systemctl --user daemon-reload 2>/dev/null || true
for rc in "$HOME/.profile" "$HOME/.zprofile"; do
  [ -f "$rc" ] && sed -i '/oc2-agent SPARK_API_KEY import/,/import-environment SPARK_API_KEY/d' "$rc"
done
rm -f "$HOME/.config/oc2-agent/env"
[ "${1:-}" = "--purge" ] && rm -rf "$TRIO_CREW_DATA_DIR" "$TRIO_LOCAL_DB" || echo "data kept (pass --purge to delete)"
```

Verify: `systemctl --user status oc2-queue` → not-found;
`grep oc2-agent ~/.profile ~/.zprofile` → empty.

# Service coverage — source on disk vs the boot manifest

Generated 2026-11-02 from directories under `services/` containing `.goose`
source, cross-checked against the 22 rows in `BOOT_MANIFEST.md`.

- service directories with Goose source: **38**
- boot manifest rows: **22**
- directories with an `entry.goose` (bootable shape): **5**
- bootable-shaped directories not in the manifest: **0**

Alias applied: `services/logd/` is the manifest's `log` (the drift is already
recorded in `os-build/layer1/CALLMATRIX_DRIFT.md`). `services/example/` is the
template and is excluded by name, not by accident.

## Bootable-shaped services NOT in the boot manifest

None. Every `entry.goose` outside the template has a manifest row.

## Libraries and tools not in the manifest (expected)

No `entry.goose`: these are imported by services or are host tools, so a boot
row would be wrong. Listed so the count is not mysterious.

- `board` — board.goose
- `clipboard` — clipboard.goose
- `dashboard` — dashboard.goose
- `dock` — dock.goose
- `echo` — echo.goose
- `fs` — fs.goose,fsck.goose,paths.goose
- `heartbeat` — heartbeat.goose
- `hello` — hello.goose
- `mcp-host` — host.goose
- `notify` — notify.goose
- `settings` — settings.goose
- `shell` — shell.goose
- `tests` — t100_common.goose,t101_netaddr.goose,t102_keycompose.goose,t103_limits_rest.goose,t104_agenthost_r11.goose,t105_audit_r11.goose,t106_board_r11.goose,t107_bootlog_r11.goose,t109_callmatrix_r11.goose,t110_console_r11.goose,t111_dashboard_r11.goose,t112_devices_r11.goose,t114_dhcp_r11.goose,t116_dns_r11.goose,t117_dock_r11.goose,t119_fs_r11.goose,t121_input_r11.goose,t122_logd_r11.goose,t123_logfmt_r11.goose,t125_net_r11.goose,t126_netcfg_r11.goose,t127_notify_r11.goose,t129_session_r11.goose,t130_settings_r11.goose,t131_shell_r11.goose,t134_storage_r11.goose,t135_supervisor_r11.goose,t136_time_r11.goose,t137_timesync_r11.goose,t138_updater_r11.goose,t139_updater_client_r11.goose,t140_r13_failpaths_b.goose,t141_clipboard.goose,t45_fmt.goose,t46_ring.goose,t47_cfg.goose,t48_boot.goose,t49_bootlog.goose,t50_logd.goose,t51_time.goose,t52_supervisor.goose,t53_watchdog.goose,t54_storage.goose,t55_hash.goose,t56_input_display.goose,t57_dhcp_dns.goose,t58_updater.goose,t59_agenthost.goose,t60_audit.goose,t61_bootorder.goose,t62_bytes.goose,t63_str.goose,t64_hex.goose,t65_fs.goose,t66_shell.goose,t67_net.goose,t68_proto.goose,t69_callmatrix.goose,t70_status.goose,t71_rotate.goose,t72_hostile.goose,t73_shell_hard.goose,t74_failure.goose,t75_supervisor_load.goose,t76_demo_session.goose,t77_gaps.goose,t78_lib_limits.goose,t79_limit_drivers.goose,t80_limit_drivers2.goose,t81_logd_deep.goose,t82_fs_deep.goose,t83_sup_deep.goose,t84_session_deep.goose,t85_net_deep.goose,t86_settings.goose,t87_wallpaper.goose,t88_dock.goose,t89_dashboard.goose,t90_updater_client.goose,t91_board.goose,t92_sup_load.goose,t93_face_walkthrough.goose,t94_face_failures.goose,t95_notify.goose,t96_logfmt.goose,t97_agent_surface.goose,t98_delta.goose,t99_calendar.goose
- `updater_client` — updater_client.goose
- `wallpaper` — wallpaper.goose

## Method and limits

Manifest rows are parsed by numeric first column. This is a name-level check:
it does not prove a service starts, that its dependencies are right, or that
its entry symbol exists. Those are the manifest checker's job (BOOT_ORDER vs
manifest) and the kernel's (entry call) respectively.

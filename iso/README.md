# The ISO lane

| Directory | What it holds | Label |
|---|---|---|
| `plymouth/` | splash theme: descriptor, script, ring asset | CODE-INSPECTED |
| `calamares/` | preseeded installer: branding, module order, presets | CODE-INSPECTED |
| `apps/` | five launchers, five dock items, Chromium policy, start page | CODE-INSPECTED |
| `apps/agent-status/` | the agent-layer status reader | CODE-INSPECTED |
| `contracts/` | the frozen `tokens.json`, pinned by sha256 | VERIFIED (sha matches) |
| `tools/` | checker, token generator, installer, boot kit, verdict | see below |

Nothing in this tree has been booted on the 8GB machine, and that machine
never boots. The boot procedure for the machine that does is
`os-build/BOOT_ON_32GB_MAC.md`.

## The tools

| Tool | What it does |
|---|---|
| `tools/check_iso_config.py` | 66 static checks over every file here; exits 1 on any failure |
| `tools/verify_lane.sh` | the lane gate: the checker plus every `tests/test_iso_*.py` |
| `tools/tokens_to_css.mjs` | generates the CSS from the frozen contract; `--check` proves it is current |
| `tools/apply.sh` | installs the whole lane into a base root; `--dry-run`, idempotent |
| `tools/boot_kit.sh` | checks prerequisites, builds userspace + kernel + image, prints the QEMU line |
| `tools/boot_log_verdict.py` | turns a serial log into PASS/FAIL per boot marker |

Run the gate first, always:

```
iso/tools/verify_lane.sh
```

It ends in `LANE GREEN` or `LANE RED` and exits non-zero on red.

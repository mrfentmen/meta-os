# The check layer — what each script proves, and what it does not

Every claim in `os-build/` should be checkable by one of these. They are all runnable from the
repo root, they all exit non-zero on failure, and none of them needs a service running.

**Read the "does not prove" column.** A green check is a statement about a file, a build or a
document — never about a machine.

| script | proves | does not prove |
|---|---|---|
| `build_kernel.sh` | the kernel compiles, links behind bootloader 0.9.35, boots, and the alive line is in the captured log | anything about hardware; K2-K6 behaviour |
| `prove_k2_k3.sh` | the VGA console drew text, the PIT advanced, a keystroke reached IRQ1 and ran a shell command | that the keyboard capture is reliable run-to-run (it is not; see `kernel/BUILD_LOG.md`) |
| `check_all.sh` | one exit code over: kernel check, kernel image, os-boot, userspace bins, Goose corpus, the document checkers, and the checkers' own negative tests | real hardware, network, persistence, the node suite's known-red tests |
| `test_checkers.sh` | each checker fails when its input is deliberately drifted (six mutations) | that the checkers cover every possible drift |
| `clean_clone_check.sh` | a fresh clone of `HEAD` builds userspace and the kernel and boots | network cloning, a different toolchain, the node/Goose suites |
| `abi_check.py` | the ABI spec, `user.rs` dispatch and `lib.rs` wrappers agree on six calls, the refusal arm, the write cap and the reserved range | that the kernel behaves that way at runtime — the boot log does that |
| `boot_manifest_check.py` | the boot order, its dependency closure, effective fatality, the manifest and the generated JSON agree | that any service starts, or that a loss produces the documented symptom |
| `failure_table_check.py` | every boot service has a failure row with a citation, and cited files exist | that the symptoms are right — only a boot can show that |
| `claim_check.py` | every proven/PROVEN table row or bullet cites an artifact that exists | that the artifact says what the row claims |
| `facts_check.py` | every cited number appears in the log that row cites | that the number means what the sentence says |
| `link_check.py` | relative links in the status documents resolve | that the linked page is current |
| `root_manifest_check.py` | every path `ROOT_MANIFEST.md` names exists (globs expanded) | that the OS/program split is the right one |
| `gen_boot_manifest_json.py --check` | `boot-manifest.json` is current with its two source documents | that the image lane consumes it correctly |
| `boot_log_parse.py` | a serial log becomes structured records; unknown lines are counted, not dropped | anything beyond the line shapes it knows |
| `boot_log_diff.py` | two boots differ only in numbers/lists (0 regressions) or names what regressed | that the shared lines are correct |
| `run_native.sh` / `check_services.sh` | the Goose corpus compiles to C and runs as host processes | that any of it runs on the kernel |

## The rules these follow

1. **Existence is not agreement.** `claim_check` proves a citation resolves; `facts_check`
   proves a number is in the cited file; neither proves the sentence is true.
2. **A checker nobody has seen fail is unverified.** `test_checkers.sh` mutates temp copies and
   requires a non-zero exit.
3. **Generated files get a freshness gate.** `boot-manifest.json` is regenerated and compared,
   not trusted.
4. **Skips are stated.** Where a script cannot run (no toolchain, no QEMU), it says SKIP and
   `check_all` reports it rather than passing quietly.

# Release — what this tree is, and what was actually run on it

Written 2026-11-04 at the merge of the two branch lines. Every number below was
printed by a command in this document; none is a estimate.

## What was released

| | |
|---|---|
| Branch | `release` (also fast-forwarded to `main` locally — **not pushed**) |
| Ancestry | `agent-r3` (lane merges, in-app chat, debrand, deletions) merged with `agent-r5` (this round's gates, receipts, kernel/PCI/framebuffer evidence) |
| Merge commit | `b9ed7b21` — its message lists every conflict and how it was decided |
| Image | `os-build/iso/output/metaos-demo-image-2026-11-03-arm64.iso`, 2.3 GB, **built 2026-11-03, before this merge** |
| Image checksum | `d376f3d4046761f0bfd66c05e6b54e2ee11af19cb4cd036c136f53ba2bb5bca7` (SHA-256) |

The ISO on disk does **not** contain this merge. Rebuilding it needs Docker with
`--privileged` (the `--rebuild` path) and a base ISO; the full build is
documented as blocked on this Mac in `os-build/iso/BOOT_POLICY.md`. Saying the
2.3 GB file is this release would be a false claim, so it is labelled here.

## Checks run on the released commit, and their results

| Check | Command | Result |
|---|---|---|
| Repo gate | `sh os-build/tools/verify_tree.sh` | **14 rows, 14 PASS**, exit 0 (71 s) |
| Round-11 suites | `npm run test:r11` | **38 tests, 38 pass, 0 fail** |
| Agent + chaos packs | `npm run test:agents` | **254 tests, 254 pass, 0 fail** |
| Lab assets | `python3 labs/check_assets.py` | `OK: 6 pages, all local assets resolve, no CDN tag assets.` |
| Image payload assembly | `sh os-build/iso/build_iso.sh --tree-only /tmp/release-tree` | exit 0, tree written, "No ISO mastered" as designed |
| Shell syntax | `sh -n` on `brand.sh`, `build_iso.sh`, `build-arm64-inner.sh`, `metaos-install.sh`, `run-stack.sh`, `provision.sh`, `meta-desktop.sh` | all OK |
| JS syntax | `node --check board/board.mjs`, `node --check server/agent-chat.mjs` | both OK |
| Python compile | `python3 -m py_compile os-build/iso/payload-theme/apps/metaos-imperium.py` | OK |
| Wallpaper selection | fallback logic exercised against a fake site root (no display) | resolved to `trio/vigiles.html` when `imperium/` is absent |

The 14 gate rows are: `allowlist`, `debrand-strings`, `desktop-entries-check`,
`profile-check`, `tokens-check`, `no-stock-art`, `wallpaper-reachability`,
`brand-identity`, `tree-refs`, `no-ubuntu`, `home-refs`, `os-release-identity`,
`worlds-check`, `lab-assets`.

## What the gate found on the merged tree, and what was done about it

Three rows failed at the merge. Each was fixed at its cause:

1. `brand-identity` — `os-build/metaos-brand/brand.sh` wrote `ID_LIKE=ubuntu debian`
   and autologined the base account. Both now say the contract values
   (`ID_LIKE=debian`, `autologin-user=meta`). The same autologin string and the
   installer's default user were fixed in `build-arm64-inner.sh`,
   `metaos-install.sh`, and a diagnostic in `build_iso.sh`.
2. `debrand-strings` — 171 hits, all in documents *about* the removal, the
   removal scripts' own search vocabulary, and three carrier facts (the base ISO
   filename, a package name, the docker image). 52 allowlist rows with explicit
   reasons were added; the shipped values were fixed rather than excused.
3. `desktop-entries-check` — `atril.desktop`/`evince.desktop` carried lane notes
   containing `Hana` and `KEEP`, which that checker bans in files a menu reads.
   The note moved to `agent-layer/desktop-entries/README.md`.

## What is proven, and what is not

Proven, with a file for each claim: the kernel boots in QEMU and its logs are
committed (`os-build/logs/`, indexed in `os-build/layer1/BOOTLOG_INDEX.md`); the
agent platform runs and leaves receipts (`os-build/aegis/`, `os-build/nervus/`,
`os-build/handsfree/`); the desk chat exists on every app and posts to a real
endpoint; the gate and the suites above are green on this commit.

Not proven, stated plainly:

- **The capability policy is not in this tree.** It is on a branch; the spec
  amendment (`os-build/KERNEL_SPEC.md:143`) says so, and the README says so.
- **No ISO was built from this commit.** The 2.3 GB image predates the merge.
- **No QEMU boot was run for this round's tree.** Boot evidence is from earlier
  commits and is labelled as such by its filenames.
- **The desktop is a remaster of a base distribution**, not our kernel running
  our apps. The README's section 7 lists this and the other limits.

## Putting the image on GitHub Releases

GitHub refuses a single release asset over 2 GB and this image is 2.3 GB, so it
goes up as two parts. The split and the hash are already done — the files sit in
`os-build/iso/output/` beside the image and are gitignored.

```sh
# 1. code and the tag (needs your credentials; nothing here is pushed for you)
git push origin release:main
git push origin v1.0.0

# 2. a release to hang the parts on, in one step
gh release create v1.0.0 --title "Meta OS 1.0" \
  --notes-file os-build/RELEASE.md \
  os-build/iso/output/metaos-demo-image-2026-11-03-arm64.iso.part-* \
  os-build/iso/output/metaos-demo-image-2026-11-03-arm64.iso.sha256

# 3. what a downloader runs — put this in the release notes too
cat metaos-demo-image-2026-11-03-arm64.iso.part-* > metaos-demo-image-2026-11-03-arm64.iso
shasum -a 256 -c metaos-demo-image-2026-11-03-arm64.iso.sha256   # sha256sum on Linux
```

The parts are `part-aa` (1.2 GB) and `part-ab` (1.1 GB), both under GitHub's
per-asset ceiling. `gh` is **not installed** on the build Mac — `brew install gh`
then `gh auth login` first, or create the release in the web UI and drag the
files in. A 1.2 GB upload takes a while on a home connection; if one part fails,
re-upload just that part with `gh release upload v1.0.0 <file> --clobber`.

A single-file mirror is worth having for judges who should not have to run `cat`:
Hugging Face accepts the whole 2.3 GB on a free public repo and gives one direct
link. Google Drive works as a *backup* only — it shows a virus-scan interstitial
on files this size and throttles a file after a handful of downloads.

## Reproduce this release from scratch

```sh
git clone <repo> && cd meta-os
git checkout release
sh os-build/tools/verify_tree.sh          # expect: 14 rows, DEAD: (none)
npm run test:r11                          # expect: 38 pass
npm run test:agents                       # expect: 254 pass
python3 labs/check_assets.py              # expect: OK
sh os-build/iso/build_iso.sh --tree-only  # expect: exit 0, no ISO mastered
```

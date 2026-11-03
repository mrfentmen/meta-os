# OC3B-212 — handoff: entries to the ISO/desktop lanes (copy-only, with sha)

Source of truth: `os-build/logs/oc3b-desktop/` on branch
`opencode/agent3-oc3`. Receiver copies the DIRECTORY, records the
sha256 of each file, never edits in place. OC2's six entries are NOT
in this handoff — OC1 copies those from `agent-layer/desktop-entries/`
@landwalls (shas in OC3-STATUS.md T2-staged list).

Receiver checklist (ISO lane / OC1):
1. `git show opencode/agent3-oc3:os-build/logs/oc3b-desktop/<f> | sha256sum`
   and compare with the shas OC1 posts at copy time (OC1 records).
2. Install to `/usr/share/applications/` (system entries, not `~/.local`).
3. Re-run `desktop-file-validate` on a Linux host; the Mac-side Python
   audit is the structural gate, not the final word.
4. Report back per-file present/missing at boot: parole, pavucontrol,
   galculator, xfce4-taskmanager, xfce4-settings-manager,
   xfce4-display-settings, xfce4-appearance-settings,
   xfce4-screenshooter. Missing binary = entry self-hides via TryExec;
   file it as a package-list gap with the ISO lane, not as a launcher
   defect.

Proposed install manifest (8 files, all TryExec-guarded, all
`OnlyShowIn=XFCE`, all `Terminal=false`):
parole, pavucontrol, galculator, xfce4-taskmanager,
xfce4-settings-manager, xfce4-display-settings,
xfce4-appearance-settings, xfce4-screenshooter — each `<name>.desktop`
as committed in `oc3b-desktop/`.

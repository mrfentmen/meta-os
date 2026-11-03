# OC3B-037/038 — file manager launcher entry

No new entry authored: Thunar already has two committed launchers
(OC2's with TryExec, ISO lane's meta-files). A third would be
clutter, not coverage.

OC3B-038 (opens to home, not /): CODE-INSPECTED from the entry text.
OC2's Exec is `thunar %U` with no Path= key and no directory
argument. Per the desktop-entry spec + Thunar behavior, bare launch
opens the default folder, which is $HOME unless the user changed
Thunar's default — not /. Observed-confirmation is OC1's one-line
boot check, named here, not claimed.

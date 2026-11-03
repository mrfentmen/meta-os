# OC3B-294 — DEL-ONLY list for this lane (Pax: merge these, nothing else)

From opencode/agent3-oc3, merge ONLY:
- os-build/logs/OC3B-*.md/.txt/.html (106 proof files, §1–§12)
- os-build/logs/oc3b-desktop/ (11 .desktop + tour.html)
- os-build/logs/oc3b-help/ (help.html + about.html)
- OC3-STATUS.md (§verdicts + §12 closeout)

DEL-ONLY = this lane stages content under os-build/logs/ only; the
ISO lane COPIES entries/pages to system paths and records shas.
Do NOT merge: nothing outside os-build/logs/ + OC3-STATUS.md was
touched (verified: git status shows only those paths across all
§commits). Shared files (mimeapps, launchers of other lanes,
calamares tree) were referenced, never edited.

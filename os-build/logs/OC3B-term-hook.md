# OC3B-054/055/056/070 — welcome hook, shell, prompt (CODE-INSPECTED)

Hook source: `metaos-theme/terminal/metaos-welcome.sh` on main
(identical twin under `os-build/iso/payload-theme/terminal/`).
- OC3B-054 fires once: `METAOS_WELCOMED` guard exports on first
  interactive shell, skips after. Verified by reading, not running.
- OC3B-055 never blocks a shell: three independent guards — PS1 check
  (interactive only), one-shot flag, trailing `|| true` so a node
  failure degrades to silence. Worst case is a skipped splash.
- OC3B-056 shell+prompt: bash (hook is bashrc.d), prompt is the
  user's existing PS1 — this lane changes nothing about it.
- OC3B-070 welcome app from terminal: `metaos-welcome.py` runs
  standalone (`python3` + GTK3, degrades section-by-section per its
  docstring); launch command is the .py path, no wrapper needed.

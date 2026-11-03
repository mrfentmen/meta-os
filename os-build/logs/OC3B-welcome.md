# OC3B-130/131 welcome + test_welcome evidence

Menu entry: metaos-welcome.desktop on main (Exec + TryExec point at
the .py). Once-only: ~/.config/metaos/welcome-shown flag file
(CODE-INSPECTED, graceful degradation per its docstring).
test_welcome.py: 30/30 PASS on this Mac when the shipped trio
(.py + test + .desktop) is co-located, as it is on main.
An earlier 4-error run in /tmp was my harness missing the .desktop
file, not a product defect — recorded so nobody re-discovers it as
a scare. Observed-shows-once remains OC1's login test.

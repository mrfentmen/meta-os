# Commercial-solver comparison plan (NC-031) — plan only

Goal: an independent number for the rung-1 champion to set beside the
finite-difference solver's 733.8 W. No accounts created, nothing
installed, no geometry uploaded anywhere as part of this task.

Tool class: any steady-state conduction+convection FEA/CFD package with
a free tier or trial (e.g. SimScale community, Autodesk CFD trial, or an
open-source Elmer/OpenFOAM run on a borrowed workstation). The boss
picks the tool; this plan only defines the comparison so any of them
fits.

Geometry file it needs: `champion-fin.txt` in this directory (NC-032) —
plain dimensions in mm plus the assumed boundary conditions block at
the top. Any CAD or solver can consume it by hand in minutes.

What output settles it: total dissipated watts at base = ambient + 50 K
with 2 m/s channel flow, same as the NC-029 sheet, plus the fin-tip
temperature. Agreement with the sheet inside the boss's rung-4
percentage corroborates the solver; disagreement sends the case to the
bench (protocol) rather than to a second simulation.

Explicitly out of scope here: accounts, installs, uploads, and any
cloud run. Plan only.

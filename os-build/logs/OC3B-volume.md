# OC3B-120/121/122 — volume control (entry authored; behavior is boot)

Present as a committed launcher: pavucontrol (oc3b-desktop/,
TryExec-guarded). 121 mute-works and any level-write verification
need the live sound server, so the mute test is an OC1 boot check
with the hardware in hand. 122 handoff: the entry rides with the
standard copy-only handoff (see desktop handoff); no separate
volume lane exists or is needed.

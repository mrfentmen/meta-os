# OC3B-218/219 — menu search behaviour

Whiskermenu (Xfce default) searches Name/GenericName/Comment keywords.
Every entry in this lane + OC2 + ISO lane carries all three fields,
so search finds every app by function name ("calculator",
"screenshot", "volume") as well as program name. Verified statically
from the committed files. Live search-ranking is an OC1 boot check,
deferred, not claimed.

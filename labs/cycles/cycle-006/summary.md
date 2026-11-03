# Cycle 006 — summary

The from-scratch implementation of the Delaney (2004) published
solubility equation, run with RDKit descriptors over the frozen
1,128-compound archived set, gave RMSE 1.0994 against measured
solubilities, inside the pre-registered band around the repo-recorded
1.099. The live literature pass (2 openalex calls through the
MCP-GATEWAY backend, both ok, $0.00) pinned the cited record to the
Delaney (2004) ESOL paper by explicit DOI/title/year match; the
citation stayed quarantined until that check passed. An independent
clean-directory re-run agreed bit-for-bit, and the figure is
byte-identical to cycle-001's. The result reproduces the repo
cross-check numbers at the stated method scope (Wildman-Crippen cLogP,
not the paper's Daylight CLOGP).

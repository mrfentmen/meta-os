# Cycle 001 — summary

The from-scratch implementation of the Delaney (2004) published
solubility equation, run with RDKit descriptors over the frozen
1,128-compound archived set, gave RMSE 1.0994 against measured
solubilities, inside the pre-registered band around the repo-recorded
1.099. An independent clean-directory re-run agreed bit-for-bit. The
result reproduces the repo cross-check numbers at the stated method
scope (Wildman-Crippen cLogP, not the paper's Daylight CLOGP).

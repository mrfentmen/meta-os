# Cycle 005 — summary

The held-out 100-compound Delaney slice (rows 31-130) scored with the
paper equation under RDKit descriptors gave RMSE 1.0752, outside the
pre-registered paper-anchored band around the paper's training se of
0.97, so the cycle DIFFERs. The miss reproduces bit-for-bit in a clean
directory: the paper's training error does not transfer to this set
under this cLogP method, while ranking is preserved (slice R2 0.7432
vs paper training R2 0.72). Details in failure.md.

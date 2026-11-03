# OC3B-011 — no first-run wizard

Mitigations, layered: --no-first-run on the launcher Exec line;
--app= mode skips the wizard surface entirely; first-boot seed
(ISO lane) is asked to pre-accept MetricsReportingEnabled=false.
Residual risk honestly noted: a Chromium version bump can re-show a
consent screen; the OC1 boot screenshot of first launch is the
confirming artifact, owned by OC1, not claimed here.

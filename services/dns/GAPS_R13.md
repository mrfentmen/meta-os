# Gap records — R13-013 dns

## R13-013-G1 — unused `netcfg` import

- **Claim:** `dns` depends on `netcfg`.
- **Reality:** `import netcfg.netcfg;` is at `services/dns/dns.goose:39`; the identifier
  `netcfg` appears nowhere else in the file, including no qualified call.
- **Evidence:** `grep -n 'netcfg' services/dns/dns.goose` returns only line 39.
- **Impact:** the dependency gate and the call matrix can be made to require a module this
  resolver never calls. Removing it should be a one-line change, but the audit does not make
  source changes.
- **Owner:** dns build manifest; call-matrix dependency list.

## R13-013-G2 — no dependency list in the README

- **Claim:** the resolver's dependencies are documented.
- **Reality:** the README has sections for scope, pointer guards, refusals and a bug, but no
  dependency or import list. The only dependency statement is the prose “pure: bytes in, bytes
  out”, which is true at runtime and silent at build time.
- **Evidence:** `services/dns/README.md` (no `import`, `depend` or `netcfg` section).
- **Impact:** a reader cannot tell whether `netcfg` is required, optional or stale. The unused
  import survives because nothing documents the intended list.
- **Owner:** dns README.

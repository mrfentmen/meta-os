# Contract note — R13-013, dns dependency list

Status: **AUDITED — 2 gaps filed**.
Facet: the complete dependency list of the resolver and whether each dependency is declared and used.

## Evidence

Commands:

```sh
nl -ba services/dns/dns.goose | sed -n '30,50p'
grep -nE 'netcfg|import ' services/dns/dns.goose
```

Relevant output:

```text
38  import common.err.err;
39  import netcfg.netcfg;
...
42  let DNS_NAME_MAX: i64 = 255;
43  let DNS_LABEL_MAX: i64 = 63;
44  let DNS_QUERY_MAX: i64 = 512;
45  let DNS_MAX_JUMPS: i64 = 32;
```

`netcfg` occurs at line 39 only; there is no `netcfg.` use anywhere in the file. The README
describes the resolver as “pure: bytes in, bytes out” and does not list imports or build
dependencies at all.

## Corrected contract

Source-level imports are exactly two: `common.err.err` for error codes and `netcfg.netcfg`.
Only `common.err.err` is used. The resolver has no runtime dependency on a clock, socket, cache,
allocator or service handle. `DNS_PORT`, `DNS_NAME_MAX`, `DNS_LABEL_MAX`, `DNS_QUERY_MAX` and
`DNS_MAX_JUMPS` are compile-time constants. Timeouts and retries are owned by the caller
(`dns_query_init` takes `timeout_ms`; `dns_query_expired` takes `now_ms`).

The build dependency list is therefore: `common/err` and (nominally) `netcfg`; the second is
unused and should not be in the list.

## Mismatches

- **R13-013-G1** — `netcfg` is imported but never referenced.
- **R13-013-G2** — the README has no dependency list, so this unused import is the only record
  of the dependency and it is wrong. See `services/dns/GAPS_R13.md`.

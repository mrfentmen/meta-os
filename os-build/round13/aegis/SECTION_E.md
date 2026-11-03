# Section E — Aegis live fire: OSV sweeps (R13-101..125)

Run: `python3 os-build/layer1/manifest_sweep.py`. Tool, machine-readable record and stdout are
committed: `os-build/layer1/manifest_sweep.py`, `os-build/round13/aegis/OSV_SWEEP.json`,
`os-build/round13/aegis/osv_sweep.txt`.

**25 / 25 addressed — 10 real manifest records, 15 records where the named artifact is not in
this tree, 0 findings, 1 positive control passing.**

## Route, stated

```
https://api.osv.dev/v1/query, direct
(osv-mcp is not installed on this host; standing written exception, route stated in the record)
```

The gateway config (`mcp-gateway/backends.json`) points osv-mcp at
`/home/hatch/workspace/mcp-servers/osv-mcp/dist/index.js`, which does not exist on this
machine, and `AEGIS_OSV_MCP` is unset. The normal Aegis rule is "no transport, no claim —
the run is BLOCKED". The Round 13 list allows the direct route under the standing written
exception, so the direct route was used and every record repeats it. A reader who does not
accept that exception should read all 25 records as blocked, because the source line is the
only thing that makes them evidence.

## The positive control, which is the part that matters

```
control crates.io/time@0.1.44 -> 2 ids ['GHSA-wcg3-cvx6-7396', 'RUSTSEC-2020-0071']
```

A sweep that reports zero findings and cannot find a known advisory has reported nothing.
`sweep.mjs` records the same failure from the first build: a parser that failed silently
reported "zero findings" for 108 references. This run proves the query path sees hits before
it reports that it saw none.

## What was actually swept

| manifest | exists | refs queried | findings |
|---|---|---:|---:|
| `Cargo.lock` (workspace, 126 `[[package]]` blocks) | yes | 107 | 0 |
| `kernel/Cargo.lock` | yes | 1 | 0 |
| `os-build/userspace/user/Cargo.lock` | yes | 0 | 0 |
| `package.json` (root) | yes | 0 declared dependencies | 0 |

The workspace lockfile has 126 package blocks, of which 107 are registry crates and the rest
are workspace members with no `source` field. Asking OSV about a workspace member would be
asking about code that has never been published, so those are excluded by the same rule
`sweep.mjs` uses.

`package.json` declares **zero** dependencies in all three dependency sections, and there is
no lockfile for it. That is why R13-101 queries nothing: the file is real, the dependency set
is empty.

## Per-task records

`exists` is about the artifact, `refs` about how many exact versions were queried.

| task | named artifact | exists | refs | findings | record |
|---|---|---:|---:|---:|---|
| R13-101 | `package.json` (root) | yes | 0 | 0 | real manifest, zero declared dependencies |
| R13-102 | `package-lock.json` | **no** | 0 | — | no npm lockfile anywhere in the tree (`find . -name package-lock.json` empty) |
| R13-103 | `Cargo.toml` (workspace) | yes | 0 | 0 | declares ranges and member paths only; resolved versions swept under R13-104 |
| R13-104 | `Cargo.lock` | yes | **107** | **0** | the real sweep |
| R13-105 | `kernel/Cargo.toml` | yes | 0 | 0 | resolved by `kernel/Cargo.lock`, swept (1 ref) |
| R13-106 | `crates/intel` | yes | 0 | 0 | crate exists; resolved versions live in `Cargo.lock` |
| R13-107 | `crates/queue-core` | yes | 0 | 0 | same |
| R13-108 | `crates/os-supervisor` | yes | 0 | 0 | same |
| R13-109 | `services/MANIFEST.md` | **no** | 0 | — | Goose services have no dependency manifest; `services/MANIFEST.md` does not exist |
| R13-110 | `server/queue` python requirements | **no** | 0 | — | no `requirements.txt` / `pyproject.toml` anywhere in the tree |
| R13-111 | science-lab requirements | **no** | 0 | — | no lab requirements file |
| R13-112 | goose toolchain manifest | **no** | 0 | — | the compiler is a host binary; no manifest in-tree |
| R13-113 | `face/package.json` | **no** | 0 | — | `face/` is static HTML/JS with no package manifest |
| R13-114 | `board/package.json` | **no** | 0 | — | no manifest |
| R13-115 | `relay/package.json` | **no** | 0 | — | no manifest |
| R13-116 | `agents/package.json` | **no** | 0 | — | `agents/` is ESM `.mjs` run by node directly, no manifest |
| R13-117 | tests manifests | **no** | 0 | — | tests are `node --test` files with no manifest |
| R13-118 | os/worlds pack manifests | **no** | 0 | — | no world-pack manifests |
| R13-119 | docs tooling manifest | **no** | 0 | — | none |
| R13-120 | image build manifest | **no** | 0 | — | none |
| R13-121 | legacy connector manifests | **no** | 0 | — | none |
| R13-122 | custom-skills manifests | **no** | 0 | — | none |
| R13-123 | `mcp-gateway/package.json` | **no** | 0 | — | gateway is a JSON backend table plus python client, no manifest |
| R13-124 | `crates/assess-server` | yes | 0 | 0 | crate exists; resolved versions in `Cargo.lock` |
| R13-125 | every remaining `crates/*/Cargo.toml` | yes | 0 | 0 | 23 manifests enumerated; resolved versions swept through `Cargo.lock` |

Severity buckets were never exercised because there were no hits: `{}` for every record. That
is stated rather than filled with zeros for each band, because a zero in a band implies the
band was consulted and a `{}` says it was not.

## What this section cannot claim

- That the tree is free of vulnerable dependencies. 107 references were checked against OSV
  and OSV answered "no records" for each; that is a statement about OSV's database at the time
  of the run, not a proof of safety.
- That the 15 missing manifests are harmless. A missing manifest is a missing input: there is
  nothing to sweep, and "nothing to sweep" is not "clean".
- That the pins are current. `Cargo.lock` was not compared against latest releases; OSV only
  answers "is this exact version known-vulnerable".

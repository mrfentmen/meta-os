# verify/ - Pax's verification lane for the Meta Trio

Additive tooling only. This folder changes no contract, no product code,
and no other lane's files. It exists so "does it all work?" is one
command with a printed answer instead of a claim.

## Run everything

```
node verify/check.mjs
```

Runs, in order:

1. The web suite (`npm test` at the repo root).
2. Milo's Sanitas eval harness tests (`eval/sanitas/harness.test.mjs`).
3. The /api/assess conformance suite in fixture mode (below).
4. A secret scan of the repo tree (key-shaped strings; `check.mjs`
   itself is excluded because it holds the patterns).
5. A contract-coherence check: the product keys in `js/products.js`
   and the native `ProductID` enum must both be exactly
   vigiles / ignis / sanitas.
6. An informational probe of `http://localhost:8080/api/assess`.
   Nothing answering is the expected state until the server lane lands;
   it is reported, never counted as a failure.

Exit code is 1 if any of checks 1-5 fail.

## Conformance suite

```
node --test verify/conformance/conformance.test.mjs
```

Default (fixture) mode spawns `conformance/fixture-server.mjs`, a
deterministic stand-in that is **not a model** and says so in every
response (`processing.model` names the fixture, observations are empty,
`latency_ms` is null). The suite drives it with the shipped client
(`js/client.js`) and validator (`js/schema.js`), so what passes here is
the real client code agreeing with the real contract.

Live mode runs the positive checks against a real server:

```
ASSESS_BASE_URL=http://localhost:8080 node --test verify/conformance/conformance.test.mjs
```

That is the suite the /api/assess server must pass when it lands. The
suite itself fires no model calls; per Del's ruling, Spark stays off
until he starts the test phase.

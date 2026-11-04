# Meta Surveyor — eval upgrade

Branch-only, no merge, no OS touched. Rowan's lane for del's 2026-11-04
all-apps eval order: Surveyor takes the eval upgrade for its own lane.

## What this tests

The agentic wiring in `docs/META_SURVEYOR_SPEC.md` (branch
`rowan/surveyor-spec`), not the demo mockups on `rowan/surveyor-demo`:

- Two-agent confirmation before a reading publishes (S reading + an
  independent V check from a different device, same place/window,
  within tolerance, sane sensor).
- Disagreement stays unpublished and is flagged for human confirm.
- Second-hand data never publishes and never counts as confirmation.
- Sensor-less devices never originate a sensor reading; a dongle
  promotes an ordinary computer to role S.
- Clusters, not single readings, trigger action: dispatch only on a
  confirmed cluster (>= 3 confirmed readings, same field + place).
- Noise readings carry a decibel level only — audio is rejected.
- No person data — a reading naming a person is rejected.

## Run it

```sh
python3 eval/surveyor/surveyor_eval.py        # 11 scenarios, exit 0 on all-pass
python3 -m unittest discover -s eval/surveyor -v
```

Python 3 stdlib only. No dependencies, no network, no live sensors.

## Honest caps

- Every reading in the harness is a FIXTURE. A full pass proves the
  wiring rules hold on known inputs. It proves nothing about any real
  street, sensor, cure, or compound, and claims none.
- NO live model calls from this harness. Model cost is $0. Any future
  model-backed verifier runs Mac-side under del's under-a-dollar cap,
  never from this VM, and never as a substitute for the two-agent rule.
- Science Lab's agentic question stays Hana's lane; this eval covers
  Surveyor only, and claims nothing about any other application.

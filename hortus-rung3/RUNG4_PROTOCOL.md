# Hortus rung 4 — bench test protocol (NC-025..NC-028, NC-030, NC-034)

Status: PREPARATION ONLY. Rung 4 (a physical cross-check) stays the
boss's call. Nothing here buys, orders, or fabricates anything.

## Unit under test (NC-025)

One rung-1 champion heatsink, nominal geometry: 40 straight fins,
60.0 mm fin height, 0.745 mm fin thickness, 1.494 mm base thickness,
100 mm x 100 mm footprint (assumed, same as rung 3).

Heat source: flat resistive heater plate matched to the 100x100 mm base,
driven at constant power, thermally greased to the base. The base bottom
temperature is the control point: drive power is trimmed until the base
thermocouple reads 50 K above ambient, then held for soak.

Measurement points (all logged with timestamps):
- T_base: thermocouple embedded at base center bottom (control point).
- T_tip: thermocouple or IR spot on one central fin tip.
- T_amb: shaded ambient sensor 1 m away, same height.
- Fan: anemometer reading in the channel inlet (target 2.0 m/s).
- Power: heater watts (volts x amps, logged).

Ambient logging: T_amb every 30 s for the whole run; abort if drift
exceeds 2 K during soak.

Safety limits: heater surface never above 120 C; kill power if T_base
exceeds 90 C above ambient or any smell/smoke; aluminium only, no
coatings that outgas. Fire extinguisher in the room. Never leave
powered while unattended.

## Parts list (NC-026) — specs only, no prices, no links

- Heatsink under test (nominal dims above; mic the fin thickness).
- Resistive heater plate, 100x100 mm, >=150 W rating.
- Bench power supply with constant-power or manual trim + DMM for V and I.
- 3x K-type thermocouples + reader (base, tip, ambient), 0.5 K or better.
- Thermal grease, thin even coat.
- Small axial fan + duct focusing flow along the channels; anemometer.
- Insulation block under the heater (so heat goes up into the sink).
- Log sheet (NC-027) + clock.

## Measurement log template (NC-027)

CSV header (one row per 30 s sample; the single row below is marked
EXAMPLE and is not data):

```
timestamp_iso,phase,T_base_C,T_tip_C,T_amb_C,fan_m_s,heater_V,heater_A,heater_W,notes
2026-01-01T00:00:00+00:00,EXAMPLE,75.0,58.2,25.0,2.0,24.0,3.1,74.4,EXAMPLE ROW — NOT A MEASUREMENT
```

## Pass/fail rule (NC-028, stated in advance)

Compare the soaked heater watts at dT=50 K against the simulation
prediction sheet (NC-029) for the matching h. Agreement percentage:

    RUNG4_PASS_PCT = ____ %   (BLANK — the boss sets this, not us)

Rung 4 is earned if and only if |measured - predicted| / predicted is at
or under the boss's percentage, with all uncertainty sources (NC-030)
smaller than the gap or explicitly accounted for. Anything else is "not
earned", filed plainly.

## Uncertainty budget (NC-030, sizes from the rung-3 work)

| source | measured size | how known |
|---|---|---|
| grid error | 0.4% (halving dy halves it) | NC-002 verification |
| stair-stepped fin width | 0.6% (modelled 0.7407 vs 0.745) | reported per run |
| aluminium k spread 167–237 | 712.6 W to 814.0 W vs 734.2 W baseline (-3% / +11%) | solver re-run at k=167/237, h=55.9 (NC-029 log) |
| h (fan speed, correlation) | dominant; bracketed 30/55.9/100 in predictions | Elenbaas-class assumption, conservative |
| base temperature control | ±0.5 K sensor + trim wander | protocol trim rule |
| ambient drift | abort past 2 K | protocol abort rule |

## What would falsify rung 3 (NC-034)

A soaked measurement, inside the stated uncertainties, that differs
from the prediction sheet by more than the boss's percentage in either
direction — hotter (solver over-predicts cooling) or colder. Either sign
counts: the solver does not get to be wrong only in the flattering
direction. A second falsifier: tip-vs-base temperature split disagreeing
with the simulated profile shape (not just the total watts), which would
show the conduction model, not the convection number, is at fault.

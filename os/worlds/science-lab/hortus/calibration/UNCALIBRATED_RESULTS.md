# Uncalibrated scorer vs datasheet reality

The Hortus toy scorer (hortus/model.py, as shipped,
h multiplier = 1.0 - i.e. its nominal h = 10 W/m2K and
its own demo plate replaced per part by the part's plate)
against measured thermal resistances of real Wakefield
Engineering bonded-fin heatsinks (datasheet_parts.json).
This table was produced and committed BEFORE any
calibration was fitted. It is the raw evidence the
calibration has to answer to.

| part | profile | fin height | subset | predicted R (K/W) | measured R (K/W) | % error |
| --- | --- | --- | --- | --- | --- | --- |
| BE8711-H2 | 8711 | 2 in | calibration | 0.641 | 1.360 | -52.9 |
| BE8711-H4 | 8711 | 4 in | calibration | 0.388 | 0.830 | -53.3 |
| BE8731-H2 | 8731 | 2 in | calibration | 0.432 | 1.110 | -61.1 |
| BE8731-H4 | 8731 | 4 in | calibration | 0.260 | 0.685 | -62.0 |
| BE8546-H2 | 8546 | 2 in | calibration | 0.327 | 1.330 | -75.4 |
| BE8546-H4 | 8546 | 4 in | calibration | 0.196 | 0.823 | -76.2 |
| BE8119-H2 | 8119 | 2 in | calibration | 0.399 | 0.880 | -54.6 |
| BE8119-H4 | 8119 | 4 in | calibration | 0.242 | 0.539 | -55.1 |
| BE8712-H2 | 8712 | 2 in | calibration | 0.262 | 1.122 | -76.7 |
| BE8712-H4 | 8712 | 4 in | calibration | 0.157 | 0.692 | -77.3 |
| BE8737-H2 | 8737 | 2 in | validation | 0.359 | 0.937 | -61.7 |
| BE8737-H4 | 8737 | 4 in | validation | 0.217 | 0.580 | -62.7 |
| BE8556-H2 | 8556 | 2 in | validation | 0.269 | 0.751 | -64.2 |
| BE8556-H4 | 8556 | 4 in | validation | 0.162 | 0.438 | -62.9 |

Subset summaries (percent error of predicted R):

- calibration: n=10, mean -64.5%, mean |error| 64.5%, RMS 65.3%
- validation: n=4, mean -62.9%, mean |error| 62.9%, RMS 62.9%

Method: check_scorer.py in this directory; predicted R
= delta_t / model.heat_watts under each part's own
geometry, alloy 6063-T5 (k = 209 W/mK), natural
convection, unpenalised heat core. Negative error means
the model predicts a LOWER thermal resistance than the
real part achieves - i.e. the toy model overstates how
well the heatsink works.

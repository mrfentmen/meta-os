# Prior-art note (stage 2b) — RESEARCH AID

Artefact class: heatsink-fin-geometry
Brief: a mounting bracket to hold a 50mm square heatsink for a hot little board, no fan, needs to stay cool under 2 degrees per watt

## Key features
- artefact class heatsink-fin-geometry
- straight rectangular aluminium fins: H=39.06 mm, t=1.50 mm, N=15, base=4.00 mm on a 50 mm square footprint
- passive (fanless) operation stated
- target target_r_c_per_w = 2.0 (stated)

## Repo context
- os/worlds/officina/runtime/heatsink.py: fin-efficiency simulator; live bounds H[5.0, 80.0] mm, t[0.5, 3.0] mm, N[4, 30], base[2.0, 12.0] mm; gap floor 1.0 mm; volume budget 100000 mm^3; aluminium k=205 W/mK
- os/worlds/officina/runtime/design_loop.py: held-out acceptance gate: re-scores under held-out conditions plus tolerance perturbation; proven needs the workshop bar at design conditions AND held out
- os/worlds/officina/PACK.md: workshop honesty record: simulated scores only, never validated against a measured physical sink
- os/worlds/officina/pack.json: repo prior art (line 1): {"agents":[{"nick":"design-smith","role":"Samples design variants inside the declared ranges, posts them as jobs, and keeps the winners: the feasible designs wi
- os/worlds/officina/runtime/brief.py: repo prior art (line 42): grader is code: heatsink.simulate plus the held-out gate.

## Public-literature shelf (URL + kind + status)
### (1) fin efficiency, adiabatic tip [primary | alive (serves application/pdf)]
Title: Incropera Fins chapter (MEngr 503 course notes PDF)
URL: https://courses.washington.edu/mengr503/Fins_Incropera.pdf
Straight rectangular fins are scored in textbooks by eta = tanh(m*H)/(m*H) with m = sqrt(h*P/(k*A_c)), the adiabatic-tip form our simulator implements (depth cancels to m = sqrt(2*h/(k*t))). A thick, conductive fin has eta near 1; thin or poorly conductive fins fall short, which is why aluminium and copper dominate sink design.
### (2) natural-convection fin spacing [primary | alive (full text fetched 2026-11-02)]
Title: Teertstra, Natural convection modeling of heat sinks using web-based tools (Electronics Cooling, 2000)
URL: https://www.electronics-cooling.com/2000/09/natural-convection-modeling-of-heat-sinks-using-web-based-tools/
Parallel-plate free convection (Elenbaas correlation; Bar-Cohen & Rohsenow optimum-spacing work, ASME J. Heat Transfer 1984, cited in the article's references) sets a practical near-optimum gap well above a millimetre for natural convection sinks; packing fins tighter backfires once flow between fins is choked. Our workshop gap rule (>= 1.0 mm) is a manufacturing/air-movement floor, not an optimum.
### (3) straight-fin vs interrupted fins [primary | alive (serves application/pdf)]
Title: Ahmadi, Mostafavi & Bahrami, Natural convection from rectangular interrupted fins (IJTS 82, 2014, PDF)
URL: https://www.sfu.ca/~mbahrami/pdf/pdf/2014/Natural%20convection%20from%20rectangular%20interrupted%20fins.pdf
Published variants interrupt the fins to restart boundary layers: rectangular interrupted fins under natural convection (measured + modelled, weight reduction noted). Our artefact class is the plain straight-fin form only; it claims none of those variants' effects.
### (4) heat-sink selection guidance [secondary | dead (HTTP 500 on re-fetch 2026-11-02, twice)]
Title: ATS, How to Select a Heat Sink (on-demand webinar page, qats.com)
URL: https://www.qats.com/cms/2011/08/29/how-to-select-a-heat-sink-an-ats-on-demand-thermal-management-webinar/
Industry selection guidance (straight-fin extrusion as the standard commercial form; keep straight fins parallel to the approaching flow under forced convection). The page itself would not load at build time, so the note uses it only as a pointer to check independently — nothing is quoted from it.
### (5) optimum-spacing paper record [secondary | unverified (index page, not independently fetched)]
Title: Bar-Cohen & Rohsenow, Thermally Optimum Spacing of Vertical, Natural Convection Cooled, Parallel Plates (Semantic Scholar record)
URL: https://www.semanticscholar.org/paper/Thermally-Optimum-Spacing-of-Vertical%2C-Natural-Bar-Cohen-Rohsenow/273257d7df3dab5a1633e80a990d11f01f364137
Bibliographic pointer to the 1984 optimum-spacing paper cited by the spacing literature. Listed so a reader can find the paper; the workshop asserts nothing from this record beyond its existence.

## Claims (each with its sources)

1. Same family as the textbook straight-fin form: the workshop geometry is that form, not a variant of it.
   source: Incropera Fins chapter (MEngr 503 course notes PDF) <https://courses.washington.edu/mengr503/Fins_Incropera.pdf>
   source: os/worlds/officina/runtime/heatsink.py
2. Wider gaps than the literature optimum where the loop lands them: the workshop floor is manufacturability, and the gate re-scores under tolerance, which the correlations do not model.
   source: Teertstra, Natural convection modeling of heat sinks using web-based tools (Electronics Cooling, 2000) <https://www.electronics-cooling.com/2000/09/natural-convection-modeling-of-heat-sinks-using-web-based-tools/>
   source: Bar-Cohen & Rohsenow, Thermally Optimum Spacing of Vertical, Natural Convection Cooled, Parallel Plates (Semantic Scholar record) <https://www.semanticscholar.org/paper/Thermally-Optimum-Spacing-of-Vertical%2C-Natural-Bar-Cohen-Rohsenow/273257d7df3dab5a1633e80a990d11f01f364137>
   source: os/worlds/officina/runtime/design_loop.py
3. Plainer than the measured variant families: no interruptions, perforations, or edge treatments.
   source: Ahmadi, Mostafavi & Bahrami, Natural convection from rectangular interrupted fins (IJTS 82, 2014, PDF) <https://www.sfu.ca/~mbahrami/pdf/pdf/2014/Natural%20convection%20from%20rectangular%20interrupted%20fins.pdf>
   source: os/worlds/officina/runtime/heatsink.py

Shelf limits: textbook fin theory, spacing correlations, one measured variant family, and industry/index pointers. No patent-database search was performed by the workshop tooling; coverage is the shelf above plus the repo, nothing more.

Research aid only. This note describes related approaches the workshop knows about (repo + shelf above) and how the brief's design differs from each. It states no conclusion about novelty or protectability, offers no legal opinion of any kind, and the workshop files nothing. A human decides what any of this means.

Provenance: status=proven proven=True rounds=4 final_R=1.7210411106861345

v5 placement trial — incomplete; NOT fabrication-ready
========================================================

Trial B moves only C7 and C14 from candidate-placement-3: C7 to
(32,259,-90) and C14 to (53,260,-90). It starts with the v5 synchronized
unrouted board and retains the existing section and antenna rule areas.
The zero-open experiment-silk-7 board remains untouched. This is a new,
independently routed hypothesis, not a finished or physically approved PCB.

Evidence
--------
* silk-b/result.kicad_pcb SHA-256:
  2a6f2adb1d2c4078de47b7a6d337af844bace43cf1a1155d9afe8d2e7d51e7e8
  Native KiCad 10.0.2 DRC: zero violations, zero unconnected items
  (silk-b/drc.json). Its adjacent project enables missing-courtyard errors
  and has no DRC exclusions. The four checks listed as ignored in the report
  remain unverified. The library table refers to the original v5 library,
  rather than another copy.
* trial-b-parity.json is a native --schematic-parity DRC run against a
  temporary copy of this exact board and the v5 schematic hierarchy, named
  DAR-1000ES-v5.kicad_pcb alongside the matching schematic and project.
  It reports zero violations, zero opens and zero schematic-parity issues.
  baseline-parity.json independently repeats this check on silk-7.
* The retained tool's netlist and section audits passed before and after
  routing: 319 netlist nodes checked, y=150 mm boundary, audio lower,
  with only GND, LOCAL_5V, SONY_5V_SENSE and the two exact UART nets allowed
  to cross. The post-processing audit also passed. This is not a check of
  installed plug, cable, screw or module envelopes.
* Freerouting output contained 715 tracks, seven vias, 0.30 mm minimum track
  width. router-b.log records the 30-pass maximum; it finished at pass 14.
  There is no global clearance increase or new custom rule.
* Pad-center distances (decoupling-b.txt) are C7/U9 4.38 mm supply and
  4.38 mm to the nearest grounded U9 pad, versus 70.19/74.01 mm in silk-7;
  C14/U11 is 5.73/6.70 mm versus 34.87/35.88 mm. The nearest grounded pad
  is not necessarily the IC ground supply pin: on trial B the 4.38 mm U9
  pad is a grounded logic input, not GND pin 7. These geometric lower bounds
  do not establish routed loop geometry, inductance, supply/return paths or
  decoupling effectiveness.
* Native KiCad copper-shape measurements, unrelated plated-through-hole
  pads versus tracks/vias on each common copper layer, are in
  trial-b-tht-clearance.json and baseline-tht-clearance.json. Trial B has
  330 pad-item-layer pairs below 0.30 mm, minimum 0.201657 mm; baseline has
  351 and the same minimum. C7 and C14 have no such pairs at or below
  0.50 mm in trial B; U9 has 13 pairs below 0.30 mm and U11 has one.
  These are pair counts, not unique locations; routing segmentation and
  layer count influence comparisons. This does not establish the requested
  generous track-to-pad spacing overall. It does not measure pad-to-pad,
  copper zones, non-plated holes or non-PTH pads.
* Trial A placed C7 at (31.5,259,-90), C14 at (44,254.5,0).
  It failed with 17 opens and one U11/C14 silkscreen-clearance warning
  after cleanup; trial-a-drc.json and router-a.log document the failure.
  Its native parity was zero (trial-a-parity.json). It is not a candidate.

Unresolved: several other IC decouplers remain roughly 12–28 mm from
corresponding supply/ground pads (see decoupling-b.txt). An orderly assembly,
installed module and socket/USB envelopes, connector plugs and bend radii,
screw hardware, antenna orientation and actual RF keepout, and physical
block fit have NOT been independently verified. Two-layer return-current
paths, RF performance, power integrity, and actual local decoupling loops
also remain unverified. The antenna rectangles and 7.5 mm mounting-hole
courtyards are hypotheses, not mechanical or RF signoff. No claim of
completion, electrical safety, fabrication or assembly readiness is made.

Reproduction
------------
From repository root, use KiCad Docker image kicad/kicad:10.0.2 and Java 25.
Download the exact pinned Freerouting 2.5.0 URL and SHA-256 in ../README.txt;
the jar is deliberately not retained. Place it in an allowed location and
remove it, generated intermediate run folders and .kicad-home afterward.
The copied route.py changes only its root calculation for this subdirectory;
board_ops.py is the retained v5 tool. Routing is heuristic; bitwise-identical
output is not guaranteed. The original source SHA-256 values are:

  synchronized.kicad_pcb  3f17f8ac83b0276d299423713e1b8e3a86ad88a685b1fce3819f0b2cab704299
  DAR-1000ES-v5.net.xml   c6d424b06f11b597e3b0e87ac63e1d30de1104816e0750a6b74f89be3b16abec
  DAR-1000ES-v5.kicad_pro beb313903373ac106929c207362c25c6bfc6b2145300d1f36ff8f86b920403f4
  plan-b.json             920e15ea7f8121e7287e83ec4274c338ddbb457c47c29c83df7d03c545a1a356

Set P=hardware/pcb-redesign/v5/routing/placement-trial and
V=hardware/pcb-redesign/v5, then:

  python3 "$P/route.py" place --board "$V/routing/synchronized.kicad_pcb" \
    --netlist "$V/DAR-1000ES-v5.net.xml" --plan "$P/plan-b.json" \
    --output "$P/reproduced-placement.kicad_pcb"
  python3 "$P/route.py" route --board "$P/reproduced-placement.kicad_pcb" \
    --netlist "$V/DAR-1000ES-v5.net.xml" --project "$V/DAR-1000ES-v5.kicad_pro" \
    --jar <verified-jar> --mode two --name reproduced-route \
    --boundary 150 --audio-side lower --passes 30 --timeout 420

The route command reports the pre-silk DRC failure due to inherited
silkscreen and missing mounting-hole courtyards, even when routing itself
has zero opens. After checking that result exists, run:

  python3 "$P/route.py" silk --board "$P/reproduced-route/result.kicad_pcb" \
    --netlist "$V/DAR-1000ES-v5.net.xml" --project "$V/DAR-1000ES-v5.kicad_pro" \
    --name reproduced-silk --boundary 150 --audio-side lower

The clearance report can be regenerated with measure_tht_clearance.py
inside the KiCad container on the resulting board. The decoupling distance
script is ../decoupling.py. Native parity requires a same-stem copy of the
board and project adjacent to the v5 schematic hierarchy; do not overwrite
any original source. Remove temporary copies, router and cache afterward.

Decoupling trial — incomplete; NOT for fabrication or power-up
=============================================================

This is a derivative of placement-trial B, not the canonical completed PCB.
It preserves that checkpoint and all footprint positions. result.kicad_pcb,
result.kicad_pro, the byte-identical copied v5 schematic hierarchy and
fp-lib-table are the candidate. No new preview has been generated: the
published inspection-readable views depict silk-7, NOT this candidate.

The only board changes are four 0.30 mm F.Cu GND segments from C7.2 to
U9.7 (independently found by another agent), one 0.30 mm B.Cu GND segment
from C14.2 (53,265) to U11.3 (48.54,260), and the two U11 SONY_5V_SENSE
junction shifts from clearance-trial C. The U5-VIN change is NOT integrated.
This keeps B's existing route and does not change any component positions.
The C14 return is shorter; the junction shift improves unrelated pad
clearance but lengthens C14's supply route. This is a limited improvement,
not the requested comprehensive bypass placement/routing fix.

Evidence and reproducibility identity
-------------------------------------
Source B SHA-256: 2a6f2adb1d2c4078de47b7a6d337af844bace43cf1a1155d9afe8d2e7d51e7e8
Candidate SHA-256, before and after the final DRC/parity/path/clearance
reports: 53428c44aaf48bd0ea867c7b11f82e9277dcee58e0993fbcc820f4a65fc4612f
See hashes.txt; tht-clearance.json independently records the latter hash.
The board diff is five added segments and three existing segments with the
two adjusted junction endpoints, not a resave of unchanged B.

Native KiCad 10.0.2 drc.json reports zero violations and zero opens;
parity.json reports zero violations, zero opens and zero parity issues.
The project has no exclusions and missing-courtyard is an error. Four
checks remain ignored: track_not_centered_on_via, tuning_profile_track_
geometries, footprint_filters_mismatch and footprint_type_mismatch.
audit.txt checks the v5 netlist, exact UART endpoints, 150 mm domain
boundary, classified footprint envelopes, unchanged footprint/pad
placement, rule-area bounds/restrictions, 720 segments, seven vias and
0.30 mm minimum trace width. The netlist has 319 nodes. The audit does not
validate installed modules, connectors, wiring, chassis or RF envelopes.
Both native reports and audits ran on the final candidate bytes.

Measured centerline copper paths
-------------------------------
measure_paths.json and baseline-paths.json use explicit actual supply pins:
SN74AHCT125 and SN74AHCT00 VCC=14/GND=7; MCP100 VDD=2/VSS=3;
DevKit socket header 5V=J1.21/GND=J1.22. The DevKit figures stop at the
header and exclude the module's internal power/ground routing. Grounded
logic inputs, such as U9.12/.13, are NOT substituted for U9's supply
ground pin 7. Every reported endpoint is connected on the correct net.

Shortest modeled centerline length in mm, capacitor pad to IC supply pin:
                 B VCC / GND        candidate VCC / GND
  C1/U3          12.804 / 123.004   12.804 / 123.004
  C2/U4          12.784 / 122.190   12.784 / 122.190
  C3/U2          26.468 / 181.309   26.468 / 181.309
  C4/U6          38.401 / 120.790   38.401 / 120.790
  C5/U7          32.228 / 30.211    32.228 / 30.211
  C6/U8         105.586 / 74.717   105.586 / 74.717
  C7/U9           4.380 / 22.053     4.380 / 20.493
  C8/U10         22.526 / 24.691    22.526 / 24.691
  C14/U11         7.288 / 7.507      7.547 / 6.700
  C10/U1         13.731 / 7.516     13.731 / 7.516
  C11/U1          8.331 / 32.112     8.331 / 32.112
  C12/U6-AUDIO1  15.331 / 9.660     15.331 / 9.660
  C13/U6-AUDIO1   8.331 / 15.168     8.331 / 15.168

C7's VCC run is direct B.Cu, 4.380 mm. Its actual pin-7 return is
F.Cu: (32,264) -> (30,272.75) -> (28.75,274.75) -> (28,275.5) ->
(20,274.24), 20.493 mm, zero vias; it is not a few-mm compact bypass
return. C7's grounded gate inputs are separate
from the ground supply pin. No interior branch was found on this selected
centerline in the graph; its end pad is shared with the wider GND network.
The short 4.413 mm route previously reported to U9.12 was not a valid
substitute for the IC supply-ground path. A bounded search of straight and
single-bend direct paths on both layers to U9.7 did not find a shorter
DRC-clean route; an independent agent's multi-bend search found the route
above. Neither search was exhaustive. C14's actual ground is pin 3;
its two paths total 14.247 mm of external centerline, versus 14.795 mm
in B. This is relatively local, not a verified low-inductance loop.

The DIP-14 supply pins occupy opposite ends/corners: U9.14 is at
(27.62,259), U9.7 at (20,274.24), 17.04 mm apart. C7.2 to U9.7
alone is 15.78 mm straight-line pad-center distance, so a few-mm
external return to that actual pin is impossible without changing the
package/placement concept. These are geometric bounds, not a reason to
alter the validated package. Most other listed loops have long, shared
ground/supply paths; C1, C2, C3, C4 and C6 are particularly poor. They
remain major unresolved electrical-layout defects.

The graph joins same-net, same-layer straight segment centerlines at
crossings, through native pad hit-tests and at plated vias; it includes
pad-center-to-contact distances and assigns zero length to via barrels.
It rejects copper zones/arcs, has no electromagnetic model, and may miss
width-only contacts not crossing centerlines. Multiple paths and shared
ground copper carry frequency-dependent current; shortest path length,
absence of intermediate pad nodes, or zero DRC opens does not prove a
local return current, low inductance, decoupling effectiveness or power
integrity. The geometry excludes capacitor/IC internals and package leads.
Intermediate shared-pad names and every selected path are in the JSON.

Section crossings, silkscreen, solder access
-------------------------------------------
crossings.json reports track centerlines at y=150 mm: GND B.Cu x=22.3;
SONY_5V_SENSE F.Cu x=48; LOCAL_5V F.Cu x=56.1791; UART IO47 F.Cu
x=57.0639 and IO21 F.Cu x=57.5656. These are actual crossings, not proof
of deliberate bounded corridors: none were specified or enforced.
The section audit checks permitted nets, not corridor bounds or return
currents. Further signal/return and corridor design is required.

tht-clearance.json reports minimum unrelated track/via to PTH pad clearance
0.201657 mm; 332 pad-item-layer pairs are below 0.30 mm (B had 330).
For U11 pad 3 the local minimum is 0.351701 mm, versus 0.201700 mm in B.
This is not global 0.30–0.50 mm compliance; the report excludes pad-pad,
zones, non-PTH holes and non-PTH pads, and pair counts depend on segmentation.

The board diff preserves all original silkscreen. silk_inventory.json finds
all footprint references visible on a silk layer, but no board-level silk
text and no connector-specific silk text beyond references: section names
and connector pin/function labels are not established. This inventory does
not check label overlap, readability, orientation, polarity or assembly
access; native DRC alone is not assembly-silk signoff. No new closeups were
produced. Physical fit, component insertion, soldering, connector mating,
RF clearance, chassis and actual bench behavior remain unverified.

Reproduction
------------
Requires Docker KiCad 10.0.2 (image digest
sha256:165c81785b2df23a09892f4cc53bc0095a83b469bfbbe07989670d64049677a7).
Use a writable OUT directory outside the repository. No router JAR is
required. Rebuilding may assign a different UUID to the new segment, so
compare geometry and checks, not a regenerated board's byte hash.

  P=hardware/pcb-redesign/v5/routing/decoupling-trial
  V=hardware/pcb-redesign/v5
  cp "$V/routing/placement-trial/silk-b/result.kicad_pcb" "$OUT/result.kicad_pcb"
  cp "$V/routing/placement-trial/silk-b/result.kicad_pro" "$OUT/result.kicad_pro"
  sed 's@../../DAR1000ES.pretty@/work/hardware/pcb-redesign/v5/DAR1000ES.pretty@' \
    "$P/fp-lib-table" > "$OUT/fp-lib-table"
  docker run --rm --network none --user "$(id -u):$(id -g)" \
    -e HOME=/nonexistent -e PYTHONDONTWRITEBYTECODE=1 \
    -v "$PWD:/work:ro" -v "$OUT:/out:rw" --entrypoint /usr/bin/python3 \
    kicad/kicad:10.0.2 /work/$P/improve.py /out/result.kicad_pcb /out/drc.json
  docker run --rm --network none --user "$(id -u):$(id -g)" \
    -e HOME=/nonexistent -e PYTHONDONTWRITEBYTECODE=1 \
    -v "$PWD:/work:ro" -v "$OUT:/out:rw" --entrypoint /usr/bin/python3 \
    kicad/kicad:10.0.2 /work/$P/adjust_c14.py /out/result.kicad_pcb /out/drc.json

  docker run --rm --network none --user "$(id -u):$(id -g)" \
    -e HOME=/nonexistent -e PYTHONDONTWRITEBYTECODE=1 \
    -v "$PWD:/work:ro" -v "$OUT:/out:rw" --entrypoint /usr/bin/python3 \
    kicad/kicad:10.0.2 /work/$P/add_c7.py /out/result.kicad_pcb /out/drc.json

The retained same-stem schematic copies permit the native parity report.
The three audits/path/clearance tools can be run read-only as shown by their
arguments in audit.py, measure_paths.py and ../measure_tht_clearance.py.
KiCad may log configuration errors because HOME is intentionally unwritable;
check subprocess exit status and report contents, not console messages alone.
Run test_measure_paths.py with the same container. No physical validation is
claimed and further bypass/routing work is essential before any fabrication.

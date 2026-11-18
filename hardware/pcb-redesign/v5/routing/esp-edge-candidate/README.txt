SUPERSEDED GEOMETRY WARNING
==========================
The placement and routing below are historical. The body and antenna model
and edge-flush claim in this original account are superseded; they do not
describe the corrected comparison at ../esp-orientation-comparison/README.txt.
Using the supplied v1.1 carrier bounds, each carrier's pin-1-end edge is
3.60 mm inside the motherboard edge. See ../esp-reference-candidate/README.txt
for the geometry-only derivative and unresolved RF restrictions. The original
PCB in this directory remains unchanged.

ESP edge-routing experiment — NOT FOR FABRICATION OR POWER
=========================================================

Historical account follows; geometry assumptions are superseded as above.

This is one experimental two-layer candidate, not an RF, mechanical,
electrical or manufacturing sign-off. The source remains unchanged:
placement-current/result.kicad_pcb, SHA-256
1639ae39478dff811224cf6ff1e299ec685bb6e8568631e4d861dfafcb36eafa.
The saved, refilled candidate hash is in board.sha256.

Placement and physical uncertainty
----------------------------------
U1-CONTROLLER1 moves rigidly to (66,5) mm, 0 degrees; U6-AUDIO1 moves
rigidly to (86,295) mm, 180 degrees. A KiCad footprint contains each entire
two-row socket assembly: the pads, footprint artwork, and relative pad
geometry rotate together. All other footprints are unchanged except C10,
C11, C12 and C13, which are relocated for bypass locality; audit.json and
placement.json record their positions and measurements. The original board
outline, connector and mounting-hole positions, pad geometry/net assignments
and power-net assignments are unchanged.

The comparison in ../esp-orientation-comparison/ models the installed
DevKit body as local x=-1.27..24.13, y=-5..57.74 mm, and the antenna as
local x=-1.27..24.13, y=-10..-5 mm. Under those assumptions the antenna
projection lies outside the board and the body is exactly flush with its
edge. THIS IS NOT A VERIFIED ANTENNA CLEARANCE: actual devkit revision,
antenna y-offset, board/body dimensions, alignment, RF clearance and required
tolerances are unknown. No fitted antenna rule area is claimed; the old
inboard provisional rule areas were removed, rather than misleadingly
retaining them at their former positions. Specifically unresolved are the
installed module and devkit manufacturer, part and board revisions (including
PCB-antenna versus external-antenna variants), antenna location and extent
relative to the two socket rows, the module/board outline and thickness, and
the required three-dimensional copper, substrate and nearby-metal exclusion.
The assumed overhang has zero edge tolerance and is not evidence that any
actual antenna is off-board or clear. The modeled controller body is
only 1.095 mm from the assumed H2 mounting-hardware courtyard. USB, connector,
washer, cable and chassis clearances require physical verification. The
comparison's signal-link proxy increases from 1113 to 1396 mm (controller)
and from 990 to 1397 mm (audio); this is not routed length or timing proof.

Routing and verification
------------------------
The complete original route and zones were removed before exporting a fresh
DSN. The pinned router generated 697 segments and 12 vias. A temporary
routing-only project uses 0.30 mm netclass clearance; the original project
is restored byte-for-byte before native DRC, and no board rules or DRC
exclusions were weakened. The router reports eight fixed pin-to-pin
violations against the stricter temporary clearance for U10/U11 close-pitch
pads; those pads were not changed. Native KiCad DRC against the original
project reports zero violations and zero opens after actual refill/save;
native schematic parity and a subsequent read-only DRC also report zero.
Four inherited checks remain ignored: track_not_centered_on_via,
tuning_profile_track_geometries, footprint_filters_mismatch and
footprint_type_mismatch.

Both original ground zones were restored and refilled. R4.2 and R11.2
retain their original zone-connection settings; no solid-pad override was
used. Native DRC reports no starved thermal. Thermal solderability, actual
plane return continuity and high-frequency current loops still need review.
Two filled GND zones and native connectivity do not prove that the capacitor
ground current follows a short, uninterrupted return underneath its supply
path, or that a high-frequency bypass loop has acceptable inductance. Actual
return currents, GND segmentation, stitching, thermal solderability and the
ESP module's own decoupling require engineering review and measurement.
The section audit checks the exact UART endpoints, every classified footprint
envelope and all pad, track, via and non-rule-zone crossings of y=150 mm.
Only GND, LOCAL_5V, SONY_5V_SENSE and the two exact UART nets are permitted
to cross. crossings.json lists actual track centerline crossings.

For unrelated PTH-pad to track/via layer pairs, clearance.json measures:
minimum 0.301649 mm versus 0.201700 mm in placement-current; pairs under
0.30 mm: 0 versus 137; under 0.25 mm: 0 versus 42. Counts are layer pairs,
not unique sites. This measure excludes zones, pad-pad, mask, non-PTH holes,
SMD pads and mechanical tolerances; it is not a manufacturing assessment.
The script enforces the same minimum and count non-regression gates.

ESP supply pad-center / track-only distances in mm: C11 4.079/4.331,
C10 9.002/9.746, C13 4.079/4.331, C12 7.046/9.331. C12 ground path is
15.622 mm track-only. In the source the respective supply pad-center /
track-only distances were C11 8.040/8.331, C10 10.121/13.731,
C13 8.040/8.331 and C12 10.121/15.331 mm. These distances do not prove a
good bypass loop or account for plane current; see audit.json
for all supply/ground path measurements and limitations.

J8-J11 and JP1/JP2 connector legends remain on F.SilkS and were relocated
to avoid the rotated socket; they are dispersed, not necessarily adjacent
to the connectors. Individual connector pin labels are retained. The fitted
preview/{assembly,front-copper,back-copper}.pdf files show the entire board;
the matching labeled PNGs are rendered at 150 dpi. The six labeled
closeup-*-controller.png and closeup-*-audio.png images are rendered at
600 dpi and show the two moved sockets with nearby components and board edge.
Copper views are unmirrored. These plots are inspection aids, not
manufacturing artwork or verification of the installed antenna geometry.

Reproduction
------------
From repository root, using KiCad image
kicad/kicad@sha256:165c81785b2df23a09892f4cc53bc0095a83b469bfbbe07989670d64049677a7,
Java 25 and the independently downloaded official Freerouting 2.5.0 JAR:

  bash hardware/pcb-redesign/v5/routing/esp-edge-candidate/build.sh \
    esp-edge-candidate-replay /absolute/path/to/freerouting-2.5.0.jar

The JAR is verified against the upstream published SHA-256
f6f51bb02245e8e717f9359bd260cc9c5c0b1bc0acc8b7cb2cd5b8ffeb5de3c7.
The output sibling must not exist. Source board, project and netlist hashes
are checked. The script re-exports from the updated placement using the
temporary 0.30 mm routing clearance, reroutes, imports, retains thermal
settings, relocates legends, refills/saves, checks DRC and parity, audits
geometry/domains and clearances, plots and verifies the saved board. KiCad
UUIDs may change the output hash. The router itself has eight fixed-pad
clearance warnings at 0.30 mm; always inspect the resulting native reports.

ESP reference-envelope correction — NOT FOR FABRICATION OR POWER
================================================================

This is a non-RF CAD correction of ../esp-edge-candidate/result.kicad_pcb,
not an antenna-safe redesign. The original, already Freerouting-routed board
is preserved; neither placement nor routing was changed here. A fresh route
is not justified by the unverified antenna model. The inherited routing
workflow, pinned Freerouting JAR hash, original project, and documented
temporary 0.30 mm router target are in ../esp-edge-candidate/build.sh and
README.txt. This derivative restores the original project byte-for-byte.

Carrier geometry and placement
------------------------------
Per the user-supplied official v1.1 carrier bounds relative to J1.1, the
F.Fab rectangle is x=-1.27..24.13, y=-1.40..61.34 mm. Its short crossbar
marks the J1.1/pin-1 end (antenna end), NOT the antenna boundary. Existing
socket F.Fab artwork remains. The local project footprint library contains
the matching updated artwork; the upstream library is unchanged.

Controller J1.1=(66,5), angle 0: carrier x=64.73..90.13, y=3.60..66.34.
Audio J1.1=(86,295), angle 180: x=61.87..87.27, y=233.66..296.40.
Both carrier ends are 3.60 mm inside the 100 x 300 mm outline, not flush.
geometry.json checks component courtyard bounding boxes, falling back to
pad boxes where absent: neither carrier box overlaps another. Closest gaps
are 1.095 mm to H2 and 0.955 mm to C12 respectively. These 2D bounds are
not a 3D assembly, hardware, tolerance, connector, USB cable, chassis or
component-height clearance analysis.

RF blocker and observed risks
-----------------------------
The exact installed module variant, antenna radiator geometry and its
required 3D copper, substrate and metal exclusion are not established here.
The primary drawing supplied by the user could not be fetched in this
environment for independent verification:
https://dl.espressif.com/dl/schematics/esp_idf/DXF_ESP32-S3-DevKitC-1_V1.1_20220429.pdf
A secondary raster reproduction was inspected during this run at
https://github.com/JamelHammoud/basecase/blob/main/tools/parts/specs/esp32-s3-devkitc-1/dim-1.png
with unknown provenance. Its MINI-ANT-TYPEB feature was roughly estimated
at x=2.4..20.5, y=-7.9..-1.5 mm relative to J1.1. This is pixel-derived,
not a verified antenna or keepout boundary. Its nominal projection intersects
63.35 mm² of motherboard substrate for each ESP; crude track/via bounding-box
intersection counts are 5 controller and 2 audio. These counts do not test
actual copper intersection, filled zones, antennas, metal, or tolerances.
There are no other courtyard-box intersections with this rough feature.
Actual conflict and RF clearance remain unknown, not demonstrated safe.

Espressif's hardware design guidance discusses 15 mm antenna clearance; its
applicability, coordinate origin and three-dimensional extent must be checked
for the actual module and installation against the primary documentation.
No invented antenna area, copper/component keepout, or RF compliance claim is
made. Confirm module and carrier revision/variant, primary antenna geometry,
the required clearance and the physical installation, then reposition/reroute
and re-audit as necessary before considering manufacture or power-up.

Validation and reproduction
---------------------------
KiCad 10.0.2 native refill/save DRC, schematic parity, and read-only DRC each
report zero violations and zero opens. The four inherited ignored checks
are listed in drc.json; no rules were weakened. audit.json verifies outline,
placements and pad geometry against placement-current, exact netlist, UART,
domain/component envelopes, filled GND zones and bypass path measurements;
verify.py also checks the inherited track/via geometry and net assignments.
The original connector positions, domains, separate power assignments and
local bypasses are retained. The PTH-pad to unrelated track/via lower bound is
0.301649 mm, with no measured pairs below 0.30 mm. This partial clearance
metric does not cover all item classes or manufacturing tolerances.

Plots in preview/ include native F.Fab in assembly; copper is unmirrored.
They are inspection aids, not manufacturing artwork. From the repository
root, with Docker and the pinned KiCad image available:

  bash hardware/pcb-redesign/v5/routing/esp-reference-candidate/build.sh \
    esp-reference-candidate-replay

The output sibling must not exist. Source board and project hashes are
checked; the script builds the local library and board, refills, runs checks,
and produces plots. Generated UUIDs and the board hash may vary between runs.
The source edge-routing build requires the separately obtained official
Freerouting JAR; no router or network access is needed for this correction.

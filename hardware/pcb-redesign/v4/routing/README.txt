DAR-1000ES v4 routing inputs
============================

Run these commands from the v4 project directory using KiCad 10's Python.
The source project is never modified. Build and verify each candidate in a
new directory; retain the best candidate only after native verification.

    /usr/bin/python3 routing/kicad_route.py DAR-1000ES-v4.kicad_pcb > /tmp/dar-layout.txt
    grep -E '^(segment|bridge) ' /tmp/dar-layout.txt > /tmp/dar-roundtrip.txt
    /usr/bin/python3 routing/kicad_route.py DAR-1000ES-v4.kicad_pcb \
        --routes /tmp/dar-roundtrip.txt --output /tmp/dar-roundtrip
    /usr/bin/python3 verify.py --project /tmp/dar-roundtrip --reports /tmp/dar-verification

The verifier exits nonzero while there are opens and writes both native
reports (wires fitted and wires open) as well as a geometry summary.
Initialize KiCad's standard symbol/footprint library tables before running
the verifier. On Linux the official kicad/kicad:10.0.2 image provides both
pcbnew and kicad-cli.

Compile and run the standalone C++17 search on an exported layout:

    c++ -std=c++17 -O3 -Wall -Wextra -pedantic routing/route.cpp -o /tmp/dar-route
    /tmp/dar-route --passes 8 --seed 1 --checkpoint /tmp/dar-best.txt \
        < /tmp/dar-layout.txt > /tmp/dar-candidate.txt
    /usr/bin/python3 routing/kicad_route.py DAR-1000ES-v4.kicad_pcb \
        --routes /tmp/dar-candidate.txt --output /tmp/dar-candidate --trim-dangling
    /usr/bin/python3 verify.py --project /tmp/dar-candidate --reports /tmp/dar-verification

The router starts with the exported copper and preserves the best estimated
connectivity in its checkpoint. Later passes can rip up obstructing segments
and try to reconnect the affected nets. To resume, combine the original
width/pad/block records with the best segment/bridge records, or export
the latest saved and native-checked candidate. Never append two sets of
tracks to the same input. See `dar-route --help` for search options.

The router's score is not native DRC. Optional dead-end cleanup removes
only track segments reported by native DRC as dangling and stops if other
violations appear. This can change the number of unconnected items;
compare the full verification report after cleanup before adopting a route.

For a fresh route, use --fresh to omit the saved copper and wires. Add
--placement routing/controller-corridor.txt to try a redistributed
controller buffer placement; supply that same flag and path on import.
The alternative placement passed native DRC with no tracks installed.

Functionally separated placement trial
-------------------------------------
separated-blocks.txt groups J9/U2 mute and relay with the audio ESP, DAC/PCM
buffers, audio passives and J10/J11. U3/U4/U5 and J3–J8 stay on the left.
J2, J12, C8/C9, U10 and R12/R13 are shared support, not isolated supplies.
The NAND change moves ENABLE_U2/SONY_POWER_GOOD/U2_OE_N from U8 pins
1/2/3 to U9 pins 9/10/8. Former U8 inputs 1/2 tie to GND and pin 3 is
explicitly unconnected. The other four gates, connector and ESP pins,
capacitor rails and firmware are unchanged. The importer installs the
matching separated-interlock sheet only in the candidate directory.

    : > /tmp/dar-empty.txt
    /usr/bin/python3 routing/kicad_route.py DAR-1000ES-v4.kicad_pcb \
        --placement routing/separated-blocks.txt --routes /tmp/dar-empty.txt \
        --output /tmp/dar-separated-placement
    /usr/bin/python3 verify.py --separated --placement-only \
        --project /tmp/dar-separated-placement --reports /tmp/dar-placement-reports
    /usr/bin/python3 routing/kicad_route.py DAR-1000ES-v4.kicad_pcb \
        --fresh --channels --placement routing/separated-blocks.txt > /tmp/dar-separated.in
    /tmp/dar-route --order long --seed 41 --escape 24 --attempts 8 \
        --passes 13 --budget 42000 --bridge-penalty 2.5 \
        --checkpoint /tmp/dar-separated-best.txt \
        < /tmp/dar-separated.in > /tmp/dar-separated-routes.txt
    /usr/bin/python3 routing/kicad_route.py DAR-1000ES-v4.kicad_pcb \
        --placement routing/separated-blocks.txt --routes /tmp/dar-separated-routes.txt \
        --output /tmp/dar-separated-routed --trim-dangling
    /usr/bin/python3 verify.py --separated \
        --project /tmp/dar-separated-routed --reports /tmp/dar-separated-reports

The placement-only run checks physical placement and parity, not routing
completion. Channels allow local nets to use part of the central gap, but
not the opposite assembly block. Cross-block nets and common power and
ground have no artificial channel boundary or split.

Routing interchange (millimetres, top-view world coordinates):

    width NET WIDTH
    channel NET MIN_X MAX_X
    pad NET X Y HALF_WIDTH HALF_HEIGHT
    block MIN_X MIN_Y MAX_X MAX_Y
    segment NET X1 Y1 X2 Y2
    bridge NET X1 Y1 X2 Y2

NET IDs are sorted by schematic net name. Zero denotes a passive copper
obstacle, not a routable net. The input uses conservative pad boxes and
top-only keepout boxes for component bodies, silkscreen, installation and
screwhead envelopes. Route only on B.Cu; 0.30 mm signal / 0.80 mm power,
0.20 mm minimum clearance, 0.50 mm copper-to-edge spacing. Bridge records
are placed as 1.60 mm plated lands with 0.80 mm drills, a straight wire
between them, and no vias. Router output is only a candidate, not sign-off.

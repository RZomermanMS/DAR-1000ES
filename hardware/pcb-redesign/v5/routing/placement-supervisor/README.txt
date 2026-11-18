C8/U10 bypass relocation — experimental, NOT FOR FABRICATION OR POWER
=====================================================================

This independent derivative starts from clearance-first-corrected, SHA-256
c63fa89924e244bbf6bfd92f2c72e6c9d34117106b4bd87cf46f7971078920c5.
C8 moves from (48,124) to (45,96) mm, rotated 270 degrees. Its pad 1 is
at (45,96), and pad 2 at (45,101). U10 pins 2/3 remain at (49.27,102)
and (50.54,102). A new F.Cu 0.30 mm SONY_5V_SENSE branch joins the
existing U10 pin 2 route at (49.164739,96); that existing route is split
at the junction. The old C8 copper remains connected to its original
nets; the C8 ground pad connects to the refilled GND planes.

The saved result.kicad_pcb SHA-256 is
ecb68db85598d475af1b20ec5be40f3d330991a4b8ae8eb20d879b0d009dd67b.
The refill/save native DRC, subsequent read-only DRC, and schematic-parity
DRC report 0 violations, 0 opens, and 0 parity issues. The four inherited
ignored checks were not changed. Netlist, UART, section, component
envelopes, unchanged other placements, antenna-rule areas, and GND zone
checks passed. Both refilled GND zones retain thermal relief and island
removal. Samples within the thermal gaps around C8.2 and U10.3 find plane
copper on both layers; this is not a return-current or thermal analysis.

Actual pin-center distances and track-only modeled paths:
  C8.1 to U10.2 SONY_5V_SENSE: 22.037 -> 7.364 mm center distance;
    track-only path 22.526 -> 10.166 mm.
  C8.2 to U10.3 GND: 22.137 -> 5.630 mm center distance;
    no track-only path in the new board; return uses the refilled planes.
These are geometric measurements, not loop inductance or proof of
high-frequency decoupling. A closer bypass may still be desirable.

Native copper-shape PTH-pad to unrelated track/via measurement gives
144 layer-specific segment pairs below 0.30 mm, 45 below 0.25 mm, and
0.201700 mm minimum, unchanged in aggregate from the source. It excludes
zones, pad-to-pad clearance, non-PTH holes, SMD pads, mask dams, tooling,
installed parts and manufacturing tolerances.

Reproduce from repository root with the pinned KiCad image using
  bash hardware/pcb-redesign/v5/routing/placement-supervisor/build.sh
The build refuses to overwrite an existing result.kicad_pcb. Remove or
rename that file first; other reports and project copies are regenerated.
KiCad-generated UUIDs can cause a different result hash on replay. The
source is hash-guarded, and the saved-board hash is verified after DRC.
The source and other placement workspaces are not modified.

No RF, actual return-current, power-sequencing, solder-access, mechanical,
fabrication, or bench validation is implied. Other bypass groups are not
included in this independent candidate.

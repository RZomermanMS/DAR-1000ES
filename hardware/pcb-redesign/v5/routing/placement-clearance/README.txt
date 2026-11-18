Placement-integrated clearance derivative — EXPERIMENTAL, NOT FOR FABRICATION OR POWER
=====================================================================================

Open result.kicad_pcb with the adjacent result.kicad_pro, schematic, child
sheets and library tables. Its saved, refilled SHA-256 is
  943231dff205f6002cc8ae35e5011da886671f8ab1f16bf03c6b5b88d6374de3
The untouched source is placement-integrated/result.kicad_pcb, SHA-256
  06f73f9b662897d0822611513cf09feb3f9ccb1c8e08e6cac4ecad31c147810c

Two connected-track junctions were moved, without changing tracks' width,
layer, net, or endpoint connectivity, and with no footprint or pad geometry
changes. On B.Cu, a Net-(U5-VIN) junction moves 0.3 mm away from controller
socket U1-CONTROLLER1; on F.Cu, the LOCAL_5V junction by U8 moves 0.3 mm
away from grounded U8 pin 13. The latter is not U8's supply GND pin (7).
No pad or global design rule was changed.

The native copper-shape measurement of unrelated PTH-pad-to-track/via layer
pairs, at a 0.5 mm reporting threshold, gives:
  minimum:                  0.201700 -> 0.201700 mm
  pairs below 0.30 mm:            144 -> 137
    B.Cu:                         137 -> 132
    F.Cu:                           7 -> 5
  pairs below 0.25 mm:             45 -> 42
  reported pairs improved:         14; worsened: 0; newly entered: 0
The unchanged worst case remains near R3 and other pads, so the 0.30 mm
preference is NOT met globally. Counts are segment/pad/layer pairs rather
than distinct places. The comparison only proves this result inside its
0.5 mm threshold; it excludes zones, pad-pad, non-PTH holes, SMD pads, mask
dams, installed components, tools and manufacturing tolerances.

Native KiCad 10.0.2 refill/save DRC: zero violations, zero opens; schematic
parity: zero violations, zero opens, zero parity issues; a second read-only
DRC confirms the exact saved board. Four inherited checks remain ignored:
track_not_centered_on_via, tuning_profile_track_geometries,
footprint_filters_mismatch and footprint_type_mismatch. Netlist, UART,
domain/component-boundary, unchanged footprint/pad geometry, provisional
antenna rule areas, common-GND zones/thermal settings and local ground-fill
sampling pass; see audit.json. Track-only bypass path lengths match the source.
These checks do not prove return-current continuity or high-frequency behavior.
No new electrical, mechanical, RF, power-sequencing or bench approval is implied.
The source's remaining limitations and 59 schematic ERC findings still apply.

preview/ contains inspection assembly, F.Cu and B.Cu PDFs/PNGs and controller
and C6/U8 closeups. These are inspection views, not manufacturing artwork.

Reproduction
------------
From repository root, with the pinned KiCad 10.0.2 Docker image available:
  bash hardware/pcb-redesign/v5/routing/placement-clearance/build.sh placement-clearance-replay
The output sibling must not exist. The script checks the exact source hash,
replays moves.json with junction/topology guards, exercises a wrong-input
guard, refills, saves, runs DRC/parity/domain/fill/clearance checks and
generates plots. It compares all reported pad/item/layer pairs against the
source and fails on a newly entered or worsened pair or insufficient
improvement. An independent replay produced the identical saved board hash
and measurements. Remove the replay directory after inspection.

search.py records the bounded exploratory method, including shape prefilter
and per-candidate native DRC with refill; moves.json contains the two selected
changes, not every candidate accepted by that exploratory search. Two other
locally accepted changes were deliberately discarded because they worsened
other reported clearances above 0.30 mm. The replay, not rerunning the search
over an output board, is the supported deterministic build.

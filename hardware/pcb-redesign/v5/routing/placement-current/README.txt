Current integrated placement review — EXPERIMENTAL, NOT FOR FABRICATION OR POWER
================================================================================

The current review board is result.kicad_pcb with adjacent result.kicad_pro,
result.kicad_sch, child sheets, fp-lib-table and sym-lib-table. Saved,
refilled board SHA-256:
  1639ae39478dff811224cf6ff1e299ec685bb6e8568631e4d861dfafcb36eafa
Both library tables are exact copies from placement-integrated. The custom
symbol library resolves through ${KIPRJMOD}/../../DAR1000ES.kicad_sym and
the footprint library through ${KIPRJMOD}/../../DAR1000ES.pretty. Preserve
the relative v5 directory layout. KiCad 10 supplies the standard libraries.

Composition
-----------
The exact placement-integrated board (SHA-256 06f73f9b662897d0822611513cf09feb3f9ccb1c8e08e6cac4ecad31c147810c)
is the common source. First replay the placement-clearance junction edits
with their exact-source and attached-track topology guards. Then apply the
placement-loop C6 and C8 edits with their local placement, net and copper
guards. Each stage's footprint and track delta is independently compared
against its respective verified standalone result. No composition conflict
was detected, so no additional reroute or search was necessary. The source
and standalone results remain unchanged.

An initial build revealed that pcbnew saving an intermediate board also
replaced the output project with defaults, adding a missing-courtyard DRC
exclusion. That output was discarded. The build now restores the exact
source project after the transform, requires byte equality with it after
verification, and asserts the exact inherited ignored-check set.

C6 moves from (55.5,41.5), 0 degrees to (58,44), 270 degrees; its pad 1 is
at (58,44) and pad 2 at (58,49) mm. Its actual U8.14 supply pad-center and
track-only distances are 5.472 mm, versus 4.533 mm in the source. Its GND
pad-to-U8.7 ground-pad center separation is 17.185 mm, versus 24.319 mm in
the source and 9.231 mm in the earlier pre-C6 board. The ground separation
improves against the immediate source but not that older placement. Neither
distance proves a compact or continuous high-frequency return loop.

C8 remains at (45,96), 270 degrees; its rerouted C8.1-to-U10.2 supply
track-only path is 8.396 mm (was 10.166), and the supply pad-center
separation is 7.364 mm. C8.2-to-U10.3 ground-pad centers remain 5.630 mm.
Track-only models omit plane current and do not establish loop inductance.
Other saved capacitor supply center / track-only distances in mm:
  C1/U3 3.380/3.380; C2/U4 3.380/3.380; C3/U2 3.880/3.880;
  C4/U6 3.015/3.015; C5/U7 4.380/4.380; C7/U9 4.380/4.380;
  C14/U11 5.730/7.547.
ESP C10/C11 to controller J1.21: 10.121/13.731 and 8.040/8.331;
C12/C13 to audio J1.21: 10.121/15.331 and 8.040/8.331. See audit.json for
all pad-center and track-only distances, ground samples and zone details.

Verification
------------
KiCad 10.0.2 native refill/save DRC: 0 violations, 0 opens; schematic
parity: 0 violations, 0 opens, 0 parity issues. A read-only native DRC
confirms the saved hash. Four inherited checks remain ignored:
track_not_centered_on_via, tuning_profile_track_geometries,
footprint_filters_mismatch and footprint_type_mismatch; no rules weakened.
Audit checks exact netlist/UART, classified section and component envelopes,
unchanged provisional antenna rules, both filled GND zones with thermal
relief and island removal, actual supply-pin geometry and sampled copper
near ground pads. Samples and native connectivity do not prove plane-return
continuity, high-frequency current distribution or impedance.

clearance.json and comparison.json measure native layer-specific copper
shapes for unrelated PTH-pad-to-track/via layer pairs. Relative to the
integrated source, minimum remains 0.201700 mm, pairs below 0.30 mm decrease
144 to 137, and pairs below 0.25 mm decrease 45 to 42. Fourteen reported
pairs improved; no common pair worsened and none entered or worsened below
0.30 mm. Three pairs enter and one leaves the 0.50 mm reporting threshold,
reflecting the combined loop edit; do not treat counts as unique locations.
Zones, pad-pad, non-PTH holes, SMD pads, mask dams, tools, installed
components and manufacturing tolerances are excluded.

preview/ provides assembly, F.Cu and B.Cu PDFs/PNGs, plus controller and
C6/U8 closeups from a title-only scratch plot copy of the saved board.
These are inspection aids, not manufacturing artwork. The provisional
antenna areas are not verified RF keepouts; substrate remains beneath the
inboard antennas. Mechanical fit, solder access, bypass return paths, power
sequencing, back-powering, RF and bench behavior remain unresolved. The
schematic retains 59 ERC findings. Do not fabricate, assemble or power.

Reproduction
------------
From repository root, with the pinned KiCad 10.0.2 Docker image available:
  bash hardware/pcb-redesign/v5/routing/placement-current/build.sh placement-current-replay
The sibling output must not already exist. The script checks source,
standalone reference, project, symbol table/library, move-plan and baseline
report hashes; verifies each composed delta; exercises reapplication and
wrong-hash guards; refills/saves; reruns DRC, parity, audits and clearance
checks; and creates previews and a saved-board hash. It uses no network and
only the output directory is writable. Remove the replay directory after
inspection. KiCad-generated UUIDs may change the hash: use the replay's own
reports. An independent replay matched all geometry, zones and clearance
results with a different board hash; the published board was not overwritten.

Placement-loop derivative — EXPERIMENTAL, NOT FOR FABRICATION OR POWER
========================================================================
Source: ../placement-integrated/result.kicad_pcb, SHA-256
06f73f9b662897d0822611513cf09feb3f9ccb1c8e08e6cac4ecad31c147810c.
Saved, natively refilled result.kicad_pcb SHA-256:
c1bb512a1d64567e40e9b5d1b4575b3344dc071ce7f61d6110152f85d02a7dfe.
Open with the adjacent result.kicad_pro, result.kicad_sch, child sheets,
fp-lib-table and sym-lib-table. The project-local symbol table references
../../DAR1000ES.kicad_sym in v5. This is independent of, and does not
modify, the source.

Changes and measured tradeoffs
------------------------------
* C6 was moved from (55.5, 41.5), 0 degrees to (58, 44), 270 degrees.
  The original C6.1-to-U8.14 F.Cu segment was removed and rebuilt to the
  moved pad. C6.2 GND to U8.7 actual supply-ground pad center distance
  decreases from 24.319 to 17.185 mm. The C6.1-to-U8.14 LOCAL_5V
  track-only path increases from 4.533 to 5.472 mm. Both pads still have
  native filled GND-zone access; audit.json records sampled copper near
  their thermal gaps on both sides.
* C8 remains at (45, 96), 270 degrees. Its F.Cu supply branch was ripped
  up and connected farther along the existing U10.2 SONY_5V_SENSE trunk;
  that trunk is split at the new junction. The modeled track-only C8.1
  to U10.2 path decreases from 10.166 to 8.396 mm; C8.2-to-U10.3 GND
  pad-center separation remains 5.630 mm.

These are geometric/track-centerline metrics, not loop inductance or proof
of current flow. Track-only models omit the GND planes; thermal-gap samples
do not establish return current distribution or compact high-frequency
loops. The C6 supply-path tradeoff is deliberate and not a universal
electrical improvement. All other footprint positions and pad geometry/nets
remain unchanged. No clearance rules or inherited exclusions were changed.

Evidence
--------
KiCad 10.0.2 native refill/save DRC: 0 violations, 0 opens; schematic parity:
0 violations, 0 opens, 0 parity issues. verification-drc.json repeats the
read-only check against the hashed saved board. The four inherited ignored
checks are listed in drc.json. audit.json records netlist/UART, component and
copper domain boundaries, unchanged provisional antenna rules, two filled
GND zones with thermal relief and island removal, actual supply-pin metrics,
and sampled GND fill. crossings.json records the crossing inventory.

clearance.json and comparison.json use native layer-specific KiCad copper
shapes for unrelated PTH-pad-to-track/via layer pairs. The minimum remains
0.201700 mm; counts below 0.30 mm remain 144 and below 0.25 mm remain 45.
No pair newly enters or worsens below 0.30 mm; three enter and one leaves
the 0.50 mm reporting threshold. These item/layer counts are not unique
locations. The measurement excludes zones, pad-pad, non-PTH holes, SMD
pads, solder mask dams, tooling, iron access and manufacturing tolerances.

Native DRC and sampled copper are not electrical, RF, assembly, mechanical
or bench approval. Provisional antenna areas are not verified RF keepouts,
and substrate remains under inboard antennas. Power sequencing,
back-powering, actual bypass return paths, installed-component and enclosure
fit, and solder access remain unresolved. Schematic ERC retains 59 findings.

Reproduction
------------
From repository root, using the locally available pinned KiCad 10.0.2 Docker
image:
  bash hardware/pcb-redesign/v5/routing/placement-loop/build.sh --replay
The replay subdirectory must not exist. The script checks source board,
project, sheets, footprint table and baseline clearance hashes; checks the
copied symbol table resolves to the v5 library; runs a
local-copper/reapplication test; rejects changed input and existing output;
refills/saves, then repeats native DRC, parity, domain/zone and clearance
checks. It verifies the saved board hash and refuses worse measured minimum,
counts or newly worsened/entered pairs below 0.30 mm. It makes no network
requests and only the output directory is writable. Fresh KiCad UUIDs may
change the replay hash, so use its own reports. Delete the replay directory
after inspection. Source and published result are never overwritten.

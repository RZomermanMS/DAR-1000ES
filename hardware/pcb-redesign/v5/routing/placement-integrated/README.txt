Integrated placement review — EXPERIMENTAL, NOT FOR FABRICATION OR POWER
========================================================================

The one current combined board is result.kicad_pcb, opened with the adjacent
result.kicad_pro, result.kicad_sch, child sheets and both library tables.
sym-lib-table resolves the custom DAR1000ES symbols through
${KIPRJMOD}/../../DAR1000ES.kicad_sym, the shared v5 library; fp-lib-table
similarly references ../../DAR1000ES.pretty. Keep the directory layout when
moving the project. Standard symbols use the KiCad 10 symbol directory.
The build copies both project library tables into the output workspace.
Saved, refilled board SHA-256:
  06f73f9b662897d0822611513cf09feb3f9ccb1c8e08e6cac4ecad31c147810c
This is a derivative of the published placement-c6 result in 04ac2d1
(SHA-256 fb1f06735ecc218e2946121efeb44f91a6d88a2804b6029a4e8973fffa8e859e).
The prior clearance-first and C6 boards remain unchanged.

Composition and placement (mm, degrees)
---------------------------------------
The independent controller, audio and supervisor transforms are replayed in
that order after C6. The saved footprint origin and angle are:
  C1 (30,24) 180;     C2 (30,49) 180;      C3 (35,173.5) 0;
  C4 (35.3,199.38) 0; C5 (40,223) 180;     C6 (55.5,41.5) 0;
  C8 (45,96) 270.
Exact saved pad positions and all pairs are in audit.json. C1/C2 move from
(25,44)/(25,69); C3/C4/C5 from (25,197)/(25,222)/(25,247); C6 from
(45,68); C8 from (48,124). Other footprint and pad geometry/net assignments
remain unchanged. The applied copper deltas match the independently verified
edits; native checks were rerun on this actual composition, not inferred.
The guards, exact incident-track checks and stepwise comparison prevent
silently combining a changed local edit. No composition conflicts or new
native DRC violations were detected; this does not establish physical fit.

Actual pad-center distances / track-only modeled supply paths (mm):
  C1.2-U3.14    3.380 / 3.380
  C2.2-U4.14    3.380 / 3.380
  C3.1-U2.14    3.880 / 3.880
  C4.1-U6.14    3.015 / 3.015
  C5.2-U7.14    4.380 / 4.380
  C6.1-U8.14    4.533 / 4.533
  C7.1-U9.14    4.380 / 4.380   (unchanged placement)
  C8.1-U10.2    7.364 / 10.166
  C14.1-U11.2   5.730 / 7.547   (unchanged placement)
  C10/C11 to controller ESP J1.21: 10.121/13.731, 8.040/8.331
  C12/C13 to audio ESP J1.21:      10.121/15.331, 8.040/8.331

The C6.2 GND-to-U8.7 ground-pad center separation increased from 9.231 to
24.319 mm. Shorter supply geometry does NOT prove a compact ground loop.
Other GND pad-center distances to the actual supply-ground pin are C1/C2
15.029, C3 15.398, C4 14.546, C5/C7 15.775, C8 5.630 and C14 6.700 mm.
Track-only paths do not include zone copper and are not loop inductance.
The two refilled GND planes pass DRC and sampled copper is present near
the relevant ground pads, but continuity of the actual high-frequency
return path and plane current distribution remain unverified.

Verification and limitations
----------------------------
KiCad 10.0.2 native refill/save DRC: 0 violations, 0 opens; schematic parity:
0 violations, 0 opens, 0 parity issues. The read-only DRC repeats on the
saved bytes and confirms the hash. Four inherited checks remain ignored:
track_not_centered_on_via, tuning_profile_track_geometries,
footprint_filters_mismatch, footprint_type_mismatch. No rules weakened.
Audit checks exact netlist/UART, component/domain boundaries, unchanged
provisional antenna rules, two filled common-GND zones with thermal relief,
island removal and sampled thermal-gap copper. These samples do not prove
return path continuity or high-frequency performance.

Native copper-shape measurement reports 0.201700 mm minimum unrelated
PTH-pad-to-track/via layer clearance, 144 segment/layer pairs below 0.30 mm
and 45 below 0.25 mm: the same totals as the C6 source. One pair entered and
one left the 0.5 mm reporting threshold; none newly entered below 0.30 mm.
Counts are item/layer pairs, not unique locations. Zones, pad-pad, non-PTH
holes, SMD pads, mask dams, tooling, installed parts and manufacturing
tolerances are excluded. This is not a solder-access or fabrication test.

preview/ has full assembly, F.Cu and B.Cu PDFs/PNGs and controller/C6
closeups, generated from the saved board with title-only changes on a
scratch plot copy. They are inspection aids, not manufacturing artwork.
The antenna areas are provisional: substrate remains beneath the inboard
antennas; RF keepout, module and enclosure dimensions are not verified.
Mechanical and solder access, bypass loop behavior, power sequencing,
back-powering, RF, electrical safety and bench behavior remain unresolved.
Schematic ERC retains 59 findings. Do not fabricate, assemble or power.

Reproduction
------------
From repository root, with the pinned KiCad 10.0.2 Docker image available:
  bash hardware/pcb-redesign/v5/routing/placement-integrated/build.sh placement-integrated-replay
The sibling output must not already exist. The build hashes the published
C6 input and each standalone reference board, applies guarded local copies
of the three transformations, and compares each footprint/copper delta
against its exact verified standalone result. It rejects reapplication and
wrong hashes, refills/saves, runs DRC/parity/domain/zone/clearance checks,
and creates plots and a saved-board hash. It uses no network and only its
output directory is writable. Remove the replay directory after inspection;
the published board is never overwritten. Generated UUIDs/timestamps can
change its hash: use the replay's own reports. An independent replay passed
with matching geometry, plane audit and clearance results.

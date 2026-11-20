Controller bypass placement experiment — NOT FOR FABRICATION OR POWER-UP
========================================================================

The project-local sym-lib-table resolves DAR1000ES symbols through
${KIPRJMOD}/../../DAR1000ES.kicad_sym, the shared v5 library. Keep the v5
directory layout; the build copies the table from placement-c6.

This independent candidate starts from integrated-review/clearance-first-
corrected/result.kicad_pcb. It moves C1 from (25,44,90°) to (30,24,180°),
and C2 from (25,69,90°) to (30,49,180°). Their supply pads now lie at
(25,24) and (25,49) respectively. New 0.8 mm F.Cu traces connect them
directly to U3.14 and U4.14. Existing supply trunks are kept joined by two
new through vias at the former supply-pad positions (25,39) and (25,64).
Five old ground-pad branches were removed; the moved ground pads depend on
the refilled GND zones, not a new explicit ground track. C1/C2 reference
text is also moved.

The C1/U3 and C2/U4 supply pad-center distance is now 3.380 mm (was
11.620 mm); track-only supply distance is 3.380 mm (was 13.248/12.784 mm).
The ground pad-center distance to pin 7 is 15.029 mm (was 17.699 mm). The
track-only ground graph has no route from either moved capacitor to its IC;
filled-zone connectivity passes native DRC, but the actual return path,
loop area, inductance, and power-integrity improvement are NOT established.

result.kicad_pcb is the standalone candidate. Native KiCad 10.0.2
refill-and-save DRC and schematic-parity DRC have zero reported violations,
unconnected items and parity issues. A second read-only native DRC also
passes without changing the saved-board hash (result-sha256.txt).
Four inherited checks are ignored: track_not_centered_on_via,
tuning_profile_track_geometries, footprint_filters_mismatch and
footprint_type_mismatch. result-audit.json records exact netlist/UART checks,
classified section envelopes, unchanged rule areas, GND fills, pad geometry
and geometry/path measurements. Only the two authorized footprint moves
are allowed when compared with the input. Thermal-gap samples are not a
return-current or thermal analysis.

result-comparison.json compares native PTH pad-to-unrelated-track/via
geometry with the input: minimum 0.201700 mm, 144 pairs below 0.30 mm,
45 below 0.25 mm, unchanged by this experiment. Counts are item/layer
pairs, not unique locations; they exclude zones, pad-pad, non-PTH holes,
SMD pads and installed parts. Mechanical fit, assembly, RF, electrical
safety and bench behavior remain unverified.

Replay from repository root:
  bash hardware/pcb-redesign/v5/routing/placement-controller/build.sh \
    hardware/pcb-redesign/v5/routing/integrated-review/clearance-first-corrected/result.kicad_pcb \
    another-name
The pinned KiCad Docker image is used without network; output stem must be
unused. It runs guarded replay tests, refill DRC, parity, audits, clearance
measurement and a second read-only DRC. Generated UUIDs and timestamps can
change. apply.py accepts an alternate input with unchanged local C1/C2
geometry and exact incident tracks; it rejects in-place or repeated replay.
The source remains untouched. Regenerate evidence on any composed board.

Integration test
----------------
combined.kicad_pcb is the same replay applied after placement-c6's saved
result with SHA-256 fb1f06735ecc218e2946121efeb44f91a6d88a2804b6029a4e8973fffa8e859e.
Its saved-board hash is recorded in combined-sha256.txt. The same native
refill DRC, parity DRC, read-only DRC, domain and geometry checks pass;
combined-comparison.json reports 144 pairs below 0.30 mm, 45 below 0.25 mm,
minimum 0.201700 mm. One pair entered and one left the 0.5 mm reporting
threshold versus the original; no pair newly entered below 0.30 mm.
This proves only this particular C6/controller composition, not composition
with any other independent change. The same physical and electrical
limitations above apply.

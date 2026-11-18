Trial C — local clearance experiment, NOT fabrication-ready
==========================================================

This is an independent derivative of placement-trial B, not an integration
with any other trial. It keeps B's placement, board outline, two antenna rule
areas, vias, pad and footprint geometry, widths, nets and all other board
data. Only endpoints of five existing B.Cu segments move at three junctions.
No new rules, exclusions, pads, layers or router were used. The long U5-VIN
segment is now slightly slanted; adjacent segments are no longer necessarily
45 degrees. Inspect manufacturability and assembly separately.

Source board SHA-256:
  2a6f2adb1d2c4078de47b7a6d337af844bace43cf1a1155d9afe8d2e7d51e7e8
Candidate board SHA-256:
  f99f7348a54bc94fd867fb7ec5e5e0f9a544eb5cf260c7a8530197dcbbef90fb
Project SHA-256:
  50232cc98a9d9072bd8f43c5f5ec578d815ad27146f54a17ccc97d2d18c3a5ed
The schematic copies are byte-identical to the original v5 hierarchy and
are retained beside the same-stem board and project for parity checks. The
footprint table points back to the original v5 library.

Observed changes, native KiCad copper-shape distances
---------------------------------------------------
Measurements compare the retained placement-trial/trial-b-tht-clearance.json
with tht-clearance.json, using the same KiCad 10.0.2 tool and 0.50 mm cutoff.
Unrelated plated-through-hole pad vs track/via pairs are counted per common
copper layer and segment, not unique locations.

* U11 pad 3 to the horizontal SONY_5V_SENSE segment, B.Cu:
  0.201700 -> 0.351701 mm; this is also that pad's measured local minimum.
* U1-CONTROLLER1 J3.11–J3.22 to the long U5-VIN segment, B.Cu: each
  0.201700 -> 0.398570 down to 0.224405 mm, respectively.
  At J3.11 the adjacent diagonal improves 0.201657 -> 0.261535 mm;
  that diagonal remains the pad's nearest unrelated track.
* Across the entire board, pairs below 0.30 mm decrease from 330 to 322;
  the 0.50 mm report has 465 pairs both before and after. Among pairs present
  in both reports 14 distances increase and none decrease; no pairs enter or
  leave that cutoff. This comparison does not imply anything about pairs
  outside the cutoff, pad-to-pad, zones, non-PTH holes or non-PTH pads.
* The board-wide minimum remains 0.201657 mm at another pad/track pair.
  Thus this does NOT establish generous or universal 0.30 mm spacing.

The initial test moved the entire U5-VIN segment 0.20 mm left and the IO4
segment by R3 0.15 mm upward, along with the U11 move. It failed native DRC:
four track-to-track conflicts at IO4/IO42 and a 0.1828 mm track-to-C8 pad
gap. Those shifts were not retained. The final change moves only the upper
U5-VIN junction, preserving its remote diagonal and avoiding that conflict.
No claim is made that this small, local search is optimal or exhaustive.

Validation and limitations
--------------------------
drc.json and drc-parity.json: native KiCad 10.0.2, zero violations, zero
unconnected items; the latter also reports zero schematic parity issues.
The project has no DRC exclusions and missing-courtyard is an error. Four
checks remain ignored: track_not_centered_on_via, tuning_profile_track_
geometries, footprint_filters_mismatch, footprint_type_mismatch. A zero
report does not verify them. audit.txt records the retained netlist/319 node,
exact UART endpoints, y=150 mm section and component-envelope audits.
It also verifies the exact board text differs only in the five intended
segment endpoint coordinates; there are 715 segments, seven vias and 0.30 mm
minimum track width. The retained measurement and board-audit unit suites
passed (7 and 10 tests). These audits do not model plugs, cables, installed
modules, chassis, RF, electrical return paths or the actual antenna keepout.
Trial B's decoupling limitations still apply; no circuit, mechanical, thermal,
RF, safety, fabrication or assembly approval is implied.

Reproduction (repository root)
------------------------------
Requires Docker image kicad/kicad:10.0.2 (observed digest
sha256:165c81785b2df23a09892f4cc53bc0095a83b469bfbbe07989670d64049677a7).
Use an existing writable OUT directory outside the repository. No router JAR
is needed. The container runs with the repository read-only; HOME is
deliberately unwritable, so KiCad may print configuration-directory errors.

  P=hardware/pcb-redesign/v5/routing/clearance-trial-c
  V=hardware/pcb-redesign/v5
  docker run --rm --network none --user "$(id -u):$(id -g)" \
    -e HOME=/nonexistent -e PYTHONDONTWRITEBYTECODE=1 \
    -v "$PWD:/work:ro" -v "$OUT:/out:rw" --entrypoint /usr/bin/python3 \
    kicad/kicad:10.0.2 /work/$P/build.py \
    /work/$V/routing/placement-trial/silk-b/result.kicad_pcb /out/rebuilt.kicad_pcb
  sha256sum "$OUT/rebuilt.kicad_pcb" "$P/DAR-1000ES-v5.kicad_pcb"
  docker run --rm --network none --user "$(id -u):$(id -g)" \
    -e HOME=/nonexistent -e PYTHONDONTWRITEBYTECODE=1 -v "$PWD:/work:ro" \
    -v "$OUT:/out:ro" --entrypoint /usr/bin/python3 kicad/kicad:10.0.2 \
    /work/$P/audit.py /work/$V/routing/placement-trial/silk-b/result.kicad_pcb \
    /out/rebuilt.kicad_pcb /work/$V/DAR-1000ES-v5.net.xml
  docker run --rm --network none --user "$(id -u):$(id -g)" \
    -e HOME=/nonexistent -v "$PWD:/work:ro" --entrypoint kicad-cli \
    kicad/kicad:10.0.2 pcb drc --schematic-parity --format json -o /dev/stdout \
    /work/$P/DAR-1000ES-v5.kicad_pcb
  docker run --rm --network none --user "$(id -u):$(id -g)" \
    -e HOME=/nonexistent -e PYTHONDONTWRITEBYTECODE=1 -v "$PWD:/work:ro" \
    --entrypoint /usr/bin/python3 kicad/kicad:10.0.2 \
    /work/$V/routing/measure_tht_clearance.py /work/$P/DAR-1000ES-v5.kicad_pcb

The parity command checks the retained candidate; first compare the rebuilt
hash to establish it is the same board. Separate normal DRC omits
--schematic-parity. Report dates and tool logs need not be bit-identical.

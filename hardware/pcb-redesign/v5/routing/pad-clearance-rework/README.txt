Track-to-PTH-pad clearance rework — trial, NOT fabrication-ready
================================================================

This derives from ../decoupling-trial/result.kicad_pcb, not a fully
integrated design. It moves only existing straight-track endpoints:
113 bounded junction moves affecting 264 segments, including both layers
and numerous controller, audio, logic and connector locations. Adjacent
segments were moved together; some resulting tracks are no longer 45
degrees. No segments, vias, nets, widths, footprints, pad geometry, holes,
rules, exclusions or zones were added, removed or altered. The project is
byte-identical to the decoupling trial: Default and Power netclass
clearances remain 0.20 mm; no global rule was increased.

The immutable source SHA-256 is
53428c44aaf48bd0ea867c7b11f82e9277dcee58e0993fbcc820f4a65fc4612f.
The result SHA-256 is
2a8b6dbc86eee45d72d20d4c0928f08e6cf29a6718ab4d71035621bd497968a8.
audit.json proves that replacing only the listed segment blocks reproduces
all other source board text exactly, including all pad geometry. apply.py
replays moves.json and produced a byte-identical result. The copied
schematics, project and footprint table support same-stem parity checking.

Measured results
----------------
clearance.json and ../decoupling-trial/tht-clearance.json use the same
KiCad 10.0.2 native effective copper shapes and measure every unrelated
PTH-pad/track-or-via/common-layer pair. 224,994 pairs are examined in each.
Pairs are segment-specific, not independent pad locations:

                                 baseline       result
  Below 0.30 mm                     332           142
  Below 0.25 mm                     217            44
  Board minimum (mm)             0.201657      0.201700
  At or below 0.50 mm               468           390

comparison.json matches pad UUID, item UUID and layer. Of pairs in both
0.50 mm reports, 162 improved and 21 worsened; 87 left and 9 entered the
0.50 mm report. No pair worsened to below 0.30 mm (2 nm tolerance), and no
new pair entered below 0.30 mm. Improvements occur on many references, not
just one long trace. These numbers do not establish universal 0.30 mm
clearance: 142 pairs remain below it. The comparison covers PTH pads to
unrelated track/via copper only, not pad-pad, zones, non-PTH holes or SMD
pads. The measurement is a native geometric calculation, not physical
fabrication tolerance.

Native KiCad 10.0.2 ordinary DRC and schematic-parity DRC report zero
violations and unconnected items; parity also reports zero parity issues.
The baseline parity report is likewise clean. Four inherited checks are
ignored: track_not_centered_on_via, tuning_profile_track_geometries,
footprint_filters_mismatch and footprint_type_mismatch; there are no DRC
exclusions and missing courtyard is an error. domain-audit.txt checks the
319-node netlist, exact UART endpoints, section envelopes and antenna rule
area bounds/restrictions; crossing coordinates are unchanged at y=150 mm.
Exact board-text comparison is stronger than the placement-only audit.

The small moves have side effects on existing routes. paths.json and the
decoupling-trial baseline measurement report model nine changed shortest
capacitor-to-supply-pin centerline paths, all longer: C1 supply 12.804 ->
13.248 mm; C2 ground 122.190 -> 122.635; C3 ground 181.309 -> 182.948;
C4 supply 38.401 -> 38.845 and ground 120.790 -> 121.542; C6 supply
105.586 -> 106.474 and ground 74.717 -> 75.161; C7 ground 20.493 ->
20.911; C11 ground 32.112 -> 32.210. Other modeled paths remain unchanged.
These are geometric shortest paths, not electrical return-current or loop
inductance validation. The inherited decoupling trial's major electrical,
mechanical, RF and solder-access limitations remain; inspect slanted tracks
and do not treat this trial as a fabrication or power-up approval.

Method and integration
----------------------
search.py is the bounded exploration used on a COPY of the exact source:
for initially sub-0.30 mm pairs, it tests 0.1/0.2/0.3 mm orthogonal
junction offsets, scores native-shape deficits, rejects reductions below
0.30 mm with a 2 nm tolerance, and accepts only ordinary DRC-clean steps.
It is a greedy, non-exhaustive experiment that overwrites result.kicad_pcb;
do not run it on the retained result. The replay manifest is the deliverable.

apply.py accepts a different integrated candidate without requiring a whole
board hash. It checks every touched track's original UUID, endpoints, net,
layer and width, each old junction's exact incident tracks and pad/centerline
contacts; it rejects copper zones, non-two-layer boards, conflicts and
in-place output. Unrelated integrated edits are retained, but changed
routing at a targeted junction may make replay impossible. A successful
replay is NOT proof that the integrated design is safe: other nearby
integrated changes may create new clearance or connectivity problems. Rerun
DRC, parity, shape measurements, path/netlist/domain checks and engineering
review on the actual integrated project. Do not waive failed preconditions.

Reproduction from repository root
---------------------------------
Requires Docker image kicad/kicad:10.0.2, digest
sha256:165c81785b2df23a09892f4cc53bc0095a83b469bfbbe07989670d64049677a7.
No router or JAR is needed. HOME is deliberately unwritable; harmless KiCad
configuration/font-cache messages may appear. All scratch files below are
inside this trial directory and must be removed after checking.

  P=hardware/pcb-redesign/v5/routing/pad-clearance-rework
  V=hardware/pcb-redesign/v5
  K="kicad/kicad:10.0.2"
  docker run --rm --network none --user "$(id -u):$(id -g)" \
    -v "$PWD:/work" -w /work -e HOME=/nonexistent \
    -e PYTHONDONTWRITEBYTECODE=1 --entrypoint /usr/bin/python3 "$K" \
    "$P/apply.py" "$V/routing/decoupling-trial/result.kicad_pcb" \
    "$P/rebuilt.kicad_pcb"
  sha256sum "$P/rebuilt.kicad_pcb" "$P/result.kicad_pcb"
  python3 "$P/audit.py" "$V/routing/decoupling-trial/result.kicad_pcb" \
    "$P/rebuilt.kicad_pcb"
  docker run --rm --network none --user "$(id -u):$(id -g)" \
    -v "$PWD:/work" -w /work -e HOME=/nonexistent \
    -e PYTHONDONTWRITEBYTECODE=1 --entrypoint /usr/bin/python3 "$K" \
    "$P/test_apply.py"
  docker run --rm --network none --user "$(id -u):$(id -g)" \
    -v "$PWD:/work" -w /work -e HOME=/nonexistent --entrypoint kicad-cli "$K" \
    pcb drc --schematic-parity --severity-all --exit-code-violations \
    --format json -o "$P/check-parity.json" "$P/result.kicad_pcb"
  docker run --rm --network none --user "$(id -u):$(id -g)" \
    -v "$PWD:/work" -w /work -e HOME=/nonexistent \
    -e PYTHONDONTWRITEBYTECODE=1 --entrypoint /usr/bin/python3 "$K" \
    "$V/routing/measure_tht_clearance.py" "$P/rebuilt.kicad_pcb" \
    > "$P/check-clearance.json"
  python3 "$P/compare.py" "$V/routing/decoupling-trial/tht-clearance.json" \
    "$P/check-clearance.json"
  rm -f "$P/rebuilt.kicad_pcb" "$P/rebuilt.kicad_pro" "$P/rebuilt.kicad_prl" \
    "$P/check-parity.json" "$P/check-clearance.json" "$P/result.kicad_prl"

The retained result, rather than a potentially project-less rebuilt board,
is used in the parity command after hash equality is established. For an
integrated candidate, use its own same-stem project, schematic hierarchy and
footprint table; run both normal and parity DRC with exit-code checking.

Power rework checkpoint — incomplete; NOT for fabrication or power-up
=====================================================================

This is a new board derived from ../decoupling-trial/result.kicad_pcb;
that checkpoint is untouched. It is not the requested finished bypass
placement/power design. No footprint was moved. All connector positions,
footprint/pad positions and nets remain unchanged. The two provisional
antenna rule areas remain unchanged. The substrate remains underneath
the antenna areas; manufacturer review has identified that limitation.
The rectangles are not a validated antenna solution and RF performance,
clearance and the installed module orientation are NOT verified.

Actual changes: a common GND zone on each copper layer over the whole
board, 0.25 mm thermal gap/spoke width and KiCad's always-remove-islands
setting, with no intentionally split grounds. Existing GND tracks are
retained. A 0.30 mm B.Cu GND segment from U6.7 (50.24,210) to
(50.24,212) connects an otherwise starved thermal. Two added 0.30 mm
power branches are defined by supply-branches.json: C3 to U2.14 B.Cu
and C6 to U8.14 F.Cu. These are additions to the old network, not an
optimized or isolated supply tree. The C6 branch makes a substantial
detour; neither branch establishes a compact bypass loop.

Evidence
--------
* result.kicad_pcb SHA-256:
  e19e9908fe62e82e88d0f32ed86c2eb219e02af9a60c4565729e243f000d3387
  Input SHA-256:
  53428c44aaf48bd0ea867c7b11f82e9277dcee58e0993fbcc820f4a65fc4612f
* Native KiCad 10.0.2 drc.json after refill and parity.json report zero
  violations, unconnected items and parity issues. The project has no
  exclusions; the four ignored checks are listed in the reports.
* audit.py uses the current routing/board_ops.py netlist, exact UART and
  y=150 section audits, plus classified component envelopes. It requires
  exactly two filled copper zones, both GND, one on each layer, thermal
  pad connection and always-remove-islands. Thus even a normally
  authorized power or UART net is forbidden as an area fill crossing the
  boundary (indeed, anywhere in this candidate). Rule area restrictions
  and bounds match the source; all placements and pad nets match.
* KiCad refill produced two F.Cu and eleven B.Cu filled polygons, with
  zero flagged isolated polygons; island removal is enabled on both.
  Native DRC reports no starved thermals. For each of C1-C8/C14 and its
  IC's actual ground supply pin, audit.json records sampled filled
  copper in the thermal gap on both layers, not just zone definitions.
  These checks and KiCad connectivity are not a field solver or a proof
  that return current follows a desired path. Multiple retained polygons
  are not evidence of an intentional split: connections can use tracks,
  plated holes and the opposite layer. Inspect return currents and plane
  constrictions before accepting the design.
* crossings.json records the unchanged track crossings of the section
  line; the two GND fills also cross it. This is not a corridor or return
  current analysis. audit.json reports distances to actual supply pins
  (DIP pin 14/7, supervisor pin 2/3). Its shortest paths use tracks and
  pads only, exclude all fill, treat via barrels as zero length and do
  not measure loop inductance. Do not interpret track-only GND lengths as
  the filled plane return path.
* C3 supply track-only shortest path is 23.732 mm versus 26.468 mm in the
  source; C6 is 41.024 mm versus 105.586 mm. Remaining supply lengths
  in mm: C1 12.804, C2 12.784, C4 38.401, C5 32.228, C7 4.380,
  C8 22.526, C14 7.547. Source pad-center placement remains: C1 and C2
  11.620 mm to VCC, C3 and C4 22.021 mm, C5 17.713 mm, C6 24.229 mm,
  C8 22.037 mm. Actual ground-pin center distances are 17.699, 17.699,
  26.193, 26.193, 27.947, 9.231 and 22.137 mm respectively. C7's
  actual U9.7 ground is 15.775 mm away despite its close VCC pad.
  These placements remain significant blockers; a coherent floorplan
  and reroute are still required for C1-C6/C8 and review of C7/C14.
* grid-results.jsonl documents a bounded 0.5 mm-grid search around
  existing placements; no C1, C2, C4, C5 or C8 branch was found by that
  search. It is not an exhaustive search, a placement study or proof
  that a route is impossible. The successful raw paths were simplified
  by merging collinear segments and independently rechecked by DRC.
* tht-clearance.json reports a 0.201657 mm minimum unrelated track/via
  to PTH-pad copper clearance and 334 pad/item/layer pairs under 0.30 mm.
  It does not measure zones, pad-pad, non-PTH holes or installed parts;
  the 0.30–0.50 mm THT goal remains unmet. Mechanical fit, assembly,
  supply integrity, signal/return behavior and bench tests are unverified.

Reproduction
------------
From repository root, using kicad/kicad:10.0.2 digest
sha256:165c81785b2df23a09892f4cc53bc0095a83b469bfbbe07989670d64049677a7.
The generator replaces ONLY the result.kicad_pcb in this directory; it
never edits the preserved input. Generated UUIDs and byte hashes can
vary. The final DRC refill is required to save actual copper polygons.
The copied schematic hierarchy and project are needed for parity.

  P=hardware/pcb-redesign/v5/routing/power-rework
  V=hardware/pcb-redesign/v5
  docker run --rm --network none --user "$(id -u):$(id -g)" \
    -e HOME=/nonexistent -e PYTHONDONTWRITEBYTECODE=1 \
    -v "$PWD:/work" -w /work --entrypoint /bin/bash kicad/kicad:10.0.2 -c '
      set -e
      P=hardware/pcb-redesign/v5/routing/power-rework
      V=hardware/pcb-redesign/v5
      /usr/bin/python3 "$P/generate.py"
      kicad-cli pcb drc --refill-zones --save-board --format json --severity-all \
        --exit-code-violations -o "$P/drc.json" "$P/result.kicad_pcb"
      kicad-cli pcb drc --schematic-parity --format json --severity-all \
        --exit-code-violations -o "$P/parity.json" "$P/result.kicad_pcb"
      /usr/bin/python3 "$P/audit.py"
      /usr/bin/python3 "$P/test_audit.py"
      /usr/bin/python3 "$V/routing/test_board_ops.py"
      /usr/bin/python3 "$V/routing/decoupling-trial/test_measure_paths.py"
      /usr/bin/python3 "$V/routing/decoupling-trial/crossings.py" \
        "$P/result.kicad_pcb" > "$P/crossings.json"
      /usr/bin/python3 "$V/routing/measure_tht_clearance.py" \
        "$P/result.kicad_pcb" --threshold-mm 0.3 > "$P/tht-clearance.json"
      rm -f "$P/result.kicad_prl"
    '

HOME is intentionally unwritable, so KiCad may print configuration
warnings; check exit status and report contents. A successful DRC is not
electrical, RF, mechanical, manufacturing or safety signoff.

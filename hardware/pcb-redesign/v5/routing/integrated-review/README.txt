v5 integrated review — experimental, NOT for fabrication or power-up
=====================================================================

This distinct candidate applies the actual saved silk-rework overlay to
the actual saved power-rework board, then refills and saves zones with
KiCad 10.0.2. It is not the pad-clearance-rework candidate. The power
source explicitly calls itself an incomplete checkpoint, not a finished
power design; integrating it does not resolve that limitation.

result.kicad_pcb SHA-256:
  16a88150a9eef163fbc119e894eaf3c47233ebe6db1f0cc457ae5fe6c4389764
Power input SHA-256:
  e19e9908fe62e82e88d0f32ed86c2eb219e02af9a60c4565729e243f000d3387
Silk result SHA-256:
  a46a6668287fbf6cfe683f042e2ea08dc502d9e10ea7c8cfbd2c2bb61b709780
The overlay script and other consumed inputs are pinned in inputs.sha256;
outputs.sha256 inventories this saved candidate and its evidence. New
overlay UUIDs vary on regeneration, so the resulting board hash will vary.

Evidence index
--------------
* clearance-first/ retains the failed uncorrected clearance/power/silk
  composition; clearance-first-corrected/ is a separate corrected review
  candidate with its own tests, measurements, reports and previews.
  This parent power+silk candidate remains unchanged.
* result.kicad_pcb, result.kicad_pro, result.kicad_sch and two child
  schematic sheets: review board and matching project/hierarchy.
* integration-audit.json: 61 added drawings geometrically match the saved
  silk board (60 texts and one line); after removing them and ignoring
  refill caches, normalized native board data matches the power input.
* drc.json and parity.json: native DRC with refill/save and native schematic
  parity respectively; zero violations, unconnected items and parity
  issues. Four inherited checks are ignored: track_not_centered_on_via,
  tuning_profile_track_geometries, footprint_filters_mismatch and
  footprint_type_mismatch. DRC is not electrical or physical signoff.
* verification.json and verification-drc.json: final native DRC of the
  already-refilled saved PCB, with the repository mounted read-only and no
  refill or save. The before and after PCB SHA-256 are both
  16a88150a9eef163fbc119e894eaf3c47233ebe6db1f0cc457ae5fe6c4389764.
  The report SHA-256, command mode, exit status, counts and ignored checks
  are recorded in verification.json.
* audit.json: netlist, exact UART, section and classified component-envelope
  checks; footprint/pad position and net equality to the decoupling source;
  unchanged provisional antenna rule-area bounds/flags; filled GND zones
  and bypass geometry/path/thermal samples. Both copper layers use GND
  zones, thermal connections and always-remove-islands. Refill produced two
  F.Cu and eleven B.Cu polygons, none flagged as isolated. The audit samples
  actual filled copper around C1–C8/C14 and their IC ground pins on both
  layers; it is not a proof of return current paths or thermal performance.
* crossings.json: track centerline crossings of y=150 mm; the GND fills
  also cross the boundary. This is not a corridor or return-current audit.
* tht-clearance.json: native shape distances for unrelated tracks/vias to
  plated through-hole pads, per copper layer. Minimum 0.201657 mm; 334
  pad/item/layer pairs at or below 0.30 mm. It omits zones, pad-pad,
  non-PTH holes and installed parts. The 0.30–0.50 mm goal remains unmet.
* preview/README.txt: assembly, front/back copper plots and closeup index.

Limitations
-----------
No capacitor, connector, footprint or pad was moved by this integration or
the power checkpoint relative to decoupling-trial. In particular C1/C2
remain 11.620 mm from their IC supply pins, C3/C4 22.021 mm, C5 17.713 mm,
C6 24.229 mm and C8 22.037 mm (pad-center distances). C7 ground is
15.775 mm from U9 ground. C3 and C6 supply branches are additions, not
optimized bypass loops; C6's track-only path is 41.024 mm. See audit.json
for all distances. Track-only paths exclude zone copper and use zero via
barrel length; they do not represent loop inductance or actual return paths.
A coherent placement and reroute remain necessary.

The antenna rule rectangles are provisional; substrate still exists below
them. Module orientation, RF clearance and RF performance are not verified.
Neither current return paths nor plane constrictions, supply integrity,
mechanical fit, cable/assembly visibility, solder access, safety or bench
behavior have been verified. See the power-rework and silk-rework READMEs
for detailed inherited restrictions and labeling caveats. No manufacturing
or fabrication readiness is claimed.

Reproduction and verification
-----------------------------
From repository root, with Docker and the locally available pinned KiCad
image digest used by build.sh:

  sha256sum --check hardware/pcb-redesign/v5/routing/integrated-review/inputs.sha256
  sha256sum --check hardware/pcb-redesign/v5/routing/integrated-review/outputs.sha256

Run the final read-only DRC again with
  PYTHONDONTWRITEBYTECODE=1 python3 hardware/pcb-redesign/v5/routing/integrated-review/verify_saved.py
It refreshes verification.json and verification-drc.json, so re-inventory
outputs.sha256 afterwards. It does not refill or change the saved board.

To regenerate, first remove only this directory's result.kicad_pcb and run
  bash hardware/pcb-redesign/v5/routing/integrated-review/build.sh
The script refuses to overwrite a board, checks pinned inputs before and
after, mounts the repository read-only except this directory, applies silk,
refills/saves, runs DRC and parity, audits, tests, and plots. It cleans
KiCad temporary files. Review fresh reports and update the output manifest
and documented board hash after regeneration; UUIDs and timestamps vary.
Do not use the retained manifest to certify regenerated bytes.

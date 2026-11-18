Clearance-first corrected — review candidate, NOT FOR FABRICATION OR POWER-UP
============================================================================

The guarded clearance replay is applied first to decoupling-trial; its
output must match the saved pad-clearance-rework board byte-for-byte. The
unchanged power generator then applies its branch and zone preconditions
and silk-rework applies its connector/net/courtyard preflight. A guarded
post-composition edit moves only the shared junction of two NEW C6 supply
branch segments from (46.5,72.5) to (46.5,72.6) mm on F.Cu. It preserves
their other endpoints, 0.30 mm widths and LOCAL_5V net. repair.py checks
exact incident segments, their new-track identity, net, width, pad contact,
and destination endpoint; test_repair.py checks replay and rejects duplicate
application, in-place operation and existing output. All other existing
clearance-board tracks match by UUID and geometry, and the 46 added power
segments match power-rework except the two corrected endpoints. The 61 silk
items match the saved silk geometry. See composition.json.

The uncorrected version in ../clearance-first/ has two 0.195 mm track-to-
track violations against a 0.200 mm requirement. The original, clean
power+silk candidate is preserved in the parent directory. Neither source
board is modified by this candidate's build.

result.kicad_pcb SHA-256:
  c63fa89924e244bbf6bfd92f2c72e6c9d34117106b4bd87cf46f7971078920c5
KiCad 10.0.2 refill/save DRC and schematic-parity DRC report zero
violations, zero unconnected items and zero parity issues; exit codes are
both zero. verification.json records that same hash immediately before and
after a second read-only native DRC, and hashes verification-drc.json.
Four inherited checks remain ignored: track_not_centered_on_via,
tuning_profile_track_geometries, footprint_filters_mismatch and
footprint_type_mismatch. DRC is not an electrical or physical signoff.

Evidence and review index
-------------------------
* audit.json: netlist, exact UART, section and classified component-envelope
  checks, unchanged footprint/pad placements and nets, unchanged provisional
  antenna rule-area bounds/flags, GND fills, path distances and sampled
  thermal-gap copper. Refilled zones contain three F.Cu and twelve B.Cu
  polygons, none flagged as islands. Samples do not establish thermal
  performance or the actual current return path.
* clearance.json: actual saved-board native PTH pad-to-unrelated-track/via
  per-layer geometric measurements at a 0.50 mm reporting threshold.
  144 pairs are below 0.30 mm, 45 below 0.25 mm, minimum 0.201700 mm.
  baseline-comparison.json compares against 332/217 in decoupling-trial;
  comparison.json compares against 142/44 in the clearance-only result.
  Adding power tracks introduces two new pairs below 0.30 mm. Pair counts
  are segment-specific, not independent pad locations. Neither measurement
  covers zones, pad-pad, non-PTH holes, SMD pads or installed parts.
* crossings.json lists track-centerline section crossings, not a return or
  corridor analysis. preview/ contains full-page and closeup assembly and
  front/back copper plots; see preview/README.txt.
* inputs.sha256 pins the scripts, source boards, project and footprint
  inputs; outputs.sha256 inventories this saved candidate and evidence.

All footprint and capacitor placements are unchanged from decoupling-trial.
C1/C2 supply pads are 11.620 mm from their IC pins, C3/C4 22.021 mm, C5
17.713 mm, C6 24.229 mm and C8 22.037 mm; C7 ground is 15.775 mm from
U9 ground. C6's track-only supply path is 40.998 mm. These distances are
not loop inductance or actual return paths; supply integrity and coherent
bypass placement remain unresolved. The provisional antenna rule areas
still have substrate beneath them. Module orientation, RF clearance and RF
performance, current returns, mechanical fit, solder access, assembly,
safety and bench behavior remain unverified. No fabrication claim is made.

Reproduce from repository root with the pinned KiCad Docker image: verify
inputs.sha256, remove only this directory's result.kicad_pcb, then run
  bash hardware/pcb-redesign/v5/routing/integrated-review/clearance-first-corrected/build.sh
The script mounts the repository read-only except this directory, tests the
guarded replay, restores the exact project rules before native DRC, saves
refilled zones, runs parity and all audits/measurement and regenerates
previews. It returns nonzero for any DRC/parity issue after saving evidence.
KiCad-generated UUIDs and report times vary. Re-run verification, review
the results, and update recorded hashes and outputs.sha256 after regeneration.

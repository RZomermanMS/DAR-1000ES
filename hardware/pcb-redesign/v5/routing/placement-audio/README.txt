Audio bypass placement trial — NOT FOR FABRICATION OR POWER-UP
=============================================================

This is an independent copy of integrated-review/clearance-first-corrected,
not a combined board with other placement trials. Source SHA-256 is
c63fa89924e244bbf6bfd92f2c72e6c9d34117106b4bd87cf46f7971078920c5.
result.kicad_pcb SHA-256 is recorded in board.sha256 and verification.json.

The actual through-hole footprints move from (25,197), (25,222), (25,247)
to C3 (35,173.5, 0 degrees), C4 (35.3,199.38, 0 degrees), C5 (40,223,
180 degrees), in mm. Each new capacitor supply pad connects directly to
the corresponding U2/U6/U7 pin 14, not a logic pin: C3 on F.Cu, C4 and C5
on B.Cu, 0.30 mm width. C4's former LOCAL_5V pad was an interlayer
junction, so an 0.8 mm via with 0.4 mm drill replaces that junction.
Existing tracks are retained, including remnants at former capacitor
locations. The moved GND pads use both refilled GND planes; no explicit
ground track or independently verified return-current path is claimed.
No connector, other footprint, pre-existing track or marked silk item is
changed. This is placement-first and preserves the actual netlist.

Measured centerline direct supply distances are 3.880, 3.015 and 4.380 mm,
versus respective 22.021, 22.021 and 17.713 mm pad-center separations in
the source. These are geometric measurements, not inductance or a proof of
globally optimal placement. Capacitor-to-IC ground-pad centers remain 15.398,
14.546 and 15.775 mm apart; track-only ground paths are absent. Thermal gap
samples detect fill near each ground pad on both layers, but do not establish
current return, impedance, plane integrity under operating conditions, or
component electrical performance.

Evidence
--------
* drc.json: KiCad 10.0.2 --refill-zones --save-board, all severities,
  zero violations and zero opens. parity.json: zero violations, opens and
  schematic-parity issues. verification-drc.json repeats read-only DRC on
  the saved board; verification.json records unchanged hash around this run.
  Four inherited checks remain ignored: track_not_centered_on_via,
  tuning_profile_track_geometries, footprint_filters_mismatch and
  footprint_type_mismatch.
* audit.json: exact netlist/UART, section and classified footprint-envelope
  checks, source rule areas, two filled GND zones with thermal settings and
  no flagged islands, sampled thermal-gap copper and bypass distances.
  Normalizing the three moved footprints and removing only the four added
  copper objects and fill caches produces the same serialized board as the
  source. The added tracks and via are separately checked against the plan.
* clearance.json and comparison.json: actual PTH-pad to unrelated track/via
  measurements. Global minimum stays 0.201700 mm; counts below 0.30 mm
  remain 144 and below 0.25 mm remain 45. The nearest reported pair involving
  a moved capacitor is C5.2 to U6_OE_N on F.Cu at 0.3174 mm. Measurements
  omit zones, pad-pad, non-PTH holes, SMD pads, and installed components;
  pairs count segments, not independent locations.
* crossings.json records track-centerline section crossings, not return
  current or routing-corridor analysis.

Run from the repository root, after removing only result.kicad_pcb in this
directory: bash hardware/pcb-redesign/v5/routing/placement-audio/build.sh
The pinned KiCad image must already be present. The script checks
inputs.sha256, uses a network-disabled container with only this directory
writable, performs guarded replay and negative tests, then refills and
checks DRC, parity and audits. Generated UUIDs and timestamps vary; update
output hashes when replaying. It refuses to overwrite an existing board.

The source's provisional antenna rule areas still have substrate beneath
them; RF, mechanical fit, solder access, bypass loop behavior, safety and
bench behavior are unverified. A clean DRC is not fabrication signoff.
